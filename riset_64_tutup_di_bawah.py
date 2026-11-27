"""
RISET #64: ANJLOK >= 10% & TUTUP DI TERENDAH (mirip ARB; Kim-Rhee 1997 lanjut vs Bremer-Sweeney 1991 memantul) -> saham IDX, data LATIH
Pra-registrasi: docs/prareg_64_tutup_di_bawah.md (di-commit SEBELUM return sesudah peristiwa dilihat).
Masuk = tutup hari pertama 1..5 sesudah d0 yang tidak terkunci. Portofolio WAKTU KALENDER (#61): U1 H=20, U2 H=60, abnormal vs keranjang 30.
|t| > 3 dua arah. Uji kode: --tes-tiruan / --tes-kosong / --potong-data (IDENTIK). Data uji 2019+ DIKUNCI.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BATAS = pd.Timestamp("2018-12-31")
TES_TIRUAN, TES_KOSONG = "--tes-tiruan" in sys.argv, "--tes-kosong" in sys.argv
TES = TES_TIRUAN or TES_KOSONG
POTONG = "--potong-data" in sys.argv
ANJLOK, H1, H2 = -0.10, 20, 60

if POTONG:
    _baca = pd.read_parquet

    def _terpotong(*a, **k):
        d = _baca(*a, **k)
        if isinstance(d.index, pd.DatetimeIndex):
            d = d[d.index <= BATAS]
        for c in ("tanggal", "Date"):
            if c in d.columns and pd.api.types.is_datetime64_any_dtype(d[c]):
                d = d[d[c] <= BATAS]
        return d
    pd.read_parquet = _terpotong


def t_rata(x):
    x = pd.Series(x).dropna()
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else np.nan


def jadi_tanggal(x):
    t = pd.DatetimeIndex(pd.to_datetime(x))
    return (t.tz_localize(None) if t.tz is not None else t).normalize().astype("datetime64[ns]")


tutup, rendah, vol, adj = {}, {}, {}, {}
for f in sorted(Path("data/raw/harga_idx").glob("*.parquet")):
    d = pd.read_parquet(f, columns=["Adj Close", "Close", "Low", "Volume"])
    d.index = jadi_tanggal(d.index)
    d = d[~d.index.duplicated(keep="last")]
    adj[f.stem], tutup[f.stem], rendah[f.stem], vol[f.stem] = d["Adj Close"], d["Close"], d["Low"], d["Volume"]
adj, tutup, rendah, vol = (pd.DataFrame(x).sort_index() for x in (adj, tutup, rendah, vol))
from bersih_idx import bersihkan
adj2 = bersihkan(adj)
rusak = adj2.isna() & adj.notna()
adj, tutup, rendah = adj2, tutup.mask(rusak), rendah.mask(rusak)
aktif = vol.fillna(0) > 0
hari = aktif.index[(aktif.sum(axis=1) >= 10) & (aktif.index.day_of_week < 5)]
adj, tutup, rendah, vol, aktif = (x.loc[hari] for x in (adj, tutup, rendah, vol, aktif))
kode15 = Path("riset_15_ramadan.py").read_text(encoding="utf-8").split("# ===== Label kalender =====")[0]
ns, simpan = {}, sys.argv
sys.argv = [sys.argv[0]]
exec(compile(kode15, "riset_15_bagian", "exec"), ns)
sys.argv = simpan
r_pasar = ns["ret_keranjang"].reindex(hari).fillna(0)
pasar_kum = np.concatenate([[1.0], np.cumprod(1 + r_pasar.values)])

ret = tutup / tutup.shift(1) - 1
bawah = (ret <= ANJLOK) & (tutup <= rendah * 1.0001) & aktif
med_nilai = (tutup * vol).where(aktif).rolling(60, min_periods=40).median().shift(1)
porsi = aktif.rolling(250, min_periods=250).mean().shift(1)
syarat = (tutup.shift(1) >= 100) & (med_nilai >= 1e9) & (porsi >= 0.8)
ev = bawah & syarat
A, P, R = adj.values, bawah.values, r_pasar.values
acak = np.random.default_rng(64)
baris, harian = [], []
for j, kode in enumerate(adj.columns):
    terakhir = -10**9
    for i0 in np.where(ev[kode].values)[0]:
        if i0 - terakhir <= 20:
            continue
        terakhir = i0
        masuk = next((i0 + k for k in range(1, 6) if i0 + k < len(hari) and not P[i0 + k, j] and np.isfinite(A[i0 + k, j])), None)
        if masuk is None or masuk + H2 >= len(hari) or hari[masuk + H2] > BATAS:      # seleksi TIDAK bergantung data > 2018
            continue
        e = {"kode": kode, "d0": hari[i0], "tunda": masuk - i0 - 1,
             "lanjut1": A[i0 + 1, j] / A[i0, j] - 1 - R[i0 + 1] if np.isfinite(A[i0 + 1, j]) else np.nan}
        for nama, h in (("u20", H1), ("u60", H2)):
            rs = A[masuk + h, j] / A[masuk, j] - 1
            e[nama] = float(np.clip(rs - (pasar_kum[masuk + h + 1] / pasar_kum[masuk + 1] - 1), -1, 1)) if np.isfinite(rs) else np.nan
        for k in range(1, H2 + 1):
            i = masuk + k
            rs = A[i, j] / A[i - 1, j] - 1
            if not np.isfinite(rs):
                continue
            a = acak.normal(0.05 / H1 if TES_TIRUAN else 0.0, 0.03) if TES else rs - R[i]
            harian.append((i, k, a))
        baris.append(e)
e = pd.DataFrame(baris)
hr = pd.DataFrame(harian, columns=["i", "k", "a"])
if TES:
    print(f"🧪 MODE TES: return harian PALSU {'+5%/20 hari + derau' if TES_TIRUAN else 'derau saja'}")
print("🔒 Data uji 2019+ DIKUNCI.\n")


def kalender(h):
    x = hr[hr["k"] <= h].groupby("i")["a"].mean()
    b = pd.DatetimeIndex(hari[x.index.values]).to_period("M")
    g = x.groupby(b)
    return g.sum()[g.size() >= 5]


m1, m2 = kalender(H1), kalender(H2)
print(f"   {len(e)} peristiwa ({e['d0'].min():%Y-%m} s/d {e['d0'].max():%Y-%m}), {e['kode'].nunique()} saham; masuk tertunda (terkunci) "
      f"{(e['tunda'] > 0).mean():.0%}; bulan kalender aktif U1 {len(m1)}, U2 {len(m2)}")
print("   per tahun: " + " ".join(f"{k}:{v}" for k, v in e['d0'].dt.year.value_counts().sort_index().items()))
for lab, m in ((f"U1 kalender H={H1}", m1), (f"U2 kalender H={H2}", m2)):
    p = len(m) // 2
    print(f"   {lab}: {m.mean():+.2%}/bln  t {t_rata(m):+.2f}  (paruh {t_rata(m.iloc[:p]):+.1f}/{t_rata(m.iloc[p:]):+.1f})")
if not TES:
    print(f"   info per peristiwa: +20 {e['u20'].mean():+.2%} (median {e['u20'].median():+.2%}) | +60 {e['u60'].mean():+.2%} "
          f"(median {e['u60'].median():+.2%}) | d0->d+1 (tak bisa dibeli) {e['lanjut1'].mean():+.2%} (median {e['lanjut1'].median():+.2%})")
hasil = {"U1": t_rata(m1), "U2": t_rata(m2)}
lolos = [k for k, v in hasil.items() if abs(v) > 3]
print(f"\n   KEPUTUSAN #64 (|t| > 3): {'✅ ' + ', '.join(lolos) if lolos else '❌ tidak ada yang lolos'}")
