"""
PAPER TRADING strategi S2 "dekat puncak 52 minggu" (lolos data uji di riset #12b, bersih realistis t~2,5 di #12c).

Tujuan: ujian paling jujur = MASA DEPAN. Tiap akhir bulan, saham pilihan S2 DICATAT SEBELUM hari beli; hasil nyata
dipantau dengan harga sungguhan. Aturan S2 TIDAK BOLEH diubah (versi baru = portofolio terpisah dengan nama baru).

Aturan S2 (identik dengan riset_12_gabung_sinyal.py, dibuktikan dengan --cek-riset):
  hari bursa = hari kerja dengan >= 10 saham bertransaksi. Semesta di akhir bulan: harga >= Rp100, median nilai transaksi
  60 hari >= Rp1 miliar, >= 80% hari aktif dalam 250 hari, tanpa lompatan harian > 50% dalam 250 hari, dan keempat sinyal
  riset #12 tersedia (momentum 12-1, puncak 250 hari, volatilitas 120 hari, max return 21 hari). S2 = harga / tertinggi
  250 hari. Beli 20% teratas (bobot sama) di harga TUTUP hari bursa pertama bulan berikutnya, jual di tutup hari bursa
  pertama bulan sesudahnya. Pembanding: semua saham semesta (bobot sama).
  (Satu beda yang tak terhindarkan: riset membuang saham yang tak punya harga masa depan; live tidak tahu masa depan.)
Biaya realistis (riset #12c): tiap saham BARU = 0,4% + max(spread Corwin-Schultz 21 hari, 1 tick / harga).

File di gudang (raw/paper_trading/), HANYA DITAMBAH, catatan lama tidak pernah diubah:
  s2_pilihan.parquet  : tanggal_sinyal, kode, nilai_s2, harga_tutup_sinyal, spread_cs, biaya_saham, baru,
                        dicatat_pada (UTC), dicatat_sebelum_beli (True = sah untuk statistik resmi)
  s2_semesta.parquet  : tanggal_sinyal, kode (pembanding)
  s2_kinerja.parquet  : dihitung ulang tiap jalan dari catatan + harga terbaru (status berjalan/selesai)

Cara pakai:
  python paper_trading.py              -> jalan normal (dipanggil workflow harian), simpan ke data/raw/paper_trading/
  python paper_trading.py --tes        -> hitung pilihan bulan terakhir, tampilkan, TANPA menyimpan
  python paper_trading.py --cek-riset  -> bukti rumus identik dengan riset #12 (pakai data lokal data/raw/harga_idx)
"""
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO = "fadli-sparks/quant-data"
FOLDER = Path("data/raw/paper_trading")
FOLDER_REPO = "raw/paper_trading"
MIN_HARGA, MIN_NILAI, MIN_HARI_AKTIF, MAX_LOMPAT, MIN_SAHAM = 100, 1e9, 0.8, 0.5, 30
KOMISI = 0.004


def jadi_tanggal(x):
    t = pd.DatetimeIndex(pd.to_datetime(x))
    if t.tz is not None:
        t = t.tz_localize(None)
    return t.normalize().astype("datetime64[ns]")


def tick(harga):
    return np.select([harga < 200, harga < 500, harga < 2000, harga < 5000], [1, 2, 5, 10], 25)


def corwin_schultz(tinggi, rendah):
    k = 3 - 2 * np.sqrt(2)
    hl = np.log(tinggi / rendah) ** 2
    beta = hl + hl.shift(1)
    gamma = np.log(np.maximum(tinggi, tinggi.shift(1)) / np.minimum(rendah, rendah.shift(1))) ** 2
    alpha = (np.sqrt(2 * beta) - np.sqrt(beta)) / k - np.sqrt(gamma / k)
    return (2 * (np.exp(alpha) - 1) / (1 + np.exp(alpha))).clip(lower=0)


