import os
import sys
import json
import warnings
from datetime import date
from pathlib import Path

import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

warnings.filterwarnings("ignore", message="BigQuery Storage module not found")

kunci_teks = os.environ.get("GCP_KEY_JSON")
if kunci_teks:
    kredensial = service_account.Credentials.from_service_account_info(json.loads(kunci_teks))
else:
    kredensial = service_account.Credentials.from_service_account_file("kunci_gcp.json")
client = bigquery.Client(credentials=kredensial, project=kredensial.project_id)

TAHUN_INI = date.today().year

# Query per tahun. {a} = awal tahun, {b} = awal tahun berikutnya
SUMBER = {
    "bitcoin": (2009, """
        SELECT DATE(timestamp) AS tanggal, COUNT(*) AS jumlah_blok,
               SUM(transaction_count) AS jumlah_transaksi,
               SUM(size) AS total_ukuran_byte, AVG(size) AS rata_ukuran_blok
        FROM `bigquery-public-data.crypto_bitcoin.blocks`
        WHERE timestamp_month >= '{a}' AND timestamp_month < '{b}'
        GROUP BY tanggal ORDER BY tanggal"""),
    "ethereum": (2015, """
        SELECT DATE(timestamp) AS tanggal, COUNT(*) AS jumlah_blok,
               SUM(transaction_count) AS jumlah_transaksi, SUM(gas_used) AS total_gas,
               AVG(base_fee_per_gas) / 1e9 AS rata_base_fee_gwei
        FROM `bigquery-public-data.crypto_ethereum.blocks`
        WHERE timestamp >= TIMESTAMP('{a}') AND timestamp < TIMESTAMP('{b}')
        GROUP BY tanggal ORDER BY tanggal"""),
    "berita_gdelt": (2015, """
        SELECT DATE(_PARTITIONTIME) AS tanggal,
          CASE ActionGeo_CountryCode WHEN 'ID' THEN 'indonesia' WHEN 'US' THEN 'amerika'
            WHEN 'CH' THEN 'tiongkok' WHEN 'JA' THEN 'jepang' WHEN 'RS' THEN 'rusia'
            ELSE 'lainnya' END AS negara,
          COUNT(*) AS jumlah_peristiwa, AVG(AvgTone) AS rata_nada,
          AVG(GoldsteinScale) AS rata_goldstein,
          AVG(IF(QuadClass IN (3, 4), 1, 0)) AS porsi_konflik
        FROM `gdelt-bq.gdeltv2.events_partitioned`
        WHERE _PARTITIONTIME >= TIMESTAMP('{a}') AND _PARTITIONTIME < TIMESTAMP('{b}')
        GROUP BY tanggal, negara ORDER BY tanggal, negara"""),
}


def sql_tahun(template, tahun):
    return template.format(a=f"{tahun}-01-01", b=f"{tahun + 1}-01-01")


# ===== Mode 1: HITUNG (gratis, tidak memakai jatah) =====
if "--hitung" in sys.argv:
    total_semua = 0
    for nama, (mulai, template) in SUMBER.items():
        total = 0
        for tahun in range(mulai, TAHUN_INI + 1):
            uji = client.query(sql_tahun(template, tahun),
                               job_config=bigquery.QueryJobConfig(dry_run=True))
            total += uji.total_bytes_processed / 1e9
        total_semua += total
        print(f"📏 {nama:14} {mulai}–{TAHUN_INI}: {total:8.1f} GB")
    print(f"\n   TOTAL: {total_semua:.1f} GB dari jatah 1.000 GB per bulan")
    sys.exit()

# ===== Mode 2: JALANKAN satu sumber =====
# Cara pakai: python isi_histori_bigquery.py --jalankan bitcoin
nama = sys.argv[sys.argv.index("--jalankan") + 1]
mulai, template = SUMBER[nama]
folder = Path(f"data/raw/histori/{nama}")
folder.mkdir(parents=True, exist_ok=True)

for tahun in range(mulai, TAHUN_INI + 1):
    file = folder / f"{tahun}.parquet"
    if file.exists():
        print(f"⏭️  {tahun}: sudah ada")
        continue
    df = client.query(sql_tahun(template, tahun)).to_dataframe()
    for kolom in df.columns:
        if str(df[kolom].dtype) == "dbdate":
            df[kolom] = pd.to_datetime(df[kolom].astype(str))
    if df.empty:
        print(f"⚠️  {tahun}: kosong")
        continue
    df.to_parquet(file, index=False)
    print(f"✅ {nama} {tahun}: {len(df)} baris")