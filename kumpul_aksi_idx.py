"""
Aksi korporasi semua saham & ETF IDX dari Yahoo: DIVIDEN tunai (Rp per lembar) & STOCK SPLIT (rasio), seluruh histori.

Kenapa:
  1) Cek kualitas data: penyesuaian split Yahoo kadang meleset (AKRA split 5:1 tercatat 27-07-2007 tapi lonjakan harga
     ada di 30-07-2007) -> titik rusak bisa dijelaskan, bukan sekadar dibuang.
  2) Harga transaksi ASLI bisa dibangun ulang (Close Yahoo sudah disesuaikan split -> saringan "harga >= Rp100" di riset
     lama memakai info masa depan).
  3) Bahan riset dividen (yield, efek sekitar tanggal ex-dividen).
Tanggal = tanggal EX (cum terakhir = hari bursa sebelumnya), WIB tanpa zona.

Hasil:
  data/raw/aksi_idx/semua.parquet          kode, tanggal, dividen, split   (DITIMPA tiap jalan)
  data/raw/aksi_idx/foto/<tanggal>.parquet salinan foto minggu itu (melacak kapan pengumuman masuk & revisi)
Cara pakai:
  python kumpul_aksi_idx.py          -> semua kode, simpan
  python kumpul_aksi_idx.py --tes    -> 15 kode, tanpa simpan
"""
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

from daftar_saham import kode_idx

logging.getLogger("yfinance").setLevel(logging.CRITICAL)
HARI_INI = datetime.now(timezone.utc).date()
TES = "--tes" in sys.argv
PEKERJA = 3
MIN_KODE_OK = 500                 # kode yang punya minimal satu aksi; kurang dari ini = ada masalah (email alarm)
FOLDER = Path("data/raw/aksi_idx")


def jadi_tanggal(idx):
    t = pd.DatetimeIndex(pd.to_datetime(idx))
    if t.tz is not None:
        t = t.tz_localize(None)            # JANGAN .values pada tanggal ber-zona (bisa geser 1 hari)
    return t.normalize().astype("datetime64[ns]")


def ambil_satu(kode):
    """DataFrame aksi satu kode (bisa kosong). None = gagal setelah 5 percobaan."""
    for percobaan in range(5):
        try:
            a = yf.Ticker(kode).actions
            if a is None or a.empty:
                return pd.DataFrame()
            a = a.reindex(columns=["Dividends", "Stock Splits"], fill_value=0.0).astype("float64")  # kolom bisa tidak ada
            df = pd.DataFrame({"kode": kode.removesuffix(".JK"), "tanggal": jadi_tanggal(a.index),
                               "dividen": a["Dividends"].values, "split": a["Stock Splits"].values})
            return df[(df["dividen"] != 0) | (df["split"] != 0)]
        except Exception as e:
            kena_batas = "RateLimit" in type(e).__name__ or "Too Many Requests" in str(e)
            if percobaan == 4:
                print(f"   ⚠️  {kode}: {type(e).__name__}: {str(e)[:80]}")
            time.sleep(60 if kena_batas else 3 * (percobaan + 1))
    return None


kode_semua = kode_idx(termasuk_etf=True)
if TES:
    kode_semua = ["AKRA.JK", "BBRI.JK", "ANTM.JK", "HMSP.JK", "XIIT.JK"] + kode_semua[:10]
print(f"📋 {len(kode_semua)} kode IDX (saham + ETF), {PEKERJA} unduhan paralel...")
mulai, bagian, gagal = time.time(), [], []
with ThreadPoolExecutor(max_workers=PEKERJA) as pool:
    tugas = {pool.submit(ambil_satu, k): k for k in kode_semua}
    for i, f in enumerate(as_completed(tugas), 1):
        hasil = f.result()
        if hasil is None:
            gagal.append(tugas[f])
        elif len(hasil):
            bagian.append(hasil)
        if i % 200 == 0:
            print(f"   {i}/{len(kode_semua)} ({time.time() - mulai:.0f} detik)")
if gagal and not TES:
    print(f"🔁 {len(gagal)} kode gagal, dicoba ulang pelan-pelan...")
    time.sleep(60)
    for k in gagal:
        hasil = ambil_satu(k)
        if hasil is not None and len(hasil):
            bagian.append(hasil)
        time.sleep(1)

d = pd.concat(bagian, ignore_index=True).sort_values(["kode", "tanggal"]).drop_duplicates(["kode", "tanggal"], keep="last")
d["kode"] = d["kode"].astype(str)
n_kode = d["kode"].nunique()
print(f"✅ {len(d):,} aksi dari {n_kode} kode ({time.time() - mulai:.0f} detik): "
      f"{(d['dividen'] > 0).sum():,} dividen, {(d['split'] > 0).sum():,} split | "
      f"{d['tanggal'].min():%Y-%m-%d} s/d {d['tanggal'].max():%Y-%m-%d}")
# Cek kewajaran: split 'terbalik' (< 1 = reverse split) & dividen negatif
print(f"   reverse split (rasio < 1): {((d['split'] > 0) & (d['split'] < 1)).sum()} | dividen negatif: {(d['dividen'] < 0).sum()}")
if TES:
    print(d[d["kode"].isin(["AKRA", "BBRI"])].tail(8).to_string(index=False))
    print("🧪 mode tes: tidak disimpan")
    sys.exit(0)
if n_kode < MIN_KODE_OK:
    print(f"❌ cuma {n_kode} kode punya aksi (min {MIN_KODE_OK}) -> tidak disimpan")
    sys.exit(1)
(FOLDER / "foto").mkdir(parents=True, exist_ok=True)
d.to_parquet(FOLDER / "semua.parquet", index=False)
d.to_parquet(FOLDER / "foto" / f"{HARI_INI.isoformat()}.parquet", index=False)
print(f"💾 {FOLDER}/semua.parquet + foto/{HARI_INI.isoformat()}.parquet")
