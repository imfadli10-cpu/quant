"""
RISET #45: NET SHARE ISSUANCE (penerbitan saham baru) -> return saham IDX bulan depan
====================================================================================
DUGAAN (ditulis 2026-11-21 SEBELUM melihat return; di-commit sebelum dijalankan)
Literatur: emiten yang menambah jumlah saham (rights issue, private placement/PMTHMETD, konversi, ESOP) cenderung KALAH dari pasar
sesudahnya; yang membeli kembali sahamnya menang (Pontiff-Woodgate 2008 JF; Daniel-Titman 2006; Fama-French 2008 "dissecting anomalies":
efek kuat di semua ukuran perusahaan). Internasional: McLean-Pontiff-Watanabe 2009 JFE (41 negara, termasuk pasar berkembang) -> efek ada
di luar AS. Novy-Marx & Velikov 2016: net issuance = anomali PERPUTARAN RENDAH yang bertahan setelah biaya (cocok dengan masalah biaya IDX).
Alasan logis: manajemen menerbitkan saham saat harga dianggap mahal (market timing); di IDX, PMTHMETD sering ke pihak terafiliasi/"goreng".
DUGAAN: saham PENERBIT (jumlah saham naik > 5% dalam 12 bulan) mendapat return bulan depan LEBIH RENDAH dari saham TANPA penerbitan.

DATA: raw/saham_beredar (Yahoo get_shares_full; padat sejak 2018Q4). Angka Yahoo TIDAK konsisten penyesuaian splitnya (dicek 21 Nov
  2026: dari 107 split 2019+, kira-kira separuh tampak sebagai lompatan, separuh sudah disesuaikan) -> bulan-saham yang jendelanya memuat
  split/saham bonus (raw/aksi_idx, split != 1) DIKELUARKAN.
SINYAL akhir bulan t: saham bersih = median 3 titik terakhir (hanya ke belakang); nilai pada tanggal D = titik bersih terakhir <= D yang
  umurnya <= 120 hari. D_akhir = t - 30 hari (jeda konservatif), D_awal = D_akhir - 365 hari. NI = log(nilai(D_akhir) / nilai(D_awal)).
  Keluarkan bila ada split dengan tanggal ex di (D_awal - 30 hari, t].
KELOMPOK: PENERBIT NI > +0,05 | TANPA |NI| <= 0,01 | BELI KEMBALI NI < -0,01 (info; jarang di IDX).
KERANGKA riset #13: semesta S2 (`lolos`, harga >= Rp100, nilai transaksi >= Rp1 M, aktif >= 80%), masuk tutup hari bursa pertama t+1,
  tahan 1 bulan (`ret_pegang`). Bulan sah: >= 5 penerbit & >= 20 tanpa-penerbitan.
UJI (t antar bulan):
  U1 (PENENTU, satu ukuran): rata-rata(PENERBIT) - rata-rata(TANPA), bobot sama. LOLOS bila t < -3.
  U2 (info, sisi yang bisa dijalankan long-only): semesta TANPA penerbit - seluruh semesta (kotor).
  U3 (info): IC Spearman NI vs return bulan depan.
PEMBAGIAN SENDIRI (data padat baru 2018Q4): LATIH = bulan sinyal yang tanggal JUAL-nya <= 2022-12-31 (sinyal 2019-12 s/d 2022-10);
  UJI = bulan sinyal yang tanggal BELI-nya >= 2023-01-01 -> DIKUNCI (--buka-uji sekali, hanya bila latih lolos).
  Daya uji RENDAH (~35 bulan latih) -> diakui di depan. (2019+ = data uji S2, tapi ini sinyal LAIN dgn pembagian sendiri.)
Daya uji (dicek sebelum commit, return palsu): pola -2%/bln -> U1 -1,74% t -3,34 (pas-pasan lolos); tanpa pola t +0,50.
  Efek literatur AS ~ -0,5..-1%/bln -> kemungkinan besar TIDAK terdeteksi walau ada; hasil negatif di sini = "belum terbukti", bukan "tidak ada".
Uji kode: --tes-tiruan (return palsu, penerbit -2%/bln) & --tes-kosong; --potong-data (hapus semua data sesudah 2022-12-31 -> harus IDENTIK).
"""
import contextlib
import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(".").resolve()))

BUKA_DATA_UJI = "--buka-uji" in sys.argv
TES_TIRUAN, TES_KOSONG = "--tes-tiruan" in sys.argv, "--tes-kosong" in sys.argv
POTONG = "--potong-data" in sys.argv
BATAS = pd.Timestamp("2022-12-31")
LIHAT_SINYAL = "--lihat-sinyal" in sys.argv     # distribusi sinyal saja (tanpa return) -> boleh sebelum pra-registrasi

if POTONG:                                       # semua file dibaca terpotong di BATAS
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
akhir_bulan, lolos, ret_pegang = g["akhir_bulan"], g["lolos"], g["ret_pegang"]
awal_bulan = g["g"]["awal_bulan"]
if POTONG:
    print(f"   (cek potong: harga terakhir {g['g']['adj'].index.max():%Y-%m-%d})")
tgl_beli = pd.Series(awal_bulan).shift(-1).reset_index(drop=True)
tgl_jual = pd.Series(awal_bulan).shift(-2).reset_index(drop=True)

