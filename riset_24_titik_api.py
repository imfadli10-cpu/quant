"""
RISET #24: TITIK API KEBAKARAN (satelit NASA) -> SAHAM SAWIT IDX vs PASAR, data LATIH saja
========================================================================================

DUGAAN (ditulis 2026-11-20 SEBELUM data histori titik api diunduh/dilihat; di-commit sebelum dijalankan)
----------------------------------------------------------------------------------------------------
Dua teori yang arahnya BERLAWANAN (maka semua uji dua arah):
  (a) RISIKO: kebakaran besar di Sumatra/Kalimantan = sorotan pemerintah & internasional pada perusahaan perkebunan
      (izin dicabut, denda, boikot) + asap mengganggu operasi -> saham sawit TERTINGGAL pasar sesudahnya.
  (b) PASOKAN: kebakaran = kemarau panjang -> produksi sawit 6-12 bulan kemudian turun -> harga CPO naik -> saham sawit
      MENGUNGGULI pasar (riset #16: ONI -> sawit tidak terbukti, tapi titik api lebih langsung dari ONI).
Perkiraan jujur: informasi titik api tersedia publik (peta FIRMS), pasar mungkin sudah menyerapnya. t < 2.

DATA: MODIS_SP (1 km, konsisten 2000-11..2018), titik api di Sumatra (bujur 95-106, lintang -6..6) + Kalimantan
  (bujur 108-119, lintang -4,5..4,5), confidence >= 30. FIRMS NRT tersedia ~3 jam setelah satelit lewat -> data hari d
  diketahui sebelum IDX buka hari d+1.
  Keranjang SAWIT = AALI, LSIP, SGRO, SIMP, BWPT (riset #3/#16), bobot sama; PASAR = keranjang 30 saham paling likuid
  (riset #4/#15). Target = return SAWIT - PASAR.
  Anomali api minggu w = log(1 + jumlah titik minggu w) - rata-rata log(1 + jumlah) minggu-ke-sama (minggu ISO) di 5 tahun
  SEBELUMNYA (musim kemarau Agu-Okt selalu ramai; yang dihitung kelebihannya). Bulanan sama dengan bulan kalender.
UJI (3; dua arah; |t| > 3):
  U1 MINGGUAN: anomali minggu w -> SAWIT-PASAR minggu w+1 (beli tutup hari bursa pertama w+1), t robust White.
  U2 BULANAN: anomali bulan m -> SAWIT-PASAR bulan m+1, t robust White.
  U3 6 BULAN (teori b): anomali bulan m -> SAWIT-PASAR bulan m+1..m+6; jendela tumpang tindih -> t = TERKECIL antara
     Newey-West(6) dan regresi tanpa tumpang tindih (pelajaran riset #16).
Data uji 2019+ DIKUNCI. Uji kode: --tes-tiruan & --tes-kosong (anomali palsu, return palsu dengan/ tanpa pola).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BATAS_LATIH = pd.Timestamp("2018-12-31")
BUKA_DATA_UJI = "--buka-uji" in sys.argv
TES_TIRUAN, TES_KOSONG = "--tes-tiruan" in sys.argv, "--tes-kosong" in sys.argv
SAWIT = ["AALI", "LSIP", "SGRO", "SIMP", "BWPT"]
WILAYAH = {"Sumatra": (95, 106, -6, 6), "Kalimantan": (108, 119, -4.5, 4.5)}


def t_robust(y, x):
    d = pd.concat([y, x], axis=1).dropna()
    yy, xx = d.iloc[:, 0].values, d.iloc[:, 1].values
    xc = xx - xx.mean()
    b = (xc * (yy - yy.mean())).sum() / (xc ** 2).sum()
    e = yy - yy.mean() - b * xc
    return b, b / (np.sqrt((xc ** 2 * e ** 2).sum()) / (xc ** 2).sum()), len(d)


def t_nw(y, x, lag):
    d = pd.concat([y, x], axis=1).dropna()
    yy, xx = d.iloc[:, 0].values, d.iloc[:, 1].values
    xc = xx - xx.mean()
    b = (xc * (yy - yy.mean())).sum() / (xc ** 2).sum()
    u = xc * (yy - yy.mean() - b * xc)
    s = (u ** 2).sum() + sum(2 * (1 - L / (lag + 1)) * (u[L:] * u[:-L]).sum() for L in range(1, lag + 1))
    return b, b / (np.sqrt(s) / (xc ** 2).sum()), len(d)


def return_periode(r_harian, P):
    """Return periode p+1 per periode sinyal p: sesudah tutup hari bursa pertama p+1 s/d tutup hari bursa pertama p+2."""
    hari = r_harian.index
    per = hari.to_period(P)
    awal = pd.Series(hari, index=hari).groupby(per).min()
    hasil = {}
    for p in awal.index:
        if p + 1 not in awal.index or p + 2 not in awal.index:
            continue
        r = r_harian[(r_harian.index > awal[p + 1]) & (r_harian.index <= awal[p + 2])]
        if len(r):
            hasil[p] = np.prod(1 + r) - 1
    return pd.Series(hasil)


def anomali(jumlah, kunci_musim):
    """log(1+jumlah) dikurangi rata-rata periode musim yang sama di 5 tahun SEBELUMNYA (minimal 3 tahun)."""
    lg = np.log1p(jumlah)
    th = pd.Series([p.year for p in lg.index], index=lg.index)
    musim = pd.Series([kunci_musim(p) for p in lg.index], index=lg.index)
    acuan = pd.Series(np.nan, index=lg.index)
    for p in lg.index:
        lalu = lg[(musim == musim[p]) & (th < th[p]) & (th >= th[p] - 5)]
        if len(lalu) >= 3:
            acuan[p] = lalu.mean()
    return lg - acuan


def periode(s):
    akhir = pd.Series([p.end_time.normalize() for p in s.index], index=s.index)
    return s[(akhir > BATAS_LATIH).values] if BUKA_DATA_UJI else s


if TES_TIRUAN or TES_KOSONG:
    acak = np.random.default_rng(24)
    hari = pd.bdate_range("2001-01-01", "2026-11-13").astype("datetime64[ns]")
    musim = 50 * (1 + 3 * np.exp(-((hari.day_of_year - 260) / 30.0) ** 2))         # kemarau Agu-Okt ramai
    jumlah_harian = pd.Series(acak.poisson(musim * np.exp(np.repeat(acak.normal(0, 0.8, len(hari) // 5 + 1), 5)[:len(hari)])),
                              index=hari).astype(float)
    r_pasar = pd.Series(acak.normal(0.0005, 0.012, len(hari)), index=hari)
    r_sawit = r_pasar + pd.Series(acak.normal(0, 0.012, len(hari)), index=hari)
    if TES_TIRUAN:      # pola: anomali api minggu ini -> sawit tertinggal minggu depan (-0,5% per +1 anomali)
        mg = jumlah_harian.groupby(hari.to_period("W-FRI")).sum()
        an = anomali(mg, lambda p: min(p.start_time.isocalendar()[1], 52)).fillna(0)
        dorong = an.shift(1).reindex(hari.to_period("W-FRI")).fillna(0).values * -0.001
        r_sawit = r_sawit + dorong
    print(f"🧪 MODE TES: data PALSU {'dengan pola (minggu depan -0,1%/hari per +1 anomali)' if TES_TIRUAN else 'tanpa pola'}")
else:
    bag = []
    for f in sorted(Path("data/raw/histori/api").glob("MODIS_SP_*.parquet")):
        d = pd.read_parquet(f, columns=["latitude", "longitude", "acq_date", "confidence"])
        bag.append(d[d["confidence"] >= 30])
    api = pd.concat(bag, ignore_index=True)
    di_wilayah = np.zeros(len(api), bool)
    for x0, x1, y0, y1 in WILAYAH.values():
        di_wilayah |= api["longitude"].between(x0, x1).values & api["latitude"].between(y0, y1).values
    api = api[di_wilayah]
    hari_kal = pd.date_range("2000-11-01", api["acq_date"].max(), freq="D")
    jumlah_harian = api.groupby("acq_date").size().reindex(hari_kal, fill_value=0).astype(float)
    print(f"🔥 {len(api):,} titik api Sumatra+Kalimantan ({api['acq_date'].min():%Y-%m-%d} s/d {api['acq_date'].max():%Y-%m-%d})")
    tahunan = jumlah_harian.groupby(jumlah_harian.index.year).sum()
    print("   per tahun: " + "  ".join(f"{t}:{int(n / 1000)}rb" for t, n in tahunan.loc[2001:2018].items()))
    sys.path.insert(0, ".")
    from bersih_idx import bersihkan
    adj = {}
    for k in SAWIT:
        d = pd.read_parquet(f"data/raw/harga_idx/{k}.parquet", columns=["Adj Close", "Volume"])
        ix = pd.DatetimeIndex(pd.to_datetime(d.index))
        d.index = (ix.tz_localize(None) if ix.tz is not None else ix).normalize().astype("datetime64[ns]")
        d = d[~d.index.duplicated(keep="last")]
        adj[k] = d["Adj Close"].where(d["Volume"].fillna(0) > 0)
    adj = bersihkan(pd.DataFrame(adj).sort_index())
    kode = Path("riset_15_ramadan.py").read_text(encoding="utf-8").split("# ===== Label kalender =====")[0]
    ns, simpan = {}, sys.argv
    sys.argv = [sys.argv[0]]
    exec(compile(kode, "riset_15_bagian", "exec"), ns)
    sys.argv = simpan
    r_pasar = ns["ret_keranjang"]
    r_sawit = adj.reindex(r_pasar.index).ffill(limit=5).pct_change(fill_method=None).mean(axis=1)   # bobot sama, yang ada

# Batas latih: sinyal & target harus selesai <= 2018-12-31 (kecuali --buka-uji)
if not BUKA_DATA_UJI:
    jumlah_harian = jumlah_harian[jumlah_harian.index <= BATAS_LATIH]
    r_pasar, r_sawit = r_pasar[r_pasar.index <= BATAS_LATIH], r_sawit[r_sawit.index <= BATAS_LATIH]
selisih = (r_sawit - r_pasar).dropna()
print(f"🔒 Data uji {'DIBUKA' if BUKA_DATA_UJI else 'DIKUNCI'}.\n")

# U1 mingguan
mg = jumlah_harian.groupby(jumlah_harian.index.to_period("W-FRI")).sum()
an_mg = anomali(mg, lambda p: min(p.start_time.isocalendar()[1], 52))
y_mg = periode(return_periode(selisih, "W-FRI"))
b, t, n = t_robust(y_mg, an_mg.reindex(y_mg.index))
print(f"   U1 MINGGUAN anomali api w -> SAWIT-PASAR w+1: {b:+.3%} per +1 anomali, t robust {t:+.1f} ({n} minggu)")
# U2 bulanan
bl = jumlah_harian.groupby(jumlah_harian.index.to_period("M")).sum()
an_bl = anomali(bl, lambda p: p.month)
y_bl = periode(return_periode(selisih, "M"))
b, t, n = t_robust(y_bl, an_bl.reindex(y_bl.index))
print(f"   U2 BULANAN  anomali api m -> SAWIT-PASAR m+1: {b:+.3%} per +1 anomali, t robust {t:+.1f} ({n} bulan)")
# U3 6 bulan: jumlah selisih bulan m+1..m+6 (semua bulan target harus ada)
y6 = sum(y_bl.shift(-k) for k in range(6)).dropna()
x6 = an_bl.reindex(y6.index)
b, t1, n = t_nw(y6, x6, 6)
tanpa = y6.iloc[::6]
b2, t2, n2 = t_robust(tanpa, x6.reindex(tanpa.index))
t3 = min(abs(t1), abs(t2)) * np.sign(b)
print(f"   U3 6 BULAN  anomali api m -> SAWIT-PASAR m+1..m+6: {b:+.3%} per +1 anomali | t NW {t1:+.1f} ({n}), "
      f"tanpa tumpang tindih {t2:+.1f} ({n2}) -> t {t3:+.1f}")
print("\n   Diagnosis (bukan uji): 5 bulan anomali api TERBESAR & SAWIT-PASAR bulan berikutnya:")
for p, v in an_bl.reindex(y_bl.index).nlargest(5).items():
    print(f"     {p}: anomali {v:+.2f}, bulan berikutnya {y_bl[p]:+.2%}")
