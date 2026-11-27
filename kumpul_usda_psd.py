"""
USDA FAS PSD (Production, Supply & Distribution) -> SEMUA versi basis data neraca komoditas pertanian dunia (point-in-time)
Sumber: https://apps.fas.usda.gov/psdonline/downloads/psd_alldata_csv.zip (unduhan publik, robots.txt kosong; tanpa kunci).
Isi: ~2,1 juta baris, 63 komoditas x 214 negara, tahun pemasaran 1960+: produksi, STOK AWAL/AKHIR, ekspor, impor, konsumsi, luas panen, hasil.
  Penting utk IDX: Oil, Palm (Indonesia/Malaysia produksi-ekspor-stok; India/China/UE impor), Oil, Palm Kernel, Oil, Soybean (pesaing sawit),
  Corn/Wheat/Rice, Sugar, Coffee, Cocoa, Cotton, Rubber? (TIDAK ada di PSD). Satuan per baris (Unit_Description, mis. '(1000 MT)').
USDA MENIMPA file tiap pembaruan (WASDE ~tgl 8-12 tiap bulan + pembaruan negara lain) -> versi lama hilang. Kolom Calendar_Year/Month =
  KAPAN angka baris itu terakhir direvisi. Collector ini menyimpan SETIAP versi baru (sidik sha256 isi CSV) -> riwayat revisi & tanggal
  terbit nyata (point-in-time) MULAI 27 Nov 2026; sebelum itu hanya versi terakhir (angka terrevisi).
SIMPAN (langsung ke gudang, satu commit atomik):
  raw/usda_psd/versi/<Last-Modified YYYY-MM-DD>__<sha8>.parquet   seluruh tabel (kode & nama komoditas/negara/atribut, Market_Year,
                                                                  Calendar_Year, Month = int; Value = float)
  raw/usda_psd/indeks.parquet   last_modified (header server), sha256, baris, waktu_ambil, jalur
Cek harian murah: HEAD (Last-Modified); unduh hanya kalau berubah dari versi terakhir di indeks. Gagal membaca indeks yang ADA -> berhenti.
Cara pakai: python kumpul_usda_psd.py  |  --tes (unduh & ringkas, tanpa simpan)
"""
import hashlib
import io
import os
import sys
import time
import zipfile
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import pandas as pd
import requests

URL = "https://apps.fas.usda.gov/psdonline/downloads/psd_alldata_csv.zip"
H = {"User-Agent": "quant-data-collector/1.0 (personal research project)"}
REPO = "fadli-sparks/quant-data"
TES = "--tes" in sys.argv
SEKARANG = datetime.now(timezone.utc)
KOLOM_INDEKS = ["last_modified", "sha256", "baris", "waktu_ambil", "jalur"]


def minta(metode):
    for coba in range(4):
        try:
            r = requests.request(metode, URL, headers=H, timeout=(20, 300))
            if r.status_code == 200:
                return r
            print(f"   ⚠️ HTTP {r.status_code}")
        except requests.RequestException as e:
            print(f"   🔌 {type(e).__name__}")
        time.sleep(15 * (coba + 1))
    return None


kepala = minta("HEAD")
if kepala is None:
    print("❌ server USDA tidak menjawab")
    sys.exit(1)
lm = pd.Timestamp(parsedate_to_datetime(kepala.headers["Last-Modified"])).tz_convert(None)
print(f"🌾 PSD Last-Modified {lm} (UTC), ukuran {int(kepala.headers.get('Content-Length', 0)) / 1e6:.1f} MB")

if TES:
    lama = pd.DataFrame(columns=KOLOM_INDEKS)
else:
    from huggingface_hub import CommitOperationAdd, HfApi, hf_hub_download
    token = os.environ.get("HF_TOKEN") or Path("kunci_hf.txt").read_text().strip()
    api = HfApi(token=token)
    try:
        lama = pd.read_parquet(hf_hub_download(REPO, "raw/usda_psd/indeks.parquet", repo_type="dataset", token=token))
    except Exception as e:
        if "404" not in str(e) and "EntryNotFound" not in type(e).__name__:
            raise                                    # indeks ADA tapi gagal dibaca -> berhenti (jangan timpa riwayat)
        lama = pd.DataFrame(columns=KOLOM_INDEKS)
    if len(lama) and (pd.to_datetime(lama["last_modified"]) >= lm).any():
        print(f"✅ versi {lm:%Y-%m-%d %H:%M} sudah tersimpan ({len(lama)} versi di indeks) -> tidak ada yang diunduh")
        sys.exit()

