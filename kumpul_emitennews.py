"""
Berita emiten IDX dari SITEMAP EmitenNews (emitennews.com; robots.txt mengizinkan /news/ & mencantumkan sitemap).
Hanya membaca sitemap (URL + tanggal), TIDAK membuka halaman artikel. Judul = slug URL (huruf kecil, tanda '-' jadi spasi);
judul asli memuat kode saham dalam kurung, mis. "... Bakrie (BUMI) ..." -> slug "...-bakrie-bumi-..." -> pencocokan kode saat riset.
Tanggal = <lastmod> sitemap. Divalidasi 21 Nov 2026: sama dengan tanggal terbit di halaman pada 7/7 artikel yang halamannya masih ada
(artikel 2017-2019 sebagian dialihkan ke beranda, tidak bisa dicek). Jam terbit TIDAK ada di sitemap -> riset pakai hari bursa berikutnya.
Isi: ~1.100 (2017) s/d ~16.000 (2023) artikel per tahun sejak 2017-03.

  python kumpul_emitennews.py            harian: sitemap-current-1..2 -> data/raw/harian/emitennews/<tanggal UTC>.parquet
  python kumpul_emitennews.py --histori  semua sitemap tahunan + current -> data/raw/histori/emitennews/semua.parquet
  python kumpul_emitennews.py --tes      cek tanpa simpan
"""
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

H = {"User-Agent": "quant-data-collector/1.0 (personal research project)"}
DASAR = "https://www.emitennews.com"
SEKARANG = datetime.now(timezone.utc)
HISTORI, TES = "--histori" in sys.argv, "--tes" in sys.argv


def ambil(url):
    for coba in range(4):
        try:
            r = requests.get(url, headers=H, timeout=60)
            if r.status_code == 200:
                return r.text
            print(f"   ⚠️ {url}: HTTP {r.status_code}")
        except Exception as e:
            print(f"   🔌 {url}: {type(e).__name__}")
        time.sleep(10 * (coba + 1))
    return None


def baca_sitemap(nama):
    teks = ambil(f"{DASAR}/{nama}")
    if teks is None:
        return None
    it = re.findall(r"<loc>\s*([^<]+?)\s*</loc>\s*<lastmod>([^<]+)</lastmod>", teks)
    d = pd.DataFrame(it, columns=["url", "lastmod"])
    d["sitemap"] = nama
    return d


indeks = ambil(f"{DASAR}/sitemap.xml")
if indeks is None:
    print("❌ sitemap indeks tidak bisa dibaca")
    sys.exit(1)
semua_nama = [u.rsplit("/", 1)[-1] for u in re.findall(r"<loc>\s*([^<]+?)\s*</loc>", indeks)]
if HISTORI:
    nama_ambil = [n for n in semua_nama if re.match(r"sitemap-(current-\d+|20\d\d)\.xml$", n)]
else:
    nama_ambil = [n for n in semua_nama if n in ("sitemap-current-1.xml", "sitemap-current-2.xml")]
bagian = []
for n in nama_ambil:
    d = baca_sitemap(n)
    if d is not None:
        bagian.append(d)
        print(f"   {n}: {len(d)} artikel", flush=True)
    time.sleep(2)
if not bagian:
    print("❌ tidak ada sitemap terbaca")
    sys.exit(1)
df = pd.concat(bagian, ignore_index=True)
df = df[df["url"].str.contains("/news/", regex=False)]
df["slug"] = df["url"].str.rsplit("/", n=1).str[-1]
df["judul_slug"] = df["slug"].str.replace("-", " ", regex=False)
df["tanggal"] = pd.to_datetime(df["lastmod"].str[:10], errors="coerce").astype("datetime64[ns]")
df["waktu_ambil"] = SEKARANG.replace(tzinfo=None)
df["waktu_ambil"] = df["waktu_ambil"].astype("datetime64[ns]")
df = df.dropna(subset=["tanggal"]).drop_duplicates("url", keep="first").sort_values("tanggal").reset_index(drop=True)
for k in ["url", "lastmod", "sitemap", "slug", "judul_slug"]:
    df[k] = df[k].astype("string")
print(f"✅ emitennews: {len(df):,} artikel, {df['tanggal'].min():%Y-%m-%d} s/d {df['tanggal'].max():%Y-%m-%d}")
if len(df) < (30000 if HISTORI else 200):
    print("❌ terlalu sedikit artikel -> ada masalah")
    sys.exit(1)
if TES:
    print(df.tail(3)[["tanggal", "judul_slug"]].to_string())
    sys.exit(0)
if HISTORI:
    f = Path("data/raw/histori/emitennews/semua.parquet")
else:
    f = Path(f"data/raw/harian/emitennews/{SEKARANG.date().isoformat()}.parquet")
f.parent.mkdir(parents=True, exist_ok=True)
df.to_parquet(f, index=False)
print(f"💾 {f}")
