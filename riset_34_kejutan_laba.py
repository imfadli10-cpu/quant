"""
RISET #34: KEJUTAN LABA -> 'DRIFT' SAHAM IDX SETELAH PENGUMUMAN (post-earnings announcement drift), data LATIH saja
==============================================================================================================

DUGAAN (ditulis 2026-11-21 SEBELUM data laba lengkap dilihat; di-commit sebelum dijalankan)
----------------------------------------------------------------------------------------
Bernard & Thomas (1989) dan ratusan replikasi: saham dengan kejutan laba POSITIF terus mengungguli saham dengan kejutan
NEGATIF selama beberapa minggu-bulan setelah pengumuman (investor bereaksi kurang terhadap informasi laba). Efek lebih kuat
di pasar dengan banyak investor ritel & sedikit analis -> IDX kandidat bagus.
Perkiraan jujur: data kejutan Yahoo untuk IDX berisik (sebagian perkiraan beda skala/mata uang); biaya IDX tinggi.

DATA: `raw/laba_idx/semua.parquet` (Yahoo): eps_perkiraan, eps_aktual, tanggal pengumuman (waktu WIB).
  Kejutan = (aktual - perkiraan) / |perkiraan|, hanya baris dengan keduanya ada & perkiraan != 0.
WAKTU (konservatif; jam Yahoo tidak bisa dipercaya): MASUK = tutup hari bursa ke-2 setelah TANGGAL pengumuman (WIB),
  KELUAR = 20 hari bursa kemudian. Abnormal = return saham - return keranjang 30 saham paling likuid (riset #4/#15) periode sama.
SEMESTA: saham dengan median nilai transaksi 60 hari >= Rp1 miliar & harga >= Rp100 di hari MASUK (data sampai hari itu).
KELOMPOK: per kuartal kalender pengumuman, kejutan dibagi 3 (tertil) di antara peristiwa semesta (minimal 15 peristiwa/kuartal).
UJI (2; |t| > 3; t antar kuartal = rata-rata / (sb/akar n) -> peristiwa dalam kuartal yang sama tidak dianggap independen):
  U1 (TERTIL ATAS - TERTIL BAWAH) abnormal 20 hari, rata-rata per kuartal.
  U2 STRATEGI bisa dijalankan: beli TERTIL ATAS saja, abnormal 20 hari dikurangi biaya bolak-balik 0,8% (komisi 0,4% + spread).
LATIH: peristiwa dengan hari KELUAR <= 2018-12-31. UJI 2019+ DIKUNCI (--buka-uji sekali kalau latih lolos).
Uji kode: --tes-tiruan (abnormal +2% tertil atas, -2% bawah) & --tes-kosong.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BATAS_LATIH = pd.Timestamp("2018-12-31")
BUKA_DATA_UJI = "--buka-uji" in sys.argv
TES_TIRUAN, TES_KOSONG = "--tes-tiruan" in sys.argv, "--tes-kosong" in sys.argv
TAHAN, BIAYA, MIN_PERISTIWA = 20, 0.008, 15


def t_rata(x):
    x = pd.Series(x).dropna()
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else np.nan


if TES_TIRUAN or TES_KOSONG:
    acak = np.random.default_rng(34)
    hari = pd.bdate_range("2012-01-02", "2026-11-13").astype("datetime64[ns]")
    kode = [f"S{i:03d}" for i in range(120)]
    r = acak.normal(0.0003, 0.02, (len(hari), len(kode)))
    ev = []
    for j, k in enumerate(kode):
        for tgl in pd.date_range("2012-03-31", "2026-06-30", freq="QE"):
            t_umum = tgl + pd.Timedelta(days=int(acak.integers(20, 60)))
            ev.append({"kode": k, "waktu_wib": t_umum, "eps_perkiraan": 100.0, "eps_aktual": 100 * (1 + acak.normal(0, 0.3))})
    ev = pd.DataFrame(ev)
    if TES_TIRUAN:
        for _, e in ev.iterrows():
            j = kode.index(e["kode"])
            i = np.searchsorted(hari.values, np.datetime64(e["waktu_wib"].normalize()), side="right") + 1   # hari bursa ke-2
            arah = np.sign(e["eps_aktual"] - e["eps_perkiraan"])
            r[i + 1:i + 1 + TAHAN, j] += arah * 0.02 / TAHAN
    adj = pd.DataFrame(1000 * np.exp(np.cumsum(r, axis=1 * 0)), index=hari, columns=kode)
    tutup = adj.copy()
    median_nilai = pd.DataFrame(5e9, index=hari, columns=kode)
    r_pasar = pd.Series(r.mean(axis=1) * 0, index=hari)
    print(f"🧪 MODE TES: data PALSU {'dengan pola (+2% / -2% selama 20 hari)' if TES_TIRUAN else 'tanpa pola'}")
else:
    sys.argv_simpan = sys.argv
    sys.argv = [sys.argv[0]]
    g = {}
    kode12 = Path("riset_12_gabung_sinyal.py").read_text(encoding="utf-8").split("baris, korelasi, lalu = [], [], {}")[0]
    exec(compile(kode12, "riset_12_bagian", "exec"), g)
    kode15 = Path("riset_15_ramadan.py").read_text(encoding="utf-8").split("# ===== Label kalender =====")[0]
    ns = {}
    exec(compile(kode15, "riset_15_bagian", "exec"), ns)
    sys.argv = sys.argv_simpan
    adj, tutup, median_nilai, hari = g["adj"], g["tutup"], g["median_nilai"], g["hari"]
    r_pasar = ns["ret_keranjang"].reindex(hari).fillna(0)
    ev = pd.read_parquet("data/raw/laba_idx/semua.parquet")

ev = ev.dropna(subset=["eps_perkiraan", "eps_aktual"])
ev = ev[ev["eps_perkiraan"] != 0].copy()
ev["kejutan"] = (ev["eps_aktual"] - ev["eps_perkiraan"]) / ev["eps_perkiraan"].abs()
ev["tanggal"] = pd.to_datetime(ev["waktu_wib"]).dt.normalize()
ev = ev.drop_duplicates(["kode", "tanggal"])
nilai = adj.values
pasar_kum = np.concatenate([[1.0], np.cumprod(1 + r_pasar.values)])        # pasar_kum[i+1] = indeks pasar s/d hari i
kolom = {k: j for j, k in enumerate(adj.columns)}
baris = []
for _, e in ev.iterrows():
    j = kolom.get(str(e["kode"]))
    if j is None:
        continue
    i1 = np.searchsorted(hari.values, np.datetime64(e["tanggal"]), side="right")      # hari bursa pertama SESUDAH tanggal
    masuk, keluar = i1 + 1, i1 + 1 + TAHAN
    if keluar >= len(hari):
        continue
    if not (tutup.iat[masuk, j] >= 100 and median_nilai.iat[masuk, j] >= 1e9):
        continue
    a0, a1 = nilai[masuk, j], nilai[keluar, j]
    if not (np.isfinite(a0) and np.isfinite(a1)):
        continue
    pasar = pasar_kum[keluar + 1] / pasar_kum[masuk + 1] - 1
    baris.append({"kode": e["kode"], "tanggal": e["tanggal"], "kuartal": e["tanggal"].to_period("Q"), "keluar": hari[keluar],
                  "kejutan": e["kejutan"], "abnormal": a1 / a0 - 1 - pasar})
h = pd.DataFrame(baris)
h = h[(h["keluar"] > BATAS_LATIH)] if BUKA_DATA_UJI else h[(h["keluar"] <= BATAS_LATIH)]
print(f"🔒 Data uji {'DIBUKA' if BUKA_DATA_UJI else 'DIKUNCI'}.\n")
per_q = []
for q, b in h.groupby("kuartal"):
    if len(b) < MIN_PERISTIWA:
        continue
    t = pd.qcut(b["kejutan"].rank(method="first"), 3, labels=False)
    per_q.append({"kuartal": q, "n": len(b), "atas": b.loc[t == 2, "abnormal"].mean(), "bawah": b.loc[t == 0, "abnormal"].mean()})
q = pd.DataFrame(per_q).set_index("kuartal")
q["selisih"] = q["atas"] - q["bawah"]
q["strategi"] = q["atas"] - BIAYA
print(f"   {len(h):,} peristiwa dalam semesta, {len(q)} kuartal ({q.index.min()} s/d {q.index.max()}), median {q['n'].median():.0f}/kuartal")
print(f"   U1 TERTIL ATAS - BAWAH (abnormal 20 hari): {q['selisih'].mean():+.2%} per kuartal, t {t_rata(q['selisih']):+.1f}")
print(f"   U2 beli TERTIL ATAS, bersih biaya {BIAYA:.1%}: {q['strategi'].mean():+.2%} per 20 hari, t {t_rata(q['strategi']):+.1f}")
print(f"   (diagnosis: atas {q['atas'].mean():+.2%}, bawah {q['bawah'].mean():+.2%}; paruh U1 "
      f"{t_rata(q['selisih'].iloc[:len(q) // 2]):+.1f} / {t_rata(q['selisih'].iloc[len(q) // 2:]):+.1f})")
