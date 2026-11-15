import yfinance as yf
from pathlib import Path

# Daftar data yang mau diambil: "nama file": "kode Yahoo"
DAFTAR = {
    "IHSG": "^JKSE",
    "BBCA": "BBCA.JK",
    "BBRI": "BBRI.JK",
    "TLKM": "TLKM.JK",
    "SP500": "^GSPC",
    "EMAS": "GC=F",
    "MINYAK": "CL=F",
    "USDIDR": "IDR=X",
    "BITCOIN": "BTC-USD",
}

# Folder tujuan: D:\quant\data\raw\harga
folder = Path("data/raw/harga")
folder.mkdir(parents=True, exist_ok=True)

for nama, kode in DAFTAR.items():
    df = yf.download(kode, period="max", interval="1d",
                     auto_adjust=False, progress=False,
                     multi_level_index=False)
    if df.empty:
        print(f"❌ GAGAL: {nama}")
        continue
    df.to_parquet(folder / f"{nama}.parquet")
    print(f"✅ {nama}: {len(df)} hari, {df.index[0].date()} s/d {df.index[-1].date()}")

print("Selesai!")