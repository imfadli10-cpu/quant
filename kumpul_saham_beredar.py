"""
HISTORI JUMLAH SAHAM BEREDAR semua saham IDX dari Yahoo (`Ticker.get_shares_full`) -> kapitalisasi pasar historis & net issuance.
Umumnya tersedia sejak 2013-2016 (ratusan titik per saham). Angka BELUM disesuaikan split (pakai raw/aksi_idx saat riset) dan bisa
berisik (titik ganda/lompatan) -> bersihkan saat dipakai. Setiap jalan mengambil ULANG seluruh histori lalu menggabung dengan file lama
(baris lama dipertahankan; data baru menang untuk (kode, tanggal) yang sama) -> revisi Yahoo tidak menghapus catatan lama.

  python kumpul_saham_beredar.py        -> data/raw/saham_beredar/semua.parquet (kode, tanggal, saham_beredar, waktu_ambil)
  python kumpul_saham_beredar.py --tes  -> 10 saham, tanpa simpan
Butuh HF_TOKEN (daftar kode via daftar_saham.kode_idx & file lama dari gudang).
"""
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

from daftar_saham import kode_idx

logging.getLogger("yfinance").setLevel(logging.CRITICAL)
TES = "--tes" in sys.argv
SEKARANG = datetime.now(timezone.utc).replace(tzinfo=None)
FILE = Path("data/raw/saham_beredar/semua.parquet")
JALUR_HF = "raw/saham_beredar/semua.parquet"


def ambil(kode):
    for coba in range(3):
        try:
            s = yf.Ticker(kode).get_shares_full(start="2000-01-01")
            if s is None or len(s) == 0:
                return None
            ix = pd.DatetimeIndex(s.index)
            ix = ix.tz_convert("Asia/Jakarta").tz_localize(None) if ix.tz is not None else ix
            d = pd.DataFrame({"kode": kode.replace(".JK", ""), "tanggal": ix.normalize(), "saham_beredar": s.values.astype("float64")})
            return d.drop_duplicates(["kode", "tanggal"], keep="last")
        except Exception as e:
            if "Too Many" in str(e) or "Rate" in str(e):
                time.sleep(60)
            else:
                time.sleep(5 * (coba + 1))
    return None


kode = kode_idx()[:10] if TES else kode_idx()
t0 = time.time()
hasil, gagal = [], []
with ThreadPoolExecutor(3) as ex:
    for k, d in zip(kode, ex.map(ambil, kode)):
        (hasil if d is not None else gagal).append(d if d is not None else k)
        if (len(hasil) + len(gagal)) % 100 == 0:
            print(f"   {len(hasil) + len(gagal)}/{len(kode)} ({time.time() - t0:.0f} dtk)", flush=True)
if gagal and not TES:            # putaran kedua untuk yang gagal
    time.sleep(60)
    kedua = [ambil(k) for k in gagal]
    hasil += [d for d in kedua if d is not None]
baru = pd.concat(hasil, ignore_index=True) if hasil else pd.DataFrame(columns=["kode", "tanggal", "saham_beredar"])
baru["waktu_ambil"] = SEKARANG
print(f"✅ saham beredar: {baru['kode'].nunique()} kode, {len(baru):,} titik, {baru['tanggal'].min()} s/d {baru['tanggal'].max()} "
      f"({time.time() - t0:.0f} dtk)")
if TES:
    print(baru.groupby("kode")["tanggal"].agg(["min", "max", "size"]).to_string())
    sys.exit(0)
if baru["kode"].nunique() < 500:
    print("❌ terlalu sedikit kode -> berhenti (jangan timpa file lama)")
    sys.exit(1)
lama = None
token = os.environ.get("HF_TOKEN") or (Path("kunci_hf.txt").read_text().strip() if Path("kunci_hf.txt").exists() else None)
try:
    from huggingface_hub import hf_hub_download, HfApi
    if HfApi(token=token).file_exists("fadli-sparks/quant-data", JALUR_HF, repo_type="dataset"):
        lama = pd.read_parquet(hf_hub_download("fadli-sparks/quant-data", JALUR_HF, repo_type="dataset", token=token))
except Exception as e:
    print(f"❌ gagal membaca file lama ({type(e).__name__}) -> berhenti supaya riwayat tidak tertimpa")
    sys.exit(1)
gabung = pd.concat([lama, baru], ignore_index=True) if lama is not None else baru
gabung = gabung.sort_values("waktu_ambil").drop_duplicates(["kode", "tanggal"], keep="last").sort_values(["kode", "tanggal"])
gabung["tanggal"] = pd.to_datetime(gabung["tanggal"]).astype("datetime64[ns]")
gabung["waktu_ambil"] = pd.to_datetime(gabung["waktu_ambil"]).astype("datetime64[ns]")
gabung["kode"] = gabung["kode"].astype("string")
FILE.parent.mkdir(parents=True, exist_ok=True)
gabung.to_parquet(FILE, index=False)
print(f"💾 {FILE}: {len(gabung):,} baris ({gabung['kode'].nunique()} kode)")
