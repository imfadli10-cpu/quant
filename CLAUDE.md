# Proyek Quant: Gudang Data & Riset Trading (proyek jangka panjang, berbulan-bulan)

Dokumen ini adalah "serah terima" dari sesi panjang sebelumnya (dimulai 15 November 2026).
Baca SELURUHNYA sebelum bekerja. Jangan mengulang keputusan yang sudah diambil tanpa alasan kuat.

---

## 1. Visi pengguna (jangan disalahpahami)

- Pengguna ingin menjadi **quant trader** dalam beberapa bulan ke depan. Ini proyek **berbulan-bulan**, bukan tugas sekali jadi.
- Inspirasinya **Renaissance Technologies (Jim Simons / Medallion)**: kumpulkan data **sebanyak mungkin**, apa pun yang bisa
  dijadikan angka, termasuk data "aneh" yang kelihatannya tidak berhubungan dengan pasar (cuaca, gempa, aktivitas matahari,
  perhatian publik, dll.), lalu analisis dengan statistik untuk mengambil keputusan trading.
- Prinsip pengguna sejak awal: **data sebanyak mungkin**, walaupun belum tentu berguna. **Jangan disimpan di laptop**
  (kapasitas terbatas). **Gratis, tanpa kartu kredit** (pengguna hanya punya kartu BRI, DANA, ShopeePay, GoPay).
- Pengguna ingin **terus menambah sumber data** bahkan saat sudah masuk tahap riset. Pola yang disepakati:
  **bergantian** antara menambah satu sumber baru dan satu langkah pengolahan/riset.
- Pemahaman yang disepakati soal Renaissance: tiru **cara berpikirnya**, bukan skalanya:
  1) data luas, 2) bersihkan dengan obsesif, 3) cari banyak sinyal lemah (mereka benar sekitar 50,75% dari waktu),
  4) gabungkan jadi satu model, 5) statistik ketat (hindari pola kebetulan), 6) modelkan biaya transaksi dengan teliti.
  Trader perorangan tidak bisa meniru kecepatan eksekusi, leverage, dan tim ilmuwan mereka. Medan realistis:
  horizon hari sampai minggu (bukan detik), dan pasar yang kurang diperebutkan dana besar (misalnya Indonesia).

## 2. Tentang pengguna & cara berkomunikasi

- SELALU pakai **Bahasa Indonesia** santai. Pengguna **pemula** pemrograman: jelaskan istilah baru dengan sederhana dan contoh.
- Berikan **file/kode LENGKAP** (ganti seluruh isi file), JANGAN potongan yang harus disisipkan manual: pengguna sering
  salah tempel, dan itu memicu error berantai. Kalau bisa, edit file dan jalankan perintahnya sendiri.
- **UJI dulu** sebelum menyerahkan. Pengguna sangat frustrasi kalau diberi kode yang salah berkali-kali
  ("JANGAN MAIN MAIN YA, HARUS SERIUS"). Uji dengan data yang meniru format ASLI (tipe tanggal, zona waktu, nama kolom).
- Pengguna mau **serius dan jujur**: jangan membesar-besarkan hasil. Hasil riset negatif disampaikan apa adanya.
- Kalau pengguna bilang "ngikut kau" / "bagusnya yang mana": **ambil keputusan** dan jelaskan alasannya singkat.
- Tugas analitis (menyusun daftar ide riset, merancang uji) adalah tugas Claude, JANGAN dilempar ke pengguna.
  Pengguna cukup memilih/menyetujui. (Pengguna pernah kesal saat diminta menulis jurnal ide sendiri.)
- Berikan **link langsung** (GitHub Actions, Hugging Face, dll.) saat menyuruh membuka sesuatu.
- Kebiasaan yang perlu diingatkan: tekan Ctrl+S sebelum menjalankan; `git status` sebelum `git add`
  (pastikan tidak ada file `kunci_*`); jangan mengetik kode Python di terminal; aktifkan venv (`(.venv)`).
- Lingkungan: Windows + PowerShell, VS Code, Python 3.13 di `D:\quant\.venv` (`.venv\Scripts\activate`).
  Drive C hampir penuh: semua di D atau cloud. Laptop bisa sleep di tengah proses lama: ingatkan.

## 3. Arsitektur (semua gratis, tanpa kartu kredit)