def siapkan(adj, tutup, volume):
    """Kalender & bahan harian, persis riset_12. Hasil: dict berisi tabel yang dibutuhkan."""
    aktif = volume.fillna(0) > 0
    hari = aktif.index[(aktif.sum(axis=1) >= 10) & (aktif.index.day_of_week < 5)]
    adj, tutup, volume, aktif = (x.loc[hari] for x in (adj, tutup, volume, aktif))
    ret_h = adj.pct_change(fill_method=None)
    b = {"hari": hari, "adj": adj, "tutup": tutup, "aktif": aktif, "volume": volume,
         "median_nilai": (tutup * volume).where(aktif).rolling(60, min_periods=40).median(),
         "porsi_aktif": aktif.rolling(250, min_periods=250).mean(),
         "lompat_maks": ret_h.abs().rolling(250, min_periods=200).max(),
         "puncak_250": adj.rolling(250, min_periods=200).max(),
         "vol_120": ret_h.rolling(120, min_periods=100).std(),
         "max_21": ret_h.rolling(21, min_periods=15).max()}
    akhir = pd.Series(hari, index=hari).groupby(hari.to_period("M")).max()
    b["akhir_bulan"] = pd.DatetimeIndex(akhir.values)
    return b


def pilih_s2(b, tgl_sinyal, wajib_ada=None):
    """Semesta & 20% teratas S2 di akhir bulan tgl_sinyal. wajib_ada = saringan tambahan (hanya untuk --cek-riset)."""
    ab = b["akhir_bulan"]
    i = ab.get_loc(tgl_sinyal)
    if i < 12:
        return None, None, None
    harga_akhir = b["adj"].loc[ab]
    s1 = harga_akhir.iloc[i - 1] / harga_akhir.iloc[i - 12] - 1
    s2 = b["adj"].loc[tgl_sinyal] / b["puncak_250"].loc[tgl_sinyal]
    s3 = -b["vol_120"].loc[tgl_sinyal]
    s4 = -b["max_21"].loc[tgl_sinyal]
    lolos = ((b["tutup"].loc[tgl_sinyal] >= MIN_HARGA) & (b["median_nilai"].loc[tgl_sinyal] >= MIN_NILAI)
             & (b["porsi_aktif"].loc[tgl_sinyal] >= MIN_HARI_AKTIF) & (b["lompat_maks"].loc[tgl_sinyal] < MAX_LOMPAT))
    ok = lolos & s1.notna() & s2.notna() & s3.notna() & s4.notna()
    if wajib_ada is not None:
        ok &= wajib_ada
    if ok.sum() < MIN_SAHAM:
        return None, None, None
    s = s2[ok]
    atas = list(s.index[pd.qcut(s.rank(method="first"), 5, labels=False) == 4])
    return sorted(atas), sorted(s.index), s


