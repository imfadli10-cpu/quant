import os
import json
import warnings
from datetime import date
from pathlib import Path

from google.cloud import bigquery
from google.oauth2 import service_account

warnings.filterwarnings("ignore", message="BigQuery Storage module not found")

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
    if df.empty:
        print(f"⚠️  {nama}: 0 baris (sumber belum diperbarui?), tidak disimpan")
        return
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

jalankan("ethereum", """
    SELECT
      DATE(timestamp)             AS tanggal,
      COUNT(*)                    AS jumlah_blok,
      SUM(transaction_count)      AS jumlah_transaksi,
      SUM(gas_used)               AS total_gas,
      AVG(base_fee_per_gas) / 1e9 AS rata_base_fee_gwei
    FROM `bigquery-public-data.crypto_ethereum.blocks`
    WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 14 DAY)
    GROUP BY tanggal
    ORDER BY tanggal
""")

jalankan("berita_gdelt", """
    SELECT
      DATE(_PARTITIONTIME) AS tanggal,
      CASE ActionGeo_CountryCode
        WHEN 'ID' THEN 'indonesia'
        WHEN 'US' THEN 'amerika'
        WHEN 'CH' THEN 'tiongkok'
        WHEN 'JA' THEN 'jepang'
        WHEN 'RS' THEN 'rusia'
        ELSE 'lainnya'
      END AS negara,
      COUNT(*)                           AS jumlah_peristiwa,
      AVG(AvgTone)                       AS rata_nada,
      AVG(GoldsteinScale)                AS rata_goldstein,
      AVG(IF(QuadClass IN (3, 4), 1, 0)) AS porsi_konflik
    FROM `gdelt-bq.gdeltv2.events_partitioned`
    WHERE _PARTITIONTIME >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 14 DAY)
    GROUP BY tanggal, negara
    ORDER BY tanggal, negara
""")

jalankan("google_trends_id", """
    SELECT
      refresh_date,
      week,
      term,
      MIN(rank)  AS peringkat,
      AVG(score) AS rata_skor
    FROM `bigquery-public-data.google_trends.international_top_terms`
    WHERE refresh_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
      AND country_code = 'ID'
      AND week >= DATE_SUB(CURRENT_DATE(), INTERVAL 21 DAY)
    GROUP BY refresh_date, week, term
    QUALIFY refresh_date = MAX(refresh_date) OVER ()
    ORDER BY week, peringkat
""")