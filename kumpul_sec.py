import os
import sys
import json
import zipfile
from pathlib import Path

import pandas as pd
import requests

UA = os.environ.get("SEC_USER_AGENT") or Path("kunci_sec.txt").read_text().strip()
HEADER = {"User-Agent": UA, "Accept-Encoding": "gzip, deflate"}
FOLDER = Path("data/raw/fundamental/sec")
FOLDER.mkdir(parents=True, exist_ok=True)

KONSEP = [
    # Laba rugi
    "Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet",
    "CostOfRevenue", "GrossProfit", "OperatingIncomeLoss", "NetIncomeLoss",
    "ResearchAndDevelopmentExpense", "EarningsPerShareBasic", "EarningsPerShareDiluted",
    "WeightedAverageNumberOfDilutedSharesOutstanding",
    # Neraca
    "Assets", "AssetsCurrent", "Liabilities", "LiabilitiesCurrent", "StockholdersEquity",
    "CashAndCashEquivalentsAtCarryingValue", "LongTermDebt", "LongTermDebtNoncurrent",
    # Arus kas
    "NetCashProvidedByUsedInOperatingActivities", "PaymentsToAcquirePropertyPlantAndEquipment",
    "PaymentsOfDividends", "PaymentsForRepurchaseOfCommonStock",
    # Info umum (taksonomi "dei")
    "EntityCommonStockSharesOutstanding", "EntityPublicFloat",
]


def olah(data):
    """Ambil konsep-konsep penting dari JSON satu perusahaan."""
    baris = []
    for taksonomi in ("us-gaap", "dei"):
        fakta = data.get("facts", {}).get(taksonomi, {})
        for konsep in KONSEP:
            if konsep not in fakta:
                continue
            for unit, isi in fakta[konsep]["units"].items():
                for f in isi:
                    baris.append({
                        "cik": data.get("cik"), "perusahaan": data.get("entityName"),
                        "konsep": konsep, "unit": unit, "nilai": f.get("val"),
                        "mulai": f.get("start"), "akhir": f.get("end"),
                        "tahun_fiskal": f.get("fy"), "periode_fiskal": f.get("fp"),
                        "form": f.get("form"), "tanggal_lapor": f.get("filed"),
                    })
    return baris


def simpan(baris, nama):
    df = pd.DataFrame(baris)
    # Paksa setiap kolom ke tipe yang konsisten (data SEC kadang campur angka & teks)
    df["cik"] = pd.to_numeric(df["cik"], errors="coerce").astype("Int64")
    df["tahun_fiskal"] = pd.to_numeric(df["tahun_fiskal"], errors="coerce").astype("Int64")
    df["nilai"] = pd.to_numeric(df["nilai"], errors="coerce")
    for kolom in ["mulai", "akhir", "tanggal_lapor"]:
        df[kolom] = pd.to_datetime(df[kolom], errors="coerce")
    for kolom in ["perusahaan", "konsep", "unit", "periode_fiskal", "form"]:
        df[kolom] = df[kolom].astype("string")
    df.to_parquet(FOLDER / nama, index=False)
    print(f"   💾 {nama}: {df['cik'].nunique()} perusahaan, {len(df):,} baris")


# ===== 1. Peta CIK (nomor perusahaan di SEC) → kode saham =====
tiker = requests.get("https://www.sec.gov/files/company_tickers.json",
                     headers=HEADER, timeout=60).json()
pd.DataFrame(tiker.values()).to_parquet(FOLDER / "tiker.parquet", index=False)
print(f"🏷️  {len(tiker)} pasangan CIK–kode saham")

# ===== 2a. Mode tes: 3 perusahaan saja =====
if "--tes" in sys.argv:
    baris = []
    for cik in [320193, 789019, 1045810]:   # Apple, Microsoft, Nvidia
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
        data = requests.get(url, headers=HEADER, timeout=60).json()
        baris += olah(data)
        print(f"✅ {data['entityName']}")
    simpan(baris, "tes.parquet")
    sys.exit()

# ===== 2b. Mode penuh: unduh file besar, olah semua perusahaan =====
zip_path = Path("companyfacts.zip")
print("⬇️  Mengunduh companyfacts.zip ...")
with requests.get("https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip",
                  headers=HEADER, stream=True, timeout=600) as r:
    r.raise_for_status()
    with open(zip_path, "wb") as f:
        for potongan in r.iter_content(chunk_size=1024 * 1024):
            f.write(potongan)
print(f"   {zip_path.stat().st_size / 1e9:.2f} GB")

with zipfile.ZipFile(zip_path) as z:
    nama_file = [n for n in z.namelist() if n.endswith(".json")]
    print(f"📂 {len(nama_file)} perusahaan di dalam file")
    baris, bagian = [], 0
    for i, nama in enumerate(nama_file, start=1):
        try:
            with z.open(nama) as f:
                baris += olah(json.load(f))
        except Exception as e:
            print(f"   ⏭️  lewati {nama}: {type(e).__name__}")
        if i % 1000 == 0 or i == len(nama_file):
            simpan(baris, f"bagian_{bagian:02d}.parquet")
            baris, bagian = [], bagian + 1

zip_path.unlink()
print("🎉 Selesai")