import os
from collections import defaultdict
from datetime import date
from pathlib import Path

from huggingface_hub import HfApi

REPO = "fadli-sparks/quant-data"
token = os.environ.get("HF_TOKEN") or Path("kunci_hf.txt").read_text().strip()
api = HfApi(token=token)
PAGAR = "`" * 3   # tanda blok kode di README

# folder: (isi, sumber asli, jadwal)
INFO = {
    "raw/harga_idx":              ("Histori harga ~920 saham IDX, 1 file per saham", "Yahoo Finance", "Sekali (awal)"),
    "raw/harga":                  ("Histori ~50 aset global: indeks saham 23 negara, futures logam/energi/pertanian/ternak, VIX, DXY, kurs, BTC", "Yahoo Finance", "Sekali (awal)"),
    "raw/histori/saham_as":       ("Histori ~12.700 saham & ETF AS, 129 bagian + daftar.parquet", "Yahoo Finance", "Sekali (awal)"),
    "raw/histori/crypto_harian":  ("Histori harga harian 404 koin crypto/USD sejak listing", "Coinbase", "Sekali (awal)"),
    "raw/histori/bitcoin":        ("Aktivitas blockchain Bitcoin per hari sejak 2009, 1 file per tahun", "BigQuery", "Sekali (awal)"),
    "raw/histori/ethereum":       ("Aktivitas blockchain Ethereum per hari sejak 2015, 1 file per tahun", "BigQuery", "Sekali (awal)"),
    "raw/histori/berita_gdelt":   ("Jumlah, nada & porsi konflik berita per negara sejak 2015", "BigQuery GDELT", "Sekali (awal)"),
    "raw/histori/wikipedia":      ("Jumlah pembaca 20 artikel Wikipedia sejak Juli 2015", "Wikimedia API", "Sekali (awal)"),

    "raw/makro":                  ("75 seri makro: suku bunga, inflasi, likuiditas Fed, tenaga kerja, kurs 15 mata uang, yield obligasi 5 negara, energi, 13 komoditas (nikel, timah, sawit, batu bara, dll.), Indonesia", "FRED", "Harian"),

    "raw/cuaca":                  ("Histori cuaca harian 15 kota sejak 1990", "Open-Meteo", "Sekali (awal)"),
    "raw/harian/harga":           ("Harga 7 hari terakhir ~920 saham IDX + aset global", "Yahoo Finance", "Harian"),
    "raw/harian/saham_as":        ("Harga 7 hari terakhir ~11.000 saham & ETF AS", "Yahoo Finance", "Harian"),
    "raw/harian/daftar_saham_as": ("Daftar semua kode saham AS hari itu (lacak delisting)", "NASDAQ Trader", "Harian"),
    "raw/harian/crypto_harian":   ("Harga harian 14 hari terakhir ~400 koin", "Coinbase", "Harian"),
    "raw/harian/crypto_jam":      ("Harga PER JAM 3 hari terakhir ~400 koin", "Coinbase", "Harian"),
    "raw/harian/cuaca":           ("Cuaca 14 hari terakhir 15 kota", "Open-Meteo", "Harian"),
    "raw/harian/bitcoin":         ("Aktivitas blockchain Bitcoin, bulan ini & lalu", "BigQuery", "Harian"),
    "raw/harian/ethereum":        ("Aktivitas blockchain Ethereum, 14 hari terakhir", "BigQuery", "Harian"),
    "raw/harian/berita_gdelt":    ("Nada & konflik berita per negara, 14 hari terakhir", "BigQuery GDELT", "Harian"),
    "raw/harian/google_trends_id": ("Istilah pencarian terpopuler Indonesia, versi terbaru", "BigQuery Google Trends", "Harian"),
    "raw/harian/wikipedia":       ("Pembaca 20 artikel Wikipedia, 30 hari terakhir", "Wikimedia API", "Harian"),
    "raw/fundamental/sec":        ("~16 juta angka laporan keuangan ~20.000 perusahaan AS + tiker.parquet", "SEC EDGAR", "Bulanan (tgl 2)"),
    "raw/harian/gempa":           ("Gempa M2.5+ seluruh dunia, 14 hari terakhir", "USGS", "Harian"),
    "raw/histori/gempa":          ("Gempa M4.5+ seluruh dunia sejak 1990, 1 file per tahun", "USGS", "Sekali (awal)"),
    "raw/alam":                   ("Badai geomagnetik (Kp/Ap), bintik matahari, F10.7 harian sejak 1932", "GFZ Potsdam", "Harian (ditimpa)"),
        "raw/harian/cot_legacy":        ("Posisi futures spekulan vs hedger, 8 minggu terakhir", "CFTC", "Harian (laporan mingguan)"),
    "raw/harian/cot_disaggregated": ("Posisi futures komoditas, pelaku lebih rinci, 8 minggu terakhir", "CFTC", "Harian (laporan mingguan)"),
    "raw/harian/cot_keuangan":      ("Posisi futures keuangan (indeks, obligasi, mata uang), 8 minggu terakhir", "CFTC", "Harian (laporan mingguan)"),
    "raw/histori/cot":              ("Histori lengkap COT: legacy sejak 1986, lainnya sejak 2006", "CFTC", "Sekali (otomatis)"),
    "raw/riset":                    ("Faktor Fama-French harian (3 & 5 faktor, momentum), dalam desimal", "Kenneth French Data Library", "Harian (ditimpa)"),
    "raw/bps":                    ("Daftar semua variabel statistik nasional BPS", "BPS", "Bulanan"),
    "raw/bps/terbaru":            ("Semua variabel BPS nasional, 3 tahun terakhir (inflasi per kota, ekspor, dll.)", "BPS", "Bulanan (tgl 2)"),
    "raw/histori/bps":            ("Semua variabel BPS nasional, semua tahun, per 100 variabel", "BPS", "Sekali (bertahap)"),
    "raw/harian/opsi":            ("Foto harian rantai opsi 49 saham/ETF AS (6 jatuh tempo terdekat): harga, volume, open interest, volatilitas tersirat", "Yahoo Finance", "Harian (hanya ke depan)"),
    "raw/harian/finra_short":     ("Volume short harian ~12.000 saham AS (short, short dikecualikan, total), 10 hari terakhir", "FINRA Reg SHO", "Harian"),
    "raw/histori/finra_short":    ("Histori volume short harian semua saham AS sejak Agustus 2018, 1 file per tahun", "FINRA Reg SHO", "Sekali (awal)"),
    "bersih":                     ("DATA SIAP PAKAI: harga saham IDX & AS (histori + harian digabung, tanpa dobel)", "Gabungan", "Mingguan (Minggu)"),

    "ref":                        ("File referensi: daftar saham IDX, katalog makro & cuaca, laporan validasi", "Berbagai", "Sesekali"),
}

