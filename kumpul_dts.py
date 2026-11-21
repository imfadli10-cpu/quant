"""
DAILY TREASURY STATEMENT (DTS) pemerintah AS: arus kas HARIAN Kementerian Keuangan AS sejak 2005-10 (API resmi fiscaldata,
tanpa kunci). Sumber: https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/<tabel>

Kenapa:
  - SALDO KAS pemerintah AS (TGA, operating_cash_balance): naik = likuiditas dolar DISEDOT dari sistem keuangan, turun = disuntik
    (komponen 'likuiditas bersih' = neraca The Fed - TGA - reverse repo) -> aset berisiko global & pasar berkembang.
  - PENERIMAAN PAJAK HARIAN (federal_tax_deposits; withheld income & employment taxes = pajak gaji yang dipotong): indikator
    ekonomi AS nyaris real-time, jauh sebelum data tenaga kerja/PDB bulanan.
  - Transaksi utang, plafon utang (debt ceiling), pengembalian pajak, setoran/penarikan per kategori (gaji pegawai, Medicare...).
Isi: data/raw/dts/<tabel>.parquet (SEMUA baris sejak 2005, DITIMPA tiap hari). Angka -> float, tanggal -> datetime, sisanya teks
  (tipe ditentukan dari ISI kolom, pelajaran lelang_as). Nilai '*' / 'null' -> kosong.
Cara pakai: python kumpul_dts.py | --tes (2 tabel kecil, tanpa simpan)
"""
import sys
import time
from pathlib import Path

import pandas as pd
import requests

B = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/"
UA = {"User-Agent": "quant-data-collector/1.0 (personal research project)"}
TABEL = ["operating_cash_balance", "deposits_withdrawals_operating_cash", "public_debt_transactions",
         "adjustment_public_debt_transactions_cash_basis", "debt_subject_to_limit", "federal_tax_deposits",
         "short_term_cash_investments", "income_tax_refunds_issued", "inter_agency_tax_transfers"]
TES = "--tes" in sys.argv
if TES:
    TABEL = ["operating_cash_balance", "federal_tax_deposits"]


def halaman(tabel, nomor):
    for percobaan in range(5):
        try:
            r = requests.get(B + tabel, params={"page[size]": 10000, "page[number]": nomor, "sort": "record_date"},
                             headers=UA, timeout=(15, 180))
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"   🔌 {tabel} halaman {nomor}: {type(e).__name__}, coba lagi...")
            time.sleep(15 * (percobaan + 1))
    raise RuntimeError(f"fiscaldata {tabel} gagal 5x")


def rapikan(df):
    df = df.replace({"null": None, "": None, "*": None})
    for k in df.columns:
        isi = df[k].dropna().astype(str)
        if len(isi) and isi.str.fullmatch(r"\d{4}-\d{2}-\d{2}").all():
            df[k] = pd.to_datetime(df[k], format="%Y-%m-%d", errors="coerce").astype("datetime64[ns]")
            continue
        angka = pd.to_numeric(df[k], errors="coerce")
        if df[k].notna().sum() and angka.notna().sum() >= 0.9 * df[k].notna().sum():
            df[k] = angka.astype("float64")
        else:
            df[k] = df[k].astype("string")
    return df.sort_values("record_date").reset_index(drop=True)


folder = Path("data/raw/dts")
gagal = []
for t in TABEL:
    t0 = time.time()
    try:
        pertama = halaman(t, 1)
        data, total = pertama["data"], pertama["meta"]["total-pages"]
        for n in range(2, total + 1):
            data += halaman(t, n)["data"]
            time.sleep(0.5)
        df = rapikan(pd.DataFrame(data))
    except Exception as e:
        print(f"⚠️  {t}: {type(e).__name__}: {str(e)[:120]}")
        gagal.append(t)
        continue
    print(f"✅ {t:48} {len(df):8,} baris | {df['record_date'].min():%Y-%m-%d} s/d {df['record_date'].max():%Y-%m-%d} "
          f"({time.time() - t0:.0f} dtk)")
    if t == "operating_cash_balance":
        tga = df[df["account_type"].astype(str).str.contains("Closing Balance|Treasury General Account \\(TGA\\) Closing",
                                                             case=False, regex=True)]
        if len(tga):
            terakhir = tga.iloc[-1]
            kol = "open_today_bal" if pd.isna(terakhir.get("close_today_bal")) else "close_today_bal"
            print(f"   saldo TGA terakhir ({terakhir['record_date']:%Y-%m-%d}): {terakhir[kol]:,.0f} juta USD")
    if not TES:
        folder.mkdir(parents=True, exist_ok=True)
        df.to_parquet(folder / f"{t}.parquet", index=False)
if TES:
    print("🧪 mode tes: tidak disimpan")
if gagal and not TES:
    print(f"❌ gagal: {gagal}")
    sys.exit(1)
