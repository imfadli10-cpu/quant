import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

API = "https://api.exchange.coinbase.com"
HEADER = {"User-Agent": "quant-data-collector/1.0 (personal research project)"}
sekarang = datetime.now(timezone.utc)
hari_ini = date.today().isoformat()


def minta(url, params=None):
    """Permintaan ke Coinbase, sabar kalau kena batas."""
    for percobaan in range(4):
        try:
            r = requests.get(url, params=params, headers=HEADER, timeout=30)
            if r.status_code == 429:
                time.sleep(5 * (percobaan + 1))
                continue
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException:
            time.sleep(5)
    return None


# ===== 1. Daftar semua pasangan crypto/USD yang aktif =====
produk = minta(f"{API}/products")
pasangan = sorted(p["id"] for p in produk
                  if p["quote_currency"] == "USD"
                  and p.get("status") == "online"
                  and not p.get("trading_disabled"))
print(f"🪙 {len(pasangan)} pasangan crypto/USD aktif\n")

# ===== 2. Ambil candle harian & per jam =====
KOLOM = ["waktu", "low", "high", "open", "close", "volume"]
harian, per_jam = [], []
for i, kode in enumerate(pasangan, start=1):
    for granularitas, mundur, wadah in [(86400, timedelta(days=14), harian),
                                         (3600, timedelta(days=3), per_jam)]:
        data = minta(f"{API}/products/{kode}/candles", params={
            "granularity": granularitas,
            "start": (sekarang - mundur).isoformat(),
            "end": sekarang.isoformat(),
        })
        if data:
            df = pd.DataFrame(data, columns=KOLOM)
            df["waktu"] = pd.to_datetime(df["waktu"], unit="s")
            wadah.append(df.assign(kode=kode))
        time.sleep(0.15)
    if i % 50 == 0:
        print(f"  ... {i}/{len(pasangan)}")

# ===== 3. Simpan =====
for nama, wadah in [("crypto_harian", harian), ("crypto_jam", per_jam)]:
    gabung = pd.concat(wadah, ignore_index=True).sort_values(["kode", "waktu"])
    folder = Path(f"data/raw/harian/{nama}")
    folder.mkdir(parents=True, exist_ok=True)
    gabung.to_parquet(folder / f"{hari_ini}.parquet", index=False)
    print(f"✅ {nama}: {gabung['kode'].nunique()} koin, {len(gabung):,} baris")