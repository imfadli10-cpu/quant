"""
RISET #53: S2 dengan PENGATURAN PORSI MENURUT VOLATILITAS (volatility-managed, long-only, TANPA utang) -> data LATIH saja
=====================================================================================================================
DUGAAN (ditulis 26 Nov 2026 SEBELUM return strategi ini dilihat; pra-registrasi lengkap: docs/prareg_53_s2_volatilitas.md)
Barroso & Santa-Clara (2015 JFE, "Momentum has its moments"): risiko momentum sangat mudah ditebak (volatilitas 6 bulan lalu),
tetapi return-nya TIDAK naik saat volatilitas tinggi -> memperkecil posisi saat bergejolak menaikkan Sharpe & mengurangi crash.
Moreira & Muir (2017 JF): sama untuk pasar & banyak faktor (uji = alpha portofolio terkelola thd portofolio asli).
Bantahan yang diakui DI DEPAN: Cederburg, O'Doherty, Wang & Yan (2020 JFE): versi luar-sampel (real-time) umumnya TIDAK mengalahkan
portofolio asli; Barroso & Detzel: hanya bekerja saat likuiditas tinggi. S2 long-only -> volatilitasnya sebagian besar volatilitas
PASAR (bukan WML long-short) -> dugaan awal: efek kecil. Alasan tetap diuji: risiko drawdown S2 (2008, Mar-Apr 2009) & modal kecil.

ATURAN (dari paper, tanpa penyetelan; tanpa utang -> porsi dibatasi 1):
  Basis = S2 resmi (kerangka #13: semesta #2, 20% teratas S2 bobot sama, beli tutup hari bursa pertama t+1, tahan 1 bulan).
  sig_hat(t) = simpangan baku return HARIAN portofolio S2 yang BENAR-BENAR dipegang selama 126 hari bursa terakhir s/d t (min 100),
               x akar 250 (BSC: 6 bulan return harian strategi itu sendiri).
  sig_ref(t) = MEDIAN semua sig_hat(tau), tau <= t (berkembang, point-in-time; min 12 nilai, sebelum itu bulan dilewati).
  porsi e(t) = min(1, sig_ref(t) / sig_hat(t)); sisanya (1 - e) di KAS berbunga rf (FRED IRSTCI01IDM156N / 1200, bulan pegang).
  Biaya = sum |w_baru - w_lama| x biaya_B / 2 per saham (biaya B = 0,4% + 1,2 x tick historis / harga asli, seperti #38/#49).
  M(t) = e x R_S2 + (1 - e) x rf - biaya_M ; S(t) = R_S2 - biaya_S (S2 selalu penuh).
UJI PENENTU (SATU): regresi (M - rf) = a + b (S - rf), galat White HC0 -> LOLOS bila t(a) > 3 (Moreira-Muir).
  Info: Sharpe M vs S, drawdown maksimum, porsi rata-rata, 6 bulan terburuk, paruh waktu, versi rf = 0 (kas menganggur di RDN),
  versi sig_hat dari SEMESTA (bukan S2), versi varians 21 hari (Moreira-Muir, e = min(1, var_ref/var_hat)).
KEPUTUSAN: lolos -> portofolio paper trading baru `s2vol` (aturan dibekukan). Gagal -> "belum terbukti", S2 resmi TIDAK diubah.
DATA UJI 2019+ TIDAK dibuka (S2 sudah memakainya); versi baru hanya dinilai lewat paper trading.
Uji kode: --tes-kosong (return harian palsu, volatilitas acak TANPA kelompok -> alpha ~0) & --tes-tiruan (volatilitas
  BERKELOMPOK, rata-rata tetap -> alpha > 0 harus terdeteksi = ukuran DAYA UJI); --potong-data (file dipotong 2018-12-31 -> IDENTIK).
"""
import contextlib
import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(".").resolve()))
from biaya_idx import tabel_tick_historis

TES_TIRUAN, TES_KOSONG = "--tes-tiruan" in sys.argv, "--tes-kosong" in sys.argv
POTONG = "--potong-data" in sys.argv
BATAS = pd.Timestamp("2018-12-31")
JENDELA, MIN_HARI, MIN_REF = 126, 100, 12

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


def alpha_white(y, x):
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
awal_bulan = pd.DatetimeIndex(gg["awal_bulan"])
adj = gg["adj"]
tgl_jual = pd.Series(awal_bulan).shift(-2).reset_index(drop=True)
if POTONG:
    print(f"   (cek potong: harga terakhir {adj.index.max():%Y-%m-%d})")
