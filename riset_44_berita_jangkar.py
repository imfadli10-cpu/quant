"""
RISET #44: BERITA EMITEN x DEKAT PUNCAK 52 MINGGU ("jangkar") -> return saham IDX bulan depan
============================================================================================
DUGAAN (ditulis 2026-11-21 SEBELUM melihat return; di-commit sebelum dijalankan)
Kalsbach & Windmuller (Bab 3 disertasi Kalsbach 2023, dibaca penuh): investor kurang bereaksi terhadap berita spesifik emiten bila
berita BAIK datang saat harga DEKAT puncak 52 minggu, atau berita BURUK saat harga JAUH dari puncak (alpha interaksi 1,47%/bln t 4,7;
efek di saham batas-arbitrase tinggi & berita tidak terjadwal). Riset #43 (berita = kejutan laba saja): interaksi t 2,5 (tak lolos).
DUGAAN: dengan SEMUA berita emiten (bukan hanya laba), saham "berita baik & dekat puncak" mengungguli "berita buruk & jauh puncak".

DATA: berita = raw/histori/emitennews (judul slug + tanggal), kode dicocokkan `berita_emiten.cocokkan` (aturan kata umum).
  Hari berita = hari bursa pertama >= tanggal artikel DAN hari bursa sesudahnya (jam terbit tidak diketahui), dibatasi <= hari bursa
  TERAKHIR bulan sinyal (tidak memakai return hari masuk).
  FN (return berita) bulan m = produk(1 + return harian di hari berita) - 1. NEAR = S2 (harga/tertinggi 250 hari) akhir bulan m.
  Kerangka riset #13: semesta S2 (#2), masuk tutup hari bursa pertama m+1, tahan 1 bulan (ret_pegang).
SEMESTA bulan m: saham semesta S2 yang punya >= 1 hari berita di bulan m; minimal 30 saham.
KELOMPOK per bulan: FN dibagi 3 (tertil), NEAR dibagi 2 di median.
UJI (|t| > 3, t antar bulan):
  U1 (PENENTU) INTERAKSI: return bulan depan (FN atas & NEAR atas) - (FN bawah & NEAR bawah).
  U2 strategi bisa dijalankan: beli (FN atas & NEAR atas) bobot sama, dikurangi rata-rata SELURUH semesta S2 bulan itu, dikurangi biaya B
     (0,4% + 1,2 x tick historis/harga asli) untuk ganti penuh tiap bulan (konservatif).
  Pembanding (info): FN atas - FN bawah tanpa syarat.
PEMBAGIAN SENDIRI (cakupan berita baru cukup sejak 2021; 2020 sitemap kosong): LATIH = bulan sinyal 2021-01 s/d 2023-12;
  UJI = 2024-01+ DIKUNCI (--buka-uji sekali, hanya bila latih lolos).
Uji kode: --tes-tiruan (return palsu + pola di sel interaksi) & --tes-kosong.
"""
import glob
import io
import contextlib
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(".").resolve()))
from berita_emiten import cocokkan
from biaya_idx import tabel_tick_historis

BUKA_DATA_UJI = "--buka-uji" in sys.argv
TES_TIRUAN, TES_KOSONG = "--tes-tiruan" in sys.argv, "--tes-kosong" in sys.argv
AWAL_LATIH, AKHIR_LATIH = pd.Timestamp("2021-01-01"), pd.Timestamp("2023-12-31")


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
akhir_bulan, lolos, ret_pegang, sinyal = g["akhir_bulan"], g["lolos"], g["ret_pegang"], g["sinyal"]
adj, tutup, hari = gg["adj"], gg["tutup"], gg["adj"].index
r_harian = adj.pct_change(fill_method=None)
tick_b = tabel_tick_historis(tutup.loc["2020":], pd.read_parquet("data/raw/aksi_idx/semua.parquet"))

# ===== berita -> hari berita per (kode, hari) =====
b = pd.read_parquet("data/raw/histori/emitennews/semua.parquet")
dx = pd.concat([pd.read_parquet(x) for x in sorted(glob.glob("data/raw/harian/daftar_idx/*.parquet"))]).drop_duplicates("kode", keep="last")
kode_kecil = [k.lower() for k in adj.columns]
m = cocokkan(b, kode_kecil, {k.lower(): n for k, n in zip(dx["kode"], dx["longName"])})
m["tanggal"] = pd.to_datetime(m["tanggal"])
idx0 = np.searchsorted(hari.values, m["tanggal"].values.astype("datetime64[ns]"), side="left")
pasang = set()
for k, i0 in zip(m["kode"], idx0):
    for i in (i0, i0 + 1):
        if i < len(hari):
            pasang.add((k, i))
