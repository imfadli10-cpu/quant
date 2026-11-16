import io
import sys
import time
import logging
from datetime import date
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

logging.getLogger("yfinance").setLevel(logging.CRITICAL)   # sembunyikan pesan error per kode

HEADER = {"User-Agent": "quant-data-collector/1.0 (personal research project)"}
SUMBER = {
    "nasdaq":  "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
    "lainnya": "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt",
}
hari_ini = date.today().isoformat()

# ===== 1. Ambil daftar semua saham & ETF AS =====
daftar = []
for nama, url in SUMBER.items():
    r = requests.get(url, headers=HEADER, timeout=60)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text), sep="|", dtype=str, keep_default_na=False)
    df = df[~df.iloc[:, 0].astype(str).str.startswith("File Creation Time")]
    kolom_simbol = "Symbol" if "Symbol" in df.columns else "ACT Symbol"
    df = df[df["Test Issue"] == "N"]
    daftar.append(pd.DataFrame({
        "simbol": df[kolom_simbol].astype(str),
        "nama": df["Security Name"],
        "etf": df["ETF"],
        "sumber": nama,
    }))

semua = pd.concat(daftar).drop_duplicates("simbol")
semua = semua[~semua["simbol"].str.contains("$", regex=False)]      # buang saham preferen
semua["kode_yahoo"] = semua["simbol"].str.replace(".", "-", regex=False)  # BRK.B → BRK-B

# Simpan daftar hari ini (catatan saham yang ada/hilang dari waktu ke waktu)
folder_daftar = Path("data/raw/harian/daftar_saham_as")
folder_daftar.mkdir(parents=True, exist_ok=True)
semua.to_parquet(folder_daftar / f"{hari_ini}.parquet", index=False)
print(f"📋 Daftar: {len(semua)} kode ({(semua['etf'] == 'Y').sum()} ETF)")

# ===== 2. Ambil harga 7 hari terakhir =====
kode = semua["kode_yahoo"].tolist()
if "--tes" in sys.argv:
    kode = kode[:300]
    print("🧪 Mode tes: hanya 300 kode pertama")

hasil = []
for i in range(0, len(kode), 100):
    kelompok = kode[i:i + 100]
    try:
        df = yf.download(kelompok, period="7d", interval="1d", auto_adjust=False,
                         progress=False, group_by="ticker", threads=True)
    except Exception as e:
        print(f"  ⚠️ Kelompok {i // 100 + 1} gagal: {type(e).__name__}")
        continue
    for k in kelompok:
        if k not in df.columns.get_level_values(0):
            continue
        d = df[k].dropna(subset=["Close"])
        if not d.empty:
            hasil.append(d.assign(kode=k))
    if (i // 100 + 1) % 10 == 0:
        print(f"  ... {min(i + 100, len(kode))}/{len(kode)} kode")
    time.sleep(3)

gabung = pd.concat(hasil).reset_index().rename(columns={"Date": "tanggal"})
folder = Path("data/raw/harian/saham_as")
folder.mkdir(parents=True, exist_ok=True)
file_out = folder / f"{hari_ini}.parquet"
gabung.to_parquet(file_out, index=False)
print(f"\n✅ {gabung['kode'].nunique()} kode, {len(gabung)} baris → {file_out}")