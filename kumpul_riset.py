import io
import os
import sys
import time
import zipfile
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests
from huggingface_hub import HfApi

REPO = "fadli-sparks/quant-data"
HEADER = {"User-Agent": "quant-data-collector/1.0 (personal research project)"}
TES = "--tes" in sys.argv
hari_ini = date.today()


def ambil(url, params=None):
    for percobaan in range(4):
        try:
            r = requests.get(url, params=params, headers=HEADER, timeout=300)
            r.raise_for_status()
            return r
        except requests.exceptions.RequestException as e:
            print(f"   🔌 {type(e).__name__}, coba lagi...")
            time.sleep(15)
    return None


# =====================================================================
# 1. CFTC Commitments of Traders (COT): posisi spekulan vs hedger, mingguan
# =====================================================================
COT = {
    "cot_legacy":         "6dca-aqww",   # sejak 1986, semua komoditas & keuangan
    "cot_disaggregated":  "72hh-3qpy",   # sejak 2006, komoditas, pelaku lebih rinci
    "cot_keuangan":       "gpe5-46if",   # sejak 2006, futures keuangan (Traders in Financial Futures)
}
KOLOM_TANGGAL = "report_date_as_yyyy_mm_dd"


def ambil_cot(id_dataset, sejak=None):
    """Ambil data COT per halaman 50.000 baris (format CSV)."""
    halaman, offset = [], 0
    while True:
        params = {"$limit": 50000, "$offset": offset, "$order": ":id"}
        if sejak:
            params["$where"] = f"{KOLOM_TANGGAL} >= '{sejak}T00:00:00'"
        r = ambil(f"https://publicreporting.cftc.gov/resource/{id_dataset}.csv", params)
        if r is None:
            return None
        df = pd.read_csv(io.StringIO(r.text), low_memory=False)
        if df.empty:
            break
        halaman.append(df)
        offset += 50000
        if len(df) < 50000:
            break
    if not halaman:
        return pd.DataFrame()
    df = pd.concat(halaman, ignore_index=True)
    df[KOLOM_TANGGAL] = pd.to_datetime(df[KOLOM_TANGGAL])
    return df


token = os.environ.get("HF_TOKEN") or Path("kunci_hf.txt").read_text().strip()
api = HfApi(token=token)

for nama, id_dataset in COT.items():
    # a. Harian: laporan 8 minggu terakhir
    df = ambil_cot(id_dataset, sejak=(hari_ini - timedelta(weeks=8)).isoformat())
    if df is None or df.empty:
        print(f"⚠️  {nama}: gagal / kosong")
    else:
        folder = Path(f"data/raw/harian/{nama}")
        folder.mkdir(parents=True, exist_ok=True)
        df.to_parquet(folder / f"{hari_ini.isoformat()}.parquet", index=False)
        print(f"✅ {nama}: {len(df):,} baris, {df[KOLOM_TANGGAL].nunique()} minggu laporan")

    # b. Histori lengkap: hanya sekali, kalau belum ada di gudang
    jalur = f"raw/histori/cot/{nama}.parquet"
    if TES or api.file_exists(REPO, jalur, repo_type="dataset"):
        continue
    print(f"   ⬇️  {nama}: histori belum ada, mengambil semuanya...")
    df = ambil_cot(id_dataset)
    if df is not None and not df.empty:
        Path("data/raw/histori/cot").mkdir(parents=True, exist_ok=True)
        df.to_parquet(Path("data") / jalur, index=False)
        print(f"   ✅ histori {nama}: {len(df):,} baris sejak {df[KOLOM_TANGGAL].min().date()}")

# =====================================================================
# 2. Faktor Fama-French: return harian faktor-faktor riset akademis
# =====================================================================
FF = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
FAKTOR = {
    "ff3_harian":        "F-F_Research_Data_Factors_daily_CSV.zip",          # sejak 1926
    "ff5_harian":        "F-F_Research_Data_5_Factors_2x3_daily_CSV.zip",    # sejak 1963
    "momentum_harian":   "F-F_Momentum_Factor_daily_CSV.zip",                # sejak 1926
}


def baca_tabel_ff(teks):
    """File Fama-French berisi teks penjelasan + tabel. Ambil tabel pertamanya saja."""
    baris = teks.splitlines()
    header, data = None, []
    for i, b in enumerate(baris):
        kolom = [k.strip() for k in b.split(",")]
        if kolom[0].isdigit() and len(kolom[0]) == 8:      # baris data: tanggal YYYYMMDD
            if header is None:
                header = [k.strip() for k in baris[i - 1].split(",")]
            data.append(kolom)
        elif data:                                          # tabel pertama sudah selesai
            break
    df = pd.DataFrame(data, columns=["tanggal"] + header[1:])
    df["tanggal"] = pd.to_datetime(df["tanggal"], format="%Y%m%d")
    for k in df.columns[1:]:
        df[k] = pd.to_numeric(df[k], errors="coerce") / 100   # persen → desimal
    return df


folder = Path("data/raw/riset")
folder.mkdir(parents=True, exist_ok=True)
for nama, file_zip in FAKTOR.items():
    r = ambil(FF + file_zip)
    if r is None:
        print(f"⚠️  {nama}: gagal")
        continue
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        teks = z.read(z.namelist()[0]).decode("latin-1")
    df = baca_tabel_ff(teks)
    df.to_parquet(folder / f"{nama}.parquet", index=False)
    print(f"✅ {nama}: {len(df):,} hari, {df['tanggal'].min().date()} s/d {df['tanggal'].max().date()}, kolom {list(df.columns[1:])}")