"""
RISET #28: KINERJA SAHAM IPO INDONESIA SETELAH 'DEMAM' AWAL (e-IPO + harga Yahoo)
=============================================================================

DUGAAN (ditulis 2026-11-21 SEBELUM data detail IPO lengkap & SEBELUM harga IPO dilihat; di-commit sebelum dijalankan)
---------------------------------------------------------------------------------------------------------------
Ritter (1991) & banyak studi pasar berkembang: saham IPO melonjak di hari-hari awal (di IDX sering ARA berturut-turut),
lalu KINERJA JANGKA PANJANGNYA BURUK dibanding pasar (euforia ritel mereda, saham pengendali bebas dijual setelah
masa kunci). Dugaan: membeli saham IPO di tutup hari bursa ke-5 setelah pencatatan lalu menahan 120 hari bursa
(~6 bulan) memberi return LEBIH RENDAH dari keranjang 30 saham paling likuid.
  H2: IPO kecil (nilai penawaran = saham ditawarkan x harga final, di bawah median) lebih buruk dari IPO besar.
Kegunaan kalau terbukti: HINDARI saham IPO baru (filter risiko), bukan strategi beli. (Short tidak bisa di IDX.)

PEMBAGIAN DATA SENDIRI (ditetapkan sekarang; semua e-IPO ada di periode 2020+, aturan global 2019+ tidak bisa dipakai):
  LATIH = IPO dengan tanggal pencatatan <= 2023-06-30 ; UJI = sesudahnya (DIKUNCI, --buka-uji hanya sekali kalau latih lolos).
DATA: e-IPO `raw/ipo/detail.parquet` status Closed dengan tanggal pencatatan & harga final; harga harian Yahoo
  (`data/raw/harga_idx/<KODE>.parquet` atau `bersih/harga_idx`). IPO tanpa harga Yahoo dilaporkan (survivorship).
UJI (2; |t| > 3; t = rata-rata antar IPO / (sb/akar n)):
  U1 selisih return (IPO d5 -> d125) - (keranjang 30 periode sama). Dugaan: NEGATIF.
  U2 selisih U1 antara IPO KECIL dan BESAR (t Welch). Dugaan: kecil lebih negatif.
Diagnosis: return hari pertama (harga final -> tutup hari 1) & hari 1-5, jumlah hari ARA, porsi IPO tanpa harga.
Uji kode: --tes-tiruan (IPO tiruan dengan -10% selama pegang) & --tes-kosong.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BATAS = pd.Timestamp("2023-06-30")
BUKA_DATA_UJI = "--buka-uji" in sys.argv
TES_TIRUAN, TES_KOSONG = "--tes-tiruan" in sys.argv, "--tes-kosong" in sys.argv
MASUK, KELUAR = 4, 124            # indeks hari bursa sejak pencatatan (0 = hari pertama): beli tutup hari ke-5, jual hari ke-125


def t_rata(x):
    x = pd.Series(x).dropna()
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else np.nan


def t_welch(a, b):
    a, b = pd.Series(a).dropna(), pd.Series(b).dropna()
    return (a.mean() - b.mean()) / np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))


def jadi_tanggal(x):
    t = pd.DatetimeIndex(pd.to_datetime(x))
    return (t.tz_localize(None) if t.tz is not None else t).normalize().astype("datetime64[ns]")


if TES_TIRUAN or TES_KOSONG:
    acak = np.random.default_rng(28)
    hari = pd.bdate_range("2019-06-01", "2026-11-13").astype("datetime64[ns]")
    r_pasar = pd.Series(acak.normal(0.0004, 0.01, len(hari)), index=hari)
    ipo, harga = [], {}
    for i in range(160):
        tgl = pd.Timestamp(acak.choice(hari[:-200]))
        kode = f"T{i:03d}"
        n = int((hari >= tgl).sum())
        r = acak.normal(0.0, 0.03, n)
        r[:3] += 0.15                                        # 'demam' awal
        if TES_TIRUAN:
            r[MASUK + 1:KELUAR + 1] -= 0.10 / (KELUAR - MASUK)  # -10% selama pegang
        harga[kode] = pd.DataFrame({"Adj Close": 100 * np.exp(np.cumsum(r)), "Close": 100 * np.exp(np.cumsum(r)),
                                    "Volume": 1e6}, index=hari[hari >= tgl])
        ipo.append({"kode_emiten": kode, "pencatatan": tgl, "harga_final": 100.0, "saham_ditawarkan": acak.uniform(1e8, 5e9)})
    ipo = pd.DataFrame(ipo)
    baca_harga = harga.get
    print(f"🧪 MODE TES: data PALSU {'dengan pola (-10% selama pegang)' if TES_TIRUAN else 'tanpa pola'}")
else:
    d = pd.read_parquet("data/raw/ipo/detail.parquet")
    ipo = d[(d["status"] == "Closed") & d["pencatatan"].notna() & d["harga_final"].notna()].copy()
    ipo["kode_emiten"] = ipo["kode_emiten"].astype(str).str.strip().str.upper()

    def baca_harga(kode):
        f = Path(f"data/raw/harga_idx/{kode}.parquet")
        if not f.exists():
            return None
        h = pd.read_parquet(f, columns=["Adj Close", "Close", "Volume"])
        h.index = jadi_tanggal(h.index)
        return h[~h.index.duplicated(keep="last")].sort_index()

    kode = Path("riset_15_ramadan.py").read_text(encoding="utf-8").split("# ===== Label kalender =====")[0]
    ns, simpan = {}, sys.argv
    sys.argv = [sys.argv[0]]
    exec(compile(kode, "riset_15_bagian", "exec"), ns)
    sys.argv = simpan
    r_pasar = ns["ret_keranjang"].dropna()

ipo["pencatatan"] = jadi_tanggal(ipo["pencatatan"])
ipo["nilai_penawaran"] = ipo["saham_ditawarkan"] * ipo["harga_final"]
ipo = ipo[(ipo["pencatatan"] > BATAS) if BUKA_DATA_UJI else (ipo["pencatatan"] <= BATAS)]
print(f"🔒 Data uji IPO (pencatatan > {BATAS:%Y-%m-%d}) {'DIBUKA' if BUKA_DATA_UJI else 'DIKUNCI'}.\n")

baris, tanpa_harga, pendek = [], [], 0
for _, r in ipo.iterrows():
    h = baca_harga(r["kode_emiten"])
    if h is None or h.empty:
        tanpa_harga.append(r["kode_emiten"])
        continue
    h = h[h.index >= r["pencatatan"]]
    if len(h) <= KELUAR:
        pendek += 1
        continue
    a = h["Adj Close"].values
    t0, t1 = h.index[MASUK], h.index[KELUAR]
    pasar = np.prod(1 + r_pasar[(r_pasar.index > t0) & (r_pasar.index <= t1)].values) - 1
    harian = pd.Series(a[:MASUK + 1]).pct_change().values[1:]
    baris.append({"kode": r["kode_emiten"], "pencatatan": r["pencatatan"], "nilai": r["nilai_penawaran"],
                  "hari1": h["Close"].iloc[0] / r["harga_final"] - 1, "hari1_5": a[MASUK] / a[0] - 1,
                  "hari_ara": int((harian >= 0.19).sum() + (h["Close"].iloc[0] / r["harga_final"] - 1 >= 0.19)),
                  "u1": (a[KELUAR] / a[MASUK] - 1) - pasar})
h = pd.DataFrame(baris)
print(f"   {len(ipo)} IPO Closed di periode ini; dipakai {len(h)} | tanpa harga Yahoo {len(tanpa_harga)} "
      f"({len(tanpa_harga) / max(1, len(ipo)):.0%}) | belum 125 hari {pendek}")
if tanpa_harga:
    print(f"   (tanpa harga: {', '.join(tanpa_harga[:15])}{' ...' if len(tanpa_harga) > 15 else ''})")
print(f"   Diagnosis: hari pertama median {h['hari1'].median():+.1%} (rata {h['hari1'].mean():+.1%}), hari 1->5 median "
      f"{h['hari1_5'].median():+.1%}, median hari ARA (5 hari pertama) {h['hari_ara'].median():.0f}")
print(f"   U1 IPO hari 5 -> 125 dikurangi keranjang 30: rata {h['u1'].mean():+.1%} (median {h['u1'].median():+.1%}), "
      f"t {t_rata(h['u1']):+.1f}, menang dari pasar {(h['u1'] > 0).mean():.0%}")
kecil = h["nilai"] < h["nilai"].median()
print(f"   U2 IPO KECIL {h.loc[kecil, 'u1'].mean():+.1%} ({kecil.sum()}) vs BESAR {h.loc[~kecil, 'u1'].mean():+.1%} "
      f"({(~kecil).sum()}) -> t {t_welch(h.loc[kecil, 'u1'], h.loc[~kecil, 'u1']):+.1f}")
