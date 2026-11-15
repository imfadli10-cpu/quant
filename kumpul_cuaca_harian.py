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

hasil = []
for nama, (lat, lon) in KOTA.items():
    url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
           f"&daily={VARIABEL}&past_days=14&forecast_days=0&timezone=auto")
    for percobaan in range(3):
        try:
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            df = pd.DataFrame(r.json()["daily"]).rename(columns={"time": "tanggal"})
            hasil.append(df.assign(kota=nama))
            print(f"✅ {nama}")
            break
        except Exception as e:
            print(f"   ⏳ {nama} gagal ({type(e).__name__}), coba lagi...")
            time.sleep(15)
    time.sleep(1)

gabung = pd.concat(hasil, ignore_index=True)
gabung["tanggal"] = pd.to_datetime(gabung["tanggal"])

folder = Path("data/raw/harian/cuaca")
folder.mkdir(parents=True, exist_ok=True)
file_out = folder / f"{date.today().isoformat()}.parquet"
gabung.to_parquet(file_out, index=False)
print(f"\n✅ {gabung['kota'].nunique()} kota, {len(gabung)} baris → {file_out}")