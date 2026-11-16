import io
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

HEADER = {"User-Agent": "quant-data-collector/1.0 (personal research project)"}
hari_ini = date.today()


def ambil_teks(url, params=None):
    for percobaan in range(4):
        try:
            r = requests.get(url, params=params, headers=HEADER, timeout=120)
            r.raise_for_status()
            return r.text
        except requests.exceptions.RequestException as e:
            print(f"   🔌 {type(e).__name__}, coba lagi...")
            time.sleep(10)
    return None


def gempa(mulai, selesai, min_magnitudo):
    teks = ambil_teks("https://earthquake.usgs.gov/fdsnws/event/1/query", {
        "format": "csv", "starttime": mulai.isoformat(), "endtime": selesai.isoformat(),
        "minmagnitude": min_magnitudo, "orderby": "time-asc"})
    if teks is None:
        return None
    df = pd.read_csv(io.StringIO(teks))
    df = df[["time", "latitude", "longitude", "depth", "mag", "magType", "place", "type", "id"]]
    df["time"] = pd.to_datetime(df["time"], utc=True, format="ISO8601").dt.tz_localize(None)
    return df


# ===== Mode histori gempa: M4.5+ sejak 1990, 1 file per tahun =====
if "--histori-gempa" in sys.argv:
    folder = Path("data/raw/histori/gempa")
    folder.mkdir(parents=True, exist_ok=True)
    for tahun in range(1990, hari_ini.year + 1):
        file = folder / f"{tahun}.parquet"
        if file.exists():
            continue
        df = gempa(date(tahun, 1, 1), date(tahun + 1, 1, 1), 4.5)
        if df is None:
            print(f"⚠️  {tahun}: gagal")
            continue
        df.to_parquet(file, index=False)
        print(f"✅ gempa {tahun}: {len(df):,} kejadian")
        time.sleep(2)
    sys.exit()

# ===== 1. Gempa harian: M2.5+ seluruh dunia, 14 hari terakhir =====
df = gempa(hari_ini - timedelta(days=14), hari_ini + timedelta(days=1), 2.5)
if df is not None:
    folder = Path("data/raw/harian/gempa")
    folder.mkdir(parents=True, exist_ok=True)
    df.to_parquet(folder / f"{hari_ini.isoformat()}.parquet", index=False)
    print(f"✅ gempa: {len(df):,} kejadian, terbesar M{df['mag'].max()}")

# ===== 2. Geomagnetik & matahari: harian sejak 1932 (seluruh file, ditimpa) =====
teks = ambil_teks("https://kp.gfz-potsdam.de/app/files/Kp_ap_Ap_SN_F107_since_1932.txt")
if teks is not None:
    df = pd.read_csv(io.StringIO(teks), sep=r"\s+", comment="#", header=None)
    NAMA = (["tahun", "bulan", "hari", "hari_sejak_1932", "hari_sejak_1932_tengah",
             "rotasi_bartels", "hari_bartels"]
            + [f"kp{i}" for i in range(1, 9)] + [f"ap{i}" for i in range(1, 9)]
            + ["Ap", "bintik_matahari", "f107_obs", "f107_adj", "status"])
    if df.shape[1] != len(NAMA):
        print(f"⚠️  geomagnetik: format berubah ({df.shape[1]} kolom, harusnya {len(NAMA)})")
    else:
        df.columns = NAMA
        df["tanggal"] = pd.to_datetime(dict(year=df["tahun"], month=df["bulan"], day=df["hari"]))
        for kolom in ["bintik_matahari", "f107_obs", "f107_adj"]:
            df[kolom] = df[kolom].where(df[kolom] >= 0)   # -1 artinya belum ada data
        folder = Path("data/raw/alam")
        folder.mkdir(parents=True, exist_ok=True)
        df.to_parquet(folder / "geomagnetik_matahari.parquet", index=False)
        print(f"✅ geomagnetik: {len(df):,} hari, {df['tanggal'].min().date()} s/d {df['tanggal'].max().date()}")