| Bagian | Layanan | Catatan |
|---|---|---|
| Kode | GitHub private `imfadli10-cpu/quant` | 2FA aktif |
| Data | Hugging Face dataset **private** `fadli-sparks/quant-data` | `raw/` = mentah, `bersih/` = siap pakai, `ref/` = referensi. Halaman depan = katalog otomatis (README) |
| Otomatisasi | GitHub Actions | Jatah repo private: 2.000 menit/bulan (= $12 "included"; $0,006/menit). Billing tidak pernah menagih (tanpa kartu), Actions berhenti kalau habis |
| Data publik raksasa | BigQuery Sandbox, project `potent-duality-512213-u4`, service account `quant-collector` (role BigQuery User) | Jatah 1 TB dibaca/bulan. Pemakaian rutin ~80 GB/bulan. Pagar pengaman 5 GB per query (dry run dulu) |
| Kunci API gratis | FRED, Hugging Face, BPS, GCP | Lihat bagian Rahasia |

Laptop hanya untuk menulis kode, tes kecil (`--tes`), dan analisis. Pekerjaan besar dijalankan di GitHub Actions.

## 4. Rahasia (JANGAN PERNAH di-commit atau ditampilkan)

- File lokal (diabaikan `.gitignore` lewat pola `kunci_*.txt`, `kunci_*.json`): `kunci_fred.txt`, `kunci_hf.txt`,
  `kunci_gcp.json`, `kunci_sec.txt`, `kunci_bps.txt`.
- GitHub Secrets: `FRED_API_KEY`, `HF_TOKEN`, `GCP_KEY_JSON`, `SEC_USER_AGENT` (nama+email, wajib untuk SEC), `BPS_KEY`.
- Pola kode: `os.environ.get("NAMA") or Path("kunci_x.txt").read_text().strip()` (server pakai Secrets, laptop pakai file).
- `.gitignore` juga mengabaikan: `.venv/`, `data/`, `*.csv`, `*.png`, `*.xlsx`, `__pycache__/`.
- Jangan memasukkan data pribadi pengguna ke User-Agent atau permintaan ke pihak luar tanpa izin (SEC sudah diizinkan).

## 5. Jadwal otomatis (.github/workflows/)

- `harian.yml`: **00:17 UTC (07:17 WIB)** setiap hari (~35 menit). Semua collector harian (masing-masing
  `continue-on-error: true` supaya tidak saling menghentikan) → `upload_ke_cloud.py` → `buat_katalog.py` →
  `validasi_harian.py` (gagal = GitHub mengirim email alarm ke pengguna).
- `fundamental.yml`: tanggal 2 setiap bulan, 02:41 UTC: `kumpul_sec.py` + `kumpul_bps.py` (mode bulanan) → upload.
- `gabung.yml`: setiap Minggu 03:23 UTC: `gabung.py` → `bersih/`.
- `fundamental_idx.yml`: setiap Sabtu 02:47 UTC: foto fundamental IDX (lihat bagian 6).
- `insider_sec.yml`: tanggal 3 setiap bulan 03:29 UTC + manual: transaksi orang dalam SEC (lihat bagian 6).
- `histori_as.yml`, `histori_bps.yml`: manual, sudah selesai 100%. `histori_finra.yml`: manual, SUDAH selesai
  19 Nov 2026 (17 menit; 9 file, 20,1 juta baris, 2.087 hari bursa, hari kosong = persis hari libur bursa AS). `PYTHONUNBUFFERED=1` wajib untuk pekerjaan panjang.

## 6. Katalog sumber data (status per 19 Nov 2026)

Collector harian (file per hari di `raw/harian/<nama>/<tanggal UTC>.parquet`, isinya beberapa hari terakhir, sengaja tumpang tindih):
- `ambil_makro.py`: FRED 75 seri (suku bunga, inflasi, likuiditas Fed, tenaga kerja, kurs 15 mata uang, yield 5 negara,
  energi, 13 komoditas IMF termasuk nikel/timah/sawit/batu bara/karet, 3 seri Indonesia termasuk kurs akhir bulan OECD; total 76) → `raw/makro/<KODE>.parquet` (ditimpa).
- `kumpul_harga_harian.py`: ~950 saham IDX + ~49 aset global (indeks 23 negara, futures, VIX, DXY, kurs, BTC), 7 hari → `raw/harian/harga`.
- `kumpul_saham_as.py`: daftar semua kode AS dari NASDAQ Trader (~12.900, termasuk ETF) → `raw/harian/daftar_saham_as`
  (lacak delisting, data "hanya ke depan") + harga 7 hari ~11.800 kode → `raw/harian/saham_as`. ~17 menit.
- `kumpul_cuaca_harian.py`: Open-Meteo 15 kota dalam SATU permintaan, 14 hari → `raw/harian/cuaca`.
- `kumpul_bigquery.py`: `bitcoin`, `ethereum`, `berita_gdelt` (nada/Goldstein/porsi konflik untuk ID/US/CH/JA/RS/lainnya),
  `google_trends_id`. Ethereum ~0,74 GB/hari, Trends ~1,8 GB/hari.