def cek_riset():
    """Bukti: pilihan paper_trading == pilihan riset_12 untuk beberapa bulan di data latih, dengan HANYA ~2 tahun data
    (seperti di server), sementara riset_12 memakai seluruh histori."""
    g = {}
    sys.argv = [sys.argv[0]]
    kode = Path("riset_12_gabung_sinyal.py").read_text(encoding="utf-8").split("baris, korelasi, lalu = [], [], {}")[0]
    exec(compile(kode, "riset_12_bagian", "exec"), g)
    adj_r, tutup_r, vol_r = g["adj"], g["tutup"], g["volume"]
    semua_cocok = True
    for bln in ["2010-06", "2015-03", "2018-10"]:
        i = [k for k, t in enumerate(g["akhir_bulan"]) if t.strftime("%Y-%m") == bln][0]
        tgl = g["akhir_bulan"][i]
        # versi riset_12
        ok = g["lolos"].loc[i] & g["ret_pegang"].loc[i].notna()
        for k in g["sinyal"]:
            ok &= g["sinyal"][k].loc[i].notna()
        s = g["sinyal"]["S2"].loc[i][ok]
        riset = sorted(s.index[pd.qcut(s.rank(method="first"), 5, labels=False) == 4])
        # versi paper_trading dengan jendela ~2 tahun (seperti data server)
        mulai = tgl - pd.DateOffset(years=2) - pd.DateOffset(days=40)
        akhir_data = g["awal_bulan"][i + 2]
        b = siapkan(adj_r.loc[mulai:akhir_data], tutup_r.loc[mulai:akhir_data], vol_r.loc[mulai:akhir_data])
        wajib = g["ret_pegang"].loc[i].notna()      # emulasi saringan riset (butuh harga masa depan) khusus untuk cek ini
        live, _, _ = pilih_s2(b, tgl, wajib_ada=wajib)
        cocok = live == riset
        semua_cocok &= cocok
        print(f"   {bln}: riset {len(riset)} saham, paper {len(live)} saham -> {'✅ IDENTIK' if cocok else '❌ BEDA'}"
              + ("" if cocok else f" (hanya riset: {sorted(set(riset) - set(live))}, hanya paper: {sorted(set(live) - set(riset))})"))
    print("🎉 Rumus identik dengan riset #12" if semua_cocok else "❌ ADA PERBEDAAN - jangan dipakai sebelum diperbaiki")
    sys.exit(0 if semua_cocok else 1)


def unduh_harga():
    """~2 tahun harga harian semua saham IDX dari Yahoo (cukup untuk jendela 250 hari + momentum 12 bulan)."""
    import yfinance as yf
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    from daftar_saham import kode_idx            # daftar awal + kode baru (IPO) dari kumpul_daftar_idx.py
    kode = kode_idx()
    bagian = {x: [] for x in ["Adj Close", "Close", "Volume", "High", "Low"]}
    for i in range(0, len(kode), 100):
        df = yf.download(kode[i:i + 100], period="2y", interval="1d", auto_adjust=False, progress=False,
                         group_by="ticker", threads=True)
        for k in kode[i:i + 100]:
            if k not in df.columns.get_level_values(0):
                continue
            for x in bagian:
                bagian[x].append(df[k][x].rename(k.replace(".JK", "")))
        time.sleep(3)
    hasil = {}
    for x, daftar in bagian.items():
        t = pd.concat(daftar, axis=1)
        t.index = jadi_tanggal(t.index)
        hasil[x] = t[~t.index.duplicated(keep="last")].sort_index()
    print(f"📥 Harga {hasil['Adj Close'].shape[1]} saham, {hasil['Adj Close'].index.min().date()} s/d "
          f"{hasil['Adj Close'].index.max().date()}")
    return hasil


def baca_catatan(api, nama):
    """Baca catatan lama dari gudang. Kalau file ADA tapi gagal dibaca -> BERHENTI (jangan sampai menimpa histori)."""
    from huggingface_hub import hf_hub_download
    jalur = f"{FOLDER_REPO}/{nama}"
    if not api.file_exists(REPO, jalur, repo_type="dataset"):
        return None
    for percobaan in range(3):
        try:
            token = os.environ.get("HF_TOKEN") or Path("kunci_hf.txt").read_text().strip()
            return pd.read_parquet(hf_hub_download(REPO, jalur, repo_type="dataset", token=token, force_download=True))
        except Exception as e:
            print(f"   🔌 gagal membaca {nama}: {type(e).__name__}, coba lagi...")
            time.sleep(10)
    print(f"❌ {nama} ada di gudang tapi tidak bisa dibaca -> BERHENTI supaya histori tidak tertimpa")
    sys.exit(1)


