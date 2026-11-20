"""
Harga INTRADAY saham & ETF IDX dari Yahoo (data "hanya ke depan": 1 menit hanya ~8 hari, 5 menit ~60 hari, 1 jam ~2 tahun).

Kenapa: kelemahan S2 = biaya eksekusi di saham kurang likuid. Intraday memperlihatkan pergerakan menjelang penutupan
(saat S2 membeli), jam-jam yang lebih murah, banyaknya menit tanpa transaksi (ukuran likuiditas), pola jam pembukaan.
Catatan: bar hanya ada di menit yang ADA transaksinya (saham sepi = sedikit bar). Bar 1 menit Yahoo berakhir ~15:49 WIB;
harga penutupan resmi (lelang penutupan ~16:00) ada di data harian. Waktu disimpan sebagai WIB (Asia/Jakarta) tanpa zona.

Isi (format panjang: waktu, kode, buka, tertinggi, terendah, tutup, volume):
  harian    : data/raw/harian/intraday_idx/<tanggal UTC>.parquet  = bar 1 MENIT 3 hari bursa terakhir (tumpang tindih)
  --histori : data/raw/histori/intraday_idx/5m_<tanggal>.parquet (5 menit ~60 hari) & 1h_<tanggal>.parquet (1 jam ~2 thn)
  --tes     : 10 saham, tanpa simpan
"""
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

from daftar_saham import kode_idx

logging.getLogger("yfinance").setLevel(logging.CRITICAL)
HARI_INI = datetime.now(timezone.utc).date()
TES, HISTORI = "--tes" in sys.argv, "--histori" in sys.argv
MIN_KODE = 300                                  # di bawah ini = ada masalah (email alarm)


def unduh(kode, interval, period):
    bagian = []
    for i in range(0, len(kode), 100):
        kelompok = kode[i:i + 100]
        for percobaan in range(3):
            try:
                df = yf.download(kelompok, period=period, interval=interval, auto_adjust=False, progress=False,
                                 group_by="ticker", threads=True)
                break
            except Exception as e:
                print(f"   🔌 {interval} kelompok {i // 100 + 1}: {type(e).__name__}, coba lagi...")
                time.sleep(20 * (percobaan + 1))
        else:
            continue
        for k in kelompok:
            if k not in df.columns.get_level_values(0):
                continue
            d = df[k].dropna(subset=["Close"])
            if d.empty:
                continue
            d = d[["Open", "High", "Low", "Close", "Volume"]].copy()
            d.columns = ["buka", "tertinggi", "terendah", "tutup", "volume"]
            d["kode"] = k.replace(".JK", "")
            bagian.append(d)
        time.sleep(3)
    if not bagian:
        return None
    hasil = pd.concat(bagian)
    idx = pd.DatetimeIndex(hasil.index)
    idx = idx.tz_convert("Asia/Jakarta") if idx.tz is not None else idx
    hasil.index = idx.tz_localize(None).astype("datetime64[ns]")
    hasil = hasil.rename_axis("waktu").reset_index()
    hasil["kode"] = hasil["kode"].astype("string")
    for c in ["buka", "tertinggi", "terendah", "tutup", "volume"]:
        hasil[c] = hasil[c].astype("float64")
    return hasil[["waktu", "kode", "buka", "tertinggi", "terendah", "tutup", "volume"]].sort_values(["kode", "waktu"])


def ringkas(df, nama):
    hari = df["waktu"].dt.date.nunique()
    per = df.groupby([df["kode"], df["waktu"].dt.date]).size()
    print(f"✅ {nama}: {len(df):,} bar, {df['kode'].nunique()} kode, {hari} hari ({df['waktu'].min()} s/d {df['waktu'].max()}) | "
          f"bar per saham-hari: median {per.median():.0f}, maks {per.max()}")


kode = kode_idx(termasuk_etf=True)
if TES:
    kode = ["BBCA.JK", "TINS.JK", "SIPD.JK", "ADRO.JK", "XIIT.JK", "GOTO.JK", "BREN.JK", "AALI.JK", "TELE.JK", "MGLV.JK"]
print(f"📋 {len(kode)} kode")

if HISTORI:
    folder = Path("data/raw/histori/intraday_idx")
    folder.mkdir(parents=True, exist_ok=True)
    for interval, period in [("5m", "60d"), ("1h", "730d")]:
        df = unduh(kode, interval, period)
        ringkas(df, f"histori {interval}")
        df.to_parquet(folder / f"{interval}_{HARI_INI.isoformat()}.parquet", index=False)
    print(f"💾 {folder}/ (upload: python upload_satu.py {folder.as_posix()})")
    sys.exit()

df = unduh(kode, "1m", "5d")
if df is None:
    print("❌ intraday: tidak ada data")
    sys.exit(1)
tiga_hari = sorted(df["waktu"].dt.normalize().unique())[-3:]          # 3 hari bursa terakhir
df = df[df["waktu"].dt.normalize().isin(tiga_hari)]
ringkas(df, "intraday 1 menit")
if TES:
    print(df.groupby("kode").size().to_string())
    sys.exit()
if df["kode"].nunique() < MIN_KODE:
    print(f"❌ hanya {df['kode'].nunique()} kode (< {MIN_KODE})")
    sys.exit(1)
folder = Path("data/raw/harian/intraday_idx")
folder.mkdir(parents=True, exist_ok=True)
df.to_parquet(folder / f"{HARI_INI.isoformat()}.parquet", index=False)
print(f"💾 {folder}/{HARI_INI.isoformat()}.parquet ({(folder / f'{HARI_INI.isoformat()}.parquet').stat().st_size / 1e6:.1f} MB)")
