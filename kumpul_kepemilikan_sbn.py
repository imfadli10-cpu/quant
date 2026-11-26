"""
KEPEMILIKAN SBN RUPIAH yang dapat diperdagangkan per jenis investor (DJPPR Kemenkeu) -> pengganti tidak langsung ARUS DANA ASING.
Halaman publik (dimuat situs djppr.kemenkeu.go.id sendiri lewat API-nya, slug dari menu beranda):
  /kepemilikansbndomestikyangdapatdiperdagangkan                       34 lampiran (26 Nov 2026): Excel 2003-2024 + PDF bulanan 2025+
  /kepemilikansbnrupiahyangdapatdiperdagangkanolehnonresiden            4 lampiran: asing per sektor & kelompok tenor (bulanan, 2008+)
Isi (Rp TRILIUN; SUN, SBSN, TOTAL): bank (konvensional/syariah), Bank Indonesia (net/gross/operasi moneter), reksadana, asuransi &
dana pensiun, NON RESIDEN (+ porsi pemerintah & bank sentral asing), individu, lain-lain. Bulanan 2003-2013 (2003-2009 SUN saja),
HARIAN sejak 2 Jan 2014. File bulan berjalan diperbarui beberapa hari sekali (23 Nov 2026 terlihat 26 Nov) -> ambil HARIAN.

Simpan (langsung ke gudang, seperti kumpul_seki.py):
  raw/kepemilikan_sbn/arsip/<media_id>__<nama asli>   file asli, HANYA versi baru (sha256) -> riwayat revisi & tanggal terbit
  raw/kepemilikan_sbn/indeks.parquet                   semua versi: halaman, judul, deskripsi, media_id, nama_file, sha256, waktu_ambil, jalur
  raw/kepemilikan_sbn/harian.parquet                   urai halaman utama: tanggal, kategori, jenis, nilai, label, media_id,
                                                       pertama_terlihat (waktu_ambil PALING AWAL file yang memuat angka itu;
                                                       histori lama = 2026-11-26, bukan tanggal terbit asli)
Lampiran halaman non-residen DIARSIPKAN mentah (belum diurai; urai saat riset membutuhkannya).
Pengurai & cek: sbn_kepemilikan.py (PDF diverifikasi lewat identitas hitung; tanggal salah ketik dikoreksi & dicetak).
Cek kewajaran (26 Nov 2026): non-residen 4 Sep 2026 Rp917,71 T (= infografik Kontan); porsi asing 38,6% (2019) -> 14,4% (2022);
  tanpa lompatan harian > 3% sejak 2014; identitas total = bank + institusi negara + non-bank cocok s/d 0,01 T semua hari.
Cara pakai:  python kumpul_kepemilikan_sbn.py   |   --tes (unduh & urai lampiran terbaru, tanpa simpan)
"""
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

import sbn_kepemilikan as sk

API = "https://api-djppr.kemenkeu.go.id/web/api/v1"
HALAMAN = {"utama": "kepemilikansbndomestikyangdapatdiperdagangkan",
           "non_residen": "kepemilikansbnrupiahyangdapatdiperdagangkanolehnonresiden"}
HEADER = {"User-Agent": "quant-data-collector/1.0 (personal research project)"}
REPO = "fadli-sparks/quant-data"
SEKARANG = pd.Timestamp(datetime.now(timezone.utc)).tz_localize(None).floor("s")
TES = "--tes" in sys.argv
MIN_LAMPIRAN = {"utama": 30, "non_residen": 3}
KOLOM_INDEKS = ["halaman", "judul", "deskripsi", "media_id", "nama_file", "sha256", "waktu_ambil", "jalur"]


def ambil(url, params=None, biner=False):
    for percobaan in range(4):
        try:
            r = requests.get(url, params=params, headers=HEADER, timeout=(20, 180))
            r.raise_for_status()
            return r if biner else r.json()
        except (requests.RequestException, ValueError) as e:
            if percobaan == 3:
                raise
            print(f"   ⚠️  {type(e).__name__}, coba lagi")
            time.sleep(15 * (percobaan + 1))


def lampiran(slug):
    isi = ambil(f"{API}/page", {"url": slug})["Data"]["PageContentLive"]
    keluar = []

    def jalan(o):
        if isinstance(o, dict):
            if "@link" in o and "/media/" in str(o.get("@link")):
                keluar.append((str(o.get("@judul", "")).strip(), str(o.get("@deskripsi", "")).strip(), o["@link"].split("/media/")[-1]))
            for v in o.values():
                jalan(v)
        elif isinstance(o, list):
            for v in o:
                jalan(v)
    jalan(json.loads(isi))
    return list(dict.fromkeys(keluar))          # buang dobel, urutan halaman (terbaru dulu) dipertahankan


