"""
RISET #55: KEPEKAAN SAHAM terhadap ARUS ASING di SBN (PENAMPANG, mingguan) -> saham IDX minggu depan, data LATIH saja
=================================================================================================================
DUGAAN (ditulis 26 Nov 2026 SEBELUM hubungan beta-asing dgn return saham dihitung; di-commit sebelum dijalankan)
#54 (timing 1 keranjang) gagal, tetapi cek kewajaran menunjukkan arus asing SBN minggu w <-> keranjang minggu w (t +3,35).
Desain timing 1 keranjang = breadth ~1 (Grinold-Kahn). Versi PENAMPANG: dana asing yang keluar/masuk Indonesia tidak menjual/membeli
semua saham sama rata -> saham yang secara historis PALING PEKA terhadap arus asing SBN (biasanya saham besar milik asing) mungkin
menyesuaikan diri lebih lambat dari arus obligasi (dana saham asing menyusul dana obligasi; journal.ipb.ac.id abq 74168; Froot-
O'Connell-Seasholes 2001: arus asing persisten & memprediksi return). Bantahan: info makro yang jelas diserap IDX di minggu yang
sama (#1-#4, #54). Perkiraan jujur: |t| < 2. Dua arah.

DATA: raw/kepemilikan_sbn/harian.parquet (non_residen & total, jenis TOTAL, harian sejak 2014). Jeda terbit konservatif 7 hari.
  G(v) = [A(Jumat v) - A(Jumat v-1)] / SBN total(Jumat v-1) x 100 (arus 1 minggu, % SBN beredar), dibatasi +-3; diketahui Jumat v+1.
  F(w) = sinyal #54 = arus 4 minggu [A(Jumat w - 7 hr) - A(Jumat w - 35 hr)] / total(Jumat w - 35 hr) x 100, dibatasi +-3.
BETA saham i di akhir minggu w: kemiringan r_i(v) (return tutup Jumat ke Jumat) terhadap G(v), v = w-52 .. w-1 (G(w-1) baru
  diketahui Jumat w -> pas), minimal 40 minggu. Harga = Adj Close Yahoo, dibersihkan bersih_idx (latih & uji terpisah).
SEMESTA (akhir minggu w): saringan riset #14/#2 (harga >= Rp100, median nilai 60 hr >= Rp1 M, >= 80% hari aktif, tanpa lompatan > 50%).
TARGET: return minggu w+1 (beli tutup hari bursa pertama w+1, jual tutup hari bursa pertama w+2), sama dgn riset #14.
UJI (3; |t| > 3; dua arah):
  U1 IC searah arus: rata-rata tanda(F(w)) x korelasi peringkat(beta_i, r_i minggu w+1), t biasa antar minggu.
  U2 kemiringan: IC(beta, r w+1) diregresikan pada F(w) (memakai besar arus), t robust White.
  U3 beli-saja 20% skor (beta x F) TERTINGGI - semesta, BERSIH 0,4% x porsi diganti (diduga gagal: perputaran mingguan).
Info: IC minggu YANG SAMA dgn tanda(G(w)) (cek kewajaran beta: harus positif bila beta bermakna), paruh waktu.
Latih: minggu target berakhir <= 2018-12-31 (~2015-02 .. 2018-12, ~200 minggu). Data uji 2019+ DIKUNCI.
Uji kode: --tes-tiruan (beta palsu tetap per saham + pola minggu depan 0,5% x beta x F) & --tes-kosong; --potong-data -> IDENTIK.
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BATAS = pd.Timestamp("2018-12-31")
TES_TIRUAN, TES_KOSONG = "--tes-tiruan" in sys.argv, "--tes-kosong" in sys.argv
POTONG = "--potong-data" in sys.argv
POLA = float(os.environ.get("POLA_55", "0.005"))
BIAYA, P = 0.004, "W-FRI"
MIN_HARGA, MIN_NILAI, MIN_HARI_AKTIF, MAX_LOMPAT, MIN_SAHAM = 100, 1e9, 0.8, 0.5, 20


def jadi_tanggal(x):
    t = pd.DatetimeIndex(pd.to_datetime(x))
    if t.tz is not None:
        t = t.tz_localize(None)
    return t.normalize().astype("datetime64[ns]")


def nilai_t(s):
    s = pd.Series(s).dropna()
    return s.mean() / (s.std(ddof=1) / np.sqrt(len(s))) if len(s) > 2 else np.nan


def t_robust(y, x):
    d = pd.concat([y, x], axis=1).dropna()
    yy, xx = d.iloc[:, 0].values, d.iloc[:, 1].values
    xc = xx - xx.mean()
    b = (xc * (yy - yy.mean())).sum() / (xc ** 2).sum()
    e = yy - yy.mean() - b * xc
    return b, b / (np.sqrt((xc ** 2 * e ** 2).sum()) / (xc ** 2).sum()), len(d)


# ---- arus asing SBN
k = pd.read_parquet("data/raw/kepemilikan_sbn/harian.parquet")
k["tanggal"] = jadi_tanggal(k["tanggal"])
if POTONG:
    k = k[k["tanggal"] <= BATAS]


def seri(kat):
    x = k[(k["kategori"] == kat) & (k["jenis"] == "TOTAL") & (k["tanggal"] >= "2014-01-01")].set_index("tanggal")["nilai"].sort_index()
    return x[~x.index.duplicated(keep="last")]


nr, tot = seri("non_residen"), seri("total")
kal_f = pd.period_range("2014-01-10", "2026-11-27", freq=P)


def nilai_pada(s, t, maks_basi=7):
    x = s[:t]
    return x.iloc[-1] if len(x) and (t - x.index[-1]).days <= maks_basi else np.nan


G, F = {}, {}
for v in kal_f:
    f = v.end_time.normalize()
    a1, a0, t0 = nilai_pada(nr, f), nilai_pada(nr, f - pd.Timedelta(days=7)), nilai_pada(tot, f - pd.Timedelta(days=7))
    G[v] = (a1 - a0) / t0 * 100
    b1, b0, u0 = nilai_pada(nr, f - pd.Timedelta(days=7)), nilai_pada(nr, f - pd.Timedelta(days=35)), nilai_pada(tot, f - pd.Timedelta(days=35))
    F[v] = (b1 - b0) / u0 * 100
G, F = pd.Series(G).clip(-3, 3), pd.Series(F).clip(-3, 3)
# G(v) baru diketahui Jumat v+1 -> hanya minggu yang Jumat+7-nya sudah lewat data terakhir
G = G[[(v.end_time.normalize() + pd.Timedelta(days=7)) <= nr.index.max() + pd.Timedelta(days=7) for v in G.index]]

# ---- harga
if TES_TIRUAN or TES_KOSONG:
    acak = np.random.default_rng(55)
    hari = pd.bdate_range("2013-01-01", "2026-11-13").astype("datetime64[ns]")
    kolom = [f"S{i:03d}" for i in range(120)]
    beta_benar = pd.Series(acak.normal(0, 1, 120), index=kolom)
    mg = hari.to_period(P)
    g_hari = G.reindex(mg).fillna(0).values / 5                         # arus minggu yang sama, dibagi 5 hari
    harian = acak.normal(0, 0.02, (len(hari), 120)) + 0.01 * np.outer(g_hari, beta_benar.values)
    if TES_TIRUAN:                                                      # minggu depan: +POLA x beta x F(minggu lalu)
        f_lalu = F.reindex(mg - 1).fillna(0).values / 5
        harian = harian + POLA * np.outer(f_lalu, beta_benar.values)
    adj = pd.DataFrame(1000 * np.exp(np.cumsum(harian, axis=0)), index=hari, columns=kolom)
    tutup, volume = adj.copy(), pd.DataFrame(1e7, index=hari, columns=kolom)
    print(f"🧪 MODE TES: harga PALSU, beta tetap per saham, {'pola minggu depan ' + format(POLA, '.3f') if TES_TIRUAN else 'TANPA pola minggu depan'}")
else:
    adj, tutup, volume = {}, {}, {}
    for f in sorted(Path("data/raw/harga_idx").glob("*.parquet")):
        d = pd.read_parquet(f, columns=["Adj Close", "Close", "Volume"])
        d.index = jadi_tanggal(d.index)
        d = d[~d.index.duplicated(keep="last")]
        adj[f.stem], tutup[f.stem], volume[f.stem] = d["Adj Close"], d["Close"], d["Volume"]
    adj, tutup, volume = (pd.DataFrame(x).sort_index() for x in (adj, tutup, volume))
    if POTONG:
        adj, tutup, volume = (x[x.index <= BATAS] for x in (adj, tutup, volume))
    from bersih_idx import bersihkan
    adj2 = bersihkan(adj)
    rusak = adj2.isna() & adj.notna()
    print(f"🧹 {int(rusak.values.sum())} titik rusak dikosongkan")
    adj, tutup = adj2, tutup.mask(rusak)
    aktif0 = volume.fillna(0) > 0
    hb = aktif0.index[(aktif0.sum(axis=1) >= 10) & (aktif0.index.day_of_week < 5)]
    adj, tutup, volume = (x.loc[hb] for x in (adj, tutup, volume))
hari = adj.index
aktif = volume.fillna(0) > 0
median_nilai = (tutup * volume).where(aktif).rolling(60, min_periods=40).median()
porsi_aktif = aktif.rolling(250, min_periods=250).mean()
lompat = adj.pct_change(fill_method=None).abs().rolling(250, min_periods=200).max()
lolos_h = (tutup >= MIN_HARGA) & (median_nilai >= MIN_NILAI) & (porsi_aktif >= MIN_HARI_AKTIF) & (lompat < MAX_LOMPAT)

kal = pd.period_range(hari.min().to_period(P), hari.max().to_period(P), freq=P)
gm = pd.Series(hari, index=hari).groupby(hari.to_period(P))
awal, akhir = gm.min().reindex(kal), gm.max().reindex(kal)
harga_awal = adj.reindex(awal.values).set_axis(kal)
harga_akhir = adj.reindex(akhir.values).set_axis(kal)
ret_depan = harga_awal.shift(-2) / harga_awal.shift(-1) - 1           # beli awal w+1, jual awal w+2
jual = awal.shift(-2)
r_mg = harga_akhir / harga_akhir.shift(1) - 1                          # return minggu v (Jumat ke Jumat)
lolos_m = lolos_h.reindex(akhir.values).set_axis(kal).fillna(False)

# ---- beta bergulir 52 minggu (v = w-52 .. w-1)
g = G.reindex(kal)
gm_ = pd.DataFrame(np.outer(g.values, np.ones(r_mg.shape[1])), index=kal, columns=r_mg.columns).where(r_mg.notna())
r_ = r_mg.where(gm_.notna())
roll = lambda x: x.rolling(52, min_periods=40).mean()
cov = roll(r_ * gm_) - roll(r_) * roll(gm_)
var = roll(gm_ ** 2) - roll(gm_) ** 2
beta = (cov / var).shift(1)                                            # pakai s/d w-1

pilih = (jual <= BATAS).fillna(False)
print(f"🔒 Data uji 2019+ DIKUNCI. Sinyal F: {F[F.index <= pd.Period('2018-12-28', freq=P)].notna().sum()} minggu latih.\n")
baris, lalu = [], set()
for w in kal[pilih.values]:
    if pd.isna(F.get(w, np.nan)) or F[w] == 0:
        continue
    b = beta.loc[w]
    r = ret_depan.loc[w]
    ok = lolos_m.loc[w] & b.notna() & r.notna()
    if ok.sum() < MIN_SAHAM:
        continue
    b, r = b[ok], r[ok]
    ic = b.rank().corr(r.rank())
    skor = b * F[w]
    atas = set(skor.index[pd.qcut(skor.rank(method="first"), 5, labels=False) == 4])
    ganti = 1 - len(atas & lalu) / len(atas) if lalu else 1.0
    rs = r_mg.shift(-0).loc[w]                                          # info: minggu yang SAMA (w) vs G(w)
    ok2 = ok & rs.reindex(ok.index).notna()
    ic_sama = np.sign(g.get(w, np.nan)) * beta.loc[w][ok2].rank().corr(rs[ok2].rank()) if ok2.sum() >= MIN_SAHAM else np.nan
    baris.append({"minggu": w, "n": int(ok.sum()), "F": F[w], "ic": ic, "ic_arah": np.sign(F[w]) * ic, "ic_sama": ic_sama,
                  "bersih": r[list(atas)].mean() - ganti * BIAYA - r.mean(), "kotor": r[list(atas)].mean() - r.mean(), "ganti": ganti})
    lalu = atas
d = pd.DataFrame(baris).set_index("minggu")
print(f"Mingguan: {len(d)} minggu ({d.index[0]} s/d {d.index[-1]}), semesta median {d['n'].median():.0f} saham")
print(f"   info cek beta (minggu SAMA, tanda G(w)) : IC {d['ic_sama'].mean():+.3f} t {nilai_t(d['ic_sama']):+.2f}")
t1 = nilai_t(d["ic_arah"])
b2, t2, n2 = t_robust(d["ic"], d["F"])
t3 = nilai_t(d["bersih"])
h = len(d) // 2
print(f"   U1 IC searah arus     : {d['ic_arah'].mean():+.4f}  t {t1:+.2f}  (paruh {nilai_t(d['ic_arah'].iloc[:h]):+.1f}/{nilai_t(d['ic_arah'].iloc[h:]):+.1f})")
print(f"   U2 IC ~ F (kemiringan): {b2:+.4f} per +1%  t robust {t2:+.2f}  ({n2} mg)")
print(f"   U3 beli 20% skor      : kotor {d['kotor'].mean():+.3%}/mg, BERSIH {d['bersih'].mean():+.3%}/mg  t {t3:+.2f}  (ganti {d['ganti'].iloc[1:].mean():.0%}/mg)")
hasil = {"U1": t1, "U2": t2, "U3": t3}
lolos = [n for n, t in hasil.items() if abs(t) > 3]
print(f"\n   KEPUTUSAN #55 (|t| > 3): {'✅ ' + ', '.join(lolos) if lolos else '❌ tidak ada yang lolos'}")
if "--simpan" in sys.argv:
    d.to_parquet("data/olah/riset55_latih.parquet")
