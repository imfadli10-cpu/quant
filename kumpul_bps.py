import os
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests
from huggingface_hub import HfApi, hf_hub_download

KUNCI = os.environ.get("BPS_KEY") or Path("kunci_bps.txt").read_text().strip()
API = "https://webapi.bps.go.id/v1/api/list"
REPO = "fadli-sparks/quant-data"
TES = "--tes" in sys.argv
HISTORI = "--histori" in sys.argv
BULAN = {"Januari": 1, "Februari": 2, "Maret": 3, "April": 4, "Mei": 5, "Juni": 6, "Juli": 7,
         "Agustus": 8, "September": 9, "Oktober": 10, "November": 11, "Desember": 12}


def minta(params):
    """Satu permintaan ke API BPS tingkat nasional (domain 0000)."""
    params = {**params, "domain": "0000", "key": KUNCI}
    for percobaan in range(4):
        try:
            r = requests.get(API, params=params, timeout=60)
            if r.status_code == 429:
                time.sleep(20 * (percobaan + 1))
                continue
            if 400 <= r.status_code < 500:      # kesalahan permintaan: percuma diulang
                return r.json()
            r.raise_for_status()
            return r.json()
        except (requests.exceptions.RequestException, ValueError):
            time.sleep(10)
    return None


def daftar_halaman(params):
    """Ambil semua halaman dari sebuah daftar BPS (variabel, tahun, dll.)."""
    hasil, halaman = [], 1
    while True:
        j = minta({**params, "page": halaman})
        if not j or j.get("data-availability") != "available":
            break
        info, isi = j["data"][0], j["data"][1]
        hasil += isi
        if halaman >= info.get("pages", 1):
            break
        if TES and params.get("model") == "var" and len(hasil) >= 20:
            break
        halaman += 1
        time.sleep(0.3)
    return hasil


def urai(v, j):
    """BPS menyimpan nilai dengan kunci gabungan: wilayah+var+kategori+tahun+periode."""
    data = j.get("datacontent") or {}
    vid = v["var_id"]
    baris = []
    for vv in j.get("vervar") or [{"val": "", "label": ""}]:
        for tv in j.get("turvar") or [{"val": 0, "label": ""}]:
            for th in j.get("tahun") or []:
                for tt in j.get("turtahun") or [{"val": 0, "label": ""}]:
                    kunci = f"{vv['val']}{vid}{tv['val']}{th['val']}{tt['val']}"
                    if kunci in data:
                        baris.append({
                            "var_id": vid, "judul": v.get("title"), "satuan": v.get("unit"),
                            "wilayah": vv["label"], "kategori": tv["label"],
                            "tahun": th["label"], "periode": tt["label"], "nilai": data[kunci],
                        })
    return baris


def ambil_variabel(v, kode_tahun):
    """Ambil data satu variabel untuk daftar kode tahun, 3 tahun per permintaan (batas BPS)."""
    baris = []
    for i in range(0, len(kode_tahun), 3):
        potong = kode_tahun[i:i + 3]
        j = minta({"model": "data", "var": v["var_id"], "th": ";".join(str(k) for k in potong)})
        if j and j.get("data-availability") == "available":
            baris += urai(v, j)
        time.sleep(0.3)
    return baris


def simpan(baris, file):
    df = pd.DataFrame(baris)
    df["nilai"] = pd.to_numeric(df["nilai"], errors="coerce")
    df["tahun"] = pd.to_numeric(df["tahun"], errors="coerce").astype("Int64")
    df["bulan"] = df["periode"].map(BULAN).astype("Int64")
    for kolom in ["judul", "satuan", "wilayah", "kategori", "periode"]:
        df[kolom] = df[kolom].astype("string")
    file.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(file, index=False)
    print(f"   💾 {file.name}: {df['var_id'].nunique()} variabel, {len(df):,} baris")


