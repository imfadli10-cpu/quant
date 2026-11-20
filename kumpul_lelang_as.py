"""
HASIL LELANG SURAT UTANG PEMERINTAH AS (Treasury bills/notes/bonds/TIPS/FRN) sejak 1979, API resmi fiscaldata (tanpa kunci).

Kenapa: tiap lelang mencatat MINAT pembeli (bid_to_cover_ratio = total penawaran / jumlah dijual) dan SIAPA pembelinya
(indirect_bidder_accepted ~ investor asing & bank sentral lewat perantara; direct; primary_dealer = sisa yang "terpaksa"
diserap dealer). Lelang sepi peminat / dealer menyerap banyak = tekanan di pasar obligasi AS -> imbal hasil naik -> dana
cenderung keluar dari pasar berkembang (termasuk Indonesia).
Catatan: baris terbaru bisa berisi lelang yang SUDAH diumumkan tapi HASILNYA belum keluar (kolom hasil kosong) -> diambil
ulang tiap hari; foto harian menyimpan versi saat itu (tahu kapan hasil benar-benar tersedia).

Isi: data/raw/lelang_as/semua.parquet (semua lelang, ditimpa) + data/raw/harian/lelang_as/<tanggal UTC>.parquet (90 hari
  terakhir menurut tanggal lelang). Semua 114 kolom; angka dipaksa float, tanggal datetime, sisanya teks.
Cara pakai: python kumpul_lelang_as.py [--tes]
"""
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

URL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/auctions_query"
UA = {"User-Agent": "quant-data-collector/1.0 (personal research project)"}
HARI_INI = datetime.now(timezone.utc).date()


def halaman(nomor):
    for percobaan in range(4):
        try:
            r = requests.get(URL, params={"page[size]": 10000, "page[number]": nomor, "sort": "auction_date"}, headers=UA, timeout=120)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"   🔌 halaman {nomor}: {type(e).__name__}, coba lagi...")
            time.sleep(15 * (percobaan + 1))
    raise RuntimeError("fiscaldata gagal 4x")


pertama = halaman(1)
data, total = pertama["data"], pertama["meta"]["total-pages"]
for n in range(2, total + 1):
    data += halaman(n)["data"]
    time.sleep(1)
df = pd.DataFrame(data).replace({"null": None, "": None})
for k in df.columns:
    isi = df[k].dropna().astype(str)
    # Tanggal HANYA kalau isinya benar-benar YYYY-MM-DD (bukan berdasarkan nama kolom: 'ref_cpi_on_issue_date' &
    # 'index_ratio_on_issue_date' berisi ANGKA indeks inflasi TIPS; dulu ikut jadi kosong)
    if len(isi) and isi.str.fullmatch(r"\d{4}-\d{2}-\d{2}").all():
        df[k] = pd.to_datetime(df[k], format="%Y-%m-%d", errors="coerce").astype("datetime64[ns]")
        continue
    angka = pd.to_numeric(df[k], errors="coerce")
    if df[k].notna().sum() and angka.notna().sum() >= 0.9 * df[k].notna().sum():
        df[k] = angka.astype("float64")
    else:
        df[k] = df[k].astype("string")
df = df.sort_values(["auction_date", "security_type", "security_term"]).reset_index(drop=True)
sudah = df["bid_to_cover_ratio"].notna()
print(f"✅ lelang_as: {len(df):,} lelang, {df['auction_date'].min().date()} s/d {df['auction_date'].max().date()} | "
      f"hasil tersedia {sudah.sum():,} | terakhir berhasil: {df.loc[sudah, 'auction_date'].max().date()} | "
      f"bid-to-cover median 2025: {df.loc[(df['auction_date'].dt.year == 2025), 'bid_to_cover_ratio'].median():.2f}")
if "--tes" in sys.argv:
    print(df.loc[sudah, ["auction_date", "security_type", "security_term", "offering_amt", "bid_to_cover_ratio",
                         "high_yield", "indirect_bidder_accepted", "primary_dealer_accepted"]].tail(5).to_string(index=False))
    sys.exit()
folder = Path("data/raw/lelang_as")
folder.mkdir(parents=True, exist_ok=True)
df.to_parquet(folder / "semua.parquet", index=False)
harian = Path("data/raw/harian/lelang_as")
harian.mkdir(parents=True, exist_ok=True)
df[df["auction_date"] >= pd.Timestamp(HARI_INI - timedelta(days=90))].to_parquet(harian / f"{HARI_INI.isoformat()}.parquet", index=False)
print(f"💾 {folder}/semua.parquet + {harian}/{HARI_INI.isoformat()}.parquet")