def nama_dari(r, media_id):
    m = re.search(r'filename="?([^";]+)"?', r.headers.get("Content-Disposition", ""))
    nama = m.group(1) if m else media_id
    return re.sub(r"[^\w.\- ]", "_", nama).strip()


# ---- 1. daftar lampiran
daftar = {k: lampiran(v) for k, v in HALAMAN.items()}
for k, v in daftar.items():
    print(f"📋 halaman {k}: {len(v)} lampiran (terbaru: {v[0][0]} | {v[0][1]})" if v else f"📋 halaman {k}: 0 lampiran")
    if len(v) < MIN_LAMPIRAN[k]:
        print(f"❌ lampiran {k} cuma {len(v)} (min {MIN_LAMPIRAN[k]}) -> struktur halaman berubah? berhenti")
        sys.exit(1)

# ---- 2. indeks lama dari gudang
if TES:
    lama = pd.DataFrame(columns=KOLOM_INDEKS)
    lama_harian = None
else:
    from huggingface_hub import HfApi, hf_hub_download
    token = os.environ.get("HF_TOKEN") or Path("kunci_hf.txt").read_text().strip()
    api = HfApi(token=token)

    def unduh_lama(jalur, kolom=None):
        try:
            return pd.read_parquet(hf_hub_download(REPO, jalur, repo_type="dataset", token=token))
        except Exception as e:
            if "404" not in str(e) and "EntryNotFound" not in type(e).__name__:
                raise                             # gagal membaca file yang ADA -> berhenti (jangan timpa riwayat)
            return None if kolom is None else pd.DataFrame(columns=kolom)
    lama = unduh_lama("raw/kepemilikan_sbn/indeks.parquet", KOLOM_INDEKS)
    lama_harian = unduh_lama("raw/kepemilikan_sbn/harian.parquet")
sidik_lama = set(lama["sha256"]) if len(lama) else set()
id_lama = set(lama["media_id"]) if len(lama) else set()

# ---- 3. unduh: semua media_id yang belum pernah dilihat + 2 lampiran teratas tiap halaman (bisa ditimpa di tempat)
folder = Path(tempfile.mkdtemp(prefix="kep_sbn_")) if TES else Path("data/raw/kepemilikan_sbn/arsip")
folder.mkdir(parents=True, exist_ok=True)
baru, gagal_unduh = [], 0
for hal, item in daftar.items():
    for n, (judul, desk, mid) in enumerate(item):
        if TES and n > 1:
            break
        if mid in id_lama and n > 1:
            continue
        try:
            r = ambil(f"{API}/media/{mid}", biner=True)
        except requests.RequestException as e:
            print(f"   ⚠️  {judul} | {desk}: {type(e).__name__} -> dilewati")
            gagal_unduh += 1
            continue
        sidik = hashlib.sha256(r.content).hexdigest()
        time.sleep(2)
        if sidik in sidik_lama:
            continue
        nama = nama_dari(r, mid)
        jalur = folder / f"{mid}__{nama}"
        jalur.write_bytes(r.content)
        baru.append({"halaman": hal, "judul": judul, "deskripsi": desk, "media_id": mid, "nama_file": nama, "sha256": sidik,
                     "waktu_ambil": SEKARANG, "jalur": f"raw/kepemilikan_sbn/arsip/{jalur.name}", "_lokal": jalur})
        sidik_lama.add(sidik)
print(f"✅ {len(baru)} file baru/berubah (gagal unduh {gagal_unduh})")

# ---- 4. urai file baru halaman utama
potongan, gagal_urai = [], []
for b in baru:
    if b["halaman"] != "utama":
        continue
    try:
        h = sk.urai(b["_lokal"])
    except Exception as e:                        # simpan arsip tetap jalan; alarm di akhir
        gagal_urai.append(f"{b['nama_file']}: {type(e).__name__}: {str(e)[-150:]}")
        continue
    if h.empty:
        gagal_urai.append(f"{b['nama_file']}: 0 baris")
        continue
    h["media_id"], h["pertama_terlihat"] = b["media_id"], SEKARANG
    potongan.append(h)
    print(f"   {b['judul'][-40:]} | {b['deskripsi'][:40]}: {len(h):,} baris, {h['tanggal'].min():%Y-%m-%d} s/d {h['tanggal'].max():%Y-%m-%d}")
for k in sk.KOREKSI:
    print(f"   🔧 tanggal salah ketik di sumber dikoreksi: {Path(k[0]).name[:60]} lembar {k[1]}: {k[2]} -> {k[3]}")

