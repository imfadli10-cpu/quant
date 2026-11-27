"""
RISET #61: DRIFT SESUDAH STOCK SPLIT (Ikenberry-Rankine-Stice 1996; Desai-Jain 1997; bantahan Boehme-Danielsen 2007) -> saham IDX, data LATIH
======================================================================================================================================
Pra-registrasi: docs/prareg_61_split.md (di-commit SEBELUM return sesudah split dilihat).
Peristiwa: split MAJU rasio >= 1,5 (raw/aksi_idx; 1,02-1,4 = rights/bonus dibuang); d0 = hari bursa pertama >= tanggal ex; masuk tutup d0.
Syarat (s/d d-1): median nilai transaksi 60 hari >= Rp1 M, >= 80% hari aktif 250 hari; tutup d0 >= Rp100. 1 peristiwa/saham/60 hari.
U1 abnormal +60 hari vs keranjang 30 likuid | U2 vs saham lolos syarat di kuintil momentum (return 250 hari s/d d0) yang sama.
t = rata-rata per bulan, bulan non-tumpang tindih (tiap 3 bulan). |t| > 3. Info: +20/+120, hari ex, split BALIK (<= 0,67), paruh.
Uji kode: --tes-tiruan / --tes-kosong / --potong-data (IDENTIK). Data uji 2019+ DIKUNCI.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BATAS = pd.Timestamp("2018-12-31")
TES_TIRUAN, TES_KOSONG = "--tes-tiruan" in sys.argv, "--tes-kosong" in sys.argv
POTONG = "--potong-data" in sys.argv
H, JAUH = 60, 120

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


# ---- harga + pembersihan + keranjang 30 (sama dgn #60)
tutup, vol, adj = {}, {}, {}
for f in sorted(Path("data/raw/harga_idx").glob("*.parquet")):
    d = pd.read_parquet(f, columns=["Adj Close", "Close", "Volume"])
    d.index = jadi_tanggal(d.index)
    d = d[~d.index.duplicated(keep="last")]
    adj[f.stem], tutup[f.stem], vol[f.stem] = d["Adj Close"], d["Close"], d["Volume"]
adj, tutup, vol = (pd.DataFrame(x).sort_index() for x in (adj, tutup, vol))
from bersih_idx import bersihkan
adj2 = bersihkan(adj)
tutup = tutup.mask(adj2.isna() & adj.notna())
adj = adj2
aktif = vol.fillna(0) > 0
hari = aktif.index[(aktif.sum(axis=1) >= 10) & (aktif.index.day_of_week < 5)]
adj, tutup, vol, aktif = (x.loc[hari] for x in (adj, tutup, vol, aktif))
kode15 = Path("riset_15_ramadan.py").read_text(encoding="utf-8").split("# ===== Label kalender =====")[0]
ns, simpan = {}, sys.argv
sys.argv = [sys.argv[0]]
exec(compile(kode15, "riset_15_bagian", "exec"), ns)
sys.argv = simpan
r_pasar = ns["ret_keranjang"].reindex(hari).fillna(0)
pasar_kum = np.concatenate([[1.0], np.cumprod(1 + r_pasar.values)])   # pasar_kum[i+1] = indeks s/d hari i

med_nilai = (tutup * vol).where(aktif).rolling(60, min_periods=40).median().shift(1)
porsi = aktif.rolling(250, min_periods=250).mean().shift(1)
syarat = ((tutup >= 100) & (med_nilai >= 1e9) & (porsi >= 0.8)).values
A = adj.values
mom = (adj / adj.shift(250) - 1).values

aksi = pd.read_parquet("data/raw/aksi_idx/semua.parquet")
aksi = aksi[aksi["split"].fillna(0) > 0].copy()
aksi["tanggal"] = jadi_tanggal(aksi["tanggal"])
idx = {k: j for j, k in enumerate(adj.columns)}


TES = TES_TIRUAN or TES_KOSONG
acak = np.random.default_rng(61)


def peristiwa(maju):
    s = aksi[(aksi["split"] >= 1.5) if maju else (aksi["split"] <= 0.67)]
    baris, harian = [], []                      # harian: (indeks hari, abnormal vs keranjang, abnormal vs kuintil momentum)
    for kode, b in s.sort_values("tanggal").groupby("kode"):
        j = idx.get(kode)
        if j is None:
            continue
        terakhir = -10**9
        for tgl, rasio in zip(b["tanggal"], b["split"]):
            i0 = int(np.searchsorted(hari.values, np.datetime64(tgl)))
            if i0 >= len(hari) or i0 - terakhir <= H or i0 + JAUH >= len(hari) or hari[i0 + H] > BATAS:
                continue
            if not (syarat[i0, j] and np.isfinite(A[i0, j]) and np.isfinite(A[i0 - 1, j])):
                continue
            terakhir = i0
            e = {"kode": kode, "d0": hari[i0], "rasio": rasio, "hari_ex": A[i0, j] / A[i0 - 1, j] - r_pasar.iloc[i0] - 1}
            for nama, h in (("u20", 20), ("u1", H), ("u120", JAUH)):
                rs = A[i0 + h, j] / A[i0, j] - 1
                rp = pasar_kum[i0 + h + 1] / pasar_kum[i0 + 1] - 1
                e[nama] = float(np.clip(rs - rp, -1, 1)) if np.isfinite(rs) and hari[i0 + h] <= BATAS else np.nan
            # pembanding kuintil momentum yang sama (saham lain yang lolos syarat di d0)
            ok = syarat[i0] & np.isfinite(mom[i0]) & np.isfinite(A[i0])
            ok[j] = False
            sama = None
            if ok.sum() >= 25 and np.isfinite(mom[i0, j]):
                batas = np.quantile(mom[i0, ok], [0.2, 0.4, 0.6, 0.8])
                q_e = np.searchsorted(batas, mom[i0, j])
                sama = ok & (np.searchsorted(batas, np.nan_to_num(mom[i0], nan=-9)) == q_e)
                e["kuintil"] = int(q_e) + 1
                if sama.sum() < 3:
                    sama = None
            for k in range(1, H + 1):
                i = i0 + k
                rs = A[i, j] / A[i - 1, j] - 1
                if not np.isfinite(rs):
                    continue
                if TES:                                  # return saham PALSU: pembanding + derau (+ drift 5% per 60 hari)
                    a1 = acak.normal(0.05 / H if TES_TIRUAN else 0.0, 0.03)
                    a2 = a1
                else:
                    a1 = rs - r_pasar.iloc[i]
                    a2 = rs - np.nanmean(A[i, sama] / A[i - 1, sama] - 1) if sama is not None else np.nan
                harian.append((i, a1, a2))
            baris.append(e)
    return pd.DataFrame(baris), pd.DataFrame(harian, columns=["i", "a1", "a2"])


def kalender(hr):
    """Portofolio waktu kalender: rata-rata abnormal harian peristiwa aktif, dijumlah per bulan (Mitchell-Stafford 2000)."""
    d = hr.groupby("i")[["a1", "a2"]].mean()
    d["bulan"] = pd.DatetimeIndex(hari[d.index.values]).to_period("M")
    g = d.groupby("bulan")
    s, n = g[["a1", "a2"]].sum(min_count=1), g.size()
    return s[n >= 5], n


e, hr = peristiwa(True)
if TES:
    print(f"🧪 MODE TES: return harian saham PALSU {'+5%/60 hari + derau' if TES_TIRUAN else 'derau saja'}")
print("🔒 Data uji 2019+ DIKUNCI.\n")
m, n_hari = kalender(hr)
m = m.dropna(how="all")
p = len(m) // 2
print(f"   {len(e)} split maju ({e['d0'].min():%Y-%m} s/d {e['d0'].max():%Y-%m}), {e['kode'].nunique()} saham; {len(m)} bulan kalender aktif "
      f"(>= 5 hari); rasio median {e['rasio'].median():.0f}; kuintil momentum median {e['kuintil'].median():.0f} (1 = terendah)")
print("   per tahun: " + " ".join(f"{k}:{v}" for k, v in e['d0'].dt.year.value_counts().sort_index().items()))
for nama, lab in (("a1", "U1 vs keranjang 30"), ("a2", "U2 vs kuintil momentum")):
    print(f"   {lab:24s}: {m[nama].mean():+.2%}/bln (~{m[nama].mean() * 3:+.1%} per 60 hari bursa); t {t_rata(m[nama]):+.2f} "
          f"(paruh {t_rata(m[nama].iloc[:p]):+.1f}/{t_rata(m[nama].iloc[p:]):+.1f})")
if not TES:
    print(f"   info per peristiwa: +20 hari {e['u20'].mean():+.2%} | +{H} {e['u1'].mean():+.2%} (median {e['u1'].median():+.2%}) | "
          f"+{JAUH} {e['u120'].mean():+.2%} (median {e['u120'].median():+.2%}) | hari ex {e['hari_ex'].mean():+.2%}")
    b, hb = peristiwa(False)
    if len(b):
        mb, _ = kalender(hb)
        print(f"   info split BALIK: {len(b)} peristiwa, +{H} hari {b['u1'].mean():+.2%} (median {b['u1'].median():+.2%}); "
              f"kalender {mb['a1'].mean():+.2%}/bln t {t_rata(mb['a1']):+.2f} ({mb['a1'].notna().sum()} bln)")
hasil = {"U1": t_rata(m["a1"]), "U2": t_rata(m["a2"])}
lolos = [k for k, v in hasil.items() if abs(v) > 3]
print(f"\n   KEPUTUSAN #61 (|t| > 3): {'✅ ' + ', '.join(lolos) if lolos else '❌ tidak ada yang lolos'}")
