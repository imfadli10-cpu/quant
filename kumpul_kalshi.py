"""
Foto HARIAN pasar prediksi Kalshi (bursa prediksi teregulasi CFTC di AS; data "hanya ke depan").

Pelengkap Polymarket: Kalshi punya banyak pasar EKONOMI & KEUANGAN yang terstruktur, mis. angka CPI/NFP/PDB bulan ini,
keputusan The Fed, rentang S&P 500/Nasdaq/emas/minyak/kurs akhir hari/minggu, imbal hasil obligasi, suhu kota, cuaca.
Harga "Yes" 0,73 = pasar memperkirakan peluang 73%. Daftar pasar aktif + peluangnya hari ini TIDAK bisa diambil mundur.

Yang difoto: SEMUA event yang masih terbuka beserta pasarnya, KECUALI kategori olahraga (Sports: >120 ribu pasar
taruhan pertandingan, tidak relevan) dan pasar parlay gabungan (KXMVE). ~85 ribu pasar, ~5 menit.
Sumber: https://api.elections.kalshi.com/trade-api/v2 (/series, /events; data pasar publik tanpa kunci).

Isi: data/raw/harian/kalshi/<tanggal UTC>.parquet, 1 baris = 1 pasar:
  waktu_ambil, kategori, seri, event, judul_event, sub_judul_event, ticker, judul, sub_judul_ya, jenis_strike,
  strike_bawah, strike_atas, ya_tawar, ya_minta, harga_terakhir, harga_kemarin, volume_24j, volume_total,
  open_interest, buka, tutup, status
Cara pakai:  python kumpul_kalshi.py        |   python kumpul_kalshi.py --tes  (5 halaman, tanpa simpan)
"""
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

URL = "https://api.elections.kalshi.com/trade-api/v2"
HEADER = {"User-Agent": "quant-data-collector/1.0 (personal research project)"}
SEKARANG = datetime.now(timezone.utc)
TES = "--tes" in sys.argv
KECUALI = {"Sports"}
MIN_PASAR_OK = 20000          # kurang dari ini (di mode penuh) = ada masalah -> keluar dengan error


def minta(jalur, params):
    for percobaan in range(6):
        try:
            r = requests.get(URL + jalur, params=params, headers=HEADER, timeout=90)
            if r.status_code == 429:
                time.sleep(int(r.headers.get("Retry-After", 10)))
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            if percobaan == 5:
                raise
            print(f"   ⚠️  {jalur}: {type(e).__name__}, coba lagi")
            time.sleep(5 * (percobaan + 1))
    raise RuntimeError(f"{jalur}: gagal terus (rate limit)")


def angka(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def waktu(x):
    t = pd.to_datetime(x, utc=True, errors="coerce")
    return t.tz_localize(None) if pd.notna(t) else pd.NaT


mulai = time.time()
kategori = {s["ticker"]: s.get("category") or "" for s in minta("/series", {})["series"]}
print(f"📋 {len(kategori):,} seri Kalshi")

baris, cur, hal = [], None, 0
while True:
    p = {"limit": 200, "status": "open", "with_nested_markets": "true"}
    if cur:
        p["cursor"] = cur
    j = minta("/events", p)
    hal += 1
    for e in j.get("events", []):
        kat = kategori.get(e.get("series_ticker"), "")
        if kat in KECUALI or str(e.get("event_ticker", "")).startswith("KXMVE"):
            continue
        for m in e.get("markets") or []:
            baris.append({
                "kategori": kat, "seri": e.get("series_ticker"), "event": e.get("event_ticker"),
                "judul_event": e.get("title"), "sub_judul_event": e.get("sub_title"),
                "ticker": m.get("ticker"), "judul": m.get("title"), "sub_judul_ya": m.get("yes_sub_title"),
                "jenis_strike": m.get("strike_type"),
                "strike_bawah": angka(m.get("floor_strike")), "strike_atas": angka(m.get("cap_strike")),
                "ya_tawar": angka(m.get("yes_bid_dollars")), "ya_minta": angka(m.get("yes_ask_dollars")),
                "harga_terakhir": angka(m.get("last_price_dollars")),
                "harga_kemarin": angka(m.get("previous_price_dollars")),
                "volume_24j": angka(m.get("volume_24h_fp")), "volume_total": angka(m.get("volume_fp")),
                "open_interest": angka(m.get("open_interest_fp")),
                "buka": waktu(m.get("open_time")), "tutup": waktu(m.get("close_time")), "status": m.get("status"),
            })
    cur = j.get("cursor")
    if hal % 20 == 0:
        print(f"   halaman {hal}: {len(baris):,} pasar ({time.time() - mulai:.0f} detik)")
    if not cur or (TES and hal >= 5):
        break
    time.sleep(0.2)

df = pd.DataFrame(baris).drop_duplicates("ticker")
df.insert(0, "waktu_ambil", pd.Timestamp(SEKARANG).tz_localize(None))
df["waktu_ambil"] = df["waktu_ambil"].astype("datetime64[ns]")
for k in ["buka", "tutup"]:
    df[k] = pd.to_datetime(df[k]).astype("datetime64[ns]")
for k in df.columns:
    if df[k].dtype == object:
        df[k] = df[k].astype("string")
print(f"✅ {len(df):,} pasar dari {df['event'].nunique():,} event ({hal} halaman, {time.time() - mulai:.0f} detik)")
print("   per kategori: " + ", ".join(f"{k} {v:,}" for k, v in df["kategori"].value_counts().items()))
print(f"   volume 24 jam: {df['volume_24j'].sum():,.0f} kontrak | harga Ya di luar 0-1: "
      f"{((df['harga_terakhir'] < 0) | (df['harga_terakhir'] > 1)).sum()}")
if TES:
    print(df[df["kategori"] == "Economics"].nlargest(5, "volume_24j")[["judul", "sub_judul_ya", "harga_terakhir", "volume_24j"]]
          .to_string(index=False))
    print("🧪 mode tes: tidak disimpan")
    sys.exit()
if len(df) < MIN_PASAR_OK:
    print(f"❌ cuma {len(df):,} pasar (min {MIN_PASAR_OK:,}) -> tidak disimpan")
    sys.exit(1)
folder = Path("data/raw/harian/kalshi")
folder.mkdir(parents=True, exist_ok=True)
df.to_parquet(folder / f"{SEKARANG.date().isoformat()}.parquet", index=False)
print(f"💾 {folder}/{SEKARANG.date().isoformat()}.parquet")
