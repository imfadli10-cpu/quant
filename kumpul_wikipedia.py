import sys
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import requests

ARTIKEL = {
    "id.wikipedia": [
        "Bank_Central_Asia", "Bank_Rakyat_Indonesia", "Telkom_Indonesia",
        "Bursa_Efek_Indonesia", "Rupiah", "Inflasi", "Resesi",
        "Emas", "Bitcoin", "Pemutusan_hubungan_kerja",
    ],
    "en.wikipedia": [
        "Bitcoin", "Ethereum", "Recession", "Inflation", "Stock_market_crash",
        "Federal_Reserve", "Gold_as_an_investment", "Nvidia", "Indonesia",
        "Indonesian_rupiah",
    ],
}

HEADER = {"User-Agent": "quant-data-collector/1.0 (personal research project; python-requests)"}

HISTORI = "--histori" in sys.argv                                       # BARU
akhir = date.today() - timedelta(days=1)
awal = date(2015, 7, 1) if HISTORI else akhir - timedelta(days=30)     # BARU: data Wikimedia mulai Juli 2015


def ambil(url):
    """Ambil satu artikel. Kalau ditolak (429), tunggu lalu coba lagi."""
    for percobaan in range(1, 5):
        try:
            r = requests.get(url, headers=HEADER, timeout=60)
        except requests.exceptions.RequestException as e:
            print(f"   🔌 {type(e).__name__}, coba lagi...")
            time.sleep(10)
            continue
        if r.status_code == 429:
            tunggu = int(r.headers.get("Retry-After", 15 * percobaan))
            print(f"   ⏳ Kena batas, tunggu {tunggu} detik (percobaan {percobaan}/4)")
            time.sleep(tunggu)
            continue
        return r
    return None


hasil = []
for proyek, daftar in ARTIKEL.items():
    for judul in daftar:
        url = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
               f"{proyek}/all-access/user/{quote(judul, safe='')}/daily/"
               f"{awal:%Y%m%d}/{akhir:%Y%m%d}")
        r = ambil(url)
        if r is None or r.status_code != 200:
            kode = "gagal" if r is None else f"HTTP {r.status_code}"
            print(f"⚠️  {proyek}/{judul}: {kode}")
            continue
        for item in r.json()["items"]:
            hasil.append({
                "tanggal": pd.to_datetime(item["timestamp"][:8]),
                "wiki": proyek,
                "artikel": judul,
                "pembaca": item["views"],
            })
        print(f"✅ {proyek}/{judul}")
        time.sleep(1)

df = pd.DataFrame(hasil)
if HISTORI:                                                             # BARU
    folder = Path("data/raw/histori/wikipedia")
    file_out = folder / "semua.parquet"
else:
    folder = Path("data/raw/harian/wikipedia")
    file_out = folder / f"{date.today().isoformat()}.parquet"
folder.mkdir(parents=True, exist_ok=True)
df.to_parquet(file_out, index=False)
jumlah = len(df[["wiki", "artikel"]].drop_duplicates())                # BARU: hitung yang benar
print(f"\n✅ {jumlah} artikel, {len(df):,} baris → {file_out}")