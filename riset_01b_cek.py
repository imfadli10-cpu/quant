import os
import numpy as np
import pandas as pd
from pathlib import Path

BATAS_LATIH = "2018-12-31"      # data uji (2019+) tetap DIKUNCI
BIAYA = 0.004                   # asumsi biaya beli+jual di IDX: 0,4% (komisi + pajak jual 0,1%)
SAHAM = ["BBCA.JK", "BBRI.JK", "BMRI.JK", "TLKM.JK", "ASII.JK"]
GUDANG = "hf://datasets/fadli-sparks/quant-data/bersih"
token = os.environ.get("HF_TOKEN") or Path("kunci_hf.txt").read_text().strip()


def jadi_tanggal(x):
    t = pd.DatetimeIndex(pd.to_datetime(x))
    if t.tz is not None:
        t = t.tz_localize(None)
    return t.normalize().astype("datetime64[ns]")


def nilai_t(x, y):
    r = x.corr(y)
    return r, r * np.sqrt(len(x) - 2) / np.sqrt(1 - r ** 2)


# ===== Data =====
mentah = pd.read_parquet("data/raw/harga/IHSG.parquet")
ihsg = pd.DataFrame({"tanggal": jadi_tanggal(mentah.index), "kode": "IHSG",
                     "Open": mentah["Open"].values, "Close": mentah["Close"].values})
mentah = pd.read_parquet(f"{GUDANG}/harga_idx.parquet", filters=[("kode", "in", SAHAM)],
                         columns=["tanggal", "kode", "Open", "Close"], storage_options={"token": token})
saham = mentah.assign(tanggal=jadi_tanggal(mentah["tanggal"]))
mentah = pd.read_parquet(f"{GUDANG}/saham_as.parquet", filters=[("kode", "==", "EIDO")],
                         columns=["tanggal", "Adj Close"], storage_options={"token": token})
eido = pd.DataFrame({"tanggal_as": jadi_tanggal(mentah["tanggal"]),
                     "eido_ret": mentah["Adj Close"].pct_change().values}).sort_values("tanggal_as")

semua = pd.concat([ihsg, saham], ignore_index=True).dropna().sort_values(["kode", "tanggal"])
semua["close_kemarin"] = semua.groupby("kode")["Close"].shift(1)
semua["buka_basi"] = semua["Open"] == semua["close_kemarin"]
semua["buka_ke_tutup"] = semua["Close"] / semua["Open"] - 1
semua = pd.merge_asof(semua.sort_values("tanggal"), eido, left_on="tanggal", right_on="tanggal_as",
                      direction="backward", allow_exact_matches=False)
semua = semua[(semua["tanggal"] - semua["tanggal_as"]).dt.days <= 4].dropna(subset=["eido_ret", "close_kemarin"])
latih = semua[semua["tanggal"] <= BATAS_LATIH]
print(f"🔒 Data uji DIKUNCI. Semua angka di bawah dari DATA LATIH (s/d {BATAS_LATIH}).\n")

# Batas "EIDO naik/turun tajam" = 20% teratas/terbawah, dihitung dari data latih saja
atas, bawah = latih["eido_ret"].quantile(0.8), latih["eido_ret"].quantile(0.2)

# ===== Cek 1: IHSG tanpa hari "harga buka basi" =====
i = latih[latih["kode"] == "IHSG"]
r1, t1 = nilai_t(i["eido_ret"], i["buka_ke_tutup"])
bersih = i[~i["buka_basi"]]
r2, t2 = nilai_t(bersih["eido_ret"], bersih["buka_ke_tutup"])
print("1️⃣  IHSG: apakah pola B bertahan setelah hari 'harga buka basi' dibuang?")
print(f"   Semua hari          : korelasi {r1:+.3f}  t = {t1:+5.1f}  ({len(i):,} hari)")
print(f"   Tanpa hari basi     : korelasi {r2:+.3f}  t = {t2:+5.1f}  ({len(bersih):,} hari)\n")

# ===== Cek 2 & 3: saham likuid (harga buka nyata) + simulasi setelah biaya =====
print("2️⃣  Saham besar & likuid (harga bukanya nyata dan bisa dibeli):")
print(f"   {'saham':9}{'buka basi':>10}{'korelasi':>10}{'t':>7}   {'EIDO naik tajam → beli buka, jual tutup':>42}")
print(f"   {'':9}{'':>10}{'':>10}{'':>7}   {'transaksi':>10}{'kotor/trx':>11}{'bersih/trx':>11}{'% untung':>10}")
for kode in SAHAM:
    s = latih[latih["kode"] == kode]
    if len(s) < 100:
        print(f"   {kode:9} data kurang")
        continue
    r, t = nilai_t(s["eido_ret"], s["buka_ke_tutup"])
    trx = s[s["eido_ret"] >= atas]["buka_ke_tutup"]
    bersih_trx = trx - BIAYA
    print(f"   {kode:9}{s['buka_basi'].mean():>9.1%}{r:>+10.3f}{t:>+7.1f}   "
          f"{len(trx):>10}{trx.mean():>+10.3%}{bersih_trx.mean():>+11.3%}{(bersih_trx > 0).mean():>10.1%}")

print(f"\n   Catatan: 'naik tajam' = EIDO semalam ≥ {atas:+.2%} (20% hari teratas di data latih).")
print(f"   Biaya diasumsikan {BIAYA:.1%} per transaksi bolak-balik.")