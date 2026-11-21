"""
WORLD BANK 'PINK SHEET': harga BULANAN ~71 komoditas sejak 1960 + indeks harga komoditas (data resmi Bank Dunia, gratis).
Halaman: https://www.worldbank.org/en/research/commodity-markets (robots.txt tidak melarang). Tautan Excel berisi ID dokumen
yang BERUBAH tiap terbitan -> selalu dicari dari halaman resmi.

Banyak ekspor utama Indonesia: minyak sawit & inti sawit, kelapa, karet (TSR20, RSS3), timah, nikel, batu bara (Australia,
Afrika Selatan), kopi robusta, kakao, LNG, kayu & kayu lapis Malaysia, emas.
Isi:
  data/raw/worldbank/harga_bulanan.parquet    format panjang: komoditas, satuan, bulan, harga (DITIMPA)
  data/raw/worldbank/indeks_bulanan.parquet   indeks harga (energi, non-energi, pertanian, logam, pupuk...) (DITIMPA)
  data/raw/worldbank/arsip/<tanggal_terbit>.xlsx   file asli tiap TERBITAN BARU (lacak revisi & tanggal terbit = point-in-time)
Cara pakai: python kumpul_pinksheet.py | --tes (tanpa simpan)
"""
import io
import os
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests

H = {"User-Agent": "quant-data-collector/1.0 (personal research project)"}
HALAMAN = "https://www.worldbank.org/en/research/commodity-markets"
TES = "--tes" in sys.argv
REPO = "fadli-sparks/quant-data"


def ambil(url, biner=False):
    for percobaan in range(4):
        try:
            r = requests.get(url, headers=H, timeout=(20, 180))
            r.raise_for_status()
            return r.content if biner else r.text
        except requests.RequestException:
            if percobaan == 3:
                raise
            time.sleep(15 * (percobaan + 1))


def lebar_ke_panjang(v, nama_lembar):
    """Header = baris 4 s/d sebelum baris data pertama (kolom 0 = 'YYYYMmm'). Per kolom: teks terisi PERTAMA = nama,
    teks berikutnya = satuan (lembar harga: '($/bbl)'); lembar indeks bertingkat (nama di baris 5-8) -> satuan 'indeks 2010=100'.
    '…' = kosong."""
    kol0 = v[0].astype(str)
    awal = int(kol0[kol0.str.fullmatch(r"\d{4}M\d{2}")].index[0])
    nama, satuan = {}, {}
    for j in range(1, v.shape[1]):
        teks = [str(c).strip() for c in v.iloc[4:awal, j].tolist() if pd.notna(c) and str(c).strip() not in ("", "nan")]
        if teks:
            nama[j] = teks[0]
            satuan[j] = teks[1] if len(teks) > 1 else "indeks 2010=100"
    data = v.iloc[awal:].copy()
    data = data[data[0].astype(str).str.fullmatch(r"\d{4}M\d{2}")]
    bulan = pd.to_datetime(data[0].astype(str).str.replace("M", "-") + "-01")
    bag = []
    for j in nama:
        x = pd.to_numeric(data[j].replace("…", None), errors="coerce")
        bag.append(pd.DataFrame({"komoditas": nama[j].replace(" **", "").strip(), "satuan": satuan[j], "bulan": bulan.values,
                                 "harga": x.values}))
    d = pd.concat(bag, ignore_index=True).dropna(subset=["harga"])
    d["komoditas"] = d["komoditas"].astype("string")
    d["satuan"] = d["satuan"].astype("string")
    d["bulan"] = d["bulan"].astype("datetime64[ns]")
    return d


html = ambil(HALAMAN)
tautan = re.findall(r'href="([^"]+CMO-Historical-Data-Monthly\.xlsx)"', html, re.I)
if not tautan:
    sys.exit("❌ tautan CMO-Historical-Data-Monthly.xlsx tidak ditemukan (halaman berubah?)")
isi = ambil(tautan[0], biner=True)
x = pd.read_excel(io.BytesIO(isi), sheet_name=None, header=None)
m = re.search(r"Updated on (\w+ \d{1,2}, \d{4})", str(x["Monthly Prices"].iat[3, 0]))
terbit = pd.to_datetime(m.group(1)) if m else pd.NaT
harga = lebar_ke_panjang(x["Monthly Prices"], "harga")
indeks = lebar_ke_panjang(x["Monthly Indices"], "indeks") if "Monthly Indices" in x else pd.DataFrame()
print(f"✅ Pink Sheet terbit {terbit:%Y-%m-%d}: {harga['komoditas'].nunique()} komoditas, {len(harga):,} baris, "
      f"{harga['bulan'].min():%Y-%m} s/d {harga['bulan'].max():%Y-%m} | indeks {indeks['komoditas'].nunique() if len(indeks) else 0}")
akhir = harga[harga["bulan"] == harga["bulan"].max()].set_index("komoditas")["harga"]
print("   terakhir: " + ", ".join(f"{k} {akhir[k]:,.1f}" for k in ["Palm oil", "Coal, Australian", "Nickel", "Tin", "Rubber, TSR20"]
                                    if k in akhir))
if harga["komoditas"].nunique() < 60:
    print("❌ komoditas terlalu sedikit -> berhenti")
    sys.exit(1)
if TES:
    print("🧪 mode tes: tidak disimpan")
    sys.exit()
folder = Path("data/raw/worldbank")
(folder / "arsip").mkdir(parents=True, exist_ok=True)
harga.to_parquet(folder / "harga_bulanan.parquet", index=False)
if len(indeks):
    indeks.to_parquet(folder / "indeks_bulanan.parquet", index=False)
from huggingface_hub import HfApi
api = HfApi(token=os.environ.get("HF_TOKEN") or Path("kunci_hf.txt").read_text().strip())
nama_arsip = f"{terbit:%Y-%m-%d}.xlsx" if pd.notna(terbit) else "tanpa_tanggal.xlsx"
sudah = set(api.list_repo_files(REPO, repo_type="dataset"))
if f"raw/worldbank/arsip/{nama_arsip}" not in sudah:
    (folder / "arsip" / nama_arsip).write_bytes(isi)
    print(f"🆕 terbitan baru -> arsip/{nama_arsip}")
api.upload_folder(folder_path=str(folder), path_in_repo="raw/worldbank", repo_id=REPO, repo_type="dataset",
                  commit_message=f"Pink Sheet {nama_arsip}")
print("☁️  raw/worldbank di gudang")
