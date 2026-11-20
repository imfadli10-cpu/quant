"""
PERHATIAN PUBLIK per saham IDX = jumlah pembaca harian artikel Wikipedia perusahaannya (bahasa Indonesia & Inggris).

Kenapa: lonjakan perhatian publik pada sebuah saham sering diikuti pola harga tertentu (Da-Engelberg-Gao 2011, memakai
pencarian Google). Data "aneh" yang langsung relevan dengan IDX (medan strategi S2).
Peta kode saham -> artikel dari Wikidata (perusahaan tercatat di Bursa Efek Indonesia, Q1661737): ~1.048 perusahaan,
~281 punya artikel id/en (20 Nov 2026). Pembaca dari Wikimedia Pageviews API (agen 'user', tanpa bot), sejak Juli 2015.
Catatan: artikel yang pernah GANTI JUDUL kehilangan histori sebelum ganti judul (API menghitung per judul persis).

Isi:
  data/ref/wikidata_idx.parquet                     peta kode/qid/nama/artikel_id/artikel_en/mulai tercatat (ditimpa)
  data/raw/harian/wikipedia_idx/<tanggal>.parquet   30 hari terakhir (tumpang tindih)
  data/raw/histori/wikipedia_idx/semua.parquet      (--histori) sejak 2015-07-01
Format: tanggal, kode, wiki (id/en), artikel, pembaca
Cara pakai: python kumpul_perhatian_idx.py [--histori | --tes]
"""
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import requests

from daftar_saham import wikidata_idx

HEADER = {"User-Agent": "quant-data-collector/1.0 (personal research project; python-requests)"}
HISTORI, TES = "--histori" in sys.argv, "--tes" in sys.argv
HARI_INI = datetime.now(timezone.utc).date()
akhir = HARI_INI - timedelta(days=1)
awal = date(2015, 7, 1) if HISTORI else akhir - timedelta(days=30)

peta = wikidata_idx()
print(f"📋 Wikidata: {len(peta)} kode IDX | artikel id {(peta['artikel_id'] != '').sum()} | "
      f"artikel en {(peta['artikel_en'] != '').sum()}")
if not TES:
    Path("data/ref").mkdir(parents=True, exist_ok=True)
    peta.to_parquet("data/ref/wikidata_idx.parquet", index=False)

tugas = [(r["kode"], w, r[f"artikel_{w}"]) for _, r in peta.iterrows() for w in ("id", "en") if r[f"artikel_{w}"]]
if TES:
    tugas = tugas[:5]


def ambil(url):
    for percobaan in range(1, 5):
        try:
            r = requests.get(url, headers=HEADER, timeout=60)
        except requests.exceptions.RequestException as e:
            print(f"   🔌 {type(e).__name__}, coba lagi...")
            time.sleep(10)
            continue
        if r.status_code == 429:
            time.sleep(int(r.headers.get("Retry-After", 15 * percobaan)))
            continue
        return r
    return None


hasil, gagal, kosong = [], 0, 0
for i, (kode, wiki, judul) in enumerate(tugas, 1):
    url = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
           f"{wiki}.wikipedia/all-access/user/{quote(judul.replace(' ', '_'), safe='')}/daily/{awal:%Y%m%d}/{akhir:%Y%m%d}")
    r = ambil(url)
    if r is None or r.status_code not in (200, 404):
        gagal += 1
    elif r.status_code == 404:          # artikel tanpa pembaca di rentang itu
        kosong += 1
    else:
        for item in r.json()["items"]:
            hasil.append({"tanggal": item["timestamp"][:8], "kode": kode, "wiki": wiki, "artikel": judul,
                          "pembaca": item["views"]})
    if i % 100 == 0:
        print(f"   {i}/{len(tugas)}")
    time.sleep(0.3)

df = pd.DataFrame(hasil)
df["tanggal"] = pd.to_datetime(df["tanggal"], format="%Y%m%d").astype("datetime64[ns]")
for k in ["kode", "wiki", "artikel"]:
    df[k] = df[k].astype("string")
df["pembaca"] = df["pembaca"].astype("int64")
print(f"✅ wikipedia_idx: {len(df):,} baris, {df['kode'].nunique()} kode, {df['tanggal'].min().date()} s/d "
      f"{df['tanggal'].max().date()} | gagal {gagal}, tanpa data {kosong} dari {len(tugas)} artikel")
if TES:
    print(df.groupby(["kode", "wiki"])["pembaca"].agg(["sum", "count"]).to_string())
    sys.exit()
if HISTORI:
    folder, nama = Path("data/raw/histori/wikipedia_idx"), "semua.parquet"
else:
    folder, nama = Path("data/raw/harian/wikipedia_idx"), f"{HARI_INI.isoformat()}.parquet"
folder.mkdir(parents=True, exist_ok=True)
df.to_parquet(folder / nama, index=False)
print(f"💾 {folder / nama}")
if gagal > 0.2 * len(tugas):
    print("❌ terlalu banyak artikel gagal")
    sys.exit(1)
