"""
PENGUMUMAN LABA (earnings) semua saham IDX dari Yahoo: tanggal & JAM pengumuman, perkiraan EPS analis, EPS aktual,
kejutan (%). Histori ~2013/2014 s/d sekarang (+ jadwal pengumuman berikutnya). Bahan riset 'post-earnings announcement drift'.

Hasil:
  data/raw/laba_idx/semua.parquet          kode, waktu_utc, waktu_wib, eps_perkiraan, eps_aktual, kejutan_pct (DITIMPA; baris lama
                                           dari foto sebelumnya DIPERTAHANKAN kalau Yahoo berhenti menampilkannya)
  data/raw/laba_idx/foto/<tanggal>.parquet  salinan foto minggu itu (perkiraan analis bisa direvisi -> point-in-time)
JEBAKAN: sebagian emiten lapor dalam USD (mis. ADRO EPS 0,01) & sebagian perkiraan beda skala (kejutan ratusan %) ->
  di riset pakai peringkat / batasi kejutan. Waktu asli Yahoo ber-zona New York -> disimpan UTC & WIB tanpa zona.
Cara pakai: python kumpul_laba_idx.py | --tes (5 kode, tanpa simpan)
"""
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

from daftar_saham import kode_idx

logging.getLogger("yfinance").setLevel(logging.CRITICAL)
HARI_INI = datetime.now(timezone.utc).date().isoformat()
TES = "--tes" in sys.argv
PEKERJA = 3
REPO = "fadli-sparks/quant-data"


def ambil_satu(kode):
    for percobaan in range(5):
        try:
            e = yf.Ticker(kode).get_earnings_dates(limit=60)
            if e is None or e.empty:
                return pd.DataFrame()
            w = pd.DatetimeIndex(e.index)
            d = pd.DataFrame({"kode": kode.removesuffix(".JK"),
                              "waktu_utc": w.tz_convert("UTC").tz_localize(None),
                              "waktu_wib": w.tz_convert("Asia/Jakarta").tz_localize(None),
                              "eps_perkiraan": pd.to_numeric(e.get("EPS Estimate"), errors="coerce").values,
                              "eps_aktual": pd.to_numeric(e.get("Reported EPS"), errors="coerce").values,
                              "kejutan_pct": pd.to_numeric(e.get("Surprise(%)"), errors="coerce").values})
            return d
        except Exception as ex:
            kena_batas = "RateLimit" in type(ex).__name__ or "Too Many Requests" in str(ex)
            if "No earnings dates found" in str(ex) or "possibly delisted" in str(ex):
                return pd.DataFrame()
            if percobaan == 4:
                print(f"   ⚠️  {kode}: {type(ex).__name__}: {str(ex)[:80]}")
                return None
            time.sleep(60 if kena_batas else 3 * (percobaan + 1))


kode = kode_idx()
if TES:
    kode = ["BBRI.JK", "TLKM.JK", "ADRO.JK", "MAPI.JK", "SIDO.JK"]
print(f"📋 {len(kode)} saham IDX, {PEKERJA} paralel...")
mulai, bag, gagal = time.time(), [], []
with ThreadPoolExecutor(max_workers=PEKERJA) as pool:
    tugas = {pool.submit(ambil_satu, k): k for k in kode}
    for i, f in enumerate(as_completed(tugas), 1):
        h = f.result()
        if h is None:
            gagal.append(tugas[f])
        elif len(h):
            bag.append(h)
        if i % 200 == 0:
            print(f"   {i}/{len(kode)} ({time.time() - mulai:.0f} dtk)")
if gagal and not TES:
    print(f"🔁 {len(gagal)} gagal, coba ulang pelan-pelan...")
    time.sleep(60)
    for k in gagal:
        h = ambil_satu(k)
        if h is not None and len(h):
            bag.append(h)
        time.sleep(1)
d = pd.concat(bag, ignore_index=True)
d["kode"] = d["kode"].astype("string")
for k in ["waktu_utc", "waktu_wib"]:
    d[k] = pd.to_datetime(d[k]).astype("datetime64[ns]")
lalu = d[d["eps_aktual"].notna()]
print(f"✅ {len(d):,} baris dari {d['kode'].nunique()} saham ({time.time() - mulai:.0f} dtk) | sudah diumumkan {len(lalu):,} "
      f"({lalu['waktu_wib'].min():%Y-%m} s/d {lalu['waktu_wib'].max():%Y-%m}) | jadwal ke depan {d['eps_aktual'].isna().sum():,}")
print("   pengumuman per tahun: " + "  ".join(f"{t}:{n}" for t, n in lalu.groupby(lalu["waktu_wib"].dt.year).size().items()))
if TES:
    print("🧪 mode tes: tidak disimpan")
    sys.exit()
if d["kode"].nunique() < 80:      # Yahoo hanya punya data laba utk saham yg diliput analis: 114 dari 945 (21 Nov 2026)
    print("❌ terlalu sedikit saham -> berhenti")
    sys.exit(1)
from huggingface_hub import HfApi, hf_hub_download
token = os.environ.get("HF_TOKEN") or Path("kunci_hf.txt").read_text().strip()
try:
    lama = pd.read_parquet(hf_hub_download(REPO, "raw/laba_idx/semua.parquet", repo_type="dataset", token=token))
    d = pd.concat([lama, d], ignore_index=True)
except Exception as ex:
    if "404" not in str(ex) and "EntryNotFound" not in type(ex).__name__:
        raise
d = d.drop_duplicates(["kode", "waktu_utc"], keep="last").sort_values(["kode", "waktu_utc"]).reset_index(drop=True)
folder = Path("data/raw/laba_idx")
(folder / "foto").mkdir(parents=True, exist_ok=True)
d.to_parquet(folder / "semua.parquet", index=False)
d.to_parquet(folder / "foto" / f"{HARI_INI}.parquet", index=False)
HfApi(token=token).upload_folder(folder_path=str(folder), path_in_repo="raw/laba_idx", repo_id=REPO, repo_type="dataset",
                                 commit_message=f"Laba IDX {HARI_INI}")
print(f"☁️  raw/laba_idx ({len(d):,} baris) di gudang")
