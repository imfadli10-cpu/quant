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
    "raw/harga":                  ("Histori ~50 aset global: indeks saham 23 negara, futures logam/energi/pertanian/ternak, sawit (SAWIT, sejak 2010), VIX, DXY, kurs, BTC", "Yahoo Finance", "Sekali (awal)"),
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
    "raw/harian/lme":             ("Harga resmi LME (tunai & 3 bulan) + stok gudang 6 logam: nikel, timah, tembaga, aluminium, seng, timbal; 40 hari terakhir", "Westmetall (data LME)", "Harian"),
    "raw/histori/lme":            ("Histori harga resmi LME + stok gudang 6 logam sejak 2008 (semua.parquet)", "Westmetall (data LME)", "Sekali (awal)"),
    "raw/harian/finra_short":     ("Volume short harian ~12.000 saham AS (short, short dikecualikan, total), 10 hari terakhir", "FINRA Reg SHO", "Harian"),
    "raw/histori/finra_short":    ("Histori volume short harian semua saham AS sejak Agustus 2018, 1 file per tahun", "FINRA Reg SHO", "Sekali (awal)"),
    "raw/histori/wiki_prices":    ("Arsip WIKI (beku 2018-03): 3.199 saham AS sejak 1962, harga ASLI + disesuaikan, rasio split, dividen; memuat 705 saham mati 2014-2017", "Nasdaq Data Link (WIKI)", "Sekali (beku)"),
    "raw/paper_trading":          ("PAPER TRADING strategi S2 (dekat puncak 52 minggu): pilihan tiap akhir bulan dicatat SEBELUM hari beli (tidak pernah diubah), semesta pembanding, kinerja berjalan", "Hitungan sendiri dari harga Yahoo", "Harian 05:41 WIB (Senin-Jumat)"),
    "raw/harian/lelang_sbn":      ("Hasil lelang SUN & SBSN (sukuk) dari berita beranda DJPPR: penawaran masuk & nominal dimenangkan (Rp triliun), yield rata-rata tertimbang, bid-to-cover per seri + total; halaman_*.parquet = HTML asli", "DJPPR Kemenkeu (djppr.kemenkeu.go.id)", "Harian (hanya ke depan; lelang tiap Selasa)"),
    "raw/saham_beredar":          ("Histori jumlah saham beredar semua saham IDX (Yahoo get_shares_full; umumnya sejak 2013-2016; BELUM disesuaikan split): kode, tanggal, saham_beredar, waktu_ambil; untuk kapitalisasi pasar historis & net issuance", "Yahoo Finance", "mingguan (Sabtu, gabung dgn file lama)"),
    "raw/harian/emitennews":      ("Berita emiten IDX dari sitemap EmitenNews: URL, judul (slug, kode saham di dalamnya), tanggal terbit; ~2.000 artikel terbaru per foto", "emitennews.com (sitemap publik)", "harian"),
    "raw/histori/emitennews":     ("Histori berita emiten IDX dari sitemap EmitenNews sejak 2017-03 (~90 ribu artikel; 2020 tampak tidak lengkap): URL, judul slug, tanggal", "emitennews.com (sitemap publik)", "sekali (21 Nov 2026)"),
    "raw/harian/spread_idx":      ("Foto bid/ask/ukuran semua saham IDX 4x sehari SAAT JAM BURSA (~09:30, 11:00, 14:00, 15:10 WIB, Senin-Jumat): bid, ask, bidSize, askSize, harga, volume hari ini, waktu kuotasi, spread %; untuk mengukur biaya transaksi nyata", "Yahoo Finance (screener JKT)", "4x per hari bursa (hanya ke depan)"),
    "raw/harian/sbn":             ("Foto harian yield obligasi Indonesia (PHEI): kurva SBN IGSYC 0,1-30 thn, seri benchmark FR & PBS, seri ritel, yield korporasi per tenor & peringkat (AAA-BBB); hari ini & kemarin", "PHEI (phei.co.id)", "Harian (hanya ke depan)"),
    "raw/harian/api":             ("Titik api (kebakaran hutan/lahan) satelit di kotak Indonesia+Malaysia (bujur 94-142, lintang -11..7), 10 hari terakhir: koordinat, kecerahan, FRP (daya api), keyakinan, siang/malam; MODIS + VIIRS NOAA-20/21", "NASA FIRMS (API, MAP_KEY gratis)", "Harian"),
    "raw/histori/api":            ("Histori titik api per sumber per tahun: MODIS_SP sejak 2000-11 (1 km), VIIRS_SNPP_SP sejak 2012 (375 m), data standar terkoreksi", "NASA FIRMS", "Sekali + ulang 2 tahun terakhir"),
    "raw/harian/pelabuhan":       ("Aktivitas harian ~2.000 pelabuhan dunia (101 di Indonesia) dari sinyal kapal AIS: kapal singgah per jenis (kontainer, curah kering, kargo umum, roro, tanker) + perkiraan impor/ekspor (ton), 30 hari terakhir", "IMF PortWatch (API resmi)", "Harian (data telat ~1 minggu)"),
    "raw/harian/jalur_kapal":     ("Transit harian kapal di 28 jalur sempit dunia (Selat Malaka, Sunda, Lombok, Suez, Panama, Hormuz, ...): jumlah & kapasitas per jenis kapal, 30 hari terakhir", "IMF PortWatch (API resmi)", "Harian"),
    "raw/histori/pelabuhan":      ("Histori aktivitas pelabuhan dunia sejak 2019-01-01, per tahun", "IMF PortWatch", "Sekali (workflow manual)"),
    "raw/histori/jalur_kapal":    ("Histori transit jalur sempit dunia sejak 2019-01-01", "IMF PortWatch", "Sekali (workflow manual)"),
    "raw/harian/kalshi":          ("Foto harian SEMUA pasar prediksi Kalshi yang terbuka kecuali olahraga & parlay (~85 ribu: ekonomi CPI/NFP/PDB/Fed, indeks saham, komoditas, kurs, cuaca, politik): peluang (harga Ya), tawar/minta, volume, open interest, strike", "Kalshi (api.elections.kalshi.com, publik)", "Harian (hanya ke depan)"),
    "raw/harian/polymarket":      ("Foto harian ~3.500 pasar prediksi (2.100 volume terbesar + 2.100 likuiditas terbesar): pertanyaan, peluang (harga Ya), tawar/minta, volume, likuiditas, tanggal akhir", "Polymarket (gamma-api)", "Harian (hanya ke depan)"),
    "raw/harian/daftar_idx":      ("Foto harian daftar saham IDX menurut Yahoo (~840 saham, 89 kolom): kapitalisasi, saham beredar, BID/ASK (spread nyata), tanggal rilis laporan, rating analis", "Yahoo Finance (screener JKT)", "Harian (hanya ke depan)"),
    "raw/harian/wikipedia_idx":   ("Perhatian publik per saham IDX: pembaca harian artikel Wikipedia (id & en) ~280 perusahaan, 30 hari terakhir", "Wikimedia + Wikidata", "Harian"),
    "raw/histori/wikipedia_idx":  ("Histori pembaca Wikipedia per saham IDX sejak Juli 2015 (semua.parquet)", "Wikimedia + Wikidata", "Sekali (awal)"),
    "raw/harian/berita":          ("Judul & ringkasan berita keuangan Indonesia (Kontan, Antara, Tempo, Liputan6) tiap 4 jam, digabung per hari; kolom kode_disebut = kode saham IDX di judul", "RSS resmi media (robots.txt mengizinkan)", "Tiap 4 jam (hanya ke depan)"),
    "raw/harian/intraday_idx":    ("Harga INTRADAY 1 menit saham & ETF IDX, 3 hari bursa terakhir (tumpang tindih); waktu WIB tanpa zona; bar hanya di menit yang ada transaksi", "Yahoo Finance", "Harian (hanya ke depan)"),
    "raw/histori/intraday_idx":   ("Histori intraday IDX yang masih tersedia saat diambil: 5 menit (~60 hari) & 1 jam (~2 tahun)", "Yahoo Finance", "Sekali (awal)"),
    "raw/iklim":                  ("Indeks iklim global (histori lengkap, ditimpa harian): ONI (El Nino/La Nina sejak 1950), SOI, MEI v2, DMI/IOD (sejak 1870), suhu laut Nino mingguan (sejak 1981)", "NOAA CPC & PSL", "Harian (ditimpa)"),
    "raw/harian/iklim":           ("Foto harian 36 bulan terakhir semua indeks iklim (melacak revisi & versi yang tersedia saat itu)", "NOAA CPC & PSL", "Harian"),
    "raw/harian/udara":           ("Kualitas udara per jam 12 kota (Jakarta, Surabaya, Bandung, Medan, Semarang, Makassar, Palembang, Pekanbaru, Pontianak, Balikpapan, Singapura, KL): PM2.5, PM10, CO, NO2, SO2, ozon, debu, AQI; 7 hari terakhir", "Open-Meteo Air Quality (CAMS)", "Harian"),
    "raw/histori/udara":          ("Histori kualitas udara per jam 12 kota sejak September 2022 (semua.parquet)", "Open-Meteo Air Quality (CAMS)", "Sekali (awal)"),
    "raw/harian/pangan":          ("Harga pangan harian (beras, ayam, sapi, telur, bawang merah/putih, cabai merah/rawit, minyak goreng, gula + rinciannya): nasional 4 jenis harga + 34 provinsi pasar tradisional, 35 hari terakhir", "PIHPS Bank Indonesia", "Harian"),
    "raw/harian/jisdor":          ("Kurs JISDOR (USD/IDR referensi resmi Bank Indonesia, ditetapkan ~10:00 WIB saat jam bursa), 60 hari terakhir", "Bank Indonesia", "Harian"),
    "raw/histori/jisdor":         ("Histori kurs JISDOR harian sejak 20 Mei 2013 (3.271 hari)", "Bank Indonesia", "Sekali (awal)"),
    "raw/histori/pangan":         ("Histori harga pangan harian sejak Juli 2017, 1 file per tahun", "PIHPS Bank Indonesia", "Sekali (awal)"),
    "raw/cboe":                   ("CBOE: indeks.parquet = 32 indeks volatilitas/sentimen harian (VIX sejak 1990, struktur waktu VIX9D/3M/6M/1Y, VVIX, SKEW, SMILE, VXEEM pasar berkembang, VXFXI, VXEWZ, VXEFA, OVX minyak, GVZ emas, VXTLT, VXHYG, COR1M/3M korelasi tersirat, DSPX...), putcall_arsip.parquet = rasio put/call harian 2006-2019", "CBOE (cdn.cboe.com, CSV publik)", "Harian (ditimpa)"),
    "raw/worldbank":              ("World Bank Pink Sheet: harga_bulanan.parquet (71 komoditas sejak 1960: sawit, inti sawit, kelapa, karet, timah, nikel, batu bara, kopi robusta, kakao, LNG, kayu...), indeks_bulanan.parquet (16 indeks harga komoditas), arsip/<tanggal terbit>.xlsx (file asli tiap terbitan)", "World Bank (worldbank.org/en/research/commodity-markets)", "Mingguan Sabtu (terbit bulanan)"),
    "raw/ojk_emisi":              ("OJK Ikhtisar Perkembangan Emisi Efek & Aksi Korporasi MINGGUAN (kumulatif sejak awal tahun): IPO, right issue (PUT), obligasi/sukuk, aksi korporasi (PMTHMETD, transaksi material, merger, go private, perubahan usaha) + tanggal; arsip/ = xlsx asli, urai/ = format panjang (file, minggu_ke, bulan, tahun, lembar, bagian, sub_bagian, no, kolom, nilai). Mulai Jul 2026, hanya ke depan", "OJK (ojk.go.id)", "Mingguan Sabtu (file baru saja)"),
    "raw/alfred":                 ("ALFRED (arsip vintage FRED): SEMUA versi angka tiap seri makro ambil_makro.py (rilis pertama & revisi; vintage/<KODE>: tanggal, berlaku_mulai, berlaku_sampai [kosong = masih berlaku], nilai) + seri_rilis (kode -> rilis) + jadwal_rilis (tanggal terbit historis & terjadwal). Seri harian > 2.000 vintage (data pasar) dilewati", "St. Louis Fed ALFRED API", "Mingguan Sabtu (ditimpa)"),
    "raw/bis":                    ("BIS (Bank for International Settlements), semua negara: WS_GLI likuiditas global (kredit USD/EUR/JPY lintas batas), WS_CREDIT_GAP, WS_DSR beban utang, WS_TC total kredit, WS_CBPOL suku bunga kebijakan harian, WS_CBTA aset bank sentral, WS_EER kurs efektif, WS_XRU kurs, WS_SPP harga properti, WS_LONG_CPI", "BIS data.bis.org (unduhan massal resmi)", "Mingguan Sabtu (ditimpa)"),
    "raw/dts":                    ("Daily Treasury Statement AS sejak 2005-10, 9 tabel: saldo kas TGA, setoran/penarikan per kategori, transaksi utang publik, plafon utang, setoran pajak (s/d 2023-02), pengembalian pajak, investasi kas jangka pendek (s/d 2023-02), transfer pajak antarlembaga (sejak 2023-02)", "fiscaldata.treasury.gov (API resmi)", "Harian (ditimpa)"),
    "raw/lelang_as":              ("Semua hasil lelang surat utang pemerintah AS sejak 1979 (bid-to-cover, imbal hasil, porsi pembeli langsung/tidak langsung/dealer), ditimpa harian", "US Treasury fiscaldata", "Harian (ditimpa)"),
    "raw/harian/lelang_as":       ("Foto harian lelang Treasury 90 hari terakhir (melacak kapan hasil lelang terisi)", "US Treasury fiscaldata", "Harian"),
    "raw/kurs_ecb":               ("Kurs RESMI harian ECB ~40 mata uang sejak 1999 (rupiah & tetangga Asia sejak 2005): per_eur & per_usd, histori lengkap ditimpa tiap hari. LEBIH BERSIH dari Yahoo IDR=X", "Bank Sentral Eropa (ECB)", "Harian (ditimpa)"),
    "raw/harian/kurs_ecb":        ("Kurs resmi ECB 30 hari terakhir (untuk validasi harian)", "Bank Sentral Eropa (ECB)", "Harian"),
    "raw/insider_sec":            ("Transaksi orang dalam perusahaan AS (Form 3/4/5) sejak 2006, 1 file per kuartal: tanggal lapor, kode, pemilik & jabatan, beli/jual, lembar, harga, penanda 10b5-1", "SEC EDGAR", "Bulanan (tgl 3)"),
    "raw/fundamental_idx/info":   ("Foto ringkasan fundamental ~950 saham IDX: kapitalisasi, saham beredar, PER, PBV, ROE, utang, dividen, target harga & rekomendasi analis, kepemilikan", "Yahoo Finance", "Mingguan Sabtu (hanya ke depan)"),
    "raw/seki":                   ("SEKI Bank Indonesia: ~108 tabel Excel resmi (uang beredar sejak 1985, kredit per sektor/provinsi, DPK, suku bunga, neraca pembayaran, utang luar negeri, keuangan pemerintah). Folder per tanggal = HANYA tabel yang berubah; indeks.parquet = semua versi (tabel, judul, tanggal_ambil, sha256)", "Bank Indonesia (bi.go.id/SEKI)", "Mingguan Sabtu (simpan perubahan)"),
    "raw/ipo/daftar":             ("Foto harian daftar IPO saham Indonesia di e-IPO: id, kode, nama, status (Pre-Effective/Book Building/Offering/Allotment/Closed/Canceled...)", "e-IPO (e-ipo.co.id, BEI; halaman publik)", "Harian"),
    "raw/ipo":                    ("detail.parquet: 1 baris per IPO sejak e-IPO berdiri: sektor, saham ditawarkan, % dari total, PENJAMIN EMISI, jadwal book building + rentang harga, penawaran + harga final, penjatahan, distribusi, tanggal pencatatan, syariah", "e-IPO (e-ipo.co.id)", "Harian (ditimpa)"),
    "raw/laba_idx":               ("Pengumuman laba semua saham IDX: tanggal & jam (UTC/WIB), EPS perkiraan analis, EPS aktual, kejutan %, histori ~2004/2014+ & jadwal ke depan; foto/ = salinan mingguan (perkiraan bisa direvisi)", "Yahoo Finance (get_earnings_dates)", "Mingguan Sabtu"),
    "raw/aksi_idx":               ("Aksi korporasi semua saham & ETF IDX: dividen tunai (Rp/lembar) & stock split (rasio), seluruh histori, tanggal = tanggal EX; foto/ = salinan tiap minggu", "Yahoo Finance", "Mingguan Sabtu (semua.parquet ditimpa)"),
    "raw/fundamental_idx/laporan": ("Foto laporan keuangan ~950 saham IDX (laba rugi, neraca, arus kas; kuartalan & tahunan), format panjang", "Yahoo Finance", "Mingguan Sabtu (hanya ke depan)"),
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