"""
Kurs RESMI harian Bank Sentral Eropa (ECB euro foreign exchange reference rates), ~30 mata uang, sejak 1999.

Kenapa: kurs harian Yahoo (IDR=X) terbukti RUSAK (lonjakan -90%/+900%, nilai nyangkut 9612 di 2013, bolong 2001-2003).
ECB bersih: USD/IDR turunan ECB vs kurs akhir bulan OECD korelasi 0,96, rasio level 0,9995, tanpa lonjakan palsu.
Rupiah di ECB baru ada sejak April 2005. Bonus: kurs tetangga Asia (MYR, THB, PHP, SGD, KRW, INR, CNY, HKD).
WAKTU: kurs ECB ditetapkan ~14:15 CET (~20:15 WIB) = SETELAH IDX tutup -> sinyal hari d baru bisa dipakai hari d+1.

Isi (format panjang: tanggal, mata_uang, per_eur, per_usd):
  per_eur = 1 EUR dalam mata uang itu (angka asli ECB); per_usd = per_eur / USD per EUR (mis. IDR per 1 USD).
  data/raw/kurs_ecb/semua.parquet                 -> SELURUH histori, ditimpa tiap hari (file ECB memang selalu lengkap)
  data/raw/harian/kurs_ecb/<tanggal UTC>.parquet  -> 30 hari terakhir (untuk validasi harian, sengaja tumpang tindih)

Cara pakai:  python kumpul_kurs_ecb.py        |   python kumpul_kurs_ecb.py --tes  (tanpa simpan)
"""
import io
import sys
import time
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.zip"
HEADER = {"User-Agent": "quant-data-collector/1.0 (personal research project)"}
HARI_INI = datetime.now(timezone.utc).date()

for percobaan in range(4):
    try:
        r = requests.get(URL, headers=HEADER, timeout=120)
        r.raise_for_status()
        break
    except requests.exceptions.RequestException as e:
        print(f"   🔌 {type(e).__name__}, coba lagi...")
        time.sleep(15 * (percobaan + 1))
else:
    print("❌ kurs_ecb: gagal mengunduh")
    sys.exit(1)

z = zipfile.ZipFile(io.BytesIO(r.content))
lebar = pd.read_csv(z.open(z.namelist()[0]), dtype=str, keep_default_na=False)
lebar = lebar.loc[:, [c for c in lebar.columns if c.strip() and not c.startswith("Unnamed")]]
lebar.columns = [c.strip() for c in lebar.columns]
lebar["Date"] = pd.to_datetime(lebar["Date"].str.strip(), format="%Y-%m-%d").astype("datetime64[ns]")
lebar = lebar.set_index("Date").sort_index()
lebar = lebar.apply(lambda s: pd.to_numeric(s.str.strip(), errors="coerce"))   # "N/A" -> kosong

usd = lebar["USD"]
panjang = lebar.stack().rename("per_eur").reset_index()
panjang.columns = ["tanggal", "mata_uang", "per_eur"]
panjang["per_usd"] = panjang["per_eur"] / panjang["tanggal"].map(usd)
tambah_eur = pd.DataFrame({"tanggal": usd.index, "mata_uang": "EUR", "per_eur": 1.0, "per_usd": (1 / usd).values})
panjang = pd.concat([panjang, tambah_eur.dropna()], ignore_index=True)
panjang["mata_uang"] = panjang["mata_uang"].astype("string")
panjang = panjang.dropna(subset=["per_eur"]).sort_values(["mata_uang", "tanggal"]).reset_index(drop=True)

idr = panjang[panjang["mata_uang"] == "IDR"].set_index("tanggal")["per_usd"]
print(f"✅ kurs_ecb: {len(panjang):,} baris, {panjang['mata_uang'].nunique()} mata uang, "
      f"{panjang['tanggal'].min().date()} s/d {panjang['tanggal'].max().date()} | USD/IDR terakhir {idr.iloc[-1]:,.0f} "
      f"({idr.index[-1].date()})")
lompat = idr.pct_change()
besar = lompat[lompat.abs() > 0.05]
print(f"   🔎 USD/IDR lompatan harian > 5%: {len(besar)} "
      + ", ".join(f"{d.date()} {v:+.1%}" for d, v in besar.items()))

if "--tes" in sys.argv:
    print(panjang.dtypes.to_string())
    print(panjang[panjang["mata_uang"].isin(["IDR", "MYR", "EUR"])].groupby("mata_uang").tail(1).to_string(index=False))
    sys.exit()

folder = Path("data/raw/kurs_ecb")
folder.mkdir(parents=True, exist_ok=True)
panjang.to_parquet(folder / "semua.parquet", index=False)
harian = Path("data/raw/harian/kurs_ecb")
harian.mkdir(parents=True, exist_ok=True)
panjang[panjang["tanggal"] >= pd.Timestamp(HARI_INI - timedelta(days=30))].to_parquet(
    harian / f"{HARI_INI.isoformat()}.parquet", index=False)
print("💾 Tersimpan: data/raw/kurs_ecb/semua.parquet + data/raw/harian/kurs_ecb/")
