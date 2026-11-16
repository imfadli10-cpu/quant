import os
import json
from datetime import date
from pathlib import Path

from google.cloud import bigquery
from google.oauth2 import service_account

# Kunci: dari Secrets (di server GitHub) atau dari file (di laptop)
kunci_teks = os.environ.get("GCP_KEY_JSON")
if kunci_teks:
    kredensial = service_account.Credentials.from_service_account_info(json.loads(kunci_teks))
else:
    kredensial = service_account.Credentials.from_service_account_file("kunci_gcp.json")

client = bigquery.Client(credentials=kredensial, project=kredensial.project_id)

BATAS_GB = 5   # pagar pengaman: tolak query yang membaca lebih dari 5 GB


def jalankan(nama, sql):
    # Langkah 1: "dry run" = hitung ukuran tanpa benar-benar menjalankan
    uji = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True))
    gb = uji.total_bytes_processed / 1e9
    if gb > BATAS_GB:
        print(f"🛑 {nama}: akan membaca {gb:.1f} GB, melebihi batas {BATAS_GB} GB. Dibatalkan.")
        return
    # Langkah 2: jalankan sungguhan
    df = client.query(sql).to_dataframe()
    folder = Path(f"data/raw/harian/{nama}")
    folder.mkdir(parents=True, exist_ok=True)
    file_out = folder / f"{date.today().isoformat()}.parquet"
    df.to_parquet(file_out, index=False)
    print(f"✅ {nama}: {len(df)} baris, membaca {gb * 1000:.1f} MB → {file_out}")


# ===== Daftar query =====
jalankan("bitcoin", """
    SELECT
      DATE(timestamp)        AS tanggal,
      COUNT(*)               AS jumlah_blok,
      SUM(transaction_count) AS jumlah_transaksi,
      SUM(size)              AS total_ukuran_byte,
      AVG(size)              AS rata_ukuran_blok
    FROM `bigquery-public-data.crypto_bitcoin.blocks`
    WHERE timestamp_month >= DATE_SUB(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL 1 MONTH)
    GROUP BY tanggal
    ORDER BY tanggal
""")