# ===== sinyal NI =====
sb = pd.read_parquet("data/raw/saham_beredar/semua.parquet").sort_values(["kode", "tanggal"])
sb["bersih"] = sb.groupby("kode")["saham_beredar"].transform(lambda s: s.rolling(3, min_periods=1).median())
aksi = pd.read_parquet("data/raw/aksi_idx/semua.parquet")
split = aksi[aksi["split"].notna() & (aksi["split"] != 0) & (aksi["split"] != 1)][["kode", "tanggal"]]
split_per = {k: v.values.astype("datetime64[ns]") for k, v in split.groupby("kode")["tanggal"]}
seri = {k: (v["tanggal"].values.astype("datetime64[ns]"), v["bersih"].values) for k, v in sb.groupby("kode")}


def nilai(k, D):
    tg, x = seri[k]
    j = np.searchsorted(tg, np.datetime64(D), side="right") - 1
    if j < 0 or (np.datetime64(D) - tg[j]) > np.timedelta64(120, "D"):
        return np.nan
    return x[j]


def ni_bulan(t, daftar):
    De = t - pd.Timedelta(days=30)
    Da = De - pd.Timedelta(days=365)
    out = {}
    for k in daftar:
        if k not in seri:
            continue
        sp = split_per.get(k)
        if sp is not None and ((sp > np.datetime64(Da - pd.Timedelta(days=30))) & (sp <= np.datetime64(t))).any():
            continue
        a, e = nilai(k, Da), nilai(k, De)
        if a > 0 and e > 0:
            out[k] = np.log(e / a)
    return pd.Series(out, dtype="float64")


if TES_TIRUAN or TES_KOSONG:
    acak = np.random.default_rng(45)
    ret_pegang = pd.DataFrame(acak.normal(0, 0.10, ret_pegang.shape), index=ret_pegang.index,
                              columns=ret_pegang.columns).where(ret_pegang.notna())
    print(f"🧪 MODE TES: return PALSU {'dengan pola (penerbit -2%/bln)' if TES_TIRUAN else 'tanpa pola'}")

baris = []
for i, t in enumerate(akhir_bulan):
    if t < pd.Timestamp("2019-12-01") or pd.isna(tgl_jual.iloc[i]):
        continue
    if BUKA_DATA_UJI:
        if tgl_beli.iloc[i] < pd.Timestamp("2023-01-01"):
            continue
    elif tgl_jual.iloc[i] > BATAS:
        continue
    ok = lolos.loc[i] & ret_pegang.loc[i].notna()
    ni = ni_bulan(t, ok.index[ok])
    if LIHAT_SINYAL:
        baris.append({"t": t, "n": len(ni), "pen": (ni > 0.05).sum(), "tanpa": (ni.abs() <= 0.01).sum(), "bk": (ni < -0.01).sum(),
                      "q90": ni.quantile(0.9)})
        continue
    r = ret_pegang.loc[i][ni.index].copy()
    pen, tanpa = ni > 0.05, ni.abs() <= 0.01
    if TES_TIRUAN:
        r[pen] -= 0.02
    if pen.sum() < 5 or tanpa.sum() < 20:
        continue
    baris.append({"t": t, "n": len(ni), "n_pen": pen.sum(), "n_bk": (ni < -0.01).sum(),
                  "u1": r[pen].mean() - r[tanpa].mean(), "u2": r[~pen].mean() - r.mean(),
                  "u3": ni.rank().corr(r.rank()), "bk": r[ni < -0.01].mean() - r[tanpa].mean() if (ni < -0.01).sum() >= 3 else np.nan})
h = pd.DataFrame(baris).set_index("t")
if LIHAT_SINYAL:
    print(h.to_string())
    print(h.median())
    sys.exit(0)
print(f"🔒 Data uji (sinyal 2022-11+) {'DIBUKA' if BUKA_DATA_UJI else 'DIKUNCI'}.{'  [DATA DIPOTONG di 2022-12-31]' if POTONG else ''}\n")
print(f"   {len(h)} bulan ({h.index.min():%Y-%m} s/d {h.index.max():%Y-%m}), median {h['n'].median():.0f} saham bersinyal, "
      f"{h['n_pen'].median():.0f} penerbit, {h['n_bk'].median():.0f} beli kembali")
print(f"   U1 PENERBIT - TANPA (PENENTU, lolos bila t < -3): {h['u1'].mean():+.2%}/bln, t {t_rata(h['u1']):+.2f}")
print(f"   U2 semesta tanpa penerbit - semesta (kotor): {h['u2'].mean():+.2%}/bln, t {t_rata(h['u2']):+.2f}")
print(f"   U3 IC NI: {h['u3'].mean():+.3f}, t {t_rata(h['u3']):+.2f}")
print(f"   (info: beli kembali - tanpa {h['bk'].mean():+.2%}/bln t {t_rata(h['bk']):+.1f} [{h['bk'].notna().sum()} bln]; "
      f"paruh U1 {t_rata(h['u1'].iloc[:len(h) // 2]):+.1f} / {t_rata(h['u1'].iloc[len(h) // 2:]):+.1f})")
tu = t_rata(h["u1"])
print(f"\n   KEPUTUSAN #45 (U1 t < -3): {tu:+.2f} -> {'✅ lolos latih' if tu < -3 else '❌ tidak lolos'}")
