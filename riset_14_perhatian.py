"""
RISET #14: LONJAKAN PERHATIAN PUBLIK (pembaca Wikipedia) -> RETURN SAHAM IDX
===========================================================================

DUGAAN (ditulis 2026-11-20, SEBELUM melihat hubungan perhatian-return apa pun)
-----------------------------------------------------------------------------
Literatur (Da-Engelberg-Gao 2011 dengan pencarian Google; Barber-Odean 2008): investor ritel membeli saham yang
sedang "ramai". Dua akibat:
  H1 jangka pendek: lonjakan perhatian minggu w -> return LEBIH TINGGI minggu w+1 (tekanan beli) -> positif.
  H2 jangka lebih panjang: lonjakan perhatian bulan m -> return LEBIH RENDAH bulan m+1..m+3 (harga balik) -> negatif.
Perkiraan jujur: data latih hanya 2015-09..2018 (~3,3 tahun) & hanya ~180 perusahaan yang punya artikel (umumnya
saham besar yang sudah banyak diperhatikan) -> daya uji rendah. Saya kira t < 2. Semua uji DUA ARAH, |t| > 3.

UKURAN PERHATIAN (pembaca id + en dijumlah per kode):
  mingguan: lonjakan = log(1 + pembaca minggu w) - log(1 + median pembaca mingguan 8 minggu sebelumnya)
  bulanan : lonjakan = log(1 + pembaca bulan m) - log(1 + median pembaca bulanan 6 bulan sebelumnya)
WAKTU: pembaca hari d (UTC) baru lengkap keesokan harinya. Minggu = Sabtu-Jumat; beli tutup hari bursa PERTAMA minggu
  w+1 (Senin), jual tutup hari bursa pertama minggu w+2. Bulanan: beli tutup hari bursa pertama bulan m+1, tahan 3 bulan.
SEMESTA: saham dengan artikel Wikipedia & lolos saringan riset #2 (harga >= Rp100, median nilai transaksi 60 hari
  >= Rp1 miliar, >= 80% hari aktif, tanpa lompatan > 50%), diukur di akhir minggu/bulan sinyal.
UJI (3):
  U1 (H1) IC mingguan lonjakan minggu w vs return minggu w+1 (antar saham, rata-rata per minggu).
  U2 (H1) beli-saja 20% lonjakan TERTINGGI, return minggu w+1 dikurangi semesta, BERSIH biaya 0,4% x porsi diganti.
  U3 (H2) IC bulanan lonjakan bulan m vs return bulan m+1..m+3 (3 bulan; tumpang tindih -> t dari bulan non-tumpang
     tindih: setiap 3 bulan sekali).
Data uji 2019+ DIKUNCI (--buka-uji). Uji kode: --tes-tiruan (pola H1 positif) & --tes-kosong.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BATAS_LATIH = pd.Timestamp("2018-12-31")
BUKA_DATA_UJI = "--buka-uji" in sys.argv
TES_TIRUAN = "--tes-tiruan" in sys.argv
TES_KOSONG = "--tes-kosong" in sys.argv
BIAYA = 0.004
MIN_HARGA, MIN_NILAI, MIN_HARI_AKTIF, MAX_LOMPAT, MIN_SAHAM = 100, 1e9, 0.8, 0.5, 20


def jadi_tanggal(x):
    t = pd.DatetimeIndex(pd.to_datetime(x))
    if t.tz is not None:
        t = t.tz_localize(None)
    return t.normalize().astype("datetime64[ns]")


def nilai_t(s):
    s = pd.Series(s).dropna()
    return s.mean() / (s.std(ddof=1) / np.sqrt(len(s))) if len(s) > 2 else np.nan


def muat_data_asli():
    adj, tutup, volume = {}, {}, {}
    for f in sorted(Path("data/raw/harga_idx").glob("*.parquet")):
        d = pd.read_parquet(f, columns=["Adj Close", "Close", "Volume"])
        d.index = jadi_tanggal(d.index)
        d = d[~d.index.duplicated(keep="last")]
        adj[f.stem], tutup[f.stem], volume[f.stem] = d["Adj Close"], d["Close"], d["Volume"]
    adj, tutup, volume = (pd.DataFrame(x).sort_index() for x in (adj, tutup, volume))
    aktif = volume.fillna(0) > 0
    hari = aktif.index[(aktif.sum(axis=1) >= 10) & (aktif.index.day_of_week < 5)]
    w = pd.read_parquet("data/raw/histori/wikipedia_idx/semua.parquet")
    w["tanggal"] = jadi_tanggal(w["tanggal"])
    pembaca = w.groupby(["tanggal", "kode"])["pembaca"].sum().unstack()
    return adj.loc[hari], tutup.loc[hari], volume.loc[hari], pembaca


def buat_data_tiruan(dengan_pola):
    """150 saham palsu + pembaca harian palsu (tingkat dasar berbeda, lonjakan acak). Pola (kalau ada): saham yang
    pembacanya melonjak minggu w mendapat return lebih tinggi minggu w+1 (0,02 x lonjakan, dibagi 5 hari)."""
    acak = np.random.default_rng(14)
    hari = pd.bdate_range("2015-01-01", "2026-11-13").astype("datetime64[ns]")
    kalender = pd.date_range("2015-01-01", "2026-11-13").astype("datetime64[ns]")
    kolom = [f"S{i:03d}" for i in range(150)]
    dasar = np.exp(acak.normal(5, 1, 150))
    lonjak = np.exp(np.cumsum(acak.normal(0, 0.15, (len(kalender), 150)), axis=0) * 0.0 + acak.normal(0, 0.4, (len(kalender), 150)))
    pembaca = pd.DataFrame(np.round(dasar * lonjak), index=kalender, columns=kolom)
    harian = pd.DataFrame(acak.normal(0, 0.02, (len(hari), 150)), index=hari, columns=kolom)
    if dengan_pola:
        mg = pembaca.groupby(kalender.to_period("W-FRI")).sum()
        lj = np.log1p(mg) - np.log1p(mg.shift(1).rolling(8, min_periods=8).median())
        dorong = lj.shift(1).reindex(hari.to_period("W-FRI")).fillna(0).values * 0.02 / 5
        harian = harian + dorong
    adj = 1000 * np.exp(harian.cumsum())
    volume = pd.DataFrame(1e7, index=hari, columns=kolom)
    return adj, adj.copy(), volume, pembaca


if TES_TIRUAN or TES_KOSONG:
    adj, tutup, volume, pembaca = buat_data_tiruan(TES_TIRUAN)
    print(f"🧪 MODE TES: data PALSU {'dengan pola H1 positif' if TES_TIRUAN else 'tanpa pola'}")
else:
    adj, tutup, volume, pembaca = muat_data_asli()
hari = adj.index
pembaca = pembaca.reindex(columns=[k for k in pembaca.columns if k in adj.columns])
print(f"📥 {adj.shape[1]} saham, {pembaca.shape[1]} punya data pembaca Wikipedia "
      f"({pembaca.index.min().date()} s/d {pembaca.index.max().date()})")

aktif = volume.fillna(0) > 0
median_nilai = (tutup * volume).where(aktif).rolling(60, min_periods=40).median()
porsi_aktif = aktif.rolling(250, min_periods=250).mean()
lompat = adj.pct_change(fill_method=None).abs().rolling(250, min_periods=200).max()
lolos_h = ((tutup >= MIN_HARGA) & (median_nilai >= MIN_NILAI) & (porsi_aktif >= MIN_HARI_AKTIF) & (lompat < MAX_LOMPAT))


def pilih_periode(awal_beli, jual):
    return ((awal_beli > BATAS_LATIH) & jual.notna()) if BUKA_DATA_UJI else (jual <= BATAS_LATIH)


# ===== MINGGUAN (H1) =====
P = "W-FRI"
kal = pd.period_range(hari.min().to_period(P), hari.max().to_period(P), freq=P)
gm = pd.Series(hari, index=hari).groupby(hari.to_period(P))
awal, akhir = gm.min().reindex(kal), gm.max().reindex(kal)
harga_awal = adj.reindex(awal.values).set_axis(kal)
ret_depan = harga_awal.shift(-2) / harga_awal.shift(-1) - 1
jual = awal.shift(-2)
mg = pembaca.groupby(pembaca.index.to_period(P)).sum(min_count=1).reindex(kal)
lonjakan = np.log1p(mg) - np.log1p(mg.shift(1).rolling(8, min_periods=8).median())
lolos_m = lolos_h.reindex(akhir.values).set_axis(kal).reindex(columns=lonjakan.columns).fillna(False)
pilih = pilih_periode(awal.shift(-1), jual)
print(f"🔒 Data uji {'DIBUKA' if BUKA_DATA_UJI else 'DIKUNCI, tidak disentuh'}. "
      f"Menganalisis {'DATA UJI (2019+)' if BUKA_DATA_UJI else 'DATA LATIH (posisi ditutup s/d 2018-12-31)'}.\n")
baris, lalu = [], set()
for w in kal[pilih.fillna(False).values]:
    s = lonjakan.loc[w]
    r = ret_depan.loc[w].reindex(s.index)
    ok = lolos_m.loc[w] & s.notna() & r.notna()
    if ok.sum() < MIN_SAHAM:
        continue
    s, r = s[ok], r[ok]
    atas = set(s.index[pd.qcut(s.rank(method="first"), 5, labels=False) == 4])
    ganti = 1 - len(atas & lalu) / len(atas) if lalu else 1.0
    baris.append({"minggu": w, "n": int(ok.sum()), "ic": s.rank().corr(r.rank()),
                  "bersih": r[list(atas)].mean() - ganti * BIAYA - r.mean(), "kotor": r[list(atas)].mean() - r.mean(),
                  "ganti": ganti})
    lalu = atas
d = pd.DataFrame(baris).set_index("minggu")
print(f"Mingguan: {len(d)} minggu ({d.index[0].end_time.date()} s/d {d.index[-1].end_time.date()}), "
      f"semesta median {d['n'].median():.0f} saham")
print(f"   U1 (H1) IC mingguan        : {d['ic'].mean():+.3f}  t = {nilai_t(d['ic']):+.1f}")
print(f"   U2 (H1) beli 20% lonjakan   : kotor {d['kotor'].mean():+.3%}/mg, BERSIH {d['bersih'].mean():+.3%}/mg  "
      f"t = {nilai_t(d['bersih']):+.1f}  (ganti {d['ganti'].iloc[1:].mean():.0%}/mg)")

# ===== BULANAN (H2) =====
P = "M"
kalb = pd.period_range(hari.min().to_period(P), hari.max().to_period(P), freq=P)
gb = pd.Series(hari, index=hari).groupby(hari.to_period(P))
awal_b, akhir_b = gb.min().reindex(kalb), gb.max().reindex(kalb)
harga_awal_b = adj.reindex(awal_b.values).set_axis(kalb)
ret_3bln = harga_awal_b.shift(-4) / harga_awal_b.shift(-1) - 1            # beli awal m+1, jual awal m+4
jual_b = awal_b.shift(-4)
bl = pembaca.groupby(pembaca.index.to_period(P)).sum(min_count=1).reindex(kalb)
lonjakan_b = np.log1p(bl) - np.log1p(bl.shift(1).rolling(6, min_periods=6).median())
lolos_b = lolos_h.reindex(akhir_b.values).set_axis(kalb).reindex(columns=lonjakan_b.columns).fillna(False)
pilih_b = pilih_periode(awal_b.shift(-1), jual_b)
ic_b = {}
for m in kalb[pilih_b.fillna(False).values]:
    s = lonjakan_b.loc[m]
    r = ret_3bln.loc[m].reindex(s.index)
    ok = lolos_b.loc[m] & s.notna() & r.notna()
    if ok.sum() < MIN_SAHAM:
        continue
    ic_b[m] = s[ok].rank().corr(r[ok].rank())
ic_b = pd.Series(ic_b)
tak_tumpang = ic_b.iloc[::3]
print(f"\nBulanan: {len(ic_b)} bulan ({ic_b.index[0]} s/d {ic_b.index[-1]})")
print(f"   U3 (H2) IC bulan m -> 3 bulan: {ic_b.mean():+.3f}  t (tiap 3 bulan, tanpa tumpang tindih) = "
      f"{nilai_t(tak_tumpang):+.1f}  ({len(tak_tumpang)} titik)")
tengah = d.index[len(d) // 2]
print(f"\nStabilitas U1: paruh 1 t {nilai_t(d['ic'].loc[:tengah]):+.1f} | paruh 2 t {nilai_t(d['ic'].loc[tengah:].iloc[1:]):+.1f}")
