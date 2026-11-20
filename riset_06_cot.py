"""
RISET #6: POSISI SPEKULAN DI FUTURES (CFTC COT) -> ETF KOMODITAS/MATA UANG/OBLIGASI BULAN DEPAN
==============================================================================================

DUA TEORI YANG BERTENTANGAN (ditulis 2026-11-20, SEBELUM melihat hubungan apa pun):
  (a) "Tekanan lindung nilai" (Keynes; De Roon-Nijman-Veld 2000; Basu-Miffre 2013): produsen/hedger membayar premi
      ke spekulan supaya mau menanggung risiko. Kalau spekulan sangat NET LONG (hedger net short), harga cenderung
      NAIK -> hubungan POSITIF.
  (b) "Kerumunan / contrarian" (populer di trader): posisi ekstrem = semua sudah masuk, tidak ada pembeli tersisa ->
      harga BERBALIK -> hubungan NEGATIF.
  Karena itu semua uji DUA ARAH (|t| > 3). Perkiraan jujur: literatur akademik lebih mendukung (a) tapi efeknya kecil
  dan melemah setelah 2004 (masuknya dana indeks komoditas). Saya kira t < 2.

INSTRUMEN (bisa dibeli: ETF di bursa AS) <-> kontrak CFTC (KODE kontrak, bukan nama; nama berganti mis. Feb 2022):
  GLD emas 088691 | SLV perak 084691 | PPLT platinum 076651 | PALL paladium 075651 | CPER tembaga 085692 |
  USO minyak WTI 067651 | UNG gas alam 023651 | UGA bensin 111659 | CORN jagung 002602 | WEAT gandum 001602 |
  SOYB kedelai 005602 | CANE gula 080732 | FXE euro 099741 | FXY yen 097741 | FXB pound 096742 | FXA dolar Aus 232741 |
  FXC dolar Kanada 090741 | FXF franc 092741 | TLT obligasi 30th 020601 | IEF obligasi 10th 043602 | SPY S&P 13874A
  (ETF kopi/kakao/kapas/ternak sudah ditutup -> tidak ada di data = survivorship, tidak ikut.)

SINYAL: posisi bersih spekulan = (noncommercial long - short) / open interest (laporan "legacy").
  Indeks COT = peringkat persentil posisi itu dalam 156 minggu (3 tahun) terakhir, hanya data sampai laporan itu.
WAKTU: posisi per Selasa diumumkan Jumat 15:30 ET. Sinyal akhir bulan memakai laporan TERAKHIR dengan tanggal posisi
  <= akhir bulan - 4 hari (pasti sudah terbit). Beli tutup hari bursa pertama bulan berikutnya, jual hari bursa
  pertama bulan sesudahnya (sama dengan riset lain).
UJI (4; dua arah; |t| > 3):
  U1 IC: korelasi peringkat indeks COT vs return ETF bulan depan, antar instrumen, dirata-rata per bulan.
  U2 sepertiga TERATAS - sepertiga TERBAWAH (bobot sama), per bulan.
  U3 beli-saja sepertiga teratas - semua instrumen, BERSIH biaya 0,2% x porsi diganti (ETF besar, spread kecil).
  U4 ekstrem (deret waktu, gaya contrarian): return 4 minggu ETF setelah indeks COT >= 0,9 dikurangi setelah <= 0,1
     (laporan mingguan, masuk tutup Senin setelah terbit), dikumpulkan semua instrumen.
Data uji 2019+ DIKUNCI (--buka-uji). Uji kode: --tes-tiruan (pola positif) & --tes-kosong.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BATAS_LATIH = pd.Timestamp("2018-12-31")
BUKA_DATA_UJI = "--buka-uji" in sys.argv
TES_TIRUAN = "--tes-tiruan" in sys.argv
TES_KOSONG = "--tes-kosong" in sys.argv
BIAYA = 0.002
PETA = {"GLD": "088691", "SLV": "084691", "PPLT": "076651", "PALL": "075651", "CPER": "085692", "USO": "067651",
        "UNG": "023651", "UGA": "111659", "CORN": "002602", "WEAT": "001602", "SOYB": "005602", "CANE": "080732",
        "FXE": "099741", "FXY": "097741", "FXB": "096742", "FXA": "232741", "FXC": "090741", "FXF": "092741",
        "TLT": "020601", "IEF": "043602", "SPY": "13874A"}


def nilai_t(s):
    s = pd.Series(s).dropna()
    return s.mean() / (s.std(ddof=1) / np.sqrt(len(s))) if len(s) > 2 else np.nan


def indeks_cot(posisi):
    """Persentil posisi minggu ini dalam 156 minggu terakhir (termasuk minggu ini), min 104 minggu."""
    return posisi.rolling(156, min_periods=104).apply(lambda x: (x[:-1] < x[-1]).mean() + 0.5 * (x[:-1] == x[-1]).mean(),
                                                      raw=True)


# ===== 1. Data =====
def muat_data_asli():
    import duckdb
    c = pd.read_parquet("data/raw/histori/cot/cot_legacy.parquet",
                        columns=["cftc_contract_market_code", "report_date_as_yyyy_mm_dd", "open_interest_all",
                                 "noncomm_positions_long_all", "noncomm_positions_short_all"])
    harian = sorted(Path("data/raw/harian/cot_legacy").glob("*.parquet"))
    if harian:                                     # tambahan laporan terbaru (tumpang tindih, dobel dibuang)
        h = pd.read_parquet(harian[-1])
        c = pd.concat([c, h[[k for k in c.columns if k in h.columns]]], ignore_index=True)
    c = c[c["cftc_contract_market_code"].isin(PETA.values())].copy()
    c["tgl"] = pd.to_datetime(c["report_date_as_yyyy_mm_dd"]).dt.normalize().astype("datetime64[ns]")
    for k in ["open_interest_all", "noncomm_positions_long_all", "noncomm_positions_short_all"]:
        c[k] = pd.to_numeric(c[k], errors="coerce")
    c = c.drop_duplicates(["cftc_contract_market_code", "tgl"], keep="last")
    c["posisi"] = (c["noncomm_positions_long_all"] - c["noncomm_positions_short_all"]) / c["open_interest_all"]
    kode_ke_etf = {v: k for k, v in PETA.items()}
    posisi = c.pivot(index="tgl", columns="cftc_contract_market_code", values="posisi").rename(columns=kode_ke_etf)
    db = duckdb.connect()
    p = db.execute(f"""SELECT CAST(tanggal AS DATE) AS tanggal, kode, "Adj Close" AS adj
                       FROM read_parquet('data/bersih/saham_as.parquet')
                       WHERE kode IN ({','.join(repr(e) for e in PETA)})""").df()
    p["tanggal"] = pd.to_datetime(p["tanggal"]).astype("datetime64[ns]")
    harga = p.pivot(index="tanggal", columns="kode", values="adj").sort_index()
    return posisi.sort_index(), harga


def buat_data_tiruan(dengan_pola):
    """21 'ETF' palsu harian & posisi spekulan mingguan palsu (berjalan acak, mean-reverting).
    Pola (kalau ada): return harian ETF mendapat dorongan 0,004 x (indeks COT minggu terakhir yang sudah terbit - 0,5)."""
    acak = np.random.default_rng(6)
    hari = pd.bdate_range("2003-01-01", "2026-11-13").astype("datetime64[ns]")
    selasa = pd.date_range("2003-01-07", "2026-11-10", freq="W-TUE").astype("datetime64[ns]")
    pos = pd.DataFrame(index=selasa, columns=list(PETA), dtype=float)
    x = np.zeros(len(PETA))
    for i in range(len(selasa)):
        x = 0.97 * x + acak.normal(0, 0.05, len(PETA))
        pos.iloc[i] = x
    harian = pd.DataFrame(acak.normal(0.0002, 0.012, (len(hari), len(PETA))), index=hari, columns=list(PETA))
    if dengan_pola:
        idx = pos.apply(indeks_cot)
        terbit = idx.copy()
        terbit.index = terbit.index + pd.Timedelta(days=6)          # baru bisa dipakai Senin setelah terbit
        dorong = terbit.reindex(hari, method="ffill").fillna(0.5) - 0.5
        harian = harian + 0.004 * dorong.values
    harga = 100 * np.exp(harian.cumsum())
    return pos, harga


if TES_TIRUAN or TES_KOSONG:
    posisi, harga = buat_data_tiruan(TES_TIRUAN)
    print(f"🧪 MODE TES: data PALSU {'dengan pola positif' if TES_TIRUAN else 'tanpa pola'}")
else:
    posisi, harga = muat_data_asli()
print(f"📥 COT {posisi.shape[1]} pasar, {posisi.index.min().date()} s/d {posisi.index.max().date()}; "
      f"ETF {harga.shape[1]}, {harga.index.min().date()} s/d {harga.index.max().date()}")
idx_cot = posisi.apply(indeks_cot)

# ===== 2. Bulanan =====
hari = harga.index[harga.notna().sum(axis=1) >= 1]
bulan = pd.Series(hari, index=hari).groupby(hari.to_period("M"))
akhir, awal = bulan.max(), bulan.min()
kal = akhir.index
harga_awal = harga.reindex(awal.values).set_axis(kal)
ret_depan = harga_awal.shift(-2) / harga_awal.shift(-1) - 1
jual = pd.Series(awal.values, index=kal).shift(-2)
# sinyal akhir bulan = laporan terakhir dengan tanggal posisi <= akhir bulan - 4 hari
sinyal = pd.DataFrame({m: idx_cot[idx_cot.index <= akhir[m] - pd.Timedelta(days=4)].iloc[-1]
                       if (idx_cot.index <= akhir[m] - pd.Timedelta(days=4)).any() else np.nan for m in kal}).T
pilih = ((jual > BATAS_LATIH) & (pd.Series(awal.values, index=kal) > BATAS_LATIH)) if BUKA_DATA_UJI else (jual <= BATAS_LATIH)
print(f"🔒 Data uji {'DIBUKA' if BUKA_DATA_UJI else 'DIKUNCI, tidak disentuh'}. "
      f"Menganalisis {'DATA UJI (2019+)' if BUKA_DATA_UJI else 'DATA LATIH (posisi ditutup s/d 2018-12-31)'}.\n")

baris, lalu = [], set()
for m in kal[pilih.fillna(False).values]:
    s, r = sinyal.loc[m], ret_depan.loc[m]
    ok = s.notna() & r.notna()
    if ok.sum() < 6:
        continue
    s, r = s[ok], r[ok]
    n3 = len(s) // 3
    urut = s.sort_values()
    atas, bawah = list(urut.index[-n3:]), list(urut.index[:n3])
    ganti = 1 - len(set(atas) & lalu) / len(atas) if lalu else 1.0
    baris.append({"bulan": m, "n": int(ok.sum()), "ic": s.rank().corr(r.rank()),
                  "atas_bawah": r[atas].mean() - r[bawah].mean(),
                  "bersih": r[atas].mean() - ganti * BIAYA - r.mean(), "ganti": ganti})
    lalu = set(atas)
d = pd.DataFrame(baris).set_index("bulan")
print(f"Bulanan: {len(d)} bulan ({d.index[0]} s/d {d.index[-1]}), instrumen per bulan median {d['n'].median():.0f} "
      f"(min {d['n'].min()}, maks {d['n'].max()})")
print("\n1️⃣  UJI BULANAN (dua arah; positif = teori tekanan lindung nilai, negatif = contrarian)")
for uji, kol, ket in [("U1", "ic", "IC rata-rata"), ("U2", "atas_bawah", "sepertiga atas - bawah"),
                      ("U3", "bersih", "beli sepertiga atas, bersih vs semua")]:
    v = d[kol]
    satuan = f"{v.mean():+.3f}" if kol == "ic" else f"{v.mean():+.2%}/bln"
    print(f"   {uji} {ket:40} {satuan:>12}  t = {nilai_t(v):+.1f}")
print(f"   (ganti isi sepertiga atas rata-rata {d['ganti'].iloc[1:].mean():.0%}/bln)")

# ===== 3. U4 ekstrem mingguan =====
hasil = []
for etf in PETA:
    if etf not in idx_cot or etf not in harga:
        continue
    ic = idx_cot[etf].dropna()
    h = harga[etf].dropna()
    for tgl, nilai in ic.items():
        if 0.1 < nilai < 0.9:
            continue
        masuk_kand = h.index[h.index >= tgl + pd.Timedelta(days=6)]       # Senin setelah terbit (Jumat)
        if len(masuk_kand) == 0:
            continue
        masuk = masuk_kand[0]
        keluar_kand = h.index[h.index >= masuk + pd.Timedelta(days=28)]
        if len(keluar_kand) == 0:
            continue
        keluar = keluar_kand[0]
        if (keluar > BATAS_LATIH) != BUKA_DATA_UJI and not (BUKA_DATA_UJI and masuk > BATAS_LATIH):
            continue
        if BUKA_DATA_UJI and masuk <= BATAS_LATIH:
            continue
        hasil.append({"etf": etf, "tgl": tgl, "ekstrem": "tinggi" if nilai >= 0.9 else "rendah",
                      "ret": h[keluar] / h[masuk] - 1})
e = pd.DataFrame(hasil)
tinggi, rendah = e[e.ekstrem == "tinggi"]["ret"], e[e.ekstrem == "rendah"]["ret"]
# t konservatif: rata-rata per BULAN kalender (laporan mingguan saling tumpang tindih 4 minggu)
e["bln"] = pd.to_datetime(e["tgl"]).dt.to_period("M")
per_bln = e.groupby(["bln", "ekstrem"])["ret"].mean().unstack()
sel = (per_bln["tinggi"] - per_bln["rendah"]).dropna()
print(f"\n2️⃣  U4 EKSTREM (4 minggu setelah terbit): setelah indeks >= 0,9: {tinggi.mean():+.2%} ({len(tinggi)} kali) | "
      f"<= 0,1: {rendah.mean():+.2%} ({len(rendah)} kali)")
print(f"   selisih tinggi - rendah per bulan: {sel.mean():+.2%}  t = {nilai_t(sel):+.1f}  ({len(sel)} bulan dengan keduanya)")

# ===== 4. Stabilitas =====
tengah = d.index[len(d) // 2]
print(f"\n3️⃣  Stabilitas IC: paruh 1 t {nilai_t(d['ic'].loc[:tengah]):+.1f} | paruh 2 t "
      f"{nilai_t(d['ic'].loc[tengah:].iloc[1:]):+.1f} (batas {tengah})")
