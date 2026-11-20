"""
RISET #11: PEMBELIAN SAHAM OLEH ORANG DALAM (SEC Form 4) -> SAHAM AS 1-6 BULAN KE DEPAN
====================================================================================

DUGAAN (ditulis 2026-11-20, SEBELUM data SEC lengkap & SEBELUM melihat hubungan apa pun)
-------------------------------------------------------------------------------------
Saham yang direktur/eksekutifnya MEMBELI di pasar terbuka (kode P, uang pribadi) memberi return lebih tinggi
daripada saham biasa selama beberapa bulan berikutnya (tanda positif).
Alasan logis: orang dalam tahu prospek perusahaannya lebih baik. Menjual bisa karena banyak alasan (butuh uang,
diversifikasi, jadwal 10b5-1), tapi MEMBELI dengan uang sendiri hanya punya satu alasan: mereka kira harganya murah.
Pasar bereaksi lambat karena laporan Form 4 banyak, kecil, dan tersebar (kurang diperhatikan).
Literatur: Lakonishok & Lee (2001), Jeng-Metrick-Zeckhauser (2003, ~6%/thn abnormal), Cohen-Malloy-Pomorski (2012).
Perkiraan jujur: efek ada di data latih 2006-2018 tapi lebih kecil dari literatur lama (pasar makin efisien,
banyak layanan yang memantau Form 4). Efek terkonsentrasi di saham kecil, yang biaya transaksinya lebih mahal.
Saya kira kotor t sekitar 2-4, bersih setelah biaya lebih lemah.

DEFINISI PERISTIWA (tetap)
- Transaksi kode P, form 4 atau 4/A, lembar > 0, harga > 0, BUKAN rencana 10b5-1, pelapor berhubungan Director atau
  Officer (pemegang >10% saja = dana investasi, DIBUANG). Bulan peristiwa = bulan TANGGAL LAPOR (saat publik).
- Cek identitas kode saham: kode bisa ganti/dipakai ulang perusahaan lain. Transaksi dipakai hanya kalau harga beli
  orang dalam cocok dengan harga Yahoo di hari transaksi (rasio dalam +/-15% dari 1, atau dari faktor split umum
  2,3,4,5,10,20 dan kebalikannya, karena harga Yahoo sudah disesuaikan split). Versi KETAT (hanya rasio ~1) = cek ketahanan.

SEMESTA & PORTOFOLIO
- Saham layak di akhir bulan m: harga >= $5, rata-rata nilai transaksi harian bulan itu >= $1 juta, >= 15 hari bertransaksi.
- Peristiwa bulan m (dilapor s/d akhir bulan m, sudah publik) -> beli tutup hari bursa pertama m+1.
- Portofolio "kalender": bulan t berisi semua saham dengan peristiwa di bulan t-H .. t-1, bobot sama.
  Return bulan t = hari bursa pertama t -> hari bursa pertama t+1. Pembanding: semua saham layak (bobot sama).
UJI UTAMA (4; ambang |t| > 3):
  U1 H=1 selisih kotor | U2 H=3 selisih kotor | U3 H=6 selisih kotor | U4 H=3 selisih BERSIH (biaya 0,4% x porsi diganti).
DIAGNOSIS: per paruh waktu, versi cek kode KETAT, porsi saham "hilang" (tanpa harga = delisting? survivorship!),
  dan portofolio JUAL orang dalam (kode S, bukan 10b5-1) sebagai pembanding arah.
PERINGATAN DATA: harga AS dari Yahoo umumnya TIDAK memuat saham yang sudah delisting -> saham yang bangkrut setelah
  dibeli orang dalam bisa hilang -> hasil bisa terlalu bagus. Porsi "hilang" dilaporkan.
Data latih: bulan pegang s/d 2018-11 (jual hari bursa pertama Des 2018). Data uji 2019+ DIKUNCI (--buka-uji).
Uji kode: --tes-tiruan (saham ber-peristiwa +1,5%/bln selama 3 bulan) & --tes-kosong.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BATAS_LATIH = pd.Period("2018-11", "M")      # bulan pegang terakhir (dijual hari bursa pertama Des 2018)
BUKA_DATA_UJI = "--buka-uji" in sys.argv
TES_TIRUAN = "--tes-tiruan" in sys.argv
TES_KOSONG = "--tes-kosong" in sys.argv
BIAYA = 0.004
MIN_HARGA, MIN_DOLAR, MIN_HARI = 5.0, 1e6, 15
SEMENTARA = Path("data/sementara/riset11")
FAKTOR_SPLIT = [1, 1.5, 2, 3, 4, 5, 10, 20]


def nilai_t(s):
    s = pd.Series(s).dropna()
    return s.mean() / (s.std(ddof=1) / np.sqrt(len(s))) if len(s) > 2 else np.nan


# ===== 1. Siapkan data (DuckDB, hemat memori) =====
def siapkan_data():
    import duckdb
    SEMENTARA.mkdir(parents=True, exist_ok=True)
    f_bln, f_ev = SEMENTARA / "bulanan.parquet", SEMENTARA / "peristiwa.parquet"
    if f_bln.exists() and f_ev.exists() and "--ulang" not in sys.argv:
        return pd.read_parquet(f_bln), pd.read_parquet(f_ev)
    db = duckdb.connect()
    db.execute("""CREATE TEMP VIEW harga AS
                  SELECT CAST(tanggal AS DATE) AS tanggal, kode, "Close" AS tutup, "Adj Close" AS adj, "Volume" AS vol
                  FROM read_parquet('data/bersih/saham_as.parquet')
                  WHERE tanggal >= TIMESTAMP '2005-06-01' AND "Adj Close" > 0 AND "Close" > 0""")
    bln = db.execute("""SELECT kode, date_trunc('month', tanggal) AS bulan,
                               arg_min(adj, tanggal) AS harga_awal, arg_max(tutup, tanggal) AS tutup_akhir,
                               avg(tutup * vol) AS dolar_vol, count(*) FILTER (WHERE vol > 0) AS hari_aktif
                        FROM harga GROUP BY 1, 2""").df()
    filter_ev = """jenis_form IN ('4', '4/A') AND lembar > 0 AND harga > 0 AND kode <> ''
                   AND rencana_10b5_1 <> '1' AND (hubungan ILIKE '%Director%' OR hubungan ILIKE '%Officer%')"""
    ev = db.execute(f"""
        WITH e AS (SELECT kode, kode_transaksi, CAST(tanggal_lapor AS DATE) AS tgl_lapor,
                          CAST(tanggal_transaksi AS DATE) AS tgl_trx, harga AS harga_trx, lembar
                   FROM read_parquet('data/raw/insider_sec/*.parquet')
                   WHERE kode_transaksi IN ('P', 'S') AND {filter_ev} AND tanggal_lapor IS NOT NULL
                         AND tanggal_transaksi IS NOT NULL)
        SELECT e.*, h.tutup AS tutup_yahoo
        FROM e ASOF LEFT JOIN harga h ON e.kode = h.kode AND e.tgl_trx >= h.tanggal""").df()
    bln["bulan"] = pd.to_datetime(bln["bulan"]).dt.to_period("M")
    ev["bulan"] = pd.to_datetime(ev["tgl_lapor"]).dt.to_period("M")
    rasio = ev["harga_trx"] / ev["tutup_yahoo"]
    log_jarak = pd.concat([np.log(rasio / f).abs() for f in FAKTOR_SPLIT + [1 / f for f in FAKTOR_SPLIT[1:]]],
                          axis=1).min(axis=1)
    ev["cocok"] = log_jarak < np.log(1.15)
    ev["cocok_ketat"] = np.log(rasio).abs() < np.log(1.15)
    ev["ada_harga"] = ev["tutup_yahoo"].notna()
    bln.to_parquet(f_bln, index=False)
    ev.to_parquet(f_ev, index=False)
    return bln, ev


def buat_data_tiruan(dengan_pola):
    """1.500 saham palsu bulanan 2005-06..2026-10. ~2% saham-bulan punya peristiwa beli. Pola (kalau ada):
    saham ber-peristiwa di bulan m mendapat +1,5% di bulan m+1, m+2, m+3."""
    acak = np.random.default_rng(11)
    bulan = pd.period_range("2005-06", "2026-10", freq="M")
    kode = [f"K{i:04d}" for i in range(1500)]
    pasar = acak.normal(0.008, 0.045, len(bulan))
    ret = pd.DataFrame(acak.normal(0, 0.10, (len(bulan), 1500)), index=bulan, columns=kode).add(pasar, axis=0)
    peristiwa = pd.DataFrame(acak.random((len(bulan), 1500)) < 0.02, index=bulan, columns=kode)
    if dengan_pola:
        dorong = sum(peristiwa.shift(h, fill_value=False).astype(float) for h in (1, 2, 3)) * 0.015
        ret = ret + dorong
    # harga_awal bulan t = harga di hari bursa PERTAMA bulan t -> belum memuat return bulan t (shift 1).
    # (Versi pertama lupa shift: pola tertanam satu bulan terlalu awal; program riset benar tidak menangkapnya.)
    harga = 20 * np.exp(np.log1p(ret.clip(lower=-0.9)).cumsum().shift(1).fillna(0))
    bln = harga.stack().rename("harga_awal").reset_index()
    bln.columns = ["bulan", "kode", "harga_awal"]
    bln["tutup_akhir"], bln["dolar_vol"], bln["hari_aktif"] = 20.0, 5e6, 21
    s = peristiwa.stack()
    ev = s[s].reset_index().iloc[:, :2]
    ev.columns = ["bulan", "kode"]
    ev["kode_transaksi"], ev["cocok"], ev["cocok_ketat"], ev["ada_harga"] = "P", True, True, True
    return bln, ev


if TES_TIRUAN or TES_KOSONG:
    bln, ev = buat_data_tiruan(TES_TIRUAN)
    print(f"🧪 MODE TES: data PALSU {'dengan pola (+1,5%/bln x 3 bulan)' if TES_TIRUAN else 'tanpa pola'}")
else:
    bln, ev = siapkan_data()
    beli = ev[ev["kode_transaksi"] == "P"]
    print(f"📥 Harga bulanan: {bln['kode'].nunique():,} kode, {bln['bulan'].min()} s/d {bln['bulan'].max()}")
    print(f"📥 Transaksi beli (P) direktur/eksekutif: {len(beli):,} | ada harga Yahoo: {beli['ada_harga'].mean():.0%} | "
          f"kode cocok: {beli['cocok'].mean():.0%} | cocok ketat: {beli['cocok_ketat'].mean():.0%}")

# ===== 2. Tabel lebar bulanan =====
kal = pd.period_range(bln["bulan"].min(), bln["bulan"].max(), freq="M")
lebar = {k: bln.pivot_table(index="bulan", columns="kode", values=k, aggfunc="last").reindex(kal)
         for k in ["harga_awal", "tutup_akhir", "dolar_vol", "hari_aktif"]}
ret = lebar["harga_awal"].shift(-1) / lebar["harga_awal"] - 1          # bulan t: awal t -> awal t+1
layak = ((lebar["tutup_akhir"] >= MIN_HARGA) & (lebar["dolar_vol"] >= MIN_DOLAR)
         & (lebar["hari_aktif"] >= MIN_HARI))


def set_peristiwa(kode_trx, kolom_cocok):
    e = ev[(ev["kode_transaksi"] == kode_trx) & ev[kolom_cocok]]
    return {m: set(g["kode"]) for m, g in e.groupby("bulan")}


def portofolio(H, peristiwa):
    """Portofolio kalender: bulan t = saham dengan peristiwa di t-H..t-1 yang layak saat peristiwa."""
    baris, lalu = [], set()
    for t in kal:
        if BUKA_DATA_UJI:
            if t <= BATAS_LATIH + 1 or t + 1 not in kal:
                continue
        elif t > BATAS_LATIH:
            continue
        isi = set()
        for h in range(1, H + 1):
            m = t - h
            if m in peristiwa and m in layak.index:
                lay = layak.loc[m]
                isi |= {k for k in peristiwa[m] if k in lay.index and lay[k]}
        if t - 1 not in layak.index:
            continue
        sem = layak.loc[t - 1]
        r_sem = ret.loc[t, sem[sem].index].dropna()
        if len(isi) < 5 or len(r_sem) < 100:
            continue
        r_isi = ret.loc[t, list(isi & set(ret.columns))]
        hilang = r_isi.isna().mean() if len(r_isi) else 1.0
        r_isi = r_isi.dropna()
        if len(r_isi) < 5:
            continue
        ganti = 1 - len(isi & lalu) / len(isi) if lalu else 1.0
        baris.append({"bulan": t, "n": len(r_isi), "port": r_isi.mean(), "semesta": r_sem.mean(),
                      "kotor": r_isi.mean() - r_sem.mean(), "ganti": ganti, "hilang": hilang})
        lalu = isi
    d = pd.DataFrame(baris).set_index("bulan")
    d["bersih"] = d["kotor"] - d["ganti"] * BIAYA
    return d


beli = set_peristiwa("P", "cocok")
print(f"🔒 Data uji {'DIBUKA' if BUKA_DATA_UJI else 'DIKUNCI, tidak disentuh'}. "
      f"Menganalisis {'DATA UJI (2019+)' if BUKA_DATA_UJI else 'DATA LATIH (bulan pegang s/d 2018-11)'}.\n")

hasil = {H: portofolio(H, beli) for H in (1, 3, 6)}
d3 = hasil[3]
print(f"Bulan: {len(d3)} ({d3.index[0]} s/d {d3.index[-1]}); saham di portofolio H=3: median {d3['n'].median():.0f}, "
      f"min {d3['n'].min()}; porsi saham HILANG (tanpa harga bulan itu): {d3['hilang'].mean():.1%}")
print("\n1️⃣  UJI UTAMA: portofolio pembelian orang dalam - semua saham layak (bobot sama, per bulan)")
print(f"   {'uji':22}{'rata-rata':>11}{'t':>7}{'per tahun':>11}{'% bln menang':>14}{'ganti/bln':>11}")
for nama, H, kol in [("U1 H=1 kotor", 1, "kotor"), ("U2 H=3 kotor", 3, "kotor"), ("U3 H=6 kotor", 6, "kotor"),
                     ("U4 H=3 BERSIH", 3, "bersih")]:
    s = hasil[H][kol]
    print(f"   {nama:22}{s.mean():>+11.2%}{nilai_t(s):>+7.1f}{(1 + s.mean()) ** 12 - 1:>+11.1%}"
          f"{(s > 0).mean():>14.0%}{hasil[H]['ganti'].iloc[1:].mean():>11.0%}")

print("\n2️⃣  DIAGNOSIS")
tengah = d3.index[len(d3) // 2]
a, b = d3["kotor"].loc[:tengah], d3["kotor"].loc[tengah:].iloc[1:]
print(f"   Stabilitas H=3 kotor: {a.index[0]}-{a.index[-1]} {a.mean():+.2%} (t {nilai_t(a):+.1f}) | "
      f"{b.index[0]}-{b.index[-1]} {b.mean():+.2%} (t {nilai_t(b):+.1f})")
if not (TES_TIRUAN or TES_KOSONG):
    k = portofolio(3, set_peristiwa("P", "cocok_ketat"))
    print(f"   Cek kode KETAT (rasio harga ~1 saja), H=3 kotor: {k['kotor'].mean():+.2%} (t {nilai_t(k['kotor']):+.1f}), "
          f"median {k['n'].median():.0f} saham")
    j = portofolio(3, set_peristiwa("S", "cocok"))
    print(f"   Pembanding arah: portofolio JUAL orang dalam (S, bukan 10b5-1), H=3 kotor: {j['kotor'].mean():+.2%} "
          f"(t {nilai_t(j['kotor']):+.1f})")
    print(f"   Survivorship: rata-rata {d3['hilang'].mean():.1%} saham portofolio tanpa harga di bulan pegang "
          f"(kemungkinan delisting; dibuang = hasil bisa terlalu bagus)")
