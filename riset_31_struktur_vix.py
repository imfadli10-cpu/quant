"""
RISET #31: STRUKTUR WAKTU VIX (VIX / VIX3M, 'PANIK JANGKA PENDEK') -> SAHAM INDONESIA MINGGU DEPAN, data LATIH saja
================================================================================================================

DUGAAN (ditulis 2026-11-21 SEBELUM menghitung hubungan apa pun; di-commit sebelum dijalankan)
-----------------------------------------------------------------------------------------
VIX / VIX3M > 1 (backwardation) = investor membayar SANGAT mahal untuk proteksi 1 bulan dibanding 3 bulan = panik akut.
Literatur S&P 500 (mis. Fassas & Hourvouliades 2019; Johnson 2017 'Risk premia and the VIX term structure'): kepanikan seperti
ini diikuti return LEBIH TINGGI (premi rasa takut dibayar ke yang berani membeli). Dugaan: hubungan POSITIF antara rasio
minggu w dan return saham Indonesia minggu w+1 (dana global kembali masuk setelah panik).
Perkiraan jujur: di AS efek ini ada tapi lemah & tidak stabil; ke Indonesia lewat jalur tidak langsung -> t < 2.

DATA: CBOE `raw/cboe/indeks.parquet` VIX & VIX3M (sejak 2009-09), harga tutup harian AS.
SINYAL minggu w (Sabtu-Jumat) = VIX/VIX3M pada hari bursa AS TERAKHIR minggu w (Jumat 16:15 NY = Sabtu pagi WIB, diketahui
  sebelum IDX buka Senin). Rasio DIBATASI 0,7..1,5 (cegah pencilan; pelajaran riset #30), TANPA z-skor bergulir.
TARGET minggu w+1 (fungsi riset #20/#30): IDX keranjang 30 saham paling likuid; EIDO (Adj Close).
UJI (3; |t| > 3; dua arah):
  U1 IDX w+1 pada rasio (t robust White).   U2 EIDO w+1 pada rasio.
  U3 IDX w+1: minggu BACKWARDATION (rasio > 1) vs lainnya (t Welch).
Data uji 2019+ DIKUNCI. Uji kode: --tes-tiruan (+3% per +1 rasio, = +0,3% per +0,1) & --tes-kosong.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BATAS_LATIH = pd.Timestamp("2018-12-31")
BUKA_DATA_UJI = "--buka-uji" in sys.argv
TES_TIRUAN, TES_KOSONG = "--tes-tiruan" in sys.argv, "--tes-kosong" in sys.argv
P = "W-FRI"
src30 = Path("riset_30_tga.py").read_text(encoding="utf-8")
exec(compile(src30[src30.index("def t_robust"):src30.index("def sinyal_tga")], "riset_30_fungsi", "exec"))


def t_welch(a, b):
    a, b = pd.Series(a).dropna(), pd.Series(b).dropna()
    return (a.mean() - b.mean()) / np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))


def sinyal_rasio(vix, vix3m):
    r = (vix / vix3m).dropna().clip(0.7, 1.5)
    return r.groupby(r.index.to_period(P)).last()


if TES_TIRUAN or TES_KOSONG:
    acak = np.random.default_rng(31)
    hari = pd.bdate_range("2009-09-18", "2026-11-13").astype("datetime64[ns]")
    lv = np.zeros(len(hari))
    for i in range(1, len(hari)):
        lv[i] = 0.97 * lv[i - 1] + acak.normal(0, 0.06)
    vix3m = pd.Series(20 * np.exp(lv), index=hari)
    vix = vix3m * (0.9 + 0.5 * np.clip(lv, -0.4, 0.6) + acak.normal(0, 0.03, len(hari)))
    s = sinyal_rasio(vix, vix3m)
    mg = pd.period_range(hari[0], hari[-1], freq=P)
    r_idx = pd.Series(acak.normal(0.002, 0.03, len(mg)), index=mg)
    r_eido = pd.Series(acak.normal(0.002, 0.035, len(mg)), index=mg)
    if TES_TIRUAN:
        r_idx = r_idx + 0.03 * (s.reindex(mg) - s.mean()).fillna(0)
        r_eido = r_eido + 0.03 * (s.reindex(mg) - s.mean()).fillna(0)
    print(f"🧪 MODE TES: data PALSU {'dengan pola (+0,3% per +0,1 rasio)' if TES_TIRUAN else 'tanpa pola'}")
else:
    c = pd.read_parquet("data/raw/cboe/indeks.parquet")
    def seri(k):
        x = c[c["indeks"] == k].set_index("tanggal")["tutup"]
        return x[x > 0]
    s = sinyal_rasio(seri("VIX"), seri("VIX3M"))
    kode = Path("riset_15_ramadan.py").read_text(encoding="utf-8").split("# ===== Label kalender =====")[0]
    ns, simpan = {}, sys.argv
    sys.argv = [sys.argv[0]]
    exec(compile(kode, "riset_15_bagian", "exec"), ns)
    sys.argv = simpan
    r_idx = mingguan_dari_harian(ns["ret_keranjang"].dropna())
    import duckdb
    e = duckdb.connect().execute("""SELECT CAST(tanggal AS DATE) t, "Adj Close" a FROM read_parquet('data/bersih/saham_as.parquet')
                                    WHERE kode = 'EIDO' ORDER BY 1""").df()
    r_eido = mingguan_dari_harian(pd.Series(e["a"].values, index=pd.DatetimeIndex(e["t"])).pct_change().dropna())
    ss = s.loc[:pd.Period("2018-12-28", freq=P)]
    print(f"📈 rasio VIX/VIX3M mingguan: {len(ss)} minggu latih, median {ss.median():.3f}, backwardation (>1) {(ss > 1).mean():.0%} minggu")

print(f"🔒 Data uji {'DIBUKA' if BUKA_DATA_UJI else 'DIKUNCI'}.\n")


def pilih(r):
    akhir = pd.Series([(w + 2).end_time.normalize() for w in r.index], index=r.index)
    return r[((akhir > BATAS_LATIH + pd.Timedelta(days=14)) if BUKA_DATA_UJI else (akhir <= BATAS_LATIH)).values]


for nama, r in [("U1 IDX keranjang 30", r_idx), ("U2 EIDO", r_eido)]:
    y = pilih(r)
    b, t, n = t_robust(y, s.reindex(y.index))
    print(f"   {nama:20}: +0,1 rasio -> minggu depan {b * 0.1:+.3%}, t robust {t:+.1f} ({n} minggu)")
y = pilih(r_idx)
x = s.reindex(y.index)
bw, lain = y[x > 1], y[x <= 1]
print(f"   U3 IDX setelah BACKWARDATION {bw.mean():+.2%}/mg ({len(bw)}) vs lainnya {lain.mean():+.2%}/mg ({len(lain)}) "
      f"-> t {t_welch(bw, lain):+.1f}")
