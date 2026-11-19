import os
import sys
from pathlib import Path

import duckdb
from huggingface_hub import HfApi, snapshot_download

REPO = "fadli-sparks/quant-data"
LOKAL = "--lokal" in sys.argv          # pakai file yang sudah ada di laptop, tanpa unduh/upload
BERSIH = Path("data/bersih")
BERSIH.mkdir(parents=True, exist_ok=True)

if not LOKAL:
    token = os.environ.get("HF_TOKEN") or Path("kunci_hf.txt").read_text().strip()
    print("⬇️  Mengunduh data mentah yang dibutuhkan dari gudang...")
    snapshot_download(REPO, repo_type="dataset", local_dir="data", token=token,
                      allow_patterns=["raw/harga_idx/*", "raw/harian/harga/*",
                                      "raw/histori/saham_as/bagian_*", "raw/harian/saham_as/*"])

db = duckdb.connect()
KOLOM = '"Open", "High", "Low", "Close", "Adj Close", "Volume"'


def ada(pola):
    return any(Path(".").glob(pola))


def tulis(nama, sql):
    """Jalankan query, simpan hasilnya ke data/bersih/<nama>.parquet, lalu laporkan."""
    file = BERSIH / f"{nama}.parquet"
    db.execute(f"COPY ({sql}) TO '{file.as_posix()}' (FORMAT parquet)")
    n, kode, awal, akhir = db.execute(
        f"SELECT COUNT(*), COUNT(DISTINCT kode), MIN(tanggal), MAX(tanggal) FROM '{file.as_posix()}'").fetchone()
    print(f"✅ {nama}: {n:,} baris, {kode:,} kode, {awal} s/d {akhir} ({file.stat().st_size / 1e6:.1f} MB)")


# Aturan umum: kalau tanggal + kode yang sama muncul di beberapa file,
# pakai versi dari file harian PALING BARU (paling mutakhir).
PILIH_TERBARU = "QUALIFY row_number() OVER (PARTITION BY tanggal, kode ORDER BY prioritas DESC, sumber DESC) = 1"

# ===== 1. Saham IDX: histori per saham + potongan harian =====
bagian = [f"""SELECT CAST("Date" AS DATE) AS tanggal,
                     regexp_extract(filename, '([^/\\\\]+)\\.parquet$', 1) || '.JK' AS kode,
                     {KOLOM}, 0 AS prioritas, '' AS sumber
              FROM read_parquet('data/raw/harga_idx/*.parquet', filename = true)"""]
if ada("data/raw/harian/harga/*.parquet"):
    bagian.append(f"""SELECT CAST(tanggal AS DATE) AS tanggal, kode, {KOLOM}, 1 AS prioritas,
                         regexp_extract(filename, '(\\d{{4}}-\\d{{2}}-\\d{{2}})', 1) AS sumber
                  FROM read_parquet('data/raw/harian/harga/*.parquet', filename = true, union_by_name = true)
                  WHERE kode LIKE '%.JK'""")
tulis("harga_idx", f"""SELECT CAST(tanggal AS TIMESTAMP) AS tanggal, kode, {KOLOM}
                       FROM ({' UNION ALL BY NAME '.join(bagian)})
                       WHERE "Close" IS NOT NULL
                       {PILIH_TERBARU}
                       ORDER BY kode, tanggal""")

# ===== 2. Saham & ETF AS: 129 bagian histori + potongan harian =====
bagian = [f"""SELECT CAST(tanggal AS DATE) AS tanggal, kode, {KOLOM}, 0 AS prioritas, '' AS sumber
              FROM read_parquet('data/raw/histori/saham_as/bagian_*.parquet', union_by_name = true)"""]
if ada("data/raw/harian/saham_as/*.parquet"):
    bagian.append(f"""SELECT CAST(tanggal AS DATE) AS tanggal, kode, {KOLOM}, 1 AS prioritas,
                         regexp_extract(filename, '(\\d{{4}}-\\d{{2}}-\\d{{2}})', 1) AS sumber
                  FROM read_parquet('data/raw/harian/saham_as/*.parquet', filename = true, union_by_name = true)""")
tulis("saham_as", f"""SELECT CAST(tanggal AS TIMESTAMP) AS tanggal, kode, {KOLOM}
                      FROM ({' UNION ALL BY NAME '.join(bagian)})
                      WHERE "Close" IS NOT NULL
                      {PILIH_TERBARU}
                      ORDER BY kode, tanggal""")

if not LOKAL:
    HfApi(token=token).upload_folder(folder_path=str(BERSIH), path_in_repo="bersih", repo_id=REPO,
                                     repo_type="dataset", commit_message="Perbarui data bersih")
    print("☁️  Ter-upload ke folder bersih/")