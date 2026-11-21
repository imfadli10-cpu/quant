"""
RISET #46: MUSIMAN PENAMPANG ("return seasonality") -> saham IDX bulan depan
==========================================================================
DUGAAN (ditulis 2026-11-21 SEBELUM melihat return; di-commit sebelum dijalankan)
Heston & Sadka (2008 JFE): return saham di bulan kalender yang SAMA pada tahun-tahun sebelumnya memprediksi return bulan itu
(jeda 12, 24, ..., 240 bulan; efek tidak meluruh selama 20 tahun). Heston & Sadka (2010 JFQA): ada di 14 negara di luar AS.
Keloharju, Linnainmaa & Nyberg (2016 JF "Return Seasonalities"): musiman muncul di saham, industri, faktor, komoditas & negara ->
penjelasan: premi risiko yang berubah per musim (bukan salah harga sederhana). Alasan IDX: dividen & RUPS musiman (Mei-Jul), window dressing
akhir tahun, Lebaran, laporan keuangan kuartalan -> pola per emiten yang berulang tiap tahun.
DUGAAN: saham dengan rata-rata return bulan kalender yang sama (tahun-tahun lalu) tinggi akan mengungguli bulan depan.

SINYAL akhir bulan i (untuk bulan pegang i+1): rata-rata ret_pegang[i - 12k], k = 1..10 (bulan kalender pegang yang SAMA di 1-10 tahun
  sebelumnya), minimal 4 tahun terisi. ret_pegang[i-12] berakhir ~11 bulan sebelum sinyal -> tanpa informasi masa depan.
KERANGKA riset #13 (= #2): semesta S2 `lolos`, masuk tutup hari bursa pertama bulan i+1, tahan 1 bulan, bobot sama, bulan >= 30 saham.
UJI:
  U1 (info) IC Spearman sinyal vs return bulan depan, t antar bulan.
  U2 (PENENTU, satu ukuran): beli 20% teratas - rata-rata semesta, dikurangi biaya B (0,4% + 1,2 x tick historis/harga asli) x
     perputaran (porsi saham baru). LOLOS bila t > 3.
  Info: K5 - K1 kotor (butuh short, diagnosis), paruh waktu.
LATIH: bulan sinyal yang tanggal JUAL <= 2018-12-31 (sinyal 2004-2018 sesuai ketersediaan 4 tahun). UJI 2019+ DIKUNCI.
  (Catatan: data uji S2 sudah terpakai, tapi ini sinyal LAIN; uji 2019+ hanya dibuka sekali kalau latih lolos.)
DAYA UJI (dicek dgn return palsu SEBELUM commit): pola musiman per saham sb 2% -> IC t +9,2 tapi U2 bersih t +0,5 (perputaran 81%/bln,
  biaya ~1%/bln) -> sebagai STRATEGI tunggal hampir pasti gagal. Maka KEPUTUSAN KEDUA (ditetapkan sekarang, sebelum data asli):
  U1 IC t > 3 -> KANDIDAT FITUR model penampang ML (bukan strategi). Tanpa pola: IC t +0,6, U2 t -5,7 (= biaya murni).
Daya uji & kode: --tes-tiruan (return palsu + komponen musiman per saham per bulan kalender) & --tes-kosong;
  --potong-data (semua file dipotong di 2018-12-31 -> harus IDENTIK).
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
tgl_jual = pd.Series(gg["awal_bulan"]).shift(-2).reset_index(drop=True)
tgl_beli = pd.Series(gg["awal_bulan"]).shift(-1).reset_index(drop=True)
if POTONG:
    print(f"   (cek potong: harga terakhir {gg['adj'].index.max():%Y-%m-%d})")
bl = akhir_bulan.to_period("M")
assert all((bl[i] - bl[i - 1]).n == 1 for i in range(1, len(bl))), "bulan tidak berurutan"
tick = tabel_tick_historis(gg["tutup"], pd.read_parquet("data/raw/aksi_idx/semua.parquet"))
biaya_rt = (0.004 + 1.2 * tick.loc[akhir_bulan]).reset_index(drop=True)

if TES_TIRUAN or TES_KOSONG:
    acak = np.random.default_rng(46)
    palsu = acak.normal(0, 0.10, ret_pegang.shape)
    if TES_TIRUAN:                                   # tiap saham punya pola musiman tetap per bulan kalender (+-2%)
        musim = acak.normal(0, 0.02, (12, ret_pegang.shape[1]))
        palsu += musim[np.array([(p + 1).month - 1 for p in bl])]
    ret_pegang = pd.DataFrame(palsu, index=ret_pegang.index, columns=ret_pegang.columns).where(ret_pegang.notna())
    print(f"🧪 MODE TES: return PALSU {'dengan pola musiman per saham (sb 2%)' if TES_TIRUAN else 'tanpa pola'}")

lalu = [ret_pegang.shift(12 * k) for k in range(1, 11)]
jumlah = sum(x.notna().astype(int) for x in lalu)
sinyal = (sum(x.fillna(0) for x in lalu) / jumlah.replace(0, np.nan)).where(jumlah >= 4)

baris, pilih_lalu = [], set()
for i, t in enumerate(akhir_bulan):
    if pd.isna(tgl_jual.iloc[i]):
        continue
    if BUKA_DATA_UJI:
        if tgl_beli.iloc[i] < pd.Timestamp("2019-01-01"):
            continue
    elif tgl_jual.iloc[i] > BATAS:
        continue
    ok = lolos.loc[i] & ret_pegang.loc[i].notna() & sinyal.loc[i].notna()
    if ok.sum() < 30:
        pilih_lalu = set()
        continue
    s, r = sinyal.loc[i][ok], ret_pegang.loc[i][ok]
    k = pd.qcut(s.rank(method="first"), 5, labels=False)
    atas = set(s.index[k == 4])
    putar = 1.0 if not pilih_lalu else len(atas - pilih_lalu) / len(atas)
    biaya = putar * biaya_rt.loc[i, list(atas)].fillna(0.012).mean()
    pilih_lalu = atas
    rata = r.mean()
    baris.append({"t": t, "n": ok.sum(), "ic": s.rank().corr(r.rank()), "putar": putar, "biaya": biaya,
                  "kotor": r[k == 4].mean() - rata, "bersih": r[k == 4].mean() - rata - biaya,
                  "k5k1": r[k == 4].mean() - r[k == 0].mean()})
h = pd.DataFrame(baris).set_index("t")
print(f"🔒 Data uji (2019+) {'DIBUKA' if BUKA_DATA_UJI else 'DIKUNCI'}.\n")
p = len(h) // 2
print(f"   {len(h)} bulan ({h.index.min():%Y-%m} s/d {h.index.max():%Y-%m}), median {h['n'].median():.0f} saham")
print(f"   U1 IC {h['ic'].mean():+.3f}, t {t_rata(h['ic']):+.2f} (paruh {t_rata(h['ic'].iloc[:p]):+.1f} / {t_rata(h['ic'].iloc[p:]):+.1f})")
print(f"   K5 - K1 kotor (diagnosis): {h['k5k1'].mean():+.2%}/bln, t {t_rata(h['k5k1']):+.2f}")
print(f"   20% teratas - semesta: kotor {h['kotor'].mean():+.2%} | putar {h['putar'].iloc[1:].mean():.0%} | biaya {h['biaya'].mean():.2%}")
print(f"   U2 BERSIH (PENENTU, t > 3): {h['bersih'].mean():+.2%}/bln, t {t_rata(h['bersih']):+.2f} "
      f"(paruh {t_rata(h['bersih'].iloc[:p]):+.1f} / {t_rata(h['bersih'].iloc[p:]):+.1f})")
tu = t_rata(h["bersih"])
print(f"\n   KEPUTUSAN #46 strategi (U2 t > 3): {tu:+.2f} -> {'✅ lolos latih' if tu > 3 else '❌ tidak lolos'}")
ti = t_rata(h["ic"])
print(f"   KEPUTUSAN #46 fitur (U1 IC t > 3): {ti:+.2f} -> {'✅ kandidat fitur model ML' if ti > 3 else '❌ bukan kandidat fitur'}")
