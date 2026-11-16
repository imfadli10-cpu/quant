import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

API = "https://api.exchange.coinbase.com"
HEADER = {"User-Agent": "quant-data-collector/1.0 (personal research project)"}
KOLOM = ["waktu", "low", "high", "open", "close", "volume"]
BATAS_AWAL = datetime(2014, 1, 1, tzinfo=timezone.utc)
sekarang = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

sementara = Path("data/sementara/crypto_histori")
sementara.mkdir(parents=True, exist_ok=True)


def minta(url, params=None):
    """Kembalikan data, [] kalau memang kosong, atau None kalau gagal."""
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


produk = minta(f"{API}/products")
pasangan = sorted(p["id"] for p in produk
                  if p["quote_currency"] == "USD" and p.get("status") == "online"
                  and not p.get("trading_disabled"))
print(f"🪙 {len(pasangan)} koin\n")

for i, kode in enumerate(pasangan, start=1):
    file = sementara / f"{kode}.parquet"
    if file.exists():
        continue

    potongan, gagal = [], False
    akhir = sekarang
    while akhir > BATAS_AWAL:
        awal = akhir - timedelta(days=299)
        data = minta(f"{API}/products/{kode}/candles", params={
            "granularity": 86400, "start": awal.isoformat(), "end": akhir.isoformat()})
        if data is None:          # gagal (bukan kosong) → jangan tandai selesai
            gagal = True
            break
        if not data:              # kosong → sudah sampai awal perdagangan koin ini
            break
        potongan.append(pd.DataFrame(data, columns=KOLOM))
        akhir = awal
        time.sleep(0.2)

    if gagal:
        print(f"⚠️  [{i}/{len(pasangan)}] {kode}: gagal, dicoba lagi saat program dijalankan ulang")
        continue
    if not potongan:
        pd.DataFrame(columns=KOLOM + ["kode"]).to_parquet(file, index=False)
        print(f"⚪ [{i}/{len(pasangan)}] {kode}: tidak ada histori")
        continue

    df = pd.concat(potongan).drop_duplicates("waktu")
    df["waktu"] = pd.to_datetime(df["waktu"], unit="s")
    df = df.sort_values("waktu").assign(kode=kode)
    df.to_parquet(file, index=False)
    print(f"✅ [{i}/{len(pasangan)}] {kode}: {len(df):,} hari sejak {df['waktu'].min().date()}")

# ===== Gabungkan semua koin jadi satu file =====
semua = [pd.read_parquet(f) for f in sementara.glob("*.parquet")]
semua = pd.concat([d for d in semua if not d.empty], ignore_index=True)
tujuan = Path("data/raw/histori/crypto_harian")
tujuan.mkdir(parents=True, exist_ok=True)
semua.to_parquet(tujuan / "semua.parquet", index=False)
print(f"\n🎉 {semua['kode'].nunique()} koin, {len(semua):,} baris → {tujuan / 'semua.parquet'}")