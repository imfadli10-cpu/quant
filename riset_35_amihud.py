"""
RISET #35: PREMI ILIKUIDITAS (AMIHUD 2002) DI SAHAM IDX, setelah BIAYA REALISTIS, data LATIH saja
==============================================================================================

DUGAAN (ditulis 2026-11-21 SEBELUM menghitung apa pun; di-commit sebelum dijalankan)
--------------------------------------------------------------------------------
Amihud (2002): saham yang harganya mudah bergerak per rupiah transaksi (ILIKUID) memberi return lebih tinggi sebagai
kompensasi. Di pasar berkembang premi ini sering lebih besar. TAPI saham ilikuid juga paling mahal diperdagangkan
(spread lebar) -> dugaan: premi KOTOR positif, premi BERSIH biaya realistis ~0 atau negatif.

DESAIN (sama persis dengan riset #12/#13: semesta riset #2 = harga >= Rp100, median nilai transaksi 60 hari >= Rp1 miliar,
  >= 80% hari aktif, tanpa lompatan > 50%; sinyal akhir bulan, beli tutup hari bursa pertama bulan berikutnya, tahan 1 bulan).
SINYAL: Amihud = rata-rata (|return harian| / nilai transaksi Rp miliar) 60 hari bursa terakhir (hari aktif saja). Besar = ilikuid.
UJI (2; |t| > 3):
  U1 IC (korelasi peringkat sinyal vs return bulan depan), rata-rata bulanan, t.
  U2 (PENENTU, satu ukuran) beli 20% PALING ILIKUID, bobot sama, biaya realistis riset #13 (0,4% + max(spread Corwin-Schultz,
     tick/harga)) atas perputaran, dibanding semesta: t bersih.
Data uji 2019+ DIKUNCI. Uji kode: --tes-tiruan (return tiruan + pola pada sinyal) & --tes-kosong.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

TES_TIRUAN, TES_KOSONG = "--tes-tiruan" in sys.argv, "--tes-kosong" in sys.argv
kode = Path("riset_13_s2_hemat.py").read_text(encoding="utf-8").split("def simulasi(varian):")[0]
g = {"__file__": "riset_13_s2_hemat.py"}
simpan_argv, sys.argv = sys.argv, [sys.argv[0]]
exec(compile(kode, "riset_13_bagian", "exec"), g)
sys.argv = simpan_argv
gg = g["g"]
akhir_bulan, pilih, lolos, ret_pegang, biaya_rt = (g[k] for k in ["akhir_bulan", "pilih", "lolos", "ret_pegang", "biaya_rt"])
adj, tutup, volume, aktif = gg["adj"], gg["tutup"], gg["volume"], gg["aktif"]

r_abs = adj.pct_change(fill_method=None).abs()
nilai_m = (tutup * volume / 1e9).where(aktif & (tutup * volume > 0))
amihud = (r_abs / nilai_m).where(aktif).rolling(60, min_periods=40).mean()
SINYAL = amihud.loc[akhir_bulan].reset_index(drop=True)

if TES_TIRUAN or TES_KOSONG:
    acak = np.random.default_rng(35)
    palsu = pd.DataFrame(acak.normal(0, 0.10, ret_pegang.shape), index=ret_pegang.index, columns=ret_pegang.columns)
    if TES_TIRUAN:
        rk = SINYAL.rank(axis=1, pct=True) - 0.5
        palsu = palsu + 0.06 * rk.fillna(0)                      # 20% teratas ~ +2,4% di atas rata-rata
    ret_pegang = palsu.where(ret_pegang.notna())
    print(f"🧪 MODE TES: return PALSU {'dengan pola (ilikuid lebih tinggi)' if TES_TIRUAN else 'tanpa pola'}")


def nilai_t(s):
    s = pd.Series(s).dropna()
    return s.mean() / (s.std(ddof=1) / np.sqrt(len(s)))


baris, w_lama = [], pd.Series(dtype=float)
for i in np.where(pilih)[0]:
    ok = lolos.loc[i] & ret_pegang.loc[i].notna() & SINYAL.loc[i].notna()
    if ok.sum() < gg["MIN_SAHAM"]:
        continue
    s, r = SINYAL.loc[i][ok], ret_pegang.loc[i][ok]
    atas = list(s.index[pd.qcut(s.rank(method="first"), 5, labels=False) == 4])
    w = pd.Series(1 / len(atas), index=sorted(atas))
    semua = w.index.union(w_lama.index)
    dw = (w.reindex(semua, fill_value=0) - w_lama.reindex(semua, fill_value=0)).abs()
    biaya = (dw * biaya_rt(i, list(semua)) / 2).sum()
    baris.append({"t": akhir_bulan[i], "ic": s.rank().corr(r.rank()), "kotor": r[atas].mean() - r.mean(),
                  "bersih": r[atas].mean() - biaya - r.mean(), "biaya": biaya, "putar": dw.sum() / 2})
    w_lama = w
h = pd.DataFrame(baris).set_index("t")
print(f"\n📊 DATA LATIH ({len(h)} bulan, {h.index.min():%Y-%m} s/d {h.index.max():%Y-%m}; data uji TIDAK disentuh)")
print(f"   U1 IC Amihud (besar = ilikuid) vs return bulan depan: {h['ic'].mean():+.3f}, t {nilai_t(h['ic']):+.1f}")
print(f"   U2 beli 20% paling ilikuid: kotor {h['kotor'].mean():+.2%}/bln | biaya {h['biaya'].mean():.2%}/bln "
      f"(putar {h['putar'].iloc[1:].mean():.0%}) | BERSIH {h['bersih'].mean():+.2%}/bln t {nilai_t(h['bersih']):+.1f}")
t2 = h.index[len(h) // 2]
print(f"   paruh (bersih): {nilai_t(h.loc[:t2, 'bersih']):+.1f} / {nilai_t(h.loc[t2:, 'bersih'].iloc[1:]):+.1f}")
print(f"\n   KEPUTUSAN (t bersih realistis > 3): {'✅ kandidat' if nilai_t(h['bersih']) > 3 else '❌ tidak dipakai'}")
