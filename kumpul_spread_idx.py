"""
FOTO BID/ASK SEMUA SAHAM IDX SAAT JAM BURSA (data "hanya ke depan") -> mengukur BIAYA TRANSAKSI NYATA.

Kenapa (21 Nov 2026): model biaya riset (0,4% + max(spread Corwin-Schultz, tick)) ternyata ~1,9x spread bid-ask ASLI dari 2 foto
daftar_idx (saham >= Rp20 miliar/hari: asli 0,47% = 1 tick vs model 1,38%). Kalau benar, kesimpulan "untung habis dimakan biaya"
(riset #36/#37) bisa berubah. TAPI 2 foto itu diambil di luar jam bursa -> butuh foto SAAT perdagangan berjalan.

Jadwal (workflow spread_idx.yml, Senin-Jumat): ~09:30, ~11:00, ~14:00, ~15:10 WIB (jadwal GitHub bisa telat -> saring saat
analisis memakai regularMarketTime & waktu_ambil). Sumber: screener Yahoo bursa JKT (sama dengan kumpul_daftar_idx.py).
Isi: data/raw/harian/spread_idx/<tanggal UTC>_<HHMM UTC>.parquet: waktu_ambil (UTC), kode, bid, ask, bidSize, askSize,
  harga (regularMarketPrice), volume_hari_ini, waktu_kuotasi (regularMarketTime, UTC), spread_pct (ask-bid)/tengah.
Cara pakai: python kumpul_spread_idx.py | --tes (tanpa simpan)
"""
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf
from yfinance import EquityQuery

logging.getLogger("yfinance").setLevel(logging.CRITICAL)
SEKARANG = datetime.now(timezone.utc)
TES = "--tes" in sys.argv
MIN_SAHAM = 500

quotes, offset, total = [], 0, None
while True:
    for percobaan in range(4):
        try:
            r = yf.screen(EquityQuery("eq", ["exchange", "JKT"]), offset=offset, size=250,
                          sortField="intradaymarketcap", sortAsc=False)
            break
        except Exception as e:
            print(f"   🔌 offset {offset}: {type(e).__name__}, coba lagi...")
            time.sleep(15 * (percobaan + 1))
    else:
        print("❌ spread_idx: screener Yahoo gagal 4x")
        sys.exit(1)
    halaman = r.get("quotes", [])
    total = r.get("total", total)
    quotes += halaman
    offset += 250
    if not halaman or offset >= (total or 0):
        break
    time.sleep(1)

df = pd.DataFrame([{
    "waktu_ambil": SEKARANG.replace(tzinfo=None),
    "kode": str(q.get("symbol", "")).replace(".JK", ""),
    "bid": q.get("bid"), "ask": q.get("ask"), "bidSize": q.get("bidSize"), "askSize": q.get("askSize"),
    "harga": q.get("regularMarketPrice"), "volume_hari_ini": q.get("regularMarketVolume"),
    "waktu_kuotasi": q.get("regularMarketTime"),
} for q in quotes]).drop_duplicates("kode")
for k in ["bid", "ask", "bidSize", "askSize", "harga", "volume_hari_ini"]:
    df[k] = pd.to_numeric(df[k], errors="coerce").astype("float64")
df["waktu_kuotasi"] = pd.to_datetime(pd.to_numeric(df["waktu_kuotasi"], errors="coerce"), unit="s")
df["waktu_ambil"] = df["waktu_ambil"].astype("datetime64[ns]")
df["kode"] = df["kode"].astype("string")
sah = (df["bid"] > 0) & (df["ask"] >= df["bid"])
df["spread_pct"] = ((df["ask"] - df["bid"]) / ((df["ask"] + df["bid"]) / 2)).where(sah)
wib = (SEKARANG + pd.Timedelta(hours=7)).strftime("%H:%M")
print(f"✅ spread_idx {wib} WIB: {len(df)} saham, {sah.sum()} punya bid & ask, spread median {df['spread_pct'].median():.2%}, "
      f"kuotasi terbaru {df['waktu_kuotasi'].max()} UTC")
if len(df) < MIN_SAHAM:
    print(f"❌ hanya {len(df)} saham")
    sys.exit(1)
if TES:
    print("🧪 mode tes: tidak disimpan")
    sys.exit()
folder = Path("data/raw/harian/spread_idx")
folder.mkdir(parents=True, exist_ok=True)
nama = folder / f"{SEKARANG.date().isoformat()}_{SEKARANG.strftime('%H%M')}.parquet"
df.to_parquet(nama, index=False)
print(f"💾 {nama}")
