import time
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import requests

# Daftar artikel yang dipantau. Tambah kapan saja.
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

# Wikimedia meminta setiap program memperkenalkan diri lewat User-Agent
HEADER = {"User-Agent": "quant-data-collector/1.0 (personal research project; python-requests)"}

akhir = date.today() - timedelta(days=1)
awal = akhir - timedelta(days=30)


def ambil(url):
    """Ambil satu artikel. Kalau ditolak (429), tunggu lalu coba lagi."""
    for percobaan in range(1, 5):
        try:
            r = requests.get(url, headers=HEADER, timeout=30)
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
folder = Path("data/raw/harian/wikipedia")
folder.mkdir(parents=True, exist_ok=True)
file_out = folder / f"{date.today().isoformat()}.parquet"
df.to_parquet(file_out, index=False)
print(f"\n✅ {df['artikel'].nunique()} artikel, {len(df)} baris → {file_out}")