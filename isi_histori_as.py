import os
import math
import time
import logging
from pathlib import Path

import pandas as pd
import yfinance as yf
from huggingface_hub import HfApi, hf_hub_download

logging.getLogger("yfinance").setLevel(logging.CRITICAL)

REPO = "fadli-sparks/quant-data"
FOLDER_REPO = "raw/histori/saham_as"
token = os.environ.get("HF_TOKEN") or Path("kunci_hf.txt").read_text().strip()
api = HfApi(token=token)
MAKS = int(os.environ.get("MAKS_KELOMPOK", "30"))   # berapa bagian per run

lokal = Path("data") / FOLDER_REPO
lokal.mkdir(parents=True, exist_ok=True)


def upload():
    if any(lokal.glob("*.parquet")):
        api.upload_folder(folder_path=str(lokal), path_in_repo=FOLDER_REPO,
                          repo_id=REPO, repo_type="dataset",
                          commit_message="Isi histori saham AS")
        print("   ☁️  Ter-upload ke Hugging Face")


# ===== 1. Daftar kode yang DIKUNCI =====
files = api.list_repo_files(REPO, repo_type="dataset")
if f"{FOLDER_REPO}/daftar.parquet" in files:
    daftar = pd.read_parquet(hf_hub_download(REPO, f"{FOLDER_REPO}/daftar.parquet",
                                             repo_type="dataset", token=token))
    print("📋 Memakai daftar yang sudah dikunci")
else:
    harian = sorted(f for f in files if f.startswith("raw/harian/daftar_saham_as/"))
    daftar = pd.read_parquet(hf_hub_download(REPO, harian[-1], repo_type="dataset", token=token))
    daftar = daftar.sort_values("kode_yahoo").reset_index(drop=True)
    daftar.to_parquet(lokal / "daftar.parquet", index=False)
    print(f"📋 Mengunci daftar baru dari {harian[-1]}")

kode = daftar["kode_yahoo"].tolist()
total = math.ceil(len(kode) / 100)
sudah = {f for f in files if f.startswith(f"{FOLDER_REPO}/bagian_")}
print(f"   {len(kode)} kode = {total} bagian, sudah selesai: {len(sudah)}\n")

# ===== 2. Kerjakan bagian yang belum ada =====
dikerjakan = 0
for n in range(total):
    nama = f"bagian_{n:04d}.parquet"
    if f"{FOLDER_REPO}/{nama}" in sudah:
        continue
    if dikerjakan >= MAKS:
        break

    kelompok = kode[n * 100:(n + 1) * 100]
    try:
        df = yf.download(kelompok, period="max", interval="1d", auto_adjust=False,
                         progress=False, group_by="ticker", threads=True)
    except Exception as e:
        print(f"🛑 {nama}: {type(e).__name__}. Berhenti, jalankan lagi nanti.")
        break

    potongan = []
    for k in kelompok:
        if k in df.columns.get_level_values(0):
            d = df[k].dropna(subset=["Close"])
            if not d.empty:
                potongan.append(d.assign(kode=k))

    if len(potongan) < 10:   # hampir kosong = kemungkinan diblokir Yahoo
        print(f"🛑 {nama}: cuma {len(potongan)} kode berhasil, kemungkinan diblokir. Berhenti.")
        break

    gabung = pd.concat(potongan).reset_index().rename(columns={"Date": "tanggal"})
    gabung.to_parquet(lokal / nama, index=False)
    dikerjakan += 1
    print(f"✅ {nama}: {len(potongan)}/{len(kelompok)} kode, {len(gabung):,} baris")

    if dikerjakan % 10 == 0:
        upload()
    time.sleep(5)

upload()
selesai = len(sudah) + dikerjakan
print(f"\n📊 Progres: {selesai}/{total} bagian ({selesai / total:.0%})")
if selesai >= total:
    print("🎉 Histori saham AS LENGKAP!")