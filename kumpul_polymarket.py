"""
Foto HARIAN pasar prediksi Polymarket (data "hanya ke depan").

Apa ini: orang bertaruh uang sungguhan pada kejadian nyata (keputusan The Fed, resesi, pemilu, perang, harga komoditas).
Harga "Yes" 0,73 = pasar memperkirakan peluang 73%. Daftar pasar aktif + peluangnya hari ini TIDAK bisa diambil ulang
besok -> harus difoto tiap hari. Data "aneh" ala Renaissance: keyakinan kolektif yang dipertaruhkan dengan uang.

Yang difoto: 2.100 pasar dengan volume 24 jam terbesar + 2.100 pasar dengan likuiditas terbesar (dobel dibuang,
~3.000 pasar). Semua pasar aktif jumlahnya sangat besar (puluhan ribu, kebanyakan taruhan kecil olahraga/kripto per jam)
dan API membatasi offset maks ~2.100 per urutan.
Sumber: https://gamma-api.polymarket.com/markets (publik, tanpa kunci).

Isi: data/raw/harian/polymarket/<tanggal UTC>.parquet, 1 baris = 1 pasar:
  waktu_ambil, id, id_kondisi, pertanyaan, slug, acara, label_acara, hasil (JSON teks), harga_hasil (JSON teks),
  harga_ya (harga hasil pertama), tawar_terbaik, minta_terbaik, harga_terakhir, volume_24j, volume_total,
  likuiditas, ubah_1hari, ubah_1minggu, tanggal_akhir, dibuat
Cara pakai:  python kumpul_polymarket.py        |   python kumpul_polymarket.py --tes  (tanpa simpan)
"""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

URL = "https://gamma-api.polymarket.com/markets"
HEADER = {"User-Agent": "quant-data-collector/1.0 (personal research project)"}
SEKARANG = datetime.now(timezone.utc)
MAKS_OFFSET = 2000          # API menolak offset lebih besar (pakai keyset untuk lebih dalam; tidak perlu)


def ambil_halaman(urutan, offset):
    for percobaan in range(4):
        try:
            r = requests.get(URL, params={"limit": 100, "offset": offset, "active": "true", "closed": "false",
                                          "order": urutan, "ascending": "false"}, headers=HEADER, timeout=60)
            if r.status_code == 429:
                time.sleep(30)
                continue
            if r.status_code == 422:            # offset terlalu dalam
                return []
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            print(f"   🔌 {urutan} offset {offset}: {type(e).__name__}, coba lagi...")
            time.sleep(10 * (percobaan + 1))
    print(f"   ⚠️  {urutan} offset {offset}: gagal 4x, dilewati")
    return []


def angka(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


semua = {}
for urutan in ["volume24hr", "liquidityNum"]:
    for offset in range(0, MAKS_OFFSET + 1, 100):
        halaman = ambil_halaman(urutan, offset)
        for m in halaman:
            semua[m["id"]] = m
        if len(halaman) < 100:
            break
        time.sleep(0.3)
print(f"📥 {len(semua):,} pasar unik")

baris = []
for m in semua.values():
    try:
        harga = json.loads(m.get("outcomePrices") or "[]")
    except (TypeError, ValueError):
        harga = []
    acara = (m.get("events") or [{}])[0]
    baris.append({
        "waktu_ambil": SEKARANG.replace(tzinfo=None), "id": str(m.get("id")), "id_kondisi": str(m.get("conditionId") or ""),
        "pertanyaan": str(m.get("question") or ""), "slug": str(m.get("slug") or ""),
        "acara": str(acara.get("title") or ""), "label_acara": str(m.get("groupItemTitle") or ""),
        "hasil": str(m.get("outcomes") or ""), "harga_hasil": str(m.get("outcomePrices") or ""),
        "harga_ya": angka(harga[0]) if harga else float("nan"),
        "tawar_terbaik": angka(m.get("bestBid")), "minta_terbaik": angka(m.get("bestAsk")),
        "harga_terakhir": angka(m.get("lastTradePrice")), "volume_24j": angka(m.get("volume24hr")),
        "volume_total": angka(m.get("volumeNum")), "likuiditas": angka(m.get("liquidityNum")),
        "ubah_1hari": angka(m.get("oneDayPriceChange")), "ubah_1minggu": angka(m.get("oneWeekPriceChange")),
        "tanggal_akhir": pd.to_datetime(m.get("endDate"), errors="coerce", utc=True),
        "dibuat": pd.to_datetime(m.get("createdAt"), errors="coerce", utc=True)})
df = pd.DataFrame(baris)
for k in ["tanggal_akhir", "dibuat"]:
    df[k] = df[k].dt.tz_localize(None).astype("datetime64[ns]")
df["waktu_ambil"] = df["waktu_ambil"].astype("datetime64[ns]")
df = df.sort_values("volume_24j", ascending=False).reset_index(drop=True)
print(f"✅ polymarket: {len(df):,} pasar | volume 24j total ${df['volume_24j'].sum() / 1e6:,.1f} juta | "
      f"> $10.000/hari: {(df['volume_24j'] > 1e4).sum()} pasar")

if "--tes" in sys.argv:
    print(df.dtypes.to_string())
    print(df[["pertanyaan", "harga_ya", "volume_24j", "likuiditas", "tanggal_akhir"]].head(12).to_string())
    kata = df["pertanyaan"].str.contains("Indonesia|rupiah|Jakarta|Prabowo", case=False)
    print(f"\nPasar terkait Indonesia: {kata.sum()}")
    print(df.loc[kata, ["pertanyaan", "harga_ya", "volume_24j"]].head(8).to_string())
    sys.exit()

folder = Path("data/raw/harian/polymarket")
folder.mkdir(parents=True, exist_ok=True)
df.to_parquet(folder / f"{SEKARANG.date().isoformat()}.parquet", index=False)
print(f"💾 {folder}/{SEKARANG.date().isoformat()}.parquet")
