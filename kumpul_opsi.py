import sys
import time
import logging
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

logging.getLogger("yfinance").setLevel(logging.CRITICAL)

KODE = [
    # ETF indeks & pasar
    "SPY", "QQQ", "IWM", "DIA", "EEM", "EIDO", "FXI", "EWZ", "EWJ",
    # ETF sektor, komoditas, obligasi, volatilitas
    "XLE", "XLF", "XLK", "GLD", "SLV", "USO", "UNG", "TLT", "HYG", "VXX",
    # Saham besar AS
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "AMD", "INTC",
    "JPM", "BAC", "GS", "V", "MA", "XOM", "CVX", "LLY", "UNH", "JNJ",
    "WMT", "COST", "HD", "NFLX", "DIS", "BA", "COIN", "MSTR", "PLTR", "BABA",
]
JATUH_TEMPO = 6          # ambil 6 tanggal jatuh tempo terdekat per saham
TES = "--tes" in sys.argv
if TES:
    KODE = KODE[:3]

waktu_ambil = datetime.now(timezone.utc).replace(tzinfo=None)
hasil, gagal = [], []
for i, kode in enumerate(KODE, start=1):
    try:
        tk = yf.Ticker(kode)
        daftar_tempo = list(tk.options)[:JATUH_TEMPO]
        for tempo in daftar_tempo:
            rantai = tk.option_chain(tempo)
            harga_dasar = (rantai.underlying or {}).get("regularMarketPrice")
            for jenis, tabel in [("call", rantai.calls), ("put", rantai.puts)]:
                hasil.append(tabel.assign(kode=kode, jenis=jenis, jatuh_tempo=tempo,
                                          harga_dasar=harga_dasar, waktu_ambil=waktu_ambil))
            time.sleep(0.5)
        print(f"✅ [{i}/{len(KODE)}] {kode}: {len(daftar_tempo)} jatuh tempo")
    except Exception as e:
        gagal.append(kode)
        print(f"⚠️  [{i}/{len(KODE)}] {kode}: {type(e).__name__}")
    time.sleep(1)

df = pd.concat(hasil, ignore_index=True)
df["jatuh_tempo"] = pd.to_datetime(df["jatuh_tempo"])
if "lastTradeDate" in df.columns:
    df["lastTradeDate"] = pd.to_datetime(df["lastTradeDate"], utc=True).dt.tz_localize(None)

folder = Path("data/raw/harian/opsi")
folder.mkdir(parents=True, exist_ok=True)
file_out = folder / f"{date.today().isoformat()}.parquet"
df.to_parquet(file_out, index=False)
print(f"\n✅ {df['kode'].nunique()} saham/ETF, {len(df):,} kontrak opsi → {file_out}")
if gagal:
    print(f"⚠️  Gagal: {', '.join(gagal)}")