- `kumpul_wikipedia.py`: 20 artikel (id & en), 30 hari. `--histori` → `raw/histori/wikipedia/semua.parquet` (sejak Juli 2015).
- `kumpul_crypto.py`: Coinbase 404 pasangan crypto/USD: `crypto_harian` (14 hari) & `crypto_jam` (per jam, 3 hari).
- `kumpul_alam.py`: gempa USGS M2.5+ 14 hari → `raw/harian/gempa`; geomagnetik Kp/Ap + bintik matahari + F10.7 sejak 1932
  (GFZ) → `raw/alam/geomagnetik_matahari.parquet`. `--histori-gempa` → `raw/histori/gempa/<tahun>` (M4.5+ sejak 1990).
- `kumpul_riset.py`: CFTC COT (legacy sejak 1986, disaggregated & keuangan sejak 2006), 8 minggu → `raw/harian/cot_*`;
  histori otomatis sekali → `raw/histori/cot`; Fama-French (3 faktor & momentum sejak 1926, 5 faktor sejak 1963, desimal) → `raw/riset`.
- `kumpul_opsi.py`: foto rantai opsi 49 saham/ETF AS (termasuk EIDO), 6 jatuh tempo terdekat → `raw/harian/opsi`
  (data "hanya ke depan", mulai 20 Nov 2026).
- `kumpul_finra.py`: FINRA Reg SHO volume short harian ~12.000 saham AS (short, short dikecualikan, total), 10 hari
  → `raw/harian/finra_short` (mulai 19 Nov 2026). `--histori` → `raw/histori/finra_short/<tahun>.parquet` (sejak 1 Agustus 2018,
  upload tiap tahun, bisa dilanjutkan). `--tes` = cek cepat tanpa simpan. Baris penutup file (jumlah baris) dibuang.
- `kumpul_lme.py`: harga resmi LME (tunai & 3 bulan) + STOK gudang LME untuk nikel, timah, tembaga, aluminium, seng, timbal,
  40 hari → `raw/harian/lme` (mulai 19 Nov 2026). Sumber: tabel publik westmetall.com (robots.txt tidak melarang, jeda 2 detik).
  `--histori` → `raw/histori/lme/semua.parquet` (sejak 2008, 4.776 hari/logam; diambil dari laptop + `upload_satu.py`).
  Divalidasi: rata-rata bulanan = IMF di FRED (rasio 0,999–1,002, korelasi ≥ 0,993). Nilai kosong sah: libur bank Inggris
  (26-05-2014, 27-12-2016), nikel dihentikan Maret 2022, harga 3 bulan awal 2008. Lompatan nikel +44%/−28% Maret 2022 = NYATA (short squeeze).
- Sawit harian: `CPO=F` (USD Malaysian Crude Palm Oil, CME) masuk daftar GLOBAL `kumpul_harga_harian.py` & `ambil_harga.py`
  → histori `raw/harga/SAWIT.parquet` (sejak Mei 2010). Kontrak jarang ditransaksikan (87% hari volume 0) tapi harga berubah
  tiap hari; vs IMF sawit: rasio 0,995, korelasi perubahan bulanan 0,92.
- `kumpul_fundamental_idx.py` (workflow `fundamental_idx.yml`, tiap SABTU 02:47 UTC, ~25-30 menit): foto fundamental ~944 saham
  IDX dari Yahoo → `raw/fundamental_idx/info/<tanggal>` (kapitalisasi, saham beredar, PER, PBV, ROE, utang, dividen, target &
  rekomendasi analis, kepemilikan) + `raw/fundamental_idx/laporan/<tanggal>` (laba rugi, neraca, arus kas; kuartalan & tahunan,
  format panjang). Data "HANYA KE DEPAN": Yahoo cuma simpan ~6 kuartal / 4-5 tahun. Foto berurutan = tahu KAPAN laporan
  pertama muncul (cegah look-ahead) + simpan versi sebelum revisi. Foto pertama 19 Nov 2026 (dari laptop): info 797 saham,
  laporan 636 saham (sebagian korban rate limit Yahoo; sejak itu: 3 paralel, tunggu 60 dtk saat dibatasi, putaran kedua).
  JEBAKAN: sebagian emiten lapor dalam USD (`financialCurrency`) sedangkan harga IDR → PBV/PER dari Yahoo bisa ngawur
  (contoh AADI PBV 19.979). Hitung ulang rasio sendiri dengan kurs.
