import sys
from datetime import date
from pathlib import Path

import db_dtypes  # supaya file lama berformat dbdate tetap bisa dibaca
import pandas as pd

HARI_INI = pd.Timestamp(date.today())
HARIAN = Path("data/raw/harian")
masalah = []


def ke_tanggal(seri):
    t = pd.to_datetime(seri).max()
    return t.tz_localize(None) if t.tzinfo else t


def cek(nama, kolom_tanggal, maks_basi, min_baris, kolom_unik=None, min_unik=None):
    """Periksa file hari ini untuk satu sumber data."""
    file = HARIAN / nama / f"{date.today().isoformat()}.parquet"
    if not file.exists():
        masalah.append(f"{nama}: file hari ini TIDAK ADA")
        print(f"❌ {nama:18} file hari ini tidak ada")
        return

    df = pd.read_parquet(file)
    basi = (HARI_INI - ke_tanggal(df[kolom_tanggal]).normalize()).days
    catatan = []

    if len(df) < min_baris:
        catatan.append(f"cuma {len(df)} baris (min {min_baris})")
    if basi > maks_basi:
        catatan.append(f"data terbaru {basi} hari lalu (maks {maks_basi})")
    if kolom_unik:
        unik = len(df[kolom_unik].drop_duplicates())
        if unik < min_unik:
            catatan.append(f"cuma {unik} {'/'.join(kolom_unik)} (min {min_unik})")

    if catatan:
        masalah.append(f"{nama}: " + "; ".join(catatan))
        print(f"❌ {nama:18} " + "; ".join(catatan))
    else:
        print(f"✅ {nama:18} {len(df):5} baris, data terbaru {basi} hari lalu")


#    nama sumber        kolom tanggal  maks basi  min baris  kolom unik           min unik
cek("harga",            "tanggal",     4,         3000,      ["kode"],            850)
cek("saham_as",         "tanggal",     4,         40000,     ["kode"],            8000),
cek("cuaca",            "tanggal",     2,         150,       ["kota"],            15)
cek("bitcoin",          "tanggal",     2,         10)
cek("ethereum",         "tanggal",     3,         7)
cek("berita_gdelt",     "tanggal",     3,         30,        ["negara"],          6)
cek("google_trends_id", "week",        21,        10)
cek("wikipedia",        "tanggal",     3,         400,       ["wiki", "artikel"], 18)
cek("crypto_harian",    "waktu",       2,         3000,      ["kode"],            300)
cek("crypto_jam",       "waktu",       1,         15000,     ["kode"],            300)
cek("gempa",            "time",        2,         100)
cek("cot_legacy",        "report_date_as_yyyy_mm_dd", 14, 500)
cek("cot_disaggregated", "report_date_as_yyyy_mm_dd", 14, 500)
cek("cot_keuangan",      "report_date_as_yyyy_mm_dd", 14, 100)
cek("opsi",             "waktu_ambil", 2,         20000,     ["kode"],            40)
cek("finra_short",      "tanggal",     5,         50000,     ["kode"],            8000)
cek("lme",              "tanggal",     5,         60,        ["logam"],           6)
cek("kurs_ecb",         "tanggal",     5,         200,       ["mata_uang"],       25)
cek("polymarket",       "waktu_ambil", 2,         1000,      ["id"],              1000)
cek("daftar_idx",       "waktu_ambil", 2,         600,       ["kode"],            600)
cek("wikipedia_idx",    "tanggal",     3,         3000,      ["kode"],            150)
cek("intraday_idx",     "waktu",       5,         50000,     ["kode"],            300)
cek("iklim",            "tanggal",     21,        500,       ["seri"],            4)
cek("udara",            "waktu",       3,         1000,      ["kota"],            10)
cek("pangan",           "tanggal",     5,         10000,     ["wilayah"],         30)

# Makro: semua 18 seri harus ada, dan suku bunga harian The Fed harus segar
file_makro = list(Path("data/raw/makro").glob("*.parquet"))
dff = pd.read_parquet("data/raw/makro/DFF.parquet") if Path("data/raw/makro/DFF.parquet").exists() else None
basi_dff = (HARI_INI - ke_tanggal(dff.index).normalize()).days if dff is not None else 999
if len(file_makro) < 170 or basi_dff > 10:
    masalah.append(f"makro: {len(file_makro)}/175 seri, DFF basi {basi_dff} hari")
    print(f"❌ {'makro':18} {len(file_makro)}/175 seri, DFF terbaru {basi_dff} hari lalu")
else:
    print(f"✅ {'makro':18} {len(file_makro)} seri, DFF terbaru {basi_dff} hari lalu")

# ===== Kesimpulan =====
if masalah:
    print(f"\n🚨 {len(masalah)} MASALAH DITEMUKAN:")
    for m in masalah:
        print(f"   - {m}")
    sys.exit(1)   # tandai gagal → GitHub kirim email
print("\n🎉 Semua sumber data sehat.")