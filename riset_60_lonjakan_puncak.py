"""
RISET #60: LONJAKAN 'TUTUP DI PUNCAK' (mirip ARA: return >= +20% & tutup = tertinggi) -> saham IDX 20/60 hari sesudahnya, data LATIH saja
================================================================================================================================
DUGAAN (ditulis 27 Nov 2026 SEBELUM return sesudah peristiwa dilihat; di-commit sebelum dijalankan). DUA ARAH (dua teori bertentangan):
  (+) MAGNET / penemuan harga tertunda (Kim-Rhee 1997 JF, batas harga Bursa Tokyo): batas harian memotong permintaan -> harga terus naik
      beberapa hari sesudahnya; permintaan ritel yang belum terpenuhi (antrean ARA) terbawa.
  (-) REAKSI BERLEBIHAN ritel / saham 'lotre' (Bali-Cakici-Whitelaw 2011 MAX; De Bondt-Thaler): lonjakan ekstrem berbalik.
  Di IDX yang ritel-sentris, #12 S4 (max return 21 hari rendah = bagus) searah (-) tapi lemah (IC t 1,7). Perkiraan jujur: lanjutan 1-2 hari
  (tidak bisa dibeli), sesudahnya cenderung berbalik; |t| < 3.
PERISTIWA (aturan BEBAS dari batas ARA resmi, yang berubah antar tahun & tidak terdokumentasi rapi sebelum 2017):
  hari d0: Close/Close(d-1) - 1 >= +20% DAN Close = High (tutup di puncak, tak ada penjual di atas) DAN Volume > 0; Close & High = harga Yahoo
  (sama-sama disesuaikan split). Syarat saham (dihitung s/d d-1): harga >= Rp100, median nilai transaksi 60 hari >= Rp1 M, >= 80% hari aktif
  250 hari (saringan #2). Peristiwa kedua dari saham yang sama dalam 20 hari bursa dibuang (ambil yang pertama). Harga dibersihkan bersih_idx.
MASUK: tutup hari pertama k = 1..5 sesudah d0 yang BUKAN hari 'tutup di puncak >= 20%' (saat terkunci tidak bisa dibeli); tidak ada -> dibuang.
UJI (|t| > 3, dua arah; abnormal = saham - keranjang 30 likuid, dibatasi +-100%; dirata-rata PER BULAN lalu t antar bulan [peristiwa berkelompok]):
  U1 abnormal masuk -> +20 hari bursa.   U2 abnormal masuk -> +60 hari bursa (t dari bulan non-tumpang tindih: setiap 3 bulan).
Info: return d0 -> d+1 (lanjutan langsung, TIDAK bisa dibeli), porsi masuk tertunda (terkunci), median, per paruh, jumlah peristiwa per tahun.
Strategi long-only (kalau U1/U2 positif & lolos) dinilai terpisah dgn biaya B. Data uji 2019+ DIKUNCI.
Uji kode: --tes-tiruan (abnormal peristiwa diganti derau + 5%) & --tes-kosong (derau saja); --potong-data -> IDENTIK.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BATAS = pd.Timestamp("2018-12-31")
TES_TIRUAN, TES_KOSONG = "--tes-tiruan" in sys.argv, "--tes-kosong" in sys.argv
POTONG = "--potong-data" in sys.argv
LONJAK, H1, H2 = 0.20, 20, 60

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


# ---- harga (Close, High, Volume, Adj Close) + pembersihan + keranjang 30
tutup, tinggi, vol, adj = {}, {}, {}, {}
for f in sorted(Path("data/raw/harga_idx").glob("*.parquet")):
    d = pd.read_parquet(f, columns=["Adj Close", "Close", "High", "Volume"])
    d.index = jadi_tanggal(d.index)
    d = d[~d.index.duplicated(keep="last")]
    adj[f.stem], tutup[f.stem], tinggi[f.stem], vol[f.stem] = d["Adj Close"], d["Close"], d["High"], d["Volume"]
adj, tutup, tinggi, vol = (pd.DataFrame(x).sort_index() for x in (adj, tutup, tinggi, vol))
from bersih_idx import bersihkan
adj2 = bersihkan(adj)
rusak = adj2.isna() & adj.notna()
adj, tutup, tinggi = adj2, tutup.mask(rusak), tinggi.mask(rusak)
aktif = vol.fillna(0) > 0
hari = aktif.index[(aktif.sum(axis=1) >= 10) & (aktif.index.day_of_week < 5)]
adj, tutup, tinggi, vol, aktif = (x.loc[hari] for x in (adj, tutup, tinggi, vol, aktif))
kode15 = Path("riset_15_ramadan.py").read_text(encoding="utf-8").split("# ===== Label kalender =====")[0]
ns, simpan = {}, sys.argv
sys.argv = [sys.argv[0]]
exec(compile(kode15, "riset_15_bagian", "exec"), ns)
sys.argv = simpan
r_pasar = ns["ret_keranjang"].reindex(hari).fillna(0)
pasar_kum = np.concatenate([[1.0], np.cumprod(1 + r_pasar.values)])   # pasar_kum[i+1] = indeks s/d hari i

ret = tutup / tutup.shift(1) - 1
puncak = (ret >= LONJAK) & (tutup >= tinggi * 0.9999) & aktif
med_nilai = (tutup * vol).where(aktif).rolling(60, min_periods=40).median().shift(1)
porsi = aktif.rolling(250, min_periods=250).mean().shift(1)
syarat = (tutup.shift(1) >= 100) & (med_nilai >= 1e9) & (porsi >= 0.8)
ev = (puncak & syarat)
print(f"📥 {adj.shape[1]} saham, {len(hari):,} hari; peristiwa mentah (lolos syarat) {int(ev.values.sum()):,}")

A, P, idx = adj.values, puncak.values, {k: j for j, k in enumerate(adj.columns)}
baris = []
for kode in adj.columns:
    j = idx[kode]
    pos = np.where(ev[kode].values)[0]
    terakhir = -10**9
    for i0 in pos:
        if i0 - terakhir <= 20:
            continue
        terakhir = i0
        masuk = next((i0 + k for k in range(1, 6) if i0 + k < len(hari) and not P[i0 + k, j] and np.isfinite(A[i0 + k, j])), None)
        if masuk is None or masuk + H2 >= len(hari):
            continue
        b = {"kode": kode, "d0": hari[i0], "tunda": masuk - i0 - 1,
             "lanjut1": A[i0 + 1, j] / A[i0, j] - 1 if np.isfinite(A[i0 + 1, j]) else np.nan}
        for nama, h in (("u1", H1), ("u2", H2)):
            k1 = masuk + h
            b[f"keluar_{nama}"] = hari[k1]
            rs = A[k1, j] / A[masuk, j] - 1
            rp = pasar_kum[k1 + 1] / pasar_kum[masuk + 1] - 1
            b[nama] = float(np.clip(rs - rp, -1, 1)) if np.isfinite(rs) else np.nan
        baris.append(b)
e = pd.DataFrame(baris)
e = e[e["keluar_u2"] <= BATAS].copy()                 # kedua jendela berakhir di data latih
if TES_TIRUAN or TES_KOSONG:
    acak = np.random.default_rng(60)
    for nama, sb in (("u1", 0.15), ("u2", 0.25)):
        e[nama] = acak.normal(0.05 if TES_TIRUAN else 0.0, sb, len(e))
    print(f"🧪 MODE TES: abnormal peristiwa PALSU {'+5% + derau' if TES_TIRUAN else 'derau saja'}")
print("🔒 Data uji 2019+ DIKUNCI.\n")
e["bulan"] = e["d0"].dt.to_period("M")
m = e.groupby("bulan")[["u1", "u2"]].mean()
print(f"   {len(e)} peristiwa ({e['d0'].min():%Y-%m} s/d {e['d0'].max():%Y-%m}), {e['kode'].nunique()} saham, {len(m)} bulan berperistiwa; "
      f"masuk tertunda (terkunci) {(e['tunda'] > 0).mean():.0%}")
print("   per tahun: " + " ".join(f"{k}:{v}" for k, v in e['d0'].dt.year.value_counts().sort_index().items()))
p = len(m) // 2
print(f"   U1 abnormal +{H1} hari: {e['u1'].mean():+.2%} (median {e['u1'].median():+.2%}); per bulan t {t_rata(m['u1']):+.2f} "
      f"(paruh {t_rata(m['u1'].iloc[:p]):+.1f}/{t_rata(m['u1'].iloc[p:]):+.1f})")
m3 = m["u2"][[x.ordinal % 3 == 0 for x in m.index]]
print(f"   U2 abnormal +{H2} hari: {e['u2'].mean():+.2%} (median {e['u2'].median():+.2%}); t bulan non-tumpang tindih {t_rata(m3):+.2f} ({len(m3)} bln)")
print(f"   info lanjutan d0 -> d+1 (tak bisa dibeli): {e['lanjut1'].mean():+.2%} (median {e['lanjut1'].median():+.2%})")
hasil = {"U1": t_rata(m["u1"]), "U2": t_rata(m3)}
lolos = [k for k, v in hasil.items() if abs(v) > 3]
print(f"\n   KEPUTUSAN #60 (|t| > 3): {'✅ ' + ', '.join(lolos) if lolos else '❌ tidak ada yang lolos'}")
