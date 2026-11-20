"""
Foto MINGGUAN data fundamental semua saham IDX dari Yahoo Finance (data "hanya ke depan").

Kenapa: Yahoo hanya menyimpan ~6 kuartal & 4-5 tahun laporan terakhir. Histori yang lebih panjang
harus dibangun dengan memotret rutin. Bonus: dari foto berurutan kita tahu KAPAN sebuah laporan
pertama kali muncul (penting supaya riset tidak memakai laporan sebelum benar-benar terbit),
dan kalau angka lama direvisi, versi lama tetap tersimpan.

Isi (2 file per foto, tanggal UTC server):
  data/raw/fundamental_idx/info/<tanggal>.parquet     1 baris per saham: kapitalisasi pasar, saham beredar,
                                                      PER, PBV, ROE, utang, dividen, target harga & rekomendasi analis,
                                                      kepemilikan orang dalam/institusi, sektor, dll.
  data/raw/fundamental_idx/laporan/<tanggal>.parquet  format panjang: kode, laporan, periode, pos, nilai
                                                      (laba rugi, neraca, arus kas; kuartalan & tahunan)

Cara pakai:
  python kumpul_fundamental_idx.py          -> semua saham IDX (~950), simpan
  python kumpul_fundamental_idx.py --tes    -> 20 saham, tanpa simpan, ukur waktu
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

logging.getLogger("yfinance").setLevel(logging.CRITICAL)
REPO = "fadli-sparks/quant-data"
HARI_INI = datetime.now(timezone.utc).date()
TES = "--tes" in sys.argv
PEKERJA = 3                      # unduhan paralel (4 sempat kena rate limit Yahoo di saham ke-700)
MIN_SAHAM_OK = 700               # kurang dari ini = ada masalah -> keluar dengan error (email alarm)

KOLOM_INFO_ANGKA = [
    "marketCap", "enterpriseValue", "sharesOutstanding", "floatShares", "impliedSharesOutstanding",
    "currentPrice", "previousClose", "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "fiftyDayAverage", "twoHundredDayAverage",
    "averageVolume", "averageVolume10days", "beta",
    "trailingPE", "forwardPE", "priceToBook", "priceToSalesTrailing12Months", "enterpriseToRevenue", "enterpriseToEbitda",
    "bookValue", "trailingEps", "forwardEps", "totalRevenue", "revenuePerShare", "grossProfits", "ebitda",
    "netIncomeToCommon", "totalCash", "totalCashPerShare", "totalDebt", "debtToEquity", "currentRatio", "quickRatio",
    "returnOnAssets", "returnOnEquity", "profitMargins", "grossMargins", "operatingMargins", "ebitdaMargins",
    "revenueGrowth", "earningsGrowth", "earningsQuarterlyGrowth", "operatingCashflow", "freeCashflow",
    "dividendRate", "dividendYield", "payoutRatio", "trailingAnnualDividendRate", "trailingAnnualDividendYield",
    "fiveYearAvgDividendYield",
    "targetHighPrice", "targetLowPrice", "targetMeanPrice", "targetMedianPrice", "recommendationMean",
    "numberOfAnalystOpinions", "heldPercentInsiders", "heldPercentInstitutions", "fullTimeEmployees",
    "auditRisk", "boardRisk", "compensationRisk", "shareHolderRightsRisk", "overallRisk",
]
KOLOM_INFO_TEKS = ["recommendationKey", "sector", "industry", "currency", "financialCurrency", "quoteType",
                   "exchange", "longName"]
KOLOM_INFO_WAKTU = ["mostRecentQuarter", "lastFiscalYearEnd", "nextFiscalYearEnd", "exDividendDate",
                    "lastDividendDate", "firstTradeDateMilliseconds"]
LAPORAN = {"laba_rugi_kuartal": "quarterly_income_stmt", "neraca_kuartal": "quarterly_balance_sheet",
           "arus_kas_kuartal": "quarterly_cashflow", "laba_rugi_tahunan": "income_stmt",
           "neraca_tahunan": "balance_sheet", "arus_kas_tahunan": "cashflow"}


def daftar_kode():
    """Daftar saham IDX = daftar awal + kode baru dari kumpul_daftar_idx.py (lihat daftar_saham.py)."""
    from daftar_saham import kode_idx
    return kode_idx()


def ke_angka(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def ambil_satu(kode):
    """Hasil: (baris info dict atau None, DataFrame laporan atau None).
    Kena rate limit Yahoo -> tunggu 60 detik lalu coba lagi (maks 5x)."""
    for percobaan in range(5):
        try:
            t = yf.Ticker(kode)
            info = t.info or {}
            baris = {"kode": kode}
            baris.update({k: ke_angka(info.get(k)) for k in KOLOM_INFO_ANGKA})
            baris.update({k: (str(info[k]) if info.get(k) is not None else None) for k in KOLOM_INFO_TEKS})
            for k in KOLOM_INFO_WAKTU:
                v = ke_angka(info.get(k))
                if k == "firstTradeDateMilliseconds":
                    v = v / 1000
                baris[k] = pd.to_datetime(v, unit="s") if pd.notna(v) else pd.NaT
            bagian = []
            for nama, atribut in LAPORAN.items():
                df = getattr(t, atribut)
                if df is None or df.empty:
                    continue
                panjang = df.stack(future_stack=True).dropna().reset_index()
                panjang.columns = ["pos", "periode", "nilai"]
                panjang.insert(0, "laporan", nama)
                bagian.append(panjang)
            laporan = None
            if bagian:
                laporan = pd.concat(bagian, ignore_index=True)
                laporan.insert(0, "kode", kode)
            punya_isi = len(info) > 5 or laporan is not None
            return (baris if punya_isi else None), laporan
        except Exception as e:                       # yfinance kadang error acak: coba lagi
            kena_batas = "RateLimit" in type(e).__name__ or "Too Many Requests" in str(e)
            if percobaan == 4:
                print(f"   ⚠️  {kode}: {type(e).__name__}: {str(e)[:80]}")
            time.sleep(60 if kena_batas else 3 * (percobaan + 1))
    return None, None


kode_semua = daftar_kode()
if TES:
    kode_semua = kode_semua[:20]
print(f"📋 {len(kode_semua)} kode saham IDX, {PEKERJA} unduhan paralel...")

mulai = time.time()
info_list, laporan_list = [], []
with ThreadPoolExecutor(max_workers=PEKERJA) as pool:
    tugas = {pool.submit(ambil_satu, k): k for k in kode_semua}
    for i, f in enumerate(as_completed(tugas), 1):
        baris, laporan = f.result()
        if baris:
            info_list.append(baris)
        if laporan is not None:
            laporan_list.append(laporan)
        if i % 100 == 0:
            print(f"   {i}/{len(kode_semua)} ({time.time() - mulai:.0f} detik)")

# Putaran kedua: saham yang kosong (bisa jadi korban rate limit diam-diam) dicoba ulang satu per satu
sudah = {b["kode"] for b in info_list} & {l["kode"].iloc[0] for l in laporan_list}
ulang = [k for k in kode_semua if k not in sudah]
if ulang and not TES:
    print(f"🔁 Putaran kedua: {len(ulang)} saham tanpa info/laporan, dicoba ulang pelan-pelan...")
    time.sleep(60)
    info_list = [b for b in info_list if b["kode"] not in ulang]
    laporan_list = [l for l in laporan_list if l["kode"].iloc[0] not in ulang]
    for k in ulang:
        baris, laporan = ambil_satu(k)
        if baris:
            info_list.append(baris)
        if laporan is not None:
            laporan_list.append(laporan)
        time.sleep(1)

info = pd.DataFrame(info_list)
for k in KOLOM_INFO_ANGKA:
    info[k] = info[k].astype("float64")
for k in KOLOM_INFO_TEKS + ["kode"]:
    info[k] = info[k].astype("string")
for k in KOLOM_INFO_WAKTU:
    info[k] = pd.to_datetime(info[k]).astype("datetime64[ns]")
info.insert(1, "tanggal_foto", pd.Timestamp(HARI_INI))
info["tanggal_foto"] = info["tanggal_foto"].astype("datetime64[ns]")

laporan = pd.concat(laporan_list, ignore_index=True)
laporan["periode"] = pd.to_datetime(laporan["periode"]).astype("datetime64[ns]")
laporan["nilai"] = pd.to_numeric(laporan["nilai"], errors="coerce").astype("float64")
for k in ["kode", "laporan", "pos"]:
    laporan[k] = laporan[k].astype("string")
laporan.insert(1, "tanggal_foto", pd.Timestamp(HARI_INI))
laporan["tanggal_foto"] = laporan["tanggal_foto"].astype("datetime64[ns]")

durasi = time.time() - mulai
print(f"\n✅ info: {len(info)} saham | laporan: {len(laporan):,} baris dari {laporan['kode'].nunique()} saham "
      f"| {durasi:.0f} detik ({durasi / len(kode_semua):.2f} detik/saham)")
print(f"   Saham dengan target harga analis: {info['targetMeanPrice'].notna().sum()} | "
      f"dengan PBV: {info['priceToBook'].notna().sum()} | kuartal terbaru: "
      f"{laporan[laporan['laporan'] == 'laba_rugi_kuartal']['periode'].max().date()}")

if TES:
    print(f"\n🧪 Perkiraan semua saham (~950): {durasi / len(kode_semua) * 950 / 60:.0f} menit")
    print(info[["kode", "marketCap", "priceToBook", "returnOnEquity", "targetMeanPrice", "mostRecentQuarter"]]
          .head(8).to_string(index=False))
    print(laporan.groupby("laporan").size().to_string())
    sys.exit()

if len(info) < MIN_SAHAM_OK:
    print(f"❌ Hanya {len(info)} saham berhasil (minimal {MIN_SAHAM_OK}): kemungkinan diblokir Yahoo")
    sys.exit(1)
for nama, df in [("info", info), ("laporan", laporan)]:
    folder = Path(f"data/raw/fundamental_idx/{nama}")
    folder.mkdir(parents=True, exist_ok=True)
    df.to_parquet(folder / f"{HARI_INI.isoformat()}.parquet", index=False)
print("💾 Tersimpan di data/raw/fundamental_idx/")
