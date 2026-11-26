"""
FOTO MINGGUAN PERKIRAAN ANALIS per saham IDX (Yahoo Finance; data HANYA KE DEPAN: Yahoo hanya menyimpan keadaan saat ini)
-> raw/estimasi_idx/<tanggal UTC>.parquet  format panjang: kode, tabel, periode, kolom, nilai, waktu_ambil
Tabel (yfinance): earnings_estimate (konsensus EPS 0q/+1q/0y/+1y: avg/low/high/jumlah analis/yearAgoEps/growth),
  revenue_estimate, eps_trend (konsensus sekarang vs 7/30/60/90 hari lalu = REVISI perkiraan), eps_revisions (jumlah analis menaikkan/
  menurunkan 7 & 30 hari), growth_estimates, recommendations (jumlah strongBuy/buy/hold/sell/strongSell 0m/-1m/-2m/-3m),
  analyst_price_targets (current/low/high/mean/median).
Kegunaan: revisi perkiraan laba (Chan-Jegadeesh-Lakonishok 1996; Hawkins-Chamberlin-Daniel 1984) = sinyal momentum laba; foto berurutan
  = point-in-time. upgrades_downgrades untuk IDX KOSONG di Yahoo (dicek 27 Nov 2026).
Semesta: saham yang punya perkiraan analis di foto screener terbaru (raw/harian/daftar_idx: epsCurrentYear / averageAnalystRating terisi,
  ~140) + semua kode di foto estimasi sebelumnya; gagal membaca -> semua kode_idx() (lebih lama).
JEBAKAN: Yahoo mengisi 0 untuk nilai kosong (mis. +1q high 0 dgn numberOfAnalysts 0) -> saat riset buang baris tabel/periode dgn
  numberOfAnalysts 0. EPS sebagian emiten dalam USD (lihat financialCurrency di foto fundamental).
Cara pakai: python kumpul_estimasi_idx.py  |  --tes (10 saham, tanpa simpan)
"""
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

logging.getLogger("yfinance").setLevel(logging.CRITICAL)
REPO = "fadli-sparks/quant-data"
TES = "--tes" in sys.argv
SEKARANG = datetime.now(timezone.utc)
WAKTU = pd.Timestamp(SEKARANG).tz_localize(None).floor("s")
TABEL = ["earnings_estimate", "revenue_estimate", "eps_trend", "eps_revisions", "growth_estimates", "recommendations", "analyst_price_targets"]


def semesta():
    if TES:
        return ["BBCA", "BBRI", "TLKM", "ADRO", "ANTM", "MAPI", "ASII", "UNVR", "ICBP", "PTBA"]
    kode = set()
    try:
        from huggingface_hub import HfApi, hf_hub_download
        token = os.environ.get("HF_TOKEN") or Path("kunci_hf.txt").read_text().strip()
        api = HfApi(token=token)
        f = sorted(x for x in api.list_repo_files(REPO, repo_type="dataset") if x.startswith(("raw/harian/daftar_idx/", "raw/estimasi_idx/")))
        dafs = [x for x in f if x.startswith("raw/harian/daftar_idx/") and x.endswith(".parquet")]
        if dafs:
            d = pd.read_parquet(hf_hub_download(REPO, dafs[-1], repo_type="dataset", token=token))
            ada = d[[c for c in ("epsCurrentYear", "averageAnalystRating", "epsForward") if c in d.columns]].notna().any(axis=1)
            kode |= set(d.loc[ada, "symbol" if "symbol" in d.columns else "kode"].astype(str).str.replace(".JK", "", regex=False))
            print(f"   screener {dafs[-1].split('/')[-1]}: {len(kode)} saham berperkiraan analis")
        est = [x for x in f if x.startswith("raw/estimasi_idx/") and x.endswith(".parquet")]
        if est:
            kode |= set(pd.read_parquet(hf_hub_download(REPO, est[-1], repo_type="dataset", token=token))["kode"].astype(str))
    except Exception as e:
        print(f"   ⚠️ gagal membaca daftar dari gudang ({type(e).__name__}) -> semua kode_idx()")
    if len(kode) < 50:
        from daftar_saham import kode_idx
        kode = set(kode_idx())
    return sorted(kode)


def ke_baris(kode, nama, x):
    out = []
    if x is None:
        return out
    if isinstance(x, dict):
        x = pd.DataFrame([x], index=["-"])
    if not isinstance(x, pd.DataFrame) or x.empty:
        return out
    for per, row in x.iterrows():
        for kol, v in row.items():
            try:
                v = float(v)
            except (TypeError, ValueError):
                continue
            if np.isfinite(v):
                out.append({"kode": kode, "tabel": nama, "periode": str(per), "kolom": str(kol), "nilai": v})
    return out


def ambil(kode):
    for coba in range(3):
        try:
            t = yf.Ticker(kode + ".JK")
            baris = []
            for nama in TABEL:
                baris += ke_baris(kode, nama, getattr(t, nama))
            return baris
        except Exception as e:
            if "Too Many" in str(e) or "Rate" in type(e).__name__:
                time.sleep(60)
            else:
                time.sleep(5 * (coba + 1))
    return None


kode = semesta()
print(f"📋 {len(kode)} saham")
baris, gagal, t0 = [], [], time.time()
with ThreadPoolExecutor(max_workers=3) as ex:
    fut = {ex.submit(ambil, k): k for k in kode}
    for f in as_completed(fut):
        b = f.result()
        if b is None:
            gagal.append(fut[f])
        else:
            baris += b
d = pd.DataFrame(baris)
if d.empty:
    print("❌ tidak ada data perkiraan")
    sys.exit(1)
for c in ("kode", "tabel", "periode", "kolom"):
    d[c] = d[c].astype("string")
d["waktu_ambil"] = WAKTU
berisi = d.groupby("kode")["tabel"].nunique()
print(f"✅ {d['kode'].nunique()} saham berisi ({len(d):,} angka, {time.time() - t0:.0f} dtk); gagal {len(gagal)}; "
      + " | ".join(f"{k} {v}" for k, v in d.groupby('tabel')['kode'].nunique().items()))
rv = d[(d["tabel"] == "eps_revisions") & (d["periode"] == "0y")]
if len(rv):
    p = rv.pivot_table(index="kode", columns="kolom", values="nilai")
    print("   contoh revisi EPS tahun ini (30 hari): naik " + str(int(p.get("upLast30days", pd.Series(dtype=float)).sum()))
          + " / turun " + str(int(p.get("downLast30days", pd.Series(dtype=float)).sum())) + " analis")
if TES:
    print(d.head(12).to_string())
    print("🧪 mode tes: tidak disimpan")
    sys.exit()
if d["kode"].nunique() < 30:
    print("❌ terlalu sedikit saham berisi (< 30) -> curigai Yahoo")
    sys.exit(1)
f = Path(f"data/raw/estimasi_idx/{SEKARANG.date().isoformat()}.parquet")
f.parent.mkdir(parents=True, exist_ok=True)
d.to_parquet(f, index=False)
print(f"💾 {f}")
