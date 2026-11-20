"""
TITIK API (kebakaran hutan/lahan) di Indonesia & sekitarnya dari satelit NASA FIRMS.

Kenapa: kebakaran lahan gambut & hutan Sumatra/Kalimantan = kabut asap (ekonomi & kesehatan), terkait El Nino, dan
LANGSUNG menyentuh emiten perkebunan sawit/kertas (AALI, LSIP, SGRO, SIMP, BWPT, INKP, TKIM). Data "aneh" yang hampir
pasti tidak dilihat dana besar untuk saham IDX. Satelit melintas ~2x sehari; tiap titik = piksel dengan api aktif.

Sumber (API resmi, robots.txt Allow /api/; butuh MAP_KEY gratis):
  MODIS_SP / MODIS_NRT        : sejak 2000-11, piksel 1 km (konsisten panjang -> untuk riset histori)
  VIIRS_SNPP_SP / _NRT        : sejak 2012-01, piksel 375 m (lebih peka)
  /api/area/csv/<KEY>/<SUMBER>/<KOTAK>/<HARI 1-5>/<TANGGAL>
Kotak: Indonesia + Malaysia + Singapura (bujur 94..142, lintang -11..7).

Isi (1 baris = 1 titik api; kolom asli FIRMS + 'sumber'):
  data/raw/harian/api/<tanggal UTC>.parquet       mode harian: 10 hari terakhir, NRT (MODIS + VIIRS NOAA-20 & NOAA-21)
  data/raw/histori/api/<sumber>_<tahun>.parquet   mode --histori: per tahun, SP (standar, sudah dikoreksi), bisa dilanjutkan
Cara pakai:
  python kumpul_api.py                 -> harian
  python kumpul_api.py --tes           -> 1 permintaan, tanpa simpan
  python kumpul_api.py --histori       -> histori MODIS_SP 2000-11..sekarang & VIIRS_SNPP_SP 2012..sekarang
"""
import io
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

KUNCI = os.environ.get("FIRMS_MAP_KEY") or Path("kunci_firms.txt").read_text().strip()
URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
KOTAK = "94,-11,142,7"                         # barat, selatan, timur, utara
HEADER = {"User-Agent": "quant-data-collector/1.0 (personal research project)"}
HARI_INI = datetime.now(timezone.utc).date()
TES, HISTORI = "--tes" in sys.argv, "--histori" in sys.argv
# VIIRS S-NPP NRT kosong sejak ~2026 (satelit tua); harian pakai penerusnya NOAA-20 & NOAA-21
SUMBER_HARIAN = ["MODIS_NRT", "VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT"]
AWAL = {"MODIS_SP": date(2000, 11, 1), "VIIRS_SNPP_SP": date(2012, 1, 20)}


def ambil(sumber, mulai, hari=5):
    """Titik api [mulai, mulai + hari - 1]. DataFrame (bisa kosong)."""
    u = f"{URL}/{KUNCI}/{sumber}/{KOTAK}/{hari}/{mulai.isoformat()}"
    for percobaan in range(6):
        try:
            r = requests.get(u, headers=HEADER, timeout=(15, 120))
            teks = r.text
            if r.status_code == 429 or "Exceeding allowed transaction limit" in teks:
                print("   ⏳ batas transaksi FIRMS (5.000 per 10 menit), tunggu 2 menit")
                time.sleep(120)
                continue
            r.raise_for_status()
            if teks.lstrip().lower().startswith(("invalid", "error")):
                raise RuntimeError(teks[:200])
            d = pd.read_csv(io.StringIO(teks), dtype={"acq_time": str, "version": str})
            d.insert(0, "sumber", sumber)
            return d
        except (requests.RequestException, RuntimeError) as e:
            if percobaan == 5:
                raise
            print(f"   ⚠️  {sumber} {mulai}: {type(e).__name__}: {str(e)[:100]}, coba lagi")
            time.sleep(10 * (percobaan + 1))


