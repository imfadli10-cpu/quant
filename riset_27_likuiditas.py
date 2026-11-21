"""
RISET #27: PERCEPATAN UANG BEREDAR (SEKI Bank Indonesia) -> SAHAM IDX BULAN DEPAN, data LATIH saja
================================================================================================

DUGAAN (ditulis 2026-11-21 SEBELUM menghitung hubungan apa pun; di-commit sebelum dijalankan)
-----------------------------------------------------------------------------------------
"Likuiditas mendorong harga aset": kalau pertumbuhan uang beredar MENINGKAT (uang di masyarakat bertambah lebih cepat),
sebagian mengalir ke saham -> return saham bulan-bulan berikutnya lebih tinggi (literatur: Thorbecke 1997; di pasar
berkembang efek likuiditas domestik lebih kuat karena investor ritel). M1 (uang tunai + giro = paling siap dibelanjakan)
diduga lebih kuat dari M2.
Perkiraan jujur: data makro bulanan terbit terlambat & pasar sudah melihat indikator lain lebih cepat; saya kira t < 2.

DATA: SEKI Tabel I.1 (`seki.seri_bulanan`), M1 & M2 akhir bulan (miliar Rp).
  JEDA TERBIT (konservatif): angka bulan m dianggap baru diketahui di AKHIR bulan m+2 (BI menerbitkan uang beredar
  ~4-6 minggu setelah akhir bulan; histori tanggal terbit tidak ada sebelum foto kita) -> sinyal akhir bulan t memakai
  angka bulan t-2.
  Pertumbuhan tahunan g(m) = M(m)/M(m-12) - 1. PERCEPATAN a(m) = g(m) - g(m-3).
  Sinyal akhir bulan t = a(t-2). Target = return keranjang 30 saham paling likuid (riset #4/#15) bulan t+1
  (sesudah tutup hari bursa pertama t+1 s/d tutup hari bursa pertama t+2).
UJI (3; dua arah; |t| > 3; t robust White):
  U1 return t+1 pada percepatan M1.   U2 sama, M2.
  U3 return t+1: bulan dengan percepatan M1 > 0 vs <= 0 (t Welch) = versi strategi 'pegang saat likuiditas menguat'.
Data uji 2019+ DIKUNCI. Uji kode: --tes-tiruan (return +0,4% per +1 poin persen percepatan M1) & --tes-kosong.
"""
import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BATAS_LATIH = pd.Timestamp("2018-12-31")
BUKA_DATA_UJI = "--buka-uji" in sys.argv
TES_TIRUAN, TES_KOSONG = "--tes-tiruan" in sys.argv, "--tes-kosong" in sys.argv
JEDA = 2


def t_robust(y, x):
    d = pd.concat([y, x], axis=1).dropna()
    yy, xx = d.iloc[:, 0].values, d.iloc[:, 1].values
    xc = xx - xx.mean()
    b = (xc * (yy - yy.mean())).sum() / (xc ** 2).sum()
    e = yy - yy.mean() - b * xc
    return b, b / (np.sqrt((xc ** 2 * e ** 2).sum()) / (xc ** 2).sum()), len(d)


def t_welch(a, b):
    a, b = pd.Series(a).dropna(), pd.Series(b).dropna()
    return (a.mean() - b.mean()) / np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))


def return_bulan_depan(r_harian):
    """Per bulan sinyal t (Period): return sesudah tutup hari bursa pertama t+1 s/d tutup hari bursa pertama t+2."""
    hari = r_harian.index
    per = hari.to_period("M")
    awal = pd.Series(hari, index=hari).groupby(per).min()
    hasil = {}
    for p in awal.index:
        if p + 1 in awal.index and p + 2 in awal.index:
            r = r_harian[(hari > awal[p + 1]) & (hari <= awal[p + 2])]
            hasil[p] = np.prod(1 + r) - 1
    return pd.Series(hasil)


def percepatan(m):
    m.index = m.index.to_period("M")
    m = m.asfreq("M")
    g = m / m.shift(12) - 1
    return g - g.shift(3)


if TES_TIRUAN or TES_KOSONG:
    acak = np.random.default_rng(27)
    bln = pd.period_range("1995-01", "2026-09", freq="M")
    tumbuh = 0.01 + np.cumsum(acak.normal(0, 0.004, len(bln))) * 0.2
    m1 = pd.Series(1000 * np.exp(np.cumsum(tumbuh)), index=bln.to_timestamp())
    m2 = pd.Series(3000 * np.exp(np.cumsum(tumbuh * 0.8 + acak.normal(0, 0.003, len(bln)))), index=bln.to_timestamp())
    a1 = percepatan(m1.copy()).shift(JEDA)
    sig_bln = pd.period_range("2002-05", "2026-09", freq="M")
    r_t1 = pd.Series(acak.normal(0.01, 0.06, len(sig_bln)), index=sig_bln)
    if TES_TIRUAN:
        r_t1 = r_t1 + 0.4 * a1.reindex(sig_bln).fillna(0)        # +0,4% per +1 poin persen (0,01) percepatan
    print(f"🧪 MODE TES: data PALSU {'dengan pola (+0,4% per +1 pp percepatan M1)' if TES_TIRUAN else 'tanpa pola'}")
else:
    sys.path.insert(0, ".")
    from seki import seri_bulanan
    f = sorted(glob.glob("data/raw/seki/*/TABEL1_1.xls"))[-1]
    m1 = seri_bulanan(f, r"uang beredar sempit|narrow money")
    m2 = seri_bulanan(f, r"uang beredar luas|broad money")
    kode = Path("riset_15_ramadan.py").read_text(encoding="utf-8").split("# ===== Label kalender =====")[0]
    ns, simpan = {}, sys.argv
    sys.argv = [sys.argv[0]]
    exec(compile(kode, "riset_15_bagian", "exec"), ns)
    sys.argv = simpan
    r_t1 = return_bulan_depan(ns["ret_keranjang"].dropna())

a1 = percepatan(m1.copy()).shift(JEDA)          # sinyal akhir bulan t = percepatan bulan t-2
a2 = percepatan(m2.copy()).shift(JEDA)
akhir_target = pd.Series([(p + 2).start_time for p in r_t1.index], index=r_t1.index)   # jual di hari bursa pertama t+2
pilih = (akhir_target > BATAS_LATIH + pd.Timedelta(days=1)) if BUKA_DATA_UJI else (akhir_target <= BATAS_LATIH)
y = r_t1[pilih.values]
print(f"🔒 Data uji {'DIBUKA' if BUKA_DATA_UJI else 'DIKUNCI'}.\n")
for nama, a in [("U1 M1", a1), ("U2 M2", a2)]:
    b, t, n = t_robust(y, a.reindex(y.index))
    print(f"   {nama}: +1 poin persen percepatan -> return bulan depan {b * 0.01:+.2%}, t robust {t:+.1f} ({n} bulan)")
x = a1.reindex(y.index)
naik, turun = y[x > 0], y[x <= 0]
print(f"   U3 bulan likuiditas M1 MENGUAT {naik.mean():+.2%} ({len(naik)}) vs MELEMAH {turun.mean():+.2%} ({len(turun)}) "
      f"-> t {t_welch(naik, turun):+.1f}")
if not (TES_TIRUAN or TES_KOSONG):
    print(f"   (cek data: percepatan M1 sb {a1.loc['2003':'2018'].std() * 100:.1f} pp, M2 {a2.loc['2003':'2018'].std() * 100:.1f} pp)")
