"""
SEKI Bank Indonesia (Statistik Ekonomi dan Keuangan Indonesia): ~108 tabel Excel resmi (uang beredar, kredit per sektor/
provinsi/kelompok bank, dana pihak ketiga, suku bunga, neraca pembayaran, utang luar negeri, keuangan pemerintah, dll.),
histori panjang. Halaman: https://www.bi.go.id/id/statistik/ekonomi-keuangan/seki/Default.aspx (robots.txt: Allow /).

BI MENIMPA file tiap pembaruan -> foto MINGGUAN; hanya tabel yang BERUBAH (sidik jari sha256) yang disimpan, jadi kita punya
riwayat revisi + tahu KAPAN angka baru terbit (cegah look-ahead: angka bulan m baru boleh dipakai setelah tanggal_ambil).

Isi:
  data/raw/seki/<tanggal UTC>/<TABELx_y>.xls   file asli yang berubah sejak foto sebelumnya (BIFF .xls; baca dengan xlrd)
  data/raw/seki/indeks.parquet                 semua versi: tabel, judul, tanggal_ambil, sha256, ukuran, jalur (DITIMPA, kumulatif)
Cara pakai:  python kumpul_seki.py      |   python kumpul_seki.py --tes   (3 tabel, tanpa simpan)
"""
import hashlib
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

HALAMAN = "https://www.bi.go.id/id/statistik/ekonomi-keuangan/seki/Default.aspx"
HEADER = {"User-Agent": "quant-data-collector/1.0 (personal research project)"}
HARI_INI = datetime.now(timezone.utc).date().isoformat()
TES = "--tes" in sys.argv
REPO = "fadli-sparks/quant-data"
MIN_TABEL_OK = 80


def ambil(url, biner=False):
    for percobaan in range(4):
        try:
            r = requests.get(url, headers=HEADER, timeout=(20, 120))
            r.raise_for_status()
            return r.content if biner else r.text
        except requests.RequestException as e:
            if percobaan == 3:
                raise
            print(f"   ⚠️  {url.split('/')[-1]}: {type(e).__name__}, coba lagi")
            time.sleep(15 * (percobaan + 1))


html = ambil(HALAMAN)
tautan = sorted(set(re.findall(r'href="(https://www\.bi\.go\.id/SEKI/tabel/[^"]+\.xls)"', html, re.I)))
judul = {}
for u in tautan:
    i = html.find(u)
    potong = html[max(0, i - 900):i]
    potong = potong[potong.find(">") + 1:potong.rfind("<")]           # buang tag terpotong di kedua ujung
    teks = re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", potong)).strip()
    m = list(re.finditer(r"[IVX]+\.\d+(?:\.\d+)*\.\s", teks))
    judul[u] = (teks[m[-1].start():] if m else teks[-150:]).strip()
print(f"📋 {len(tautan)} tabel SEKI di halaman")
if TES:
    tautan = tautan[:3]

# Indeks versi sebelumnya (dari gudang) -> sidik jari terakhir per tabel
if TES:
    lama = pd.DataFrame(columns=["tabel", "sha256"])
else:
    from huggingface_hub import HfApi, hf_hub_download
    token = os.environ.get("HF_TOKEN") or Path("kunci_hf.txt").read_text().strip()
    api = HfApi(token=token)
    try:
        lama = pd.read_parquet(hf_hub_download(REPO, "raw/seki/indeks.parquet", repo_type="dataset", token=token))
    except Exception as e:
        if "404" not in str(e) and "EntryNotFound" not in type(e).__name__:
            raise                                     # gagal membaca indeks yang ADA -> berhenti (jangan timpa riwayat)
        lama = pd.DataFrame(columns=["tabel", "judul", "tanggal_ambil", "sha256", "ukuran", "jalur"])
terakhir = lama.sort_values("tanggal_ambil").groupby("tabel")["sha256"].last().to_dict() if len(lama) else {}

folder = Path(f"data/raw/seki/{HARI_INI}")
baru, berhasil = [], 0
for u in tautan:
    nama = u.split("/")[-1]
    isi = ambil(u, biner=True)
    if not isi.startswith(b"\xd0\xcf\x11\xe0"):                  # tanda file Excel lama (BIFF/OLE)
        print(f"   ⚠️  {nama}: bukan file Excel ({isi[:20]!r}) -> dilewati")
        continue
    berhasil += 1
    sidik = hashlib.sha256(isi).hexdigest()
    tabel = nama.removesuffix(".xls")
    if terakhir.get(tabel) == sidik:
        continue
    jalur = f"raw/seki/{HARI_INI}/{nama}"
    baru.append({"tabel": tabel, "judul": judul[u], "tanggal_ambil": pd.Timestamp(HARI_INI), "sha256": sidik,
                 "ukuran": len(isi), "jalur": jalur})
    if not TES:
        folder.mkdir(parents=True, exist_ok=True)
        (folder / nama).write_bytes(isi)
    time.sleep(1)

print(f"✅ {berhasil} tabel terunduh, {len(baru)} BERUBAH/baru sejak foto sebelumnya")
for b in baru[:8]:
    print(f"   {b['tabel']:12} {b['ukuran'] / 1024:6.0f} KB  {b['judul'][:90]}")
if TES:
    print("🧪 mode tes: tidak disimpan")
    sys.exit()
if berhasil < MIN_TABEL_OK:
    print(f"❌ cuma {berhasil} tabel (min {MIN_TABEL_OK}) -> berhenti")
    sys.exit(1)
if baru:
    indeks = pd.concat([lama, pd.DataFrame(baru)], ignore_index=True)
    indeks["tanggal_ambil"] = pd.to_datetime(indeks["tanggal_ambil"]).astype("datetime64[ns]")
    for k in ["tabel", "judul", "sha256", "jalur"]:
        indeks[k] = indeks[k].astype("string")
    indeks["ukuran"] = indeks["ukuran"].astype("int64")
    Path("data/raw/seki").mkdir(parents=True, exist_ok=True)
    indeks.to_parquet("data/raw/seki/indeks.parquet", index=False)
    api.upload_folder(folder_path=str(folder), path_in_repo=f"raw/seki/{HARI_INI}", repo_id=REPO, repo_type="dataset",
                      commit_message=f"SEKI {HARI_INI}: {len(baru)} tabel berubah")
    api.upload_file(path_or_fileobj="data/raw/seki/indeks.parquet", path_in_repo="raw/seki/indeks.parquet", repo_id=REPO,
                    repo_type="dataset", commit_message=f"SEKI indeks {HARI_INI}")
    print(f"☁️  {len(baru)} tabel + indeks ({len(indeks)} versi) di gudang")
