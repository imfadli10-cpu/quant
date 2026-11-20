import os
import time
from datetime import date
from pathlib import Path

import pandas as pd
import yfinance as yf
from huggingface_hub import hf_hub_download

REPO = "fadli-sparks/quant-data"
token = os.environ.get("HF_TOKEN") or Path("kunci_hf.txt").read_text().strip()

# 1. Daftar saham IDX = daftar awal + kode baru yang ditemukan kumpul_daftar_idx.py (lihat daftar_saham.py)
from daftar_saham import kode_idx as ambil_kode_idx
kode_idx = ambil_kode_idx()

# Aset global yang juga dipantau
GLOBAL = [
    "^JKSE", "^GSPC", "GC=F", "CL=F", "IDR=X", "BTC-USD",
    "^N225", "^HSI", "000001.SS", "^STI", "^KLSE", "^SET.BK", "PSEI.PS",
    "^BSESN", "^NSEI", "^KS11", "^TWII", "^AXJO",
    "^FTSE", "^GDAXI", "^FCHI", "^STOXX50E", "^DJI", "^IXIC", "^RUT", "^BVSP",
    "^VIX", "DX-Y.NYB", "^TNX",
    "SI=F", "HG=F", "PL=F", "PA=F", "BZ=F", "NG=F", "RB=F", "HO=F",
    "ZC=F", "ZW=F", "ZS=F", "ZM=F", "ZL=F", "KC=F", "CC=F", "SB=F", "CT=F", "LE=F", "HE=F", "OJ=F",
    "CPO=F",   # sawit (CME, mengikuti harga sawit Malaysia), ditambahkan 19 Nov 2026
]
semua_kode = kode_idx + GLOBAL
print(f"Mengambil 7 hari terakhir untuk {len(semua_kode)} kode...\n")

# 2. Ambil per kelompok 100 kode supaya tidak diblokir Yahoo
hasil = []
for i in range(0, len(semua_kode), 100):
    kelompok = semua_kode[i:i + 100]
    df = yf.download(kelompok, period="7d", interval="1d", auto_adjust=False,
                     progress=False, group_by="ticker", threads=True)

    for kode in kelompok:
        if kode not in df.columns.get_level_values(0):
            continue
        data_kode = df[kode].dropna(subset=["Close"])
        if data_kode.empty:
            continue
        hasil.append(data_kode.assign(kode=kode))

    print(f"  Kelompok {i // 100 + 1}: selesai ({min(i + 100, len(semua_kode))}/{len(semua_kode)})")
    time.sleep(5)

# 3. Gabung jadi satu tabel panjang, lalu simpan sebagai potongan hari ini
gabung = pd.concat(hasil).reset_index().rename(columns={"Date": "tanggal"})
folder = Path("data/raw/harian/harga")
folder.mkdir(parents=True, exist_ok=True)
file_out = folder / f"{date.today().isoformat()}.parquet"
gabung.to_parquet(file_out, index=False)

print(f"\n✅ {gabung['kode'].nunique()} kode, {len(gabung)} baris → {file_out}")