def rapikan(d):
    if d.empty:
        return d
    d["acq_date"] = pd.to_datetime(d["acq_date"]).astype("datetime64[ns]")
    d["acq_time"] = d["acq_time"].astype(str).str.zfill(4)         # jam UTC 'HHMM'
    for k in d.columns:
        if d[k].dtype == object:
            d[k] = d[k].astype("string")
    kunci = [k for k in ["sumber", "latitude", "longitude", "acq_date", "acq_time", "satellite"] if k in d]
    return d.drop_duplicates(kunci).reset_index(drop=True)


def ringkas(d):
    if d.empty:
        return "0 titik"
    per = d.groupby("sumber").size().to_dict()
    return f"{len(d):,} titik {per} | {d['acq_date'].min():%Y-%m-%d} s/d {d['acq_date'].max():%Y-%m-%d}"


if TES:
    d = rapikan(ambil("VIIRS_NOAA20_NRT", HARI_INI - timedelta(days=4)))
    print(f"🧪 {ringkas(d)}")
    print(d.head(3).to_string())
    print(d.columns.tolist())
    sys.exit()

if not HISTORI:
    bagian = [ambil(s, HARI_INI - timedelta(days=m), 5) for s in SUMBER_HARIAN for m in (9, 4)]
    d = rapikan(pd.concat([b for b in bagian if not b.empty], ignore_index=True))
    print(f"✅ {ringkas(d)}")
    folder = Path("data/raw/harian/api")
    folder.mkdir(parents=True, exist_ok=True)
    d.to_parquet(folder / f"{HARI_INI.isoformat()}.parquet", index=False)
    print(f"💾 {folder}/{HARI_INI.isoformat()}.parquet")
    sys.exit()

# ===== Histori: per sumber per tahun; tahun yang sudah ada dilewati (kecuali 2 tahun terakhir) =====
folder = Path("data/raw/histori/api")
folder.mkdir(parents=True, exist_ok=True)
from huggingface_hub import HfApi                     # upload tiap tahun -> bisa dilanjutkan kalau terputus
api_hf = HfApi(token=os.environ.get("HF_TOKEN") or Path("kunci_hf.txt").read_text().strip())
REPO = "fadli-sparks/quant-data"
sudah = {Path(x).name for x in api_hf.list_repo_files(REPO, repo_type="dataset") if x.startswith("raw/histori/api/")}
print(f"☁️  {len(sudah)} file histori api sudah ada di gudang (dilewati, kecuali 2 tahun terakhir)")


def unggah(f):
    for percobaan in range(6):
        try:
            api_hf.upload_file(path_or_fileobj=str(f), path_in_repo=f"raw/histori/api/{f.name}", repo_id=REPO,
                               repo_type="dataset", commit_message=f"Upload raw/histori/api/{f.name}")
            return
        except Exception as e:
            print(f"   ⚠️  upload {f.name}: {type(e).__name__}, tunggu 2 menit")
            time.sleep(120)
    raise RuntimeError(f"upload {f.name} gagal terus")


for sumber, awal in AWAL.items():
    for th in range(awal.year, HARI_INI.year + 1):
        f = folder / f"{sumber}_{th}.parquet"
        if (f.exists() or f.name in sudah) and th < HARI_INI.year - 1:
            continue
        mulai, akhir = max(awal, date(th, 1, 1)), min(date(th, 12, 31), HARI_INI)
        t0, bagian, tgl = time.time(), [], mulai
        while tgl <= akhir:
            hari = min(5, (akhir - tgl).days + 1)
            b = ambil(sumber, tgl, hari)
            if not b.empty:
                bagian.append(b)
            tgl += timedelta(days=hari)
            time.sleep(0.15)
        d = rapikan(pd.concat(bagian, ignore_index=True)) if bagian else pd.DataFrame()
        if d.empty:
            print(f"   {sumber} {th}: kosong (SP mungkin belum tersedia untuk tahun ini)")
            continue
        d.to_parquet(f, index=False)
        unggah(f)
        print(f"   💾☁️  {sumber} {th}: {len(d):,} titik ({time.time() - t0:.0f} detik)")
print("✅ histori selesai")
