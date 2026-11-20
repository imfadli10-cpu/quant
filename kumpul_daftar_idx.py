"""
Foto HARIAN daftar saham Bursa Efek Indonesia menurut Yahoo (screener bursa JKT) + jaga daftar kode tambahan.

Kenapa:
 1. Daftar awal ref/daftar_saham.xlsx statis -> saham yang IPO kemudian TIDAK ikut terkumpul. Kode baru yang muncul
    di Yahoo ditambahkan otomatis ke ref/daftar_saham_tambahan.csv (tidak pernah dikurangi), dipakai semua collector
    lewat daftar_saham.py.
 2. Fotonya sendiri = data "hanya ke depan": kapitalisasi pasar, saham beredar, BID/ASK (spread nyata, untuk mengecek
    perkiraan spread Corwin-Schultz di riset #12c), tanggal rilis laporan berikutnya, rating analis, dll.
Catatan: daftar Yahoo TIDAK lengkap (20 Nov 2026: 838 saham, 106 saham kita tidak ada, mis. ADHI) -> hanya untuk
MENAMBAH, tidak pernah untuk membuang.
WAKTU: jalan ~07:17 WIB sebelum bursa buka -> bid/ask = sisa antrean penutupan hari sebelumnya.

Isi: data/raw/harian/daftar_idx/<tanggal UTC>.parquet (1 baris = 1 saham, semua kolom skalar dari Yahoo + waktu_ambil)
     data/ref/daftar_saham_tambahan.csv (kode, pertama_terlihat, nama)
Cara pakai:  python kumpul_daftar_idx.py   |   python kumpul_daftar_idx.py --tes  (tanpa simpan)
"""
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf
from yfinance import EquityQuery

from daftar_saham import kode_idx

logging.getLogger("yfinance").setLevel(logging.CRITICAL)
SEKARANG = datetime.now(timezone.utc)
MIN_SAHAM = 600                  # kurang dari ini = ada masalah dengan screener -> error (email alarm)

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
        print("❌ daftar_idx: screener Yahoo gagal 4x")
        sys.exit(1)
    halaman = r.get("quotes", [])
    total = r.get("total", total)
    quotes += halaman
    offset += 250
    if not halaman or offset >= (total or 0):
        break
    time.sleep(1)

baris = []
for q in quotes:
    b = {"waktu_ambil": SEKARANG.replace(tzinfo=None), "kode": q.get("symbol", "").replace(".JK", "")}
    for k, v in q.items():
        if isinstance(v, (dict, list)):
            b[k] = json.dumps(v, ensure_ascii=False)        # kolom bertingkat (mis. corporateActions) disimpan sebagai teks
        else:
            b[k] = v
    baris.append(b)
df = pd.DataFrame(baris).drop_duplicates("kode")
for k in df.columns:                                       # paksa tipe: angka -> float, sisanya teks
    if k == "waktu_ambil":
        continue
    angka = pd.to_numeric(df[k], errors="coerce")
    df[k] = angka.astype("float64") if angka.notna().sum() >= 0.5 * df[k].notna().sum() and df[k].notna().any() \
        and not df[k].astype(str).str.contains("[A-Za-z]", regex=True).any() else df[k].astype("string")
df["waktu_ambil"] = df["waktu_ambil"].astype("datetime64[ns]")
spread = (df["ask"] - df["bid"]) / ((df["ask"] + df["bid"]) / 2)
spread = spread[(df["bid"] > 0) & (df["ask"] > df["bid"])]
print(f"✅ daftar_idx: {len(df)} saham (total Yahoo {total}) | kolom {df.shape[1]} | "
      f"spread bid-ask median {spread.median():.2%} ({len(spread)} saham punya bid & ask)")
if len(df) < MIN_SAHAM:
    print(f"❌ hanya {len(df)} saham (< {MIN_SAHAM})")
    sys.exit(1)

# Kode baru (ada di Yahoo, belum ada di daftar gabungan) -> tambahan
sudah = set(kode_idx(akhiran=""))
baru = df[~df["kode"].isin(sudah) & (df.get("quoteType", "EQUITY") == "EQUITY")]
print(f"🆕 kode baru dibanding daftar gabungan: {len(baru)} {sorted(baru['kode'])[:20]}")

if "--tes" in sys.argv:
    print(df[["kode", "longName", "marketCap", "sharesOutstanding", "bid", "ask", "earningsTimestamp"]].head(8).to_string())
    sys.exit()

folder = Path("data/raw/harian/daftar_idx")
folder.mkdir(parents=True, exist_ok=True)
df.to_parquet(folder / f"{SEKARANG.date().isoformat()}.parquet", index=False)
if len(baru):
    ref = Path("data/ref/daftar_saham_tambahan.csv")
    lama = None
    try:
        from daftar_saham import _berkas
        f = _berkas("daftar_saham_tambahan.csv")
        lama = pd.read_csv(f, dtype=str, keep_default_na=False) if f is not None else None
    except Exception as e:
        print(f"❌ gagal membaca daftar tambahan lama ({type(e).__name__}) -> tidak menulis supaya tidak tertimpa")
        sys.exit(1)
    tambah = pd.DataFrame({"kode": baru["kode"], "pertama_terlihat": SEKARANG.date().isoformat(),
                           "nama": baru.get("longName", baru.get("shortName", ""))})
    gabung = pd.concat([lama, tambah], ignore_index=True) if lama is not None else tambah
    ref.parent.mkdir(parents=True, exist_ok=True)
    gabung.drop_duplicates("kode").to_csv(ref, index=False)
    print(f"📝 {len(tambah)} kode ditambahkan ke {ref}")
print(f"💾 {folder}/{SEKARANG.date().isoformat()}.parquet")
