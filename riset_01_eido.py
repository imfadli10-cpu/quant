import os
import sys
import numpy as np
import pandas as pd
from pathlib import Path

BATAS_LATIH = "2018-12-31"      # data setelah tanggal ini = DATA UJI, dikunci
BUKA_DATA_UJI = "--buka-uji" in sys.argv


def jadi_tanggal(x):
    """Ubah apa pun jadi tanggal polos dengan format seragam (tanpa zona waktu, presisi ns)."""
    t = pd.DatetimeIndex(pd.to_datetime(x))
    if t.tz is not None:
        t = t.tz_localize(None)
    return t.normalize().astype("datetime64[ns]")


# ===== 1. Ambil data =====
# IHSG: dari file lokal (hasil ambil_harga.py)
mentah = pd.read_parquet("data/raw/harga/IHSG.parquet")
ihsg = pd.DataFrame({"tanggal": jadi_tanggal(mentah.index),
                     "Open": mentah["Open"].values, "Close": mentah["Close"].values}).dropna()

# EIDO: dari file bersih di Hugging Face, hanya baris EIDO yang diunduh
token = os.environ.get("HF_TOKEN") or Path("kunci_hf.txt").read_text().strip()
mentah = pd.read_parquet("hf://datasets/fadli-sparks/quant-data/bersih/saham_as.parquet",
                         filters=[("kode", "==", "EIDO")], columns=["tanggal", "Adj Close"],
                         storage_options={"token": token})
eido = pd.DataFrame({"tanggal_as": jadi_tanggal(mentah["tanggal"]),
                     "harga": mentah["Adj Close"].values}).sort_values("tanggal_as")
print(f"📥 IHSG: {len(ihsg):,} hari | EIDO: {len(eido):,} hari sejak {eido['tanggal_as'].iloc[0].date()}")

# ===== 2. Cek kualitas data: apakah harga Open IHSG bisa dipercaya? =====
ihsg = ihsg.sort_values("tanggal")
sama = (ihsg["Open"] == ihsg["Close"].shift(1)).mean()
print(f"🔎 Hari dengan Open IHSG = Close kemarin persis: {sama:.1%}"
      f"{'  ⚠️ tinggi, Open mungkin tidak akurat' if sama > 0.2 else '  (wajar)'}")

# ===== 3. Hitung return =====
ihsg["lompatan_buka"] = ihsg["Open"] / ihsg["Close"].shift(1) - 1     # A: tutup kemarin -> buka hari ini
ihsg["buka_ke_tutup"] = ihsg["Close"] / ihsg["Open"] - 1              # B: buka -> tutup hari ini
eido["eido_ret"] = eido["harga"].pct_change()

# Untuk setiap hari bursa IDX, ambil return EIDO dari sesi AS TERAKHIR yang sudah selesai
# sebelum IDX buka = sesi AS bertanggal SEBELUM hari itu (allow_exact_matches=False)
gabung = pd.merge_asof(ihsg, eido[["tanggal_as", "eido_ret"]],
                       left_on="tanggal", right_on="tanggal_as",
                       direction="backward", allow_exact_matches=False)
gabung = gabung[(gabung["tanggal"] - gabung["tanggal_as"]).dt.days <= 4]      # buang jeda libur panjang
gabung = gabung.dropna(subset=["eido_ret", "lompatan_buka", "buka_ke_tutup"])

# ===== 4. Pisahkan data latih & uji =====
latih = gabung[gabung["tanggal"] <= BATAS_LATIH]
uji = gabung[gabung["tanggal"] > BATAS_LATIH]
data = uji if BUKA_DATA_UJI else latih
label = "DATA UJI (2019+)" if BUKA_DATA_UJI else f"DATA LATIH ({latih['tanggal'].min().year}-2018)"
print(f"\n🔒 Data uji ({len(uji):,} hari) {'DIBUKA' if BUKA_DATA_UJI else 'DIKUNCI, tidak disentuh'}")
print(f"📊 Menganalisis {label}: {len(data):,} hari\n")


def uji_korelasi(x, y, nama):
    r = x.corr(y)
    n = len(x)
    t = r * np.sqrt(n - 2) / np.sqrt(1 - r ** 2)
    tanda = "✅ signifikan" if abs(t) > 3 else ("🟡 lemah" if abs(t) > 2 else "⚪ tidak signifikan")
    print(f"  {nama:38} korelasi {r:+.3f}   t = {t:+5.1f}   {tanda}")


print("1️⃣  Seberapa kuat EIDO semalam berhubungan dengan IHSG hari ini?")
uji_korelasi(data["eido_ret"], data["lompatan_buka"], "A. EIDO semalam -> lompatan pembukaan")
uji_korelasi(data["eido_ret"], data["buka_ke_tutup"], "B. EIDO semalam -> buka sampai tutup")

print("\n2️⃣  Rata-rata return IHSG buka->tutup, dikelompokkan menurut EIDO semalam:")
data = data.assign(kelompok=pd.qcut(data["eido_ret"], 5,
                                    labels=["1 EIDO turun tajam", "2", "3", "4", "5 EIDO naik tajam"]))
ringkas = data.groupby("kelompok", observed=True).agg(
    hari=("buka_ke_tutup", "size"),
    eido_rata=("eido_ret", "mean"),
    ihsg_buka_ke_tutup=("buka_ke_tutup", "mean"),
    persen_naik=("buka_ke_tutup", lambda s: (s > 0).mean()))
ringkas["eido_rata"] = (ringkas["eido_rata"] * 100).map("{:+.2f}%".format)
ringkas["ihsg_buka_ke_tutup"] = (ringkas["ihsg_buka_ke_tutup"] * 100).map("{:+.3f}%".format)
ringkas["persen_naik"] = (ringkas["persen_naik"] * 100).map("{:.1f}%".format)
print(ringkas.to_string())