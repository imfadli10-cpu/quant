"""
RISET #47: DIVIDEND YIELD (value) -> saham IDX bulan depan
==========================================================
DUGAAN (ditulis 2026-11-21 SEBELUM melihat return; di-commit sebelum dijalankan)
Value = saham "murah" relatif terhadap fundamentalnya mengungguli saham "mahal". Rouwenhorst (1999 JF, "Local return factors and turnover
in emerging stock markets"): premi value, momentum & ukuran ada di 20 pasar berkembang TERMASUK Indonesia; Fama-French (2012 JFE): premi
value internasional; Hanauer-Lauterbach (2019 EMR): value kuat di pasar berkembang. Rasio buku/harga historis IDX TIDAK tersedia (Yahoo
hanya ~6 kuartal) -> proksi value = DIVIDEND YIELD 12 bulan dari raw/aksi_idx (dividen sejak 2000). Alasan logis IDX: investor ritel
mengejar saham "cerita"/lotre, saham pembagi dividen besar & membosankan cenderung terlalu murah. Kelebihan praktis: sinyal berubah lambat
-> perputaran RENDAH (masalah utama IDX = biaya, riset #36-#39, #46).
DUGAAN: saham dengan dividend yield tinggi mengungguli semesta bulan depan.

SINYAL akhir bulan t: DY = jumlah dividen (Rp/lembar, tanggal EX di (t-365 hari, t]) / Close Yahoo (disesuaikan split, sama seperti dividen
  Yahoo) pada t. DY > 0,30 dianggap salah data -> dikosongkan. Saham tanpa dividen di jendela -> DY = 0.
  KETERBATASAN (diakui di depan): cakupan dividen Yahoo awal tidak lengkap (74 kode 2003 -> 230 2018) -> sebagian pembagi dividen tampak 0
  -> sinyal TERENCERKAN (bias ke arah nol, bukan ke arah positif). Survivorship IDX tetap ada.
KERANGKA riset #13: semesta S2 `lolos`, masuk tutup hari bursa pertama t+1, tahan 1 bulan, bobot sama, bulan >= 30 saham.
UJI:
  U1 (info) IC Spearman DY vs return bulan depan (semua saham semesta, DY 0 ikut).
  U2 (PENENTU, satu ukuran): beli 20% DY tertinggi (urut DY, seri diputus acak-tetap via rank 'first') - rata-rata semesta, dikurangi biaya B
     (0,4% + 1,2 x tick historis/harga asli) x perputaran (porsi saham baru). LOLOS bila t > 3.
  Info: pembagi dividen - bukan pembagi; K5 - K1 di antara pembagi saja; paruh waktu.
LATIH: bulan sinyal yang tanggal JUAL <= 2018-12-31. UJI 2019+ DIKUNCI (--buka-uji sekali, hanya bila latih lolos).
Daya uji (dicek dgn return palsu SEBELUM commit): premi +1,5%/bln -> kotor +1,31%, bersih t +5,7; tanpa pola bersih -0,16% t -0,9
  (= biaya). Perputaran 21%/bln, biaya 0,27%/bln -> premi bersih ~+0,6%/bln kira-kira cukup untuk t > 3.
Uji kode: --tes-tiruan (return palsu + premi +1,5%/bln untuk 20% DY teratas) & --tes-kosong; --potong-data (dipotong di 2018-12-31).
"""
import contextlib
import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(".").resolve()))
from biaya_idx import tabel_tick_historis

BUKA_DATA_UJI = "--buka-uji" in sys.argv
TES_TIRUAN, TES_KOSONG = "--tes-tiruan" in sys.argv, "--tes-kosong" in sys.argv
POTONG = "--potong-data" in sys.argv
BATAS = pd.Timestamp("2018-12-31")

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


kode13 = Path("riset_13_s2_hemat.py").read_text(encoding="utf-8").split("def simulasi(varian):")[0]
g = {"__file__": "riset_13_s2_hemat.py"}
simpan, sys.argv = sys.argv, [sys.argv[0]]
with contextlib.redirect_stdout(io.StringIO()):
    exec(compile(kode13, "riset_13_bagian", "exec"), g)
sys.argv = simpan
gg = g["g"]
akhir_bulan, lolos, ret_pegang = g["akhir_bulan"], g["lolos"], g["ret_pegang"].copy()
tutup = gg["tutup"]
tgl_jual = pd.Series(gg["awal_bulan"]).shift(-2).reset_index(drop=True)
tgl_beli = pd.Series(gg["awal_bulan"]).shift(-1).reset_index(drop=True)
if POTONG:
    print(f"   (cek potong: harga terakhir {gg['adj'].index.max():%Y-%m-%d})")
aksi = pd.read_parquet("data/raw/aksi_idx/semua.parquet")
tick = tabel_tick_historis(tutup, aksi)
biaya_rt = (0.004 + 1.2 * tick.loc[akhir_bulan]).reset_index(drop=True)