def main(pemilih=None, awalan="s2"):
    """pemilih(b, tgl_sinyal) -> (pilihan, semesta, skor). Bawaan = S2. Portofolio lain (mis. dari private/) memakai
    awalan file berbeda; aturannya tidak perlu ada di repo publik."""
    pemilih = pemilih or pilih_s2
    if "--cek-riset" in sys.argv:
        cek_riset()
    tes = "--tes" in sys.argv
    sekarang = pd.Timestamp(datetime.now(timezone.utc)).tz_localize(None)
    h = unduh_harga()
    b = siapkan(h["Adj Close"], h["Close"], h["Volume"])
    hari, ab = b["hari"], b["akhir_bulan"]
    tinggi = h["High"].reindex(index=hari, columns=b["adj"].columns)
    rendah = h["Low"].reindex(index=hari, columns=b["adj"].columns)
    sah = (tinggi > 0) & (rendah > 0) & (tinggi >= rendah) & b["aktif"]
    cs = corwin_schultz(tinggi.where(sah), rendah.where(sah)).rolling(21, min_periods=10).mean()
    b["cs"] = cs                     # dipakai pemilih lain (mis. portofolio ml di private/); S2 tidak memakainya

    # Akhir bulan yang SUDAH lengkap = akhir bulan yang punya hari bursa sesudahnya di bulan berikutnya,
    # ATAU bulan kalender sudah lewat (hari ini sudah bulan berikutnya).
    lengkap = [t for t in ab if t.to_period("M") < sekarang.to_period("M")]
    if not lengkap:
        print("Belum ada akhir bulan yang lengkap")
        return
    tgl_sinyal = lengkap[-1]
    atas, semesta, s = pemilih(b, tgl_sinyal)
    if atas is None:
        print(f"❌ Semesta {tgl_sinyal.date()} terlalu kecil")
        sys.exit(1)
    hari_setelah = hari[hari > tgl_sinyal]
    sudah_beli = len(hari_setelah) > 0 and hari_setelah[0].to_period("M") > tgl_sinyal.to_period("M")
    print(f"📅 Sinyal akhir bulan {tgl_sinyal.date()}: semesta {len(semesta)} saham, pilihan {len(atas)} saham; "
          f"harga beli {'SUDAH' if sudah_beli else 'BELUM'} ada di data")
    if tes:
        print(s[atas].sort_values(ascending=False).round(3).to_string())
        return

    from huggingface_hub import HfApi
    api = HfApi(token=os.environ.get("HF_TOKEN") or Path("kunci_hf.txt").read_text().strip())
    pilihan = baca_catatan(api, f"{awalan}_pilihan.parquet")
    semesta_lama = baca_catatan(api, f"{awalan}_semesta.parquet")

    # 1) Catat pilihan bulan ini KALAU bulan itu belum pernah dicatat (dicek per BULAN, bukan per tanggal, supaya data
    #    Yahoo yang telat tidak membuat satu bulan tercatat dua kali) DAN data cukup segar (<= 5 hari).
    #    Catatan lama tidak pernah diubah.
    bulan_tercatat = set() if pilihan is None else set(pd.to_datetime(pilihan["tanggal_sinyal"]).dt.to_period("M"))
    segar = (sekarang.normalize() - hari[-1]).days <= 5
    if tgl_sinyal.to_period("M") in bulan_tercatat:
        print(f"ℹ️  Pilihan bulan {tgl_sinyal.to_period('M')} sudah tercatat sebelumnya (tidak diubah)")
    elif not segar:
        print(f"⚠️  Data terbaru {hari[-1].date()} terlalu basi -> pencatatan ditunda ke jalan berikutnya")
    else:
        sebelumnya = set()
        if pilihan is not None and len(pilihan):
            terakhir = pilihan["tanggal_sinyal"].max()
            sebelumnya = set(pilihan.loc[pilihan["tanggal_sinyal"] == terakhir, "kode"])
        tk = pd.Series(tick(b["tutup"].loc[tgl_sinyal, atas].values) / b["tutup"].loc[tgl_sinyal, atas].values, index=atas)
        spread = cs.loc[tgl_sinyal, atas]
        baru = pd.DataFrame({
            "tanggal_sinyal": tgl_sinyal, "kode": atas, ("nilai_s2" if awalan == "s2" else "skor"): s[atas].values,
            "harga_tutup_sinyal": b["tutup"].loc[tgl_sinyal, atas].values, "spread_cs": spread.values,
            "biaya_saham": (KOMISI + np.maximum(spread.fillna(tk), tk)).values,
            "baru": [k not in sebelumnya for k in atas], "dicatat_pada": sekarang,
            "dicatat_sebelum_beli": not sudah_beli})
        pilihan = pd.concat([pilihan, baru], ignore_index=True) if pilihan is not None else baru
        sem_baru = pd.DataFrame({"tanggal_sinyal": tgl_sinyal, "kode": semesta})
        semesta_lama = pd.concat([semesta_lama, sem_baru], ignore_index=True) if semesta_lama is not None else sem_baru
        print(f"📝 Pilihan {tgl_sinyal.date()} DICATAT ({len(atas)} saham, "
              f"{'SEBELUM hari beli ✅ sah' if not sudah_beli else 'TERLAMBAT ⚠️ tidak masuk statistik resmi'})")
    if pilihan is None:
        print("Belum ada catatan sama sekali")
        return

    # 2) Hitung ulang kinerja semua portofolio dari catatan + harga terbaru
    adj = b["adj"]
    kinerja = []
    for tgl, grup in pilihan.groupby("tanggal_sinyal"):
        hs = hari[hari > tgl]
        if len(hs) == 0:
            continue
        tgl_beli = hs[0]
        tgl_jual_kand = hs[hs.to_period("M") > tgl_beli.to_period("M")]
        selesai = len(tgl_jual_kand) > 0
        tgl_nilai = tgl_jual_kand[0] if selesai else hari[-1]
        kode_p = [k for k in grup["kode"] if k in adj.columns]
        kode_s = [k for k in semesta_lama.loc[semesta_lama["tanggal_sinyal"] == tgl, "kode"] if k in adj.columns]
        r_p = (adj.loc[tgl_nilai, kode_p] / adj.loc[tgl_beli, kode_p] - 1).dropna()
        r_s = (adj.loc[tgl_nilai, kode_s] / adj.loc[tgl_beli, kode_s] - 1).dropna()
        biaya = grup.loc[grup["baru"], "biaya_saham"].sum() / len(grup)
        kinerja.append({"tanggal_sinyal": tgl, "tanggal_beli": tgl_beli, "tanggal_nilai": tgl_nilai,
                        "status": "selesai" if selesai else "berjalan", "sah": bool(grup["dicatat_sebelum_beli"].all()),
                        "n_saham": len(r_p), "ret_portofolio": r_p.mean(), "ret_semesta": r_s.mean(),
                        "kotor": r_p.mean() - r_s.mean(), "biaya": biaya, "bersih": r_p.mean() - r_s.mean() - biaya,
                        "dihitung_pada": sekarang})
    kinerja = pd.DataFrame(kinerja)
    resmi = kinerja[(kinerja["status"] == "selesai") & kinerja["sah"]] if len(kinerja) else kinerja
    print(f"📊 Portofolio tercatat: {len(kinerja)} | selesai & sah: {len(resmi)}"
          + (f" | rata-rata bersih {resmi['bersih'].mean():+.2%}/bln" if len(resmi) else ""))
    FOLDER.mkdir(parents=True, exist_ok=True)
    pilihan.to_parquet(FOLDER / f"{awalan}_pilihan.parquet", index=False)
    semesta_lama.to_parquet(FOLDER / f"{awalan}_semesta.parquet", index=False)
    kinerja.to_parquet(FOLDER / f"{awalan}_kinerja.parquet", index=False)
    print(f"💾 Tersimpan di {FOLDER}/ (diunggah oleh langkah upload)")


if __name__ == "__main__":
    main()