r = minta("GET")
if r is None:
    print("❌ unduhan gagal")
    sys.exit(1)
z = zipfile.ZipFile(io.BytesIO(r.content))
mentah = z.read(z.namelist()[0])
sidik = hashlib.sha256(mentah).hexdigest()
d = pd.read_csv(io.BytesIO(mentah), dtype=str, keep_default_na=False)
for c in ("Market_Year", "Calendar_Year", "Month"):
    d[c] = pd.to_numeric(d[c], errors="coerce").astype("Int64")
d["Value"] = pd.to_numeric(d["Value"], errors="coerce")
for c in d.columns:
    if d[c].dtype == object or str(d[c].dtype) in ("str", "string"):
        d[c] = d[c].str.strip().astype("string")
sawit = d[(d["Country_Name"] == "Indonesia") & (d["Commodity_Description"] == "Oil, Palm") & (d["Attribute_Description"] == "Production")]
akhir = sawit.sort_values("Market_Year").tail(2)
print(f"✅ {len(d):,} baris, {d['Commodity_Description'].nunique()} komoditas, {d['Country_Name'].nunique()} negara, tahun {d['Market_Year'].min()}–"
      f"{d['Market_Year'].max()}; revisi terbaru {int(d['Calendar_Year'].max())}-{int(d.loc[d['Calendar_Year'] == d['Calendar_Year'].max(), 'Month'].max()):02d}")
print("   sawit Indonesia produksi: " + " | ".join(f"MY{int(a)} {v:,.0f} {u} (direvisi {int(cy)}-{int(m):02d})"
                                                for a, v, u, cy, m in akhir[["Market_Year", "Value", "Unit_Description", "Calendar_Year", "Month"]].values))
if len(d) < 1_000_000 or akhir.empty:
    print("❌ isi terlalu sedikit / sawit Indonesia hilang -> curigai format berubah")
    sys.exit(1)
if TES:
    print("🧪 mode tes: tidak disimpan")
    sys.exit()
if len(lama) and sidik in set(lama["sha256"]):
    print("✅ isi sama dgn versi tersimpan (hanya Last-Modified berubah) -> indeks dicatat, data tidak diunggah ulang")
    jalur = lama.loc[lama["sha256"] == sidik, "jalur"].iloc[0]
    ops_data = []
else:
    jalur = f"raw/usda_psd/versi/{lm:%Y-%m-%d}__{sidik[:8]}.parquet"
    lokal = Path("data") / jalur
    lokal.parent.mkdir(parents=True, exist_ok=True)
    d.to_parquet(lokal, index=False)
    print(f"💾 {lokal} ({lokal.stat().st_size / 1e6:.1f} MB)")
    ops_data = [CommitOperationAdd(path_in_repo=jalur, path_or_fileobj=str(lokal))]
baru = pd.DataFrame([{"last_modified": lm, "sha256": sidik, "baris": len(d), "waktu_ambil": pd.Timestamp(SEKARANG).tz_localize(None).floor("s"),
                      "jalur": jalur}])
indeks = pd.concat([lama, baru], ignore_index=True) if len(lama) else baru
indeks["last_modified"] = pd.to_datetime(indeks["last_modified"]).astype("datetime64[ns]")
indeks["waktu_ambil"] = pd.to_datetime(indeks["waktu_ambil"]).astype("datetime64[ns]")
indeks["baris"] = indeks["baris"].astype("int64")
for k in ("sha256", "jalur"):
    indeks[k] = indeks[k].astype("string")
Path("data/raw/usda_psd").mkdir(parents=True, exist_ok=True)
indeks.to_parquet("data/raw/usda_psd/indeks.parquet", index=False)
ops = ops_data + [CommitOperationAdd(path_in_repo="raw/usda_psd/indeks.parquet", path_or_fileobj="data/raw/usda_psd/indeks.parquet")]
for percobaan in range(4):
    try:
        api.create_commit(repo_id=REPO, repo_type="dataset", operations=ops, commit_message=f"USDA PSD versi {lm:%Y-%m-%d}")
        break
    except Exception as e:
        if percobaan == 3:
            raise
        print(f"   ⚠️ upload gagal ({type(e).__name__}), coba lagi")
        time.sleep(60 * (percobaan + 1))
print(f"☁️  indeks {len(indeks)} versi di gudang")
