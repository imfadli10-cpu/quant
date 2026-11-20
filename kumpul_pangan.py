"""
HARGA PANGAN HARIAN Indonesia (PIHPS Bank Indonesia): 10 kategori pangan pokok + rinciannya, nasional & 34 provinsi.

Kenapa: harga pangan bergerak SEBELUM inflasi resmi BPS (bulanan) terbit -> sinyal dini inflasi, kebijakan BI, daya beli;
terkait El Nino (kekeringan -> beras & cabai naik). Data "aneh" yang hampir tidak dilirik investor saham.
Sumber: alamat data publik yang dipanggil halaman https://www.bi.go.id/hargapangan (robots.txt BI MENGIZINKAN /hargapangan).
Histori mulai Juli 2017. JEBAKAN: dari laptop, WARP harus MATI (dengan WARP server BI sangat lambat / tidak merespons).
Sopan: jeda 2 detik antar permintaan; histori diambil per SETENGAH TAHUN (±10 detik; setahun penuh ±43 detik).

Kategori: Beras, Daging Ayam, Daging Sapi, Telur Ayam, Bawang Merah, Bawang Putih, Cabai Merah, Cabai Rawit, Minyak Goreng,
  Gula Pasir (+ rincian kualitas/jenis). Jenis harga: 1 Pasar Tradisional, 2 Pasar Modern, 3 Pedagang Besar, 4 Produsen.
Cakupan: NASIONAL untuk 4 jenis harga + 34 PROVINSI untuk pasar tradisional.
Isi (format panjang): tanggal, jenis_harga, wilayah, kategori, komoditas, level (1 = kategori, 2 = rincian), harga (Rp)
  harian    : data/raw/harian/pangan/<tanggal UTC>.parquet  (35 hari terakhir, tumpang tindih)
  --histori : data/raw/histori/pangan/<tahun>.parquet       (sejak 2017-07; tahun yang sudah ada dilewati -> bisa dilanjutkan)
Cara pakai: python kumpul_pangan.py [--histori | --tes]
"""
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

DASAR = "https://www.bi.go.id/hargapangan/WebSite/TabelHarga/"
JENIS = {1: "Pasar Tradisional", 2: "Pasar Modern", 3: "Pedagang Besar", 4: "Produsen"}
HARI_INI = datetime.now(timezone.utc).date()
HISTORI, TES = "--histori" in sys.argv, "--tes" in sys.argv
sesi = requests.Session()
sesi.headers.update({"User-Agent": "quant-data-collector/1.0 (personal research project)", "X-Requested-With": "XMLHttpRequest"})


def minta(nama, params=None):
    for percobaan in range(4):
        try:
            r = sesi.get(DASAR + nama, params=params, timeout=180)
            r.raise_for_status()
            j = r.json()
            return j.get("data", j) if isinstance(j, dict) else j
        except Exception as e:
            print(f"   🔌 {nama}: {type(e).__name__} {str(e)[:80]}, coba lagi...")
            time.sleep(20 * (percobaan + 1))
    raise RuntimeError(f"gagal: {nama} {params}")


kom = minta("GetRefCommodityAndCategory")
KATEGORI = ",".join(k["id"] for k in kom if str(k["id"]).startswith("cat_"))
PROVINSI = {p["id"]: p["name"] for p in minta("GetRefProvince")}


def ambil(mulai, akhir, jenis, prov_id=""):
    data = minta("GetGridDataDaerah", {"price_type_id": jenis, "comcat_id": KATEGORI, "province_id": prov_id,
                                       "regency_id": "", "market_id": "", "tipe_laporan": 1,
                                       "start_date": mulai.isoformat(), "end_date": akhir.isoformat()})
    time.sleep(2)
    baris, kategori = [], None
    for r in data or []:
        if r.get("level") == 1:
            kategori = r["name"]
        for k, v in r.items():
            if k in ("no", "name", "level"):
                continue
            baris.append({"tanggal": k, "jenis_harga": JENIS[jenis],
                          "wilayah": PROVINSI.get(int(prov_id), f"prov_{prov_id}") if prov_id else "Nasional",
                          "kategori": kategori, "komoditas": r["name"], "level": r.get("level"), "harga": v})
    d = pd.DataFrame(baris)
    if d.empty:
        return d
    d["tanggal"] = pd.to_datetime(d["tanggal"], format="%d/%m/%Y", errors="coerce").astype("datetime64[ns]")
    d["harga"] = pd.to_numeric(d["harga"].astype(str).str.replace(",", "", regex=False), errors="coerce").astype("float64")
    for c in ["jenis_harga", "wilayah", "kategori", "komoditas"]:
        d[c] = d[c].astype("string")
    d["level"] = d["level"].astype("int64")
    return d.dropna(subset=["tanggal", "harga"])


def semua(mulai, akhir, provinsi=True):
    bagian = [ambil(mulai, akhir, j) for j in JENIS]                       # nasional, 4 jenis harga
    if provinsi:
        bagian += [ambil(mulai, akhir, 1, str(p)) for p in PROVINSI]       # 34 provinsi, pasar tradisional
    d = pd.concat([b for b in bagian if not b.empty], ignore_index=True)
    return d.drop_duplicates(["tanggal", "jenis_harga", "wilayah", "komoditas"])


def ringkas(d, nama):
    print(f"✅ {nama}: {len(d):,} baris, {d['tanggal'].min().date()} s/d {d['tanggal'].max().date()}, "
          f"{d['wilayah'].nunique()} wilayah, {d['komoditas'].nunique()} komoditas")


if TES:
    d = ambil(HARI_INI - timedelta(days=10), HARI_INI, 1)
    ringkas(d, "tes nasional")
    print(d[d["level"] == 1].pivot_table(index="tanggal", columns="kategori", values="harga").tail(3).to_string())
    sys.exit()

if HISTORI:
    folder = Path("data/raw/histori/pangan")
    folder.mkdir(parents=True, exist_ok=True)
    for tahun in range(2017, HARI_INI.year + 1):
        f = folder / f"{tahun}.parquet"
        if f.exists() and tahun < HARI_INI.year:
            print(f"⏭️  {tahun} sudah ada")
            continue
        potongan = [(date(tahun, 1, 1), date(tahun, 6, 30)), (date(tahun, 7, 1), date(tahun, 12, 31))]
        bagian = []
        for a, b in potongan:
            a, b = max(a, date(2017, 7, 1)), min(b, HARI_INI - timedelta(days=1))
            if a > b:
                continue
            print(f"   ⬇️  {a}..{b}", flush=True)
            bagian.append(semua(a, b))
        d = pd.concat(bagian, ignore_index=True)
        d.to_parquet(f, index=False)
        ringkas(d, f"histori {tahun}")
    print("💾 data/raw/histori/pangan/ (upload: python upload_satu.py data/raw/histori/pangan, nyalakan WARP kalau perlu)")
    sys.exit()

d = semua(HARI_INI - timedelta(days=35), HARI_INI)
ringkas(d, "pangan harian")
if d["wilayah"].nunique() < 30:
    print(f"❌ hanya {d['wilayah'].nunique()} wilayah")
    sys.exit(1)
folder = Path("data/raw/harian/pangan")
folder.mkdir(parents=True, exist_ok=True)
d.to_parquet(folder / f"{HARI_INI.isoformat()}.parquet", index=False)
print(f"💾 {folder}/{HARI_INI.isoformat()}.parquet")
