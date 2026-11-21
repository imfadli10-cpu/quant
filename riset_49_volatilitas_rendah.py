"""
RISET #49: STRATEGI VOLATILITAS RENDAH long-only (S3 sendiri) -> saham IDX, dinilai dengan ALPHA setelah beta
==========================================================================================================
DUGAAN (ditulis 2026-11-21 SEBELUM melihat return strategi ini; di-commit sebelum dijalankan)
"Low-volatility anomaly": saham paling tenang memberi return per risiko lebih tinggi dari yang diprediksi CAPM. Blitz & van Vliet (2007 JPM);
Blitz, Pang & van Vliet (2013 EMR, "The volatility effect in emerging markets": efek KUAT di pasar berkembang); Frazzini & Pedersen (2014 JFE,
betting against beta, 20 negara); Ang dkk. (2006/2009 JF). Alasan logis: investor (terutama ritel IDX) menyukai saham bergejolak/lotre & dana
terbatas leverage -> saham tenang kurang diminati -> terlalu murah per unit risiko. Di riset #12, S3 (vol 120 hari rendah) IC t 4,4 sebagai
peringkat, tapi TIDAK pernah diuji sebagai strategi sendiri. Kelebihan praktis: volatilitas sangat persisten -> perputaran rendah; saham tenang
cenderung likuid -> tick/harga kecil -> biaya rendah.
PENTING: saham tenang ber-beta < 1 -> return mentah vs semesta MENYESATKAN (di pasar naik pasti tertinggal). Ukuran = ALPHA CAPM terhadap semesta.

STRATEGI: akhir bulan t, P = 20% saham semesta S2 (`lolos`, kerangka #13) dengan S3 tertinggi (= simpangan baku return harian 120 hari
  TERENDAH), bobot sama, masuk tutup hari bursa pertama t+1, tahan 1 bulan. Biaya B (0,4% + 1,2 x tick historis/harga asli) x perputaran.
  rf = suku bunga jangka pendek Indonesia FRED IRSTCI01IDM156N (% per tahun / 12) bulan pegang. U = rata-rata semesta bobot sama.
UJI:
  U1 (PENENTU, satu ukuran): regresi (P_bersih - rf) = a + b (U - rf), t untuk a dgn galat baku White (HC0). LOLOS bila t(a) > 3.
  Info: beta b, selisih mentah bersih P - U, Sharpe P vs U (tahunan, bersih), perputaran & biaya, paruh waktu, alpha versi kotor.
LATIH: bulan sinyal yang tanggal JUAL <= 2018-12-31. UJI 2019+ DIKUNCI (--buka-uji sekali, hanya bila latih lolos).
Daya uji (return palsu, dicek SEBELUM commit): alpha +1%/bln -> kotor +0,89% t 6,0, BERSIH +0,58% t 3,9; tanpa alpha: bersih -0,21% t -1,4
  (= biaya). Perputaran 24%/bln, biaya 0,31%/bln -> butuh alpha kotor ~+0,8-1%/bln untuk lolos.
Uji kode: --tes-tiruan (return palsu faktor pasar + beta acak + alpha +1%/bln utk P) & --tes-kosong (beta acak, tanpa alpha);
  --potong-data (semua file dipotong di 2018-12-31 -> harus IDENTIK, kecuali biaya beda tipis karena harga_asli; lihat #46).
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


def alpha_white(y, x):
    """OLS y = a + b x, galat baku White HC0. Hasil (a, b, t_a)."""
    X = np.column_stack([np.ones(len(x)), x])
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    e = y - X @ beta
    XtX = np.linalg.inv(X.T @ X)
    V = XtX @ (X.T * e ** 2) @ X @ XtX
    return beta[0], beta[1], beta[0] / np.sqrt(V[0, 0])


kode13 = Path("riset_13_s2_hemat.py").read_text(encoding="utf-8").split("def simulasi(varian):")[0]
g = {"__file__": "riset_13_s2_hemat.py"}
simpan, sys.argv = sys.argv, [sys.argv[0]]
with contextlib.redirect_stdout(io.StringIO()):
    exec(compile(kode13, "riset_13_bagian", "exec"), g)
sys.argv = simpan
gg = g["g"]
akhir_bulan, lolos, ret_pegang, sinyal = g["akhir_bulan"], g["lolos"], g["ret_pegang"].copy(), g["sinyal"]
tgl_jual = pd.Series(gg["awal_bulan"]).shift(-2).reset_index(drop=True)
tgl_beli = pd.Series(gg["awal_bulan"]).shift(-1).reset_index(drop=True)
if POTONG:
    print(f"   (cek potong: harga terakhir {gg['adj'].index.max():%Y-%m-%d})")
tick = tabel_tick_historis(gg["tutup"], pd.read_parquet("data/raw/aksi_idx/semua.parquet"))
biaya_rt = (0.004 + 1.2 * tick.loc[akhir_bulan]).reset_index(drop=True)
bunga = pd.read_parquet("data/raw/makro/IRSTCI01IDM156N.parquet")["nilai"]
bunga.index = pd.to_datetime(bunga.index).to_period("M")

if TES_TIRUAN or TES_KOSONG:
    acak = np.random.default_rng(49)
    pasar = acak.normal(0.01, 0.06, len(ret_pegang))
    b_saham = acak.uniform(0.4, 1.4, ret_pegang.shape[1])
    palsu = pasar[:, None] * b_saham[None, :] + acak.normal(0, 0.08, ret_pegang.shape)
    ret_pegang = pd.DataFrame(palsu, index=ret_pegang.index, columns=ret_pegang.columns).where(ret_pegang.notna())
    print(f"🧪 MODE TES: return PALSU (faktor pasar, beta acak) {'+ alpha +1%/bln untuk P' if TES_TIRUAN else 'tanpa alpha'}")

baris, pilih_lalu = [], set()
for i, t in enumerate(akhir_bulan):
    if pd.isna(tgl_jual.iloc[i]):
        continue
    if BUKA_DATA_UJI:
        if tgl_beli.iloc[i] < pd.Timestamp("2019-01-01"):
            continue
    elif tgl_jual.iloc[i] > BATAS:
        continue
    s3 = sinyal["S3"].loc[i]
    ok = lolos.loc[i] & ret_pegang.loc[i].notna() & s3.notna()
    if ok.sum() < 30:
        pilih_lalu = set()
        continue
    s, r = s3[ok], ret_pegang.loc[i][ok].copy()
    k = pd.qcut(s.rank(method="first"), 5, labels=False)
    if TES_TIRUAN:
        r[k == 4] += 0.01
    P = set(s.index[k == 4])
    putar = 1.0 if not pilih_lalu else len(P - pilih_lalu) / len(P)
    biaya = putar * biaya_rt.loc[i, list(P)].fillna(0.012).mean()
    pilih_lalu = P
    bulan_pegang = (t.to_period("M") + 1)
    rf = bunga.get(bulan_pegang, np.nan) / 1200
    baris.append({"t": t, "n": ok.sum(), "putar": putar, "biaya": biaya, "rf": rf,
                  "P_kotor": r[k == 4].mean(), "P_bersih": r[k == 4].mean() - biaya, "U": r.mean()})
h = pd.DataFrame(baris).set_index("t")
if h["rf"].isna().any():
    print(f"   ⚠️ rf kosong {h['rf'].isna().sum()} bulan -> diisi nilai terakhir")
    h["rf"] = h["rf"].ffill()
print(f"🔒 Data uji (2019+) {'DIBUKA' if BUKA_DATA_UJI else 'DIKUNCI'}.\n")
p = len(h) // 2


def nilai(d):
    a, b, ta = alpha_white((d["P_bersih"] - d["rf"]).values, (d["U"] - d["rf"]).values)
    return a, b, ta


a, b, ta = nilai(h)
ak, _, tak = alpha_white((h["P_kotor"] - h["rf"]).values, (h["U"] - h["rf"]).values)
sh = lambda x: (x - h["rf"]).mean() / (x - h["rf"]).std() * np.sqrt(12)
print(f"   {len(h)} bulan ({h.index.min():%Y-%m} s/d {h.index.max():%Y-%m}), median {h['n'].median():.0f} saham; "
      f"putar {h['putar'].iloc[1:].mean():.0%}, biaya {h['biaya'].mean():.2%}/bln; rf rata {h['rf'].mean() * 12:.1%}/thn")
print(f"   mentah: P bersih {h['P_bersih'].mean():+.2%}/bln vs semesta {h['U'].mean():+.2%} (selisih t {t_rata(h['P_bersih'] - h['U']):+.2f}); "
      f"Sharpe P {sh(h['P_bersih']):.2f} vs semesta {sh(h['U']):.2f}")
print(f"   alpha KOTOR {ak:+.2%}/bln t {tak:+.2f}")
print(f"   U1 ALPHA BERSIH (PENENTU, t > 3): {a:+.2%}/bln, beta {b:.2f}, t {ta:+.2f} "
      f"(paruh {nilai(h.iloc[:p])[2]:+.1f} / {nilai(h.iloc[p:])[2]:+.1f})")
if BUKA_DATA_UJI:
    print("   per tahun (P bersih - semesta): " + " | ".join(f"{y} {v:+.2%}" for y, v in (h["P_bersih"] - h["U"]).groupby(h.index.year).mean().items()))
print(f"\n   KEPUTUSAN #49 (alpha bersih t > 3): {ta:+.2f} -> {'✅ lolos latih' if ta > 3 else '❌ tidak lolos'}")
