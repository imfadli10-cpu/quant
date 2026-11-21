"""
RISET #43: KEJUTAN LABA x DEKAT PUNCAK 52 MINGGU ("jangkar") -> drift saham IDX, data LATIH saja
==============================================================================================
DUGAAN (ditulis 2026-11-21 SEBELUM dijalankan; di-commit sebelum dijalankan)
George, Hwang & Li (2014) & Kalsbach-Windmuller (Bab 3 disertasi Kalsbach 2023, dibaca penuh): investor memakai puncak 52 minggu sebagai
JANGKAR -> berita BAIK saat harga DEKAT puncak & berita BURUK saat harga JAUH dari puncak paling lambat dicerna (alpha interaksi 1,47%/bln
t 4,7 di 23 pasar maju). Riset #34 (IDX): tertil atas - bawah +1,44% / 20 hari, t 2,8 (belum lolos).
DUGAAN: drift terkonsentrasi di (kejutan atas & dekat puncak) dan (kejutan bawah & jauh dari puncak).
DESAIN: PERSIS #34 (data laba Yahoo 114 saham, masuk tutup hari bursa ke-2 setelah tanggal, tahan 20 hari, abnormal vs keranjang 30,
  semesta harga >= 100 & nilai >= Rp1 M, tertil kejutan per kuartal, min 15 peristiwa) + DEKAT = Adj Close / maks 250 hari (rumus S2)
  pada hari bursa TERAKHIR <= tanggal pengumuman; dibagi DUA di median per kuartal (sampel kecil -> 2 kelompok, bukan 5).
UJI (|t| > 3, t antar kuartal):
  U1 (PENENTU) INTERAKSI: abnormal (kejutan atas & dekat) - (kejutan bawah & jauh), rata-rata per kuartal.
  U2 strategi bisa dijalankan: beli (kejutan atas & dekat) saja, bersih biaya 0,8%.
  Pembanding (info): #34 atas - bawah tanpa syarat.
LATIH: keluar <= 2018-12-31; UJI 2019+ DIKUNCI. Uji kode: --tes-tiruan (pola ditanam HANYA di sel interaksi) & --tes-kosong.
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
            dekat = np.exp(np.cumsum(r[:i, j])[-1] - np.max(np.cumsum(r[max(0, i - 250):i, j])))
            if (arah > 0 and dekat > 0.85) or (arah < 0 and dekat < 0.85):
                r[i + 1:i + 1 + TAHAN, j] += arah * 0.03 / TAHAN
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
    i0 = i1 - 1
    if i0 < 200:
        continue
    puncak = np.nanmax(nilai[max(0, i0 - 249):i0 + 1, j])
    dekat = nilai[i0, j] / puncak if puncak > 0 else np.nan
    baris.append({"kode": e["kode"], "tanggal": e["tanggal"], "kuartal": e["tanggal"].to_period("Q"), "keluar": hari[keluar],
                  "kejutan": e["kejutan"], "dekat": dekat, "abnormal": a1 / a0 - 1 - pasar})
h = pd.DataFrame(baris)
h = h[(h["keluar"] > BATAS_LATIH)] if BUKA_DATA_UJI else h[(h["keluar"] <= BATAS_LATIH)]
print(f"🔒 Data uji {'DIBUKA' if BUKA_DATA_UJI else 'DIKUNCI'}.\n")
per_q = []
h = h.dropna(subset=["dekat"])
for q, b in h.groupby("kuartal"):
    if len(b) < MIN_PERISTIWA:
        continue
    t = pd.qcut(b["kejutan"].rank(method="first"), 3, labels=False)
    dk = b["dekat"] >= b["dekat"].median()
    sel = lambda m: b.loc[m, "abnormal"].mean() if m.sum() else np.nan
    per_q.append({"kuartal": q, "n": len(b), "atas": sel(t == 2), "bawah": sel(t == 0),
                  "atas_dekat": sel((t == 2) & dk), "bawah_jauh": sel((t == 0) & ~dk),
                  "atas_jauh": sel((t == 2) & ~dk), "bawah_dekat": sel((t == 0) & dk), "n_ad": int(((t == 2) & dk).sum())})
q = pd.DataFrame(per_q).set_index("kuartal")
q["interaksi"] = q["atas_dekat"] - q["bawah_jauh"]
q["strategi"] = q["atas_dekat"] - BIAYA
q["pembanding"] = q["atas"] - q["bawah"]
print(f"   {len(h):,} peristiwa, {len(q)} kuartal ({q.index.min()} s/d {q.index.max()}), median {q['n'].median():.0f}/kuartal, "
      f"sel atas&dekat median {q['n_ad'].median():.0f} saham")
print(f"   U1 INTERAKSI (atas&dekat - bawah&jauh): {q['interaksi'].mean():+.2%} per 20 hari, t {t_rata(q['interaksi']):+.1f}")
print(f"   U2 beli atas&dekat, bersih {BIAYA:.1%}: {q['strategi'].mean():+.2%} per 20 hari, t {t_rata(q['strategi']):+.1f}")
print(f"   pembanding #34 atas-bawah: {q['pembanding'].mean():+.2%}, t {t_rata(q['pembanding']):+.1f}")
print(f"   (diagnosis sel: atas&dekat {q['atas_dekat'].mean():+.2%} | atas&jauh {q['atas_jauh'].mean():+.2%} | "
      f"bawah&dekat {q['bawah_dekat'].mean():+.2%} | bawah&jauh {q['bawah_jauh'].mean():+.2%}; paruh U1 "
      f"{t_rata(q['interaksi'].iloc[:len(q) // 2]):+.1f} / {t_rata(q['interaksi'].iloc[len(q) // 2:]):+.1f})")