KUNCI = ["tanggal", "kategori", "jenis"]
if potongan:
    urutan = {b["media_id"]: i for i, b in enumerate(baru)}          # urutan halaman: terbaru dulu
    nb = pd.concat(potongan, ignore_index=True)
    nb["_u"] = nb["media_id"].map(urutan)
    nb = nb.sort_values("_u").drop_duplicates(KUNCI, keep="first").drop(columns="_u")
    if lama_harian is not None and len(lama_harian):
        awal = lama_harian.groupby(KUNCI)["pertama_terlihat"].min()
        gabung = pd.concat([nb, lama_harian], ignore_index=True).drop_duplicates(KUNCI, keep="first")  # versi BARU menang
        gabung = gabung.set_index(KUNCI)
        gabung["pertama_terlihat"] = awal.reindex(gabung.index).fillna(gabung["pertama_terlihat"])
        harian = gabung.reset_index()
    else:
        harian = nb
    harian = harian[KUNCI + ["nilai", "label", "media_id", "pertama_terlihat"]].sort_values(KUNCI).reset_index(drop=True)
    harian["tanggal"] = pd.to_datetime(harian["tanggal"]).astype("datetime64[ns]")
    harian["pertama_terlihat"] = pd.to_datetime(harian["pertama_terlihat"]).astype("datetime64[ns]")
    for k in ["kategori", "jenis", "label", "media_id"]:
        harian[k] = harian[k].astype("string")
    harian["nilai"] = harian["nilai"].astype("float64")
    nr = harian[(harian["kategori"] == "non_residen") & (harian["jenis"] == "TOTAL")].set_index("tanggal")["nilai"]
    print(f"📊 harian: {len(harian):,} baris, {harian['tanggal'].nunique():,} tanggal, {harian['tanggal'].min():%Y-%m-%d} s/d "
          f"{harian['tanggal'].max():%Y-%m-%d}; non-residen terakhir Rp{nr.iloc[-1]:,.2f} T ({nr.index[-1]:%Y-%m-%d})")
else:
    harian = None

if TES:
    print("🧪 mode tes: tidak disimpan")
    sys.exit(1 if gagal_urai else 0)

# ---- 5. simpan ke gudang
if baru:
    indeks = pd.concat([lama, pd.DataFrame(baru).drop(columns="_lokal")], ignore_index=True)
    indeks["waktu_ambil"] = pd.to_datetime(indeks["waktu_ambil"]).astype("datetime64[ns]")
    for k in [c for c in KOLOM_INDEKS if c != "waktu_ambil"]:
        indeks[k] = indeks[k].astype("string")
    Path("data/raw/kepemilikan_sbn").mkdir(parents=True, exist_ok=True)
    indeks.to_parquet("data/raw/kepemilikan_sbn/indeks.parquet", index=False)
    # SATU commit atomik (arsip + harian + indeks): putus koneksi di tengah tidak meninggalkan gudang setengah jadi
    from huggingface_hub import CommitOperationAdd
    ops = [CommitOperationAdd(path_in_repo=b["jalur"], path_or_fileobj=str(b["_lokal"])) for b in baru]
    if harian is not None:
        harian.to_parquet("data/raw/kepemilikan_sbn/harian.parquet", index=False)
        ops.append(CommitOperationAdd(path_in_repo="raw/kepemilikan_sbn/harian.parquet",
                                      path_or_fileobj="data/raw/kepemilikan_sbn/harian.parquet"))
    ops.append(CommitOperationAdd(path_in_repo="raw/kepemilikan_sbn/indeks.parquet", path_or_fileobj="data/raw/kepemilikan_sbn/indeks.parquet"))
    for percobaan in range(4):
        try:
            api.create_commit(repo_id=REPO, repo_type="dataset", operations=ops,
                              commit_message=f"Kepemilikan SBN {SEKARANG:%Y-%m-%d}: {len(baru)} file baru")
            break
        except Exception as e:
            if percobaan == 3:
                raise
            print(f"   ⚠️  upload gagal ({type(e).__name__}), coba lagi")
            time.sleep(60 * (percobaan + 1))
    print(f"☁️  {len(baru)} file + indeks ({len(indeks)} versi) di gudang")
else:
    print("   tidak ada file baru (normal: DJPPR memperbarui beberapa hari sekali)")

if gagal_urai:
    print("❌ GAGAL URAI (arsip tetap tersimpan; perbaiki sbn_kepemilikan.py):")
    for g in gagal_urai:
        print(f"   {g}")
    sys.exit(1)