hari_berita = pd.DataFrame(False, index=hari, columns=adj.columns)
for k, i in pasang:
    if k in hari_berita.columns:
        hari_berita.iat[i, hari_berita.columns.get_loc(k)] = True
print(f"   {len(m):,} sebutan kode di {m['url'].nunique():,} artikel; {len(pasang):,} pasangan (kode, hari berita)")

if TES_TIRUAN or TES_KOSONG:
    acak = np.random.default_rng(44)
    r_harian = pd.DataFrame(acak.normal(0, 0.025, r_harian.shape), index=hari, columns=adj.columns).where(r_harian.notna())
    ret_pegang = pd.DataFrame(acak.normal(0, 0.10, ret_pegang.shape), index=ret_pegang.index, columns=ret_pegang.columns).where(ret_pegang.notna())
    print(f"🧪 MODE TES: return PALSU {'dengan pola di sel interaksi (+3% / -3%)' if TES_TIRUAN else 'tanpa pola'}")

baris = []
bulan_hari = pd.Series(hari.to_period("M"), index=hari)
for i, t in enumerate(akhir_bulan):
    if BUKA_DATA_UJI:
        if t <= AKHIR_LATIH or i + 2 >= len(akhir_bulan):
            continue
    elif not (AWAL_LATIH <= t <= AKHIR_LATIH):
        continue
    hb = hari_berita.loc[bulan_hari.index[bulan_hari == t.to_period("M")]]
    hb = hb.loc[:t]
    ada = hb.any()
    ok = lolos.loc[i] & ret_pegang.loc[i].notna() & sinyal["S2"].loc[i].notna() & ada.reindex(lolos.columns, fill_value=False)
    if ok.sum() < 30:
        continue
    kd = ok.index[ok]
    rh = r_harian.loc[hb.index, kd]
    fn = (1 + rh.where(hb[kd]).fillna(0)).prod() - 1
    near = sinyal["S2"].loc[i][kd]
    r = ret_pegang.loc[i][kd].copy()
    tf = pd.qcut(fn.rank(method="first"), 3, labels=False)
    nr = near >= near.median()
    if TES_TIRUAN:
        r[(tf == 2) & nr] += 0.03
        r[(tf == 0) & ~nr] -= 0.03
    sel_ad, sel_bj = kd[(tf == 2) & nr], kd[(tf == 0) & ~nr]
    semesta_all = lolos.loc[i] & ret_pegang.loc[i].notna()
    rata_semesta = ret_pegang.loc[i][semesta_all].mean()
    if TES_TIRUAN or TES_KOSONG:
        rata_semesta = r.mean()
    biaya = (0.004 + 1.2 * tick_b.loc[t, sel_ad].fillna(0.01)).mean() if t in tick_b.index else 0.012
    baris.append({"t": t, "n": len(kd), "n_ad": len(sel_ad),
                  "interaksi": r[sel_ad].mean() - r[sel_bj].mean(),
                  "strategi": r[sel_ad].mean() - rata_semesta - biaya,
                  "pembanding": r[tf == 2].mean() - r[tf == 0].mean(),
                  "ad": r[sel_ad].mean(), "aj": r[kd[(tf == 2) & ~nr]].mean(), "bd": r[kd[(tf == 0) & nr]].mean(), "bj": r[sel_bj].mean()})
h = pd.DataFrame(baris).set_index("t")
print(f"🔒 Data uji (2024+) {'DIBUKA' if BUKA_DATA_UJI else 'DIKUNCI'}.\n")
print(f"   {len(h)} bulan ({h.index.min():%Y-%m} s/d {h.index.max():%Y-%m}), median {h['n'].median():.0f} saham berita/bulan, "
      f"sel FN atas & NEAR atas median {h['n_ad'].median():.0f}")
print(f"   U1 INTERAKSI (FN atas&dekat - FN bawah&jauh): {h['interaksi'].mean():+.2%}/bln, t {t_rata(h['interaksi']):+.1f}")
print(f"   U2 beli FN atas&dekat - semesta, bersih biaya B: {h['strategi'].mean():+.2%}/bln, t {t_rata(h['strategi']):+.1f}")
print(f"   pembanding FN atas - bawah: {h['pembanding'].mean():+.2%}/bln, t {t_rata(h['pembanding']):+.1f}")
print(f"   (sel: atas&dekat {h['ad'].mean():+.2%} | atas&jauh {h['aj'].mean():+.2%} | bawah&dekat {h['bd'].mean():+.2%} | "
      f"bawah&jauh {h['bj'].mean():+.2%}; paruh U1 {t_rata(h['interaksi'].iloc[:len(h) // 2]):+.1f} / {t_rata(h['interaksi'].iloc[len(h) // 2:]):+.1f})")