tick = tabel_tick_historis(gg["tutup"], pd.read_parquet("data/raw/aksi_idx/semua.parquet"))
biaya_rt = (0.004 + 1.2 * tick.loc[akhir_bulan]).reset_index(drop=True)
bunga = pd.read_parquet("data/raw/makro/IRSTCI01IDM156N.parquet")["nilai"]
bunga.index = pd.to_datetime(bunga.index).to_period("M")
ret_h = adj.pct_change(fill_method=None)

if TES_TIRUAN or TES_KOSONG:
    # Return harian PALSU: faktor pasar x beta + derau sendiri. Volatilitas pasar log-AR(1) harian (phi 0,99 = berkelompok)
    # untuk tiruan, atau acak per hari (tanpa kelompok) untuk kosong. Rata-rata harian TETAP (tidak naik saat bergejolak).
    acak = np.random.default_rng(53)
    n_hari, n_saham = ret_h.shape
    phi = 0.99 if TES_TIRUAN else 0.0
    sd_lv = float(__import__("os").environ.get("SD_LOGVOL", "0.35"))   # simpangan baku log-vol stasioner (kedua mode SAMA)
    sd_inov = sd_lv * np.sqrt(1 - phi ** 2)
    lv = np.zeros(n_hari)
    for d in range(1, n_hari):
        lv[d] = phi * lv[d - 1] + acak.normal(0, sd_inov)
    sig = 0.012 * np.exp(lv - sd_lv ** 2 / 2)
    pasar = 0.0006 + sig * acak.standard_normal(n_hari)
    beta_s = acak.uniform(0.6, 1.4, n_saham)
    palsu = pasar[:, None] * beta_s[None, :] + acak.normal(0, 0.015, (n_hari, n_saham))
    ret_h = pd.DataFrame(palsu, index=ret_h.index, columns=ret_h.columns).where(ret_h.notna())
    harga = (1 + ret_h.fillna(0)).cumprod()
    ha = harga.loc[awal_bulan].reset_index(drop=True)
    ret_pegang = (ha.shift(-2) / ha.shift(-1) - 1).where(ret_pegang.notna())
    print(f"🧪 MODE TES: return harian PALSU, volatilitas {'BERKELOMPOK (phi 0,99)' if TES_TIRUAN else 'TANPA kelompok'}, sd log-vol {sd_lv}")


def vol_harian(hist_pos, t, jendela):
    """Simpangan baku return harian portofolio yang dipegang (daftar (mulai, akhir, kode)) s/d tanggal t."""
    hari = ret_h.index[(ret_h.index <= t)][-jendela:]
    r = pd.Series(np.nan, index=hari)
    for mulai, akhir, kode in hist_pos:
        m = (hari > mulai) & (hari <= akhir)
        if m.any():
            r[m] = ret_h.loc[hari[m], kode].mean(axis=1).values
    r = r.dropna()
    return r.std(ddof=1) * np.sqrt(250) if len(r) >= min(MIN_HARI, jendela - 5) else np.nan


baris, pos_s2, pos_u = [], [], []
w_lama = {"M": pd.Series(dtype=float), "S": pd.Series(dtype=float), "MU": pd.Series(dtype=float), "MV": pd.Series(dtype=float)}
ref = {"M": [], "MU": [], "MV": []}
for i, t in enumerate(akhir_bulan):
    if pd.isna(tgl_jual.iloc[i]) or tgl_jual.iloc[i] > BATAS:
        continue
    s2 = sinyal["S2"].loc[i]
    ok = lolos.loc[i] & ret_pegang.loc[i].notna() & s2.notna()
    if ok.sum() < gg["MIN_SAHAM"]:
        continue
    s, r = s2[ok], ret_pegang.loc[i][ok]
    atas = sorted(s.index[pd.qcut(s.rank(method="first"), 5, labels=False) == 4])
    semesta = sorted(ok.index[ok])
    # estimasi risiko dari masa lalu SAJA (posisi bulan-bulan sebelumnya, hari <= t)
    sh = {"M": vol_harian(pos_s2, t, JENDELA), "MU": vol_harian(pos_u, t, JENDELA), "MV": vol_harian(pos_s2, t, 21)}
    beli, jual = awal_bulan[i + 1], awal_bulan[i + 2]
    pos_s2.append((beli, jual, atas))
    pos_u.append((beli, jual, semesta))
    e = {}
    for k in ref:
        if np.isnan(sh[k]):
            e[k] = np.nan
            continue
        ref[k].append(sh[k] if k != "MV" else sh[k] ** 2)
        if len(ref[k]) < MIN_REF:
            e[k] = np.nan
        elif k == "MV":
            e[k] = min(1.0, np.median(ref[k]) / sh[k] ** 2)
        else:
            e[k] = min(1.0, np.median(ref[k]) / sh[k])
    rf = bunga.get(t.to_period("M") + 1, np.nan) / 1200
    br = biaya_rt.loc[i]
    hasil = {"t": t, "rf": rf, "R": r.reindex(atas).mean(), "U": r.mean(), "sig": sh["M"]}
    for k, porsi in [("S", 1.0), ("M", e["M"]), ("MU", e["MU"]), ("MV", e["MV"])]:
        porsi_pakai = 1.0 if np.isnan(porsi) else porsi        # sebelum ada estimasi: penuh (bulan itu tidak dinilai)
        w = pd.Series(porsi_pakai / len(atas), index=atas)
        semua = w.index.union(w_lama[k].index)
        dw = (w.reindex(semua, fill_value=0) - w_lama[k].reindex(semua, fill_value=0)).abs()
        biaya = (dw * br.reindex(semua).fillna(0.012) / 2).sum()
        hasil[f"e_{k}"] = porsi
        hasil[f"{k}_bersih"] = porsi_pakai * hasil["R"] + (1 - porsi_pakai) * rf - biaya
        hasil[f"{k}_rf0"] = porsi_pakai * hasil["R"] - biaya
        w_lama[k] = w
    baris.append(hasil)