- `kumpul_kurs_ecb.py`: kurs RESMI harian ECB, ~42 mata uang (sejak 1999; IDR, MYR, THB, PHP, CNY sejak 2005-04; INR 2009)
  → `raw/kurs_ecb/semua.parquet` (histori lengkap, DITIMPA tiap hari) + `raw/harian/kurs_ecb` (30 hari). Format panjang:
  tanggal, mata_uang, per_eur, per_usd. **PAKAI INI untuk kurs harian, BUKAN Yahoo IDR=X** (USD/IDR ECB vs OECD akhir bulan:
  korelasi 0,96, rasio 0,9995; hanya 2 lompatan > 5%, krisis 2008 = nyata). Kurs ECB ditetapkan ~20:15 WIB = setelah IDX tutup.
  Situs Bank Indonesia (JISDOR) tidak merespons dari laptop (20 Nov 2026, WARP menyala) → belum dipakai.
- Batu bara HARIAN: tidak ada sumber gratis yang hidup (`MTF=F` Yahoo berhenti Des 2025; Newcastle tidak ada). Tetap bulanan IMF.

Bulanan:
- `kumpul_insider_sec.py` (workflow `insider_sec.yml`): transaksi ORANG DALAM perusahaan AS (SEC Form 3/4/5 "Insider
  Transactions Data Sets") → `raw/insider_sec/<2006q1..>.parquet`, 1 baris = 1 transaksi saham biasa. Sejak 2006q1 (sebelumnya
  tidak ada), ~60–170 ribu transaksi/kuartal, termasuk perusahaan yang sudah mati. Kolom kunci: `tanggal_lapor` (= saat
  PUBLIK, pakai ini di riset), `kode_transaksi` (P=beli pasar, S=jual, A/M/F/G = hibah/opsi/pajak/hadiah = bukan sinyal),
  `rencana_10b5_1` ("1"/"0", kosong sebelum ~2023; 61% penjualan 2026q3 terjadwal), `hubungan`/`jabatan`.
  Tautan dibaca dari halaman indeks SEC (lokasi file PINDAH sejak 2026q2). Kuartal yang sudah ada dilewati, 2 terbaru ditimpa.
  Kolom AFF10B5ONE tidak ada di arsip lama → diisi kosong. Alamat pelapor sengaja TIDAK disimpan (data pribadi).
- `kumpul_sec.py`: SEC companyfacts.zip (~1,4 GB), 25 konsep keuangan, ~20.588 perusahaan (termasuk yang sudah mati),
  ~16 juta baris → `raw/fundamental/sec/bagian_xx` + `tiker.parquet` (CIK → kode saham).
- `kumpul_bps.py`: BPS 1.767 variabel nasional, 3 tahun terakhir, 6 permintaan paralel → `raw/bps/terbaru`.
  `--histori` → `raw/histori/bps` (18 bagian, SUDAH lengkap, jutaan baris). Format panjang:
  var_id, judul, satuan, wilayah (banyak per provinsi/kota), kategori, tahun, periode, bulan, nilai.

Histori sekali jalan (sudah selesai): `ambil_semua_idx.py` (`raw/harga_idx`, 918 saham), `ambil_harga.py` (`raw/harga`, 52 aset),
`ambil_cuaca.py` (`raw/cuaca`, 15 kota sejak 1990), `isi_histori_as.py` (`raw/histori/saham_as`, 129 bagian, ~35 juta baris),
`isi_histori_bigquery.py` (Bitcoin sejak 2009, Ethereum & GDELT sejak 2015, per tahun), `isi_histori_crypto.py`
(`raw/histori/crypto_harian/semua.parquet`, 404 koin sejak listing).

Data bersih (`gabung.py`, DuckDB, versi file harian paling baru menang, tanpa dobel):
- `bersih/harga_idx.parquet`: 2,93 juta baris, 918 saham, 2000 → sekarang.
- `bersih/saham_as.parquet`: 35 juta baris, 12.740 kode, 1962 → sekarang (902 MB).
- Sumber lain BELUM digabung. Gabungkan hanya yang dibutuhkan riset.

Alat bantu: `upload_satu.py <jalur...>` (upload file/folder tertentu), `cari_bps.py <kata>`, `cek_bps.py <var_id>`,
`validasi_harian.py`, `buat_katalog.py` (tambahkan keterangan setiap folder baru ke kamus INFO).

## 7. Keterbatasan data yang diketahui