# Hitung jumlah file & ukuran per folder langsung dari gudang
jumlah, ukuran = defaultdict(int), defaultdict(int)
for item in api.list_repo_tree(REPO, repo_type="dataset", recursive=True):
    if hasattr(item, "size") and "/" in item.path:
        folder = item.path.rsplit("/", 1)[0]
        jumlah[folder] += 1
        ukuran[folder] += item.size or 0


def mb(byte):
    return f"{byte / 1e6:,.1f} MB" if byte >= 1e6 else f"{byte / 1e3:,.0f} KB"


baris_tabel = []
for folder in sorted(jumlah):
    isi, sumber, jadwal = INFO.get(folder, ("⚠️ belum ada keterangan", "-", "-"))
    baris_tabel.append(f"| `{folder}` | {isi} | {sumber} | {jadwal} | {jumlah[folder]:,} | {mb(ukuran[folder])} |")

total = sum(ukuran.values())
tabel = "\n".join(baris_tabel)

README = f"""---
pretty_name: Gudang Data Quant
viewer: false
---

# Gudang Data Quant

*Diperbarui otomatis: {date.today().isoformat()} | {sum(jumlah.values()):,} file | {mb(total)}*

## Isi gudang

| Folder | Isi | Sumber | Jadwal | File | Ukuran |
|---|---|---|---|---|---|
{tabel}

## Catatan penting saat memakai data

1. **Look-ahead bias (SEC):** pakai kolom `tanggal_lapor`, bukan `akhir`, untuk menentukan kapan angka laporan keuangan diketahui publik.
2. **Survivorship bias:** daftar saham IDX dan crypto hanya berisi yang masih aktif saat diambil. SEC (~20.000 perusahaan) dan `daftar_saham_as` harian termasuk yang sudah hilang.
3. **Data harian tumpang tindih:** setiap file harian berisi 7-30 hari terakhir. Saat menggabungkan, buang baris dobel (tanggal + kode yang sama).
4. **Waktu:** crypto dan file harian memakai UTC. Nama file harian = tanggal UTC saat diambil.
5. **Nilai khusus:** harga minyak WTI benar-benar negatif pada 20 April 2020, itu bukan error.
6. **GDELT:** `rata_nada` -10 (negatif) s/d +10 (positif); `rata_goldstein` -10 (konflik) s/d +10 (kerja sama).

## Cara membaca data

{PAGAR}python
import pandas as pd
df = pd.read_parquet("hf://datasets/{REPO}/raw/histori/crypto_harian/semua.parquet",
                     storage_options={{"token": "TOKEN_KAMU"}})
{PAGAR}
"""

api.upload_file(path_or_fileobj=README.encode("utf-8"), path_in_repo="README.md",
                repo_id=REPO, repo_type="dataset", commit_message="Perbarui katalog")
print(f"📖 Katalog diperbarui: {len(jumlah)} folder, {sum(jumlah.values()):,} file, {mb(total)}")