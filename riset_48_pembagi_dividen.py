"""
RISET #48: UJI DATA UJI untuk ide dari #47 -> "PEMBAGI DIVIDEN" (long-only) vs semesta saham IDX
=================================================================================================
LATAR (jujur): ide ini MUNCUL SETELAH melihat data latih #47 (pembagi - bukan pembagi +1,02%/bln t 2,7; di antara pembagi besarnya yield
tidak berpengaruh). Menguji ulang di data latih = melingkar. Maka (seperti S2 di #12b) aturan ditetapkan & di-commit SEKARANG (2026-11-21),
lalu data uji 2019+ dibuka SEKALI. Dasar logis & literatur: perusahaan yang membayar dividen = laba nyata & arus kas (sinyal kualitas;
Fama-French 2001 "disappearing dividends"; Asness-Frazzini-Pedersen "Quality minus junk" 2019); bukan pembagi di IDX sering emiten rugi /
"saham gorengan" yang disukai ritel (lotre, Bali-Cakici-Whitelaw 2011) -> cenderung tertinggal.
STRATEGI (tetap): akhir bulan t, P = saham semesta S2 (`lolos`, kerangka #13) yang punya dividen (tgl EX) di (t-365 hari, t] di raw/aksi_idx;
  bobot sama; masuk tutup hari bursa pertama t+1, tahan 1 bulan. Pembanding = SELURUH semesta bobot sama.
  BERSIH = rata(P) - rata(semesta) - biaya B (0,4% + 1,2 x tick historis/harga asli) x perputaran P (porsi saham baru).
KRITERIA DATA UJI (sinyal yang tanggal BELI >= 2019-01-01, semua bulan tersedia): LOLOS bila rata-rata BERSIH > 0 DAN t > 2.
  Info (bukan kriteria): pembagi - bukan pembagi (kotor), paruh waktu, nilai di data latih (sudah diketahui, in-sample).
Data uji untuk ide ini HANYA dibuka SEKALI. Gagal -> ide dibuang sebagai strategi (boleh tetap jadi fitur ML dgn pra-registrasi sendiri).
Uji kode: --tes-tiruan (premi +1%/bln utk pembagi) & --tes-kosong; jalur latih (tanpa --buka-uji) = cek kode & angka in-sample.

KEPUTUSAN 2026-11-21 (SEBELUM data uji dibuka): DIBATALKAN, data uji TIDAK dibuka. Analisis daya uji: premi tiruan +1%/bln utk pembagi
-> P - semesta bersih hanya +0,09%/bln t 1,4 dalam 160 bulan (pembagi = ~72% semesta -> P hampir = pembanding; untung hanya dari menghindari
~28 saham). In-sample asli: bersih +0,20%/bln t 1,6. Data uji ~93 bulan -> peluang t > 2 sangat kecil walau efek nyata, dan untungnya
~0,2%/bln. Membuka data uji untuk uji berdaya rendah = membuang kesempatan. Ide disimpan sbg FITUR/penyaring model penampang (pra-registrasi sendiri).
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
    acak = np.random.default_rng(48)
    ret_pegang = pd.DataFrame(acak.normal(0, 0.10, ret_pegang.shape), index=ret_pegang.index,
                              columns=ret_pegang.columns).where(ret_pegang.notna())
    print(f"🧪 MODE TES: return PALSU {'dengan premi +1%/bln untuk pembagi dividen' if TES_TIRUAN else 'tanpa pola'}")

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
    bayar = s > 0
    if TES_TIRUAN:
        r[bayar] += 0.01
    P = set(s.index[bayar])
    putar = 1.0 if not pilih_lalu else len(P - pilih_lalu) / len(P)
    biaya = putar * biaya_rt.loc[i, list(P)].fillna(0.012).mean()
    pilih_lalu = P
    baris.append({"t": t, "n": ok.sum(), "n_bayar": bayar.sum(), "putar": putar, "biaya": biaya,
                  "kotor": r[bayar].mean() - r.mean(), "bersih": r[bayar].mean() - r.mean() - biaya,
                  "bayar_vs_tidak": r[bayar].mean() - r[~bayar].mean() if (~bayar).sum() >= 5 else np.nan})
h = pd.DataFrame(baris).set_index("t")
print(f"🔒 Data uji (2019+) {'DIBUKA' if BUKA_DATA_UJI else 'DIKUNCI (jalur latih, in-sample)'}.\n")
p = len(h) // 2
print(f"   {len(h)} bulan ({h.index.min():%Y-%m} s/d {h.index.max():%Y-%m}), median {h['n'].median():.0f} saham, {h['n_bayar'].median():.0f} pembagi")
print(f"   pembagi - bukan pembagi (info): {h['bayar_vs_tidak'].mean():+.2%}/bln t {t_rata(h['bayar_vs_tidak']):+.2f}")
print(f"   P - semesta: kotor {h['kotor'].mean():+.2%} | putar {h['putar'].iloc[1:].mean():.0%} | biaya {h['biaya'].mean():.2%}")
print(f"   BERSIH: {h['bersih'].mean():+.2%}/bln, t {t_rata(h['bersih']):+.2f} (paruh {t_rata(h['bersih'].iloc[:p]):+.1f} / {t_rata(h['bersih'].iloc[p:]):+.1f})")
if BUKA_DATA_UJI:
    print("   per tahun (bersih/bln): " + " | ".join(f"{y} {v:+.2%}" for y, v in h["bersih"].groupby(h.index.year).mean().items()))
    lulus = h["bersih"].mean() > 0 and t_rata(h["bersih"]) > 2
    print(f"\n   KEPUTUSAN #48 (data uji: bersih > 0 DAN t > 2): {'✅ LOLOS' if lulus else '❌ GAGAL'}")