- Survivorship bias: daftar saham IDX & crypto hanya yang masih aktif saat diambil. SEC & daftar AS harian mencakup yang mati.
- Histori saham IDX di Yahoo umumnya baru sejak ~2000 (indeks IHSG sejak 1990).
- SET Thailand & PSEi Filipina di Yahoo hanya 1 hari histori (terbentuk perlahan dari collector harian).
- Kode AS "NA" hilang dari histori (dibaca pandas sebagai kosong), sudah diperbaiki untuk data harian.
- `IDNCPIALLMINMEI` berhenti April 2025; `BAMLH0A0HYM2`/`BAMLC0A0CM` di FRED hanya 3 tahun terakhir.
- Fama-French telat 1-2 bulan. Google Trends mingguan. Harga minyak WTI benar-benar negatif 20 April 2020.
- Arus dana asing per saham IDX TIDAK tersedia: situs IDX memblokir program (Cloudflare). Keputusan pengguna:
  JANGAN menembus/menyamar. Pakai pendekatan tidak langsung (USD/IDR, EIDO, BPS, FRED). Alternatif nanti: download manual harian.
- FINRA short: server hanya menyimpan file sejak 1 Agustus 2018 (lebih lama = 403), jadi hampir seluruhnya jatuh di
  periode DATA UJI (2019+). Riset dengan data ini butuh pembagian latih/uji sendiri, ditetapkan SEBELUM melihat data.
  Volume = hanya yang dilaporkan ke FINRA (off-exchange/TRF), bukan seluruh volume bursa. Sejak ~2022 volume berdesimal.
- Collector selalu mengambil beberapa hari ke belakang: kegagalan satu-dua hari tidak menghilangkan data.

## 8. Jebakan teknis yang SUDAH ditemukan (jangan diulang)

- JANGAN jalankan `upload_ke_cloud.py` dari laptop (menimpa file server dengan file tes). Pakai `upload_satu.py`.
- Jadwal harus mulai SETELAH 00:00 UTC (dulu alarm palsu karena proses melewati tengah malam UTC dan tanggal file berbeda).
- Tanggal dari sumber berbeda punya presisi/zona waktu beda (ms vs us, tz Jakarta): samakan dengan
  `pd.DatetimeIndex(pd.to_datetime(x))` → `tz_localize(None)` → `normalize()` → `astype("datetime64[ns]")`.
  JANGAN pakai `.values` pada tanggal ber-zona waktu (diam-diam menggeser satu hari).
- BigQuery `to_dataframe()` menghasilkan tipe `dbdate`: ubah ke datetime standar sebelum disimpan.
- `pd.read_csv` membaca "NA" sebagai kosong: pakai `dtype=str, keep_default_na=False`.
- SEC: kolom bertipe campur (CIK angka/teks): paksa tipe setiap kolom sebelum simpan.
- BPS: parameter `th` wajib, maksimal 3 tahun per permintaan, kode tahun = tahun − 1900, daftar dibagi per halaman.
  Jangan ulangi permintaan yang gagal 4xx (kecuali 429).
- Yahoo: sesekali gagal untuk kode tertentu ("possibly delisted"), biasanya sementara. Sembunyikan log dengan
  `logging.getLogger("yfinance").setLevel(logging.CRITICAL)`. Batch 100 kode + jeda.
- Open-Meteo & Wikipedia membatasi kecepatan: jeda + coba ulang (hormati `Retry-After`).
- Koneksi Python ke Hugging Face dari laptop pengguna kadang putus: nyalakan Cloudflare WARP. Situs Indonesia lebih cepat tanpa WARP.
- Pekerjaan panjang di Actions: upload per bagian (bukan per 5), `PYTHONUNBUFFERED=1`, dan bisa dilanjutkan (resume).
- Stok gudang LME nikel RUSAK di sumber 2–10 April 2012 (26–614 ton, seharusnya ~99.000): satu titik membuat t robust
  palsu −5,5. Data mentah dibiarkan; bersihkan saat dipakai (fungsi `bersihkan` di `riset_03b`: buang nilai < 10% atau
  > 10x median 21 hari). Aturan itu memakai median TERPUSAT (melihat 10 hari ke depan): boleh untuk riset historis,
  JANGAN untuk sinyal live. Pelajaran umum: kalau t robust dan t biasa sangat berbeda, curigai pencilan/data rusak.
- Kurs Yahoo `IDR=X` (`raw/harga/USDIDR.parquet`) RUSAK: lonjakan 1 hari (2010-11-01 = 888, 2012-02-07 −90%), nilai nyangkut
  9612,45 berulang Juli–Des 2013 (sampai 3 hari berturut-turut), dan BOLONG 2001–2003 (2003 cuma 106 hari). Untuk bulanan pakai
  FRED `CCUSSP02IDM650N` (kurs akhir bulan OECD, s/d 2023-12, sudah masuk `ambil_makro.py` → 76 seri). Untuk harian: fungsi
  `bersihkan` di `riset_04` (median TERPUSAT 9 hari, 4%, diulang; 21 titik dibuang) dan hanya sejak 2004. Pelajaran: SELALU
  cek lompatan harian & bandingkan dengan sumber kedua sebelum memakai seri harga apa pun.
