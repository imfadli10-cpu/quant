import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

KOTA = {
    "jakarta": (-6.21, 106.85),     "surabaya": (-7.25, 112.75),
    "medan": (3.59, 98.67),         "pekanbaru": (0.51, 101.45),
    "makassar": (-5.15, 119.43),    "new_york": (40.71, -74.01),
    "london": (51.51, -0.13),       "tokyo": (35.68, 139.69),
    "shanghai": (31.23, 121.47),    "singapura": (1.35, 103.82),
    "kuala_lumpur": (3.14, 101.69), "des_moines": (41.59, -93.62),
    "chicago": (41.88, -87.63),     "houston": (29.76, -95.37),
    "minas_gerais": (-19.92, -43.94),
}
VARIABEL = ("temperature_2m_max,temperature_2m_min,precipitation_sum,"
            "sunshine_duration,wind_speed_10m_max")

# Gabungkan semua koordinat jadi satu permintaan, dipisah koma
lintang = ",".join(str(lat) for lat, lon in KOTA.values())
bujur = ",".join(str(lon) for lat, lon in KOTA.values())
url = (f"https://api.open-meteo.com/v1/forecast?latitude={lintang}&longitude={bujur}"
       f"&daily={VARIABEL}&past_days=14&forecast_days=0&timezone=auto")

data = None
for percobaan in range(1, 6):
    try:
        r = requests.get(url, timeout=120)
        if r.status_code == 429:
            print(f"   ⏳ Kena batas, tunggu 60 detik (percobaan {percobaan}/5)")
            time.sleep(60)
            continue
        r.raise_for_status()
        data = r.json()
        break
    except requests.exceptions.RequestException as e:
        print(f"   🔌 {type(e).__name__}, coba lagi 30 detik (percobaan {percobaan}/5)")
        time.sleep(30)

if data is None:
    print("❌ Cuaca gagal diambil hari ini. Besok dicoba lagi (data 14 hari tetap aman).")
else:
    hasil = []
    for nama, isi in zip(KOTA, data):   # urutan jawaban = urutan kota
        df = pd.DataFrame(isi["daily"]).rename(columns={"time": "tanggal"})
        hasil.append(df.assign(kota=nama))

    gabung = pd.concat(hasil, ignore_index=True)
    gabung["tanggal"] = pd.to_datetime(gabung["tanggal"])

    folder = Path("data/raw/harian/cuaca")
    folder.mkdir(parents=True, exist_ok=True)
    file_out = folder / f"{date.today().isoformat()}.parquet"
    gabung.to_parquet(file_out, index=False)
    print(f"✅ {gabung['kota'].nunique()} kota, {len(gabung)} baris → {file_out}")