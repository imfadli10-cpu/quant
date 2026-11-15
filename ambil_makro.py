import os
import time
import requests
import pandas as pd
from pathlib import Path


KUNCI = os.environ.get("FRED_API_KEY") or Path("kunci_fred.txt").read_text().strip()

# Kode FRED : keterangan
SERI = {
    "DFF":          "Suku bunga The Fed (harian)",
    "DGS2":         "Yield obligasi AS 2 tahun",
    "DGS10":        "Yield obligasi AS 10 tahun",
    "T10Y2Y":       "Selisih yield 10th - 2th (sinyal resesi)",
    "MORTGAGE30US": "Bunga KPR AS 30 tahun",
    "CPIAUCSL":     "Inflasi AS (CPI)",
    "M2SL":         "Uang beredar M2 AS",
    "UNRATE":       "Tingkat pengangguran AS",
    "PAYEMS":       "Jumlah pekerja non-pertanian AS",
    "ICSA":         "Klaim pengangguran mingguan AS",
    "INDPRO":       "Produksi industri AS",
    "UMCSENT":      "Sentimen konsumen Michigan",
    "VIXCLS":       "VIX - indeks ketakutan pasar",
    "BAMLH0A0HYM2": "Selisih bunga obligasi sampah (risiko kredit)",
    "DTWEXBGS":     "Indeks kekuatan dolar AS",
    "DCOILWTICO":   "Harga minyak WTI",
    "IDNCPIALLMINMEI":  "Inflasi Indonesia (CPI)",
    "IRSTCI01IDM156N":  "Suku bunga jangka pendek Indonesia",
}

folder = Path("data/raw/makro")
folder.mkdir(parents=True, exist_ok=True)
Path("data/ref").mkdir(parents=True, exist_ok=True)


def ambil(kode):
    """Ambil satu seri dari FRED API, coba ulang sampai 3 kali kalau gagal."""
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {"series_id": kode, "api_key": KUNCI, "file_type": "json"}
    for percobaan in range(1, 4):
        try:
            r = requests.get(url, params=params, timeout=60)
            r.raise_for_status()
            return r.json()["observations"]
        except Exception as e:
            print(f"   ⏳ {kode} gagal (percobaan {percobaan}/3): {type(e).__name__}")
            time.sleep(5)
    return None


for kode, ket in SERI.items():
    data = ambil(kode)
    if data is None:
        print(f"❌ {kode}: tetap gagal setelah 3 kali")
        continue

    df = pd.DataFrame(data)[["date", "value"]]
    df["date"] = pd.to_datetime(df["date"])
    df["nilai"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.set_index("date")[["nilai"]].dropna()

    df.to_parquet(folder / f"{kode}.parquet")
    print(f"✅ {kode}: {len(df)} data, {df.index[0].date()} s/d {df.index[-1].date()}  ({ket})")
    time.sleep(1)

pd.Series(SERI, name="keterangan").to_csv("data/ref/katalog_makro.csv")
print("\nSelesai!")