- Uji yang memakai return "besok"/"minggu depan": filter harus berdasarkan tanggal TARGET (d+1) ≤ 2018-12-31, bukan
  tanggal sinyal. Cek hapus-data-2019+ WAJIB dijalankan tiap riset (menangkap kebocoran 1 hari di riset #5).
- Saat menulis kode Python yang berisi tiga backtick di dalam string, buat lewat variabel (mis. `"`" * 3`) supaya tampilan chat tidak rusak.

## 9. Aturan riset (WAJIB)

- Tulis dugaan + alasan logis SEBELUM melihat data (hindari HARKing & data mining).
- Data latih s/d **2018-12-31**; data uji **2019+ DIKUNCI**, dibuka sekali di akhir (`--buka-uji`), hanya untuk strategi yang lolos di data latih.
- Ambang signifikansi **|t| > 3**. Hitung berapa banyak uji yang sudah dilakukan (multiple testing).
- Uji di instrumen yang **BISA dibeli** (bukan indeks). Selalu potong biaya transaksi (asumsi IDX 0,4% bolak-balik).
- Uji kode riset dulu dengan data tiruan yang diberi pola tersembunyi: program harus menemukan pola itu kembali.

## 10. Status riset & rencana berikutnya

- **Riset #1 SELESAI: EIDO (ETF Indonesia di bursa AS) semalam → IHSG besok** (`riset_01_eido.py`, `riset_01b_cek.py`).
  IHSG buka→tutup t = +10,5 (tampak kuat), TAPI sebagian besar ilusi harga buka indeks yang basi (saham penyusun kecil belum
  bertransaksi saat pembukaan). Di saham likuid: BBRI t = +4,8, BBCA/BMRI/TLKM/ASII t ≈ 1,5–2,1, dan SEMUA rugi setelah biaya 0,4%
  (keuntungan kotor +0,1% s/d +0,3% per transaksi). Data uji tidak dibuka. Kesimpulan: bukan strategi tunggal; EIDO semalam
  mungkin berguna sebagai SALAH SATU sinyal dalam model gabungan.
- **Riset #2 SELESAI: momentum saham IDX** (`riset_02_momentum.py`). Data latih Des 2004–Okt 2018 (155 bulan), semesta
  ~98 saham (harga ≥ Rp100, median nilai transaksi 60 hari ≥ Rp1 miliar, ≥ 80% hari aktif). Sinyal akhir bulan, beli di
  tutup hari bursa pertama bulan berikutnya, tahan 1 bulan, 5 kelompok (K1–K5), bobot sama. 4 varian ditetapkan di depan.
  - **12-1 NYATA sebagai sinyal**: IC +0,069 (t = 5,0), K5−K1 +2,11%/bln (t = 4,0), naik rapi K1→K5; tahan di 50 saham
    paling likuid (IC t = 3,8) & saat return dipotong ±30% (t = 5,0); melemah di paruh kedua (2012–2018 t = 2,9).
  - **Yang bisa dijalankan BELUM LOLOS**: beli K5 saja, potong 0,4% × perputaran (~26%/bln), dibanding semesta tanpa biaya:
    +0,79%/bln, t = 2,6. K5 ~20 saham, median nilai transaksi Rp10 miliar/hari (34% di bawah Rp5 miliar).
  - 6-1 & 3-1 lebih lemah (IC t 3,1 & 2,6). Dugaan "pembalikan 1 bulan" SALAH: justru berlanjut (IC t = +2,9);
    membeli yang paling jatuh rugi ~13%/thn.
  - Kode lolos uji: `--tes-kosong` (data acak, IC ≈ 0) dan `--tes-tiruan` (pola tersembunyi ditemukan, t = 18,9).
    Menghapus semua data 2019+ memberi hasil IDENTIK (data uji benar-benar tidak disentuh). Data uji tidak dibuka.
  - Kelemahan yang belum bisa diatasi: survivorship bias; `Close` Yahoo sudah disesuaikan split (saringan harga memakai
    info masa depan, dampak kecil; nilai transaksi tidak terpengaruh); biaya 0,4% belum memasukkan spread/tick
    (saham murah: 1 tick bisa 0,5–1%), jadi hasil nyata kemungkinan sedikit lebih buruk.
  - Kesimpulan: bukan strategi tunggal; momentum 12-1 adalah kandidat TERKUAT sejauh ini untuk model gabungan.
- **Riset #3 SELESAI: komoditas bulan m → saham produsennya bulan m+1** (`riset_03_komoditas.py`). HASIL NEGATIF.
  Pasangan (tetap): nikel→INCO/ANTM, timah→TINS, batu bara→PTBA/ITMG/ADRO/BUMI/INDY/HRUM, sawit→AALI/LSIP/SGRO/SIMP/BWPT,
  Brent→MEDC/ENRG. Sinyal = perubahan rata-rata bulanan IMF/FRED; beli tutup hari bursa pertama m+1, tahan 1 bulan.
  - Cek kewajaran (bulan yang sama) OK: nikel t 5,9, timah 4,9, batu bara 4,0, sawit 7,4; minyak hanya 1,6 (MEDC/ENRG lemah terhadap Brent).
  - Prediksi bulan depan: SEMUA kemiringan positif tapi TIDAK ADA yang lolos: nikel t 1,7, timah 2,3, batu bara 0,9,
    sawit 0,2, minyak 2,5. Strategi "beli kelompok yang komoditasnya naik" vs pegang semua: +0,48%/bln, t = 0,8.
  - Kode lolos `--tes-kosong`/`--tes-tiruan` (pola 0,3 ditemukan, strategi t 4,7; TAPI kelompok 1 saham seperti timah
    daya ujinya rendah). Hapus data 2019+ → hasil IDENTIK. Data uji tidak dibuka.
  - Jeda terbit IMF di FRED tidak teratur (1-2 bulan, kadang >1 tahun; arsip ALFRED baru sejak Nov 2015). Uji memakai prinsip
    "informasi sudah publik di bursa LME/ICE akhir bulan m". Untuk dijalankan sungguhan butuh sumber harga HARIAN nikel/timah/batu bara/sawit.
  - "Pegang semua kelompok" +2,5%/bln di 2001-2018 = boom komoditas + survivorship bias, BUKAN sinyal.
  - Kesimpulan: bukan strategi; arah positif konsisten tapi lemah. Kalau nanti ada harga harian, bisa diuji ulang di horizon mingguan.
- **Riset #3b SELESAI: harga & stok komoditas HARIAN → saham minggu depan** (`riset_03b_komoditas_mingguan.py`). HASIL NEGATIF.
  Nikel/timah (LME, 2008–2018, 550 minggu), sawit (CPO=F, 2010–2018, 398 minggu). Minggu Sabtu–Jumat; sinyal minggu w,
  beli tutup hari bursa pertama minggu w+1 (harga LME & CME terbentuk SETELAH IDX tutup). t robust (White) = ukuran utama.
  - Cek kewajaran minggu yang sama sangat kuat (t 7,7–8,1), tapi prediksi minggu depan: nikel t −0,7, timah −0,7,
    sawit +2,1 (tidak lolos). Stok LME (dugaan negatif): nikel +1,0, timah +0,2. Strategi mingguan: kotor −0,02%/mg
    (t −0,1), bersih −14%/thn. Ganti ~67%/minggu → biaya membunuh strategi mingguan berbasis tanda naik/turun.
  - Di data TIRUAN dengan pola 0,2 pun strategi bersih hanya t 1,5: strategi mingguan butuh efek sangat besar.
  - Kode lolos `--tes-kosong`/`--tes-tiruan`; hapus data 2019+ → IDENTIK. Data uji tidak dibuka.
  - Kesimpulan riset #3 + #3b: pasar IDX menyerap harga komoditas DALAM minggu yang sama. Tidak ada reaksi lambat yang bisa dipakai.
- **Riset #4 SELESAI: kurs rupiah & DXY → keranjang 30 saham paling likuid IDX** (`riset_04_rupiah.py`). HASIL NEGATIF.
  Keranjang = 30 saham nilai transaksi terbesar tiap akhir bulan (saringan riset #2), bobot sama. 5 uji ditetapkan di depan.
  - Cek kewajaran bulan yang sama kuat: rupiah melemah ↔ keranjang turun (t −7,9), DXY (t −5,3).
  - Bulan m → m+1: kurs t −0,6 (robust), DXY t −1,3. Strategi "rupiah melemah bulan lalu → kas (bunga BI)":
    −0,19%/bln vs selalu pegang (t −0,5); Sharpe sedikit lebih baik (0,89 vs 0,68) hanya karena lebih sering di kas.
    Mingguan (tambahan): kurs t −1,3, DXY t +0,3. Tidak ada yang lolos.
  - Di data TIRUAN dengan pola −0,5 (t −3,8), strategi pindah-ke-kas pun hanya t 1,4: strategi timing butuh efek sangat besar.
  - Kode lolos `--tes-kosong`/`--tes-tiruan`; hapus data 2019+ → IDENTIK. Data uji tidak dibuka.
  - Catatan kejujuran: versi pertama memakai kurs Yahoo yang RUSAK (hasil H1 t 0,0 sempat terlihat). Sumber diganti
    karena cek kualitas otomatis, bukan karena hasil; versi bersih juga negatif.
  - Kesimpulan riset #1–#4: informasi makro/pasar yang JELAS (EIDO, komoditas, kurs) diserap IDX dalam hari/minggu yang sama.
- **Riset #5 SELESAI: saham "tidur" telat bereaksi** (`riset_05_saham_tidur.py`). HASIL NEGATIF untuk dugaan utama.
  Keranjang bulanan: LIKUID = peringkat nilai transaksi 1–30, TIDUR = 31–130 (saringan riset #2, ≥ Rp1 miliar).
  Butuh ≥ 80 saham lolos → sampel baru mulai 2010-08 (409 minggu latih). 4 uji ditetapkan di depan.
  - U1 LIKUID minggu w → TIDUR minggu w+1: t −0,6 (TIDUR TIDAK menyusul). Cek harga basi sama (−0,6).
  - U2 → (TIDUR − LIKUID) minggu w+1: t robust +3,2 (t biasa 3,9), TAPI diagnosis: berasal dari LIKUID yang BERBALIK
    minggu depan (kemiringan −0,14, t −2,1), bukan TIDUR menyusul (−0,04). Butuh short → tidak bisa dijalankan.
  - U3 strategi (TIDUR hanya setelah LIKUID naik, else kas): −9%/thn vs selalu pegang (t −1,9). U4 harian (diagnosis): t 2,9.
  - Kode lolos `--tes-kosong`/`--tes-tiruan` (pola 0,3 → t 5,8). Cek hapus-data-2019+ MENEMUKAN kebocoran 1 hari di U4
    (hari terakhir 2018 memakai return 2 Jan 2019) → diperbaiki → IDENTIK. Data uji tidak dibuka.
  - IDE BARU (muncul SETELAH lihat data, wajib riset terpisah dengan dugaan tertulis baru, hitung sebagai uji tambahan):
    pembalikan mingguan keranjang LIKUID → long-only "pindah keranjang" (setelah LIKUID naik pegang TIDUR, setelah turun
    pegang LIKUID). Efek kecil (~0,1 × gerak mingguan) vs biaya pindah 0,4% → peluang tipis.
- **Daftar ide berikutnya** (urutan rekomendasi):
  #6 posisi COT ekstrem → berbalik →
  #7 lonjakan Wikipedia → volatilitas crypto → #8 rezim stres (VIX/STLFSI) sebagai filter → #9 badai geomagnetik (latihan uji jujur)
  → #10 volatilitas tersirat opsi (tunggu data beberapa bulan)
  → #11 PEMBELIAN orang dalam (SEC, kode P, bukan 10b5-1) → saham AS 1–6 bulan ke depan (histori 2006+, tanpa survivorship;
  bisa dibeli lewat broker saham AS; latih s/d 2018, uji 2019+).
- Calon sumber data berikutnya: Polymarket, lelang Treasury AS. (SEC Form 4 & kurs ECB SUDAH ditambahkan 20 Nov 2026.)
  (Volume short FINRA, logam LME + stok, dan sawit harian SUDAH ditambahkan 19 Nov 2026.)
  Dengan harga harian LME & sawit, riset #3 bisa diuji ulang di horizon MINGGUAN (nikel/timah sejak 2008, sawit sejak 2010).
  Prioritaskan data "hanya ke depan" (tidak bisa diambil mundur).
- Pantau: email alarm, jatah menit GitHub (github.com/settings/billing, "$x used / $12.00"), jatah BigQuery.
- **Jatah GitHub Actions (keputusan 20 Nov 2026):** repo TETAP PRIVATE. Pengguna minta DIKABARI kalau mendekati batas.
  Per 20 Nov: $4,62 (~770 menit) terpakai; run harian ~42,5 menit; perkiraan bulan penuh ~1.500–1.600 dari 2.000 menit.
  Pengguna: "nggak usah mikirin menit" → menit BUKAN pertimbangan memilih data/riset & jangan dibahas; cukup pantau
  diam-diam. HANYA kalau perkiraan > ~1.800 menit/bulan atau Compute > ~$10:
  kabari, tawarkan (1) hemat `kumpul_saham_as.py` (~17 menit/hari) atau (2) jadikan publik SETELAH merapikan catatan pribadi
  di CLAUDE.md (repo publik = menit tak terbatas, tapi jadwal mati setelah 60 hari tanpa aktivitas & log Actions publik).
  Riwayat git sudah dicek bersih dari kunci/token (39 commit). Repo `sim-runs` publik, tidak memotong jatah.