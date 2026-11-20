"""
KUALITAS UDARA per jam, 12 kota Indonesia & tetangga (Open-Meteo Air Quality API, model CAMS; gratis, tanpa kunci).

Kenapa: polusi udara menurunkan suasana hati & kualitas keputusan investor -> return saham cenderung lebih rendah di hari
berpolusi tinggi (Levy-Yagil 2011; Heyes-Neidell-Saberian 2016). Jakarta = salah satu kota terpolusi dunia & pusat
investor/pialang IDX. Kota rawan asap kebakaran hutan (Palembang, Pekanbaru, Pontianak, Balikpapan) = penanda kebakaran
(terkait El Nino/IOD, riset #16), plus Singapura & Kuala Lumpur (penerima asap kiriman).
Histori di Open-Meteo baru ada sejak ~September 2022 (dicek 20 Nov 2026) -> sebagian besar data = ke depan.

Isi (format panjang: waktu WIB tanpa zona, kota, pm2_5, pm10, carbon_monoxide, nitrogen_dioxide, sulphur_dioxide, ozone,
  dust, us_aqi):
  harian    : data/raw/harian/udara/<tanggal UTC>.parquet   = 7 hari terakhir (tumpang tindih)
  --histori : data/raw/histori/udara/semua.parquet         = sejak 2022-09-01, diambil per 6 bulan
Cara pakai: python kumpul_udara.py [--histori | --tes]
"""
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

KOTA = {"Jakarta": (-6.20, 106.82), "Surabaya": (-7.25, 112.75), "Bandung": (-6.91, 107.61), "Medan": (3.59, 98.67),
        "Semarang": (-6.97, 110.42), "Makassar": (-5.14, 119.42), "Palembang": (-2.98, 104.75), "Pekanbaru": (0.51, 101.45),
        "Pontianak": (-0.03, 109.33), "Balikpapan": (-1.27, 116.83), "Singapura": (1.35, 103.82), "Kuala Lumpur": (3.14, 101.69)}
VAR = ["pm2_5", "pm10", "carbon_monoxide", "nitrogen_dioxide", "sulphur_dioxide", "ozone", "dust", "us_aqi"]
UA = {"User-Agent": "quant-data-collector/1.0 (personal research project)"}
HARI_INI = datetime.now(timezone.utc).date()
HISTORI, TES = "--histori" in sys.argv, "--tes" in sys.argv


def ambil(mulai, akhir):
    """Semua kota dalam SATU permintaan (lat/lon dipisah koma)."""
    params = {"latitude": ",".join(str(v[0]) for v in KOTA.values()),
              "longitude": ",".join(str(v[1]) for v in KOTA.values()),
              "hourly": ",".join(VAR), "start_date": mulai.isoformat(), "end_date": akhir.isoformat(),
              "timezone": "Asia/Jakarta"}
    for percobaan in range(5):
        try:
            r = requests.get("https://air-quality-api.open-meteo.com/v1/air-quality", params=params, headers=UA, timeout=120)
            if r.status_code == 429:
                time.sleep(int(r.headers.get("Retry-After", 60)))
                continue
            r.raise_for_status()
            j = r.json()
            j = j if isinstance(j, list) else [j]
            bagian = []
            for nama, isi in zip(KOTA, j):
                d = pd.DataFrame(isi["hourly"])
                d.insert(1, "kota", nama)
                bagian.append(d)
            return pd.concat(bagian, ignore_index=True)
        except Exception as e:
            print(f"   🔌 {mulai}..{akhir}: {type(e).__name__}, coba lagi...")
            time.sleep(15 * (percobaan + 1))
    raise RuntimeError(f"gagal {mulai}..{akhir}")


def rapikan(d):
    d = d.rename(columns={"time": "waktu"})
    d["waktu"] = pd.to_datetime(d["waktu"]).astype("datetime64[ns]")
    d["kota"] = d["kota"].astype("string")
    for v in VAR:
        d[v] = pd.to_numeric(d[v], errors="coerce").astype("float64")
    return d.dropna(subset=VAR, how="all").drop_duplicates(["waktu", "kota"]).sort_values(["kota", "waktu"])


if HISTORI:
    bagian, mulai = [], date(2022, 9, 1)
    while mulai < HARI_INI:
        akhir = min(mulai + timedelta(days=182), HARI_INI - timedelta(days=1))
        bagian.append(ambil(mulai, akhir))
        print(f"   ✅ {mulai}..{akhir}")
        mulai = akhir + timedelta(days=1)
        time.sleep(3)
    df = rapikan(pd.concat(bagian, ignore_index=True))
    folder, nama = Path("data/raw/histori/udara"), "semua.parquet"
else:
    df = rapikan(ambil(HARI_INI - timedelta(days=7), HARI_INI - timedelta(days=1)))
    folder, nama = Path("data/raw/harian/udara"), f"{HARI_INI.isoformat()}.parquet"
rata = df.groupby("kota")["pm2_5"].mean().sort_values(ascending=False)
print(f"✅ udara: {len(df):,} baris, {df['kota'].nunique()} kota, {df['waktu'].min()} s/d {df['waktu'].max()} | "
      f"PM2.5 rata-rata tertinggi: " + ", ".join(f"{k} {v:.0f}" for k, v in rata.head(3).items()))
if TES:
    print(df.dtypes.to_string())
    sys.exit()
folder.mkdir(parents=True, exist_ok=True)
df.to_parquet(folder / nama, index=False)
print(f"💾 {folder / nama}")