h = pd.DataFrame(baris).set_index("t")
if h["rf"].isna().any():
    print(f"   ⚠️ rf kosong {h['rf'].isna().sum()} bulan -> diisi nilai terakhir")
    h["rf"] = h["rf"].ffill()
h = h[h["e_M"].notna()]
print("🔒 Data uji (2019+) DIKUNCI.\n")


def ringkas(d, k, kolom="bersih", rf0=False):
    rf = 0 * d["rf"] if rf0 else d["rf"]
    y, x = d[f"{k}_{kolom}"] - rf, d["S_bersih" if not rf0 else "S_rf0"] - rf
    return alpha_white(y.values, x.values)


def sharpe(x, rf):
    return (x - rf).mean() / (x - rf).std() * np.sqrt(12)


def dd_maks(x):
    nilai = (1 + x).cumprod()
    return (nilai / nilai.cummax() - 1).min()


p = len(h) // 2
a, b, ta = ringkas(h, "M")
print(f"   {len(h)} bulan dinilai ({h.index.min():%Y-%m} s/d {h.index.max():%Y-%m}); porsi rata {h['e_M'].mean():.2f} "
      f"(min {h['e_M'].min():.2f}; bulan porsi < 1: {(h['e_M'] < 1).mean():.0%}); vol S2 median {h['sig'].median():.0%}/thn")
print(f"   S2 selalu : bersih {h['S_bersih'].mean():+.2%}/bln, Sharpe {sharpe(h['S_bersih'], h['rf']):.2f}, DD maks {dd_maks(h['S_bersih']):.0%}")
print(f"   S2 terkelola: bersih {h['M_bersih'].mean():+.2%}/bln, Sharpe {sharpe(h['M_bersih'], h['rf']):.2f}, DD maks {dd_maks(h['M_bersih']):.0%}")
print(f"   U1 (PENENTU) alpha terkelola vs S2: {a:+.3%}/bln, beta {b:.2f}, t {ta:+.2f} "
      f"(paruh {ringkas(h.iloc[:p], 'M')[2]:+.1f} / {ringkas(h.iloc[p:], 'M')[2]:+.1f})")
for k, nama in [("MU", "vol SEMESTA"), ("MV", "varians 21 hari (Moreira-Muir)")]:
    d = h[h[f"e_{k}"].notna()]
    a2, b2, t2 = ringkas(d, k)
    print(f"   info {nama}: {len(d)} bln, porsi rata {d[f'e_{k}'].mean():.2f}, alpha {a2:+.3%}/bln t {t2:+.2f}, "
          f"Sharpe {sharpe(d[f'{k}_bersih'], d['rf']):.2f} vs {sharpe(d['S_bersih'], d['rf']):.2f}")
a3, _, t3 = ringkas(h, "M", "rf0", rf0=True)
print(f"   info kas TANPA bunga (rf=0): alpha {a3:+.3%}/bln t {t3:+.2f}")
print("   6 bulan terburuk S2 selalu -> terkelola (porsi):")
for t, v in h["S_bersih"].nsmallest(6).items():
    print(f"     {t:%Y-%m}: {v:+.1%} -> {h.loc[t, 'M_bersih']:+.1%} (porsi {h.loc[t, 'e_M']:.2f})")
print(f"\n   KEPUTUSAN #53 (alpha t > 3): {ta:+.2f} -> {'✅ lolos latih -> paper trading s2vol' if ta > 3 else '❌ belum terbukti; S2 resmi tidak diubah'}")