div = aksi[aksi["dividen"] > 0][["kode", "tanggal", "dividen"]]
div = div[div["kode"].isin(tutup.columns)]
harian = div.pivot_table(index="tanggal", columns="kode", values="dividen", aggfunc="sum")
harian = harian.reindex(columns=tutup.columns)
idx_gab = harian.index.union(tutup.index)
kum = harian.reindex(idx_gab).fillna(0).cumsum()          # dividen kumulatif per saham


def dy_bulan(t):
    k1 = kum.loc[:t].iloc[-1]
    sebelum = kum.loc[:t - pd.Timedelta(days=365)]
    k0 = sebelum.iloc[-1] if len(sebelum) else 0 * k1
    d = (k1 - k0) / tutup.loc[t]
    return d.where(d <= 0.30)


if TES_TIRUAN or TES_KOSONG:
    acak = np.random.default_rng(47)
    ret_pegang = pd.DataFrame(acak.normal(0, 0.10, ret_pegang.shape), index=ret_pegang.index,
                              columns=ret_pegang.columns).where(ret_pegang.notna())
    print(f"🧪 MODE TES: return PALSU {'dengan premi +1,5%/bln untuk 20% DY teratas' if TES_TIRUAN else 'tanpa pola'}")

baris, pilih_lalu = [], set()
for i, t in enumerate(akhir_bulan):
    if pd.isna(tgl_jual.iloc[i]):
        continue
    if BUKA_DATA_UJI:
        if tgl_beli.iloc[i] < pd.Timestamp("2019-01-01"):
            continue
    elif tgl_jual.iloc[i] > BATAS:
        continue
    dy = dy_bulan(t)
    ok = lolos.loc[i] & ret_pegang.loc[i].notna() & dy.notna()
    if ok.sum() < 30:
        pilih_lalu = set()
        continue
    s, r = dy[ok], ret_pegang.loc[i][ok].copy()
    k = pd.qcut(s.rank(method="first"), 5, labels=False)
    if TES_TIRUAN:
        r[k == 4] += 0.015
    atas = set(s.index[k == 4])
    putar = 1.0 if not pilih_lalu else len(atas - pilih_lalu) / len(atas)
    biaya = putar * biaya_rt.loc[i, list(atas)].fillna(0.012).mean()
    pilih_lalu = atas
    rata = r.mean()
    bayar = s > 0
    sp = s[bayar]
    k5k1 = np.nan
    if bayar.sum() >= 25:
        kp = pd.qcut(sp.rank(method="first"), 5, labels=False)
        k5k1 = r[sp.index[kp == 4]].mean() - r[sp.index[kp == 0]].mean()
    baris.append({"t": t, "n": ok.sum(), "n_bayar": bayar.sum(), "dy_atas": s[k == 4].median(),
                  "ic": s.rank().corr(r.rank()), "putar": putar, "biaya": biaya,
                  "kotor": r[k == 4].mean() - rata, "bersih": r[k == 4].mean() - rata - biaya,
                  "bayar_vs_tidak": r[bayar].mean() - r[~bayar].mean() if (~bayar).sum() >= 5 else np.nan, "k5k1_bayar": k5k1})
h = pd.DataFrame(baris).set_index("t")
print(f"🔒 Data uji (2019+) {'DIBUKA' if BUKA_DATA_UJI else 'DIKUNCI'}.\n")
p = len(h) // 2
print(f"   {len(h)} bulan ({h.index.min():%Y-%m} s/d {h.index.max():%Y-%m}), median {h['n'].median():.0f} saham, "
      f"{h['n_bayar'].median():.0f} pembagi dividen; DY median kelompok atas {h['dy_atas'].median():.1%}")
print(f"   U1 IC {h['ic'].mean():+.3f}, t {t_rata(h['ic']):+.2f} (paruh {t_rata(h['ic'].iloc[:p]):+.1f} / {t_rata(h['ic'].iloc[p:]):+.1f})")
print(f"   pembagi - bukan pembagi: {h['bayar_vs_tidak'].mean():+.2%}/bln t {t_rata(h['bayar_vs_tidak']):+.2f} | "
      f"K5-K1 di antara pembagi: {h['k5k1_bayar'].mean():+.2%} t {t_rata(h['k5k1_bayar']):+.2f}")
print(f"   20% DY teratas - semesta: kotor {h['kotor'].mean():+.2%} | putar {h['putar'].iloc[1:].mean():.0%} | biaya {h['biaya'].mean():.2%}")
print(f"   U2 BERSIH (PENENTU, t > 3): {h['bersih'].mean():+.2%}/bln, t {t_rata(h['bersih']):+.2f} "
      f"(paruh {t_rata(h['bersih'].iloc[:p]):+.1f} / {t_rata(h['bersih'].iloc[p:]):+.1f})")
tu = t_rata(h["bersih"])
print(f"\n   KEPUTUSAN #47 (U2 t > 3): {tu:+.2f} -> {'✅ lolos latih' if tu > 3 else '❌ tidak lolos'}")