# =====================================================================
# MODE BULANAN: semua variabel, 3 tahun terakhir (1 permintaan per variabel)
# =====================================================================
if not HISTORI:
    semua = daftar_halaman({"model": "var"})
    folder = Path("data/raw/bps")
    folder.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(semua).astype(str).to_parquet(folder / "daftar_variabel.parquet", index=False)
    if TES:
        semua = semua[:20]
    print(f"📋 {len(semua)} variabel nasional{' (mode tes)' if TES else ''}")

    kode = [date.today().year - 1900 - 2, date.today().year - 1900 - 1, date.today().year - 1900]
    baris, nomor, berisi = [], 0, 0
    for i, v in enumerate(semua, start=1):
        hasil = ambil_variabel(v, kode)
        berisi += bool(hasil)
        baris += hasil
        if TES or i % 100 == 0:
            print(f"  ... {i}/{len(semua)}  [{v['var_id']}] {'✅' if hasil else '⚪'} {str(v.get('title'))[:50]}")
        if (i % 300 == 0 or i == len(semua)) and baris:
            simpan(baris, folder / "terbaru" / f"bagian_{nomor:02d}.parquet")
            baris, nomor = [], nomor + 1
    print(f"\n🎉 Selesai. {berisi} dari {len(semua)} variabel punya data {kode[0] + 1900}-{kode[-1] + 1900}")
    sys.exit()

# =====================================================================
# MODE HISTORI: semua tahun, dicicil per 100 variabel, bisa dilanjutkan
# =====================================================================
token = os.environ.get("HF_TOKEN") or Path("kunci_hf.txt").read_text().strip()
api = HfApi(token=token)
FOLDER_REPO = "raw/histori/bps"
MAKS = int(os.environ.get("MAKS_KELOMPOK", "10"))
lokal = Path("data") / FOLDER_REPO
lokal.mkdir(parents=True, exist_ok=True)

files = api.list_repo_files(REPO, repo_type="dataset")
if f"{FOLDER_REPO}/daftar.parquet" in files:
    daftar = pd.read_parquet(hf_hub_download(REPO, f"{FOLDER_REPO}/daftar.parquet",
                                             repo_type="dataset", token=token))
    print("📋 Memakai daftar variabel yang sudah dikunci")
else:
    daftar = pd.DataFrame(daftar_halaman({"model": "var"})).astype(str)
    daftar = daftar.sort_values("var_id", key=lambda s: s.astype(int)).reset_index(drop=True)
    daftar.to_parquet(lokal / "daftar.parquet", index=False)
    print("📋 Mengunci daftar variabel baru")

semua = daftar.to_dict("records")
total = (len(semua) + 99) // 100
sudah = {f for f in files if f.startswith(f"{FOLDER_REPO}/bagian_")}
print(f"   {len(semua)} variabel = {total} bagian, sudah selesai: {len(sudah)}\n")


def upload():
    if any(lokal.glob("*.parquet")):
        api.upload_folder(folder_path=str(lokal), path_in_repo=FOLDER_REPO, repo_id=REPO,
                          repo_type="dataset", commit_message="Isi histori BPS")
        print("   ☁️  Ter-upload ke Hugging Face")


dikerjakan = 0
for n in range(total):
    nama = f"bagian_{n:03d}.parquet"
    if f"{FOLDER_REPO}/{nama}" in sudah:
        continue
    if dikerjakan >= MAKS:
        break
    baris = []
    for v in semua[n * 100:(n + 1) * 100]:
        tahun = sorted({int(t["th_id"]) for t in daftar_halaman({"model": "th", "var": v["var_id"]})})
        baris += ambil_variabel(v, tahun)
    if baris:
        simpan(baris, lokal / nama)
    else:
        pd.DataFrame(columns=["var_id"]).to_parquet(lokal / nama, index=False)   # tanda: sudah dicek, kosong
        print(f"   ⚪ {nama}: tidak ada data")
    dikerjakan += 1
    if dikerjakan % 5 == 0:
        upload()

upload()
selesai = len(sudah) + dikerjakan
print(f"\n📊 Progres: {selesai}/{total} bagian ({selesai / total:.0%})")
if selesai >= total:
    print("🎉 Histori BPS LENGKAP!")