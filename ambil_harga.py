import yfinance as yf
from pathlib import Path

# Daftar data yang mau diambil: "nama file": "kode Yahoo"
DAFTAR = {
    # --- Yang sudah ada sebelumnya ---
    "IHSG": "^JKSE", "BBCA": "BBCA.JK", "BBRI": "BBRI.JK", "TLKM": "TLKM.JK",
    "SP500": "^GSPC", "EMAS": "GC=F", "MINYAK": "CL=F", "USDIDR": "IDR=X", "BITCOIN": "BTC-USD",
    # --- Indeks saham Asia-Pasifik ---
    "NIKKEI": "^N225", "HANGSENG": "^HSI", "SHANGHAI": "000001.SS", "STI": "^STI",
    "KLCI": "^KLSE", "SET_THAILAND": "^SET.BK", "PSEI_FILIPINA": "PSEI.PS",
    "SENSEX": "^BSESN", "NIFTY": "^NSEI", "KOSPI": "^KS11", "TAIEX": "^TWII", "ASX200": "^AXJO",
    # --- Indeks saham Eropa & Amerika ---
    "FTSE": "^FTSE", "DAX": "^GDAXI", "CAC40": "^FCHI", "EUROSTOXX50": "^STOXX50E",
    "DOWJONES": "^DJI", "NASDAQ": "^IXIC", "RUSSELL2000": "^RUT", "BOVESPA": "^BVSP",
    # --- Indikator pasar ---
    "VIX": "^VIX", "DOLAR_INDEX": "DX-Y.NYB", "YIELD_AS_10TH": "^TNX",
    # --- Futures logam ---
    "PERAK": "SI=F", "TEMBAGA": "HG=F", "PLATINUM": "PL=F", "PALADIUM": "PA=F",
    # --- Futures energi ---
    "BRENT": "BZ=F", "GAS_ALAM": "NG=F", "BENSIN": "RB=F", "HEATING_OIL": "HO=F",
    # --- Futures pertanian & ternak ---
    "JAGUNG": "ZC=F", "GANDUM": "ZW=F", "KEDELAI": "ZS=F", "BUNGKIL_KEDELAI": "ZM=F",
    "MINYAK_KEDELAI": "ZL=F", "KOPI": "KC=F", "KAKAO": "CC=F", "GULA": "SB=F",
    "KAPAS": "CT=F", "SAPI": "LE=F", "BABI": "HE=F", "JUS_JERUK": "OJ=F",
    "SAWIT": "CPO=F",   # USD Malaysian Crude Palm Oil (CME), sejak 2010, ditambahkan 19 Nov 2026
    "LQ45": "^JKLQ45", "JII": "^JKII",   # indeks IDX (LQ45 sejak 1997, JII sejak 2000), ditambahkan 21 Nov 2026
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