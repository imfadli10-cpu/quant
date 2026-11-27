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
  (kapasitas terbatas). **Gratis, tanpa kartu kredit** (pengguna tidak punya kartu kredit).
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
- **UJI dulu** sebelum menyerahkan. Kode yang salah berkali-kali sangat mengganggu pengguna:
  proyek ini SERIUS. Uji dengan data yang meniru format ASLI (tipe tanggal, zona waktu, nama kolom).
- Pengguna mau **serius dan jujur**: jangan membesar-besarkan hasil. Hasil riset negatif disampaikan apa adanya.
- Kalau pengguna bilang "ngikut kau" / "bagusnya yang mana": **ambil keputusan** dan jelaskan alasannya singkat.
- Tugas analitis (menyusun daftar ide riset, merancang uji) adalah tugas Claude, JANGAN dilempar ke pengguna.
  Pengguna cukup memilih/menyetujui.
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
| Data publik raksasa | BigQuery Sandbox (ID project & service account ada di `kunci_gcp.json` / secret `GCP_KEY_JSON`, role BigQuery User) | Jatah 1 TB dibaca/bulan. Pemakaian rutin ~80 GB/bulan. Pagar pengaman 5 GB per query (dry run dulu) |
| Kunci API gratis | FRED, Hugging Face, BPS, GCP | Lihat bagian Rahasia |

Laptop hanya untuk menulis kode, tes kecil (`--tes`), dan analisis. Pekerjaan besar dijalankan di GitHub Actions.

## 4. Rahasia (JANGAN PERNAH di-commit atau ditampilkan)

- File lokal (diabaikan `.gitignore` lewat pola `kunci_*.txt`, `kunci_*.json`): `kunci_fred.txt`, `kunci_hf.txt`,
  `kunci_gcp.json`, `kunci_sec.txt`, `kunci_bps.txt`, `kunci_firms.txt` (NASA FIRMS, 20 Nov 2026), `kunci_nasdaq.txt` (Nasdaq Data Link, akun gratis
  dibuat 20 Nov 2026; hanya dipakai di laptop, belum perlu GitHub Secret karena WIKI sudah membeku).
- GitHub Secrets: `FRED_API_KEY`, `HF_TOKEN`, `GCP_KEY_JSON`, `SEC_USER_AGENT` (nama+email, wajib untuk SEC), `BPS_KEY`, `FIRMS_MAP_KEY`.
- Pola kode: `os.environ.get("NAMA") or Path("kunci_x.txt").read_text().strip()` (server pakai Secrets, laptop pakai file).
- `.gitignore` juga mengabaikan: `.venv/`, `data/`, `*.csv`, `*.png`, `*.xlsx`, `__pycache__/`.
- Jangan memasukkan data pribadi pengguna ke User-Agent atau permintaan ke pihak luar tanpa izin (SEC sudah diizinkan).

## 5. Jadwal otomatis (.github/workflows/)

- `harian.yml`: **00:17 UTC (07:17 WIB)** setiap hari (~76 menit per 22 Nov 2026; terlama: Wikipedia per saham ~35 mnt, saham AS ~12 mnt,
  opsi ~7 mnt; batas job 150 mnt, langkah Wikipedia per saham 45 mnt). Job yang terpotong batas waktu = upload di akhir TIDAK jalan = data hari itu hilang. Semua collector harian (masing-masing
  `continue-on-error: true` supaya tidak saling menghentikan) → `upload_ke_cloud.py` → `buat_katalog.py` →
  `validasi_harian.py` (gagal = GitHub mengirim email alarm ke pengguna).
- `fundamental.yml`: tanggal 2 setiap bulan, 02:41 UTC: `kumpul_sec.py` + `kumpul_bps.py` (mode bulanan) → upload.
- `gabung.yml`: setiap Minggu 03:23 UTC: `gabung.py` → `bersih/`.
- `fundamental_idx.yml`: setiap Sabtu 02:47 UTC: foto fundamental IDX (lihat bagian 6).
- `insider_sec.yml`: tanggal 3 setiap bulan 03:29 UTC + manual: transaksi orang dalam SEC (lihat bagian 6).
- `berita.yml`: tiap 4 jam (00:11, 04:11, ... UTC), paket minimal: `kumpul_berita.py` → `raw/harian/berita` (bagian 6).
- `paper_trading.yml`: Senin–Jumat 22:41 UTC (05:41 WIB, SEBELUM bursa buka) + manual: `paper_trading.py` →
  `raw/paper_trading/` (s2_pilihan, s2_semesta, s2_kinerja). Pilihan akhir bulan dicatat SEKALI per bulan, sebelum hari beli
  (`dicatat_sebelum_beli`=True = sah). Catatan lama TIDAK PERNAH diubah; kalau gagal membaca catatan lama → berhenti.
  Rumus terbukti IDENTIK dengan riset #12 (`--cek-riset`, 3 bulan). JANGAN ubah aturan S2; versi baru = portofolio baru.
  Portofolio resmi pertama: sinyal akhir Nov 2026, beli tutup 1 Des 2026. Portofolio kedua `s2v` (aturan private) menyusul sama.
  Portofolio KETIGA `ml` (EKSPERIMEN, 21 Nov 2026): model ML riset #36 (aturan & model di HF private: `private/paper_ml.py`,
  `private/model_ml_<T>.txt`; diunduh workflow). Model tahun T dilatih dgn sinyal <= Okt T-1 (aturan uji maju #36; model live ikut
  berlatih dgn data 2019+). `--cek-riset` IDENTIK 3 bulan. **WAJIB latih ulang tiap tahun**: model 2027 dilatih SETELAH target sinyal
  Okt 2026 terealisasi (awal Des 2026) & SEBELUM sinyal akhir Jan 2027 — `python private/paper_ml.py --latih 2027` lalu
  `python simpan_private.py`. CATATAN: `kerangka_riset()` membaca `data/raw/harga_idx` (histori statis Nov 2026) → sebelum melatih 2027,
  UNDUH ULANG histori penuh (`python ambil_semua_idx.py`, laptop) — JANGAN pakai `bersih/harga_idx`: Adj Close Yahoo menyesuaikan ulang
  SELURUH histori tiap dividen baru, sedangkan `bersih` = histori lama + potongan harian 7 hari → return di sekitar ex-dividen setelah
  histori diunduh KEHILANGAN dividen (bias kecil tapi sistematis). Tumpang tindih raw vs bersih s/d Nov 2026: identik (rasio 1,0000). `paper_trading.main()` kini meneruskan
  `b["cs"]` (spread Corwin-Schultz) ke pemilih. Tanpa model tahun berjalan → langkah `ml` gagal (continue-on-error), S2 tetap jalan.
  Portofolio KEEMPAT `s2p` (EKSPERIMEN, 21 Nov 2026, riset #40): S2, tapi saat BEARISH (IHSG 24 bulan < 0, Daniel-Moskowitz 2016)
  pegang SEMUA saham semesta bobot sama. Aturan di HF private (`private/paper_s2p.py`), `--cek-riset` IDENTIK (termasuk 2009-03 bearish).
- `histori_as.yml`, `histori_bps.yml`: manual, sudah selesai 100%. `histori_finra.yml`: manual, SUDAH selesai
  19 Nov 2026 (17 menit; 9 file, 20,1 juta baris, 2.087 hari bursa, hari kosong = persis hari libur bursa AS). `PYTHONUNBUFFERED=1` wajib untuk pekerjaan panjang.

## 6. Katalog sumber data (status per 19 Nov 2026)

Collector harian (file per hari di `raw/harian/<nama>/<tanggal UTC>.parquet`, isinya beberapa hari terakhir, sengaja tumpang tindih):
- `ambil_makro.py`: FRED 75 seri (suku bunga, inflasi, likuiditas Fed, tenaga kerja, kurs 15 mata uang, yield 5 negara,
  energi, 13 komoditas IMF termasuk nikel/timah/sawit/batu bara/karet, 3 seri Indonesia termasuk kurs akhir bulan OECD) + 99 seri FRED Indonesia AKTIF (tambahan 20 Nov 2026) + 22 seri likuiditas/resesi/kredit/ketidakpastian (21 Nov 2026: WRESBAL,
  WEI, IORB, T10Y3M, BAA10Y/AAA10Y, Sahm, CFNAI, prob. resesi, GEPU global, ketidakpastian pasar saham harian, ANFCI, KCFSI...; total 197)
  → `raw/makro/<KODE>.parquet` (ditimpa). Tambahan penting: data TIC Kemenkeu AS = ARUS DANA investor AS ke saham/obligasi
  Indonesia per bulan (mis. `USLTEQTYNET42218` pembelian bersih saham Indonesia oleh investor AS) = pengganti tidak langsung
  arus dana asing IDX; indeks HARIAN NASDAQ Indonesia sejak 2001 (kecil/menengah/besar & sektor, `NASDAQNQID*`) = sumber harga
  independen dari Yahoo; kepercayaan konsumen, indikator utama OECD, cadangan devisa, ekspor-impor, harga properti, kredit, PDB.
  Keterangan seri tambahan = judul asli FRED (bahasa Inggris) dengan awalan frekuensi [D]/[M]/[Q].
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
- `kumpul_jisdor.py` (harian, ~1 menit): KURS JISDOR Bank Indonesia (USD/IDR referensi resmi, ditetapkan ~10:00 WIB = SAAT jam bursa)
  → `raw/harian/jisdor` (60 hari) + `raw/histori/jisdor/semua.parquet` (`--histori`, 3.271 hari sejak 2013-05-20). Cara: formulir publik
  halaman JISDOR (rentang tanggal + tombol Unduh XLSX, ASP.NET postback; robots BI Allow /). Tanggal XLSX format AS (m/d/Y), kurs format
  Indonesia. Dari laptop WARP HARUS MATI. Server BI menerima GitHub (file pangan & sbn 21 Nov 2026 ada). Cek vs ECB: rasio median 1,0001,
  korelasi perubahan harian hanya 0,52 (jam penetapan beda 10 jam). Selisih 2–5% vs ECB Agu–Okt 2013 SEBABNYA BELUM TERBUKTI
  (dulu ditulis 'nyata, taper tantrum' tanpa diuji; OECD akhir bulan = JISDOR persis jadi bukan sumber independen; ECB 17–21 Okt 2013 melompat
  10.859→11.329→10.876 = ECB bisa jadi yang berderau); lompatan > 3% hanya 19–20 Mar 2020 (COVID).
- `kumpul_polymarket.py`: foto HARIAN pasar prediksi Polymarket (data "hanya ke depan", mulai 20 Nov 2026) → `raw/harian/polymarket`.
  2.100 pasar volume 24 jam terbesar + 2.100 likuiditas terbesar (dobel dibuang, ~3.500 pasar, ~$22 juta volume/hari).
  `harga_ya` = peluang hasil pertama. API: maks 100 per halaman, offset maks ~2.100 (lebih dalam butuh /markets/keyset yang
  berisi puluhan ribu pasar kecil: keyset > 10 menit, TIDAK dipakai). `--tes` = cek tanpa simpan.
- `kumpul_api.py` (harian): TITIK API kebakaran satelit NASA FIRMS di kotak Indonesia+Malaysia (bujur 94–142, lintang −11..7), 10 hari
  → `raw/harian/api` (MODIS_NRT + VIIRS_NOAA20_NRT + VIIRS_NOAA21_NRT; ~17 ribu titik/10 hari di musim hujan). `--histori`
  (workflow MANUAL `histori_api.yml`, ~3–4 jam, upload tiap tahun, bisa dilanjutkan) → `raw/histori/api/<sumber>_<tahun>.parquet`:
  MODIS_SP sejak 2000-11 (1 km, seri panjang konsisten) & VIIRS_SNPP_SP sejak 2012 (375 m). API area: maks 5 hari per permintaan,
  batas 5.000 transaksi/10 menit. Kunci: `kunci_firms.txt` / secret `FIRMS_MAP_KEY` (gratis, email; dibuat 20 Nov 2026).
  JEBAKAN: VIIRS S-NPP NRT KOSONG di 2026 (satelit tua) → pakai NOAA-20/21. `confidence` MODIS = angka 0–100, VIIRS = huruf l/n/h.
  Cek kewajaran: 15–19 Sep 2015 (kebakaran besar) 8.372 titik MODIS / 40.862 VIIRS. Kegunaan: emiten sawit/kertas, asap, El Nino.
- `kumpul_lelang_sbn.py` (harian, detik): HASIL LELANG SUN & SBSN dari DJPPR Kemenkeu → `raw/harian/lelang_sbn/<tanggal>` (format panjang:
  tanggal_lelang, jenis, seri, pos, teks, nilai; Rp dalam TRILIUN) + `halaman_<tanggal>` (HTML asli). Mulai 21 Nov 2026, HANYA ke depan.
  Cara (keputusan pengguna 21 Nov 2026): baca daftar berita BERANDA (API `api-djppr.kemenkeu.go.id/web/api/v1/page` = yang dimuat situs
  sendiri), buka berita "Hasil Lelang", urai tabel. Beranda cuma memuat ~1 hasil lelang terbaru → wajib harian. Tidak ada file kalau tidak
  ada hasil lelang (bukan error; tidak masuk validasi). DILARANG mendaftar seluruh situs lewat `/page/filter` (endpoint pencarian CMS
  internal; DITOLAK pengaman Claude Code sebagai akses tidak sah). Histori lama hanya lewat jalur resmi (permintaan data/publikasi DJPPR).
  JEBAKAN: `read_html` default mengubah "5,55" jadi 555 → baca sel sebagai teks (`thousands=None, decimal="|"`) lalu urai sendiri.
  Cek: SBSN 17 Nov 2026 penawaran Rp20,10 T, dimenangkan Rp10 T, bid-to-cover PBS041 2,60 (= 3,9063 / 1,5).
- `kumpul_kepemilikan_sbn.py` (harian, hanya file baru; pengurai `sbn_kepemilikan.py`): KEPEMILIKAN SBN Rupiah per jenis investor dari halaman
  publik DJPPR (slug dari menu beranda, API yang dimuat situs sendiri; TIDAK pakai /page/filter) → `raw/kepemilikan_sbn/harian.parquet`
  (tanggal, kategori, jenis SUN/SBSN/TOTAL, nilai Rp T, label, media_id, pertama_terlihat) + `arsip/` (file asli tiap versi, sha256) + `indeks.parquet`.
  Bulanan 2003-2013 (2003-2009 SUN saja), HARIAN sejak 2014 (Excel s/d 2024, PDF per bulan 2025+). Kategori baku: bank(+konvensional/syariah),
  institusi_negara, bi_net/bi_gross/bi_operasi_moneter, non_bank, reksadana, asuransi(_dana_pensiun), dana_pensiun, NON_RESIDEN (+pemerintah_asing),
  individu, lainnya, total. = PENGGANTI ARUS DANA ASING (asing di SBN). Cek: non-residen 4 Sep 2026 Rp917,71 T (= Kontan); porsi asing 38,6% (2019)
  → 14,4% (2022); identitas total cocok s/d 0,01 T. JEBAKAN: PDF format angka BERGANTI (Okt 2026 '1.209,49' Indonesia, Nov '1 ,209.49' Inggris
  + spasi nyasar); sel tabel PDF menempel antar baris tak konsisten per kolom → dibaca PER KOLOM (harus 15 nilai) + identitas hitung (gagal = error,
  bukan tebakan); label 'Bank Indonesia (net, tidak termasuk ... operasi moneter)' = bi_net; Excel lama ikut bagian B persen → berhenti di TOTAL;
  salah ketik tahun sumber (lembar Des 2022: 30-12-2023) dikoreksi otomatis & dicetak. Dobel antar file (2015-12-31 direvisi) → file terbaru menang.
  `pertama_terlihat` histori = 26 Nov 2026 (bukan tanggal terbit); jeda terbit nyata terlihat ke depan (23 Nov terlihat 26 Nov). Lampiran asing
  per SEKTOR & TENOR (bulanan 2008+) diarsip mentah, BELUM diurai.
- `kumpul_operasi_moneter.py` (harian, ~2 mnt): HASIL OPERASI MONETER Bank Indonesia (halaman publik bi.go.id/id/publikasi/lelang/operasi-moneter,
  robots Allow /) → `raw/harian/operasi_moneter/<tanggal>` (format panjang url/judul/tanggal_operasi/jenis/tabel_ke/baris/kolom/teks; angka = TEKS
  asli format Indonesia, mis. '39.023,00', 'Rp18.409', 'Tidak terdapat penawaran yang masuk') + `halaman_<tanggal>` (potongan <table> HTML asli).
  Jenis: SRBI, SUVBI, SVBI, SukBI, Term Deposit (Rp/valas), Repo, Reverse Repo SBN, PasBI, BI FRN, FX Swap, Spot/Swap CNY-CNH-JPY, Rollover DNDF,
  **DNDF Jual (volume USD per tenor = jejak INTERVENSI kurs BI)**. Daftar = 10/halaman, halaman 2-3 lewat postback tombol halaman (pola JISDOR).
  Mulai 26 Nov 2026. JEBAKAN: `<title>` halaman kadang generik → judul dari teks tautan daftar; halaman utuh ~300 KB → simpan tabel saja.
  HISTORI (`--histori`, workflow MANUAL `histori_operasi_moneter.yml`, ~3–4 jam, upload per tahun, bisa dilanjutkan) → `raw/histori/operasi_moneter/<tahun>`
  + `halaman_<tahun>`: lewat FILTER TANGGAL RESMI halaman daftar (dd/mm/yyyy, tombol Cari) per bulan + tombol Next. Daftar resmi baru mulai 2019
  (filter 2010–2018 kosong; label '20.138'/'4.667 data' tak konsisten → jumlah per BULAN yang dipercaya; Mar 2020 = 165 operasi). Halaman 2020 terurai
  normal. JEBAKAN: judul daftar memuat '&#160;' & U+200B di tengah kata → `bersih_judul()` sebelum tanggal/jenis diurai.
- `kumpul_indonia.py` (harian, detik): Bank Indonesia (robots Allow /) → (1) `raw/harian/indonia/<tgl>` = SELURUH histori IndONIA (suku bunga antarbank
  SEMALAM, sejak 2017-01-03, 2.396 hari) + Compounded IndONIA 30/90/180/360 hr & Indeks IndONIA (sejak 2019-01-02), format panjang tanggal/seri/nilai;
  formulir publik rentang bulan (pola JISDOR, 1 permintaan). (2) `raw/harian/kurva_pasar_uang/<tgl>` = MM Curve BI: rata-rata tertimbang & VOLUME
  pasar sekunder REPO 1 bln & SRBI 3/6/12 bln, sejak Jun 2026 (zip tahunan ditimpa BI; tahun lalu 302 → HANYA KE DEPAN). Angka file = pecahan (×100).
  Cek 26 Nov 2026: indeks = ACT/360 (selisih maks 0,00002 pp vs IndONIA); IndONIA − suku bunga kebijakan (BIS) −1,09..+0,92 pp (di koridor;
  2021–22 −0,71 = banjir likuiditas); lonjakan > 0,5 pp kebanyakan MENJELANG LEBARAN (2018-06-08, 2022-04-28, 2025-03-27, 2026-03-17) = nyata.
  JIBOR: halaman ada tapi tanpa tabel (tidak diambil). BI-Rate: sudah ada di BIS WS_CBPOL.
- `kumpul_reksadana_ojk.py` (workflow SENDIRI `reksadana_ojk.yml`, harian 05:37 UTC, anggaran 45 mnt): NAB & UNIT PENYERTAAN SETIAP REKSA DANA
  per akhir bulan dari halaman publik OJK (reksadana.ojk.go.id, tanpa robots.txt; detail bulan = StatistikNABReksadanaPublicDetail.aspx?year=&month=,
  grid DevExpress; 'Page size: All' = callback `c0:KV|<n>;<kv>;GB|21;12|PAGERONCLICK5|PSP-1;` + SEMUA input hidden termasuk CallbackState) →
  `raw/reksadana_ojk/bulan/<YYYY-MM>__<sha8>.parquet` (SETIAP versi; revisi bank kustodian) + `indeks.parquet`. Sejak 2013-01 (710 RD, Rp186 T) s/d
  2026-10 (2.161 RD, Rp624 T; Equity 361, Fixed Income 528, Money Market 308, Index 115, ETF 48). RD NAB 0 ikut (bubar) = BEBAS PENYINTAS.
  Cek: jumlah baris = 'N items' & jumlah NAB/unit = [Total] resmi (selisih pembulatan sen). Server OJK ~30–60 dtk/bulan. Histori dicicil
  ~3 run. Terbit mulai tgl 8 bulan berikutnya (OJK) → pit: tersedia = waktu_ambil versi pertama (histori: 27 Nov 2026 = artefak, pakai tgl 8 m+1
  + jeda). Total sejak Okt 2021 termasuk 'produk investasi lainnya'. Arus dana RD saham = permintaan domestik (bahan riset arus dana per saham? —
  portofolio per RD TIDAK ada, hanya NAB/unit). Pasardana (komersial, histori butuh login) & Infovesta (robots melarang) TIDAK dipakai.
  HBA/HMA ESDM TIDAK diambil (27 Nov 2026): situs Minerba 'dalam perbaikan', Kepmen di JDIH = PDF HASIL PINDAI (butuh OCR), dan HBA = rata-rata
  indeks bulan lalu (mirip IMF batu bara). Google News RSS: robots MELARANG bot Claude.
- `kumpul_estimasi_idx.py` (workflow SENDIRI `estimasi_idx.yml`, SABTU 04:23 UTC): foto PERKIRAAN ANALIS ~140 saham IDX dari Yahoo → `raw/estimasi_idx/<tgl>`
  (format panjang kode/tabel/periode/kolom/nilai): earnings & revenue estimate, eps_trend (konsensus vs 7/30/60/90 hr lalu), eps_revisions (naik/turun
  7/30 hr), growth, recommendations (4 bln), target harga. HANYA KE DEPAN (mulai 28 Nov 2026) → bahan riset REVISI PERKIRAAN LABA (Chan-Jegadeesh-
  Lakonishok 1996) setelah ~1 tahun foto. upgrades_downgrades IDX KOSONG di Yahoo. JEBAKAN: 0 = kosong bila numberOfAnalysts 0.
  Laporan publikasi BULANAN per bank (cfs.ojk.go.id) TIDAK diambil: sejak POJK 37/2019 terbit 3 bulan setelah periode (bulan ke-4) & bulan
  Mar/Jun/Sep/Des tidak wajib → kalah segar dari laporan kuartalan emiten (27 Nov 2026).
- `kumpul_mpob.py` (harian, detik): STATISTIK SAWIT MALAYSIA MPOB (bepi.mpob.gov.my; robots mpob.gov.my tanpa larangan) → `raw/harian/mpob/<tgl>`
  (format panjang laporan/bagian/baris/kolom/teks/nilai). Laporan = iframe `stat/web_report1.php?val=...` yg URL-nya DIBACA dari halaman menu
  (Monthly Release terbaru & Summary tahun berjalan; `val` = kode laporan, BUKAN tahun — tebakan val lain kosong). Bulanan: bulan lalu (r) & ini (p)
  per negara bagian (produksi, STOK, ekspor, impor, TBS) dgn header DIFFERENCE = 2 sel (selisih, selisih_pct). Ringkasan: tabel bulanan Des−bulan
  terakhir; impor CPO punya SEL GABUNGAN (kolom sel_<j>). Cek 26 Nov 2026: stok palm oil Sep 3.510.554 (bulanan) = 3.510.555 (ringkasan); Okt (p)
  3,62 jt t (+3,2%); ekspor Okt +56%. Histori tahun lalu TIDAK ada (hanya PDF Overview tahunan 2016–2025, belum diurai) → HANYA KE DEPAN.
- `kumpul_sbn.py` (harian, detik): YIELD OBLIGASI INDONESIA dari PHEI (Penilai Harga Efek Indonesia; robots.txt mengizinkan /Data)
  → `raw/harian/sbn` (mulai 20 Nov 2026, hanya ke depan; histori gratis tidak ada). Format panjang: kurva IGSYC tenor 0,1–30 thn,
  benchmark SUN (FR) & sukuk (PBS) dengan harga & kupon, seri ritel (ORI/SBR/ST/SR), korporasi per tenor × peringkat (IGS/AAA/AA/A/BBB).
  Halaman memuat 'hari ini' & 'kemarin' (kolom `hari`; `tanggal_data` = tanggal 'hari ini' dari judul kurva). Angka berformat Indonesia
  (`read_html(decimal=",", thousands=".")`). Tabel dikenali dari NAMA kolom. 20 Nov 2026: 1 thn 6,87%, 10 thn 7,75%.
  Kurva tenor ≥ 16 thn datar (sesuai halaman). BELUM TERBUKTI server PHEI menerima akses dari GitHub → cek run harian pertama.
- `kumpul_pelabuhan.py` (harian, ~2 menit): IMF PortWatch (API resmi ArcGIS, terbuka; atribusi IMF PortWatch) → `raw/harian/pelabuhan`
  (30 hari, ~2.071 pelabuhan dunia, 101 di Indonesia: kapal singgah per jenis + perkiraan impor/ekspor ton) & `raw/harian/jalur_kapal`
  (28 jalur sempit: Selat Malaka ~224 kapal/hari). Data TELAT ~1 minggu. `--histori` (workflow MANUAL `histori_pelabuhan.yml`,
  ~6 juta baris sejak 2019-01-01, upload per tahun, bisa dilanjutkan) → `raw/histori/pelabuhan/<tahun>` + `raw/histori/jalur_kapal/semua`.
  Maks 1.000 baris/permintaan (pelabuhan) & 10.000 (jalur); urut ObjectId + resultOffset. Kolom `date` = DateOnly.
  Kegunaan: ekspor batu bara (Balikpapan/Samarinda/Tanjung Redeb), nikel (Morowali/Kendari), sawit (Dumai/Belawan), kontainer Priok
  = perdagangan fisik ~1 bulan SEBELUM data BPS. Histori 2019+ = semuanya di periode DATA UJI → riset butuh pembagian sendiri.
- `kumpul_kalshi.py` (harian, ~5 menit): foto SEMUA pasar prediksi Kalshi (bursa prediksi teregulasi CFTC) yang terbuka, KECUALI
  kategori Sports (>120 ribu pasar) & parlay `KXMVE` → `raw/harian/kalshi` (mulai 20 Nov 2026, hanya ke depan). ~85 ribu pasar/hari:
  Elections, Financials (rentang S&P/Nasdaq/emas/platinum/kurs), Economics (CPI, NFP, PDB, Fed), Crypto, Commodities, cuaca, dll.
  Cara: `/series` (peta kategori, 16.757 seri) + `/events?with_nested_markets=true&status=open` (200 per halaman, ~115 halaman).
  Data pasar publik TANPA kunci. Situs kalshi.com (bukan API) memasang Vercel checkpoint → jangan disentuh, pakai API saja.
  Pasar ekonomi Kalshi = PERKIRAAN PASAR untuk rilis data (CPI, NFP) → bahan riset "kejutan" rilis makro nanti.
- `kumpul_spread_idx.py` (workflow `spread_idx.yml`, Senin–Jumat 4x: ~09:31, 11:01, 14:01, 15:11 WIB): foto BID/ASK semua saham IDX SAAT
  JAM BURSA → `raw/harian/spread_idx/<tanggal>_<HHMM UTC>.parquet` (mulai 23 Nov 2026). Tujuan: mengukur BIAYA TRANSAKSI NYATA.
  TEMUAN AWAL (21 Nov 2026, 2 foto daftar_idx DI LUAR jam bursa, 815 saham): spread ASLI vs model biaya riset (max(Corwin-Schultz, tick)):
  >Rp20 M/hari 0,47% vs 1,38% | Rp5–20 M 0,70% vs 1,33% | Rp1–5 M 0,97% vs 1,80% | <Rp1 M 1,50% vs 1,85% → model ~1,9x terlalu mahal
  untuk semesta riset; Corwin-Schultz di IDX lebih mencerminkan volatilitas. Korelasi peringkat asli vs CS hanya 0,39. BELUM final:
  tunggu foto jam bursa beberapa minggu, lalu pra-registrasi ulang evaluasi biaya (#36/#37/S2). Aturan tick IDX berubah antar tahun.
  ESTIMATOR EDGE (Ardia-Guidotti-Kroencke 2022, pustaka `bidask`, dipakai Hanauer-Kalsbach) DIUJI 21 Nov 2026 (818 saham, 42 hari OHLC):
  TIDAK lebih baik di IDX: rasio ke spread asli (saham >= Rp1 M/hari) EDGE 2,03 | CS 1,88 | **1 tick/harga 0,96 (galat median 0,04 pp)**;
  korelasi peringkat EDGE 0,39 = CS 0,39 < tick 0,46. Di IDX spread ~ 1 tick (antrean tebal) → pakai model biaya B (tick historis), BUKAN EDGE/CS.
- `kumpul_daftar_idx.py` (harian, SEBELUM harga harian): foto screener Yahoo bursa JKT (~838 saham, 89 kolom: marketCap,
  sharesOutstanding, BID/ASK, earningsTimestamp, rating analis...) → `raw/harian/daftar_idx` (mulai 20 Nov 2026, hanya ke depan).
  Kode yang ada di Yahoo tapi belum di daftar → `ref/daftar_saham_tambahan.csv` (TIDAK pernah dikurangi). Daftar Yahoo TIDAK
  lengkap (106 saham kita tidak ada, mis. ADHI) → hanya untuk MENAMBAH. Spread bid-ask median 1,00% (20 Nov, siang).
- `daftar_saham.py` → `kode_idx()`: daftar_saham.xlsx + tambahan. DIPAKAI `kumpul_harga_harian.py`, `kumpul_fundamental_idx.py`,
  `paper_trading.py` (dulu daftar statis → saham IPO baru tidak pernah terkumpul).
- `kumpul_perhatian_idx.py` (harian): PERHATIAN PUBLIK per saham IDX = pembaca harian artikel Wikipedia (id & en, agen 'user')
  → `raw/harian/wikipedia_idx` (30 hari) + `raw/histori/wikipedia_idx/semua.parquet` (`--histori`, sejak 2015-07).
  Peta kode → artikel dari WIKIDATA (`daftar_saham.wikidata_idx()`, BEI = Q1661737, BUKAN Q1144893): ~1.012 kode, ~279 artikel id,
  ~74 en → `ref/wikidata_idx.parquet`. Artikel yang ganti judul kehilangan histori sebelum ganti judul.
  Wikidata TIDAK mencatat tanggal delisting (hanya 2 dari 1.048) & Yahoo TIDAK menyimpan harga saham IDX yang sudah delisting
  (1 dari 37 kandidat) → survivorship IDX tetap tidak bisa ditambal.
- `kumpul_daftar_idx.py` juga memakai Wikidata sebagai sumber KEDUA kode terlewat: kode Wikidata yang belum di daftar tapi punya
  harga Yahoo 10 hari terakhir → tambahan dengan kolom `jenis` (saham/etf, dari quoteType Yahoo). 20 Nov 2026: TELE (saham) +
  31 ETF IDX (XIIT, XBLQ, XISI...). `kode_idx()` bawaan = SAHAM saja (paper trading & fundamental: semesta S2 tetap);
  `kode_idx(termasuk_etf=True)` = saham + ETF (collector harga harian). ETF IDX = instrumen indeks yang BISA dibeli.
- `kumpul_berita.py` (workflow `berita.yml`, tiap 4 jam): judul + ringkasan berita RSS RESMI media yang robots.txt-nya
  MENGIZINKAN: Kontan Investasi, Antara Bursa & Ekonomi, Tempo Bisnis, Liputan6 Bisnis + (21 Nov 2026) Detik Finance (100), Okezone
  Ekonomi, Sindonews Ekbis, Republika Ekonomi, Kumparan (umum) (~365 berita per foto; Suara & JPNN robots MELARANG; Tempo Bisnis RSS BASI:
  item terbaru 8 Nov 2026 saat dicek 21 Nov) →
  `raw/harian/berita/<tanggal UTC>.parquet` (foto-foto di hari yang sama DIGABUNG, dobel dibuang menurut tautan; gagal
  membaca file hari ini → berhenti). `kode_disebut` = kode saham IDX di judul/ringkasan. Mulai 20 Nov 2026 (hanya ke depan).
  TIDAK dipakai: CNBC Indonesia & IDX Channel (robots.txt MELARANG), Bisnis.com (403). Kontan cuma ~7 jam → wajib tiap 4 jam.
  TERKONFIRMASI 20 Nov 2026 (file `status_<tanggal>.parquet`): Kontan MENOLAK server GitHub (HTTP 403), dari laptop diterima
  → pemblokiran per alamat server; JANGAN ditembus. Dari server praktis 4 sumber (Antara x2, Tempo, Liputan6).
  Tidak ada di `validasi_harian.py` (jam tidak sinkron); workflow berita gagal sendiri = email.
- `kumpul_emitennews.py` (harian, detik): BERITA EMITEN IDX dari SITEMAP EmitenNews (robots mengizinkan /news/ & mencantumkan sitemap; HANYA
  sitemap dibaca, halaman artikel tidak) → `raw/harian/emitennews` (~2.000 terbaru) + `raw/histori/emitennews/semua.parquet` (`--histori`,
  89.902 artikel 2017-03 s/d 2026-11; per tahun 1,1 rb (2017) → 16,3 rb (2022); **2020 cuma 1.111 = sitemap 2020 TIDAK LENGKAP**).
  Kolom: url, slug, judul_slug, tanggal (= lastmod; divalidasi = tanggal terbit 7/7 artikel yg halamannya masih ada), sitemap. Judul asli memuat
  kode dalam kurung ("Bakrie (BUMI)") → slug memuat kode huruf kecil; cocokkan dgn daftar kode & BUANG kode yang juga kata umum. Jam terbit
  tidak ada → pakai hari bursa SESUDAH tanggal. JEBAKAN (22 Nov 2026): lastmod bisa di MASA DEPAN (artikel terjadwal, mis. "rupiah pagi ini"
  bertanggal Senin 23 Nov sudah ada di sitemap Minggu 22 Nov; histori 1 kasus) → arahnya konservatif (kita tahu SEBELUM tanggalnya), bukan
  kebocoran; untuk sinyal live pakai max(tanggal, tanggal ambil). Bahan riset "berita × dekat puncak 52 mg" (Kalsbach Bab 3): histori 2017+ = sebagian besar
  periode UJI → butuh pembagian latih/uji sendiri.
- `kumpul_intraday_idx.py` (harian): bar 1 MENIT semua saham & ETF IDX, 3 hari bursa terakhir → `raw/harian/intraday_idx`
  (~284 ribu bar/hari, ~1,9 MB, ~2,5 menit; mulai 20 Nov 2026). Yahoo hanya menyimpan 1 menit ~8 hari, 5 menit ~60 hari, 1 jam
  ~2 tahun → data HANYA KE DEPAN. `--histori` (sekali, 20 Nov 2026) → `raw/histori/intraday_idx/5m_*.parquet` & `1h_*.parquet`.
  Waktu = WIB tanpa zona. Bar hanya ada di menit yang ada transaksi. Bar terakhir ~15:49; harga penutupan resmi di data harian.
- `kumpul_iklim.py` (harian): indeks iklim NOAA → `raw/iklim/<seri>.parquet` (ditimpa) + `raw/harian/iklim` (foto 36 bulan,
  melacak revisi). Seri: `oni` (El Nino ≥ +0,5 / La Nina ≤ −0,5, rata-rata 3 bulan ditandai bulan TENGAH, sejak 1950), `soi`
  (tabel STANDARDIZED, negatif = El Nino), `mei` (v2, musim 2 bulan ditandai bulan kedua, sejak 1979), `dmi` (IOD, positif =
  Indonesia lebih kering, sejak 1870, TERLAMBAT ~6 bulan!), `nino_mg` (suhu & anomali mingguan Nino 1+2/3/3.4/4, sejak 1981,
  paling segar). Cek kewajaran OK: ONI 1997-12 +2,37, 2015-12 +2,59, La Nina 2010-12 −1,48; IOD+ 1997 & 2019.
  JEBAKAN format: SOI lebar tetap 6 karakter (nilai kosong '-999.9' menempel); kode kosong beda tiap file (-999.9/-999.00/-9999).
  Riset nanti: pakai versi yang SUDAH TERBIT saat itu (ONI/SOI/MEI terbit ~awal-pertengahan bulan berikutnya & bisa direvisi).
  Per 20 Nov 2026: El Nino KUAT sedang berlangsung (ONI ASO +2,46; Nino 3.4 mingguan +3,2).
- `kumpul_udara.py` (harian): KUALITAS UDARA per jam 12 kota (6 kota besar RI + 4 kota rawan asap kebakaran + Singapura & KL)
  → `raw/harian/udara` (7 hari) + `raw/histori/udara/semua.parquet` (`--histori`, sejak 2022-09; sebelum itu KOSONG di Open-Meteo).
  Semua kota dalam SATU permintaan. Cek kewajaran OK: PM2.5 bulanan tertinggi Palembang = Okt 2023 & Sep–Okt 2026 (tahun El Nino,
  asap kebakaran). Dasar riset: polusi ↓ suasana hati investor (Levy-Yagil 2011; Heyes dkk. 2016). Histori pendek → data ke depan.
- `kumpul_pangan.py` (harian): HARGA PANGAN harian PIHPS Bank Indonesia (alamat data publik halaman bi.go.id/hargapangan;
  robots.txt MENGIZINKAN) → `raw/harian/pangan` (35 hari) + `raw/histori/pangan/<tahun>.parquet` (`--histori`, sejak 2017-07).
  10 kategori (beras, daging ayam/sapi, telur, bawang merah/putih, cabai merah/rawit, minyak goreng, gula) + rincian = 31 baris;
  NASIONAL 4 jenis harga (pasar tradisional/modern, pedagang besar, produsen) + 34 PROVINSI pasar tradisional.
  JEBAKAN: dari laptop WARP HARUS MATI (dengan WARP server BI lambat 20 dtk lalu tidak merespons). Permintaan setengah tahun
  ±10 dtk (setahun ±43 dtk). Jeda 2 dtk. Kode provinsi = angka (bug label 'Nasional' sudah diperbaiki; cek ≥ 30 wilayah).
  BELUM TERBUKTI server BI menerima akses dari server GitHub (Kontan menolak) → cek hasil run harian pertama.
- `kumpul_lelang_as.py` (harian): SEMUA lelang Treasury AS sejak 1979 (11.154 lelang, 114 kolom) → `raw/lelang_as/semua.parquet`
  (ditimpa) + `raw/harian/lelang_as` (90 hari, melacak kapan hasil terisi). API fiscaldata TERLAMBAT ~1 bulan & memuat lelang
  yang baru diumumkan (kolom hasil kosong). JEBAKAN: kolom 'ref_cpi_on_*_date' & 'index_ratio_on_issue_date' berisi ANGKA
  (indeks inflasi TIPS) walau namanya '_date' → tipe ditentukan dari ISI, bukan nama kolom.
- `kumpul_dts.py` (harian, ~5 menit): DAILY TREASURY STATEMENT AS (fiscaldata, tanpa kunci) → `raw/dts/<tabel>.parquet` (9 tabel, SEMUA
  baris sejak 2005-10, DITIMPA; ~870 ribu baris, 8 MB). Saldo kas TGA (`operating_cash_balance`; 19 Nov 2026: $891 miliar) = komponen
  likuiditas dolar (neraca Fed − TGA − RRP). Pajak harian: `federal_tax_deposits` & `short_term_cash_investments` BERHENTI 2023-02-13
  (format DTS berubah) → sesudahnya rincian pajak ada di `deposits_withdrawals_operating_cash` (kategori) + `inter_agency_tax_transfers`.
  Riset nanti harus menyambung dua format itu. Tipe kolom dari ISI (pola lelang_as).
- FRAKSI HARGA (tick) BEI BERUBAH: s/d 5 Jan 2014 Rp1/5/10/25/50 (batas 200/500/2.000/5.000); 6 Jan 2014–1 Mei 2016 Rp1/5/25 (batas
  500/5.000); sejak 2 Mei 2016 Rp1/2/5/10/25. `paper_trading.tick()` = aturan 2016 (SALAH untuk 2005–2015) → pakai `biaya_idx.tick_historis`
  + `harga_asli` (Close Yahoo disesuaikan split; dibalik pakai raw/aksi_idx).
- `kumpul_cboe.py` (harian, ~30 dtk): CBOE (CSV publik cdn.cboe.com; robots www hanya melarang /book/ & laporan volume) →
  `raw/cboe/indeks.parquet` (32 indeks, format panjang indeks/tanggal/buka/tertinggi/terendah/tutup, DITIMPA): VIX 1990+, VIX9D/3M/6M/1Y/1D,
  VVIX, SKEW, SMILE, VXEEM (pasar berkembang, 2011+), VXFXI, VXEWZ, VXEFA, VXN, RVX, VXD, OVX, GVZ, VXSLV, VXGDX, VXTLT, VXHYG, COR1M/3M,
  DSPX, VIXEQ, VX saham tunggal, SPX. + `raw/cboe/putcall_arsip.parquet` (put/call total/ekuitas/indeks/VIX/ETF 2006–2019-10; sesudahnya
  tidak ada file). 20 Nov 2026: VIX 35,9 (puncak 40), VXEEM 45,9. JEBAKAN data sumber: VXHYG 2017–2018 RUSAK (−19,7 juta & lompatan acak),
  DSPX ada nilai 0 (2018), VXD 2021-07-14 +472% & VXEEM 2021-04-22 +165% mencurigakan → bersihkan saat dipakai. Lompatan NYATA:
  VIX 2018-02-05 +116% (Volmageddon), OVX 2020-04 (minyak negatif). Indeks EVZ, VXXLE, TYVIX, SRVIX, VOLI: 403 (tidak tersedia).
- `kumpul_putcall.py` (harian, detik): CBOE daily market statistics (JSON publik cdn.cboe.com/data/us/options/market_statistics/daily/
  <tgl>_daily_options; robots hanya melarang /book/ & volume_reports) → `raw/harian/putcall` (10 hari) + `raw/histori/putcall/semua.parquet`
  (`--histori`, 1.793 hari 2019-10-07 s/d 2026-11-20). Format panjang: tanggal, produk (TOTAL/INDEX/EQUITY/ETP/VIX/SPX/MXEF...), ukuran
  (RASIO / VOLUME / OPEN INTEREST), call, put, total, rasio. MENYAMBUNG `raw/cboe/putcall_arsip` (berakhir 2019-10-04) TANPA celah, tanpa
  tumpang tindih (rata 60 hari indeks 1,26 → 1,29). Cek: rasio ekuitas = put/call volume (korelasi 1,0); hari kosong = libur bursa AS (67).
  Rasio tepat 0 DIKOSONGKAN (0/0 saat produk tak diperdagangkan; mis. 2025-01-09 hanya sesi pendek opsi indeks). Rasio ekuitas tinggi akhir
  2022 (s/d 2,40) = nyata (pasar bearish, volume normal). Median rasio total 2019–2026 0,90; 20 Nov 2026: 1,13.
- `kumpul_pinksheet.py` (workflow `fundamental_idx.yml`, SABTU): World Bank Pink Sheet → `raw/worldbank/harga_bulanan.parquet` (71 komoditas
  sejak 1960, format panjang komoditas/satuan/bulan/harga) + `indeks_bulanan.parquet` (16 indeks, 2010=100) + `arsip/<tanggal terbit>.xlsx`
  (hanya terbitan BARU; terbit ~awal bulan, mis. 2026-11-03 berisi s/d Okt 2026 → point-in-time). Tautan Excel ber-ID yang berubah tiap
  terbitan → dicari dari halaman resmi. Header lembar indeks BERTINGKAT (nama di baris 5–8) → nama = teks terisi pertama per kolom. '…' = kosong.
  Sumber KEDUA untuk harga IMF di FRED (sawit, nikel, timah, batu bara, karet) → cek silang.
- GDELT GKG per EMITEN IDX TIDAK diambil (21 Nov 2026): uji Okt 2026 (0,57 GB) → hanya 17 dari 834 nama emiten (nama resmi dinormalkan)
  muncul di kolom V2Organizations, kebanyakan bank besar dengan 1–183 sebutan/bulan. Biaya histori 2015–2026 ~330 GB (≈20–44 GB/tahun) tidak
  sebanding. Untuk perhatian media per saham pakai `raw/harian/berita` (RSS Indonesia, kolom kode_disebut).
- PORTAL DATA OJK (data.ojk.go.id/SJKPublic) TIDAK diambil (27 Nov 2026): firewall (F5 'Request Rejected') MENOLAK program — robots.txt pun
  ditolak, data katalog (GetGridData) ditolak → JANGAN ditembus. Isinya PENTING (dari 'Mapping Statistik Pasar Modal.xlsx' di halaman statistik OJK):
  nilai perdagangan saham per TIPE INVESTOR (asing/domestik), komposisi kepemilikan efek KSEI per tipe investor, SID per provinsi/kota,
  penjualan APERD, NAB per jenis RD. Alternatif: UNDUH MANUAL oleh pengguna dari portal (fitur 'Download' resmi) lalu `upload_satu.py`.
- KSEI (statistik investor) TIDAK diambil: hanya PDF bulanan bergrafik dengan nama file tak konsisten & tanpa daftar publik (21 Nov 2026).
- `kumpul_bis.py` (workflow `fundamental_idx.yml`, SABTU): BIS unduhan massal resmi (data.bis.org/static/bulk, robots Allow /) →
  `raw/bis/<DATASET>.parquet` (DITIMPA, semua negara): WS_GLI likuiditas global, WS_CREDIT_GAP, WS_DSR, WS_TC, WS_CBPOL (suku bunga kebijakan
  HARIAN), WS_CBTA, WS_EER (kurs efektif harian), WS_XRU, WS_SPP, WS_LONG_CPI; ~3,9 juta baris, 21 MB. Kolom 'KODE: Label' dipecah jadi
  <dim> & <dim>_label (hanya nilai unik → cepat). Unduhan dari laptop SANGAT lambat (~22 KB/dtk, ±20 menit total); di server lebih cepat;
  batas langkah 40 menit. LBS (365 MB) & DEBT_SEC (147 MB) belum diambil. Survei BI (penjualan eceran dll.) TIDAK diambil: nama file PDF
  bulanan tidak konsisten, Excel hanya sesekali (sama seperti KSEI).
- `ref/pelabuhan_portwatch.parquet`: database 2.071 pelabuhan PortWatch (koordinat, jumlah kapal per jenis, industri utama). 18 di kotak Kalimantan.
- `kumpul_laba_idx.py` (workflow `fundamental_idx.yml`, SABTU, ~15 menit): PENGUMUMAN LABA semua saham IDX dari Yahoo
  (`get_earnings_dates(limit=60)`) → `raw/laba_idx/semua.parquet` (kode, waktu_utc, waktu_wib, eps_perkiraan, eps_aktual, kejutan_pct;
  baris lama DIPERTAHANKAN) + `foto/<tanggal>` (perkiraan analis bisa direvisi). Histori umumnya sejak 2013/2014 (sebagian 2004).
  JEBAKAN: jam pengumuman Yahoo banyak berupa jam tempelan (04:00 New York) → riset pakai hari bursa ke-2 setelah TANGGAL; sebagian
  emiten lapor USD (ADRO EPS 0,01) & sebagian perkiraan beda skala (SIDO kejutan +673%) → pakai peringkat/tertil, bukan angka mentah.
- `kumpul_aksi_idx.py` (workflow `fundamental_idx.yml`, tiap SABTU, ~11 menit): AKSI KORPORASI semua saham & ETF IDX dari Yahoo
  (`Ticker.actions`) → `raw/aksi_idx/semua.parquet` (DITIMPA; kode, tanggal EX tanpa zona, dividen Rp/lembar, split rasio)
  + `raw/aksi_idx/foto/<tanggal>` (salinan mingguan, lacak revisi). 20 Nov 2026: 6.205 aksi dari 656 kode (5.888 dividen,
  368 split termasuk 27 reverse split < 1), sejak 2000. Cakupan dividen naik dari 74 kode (2003) ke 230 (2018) → data awal tidak lengkap.
  Dari 248 titik rusak harga (bagian 8) hanya 6 yang dekat tanggal split (AKRA 2007: split 27-07, lonjakan 30-07) → kebanyakan nilai basi.
  Saham tanpa split tidak punya kolom 'Stock Splits' (reindex kolom). Bisa dipakai membangun ulang harga transaksi ASLI.
- `kumpul_seki.py` (workflow `fundamental_idx.yml`, tiap SABTU): SEKI Bank Indonesia, 108 tabel Excel resmi (robots.txt BI: Allow /)
  → `raw/seki/<tanggal>/TABELx_y.xls` (HANYA tabel yang BERUBAH sejak foto sebelumnya, sidik jari sha256) + `raw/seki/indeks.parquet`
  (semua versi: tabel, judul, tanggal_ambil, sha256, ukuran, jalur; DITIMPA kumulatif). BI menimpa file tiap pembaruan → riwayat revisi
  & tanggal terbit (point-in-time) hanya ada dari foto kita, mulai 21 Nov 2026 (foto pertama: 108 tabel). File .xls lama (BIFF) →
  `pd.read_excel(..., engine="xlrd")` (xlrd di requirements). Header bertingkat (judul baris 0-1, tahun/bulan ~baris 6, data mulai ~baris 8;
  kolom tahunan lalu bulanan) → urai per tabel saat riset membutuhkan. Gagal membaca indeks yang ADA → berhenti (jangan timpa riwayat).
- `kumpul_ipo.py` (harian): IPO saham Indonesia dari e-IPO (e-ipo.co.id, sistem resmi BEI; robots.txt Allow /), HANYA halaman PUBLIK
  (halaman 'closed' & penjatahan butuh LOGIN → tidak diambil; kode berhenti kalau diminta login). `raw/ipo/daftar/<tanggal>` (foto status
  harian) + `raw/ipo/detail.parquet` (1 baris per IPO: sektor, saham ditawarkan, % dari total, PENJAMIN EMISI, jadwal book building +
  rentang harga, penawaran + harga final, penjatahan, distribusi, pencatatan, syariah). Harian: detail hanya IPO yang belum Closed/Canceled.
  `--histori` sekali (21 Nov 2026). JEBAKAN: menu filter halaman daftar memuat nama-nama status → urai teks SETELAH 'Tanggal Selesai';
  persen memakai TITIK desimal ('30.3') → pengurai `persen()` khusus. Angka kelebihan pemesanan ada di PDF 'Informasi Tambahan' (belum diurai).
  Indodax (kripto IDR) TIDAK dipakai: robots.txt `Disallow: /api`.
- `kumpul_saham_beredar.py` (workflow `fundamental_idx.yml`, SABTU, ~4 menit): HISTORI JUMLAH SAHAM BEREDAR IDX dari Yahoo
  (`get_shares_full`) → `raw/saham_beredar/semua.parquet` (kode, tanggal, saham_beredar, waktu_ambil; baris lama DIPERTAHANKAN, gagal baca
  file lama → berhenti). 21 Nov 2026: 919 kode, 194.611 titik. Cakupan PADAT baru sejak **2018Q4** (~550 kode → ~900 di 2025; sebelumnya
  ~1 titik/kode); kebanyakan kode BERHENTI ~Nov 2025 di Yahoo → foto mingguan menyambung ke depan. Cek: vs `daftar_idx` sharesOutstanding
  rasio median 1,0000 (95% dalam 1%; beberapa beda 2–5x: BJBR, BJTM, BRMS → curigai); rights issue BBRI 2022 +25% terlihat. 74 titik
  bolak-balik (TAXI, MKNT, BEKS...) → bersihkan dgn median. Angka BELUM disesuaikan split → bagi dengan faktor split `raw/aksi_idx`.
- `kumpul_alfred.py` (workflow `fundamental_idx.yml`, SABTU, ~13 menit): ALFRED (arsip vintage FRED) = SEMUA versi angka tiap seri
  `ambil_makro.py` + 12 seri rilis AS penting (GDPC1, PCE, PPI, upah, DGORDER, UMCSENT...) → `raw/alfred/vintage/<KODE>.parquet` (tanggal,
  berlaku_mulai, berlaku_sampai [NaT = masih berlaku], nilai) + `seri_rilis.parquet` + `jadwal_rilis.parquet` (tanggal terbit historis &
  TERJADWAL ke depan). 21 Nov 2026: 187 seri, 3,48 juta baris; 72 seri Indonesia (vintage umumnya sejak ~2018); 45 rilis, 39.752 tanggal
  (285 terjadwal s/d 2027-05). Seri harian > 2.000 vintage (20 seri: yield, kurs harian) DILEWATI (batas API; data pasar tidak direvisi).
  PAKAI INI untuk riset makro point-in-time (riset lama memakai angka TERREVISI). Contoh revisi nyata: NFP Jun 2025 rilis pertama 159.724 →
  158.478 ribu. JEBAKAN: level PDB riil antar vintage beda TAHUN DASAR (Apr 2020: 17.206 [dolar 2012] vs 19.078 [dolar 2017]) → bandingkan
  PERTUMBUHAN di dalam satu vintage. Jangan cetak emoji dari terminal Bash (charmap) → jalankan via PowerShell / PYTHONIOENCODING=utf-8.
- `kumpul_ojk_emisi.py` (workflow `fundamental_idx.yml`, SABTU; hanya file BARU): OJK "Ikhtisar Perkembangan Emisi Efek & Aksi Korporasi"
  MINGGUAN (ojk.go.id tanpa robots.txt; hanya halaman & lampiran yang ditautkan halaman publik Statistik Pasar Modal) → `raw/ojk_emisi/arsip/<nama>.xlsx`
  + `urai/<nama>.parquet` (format panjang: file, minggu_ke, bulan, tahun, lembar, bagian, sub_bagian, no, kolom, nilai TEKS). Isi KUMULATIF sejak awal
  tahun: IPO, right issue (PUT), EBUS/PUB obligasi-sukuk, AKSI KORPORASI (PMTHMETD/private placement, transaksi material, merger, go private,
  perubahan usaha) + tgl RUPS/efektif → deretan mingguan = point-in-time. Halaman utama hanya menautkan ~5 bulan → mulai Jul 2026 (19 file),
  HANYA KE DEPAN. 2026 s/d Nov: 90 aksi korporasi (21 PMTHMETD), 18+ right issue. Nama emiten = nama PT (bukan kode) → cocokkan dgn longName.
  Server OJK lambat (~1 menit/file dari laptop). OJK juga punya xlsx "Rata-rata Bid-Ask Spread & Turnover" mingguan, tapi hanya agregat pasar (tidak diambil).
- Batu bara HARIAN: tidak ada sumber gratis yang hidup (`MTF=F` Yahoo berhenti Des 2025; Newcastle tidak ada). Tetap bulanan IMF.

Bulanan:
- `kumpul_insider_sec.py` (workflow `insider_sec.yml`): transaksi ORANG DALAM perusahaan AS (SEC Form 3/4/5 "Insider
  Transactions Data Sets") → `raw/insider_sec/<2006q1..>.parquet`, 1 baris = 1 transaksi saham biasa. Sejak 2006q1 (sebelumnya
  tidak ada), ~60–170 ribu transaksi/kuartal, termasuk perusahaan yang sudah mati. Kolom kunci: `tanggal_lapor` (= saat
  PUBLIK, pakai ini di riset), `kode_transaksi` (P=beli pasar, S=jual, A/M/F/G = hibah/opsi/pajak/hadiah = bukan sinyal),
  `rencana_10b5_1` ("1"/"0", kosong sebelum ~2023; 61% penjualan 2026q3 terjadwal), `hubungan`/`jabatan`.
  Tautan dibaca dari halaman indeks SEC (lokasi file PINDAH sejak 2026q2). Kuartal yang sudah ada dilewati, 2 terbaru ditimpa.
  Kolom AFF10B5ONE tidak ada di arsip lama → diisi kosong. Alamat pelapor sengaja TIDAK disimpan (data pribadi).
  Tanggal salah ketik di laporan SEC ('18-JUN-0025', '01-JAN-0001') → tahun di luar 1990–2035 dikosongkan (dulu bikin
  23 kuartal gagal OutOfBoundsDatetime). Upload per 10 kuartal + tunggu 2 menit saat Hugging Face 429 (batas jumlah commit).
- `kumpul_sec.py`: SEC companyfacts.zip (~1,4 GB), 25 konsep keuangan, ~20.588 perusahaan (termasuk yang sudah mati),
  ~16 juta baris → `raw/fundamental/sec/bagian_xx` + `tiker.parquet` (CIK → kode saham).
- `kumpul_bps.py`: BPS 1.767 variabel nasional, 3 tahun terakhir, 6 permintaan paralel → `raw/bps/terbaru`.
  `--histori` → `raw/histori/bps` (18 bagian, SUDAH lengkap, jutaan baris). Format panjang:
  var_id, judul, satuan, wilayah (banyak per provinsi/kota), kategori, tahun, periode, bulan, nilai.

- `raw/histori/wiki_prices/semua.parquet` (529 MB): arsip WIKI Nasdaq Data Link (gratis, BEKU 2018-03-27), 3.199 saham AS,
  15,4 juta baris sejak 1962. Kolom: harga ASLI (buka/tertinggi/terendah/tutup) + versi `_adj`, `rasio_split`, `dividen`.
  Memuat 705 saham yang mati 2014–2017 (diakuisisi: Dell, EMC, Yahoo, Whole Foods...), TAPI 0 yang mati sebelum 2014
  (Lehman, Bear Stearns, Merrill tidak ada). Diunduh sekali dari laptop (bulk export) + `upload_satu.py`.
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
- **HARGA SAHAM AS (`bersih/saham_as.parquet`) = SURVIVORSHIP 100%**: dari 12.740 kode, 0 berhenti sebelum 2026 (Lehman,
  Bear Stearns, Twitter tidak ada). Kode dipakai ulang: `WM` = Waste Management sejak 1988 (dulu Washington Mutual).
  60% transaksi beli orang dalam SEC 2006–2018 emitennya tidak punya harga Yahoo. SEMUA riset saham AS harus melaporkan
  porsi hilang & membandingkan dengan kelompok pembanding.
  Pencarian sumber gratis (20 Nov 2026): WIKI menambal 2014–2017 saja (saham besar); Tiingo gratis = 500 saham/bulan &
  delisting condong 2017+ (2008 cuma 6); Stooq memblokir program (JANGAN ditembus); EODHD/FMP gratis terlalu kecil;
  CRSP/Norgate berbayar (~$630+/thn). KESIMPULAN: 2006–2013 TIDAK BISA ditambal gratis. Data ke depan otomatis bebas
  survivorship karena collector harian memotret ~11.800 saham AS tiap hari sejak Nov 2026.
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
- JANGAN menambah baris ke `requirements.txt` dengan `echo >>` (file tanpa pindah baris di akhir → 20 Nov 2026 'duckdb' + 'hijridate'
  menempel jadi 'duckdbhijridate' → SEMUA workflow gagal install). Tulis ulang file dengan Python, lalu cek
  `python -m pip install --dry-run -r requirements.txt` sebelum push.
- **HARGA IDX YAHOO PUNYA TITIK RUSAK** (ditemukan 20 Nov 2026 lewat pembanding indeks NASDAQ Indonesia): ~266 titik di ~98 saham
  menyimpang > 50% dari median 9 hari lalu KEMBALI (ANTM 2008-10-24 = 1757 vs ~576, nilai basi berulang bervolume 0; ELTY 2018-05 = 5000
  vs 500; MAPI/TOWR 2018-05-02 turun ~90% satu hari). IDX punya batas ARA/ARB → lonjakan > 50% yang balik = salah data.
  `bersih_idx.bersihkan()` mengosongkan titik itu (median TERPUSAT → HANYA riset historis; ≤ 2018 & 2019+ dibersihkan TERPISAH
  supaya tidak bocor). Dipakai BAWAAN di `riset_02` & `riset_12` (dan semua skrip yang meng-exec-nya); `BERSIHKAN_IDX=0` = versi lama.
  DAMPAK BESAR: lihat catatan koreksi di bagian 10. Pelajaran: satu bulan palsu (MAPI +900%) bisa menghasilkan "t 2,7".
- `continue-on-error: true` MENYAMARKAN error jadi "success". Cek DURASI langkah (API publik repo: /actions/runs/<id>/jobs):
  langkah yang selesai 1 detik = crash. 21 Nov 2026: `kumpul_aksi_idx.py` di workflow Sabtu crash karena langkahnya tidak diberi
  `HF_TOKEN` (`daftar_saham.kode_idx()` mengunduh daftar tambahan dari gudang) → SETIAP langkah yang memakai `kode_idx()` WAJIB punya `HF_TOKEN`.
- Opsi (`kumpul_opsi.py`) 21 Nov 2026 dari server: SEMUA 49 kode gagal seketika (dari laptop normal) → dulu `pd.concat([])` crash tanpa
  pesan. Sekarang: 3x coba ulang (jeda 5/15/30 dtk) + putaran kedua setelah 60 dtk + pesan error jelas. Pantau beberapa hari.
- SEKI (`seki.py`): lembar 'I.1' menaruh label TAHUN di kolom TERAKHIR tiap tahun (bukan pertama). Isi-ke-kanan biasa membuat
  Jan–Nov 2025 terbaca sebagai 2024 & MENIMPA angka 2024 (21 Nov 2026, sempat terlihat sebagai "lonjakan M1 +19%"). Sekarang kolom bulan
  dikelompokkan per blok (bulan turun = blok baru) dan tahun diambil dari label di dalam blok. Singkatan Agustus: 'Ags'/'Agt'/'Aug'.
  Cek: pertumbuhan M2 Des 2018 6,3%, 2020 12,5%, 2023 3,5% (cocok angka resmi BI). Header CAMPURAN juga ada (TABEL1_4 'Th 2002-2017':
  tanggal s/d Feb 2015 lalu nama bulan) → `peta_kolom` berjalan kiri→kanan (tanggal langsung; nama bulan menyambung, tahun +1 saat bulan turun)
  + label tahun sebagai pemeriksa. Label total kadang berspasi: 'J U M L A H' (regex `j\s*u\s*m...`).
- `bersih/harga_idx` (gabung.py) TIDAK konsisten penyesuaian dividennya untuk periode setelah histori diunduh (Adj Close Yahoo dihitung
  ulang tiap dividen baru, file harian cuma 7 hari) → riset return jangka panjang setelah Nov 2026: unduh ulang histori penuh dulu.
- Saat menulis kode Python yang berisi tiga backtick di dalam string, buat lewat variabel (mis. `"`" * 3`) supaya tampilan chat tidak rusak.

## 9. Aturan riset (WAJIB)

- **PRINSIP PENGGUNA (22 Nov 2026, teguran tegas):** proyek ini SERIUS dan butuh BERBULAN-BULAN sampai BERTAHUN-TAHUN. JANGAN cepat
  menyimpulkan. Model BELUM jadi: S2 hanya kandidat PERTAMA untuk paper trading, BUKAN "model akhir". TIDAK ADA variabel yang "dibuang":
  hasil negatif = "belum terbukti dengan uji X (desain, periode, daya uji)", bukan "tidak berguna"; setiap variabel tetap di gudang dan
  diuji ulang saat ada metode baru / data lebih panjang / digabung dengan yang lain. Teliti hal sekecil apa pun (format, satuan, spasi,
  tipe data, tanggal terbit, revisi, tahun dasar). Pakai cara berpikir LINTAS ILMU (Renaissance merekrut matematikawan, fisikawan,
  ahli sinyal/pengenalan suara, statistikawan, ilmuwan komputer — bukan ekonom): pemrosesan sinyal, model rantai Markov tersembunyi,
  teori informasi, statistik nonparametrik, analisis jaringan, NLP, ekologi/klimatologi. Baca banyak paper dari berbagai bidang
  sebelum merancang; catat bacaan di `docs/`.

- Tulis dugaan + alasan logis SEBELUM melihat data (hindari HARKing & data mining).
- Data latih s/d **2018-12-31**; data uji **2019+ DIKUNCI**, dibuka sekali di akhir (`--buka-uji`), hanya untuk strategi yang lolos di data latih.
- Ambang signifikansi **|t| > 3**. Hitung berapa banyak uji yang sudah dilakukan (multiple testing).
- Uji di instrumen yang **BISA dibeli** (bukan indeks). Selalu potong biaya transaksi (asumsi IDX 0,4% bolak-balik).
- Uji kode riset dulu dengan data tiruan yang diberi pola tersembunyi: program harus menemukan pola itu kembali.

## 10. Status riset & rencana berikutnya

### ⏰ DAFTAR PERIKSA TERTUNDA (cek di awal tiap sesi; coret/hapus yang sudah selesai, tambahkan yang baru)
- [x] ~~`spread_idx.yml` run pertama~~ → SELESAI 23 Nov 2026: 4 file (`2026-11-23_0330/0510/0827/0927`), 838 saham, bid&ask sah 734–811,
  spread median 0,91–1,00% (semua saham). TEMUAN: (1) jadwal GitHub TERLAMBAT 58–86 mnt → foto ke-4 jatuh 16:26 WIB (kuotasi 16:14 = SETELAH
  tutup) → cron digeser ke 09:17/10:37/13:31/14:11 WIB (aman s/d ~90 mnt terlambat); (2) kuotasi Yahoo tertunda ~10–15 mnt (`waktu_kuotasi`).
  ANALISIS NANTI: pakai `waktu_kuotasi` (bukan waktu_ambil) & buang kuotasi di luar sesi (09:00–12:00, 13:30–15:50; Jumat 09:00–11:30, 14:00–15:50).
- [x] ~~Jadwal BARU `spread_idx.yml`~~ → SELESAI: 8 foto 24–25 Nov, kuotasi 95–99% di dalam sesi (09:58 s/d 15:25 WIB). Opsi normal 22–25 Nov.
- [x] ~~Aturan BERHENTI S2~~ → DITETAPKAN 26 Nov 2026 sebelum paper trading (pengguna menyerahkan ke Claude; boleh diubah pengguna): dinilai dari paper
  S2 PENUH; kuning 12 bln < −1% (periksa), merah 24 bln < −0,5% (stop tambah uang), batas keras −50% dari puncak (jual semua). Detail di docs/.
- [ ] **SEBELUM uang sungguhan**: pengguna menegaskan sanggup kehilangan 50% modal; kalau tidak, modal dikecilkan (bukan batasnya diketatkan).
- [x] ~~Harian 23 Nov dgn batas baru~~ → sukses 81 mnt (batas 150), Wikipedia 34 mnt (batas 45), opsi normal hari ke-2 (255 dtk).
- [x] ~~`harian.yml` langkah BARU JISDOR / put/call / EmitenNews~~ → SELESAI 22 Nov 2026 (run 44971739609): ketiganya sukses
  (6/5/6 dtk), file 22 Nov ada & isinya benar (JISDOR 43 hari s/d 20 Nov Rp18.278; put/call 7 hari; EmitenNews 2.000); 37/37 folder
  harian punya file; validasi hijau (langkah validasi TANPA continue-on-error). Server BI & CBOE menerima GitHub.
  TEMUAN: job harian ~76 menit (bukan 35) dgn batas lama 90 → MEPET; langkah Wikipedia per saham ~35 mnt (429 Wikimedia) → batas job
  dinaikkan ke 150 & langkah Wikipedia dibatasi 45 mnt (22 Nov 2026). Cek run 23 Nov: job sukses & durasi wajar.
- [ ] **Jumat 27 Nov – Senin 30 Nov 2026**: `reksadana_ojk.yml` (12:37 WIB) run pertama → cek server OJK menerima GitHub (callback 'All'),
  `raw/reksadana_ojk/indeks.parquet` bertambah ~50–60 bulan/run; histori 166 bulan lengkap ~3 run; job < 70 mnt. Gagal dari server → jalankan dari laptop.
- [ ] **Sabtu 28 Nov 2026** (setelah ~11:45 WIB): `estimasi_idx.yml` run pertama → file `raw/estimasi_idx/2026-11-28.parquet`, ≥ 100 saham berisi.
- [ ] **Sabtu 28 Nov 2026** (setelah ~13:00 WIB): `fundamental_idx.yml` → langkah BARU saham beredar, ALFRED (~13 mnt), OJK emisi
  (hanya file baru) → cek durasi tiap langkah & file baru di HF (`raw/saham_beredar`, `raw/alfred/vintage`, `raw/ojk_emisi/arsip`);
  job total < 240 menit.
- [ ] **Jumat 27 Nov 2026** (setelah ~08:40 WIB): `harian.yml` langkah BARU kepemilikan SBN → cek sukses & di HF ada `raw/kepemilikan_sbn/harian.parquet`
  + `indeks.parquet` (run pertama dari laptop 26 Nov TERPUTUS tanpa WARP: 38 file arsip sudah di HF, harian & indeks BELUM; run server mengunggah
  ulang semuanya dalam SATU commit). Cek: ~3.200 tanggal, non-residen terakhir ~Rp930 T, server DJPPR menerima GitHub.
  JUGA langkah BARU MPOB: `raw/harian/mpob/2026-11-27.parquet` ~280 sel (server MPOB menerima GitHub?).
  JUGA langkah BARU IndONIA: file `raw/harian/indonia/2026-11-27.parquet` (~2.400 hari) & `kurva_pasar_uang` ada; kalau sukses → tambah ke validasi_harian.
  JUGA langkah BARU operasi moneter BI: file `raw/harian/operasi_moneter/2026-11-27.parquet` ada (~30 operasi) = server BI menerima postback dari GitHub.
- [ ] **Pantau beberapa hari**: `kumpul_opsi.py` dari server (21 Nov semua 49 kode gagal; 22 Nov PULIH: 34.649 kontrak, 426 dtk) &
  Kontan RSS (403 dari server, sudah diketahui). Centang setelah ~5 hari opsi berturut-turut normal.
- [ ] **Senin 30 Nov / Selasa 1 Des 2026**: paper trading — pilihan akhir Nov tercatat SEBELUM beli (`dicatat_sebelum_beli`=True) untuk
  s2, s2v, ml, s2p; beli tutup 1 Des. Cek log `paper_trading.yml` 30 Nov 22:41 UTC.
- [ ] **Awal Des 2026 – akhir Jan 2027**: latih model `ml` 2027 (lihat bagian 5: unduh ulang histori penuh `ambil_semua_idx.py` dulu,
  lalu `python private/paper_ml.py --latih 2027`, `python simpan_private.py`) SEBELUM sinyal akhir Jan 2027.
- [ ] **Pertengahan Des 2026** (≥ 3 minggu foto spread jam bursa): kalibrasi ulang model biaya B (faktor 1,2 × tick) → pra-registrasi dulu.
- [ ] **Tiap awal bulan (mulai Jan 2027)**: laporan paper trading untuk pengguna + cek syarat Fase 1 & aturan BERHENTI di
  `docs/rencana_eksekusi_s2.md` (ditetapkan 22 Nov 2026 SEBELUM hasil paper trading ada; JANGAN diubah setelah melihat hasil).
  Fase 1 (uang kecil) paling cepat Mar 2027.
- [ ] **PRIORITAS RISET BERIKUTNYA (#52, keputusan 22 Nov 2026 atas teguran pengguna): MESIN PENYARING MASSAL "data aneh"** —
  variabel yang dulu gagal sebagai timing 1 keranjang (cuaca, alam, iklim, BPS 1.767 variabel, FRED, SEKI, pangan, komoditas, kurs...) diuji
  ULANG secara PENAMPANG: kepekaan tiap saham (beta bergulir thd variabel, data masa lalu saja) × perubahan variabel terbaru = skor per saham.
  Wajib: point-in-time (jeda terbit konservatif; ALFRED utk FRED), koreksi uji ganda (Benjamini-Hochberg/ambang t ketat), saring di 2005–2018,
  validasi ulang 2019–2022, penyintas digabung lalu dibandingkan dgn S2. Langkah 1 = tabel bulanan terpadu semua variabel (point-in-time).
  Sesudahnya: #53 S2 dgn porsi menurut volatilitas → SELESAI 26 Nov 2026 (❌ belum terbukti, daya uji nol; lihat entri #53).
  **POSISI KERJA (serah terima 22 Nov 2026, kredit pengguna hampir habis):**
  - SELESAI: `panel_bps.py` → `data/olah/panel_bps.parquet` (6,67 jt baris, 644 rb seri; cukup utk latih 2005–2018: M 1.083 seri/26 var,
    Q 4.189/43, Y 13.707/262). Aturan: periode di-strip ('Februari ' berspasi 9.006 baris), proyeksi > 2026 dibuang, jeda terbit M+2/Q+3/S+3/Y+12.
    BUG DIPERBAIKI: label wilayah BPS berjenjang & berulang ('1.1 Pertanian' di bawah Bahan Baku/Konsumsi/Modal = kode 11/21/31) → 57 variabel
    (PDB triwulanan per pengeluaran, IHPB, ekspor per pelabuhan...) tercampur. `kumpul_bps.py` kini menyimpan kode_wilayah/kode_kategori/
    kode_periode + mode `--ulang ID,ID` → `raw/histori/bps/perbaikan_kode.parquet` (365.936 baris = jumlah lama, 0 dobel; SUDAH di HF);
    panel memakainya otomatis. `var_id` diseragamkan teks (dulu campur int/str).
  - SELESAI (23 Nov 2026): `panel_fred.py` → `data/olah/panel_fred.parquet` (207 seri, 95.832 baris: M 109, harian→bulanan 83, Q 15;
    kolom bulan, tersedia, nilai, pit, tumbuh1, tumbuh12). POINT-IN-TIME: jeda normal seri = median jeda rilis 24 obs TERBARU; obs dgn jeda
    <= max(2×normal, normal+45 hr) = rilis pertama ALFRED (pit=True, 60% titik 2005–2018), selain itu nilai revisi + jeda konservatif
    max(2×normal, 90/180/450 hr) (pit=False; seri Indonesia/IMF sebelum ~2015 = artefak arsip ALFRED). PERTUMBUHAN REAL-TIME: nilai t & t−L
    dari VINTAGE YANG SAMA (rilis pertama PDB AS 2008Q4 = dolar 2000, 2013Q3 = dolar 2009 → tanpa ini pertumbuhan lompat palsu).
    Cek manual: PDB AS 2008Q4 −0,97% q/q (advance 30 Jan 2009 ✓), CPI Jun 2022 +8,6% yoy rilis 13 Jul 2022 ✓, 0 titik tersedia sebelum periodenya.
    BUG DITEMUKAN & DIPERBAIKI: jeda normal dari obs ≥ 2019 membuat TIC Mar 2015 'tersedia' Apr 2022. KOREKSI 26 Nov 2026: 'TIC ~7 bulan' SALAH =
    artefak (arsip ALFRED TIC baru mulai 2026-05-18, obs lama isi-mundur). Jeda nyata 77 hari sejak awal bulan (~6–7 minggu) → asumsi 2 bln riset #19
    WAJAR, keraguan DICABUT. Jeda normal kini membuang obs isi-mundur (28 seri TIC terdampak).
  - SELESAI (23 Nov 2026): `panel_alam.py` → `data/olah/panel_alam.parquet` (119 seri: cuaca 15 kota ×6, titik api MODIS/VIIRS ×3 wilayah,
    iklim ONI/SOI/MEI/DMI + anomali Nino mingguan, geomagnetik/matahari ×5, gempa ×4; 113 seri ≥ 120 bln latih). pit=False SEMUA (reanalisis/
    arsip revisi). Jeda: cuaca +7 hr, ONI +2 bln+10 hr (bulan tengah), SOI/MEI +1 bln+10 hr, DMI +6 bln, Nino mg +7 hr, matahari +5 hr, gempa +2 hr,
    api +7 hr. Bulan BERJALAN dibuang. Cek kewajaran lolos (gempa Aceh/Nias/Bengkulu/Biak, api 2015/2006/2019, banjir Jakarta 2002/2020,
    ONI 2015/1997/2026, DMI 1997/2019). Dugaan "bintik matahari modern harus tinggi" SALAH: siklus 19/21/22 memang lebih kuat. Sudah di HF `olah/`.
  - SELESAI (26 Nov 2026): `panel_pasar.py` → `data/olah/panel_pasar.parquet` (302 seri: Yahoo 98, World Bank 87, kurs 43, CBOE 32, LME 18, put/call 18,
    FF 6; cek kewajaran di docstring). Beda biaya di cek potong #46 (0,95 vs 0,98%) TERBUKTI karena aksi korporasi ikut terpotong (aksi utuh → 0,95% identik).
  - KOREKSI panel BPS (26 Nov 2026): (1) BOCOR kecil diperbaiki: Sakernas Feb/Ags tercatat 'M' (diketahui akhir Apr/Okt) padahal rilis 5 Mei /
    5–6 Nov (dicek di bps.go.id); kemiskinan Maret rilis Juli → 58 variabel 'bulanan' palsu kini Q/S dari ISI (<= 4 bulan kalender); jeda kini
    M+2, Q+4 (PDB +3), S+5, Y+18. (2) `seri` kini memuat frek (dulu bulanan & tahunan bernama sama, 18 rb seri). (3) Angka "Q 4.189 seri / 43 var"
    di atas SALAH HITUNG (ikut menghitung baris tahunan); yang benar Q 635 seri/13 var, M 1.116/32, S 299/8, Y 13.447/250 (≥ titik minimum latih).
  - SELESAI (26 Nov 2026): `sambung_bps.py` → `data/olah/panel_bps_sambung.parquet` (205 seri: tumbuh1, tumbuh12, tersedia). Aturan ditetapkan
    SEBELUM melihat hasil: seri lama dipakai s/d akhir hidupnya lalu seri baru (angka dasar baru utk masa lalu belum ada saat itu); pertumbuhan
    dihitung di dalam tiap seri; disambung bila tumpang tindih >= 6 titik & korelasi pertumbuhan >= 0,7. HASIL: 202 disambung (NTP provinsi 181,
    PDB pengeluaran riil/nominal 18: PDB total kor 0,96/0,94, PMTB, ekspor, impor, konsumsi pemerintah; sektor 3), 102 GAGAL (NTP nasional 4
    kor 0,42–0,57; NTP provinsi 89; konsumsi RT kor 0,41/0,44 walau beda median cuma 0,3 pp — korelasi lemah utk seri yang sangat mulus = ukuran
    uji kurang tepat, TIDAK diubah setelah melihat hasil; konstruksi kor −0,07 = definisi berubah). Yang gagal TETAP ada per segmen di panel_bps.
    IHPB 2019-11 → 2019-12 tanpa tumpang tindih = digabung dgn CELAH 12 bln untuk tumbuh12 (tidak dijembatani). Kelompok IHK tidak disambung (7 → 11 kelompok).
  - SELESAI (26 Nov 2026): `panel_lain.py` → `data/olah/panel_lain.parquet` (2.933 seri, 441 rb baris; 651 seri cukup panjang di latih):
    COT 1.366 (per KODE CFTC: net spekulan/komersial/OI legacy, managed money, leveraged funds & asset manager; rilis Selasa+6 hr, penutupan
    pemerintah 2013/2018-19/2025 = rilis susulan konservatif; net/OI > 1 = salah sumber → kosong), BIS 350 (semua seri Indonesia + GLI global +
    suku bunga kebijakan semua negara + aset bank sentral US/XM/JP/CN/GB; jeda 0–7 bln), DTS 4 (TGA & kas operasi akhir/rata bulan), lelang
    Treasury 26 (bid-to-cover & porsi indirect per tenor, nominal saja), Wikipedia 20, pangan PIHPS 1.167 (4 jenis harga × 35 wilayah × komoditas).
    JEBAKAN DTS: sejak 2022-04-18 saldo TGA ada di kolom `open_today_bal` (close kosong); 2021-10..2022-04 akun 'Treasury General Account (TGA)'.
    JEBAKAN BIS: kolom `collection` = DIMENSI di WS_XRU (rata-rata vs akhir periode), bukan atribut. Sudah di HF `olah/`.
  - SELESAI (26 Nov 2026): `panel_seki.py` → `data/olah/panel_seki.parquet` (7.725 seri: M 6.739, Q 986; 1.162 cukup panjang di latih)
    dari 87 dari 108 tabel SEKI. Lembar periode disambung HANYA lewat ANGKA (bulan tumpang tindih sama ≤ 0,5%, pasangan saling tunggal;
    baris kembar identitas dipasangkan menurut urutan) karena nama baris & susunan berubah antar periode; tanpa tumpang tindih = segmen.
    Cek: M2 yoy Des 2018/2020/2023 = 6,3/12,5/3,5% (resmi), kredit total 2020 −2,6%. TERLEWAT 21 tabel berheader kuartalan/tahunan
    (IV.1–3 APBN, V.1–V.8 neraca pembayaran, V.39 PII, VI.1–5 ULN, IX.1–4) → pengurai kuartalan NANTI. CATATAN: III.3 versi baru = volume/
    nilai transaksi & indeks BEI, BUKAN kepemilikan asing (kepemilikan asing hanya lembar lama 1990–2003). Sudah di HF `olah/`.
  - HASIL (26 Nov 2026): #52 per-variabel ❌ 0 lolos BH dari 10.766 uji (|t|>3: 48 vs acak 29, kebanyakan kredit bank SEKI berkorelasi;
    terbesar kredit pengangkutan & komunikasi t +4,0); #52b gabungan ❌ IC +0,0035 t +0,27 (pit saja −0,33). Data uji TIDAK dibuka.
    Bug kebocoran (pilihan log/selisih melihat data > 2018) ditemukan --potong-data & diperbaiki. JEBAKAN RAM: 2 proses #52b paralel
    di laptop 7,5 GB → Memory Compression, macet → jalankan SENDIRIAN (panel mentah dilepas setelah Z dibangun).
    Langkah berikutnya yang masuk akal: desain TERARAH dgn mekanisme jelas (bukan penyaring buta), horizon lain, atau #53 (S2 + vol scaling).
  - (riwayat) MESIN PENYARING #52 (`riset_52_penyaring.py`, pra-reg `docs/prareg_52_penyaring.md` 2558b44 + hasil tes kode
    f9979bb) & GABUNGAN #52b (`riset_52b_gabungan.py`, pra-reg `docs/prareg_52b_gabungan.md` b37d712). Tes kode: #52 kosong terkalibrasi;
    daya uji per-variabel RENDAH (IC 0,06 → t ~2,5; ambang BH ~4,5). #52b: jalur "berita persisten" terdeteksi kuat (t 8) tapi itu sebagian
    ARTEFAK pembuat data palsu (rata-rata bulanan berautokorelasi; Working 1960); dgn berita acak (`--z-acak`) reaksi tertunda IC ≤ 0,06
    TIDAK terdeteksi (t −0,9; versi bobot disusut James-Stein 1−4/t² juga −1,3). Bendera tes: --tes-kosong/--tes-tiruan/--satu/--lemah/
    --tanpa-gamma/--z-acak/--cepat/--potong-data. Run asli #52 penuh ~30 mnt → `data/olah/riset52_latih.parquet`.
  - BELUM: (a) ~~sambung seri beda tahun dasar~~ SELESAI (lihat atas);
    (b) panel sumber lain: FRED (pakai ALFRED rilis pertama, tersedia = tanggal rilis), cuaca 15 kota, iklim (ONI jeda 1 bln, DMI 6 bln!),
    alam (Kp/Ap, bintik matahari), gempa, titik api, LME, harga global, kurs ECB/JISDOR, CBOE, Fama-French (jeda 2), COT, World Bank,
    SEKI (perlu urai per tabel), BIS, DTS, lelang AS, Wikipedia; (c) mesin penyaring (beta bergulir saham × variabel; uji tiruan dulu);
    (d) ~~upload panel~~ SELESAI 23 Nov 2026: `data/olah/` (panel_bps, panel_fred + ringkas) → HF `olah/` (katalog INFO "olah").
    SETIAP panel/olahan baru WAJIB di-upload (`python upload_satu.py data/olah`) — prinsip pengguna: data JANGAN hanya di laptop.
  - INFO OPSIONAL utk pengguna (butuh email pengguna → keputusan pengguna): webinar GRATIS Stefan Jansen "Open-Source Tools for ML Trading
    Research" Rabu 25 Nov 2026 16:00 UTC (23:00 WIB), rekaman dikirim ke pendaftar (link di README repo machine-learning-for-trading);
    juga "ML for Trading 3rd Ed." 23 Des 2026 & "Build ML for Trading Strategies with AI Agents" 21 Jan 2027 (16:00 UTC).
  - METODE LINTAS ILMU yang harus dicoba (bukan hanya regresi/uji faktor): analisis spektral & wavelet (siklus), Hidden Markov Model
    (keadaan pasar; Baum-Welch = akar Renaissance), mutual information / transfer entropy (hubungan non-linear), uji permutasi & bootstrap,
    jaringan korelasi/lead-lag saham (networkx), korelasi silang berjeda & Granger/CCM (iklim→saham), NLP isi berita. Tinjau literatur
    tiap bidang dulu, catat di `docs/`.
  - BACAAN (23 Nov 2026): `docs/bacaan_alat_dan_repo.md` — penilaian 9 plugin (graphify, OmniRoute, ponytail, Agent Reach, Understand
    Anything, last30days, career-ops, Headroom, REA: TIDAK ada yang disarankan dipasang; OmniRoute/Agent Reach/REA dihindari) + peta bab
    *Machine Learning for Trading* ed.3 (BH-FDR & Deflated Sharpe Bab 7; Kalman/wavelet/GARCH/HMM Bab 9; PCMCI/Double ML Bab 15; biaya Bab 18)
    + pilihan awesome-quant (tsfresh, purgedcv, pit-release-gate, Carver). Pakai sbg acuan #52/#53 & kalibrasi biaya.
  - ALAT gratis yang ditawarkan ke pengguna (belum diputuskan): Google Colab (komputasi lebih kuat, akun Google, tanpa kartu), Jupyter
    Notebook (eksplorasi yang bisa dilihat langkah demi langkah), pustaka hmmlearn/PyWavelets/networkx.
  - RENCANA 4 TAHAP: (1) fondasi data panel terpadu & bersih → (2) eksplorasi multi-metode → (3) model gabungan banyak sinyal lemah →
    (4) validasi bertahun-tahun lewat data maju & paper trading. Pengumpulan data otomatis tetap jalan.
- [ ] **Histori operasi moneter BI** (kode SIAP 27 Nov 2026, daftar mulai 2019): pengguna menjalankan workflow MANUAL `histori_operasi_moneter.yml`
  (Actions → Run workflow; ~3–4 jam) → cek `raw/histori/operasi_moneter/2019..2026.parquet` di HF, log 'jumlah tautan beda dgn label' & 'tanpa tabel'.
  Terputus → jalankan ulang (tahun yang sudah ada dilewati).
- [ ] Ide tersimpan (perlu pra-registrasi sendiri): fitur "pembagi dividen" (#47/#48) untuk model penampang; riset kejutan rilis makro
  (ALFRED rilis pertama + Kalshi, setelah data Kalshi beberapa bulan); #10 volatilitas tersirat opsi (data opsi beberapa bulan).

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
- **Riset #11 SELESAI: pembelian orang dalam (SEC Form 4) → saham AS** (`riset_11_orang_dalam.py`). TIDAK MEYAKINKAN.
  Desain di-commit SEBELUM data lengkap (1a1d878, 10:40 WIB 20 Nov 2026). P oleh Director/Officer, bukan 10b5-1, bulan lapor;
  kode dicek via harga beli vs Yahoo (faktor split). Semesta: harga ≥ $5, nilai transaksi ≥ $1 juta/hari. Latih 2006-02..2018-11.
  - Angka utama: U1 H=1 t 1,7 | U2 H=3 +0,37%/bln t 3,1 | U3 H=6 +0,39% t 3,6 | U4 H=3 BERSIH +0,28% t 2,3 (gagal).
    Paruh 1 t 1,4, paruh 2 t 3,7. Cek kode ketat H=3 t 3,1.
  - TAPI: portofolio JUAL orang dalam juga +0,20%/bln (t 2,6) → bias bersama. BELI−JUAL (diagnosis): H=3 +0,17% t 1,4,
    H=6 +0,14% t 1,6. Survivorship berat & ASIMETRIS: beli tanpa harga Yahoo 53–80%/thn vs jual 38–60%.
  - Lolos `--tes-kosong`/`--tes-tiruan` (pembuat data tiruan sempat meleset 1 bulan; program riset benar tidak menangkap bulan
    sebelum lapor). Hapus data 2019+ → IDENTIK. Data uji TIDAK dibuka.
  - Kesimpulan: belum bisa dipercaya dengan data harga sekarang. Ulangi kalau sudah ada harga AS yang memuat saham delisting.
- **Riset #12 SELESAI: gabungan sinyal IDX** (`riset_12_gabung_sinyal.py`). Uji penentu GAGAL, tapi ada KANDIDAT.
  4 sinyal dari literatur (S1 momentum 12-1, S2 dekat puncak 52 minggu = harga/tertinggi 250 hari, S3 volatilitas 120 hari
  rendah, S4 bukan 'saham lotre' = max return harian 21 hari rendah), z-skor, bobot SAMA. Desain sama dengan riset #2.
  - IC: S1 t 5,0 | S2 t 6,6 | S3 t 4,4 | S4 t 1,7 | GABUNGAN t 7,0. Korelasi S3–S4 0,54, S1–S2 0,38.
  - U6 (penentu, ditetapkan di depan): beli 20% teratas GABUNGAN bersih +0,66%/bln t 2,1 → GAGAL (lebih buruk dari
    momentum saja; S3/S4 mengencerkan). Pelajaran: IC tinggi ≠ strategi beli-saja bagus.
  - KANDIDAT (angka ini BUKAN uji yang ditetapkan di depan): S2 beli 20% teratas bersih +1,35%/bln t 3,9 (ganti 49%/bln).
    Cek ketahanan (ditambahkan SETELAH lihat hasil): potong ±30% t 4,5; biaya 0,8% t 3,4; TAPI 50 saham paling likuid
    t 2,4 dan paruh kedua (2012–2018) lemah (t 1,5; likuid: −0,6). Efek terutama di saham kurang likuid & melemah.
  - Lolos `--tes-kosong`/`--tes-tiruan`; hapus data 2019+ → IDENTIK. Data uji BELUM dibuka.
  - RENCANA UJI S2 DI DATA UJI (ditetapkan 20 Nov 2026 SEBELUM dibuka; JANGAN diubah setelah melihat hasil):
    strategi persis seperti di latih (semesta riset #2, S2 = harga/tertinggi 250 hari, beli 20% teratas, bulanan,
    biaya 0,4%, dibanding semesta). Periode: semua bulan 2019+. LOLOS kalau rata-rata bersih > 0 DAN t > 2
    (sampel uji lebih pendek). Laporkan juga versi 50 saham paling likuid & biaya 0,8% (informasi, bukan kriteria).
    Data uji untuk ide ini HANYA dibuka SEKALI; kalau gagal, S2 dibuang sebagai strategi tunggal.
  - **DATA UJI DIBUKA 20 Nov 2026 (`riset_12b_uji_s2.py`, HANYA S2; sinyal lain & gabungan TIDAK disentuh): ✅ LOLOS.**
    2019-01..2026-09 (93 bln): bersih +1,43%/bln, t 3,4, ~+18,6%/thn, menang 70% bulan, IC t 5,3. Biaya 0,8%: t 3,1.
    Per tahun: 2019 +1,34% | 2020 −1,19% (COVID) | 2021 +3,08% | 2022 +2,50% | 2023 +0,92% | 2024 +1,92% | 2025 +1,19%.
    PERINGATAN BESAR: versi 50 saham paling likuid +0,11%/bln t 0,2 = efek HANYA ada di saham kurang likuid →
    risiko nyata: spread/tick > asumsi, saham terkunci ARA (tidak bisa dibeli), kapasitas kecil, survivorship IDX
    (daftar saham = yang masih tercatat; saham kecil paling sering delisting). BELUM siap uang sungguhan.
  - **Uji eksekusi realistis (`riset_12c_eksekusi.py`, strategi TIDAK diubah):** spread Corwin-Schultz saham pilihan
    median 0,69% (latih) / 0,89% (uji); tick/harga 0,44%. Biaya nyata ~0,62%/bln (bukan 0,16–0,20%). Terkunci ARA saat
    beli 0,1–0,2% (bukan masalah); ARB saat jual 0,6–1,5%. BERSIH REALISTIS: latih +0,87%/bln t 2,5 (~+11%/thn),
    uji +0,99%/bln t 2,4 (~+12,6%/thn). Kapasitas (5% nilai transaksi harian): median Rp 1,7–3,4 miliar per transaksi.
    Kesimpulan: konsisten untung di 2 periode terpisah tapi t ~2,5 setelah gesekan nyata = kandidat, bukan jaminan.
  - **KOREKSI BIAYA (21 Nov 2026, biaya B = 0,4% + 1,2 × tick historis/harga asli; aturan S2 TIDAK diubah):** latih 2005–2018
    +0,44%/bln t 1,1 (≈ lama, tick dulu besar) | **uji 2019–2026 +1,22%/bln t 2,9 (~+15,6%/thn, menang 69%; lama +1,00% t 2,4)**;
    semesta uji ~40 saham/bulan vs ~20 dulu. = perkiraan TERBAIK untuk paper trading. Kalibrasi 1,2 akan dicek ulang dgn foto jam bursa.
    LINIMASA S2 per tahun (biaya B, bersih/bln): 2005–2010 naik-turun (2008 +4,6%, 2009 −4,8% crash) | 2011–2017 KERING (−0,55..+0,41%) |
    2018 +2,0%, 2019 +1,2%, 2020 −1,4% (COVID) | 2021–2026 +0,7..+2,9% (2020–2026: +1,22% t 2,6). Bersamaan dgn ledakan investor ritel
    (SID KSEI: 12,17 jt akhir 2023 → 14,87 jt 2024 → 20,13 jt Des 2025 → 30,30 jt Agu 2026 [1 sumber]) & semesta 22 → 54 saham.
    KORELASI WAKTU, bukan bukti sebab. RISIKO: kalau rezim berbalik, S2 bisa "kering" bertahun-tahun seperti 2011–2017.
  - LANGKAH BERIKUTNYA: PAPER TRADING MAJU (catat pilihan S2 tiap akhir bulan, pantau hasil nyata 6–12 bulan).
    JANGAN memodifikasi S2 lalu menilainya di 2019–2026 (data uji S2 sudah terpakai). Ide pengurang biaya (mis. aturan
    penyangga/buffer, tahan 2–3 bulan) hanya boleh dirancang di data LATIH lalu dinilai lewat paper trading.
- **Riset #13 SELESAI: S2 hemat biaya** (`riset_13_s2_hemat.py`, HANYA data latih). Aturan keputusan ditetapkan di depan:
  varian jadi paper trading kedua hanya kalau rata-rata bersih ≥ V0 DAN t > V0.
  - V0 S2 asli: 20 saham, putar 50%/bln, biaya 0,63%, bersih realistis +0,92%/bln t 2,7 (paruh 3,3 / 0,8) [cocok #12c].
  - V1 penyangga (masuk 20% teratas, jual kalau keluar 40%): 29 saham, putar 28%, biaya 0,35%, bersih +0,84% t 3,3 (3,3/1,3).
  - V2 tahan 3 bulan (3 kelompok bertumpuk): 34 saham, putar 22%, biaya 0,28%, bersih +0,81% t 2,8.
  - KEPUTUSAN: ❌ tidak ada (V1 t lebih tinggi tapi rata-rata sedikit lebih rendah). S2 asli tetap satu-satunya paper trading.
    Aturan TIDAK diubah setelah melihat hasil. Pelajaran: kriteria keputusan sebaiknya SATU ukuran (mis. t) agar tidak ambigu.
- **Riset #6 SELESAI: posisi spekulan COT → 21 ETF komoditas/mata uang/obligasi/S&P** (`riset_06_cot.py`). HASIL NEGATIF.
  Dua teori bertentangan (tekanan lindung nilai = positif; contrarian = negatif) → semua uji dua arah. Sinyal = persentil
  (noncomm long−short)/OI dalam 156 minggu (laporan legacy), dipakai setelah pasti terbit. Pasar dicocokkan via KODE CFTC
  (nama berganti: mis. 'NATURAL GAS' → 'NAT GAS NYME' Feb 2022; mencocokkan nama = kehilangan 30 thn data).
  - Latih 2006-04..2018-10 (151 bln, median 21 ETF): U1 IC −0,035 t −1,6 | U2 atas−bawah −0,21%/bln t −0,7 |
    U3 beli sepertiga atas bersih −0,14% t −0,8 | U4 ekstrem ≥0,9 vs ≤0,1 (4 minggu) −0,43%/bln t −1,5. Semua condong
    contrarian tapi tidak ada yang mendekati 3. Paruh: IC t −1,5 / −0,7.
  - ETF kopi/kakao/kapas/ternak (JO, NIB, BAL, COW) sudah ditutup → hilang (survivorship).
  - Lolos `--tes-kosong`/`--tes-tiruan`; hapus data 2019+ → IDENTIK. Data uji tidak dibuka.
- **Riset #14 SELESAI: lonjakan perhatian Wikipedia → saham IDX** (`riset_14_perhatian.py`). HASIL NEGATIF (daya uji rendah).
  Lonjakan = log(pembaca id+en) − log(median 8 minggu / 6 bulan sebelumnya). Semesta = punya artikel & lolos saringan riset #2
  (median 59 saham, umumnya saham besar). Latih 2015-08..2018-12 (164 minggu, 32 bulan).
  - U1 (H1 tekanan beli) IC mingguan +0,011 t 0,9 | U2 beli 20% lonjakan: kotor +0,20%/mg, bersih −0,02% t −0,2 (ganti 55%/mg)
    | U3 (H2 balik) IC bulan→3 bulan −0,033, t +0,1 (hanya 11 titik tanpa tumpang tindih). Arah H1 sesuai literatur tapi lemah.
  - Lolos `--tes-kosong`/`--tes-tiruan` (pola → IC t 6,6; tapi U2 bersih tetap negatif karena ganti 79%/mg); hapus 2019+ → IDENTIK.
  - Catatan: perhatian Wikipedia paling berguna untuk saham kecil, tapi saham kecil jarang punya artikel. Uji ulang setelah
    data maju menumpuk (sinyal perhatian bisa jadi komponen model gabungan, bukan strategi sendiri).
- **Riset #8 SELESAI: filter rezim stres untuk S2** (detail di `private/`, ringkasan di sini). HASIL: filter TIDAK dipakai.
  Stres = VIX ≥ 25 di akhir bulan (19 dari 155 bulan latih; cek STLFSI4 > 0). Keunggulan S2 vs semesta TETAP ada sesudah
  bulan stres (+1,01% vs +0,91% tenang); pindah ke kas saat stres tidak membantu (t −0,3; versi STLFSI t −1,9).
  Pelajaran: S2 tidak perlu dimatikan saat krisis. Pra-registrasi dicatat & dicadangkan sebelum dijalankan.
- **Riset #15 SELESAI: efek Ramadan & libur Lebaran** (`riset_15_ramadan.py`). HASIL NEGATIF (daya uji rendah).
  Keranjang 30 saham paling likuid (riset #4), return harian, latih 2002-05..2018-12 (17 Ramadan). Tanggal Ramadan dari pustaka
  `hijridate` (Umm al-Qura, bisa beda 1 hari dari penetapan RI); libur Lebaran = jeda hari bursa terpanjang ±12 hari dari 1 Syawal.
  - U1 Ramadan +0,076%/hari vs bukan Ramadan +0,085% (t −0,1) | U2 2 hari sebelum libur Lebaran +0,42%/hari vs biasa +0,09%
    (t +1,7, searah dugaan, belum lolos) | U3 abnormal Ramadan per tahun bersih −0,51% (t −0,3; 2003 −18% NYATA: IHSG −2,8%
    selama Ramadan padahal setahun +63%).
  - Data tiruan: pola +0,15%/hari (≈ +3%/Ramadan) hanya t 2,8 (U1) / 1,9 (U3) → efek kalender butuh puluhan tahun untuk terbukti.
  - Hapus data 2019+ → IDENTIK. Data uji tidak dibuka. Catatan: pra-Lebaran bisa diuji ulang setelah data uji makin panjang.
- **Riset #16 SELESAI: El Nino → saham sawit IDX vs pasar, 6 bulan** (skrip di `private/`). HASIL NEGATIF.
  ONI dipakai dengan jeda konservatif (berpusat m−2). Sawit (AALI/LSIP/SGRO/SIMP/BWPT) − pasar: −2,5% per +1 ONI (t −0,2);
  saat El Nino −1,2% vs +3,3% (t −0,1). Mekanisme ONI → harga CPO searah teori (+5,1% per +1 ONI) tapi lemah (t +0,5).
  PELAJARAN METODE: sinyal persisten (ONI) + jendela return tumpang tindih → t Newey-West TERLALU OPTIMIS (data tiruan tanpa
  pola memberi t +2,5). Selalu laporkan juga t tanpa tumpang tindih & pakai yang terkecil. Hapus 2019+ → IDENTIK.
- **Riset #17 SELESAI: momentum mingguan kripto (BTC, ETH, LTC; Coinbase)** (skrip di `private/`). HASIL NEGATIF.
  Latih 2015-08..2018-12 (BTC 175, ETH 132, LTC 119 minggu; koin lama yang bertahan → tanpa masalah koin mati). Masuk tutup Senin
  (lewati 1 hari), biaya 0,6%. U1 return minggu ini → minggu depan +0,076 (searah Liu-Tsyvinski 2021) t 1,4 | strategi 'pegang
  kalau naik' 1 minggu −0,79%/mg (t −1,5), 4 minggu −0,55%/mg (t −1,0) vs beli-dan-tahan. Pelajaran: aset dengan tren naik kuat
  → strategi timing (sering di kas) harus SANGAT kuat untuk menang. Daya uji rendah (data tiruan pola 0,15 → t 2,0).
  Ulangi setelah data uji (2019+) bisa dipakai untuk ide lain / data kripto lebih panjang. Hapus 2019+ → IDENTIK.
- **Riset #9 SELESAI: badai geomagnetik → saham ('latihan uji jujur')** (skrip di `private/`). HASIL NEGATIF, sesuai dugaan.
  Klaim Krivelyova-Robotti 2003 (return turun ~6 hari setelah badai). Badai = Ap ≥ 48 (94 hari di 2001–2018), jendela 6 hari
  bursa mulai tanggal ≥ d+2. IDX keranjang 30: −0,014%/hari vs +0,093% (t −1,2); SPY (sejak 1993): +0,031% vs +0,042% (t −0,2);
  strategi kas pasca-badai −0,8%/thn (t −0,5). Disiplin uji menolak klaim menarik yang lemah. Hapus 2019+ → IDENTIK.
- **Riset #18 SELESAI: lonjakan volume transaksi → saham IDX bulan depan** (detail & angka di `private/`).
  Sinyal NYATA secara statistik (IC kuat, stabil, korelasi rendah dengan S2) TAPI TIDAK bisa dijalankan sendiri: perputaran
  sangat tinggi → biaya realistis (spread) menghapus keuntungan. Kandidat KOMPONEN pendamping S2 (riset terpisah nanti).
  Pelajaran desain (ditemukan tes tiruan): lonjakan 'nilai transaksi' tercampur kenaikan harga → pakai JUMLAH LEMBAR.
- **Riset #18b SELESAI: gabungan S2 + sinyal lain** (detail di `private/`). Lolos aturan keputusan satu ukuran (t bersih
  realistis > 3, data LATIH saja) → PAPER TRADING KEDUA dengan awalan `s2v` (`raw/paper_trading/s2v_*`). Aturannya RAHASIA:
  `private/paper_s2v.py`, diunduh dari gudang HF private oleh `paper_trading.yml` saat jalan. `paper_trading.main(pemilih, awalan)`
  = colokan umum di kode publik. Rumus terbukti identik dengan riset (`--cek-riset`).
- **Riset #19 SELESAI: arus dana investor AS (TIC) → keranjang 30 saham likuid IDX bulan depan** (skrip di `private/`).
  HASIL NEGATIF. Sinyal = data bulan m−2 (TIC terbit ~6–7 minggu kemudian) dibagi simpangan baku 36 bulan sebelumnya.
  Latih 2002–2018: saham −0,42% per +1 std (t −1,4), semua efek −0,27% (t −0,9); strategi kas-kalau-arus-negatif −0,67%/bln
  (t −2,0, merugi). Arah sedikit berlawanan teori (arus masuk → sedikit lebih buruk). Hapus 2019+ → IDENTIK.
- **Riset #20 SELESAI: lelang Treasury AS sepi peminat → saham Indonesia minggu depan** (skrip di `private/`). BELUM LOLOS.
  Minat abnormal = bid-to-cover − rata-rata 6 lelang sebelumnya bertenor sama (Note/Bond nominal; tenor lelang ulang dibulatkan).
  Searah dugaan di ketiga uji (lelang sepi → IDX/EIDO lebih lemah) tapi t 2,0 (IDX) / 2,7 (EIDO) / −1,3 (sepi vs ramai) < 3.
  Kandidat komponen model gabungan nanti, bukan strategi sendiri. Hapus 2019+ → IDENTIK.
- **Riset #21 SELESAI: model gabungan 6 sinyal IDX, uji maju bertahap (dilatih ulang tiap tahun dengan masa lalu saja)**
  (detail di `private/`). Kemampuan meranking KUAT (IC uji maju 2009–2018 t 6,2; bobot stabil, S2 terbesar), tapi strategi
  beli-saja bersih realistis t 2,1 → TIDAK dipakai (aturan t > 3). Tetap terbaik dibanding S2 saja & s2v di periode yang sama.
  PERINGATAN: kekuatan S2 & s2v di data latih banyak berasal dari 2005–2008; di 2009–2018 jauh lebih tipis (sinyal IDX
  MELEMAH seiring waktu) → turunkan harapan pada paper trading. Mesin uji maju terbukti benar dengan data tiruan.
- **KOREKSI DATA 20 Nov 2026 (titik rusak harga IDX, lihat bagian 8) — angka DATA LATIH di atas TERLALU OPTIMIS.**
  Penyebab: (1) bulan sinyal 2018-04 berisi MAPI +900% & TOWR +361% palsu (harga beli 2 Mei 2018 salah ~10x) → S2 +24% palsu
  dalam sebulan; (2) bulan krisis 2008-10, 2009-03, 2009-04 dulu TERBUANG (lonjakan palsu membuat jumlah saham 29 < 30); bulan itu
  nyata: Mar–Apr 2009 = "momentum crash" (pasar memantul +41%, S2 tertinggal −31% & −24%). Angka BERSIH (data latih):
  #2 momentum 12-1: IC t 4,0 (dulu 5,0), K5−K1 +1,43% t 1,8, K5 bersih +0,55% t 1,4 (paruh IC 2,8/3,0).
  #12c/#13 S2 V0: bersih realistis +0,46–0,50%/bln t 1,1–1,3 (dulu 2,5–2,7). #18b s2v: t 2,3 (dulu 3,7) → TIDAK LOLOS aturan t > 3.
  #21 uji maju 2009–2018: IC t 4,7 (masih kuat) tapi bersih realistis model −0,04% / S2 −0,13% / s2v +0,12% (semua t < 0,5).
  #8: kesimpulan sama (filter tidak membantu). DATA UJI S2 (#12b/#12c, 2019+): TIDAK berubah (+1,00%/bln t 2,4 realistis) → kelulusan S2 tetap sah.
  KEPUTUSAN: S2 tetap paper trading resmi. `s2v` TETAP dicatat (aturan tidak diubah, gratis) tapi statusnya diturunkan jadi
  EKSPERIMEN: lolosnya berasal dari data rusak. Gambaran jujur: kemampuan MERANKING saham IDX nyata (IC t 4–5), tapi setelah
  biaya realistis keuntungan di 2005–2018 tipis & rawan "momentum crash" setelah dasar pasar. Turunkan harapan.
- **Riset #22 SELESAI: "bulan dividen" (Hartzmark-Solomon 2013) → saham IDX** (`riset_22_bulan_dividen.py`). HASIL NEGATIF.
  Pra-registrasi di-commit SEBELUM data dividen dilihat (248f985). Kelompok bulan m = saham semesta #12 yang ex-dividen di bulan (m−12).
  Latih (data bersih): 69 bulan aktif (median 10 saham; ramai Mei–Jul). U1 kotor −0,37%/bln t −0,9 (arah BERLAWANAN literatur);
  U2 bersih realistis −1,14%/bln t −3,9 (keluar-masuk tiap bulan = biaya ~1% per siklus). Data tiruan: premi +2%/bln pun bersih ≈ 0
  → strategi musiman bulanan di IDX butuh efek sangat besar. Bug ditemukan tes tiruan (biaya jual bulan keluar tak terhitung) → diperbaiki
  sebelum data asli. Hapus dividen 2019+ → IDENTIK. Data uji tidak dibuka.
- **Riset #7 SELESAI: lonjakan perhatian Wikipedia → volatilitas minggu depan** (`riset_07_perhatian_volatilitas.py`). HASIL NEGATIF.
  Pra-registrasi di-commit sebelum dijalankan (2e7a59b). log RV(w+1) = a + b·log RV(w) + c·lonjakan(w); t = terkecil White/NW(4).
  Latih: U1 BTC ← Bitcoin en+id c +0,013 t +0,1 (174 mg) | U2 ETH ← Ethereum c +0,12 t +1,0 (135 mg) | U3 SPY ← Stock_market_crash+
  Recession c +0,05 t +0,3. Volatilitas sangat lengket (b 0,44–0,60): perhatian tidak menambah informasi. DAYA UJI RENDAH: RV mingguan
  dari 5–7 return harian berderau; data tiruan c 0,3 hanya t 0,6–2,1, c 1,0 → t 6–9 (kode benar, `--tes-tiruan-kuat`).
  Hapus data 2019+ → IDENTIK. Data uji tidak dibuka. Ulangi nanti dengan RV dari data per jam (`crypto_jam`, hanya ke depan).
- **Riset #23 SELESAI: cuaca kota bursa → return hari itu (Hirshleifer-Shumway 2003)** (`riset_23_cuaca.py`). HASIL NEGATIF.
  Pra-registrasi di-commit sebelum dijalankan (6cc738f). Cuaca = Open-Meteo reanalisis; z sinar matahari per bulan kalender (statistik
  dari data latih saja). U1 keranjang 30 IDX ← sinar Jakarta −0,006%/z t −0,3 (3.922 hari, 2002–2018) | U2 hujan lebat ≥ 20 mm
  +0,16% vs +0,08% t +0,7 (132 hari) | U3 SPY ← sinar New York +0,006%/z t +0,4 (1993–2018). Daya uji CUKUP (tiruan 0,05%/z → t 2,9–3,4)
  → efek suasana hati cuaca, kalau ada, < ~0,03%/hari. Sesuai literatur baru (efek hilang setelah publikasi). Hapus 2019+ → IDENTIK.
- **Riset #24 SELESAI: titik api kebakaran (NASA FIRMS MODIS) → saham sawit IDX vs pasar** (`riset_24_titik_api.py`). HASIL NEGATIF.
  Pra-registrasi di-commit SEBELUM histori diunduh (6392868). Titik api Sumatra+Kalimantan (confidence ≥ 30), anomali = log(1+jumlah) −
  rata-rata periode musim yang sama 5 tahun sebelumnya. Sawit = AALI/LSIP/SGRO/SIMP/BWPT − keranjang 30 likuid. Latih 2001–2018:
  U1 mingguan +0,09%/anomali t +0,8 (760 mg) | U2 bulanan −0,07% t −0,1 (180 bln) | U3 6 bulan +1,6% t NW +0,7, tanpa tumpang tindih +0,1.
  Cek kewajaran data: tahun El Nino (2002/04/06/09/14/15) terbanyak (2015: 131 ribu), 2010/2016/2017 sepi; 2001 rendah (MODIS Aqua baru 2002).
  Tes tiruan: pola mingguan tertangkap t −3,9. Hapus 2019+ → IDENTIK. Data uji tidak dibuka. Kesimpulan riset #16 + #24: El Nino &
  kebakaran (yang publik & mencolok) tidak memberi keunggulan pada saham sawit; pasar sudah menyerapnya.
- **Riset #25 SELESAI: gempa besar di Indonesia → keranjang 30 saham likuid IDX** (`riset_25_gempa.py`). HASIL NEGATIF.
  Pra-registrasi di-commit sebelum dijalankan (b0e22a6). USGS M ≥ 6,5, kedalaman ≤ 70 km, kotak Indonesia, gempa susulan ≤ 7 hari dibuang;
  d0 = hari bursa pertama yang tutup (16:00 WIB) sesudah gempa; abnormal = dikurangi rata-rata 250 hari sebelumnya.
  Latih 2004–2018 (58 gempa, 22 ≥ M7): U1 reaksi d0 +0,23% t +0,9 (TIDAK turun) | U2 d0+1..5 −0,02% t −0,0 | U3 M ≥ 7 +0,90% t +1,3.
  Tsunami Aceh 2004: d0 +1,15%. Nias 2005 (M8,6): d0 −4,35% lalu +1,6%. Tes tiruan: −1%/+1% ditemukan (t −8,0 / +3,7).
  Hapus 2019+ → IDENTIK. Data uji tidak dibuka. Kesimpulan: gempa (umumnya jauh dari pusat ekonomi) tidak menggerakkan saham likuid IDX.
- **Riset #26 SELESAI: efek kalender IDX — pra-libur & pergantian bulan** (`riset_26_kalender.py`). HASIL NEGATIF.
  Pra-registrasi di-commit sebelum dijalankan (222dc81). Keranjang 30 likuid, 2002-05..2018-12 (3.921 hari; 190 hari pra-libur; jendela
  pergantian bulan = hari terakhir + 3 hari pertama). U1 pra-libur −0,00%/hari vs +0,09% t −0,7 | U2 pergantian bulan +0,175% vs +0,062%
  t +1,6 (searah literatur, paruh 1,4/0,8) | U3 strategi pra-libur bersih −0,50%/peristiwa | U4 strategi pergantian bulan bersih −0,03%/bln
  t −0,1. Tes tiruan: pola +0,3% & +0,15% ditemukan. Cek hapus-2019+ MENEMUKAN beda 1 hari (label pra-libur 28-12-2018 bergantung pada
  hari bursa 2 Jan 2019) → hari yang hari bursa berikutnya di 2019 dikeluarkan → IDENTIK. Data uji tidak dibuka.
- **Riset #27 SELESAI: percepatan uang beredar M1/M2 (SEKI BI) → keranjang 30 likuid IDX bulan depan** (`riset_27_likuiditas.py`).
  BELUM LOLOS (searah dugaan). Pra-registrasi di-commit sebelum dijalankan (b4915c9). Jeda terbit konservatif 2 bulan; percepatan =
  pertumbuhan tahunan(m) − pertumbuhan tahunan(m−3). Latih 189 bulan: U1 M1 +0,17%/pp t +1,0 | U2 M2 +0,36%/pp t +1,8 |
  U3 bulan M1 menguat +2,91% vs melemah +0,74% (t +2,0). Ketiganya POSITIF (sesuai teori likuiditas) tapi < 3. Catatan: angka SEKI = versi
  TERREVISI terbaru (bukan point-in-time; foto kita baru mulai 21 Nov 2026). Hapus 2019+ → IDENTIK. Data uji tidak dibuka.
  Kandidat KOMPONEN model gabungan makro (bersama lelang Treasury #20, pergantian bulan #26), bukan strategi sendiri.
- **Riset #28 SELESAI: kinerja saham IPO setelah 5 hari (e-IPO 2021–2023-06, 134 IPO)** (`riset_28_ipo.py`). TIDAK LOLOS, pola "LOTRE".
  Pra-registrasi di-commit SEBELUM data lengkap (e8119ce); pembagian SENDIRI: latih = pencatatan ≤ 2023-06-30, uji sesudahnya (DIKUNCI).
  U1 (hari 5 → 125) − keranjang 30: RATA-RATA +13,7% (t +1,4) TAPI MEDIAN −15,8%, hanya 37% IPO mengalahkan pasar; buang 5% ekor
  → −5,1%; potong ±100% → −4,7% t −1,0. Ekor kanan NYATA (BSML +736%, CHIP +573%, ADMR +325%, CUAN +309%; EURO +474% dengan 5 hari
  pertama datar = curigai). U2 kecil +21,0% vs besar +6,4% t +0,7. Semua IPO punya harga Yahoo sejak hari pencatatan (0 hilang).
  Kesimpulan: kebanyakan IPO tertinggal pasar, tapi segelintir melonjak berlipat → rata-rata tidak bisa dipakai (tidak bisa short,
  menghindari IPO juga melewatkan ekor kanan). Cacat diagnosis: `Close` Yahoo disesuaikan split → return hari pertama vs harga final
  salah untuk saham yang split (CUAN, RMKE tampak −80%); perbaiki dengan `raw/aksi_idx` kalau dipakai lagi.
- **Riset #29 SELESAI: percepatan kredit bank (SEKI I.4) → saham bank vs pasar** (`riset_29_kredit_bank.py`). HASIL NEGATIF.
  Pra-registrasi di-commit sebelum dijalankan (aae0018). Total kredit = jumlah 5 kelompok bank (cek vs baris 'J U M L A H' BI: beda maks 2,6%);
  jeda 2 bulan. Latih 185 bulan: U1 12 saham bank − pasar +0,07%/pp t +0,5 | U2 4 bank Persero − pasar (kredit Persero) −0,06% t −0,5 |
  U3 pasar −0,37% t −1,6. Tes tiruan: +0,3%/pp ditemukan tepat. Hapus 2019+ → IDENTIK. Data uji tidak dibuka.
- **Riset #30 SELESAI: kenaikan kas pemerintah AS di The Fed (TGA, DTS) → saham minggu depan** (`riset_30_tga.py`). HASIL NEGATIF
  (setelah membongkar ARTEFAK). Pra-registrasi di-commit sebelum dijalankan (384a29e). Sinyal = perubahan saldo Kamis→Kamis dibagi sb 52 minggu.
  Angka pra-registrasi: U1 IDX +0,17%/z t **+10,0** | U2 EIDO −0,10% t −0,6 | U3 SPY +0,11% t +5,8 → MENCURIGAKAN. Diagnosis: SATU minggu
  (Okt 2008, z = 117,8: Kemenkeu memindahkan kas ke The Fed di puncak krisis; TGA 2006 cuma ~$5 miliar) bertepatan dengan pantulan
  IDX +21,9% / SPY +15,7%. z dipotong ±3: IDX t +0,8, SPY t −0,8; 2010–2018 saja: −0,2 / −1,3; korelasi peringkat ≈ 0. Hapus 2019+ → IDENTIK.
  PELAJARAN METODE: z-skor dengan sb bergulir MELEDAK saat rezim berubah (seri kecil → besar). Rancang uji dengan z DIPOTONG (mis. ±3)
  atau peringkat SEJAK pra-registrasi; t yang luar biasa (> 6) pada sinyal makro = periksa pencilan dulu, jangan dirayakan.
- **Riset #31 SELESAI: struktur waktu VIX (VIX/VIX3M, panik jangka pendek) → saham Indonesia minggu depan** (`riset_31_struktur_vix.py`).
  BELUM LOLOS (searah dugaan). Pra-registrasi di-commit sebelum dijalankan (c102383). Rasio Jumat (dibatasi 0,7–1,5, TANPA z bergulir).
  Latih 2009-09..2018 (median rasio 0,878; backwardation 9% minggu): U1 IDX +0,32% per +0,1 rasio t +1,3 | U2 EIDO +0,68% t +2,1 |
  U3 IDX setelah backwardation +0,40%/mg vs +0,19% t +0,3 (39 minggu). Semua positif (premi rasa takut) tapi < 3. Tes tiruan: +0,3% tepat.
  Hapus 2019+ → IDENTIK. Data uji tidak dibuka. (Gabungan dengan #20 GAGAL di data uji → riset #32; sinyal mingguan ini dibuang.)
- **Riset #32 SELESAI: gabungan makro mingguan (#20 minat lelang Treasury + #31 VIX/VIX3M) → EIDO & IDX** (skrip di `private/`). ❌ GAGAL DI DATA UJI.
  Karena kedua sinyal DIPILIH dari data latih, aturan gabungan (skor = rata-rata z statistik latih, dibatasi ±3) & kriteria (EIDO kemiringan > 0
  DAN t > 2 di data uji) ditetapkan & dicadangkan SEBELUM dijalankan; data uji 2019+ dibuka SEKALI. Latih (in-sample): EIDO t 3,2.
  UJI: EIDO +0,32%/skor t +0,6 (410 minggu), IDX t −0,0 → kedua sinyal DIBUANG sebagai sinyal mingguan. PELAJARAN: sinyal "searah tapi
  t ~2" yang dikumpulkan dari banyak uji = kemungkinan besar KEBETULAN (multiple testing); gabungannya juga ikut kebetulan.
- **Riset #33 SELESAI: ekspor curah kering pelabuhan Kalimantan (PortWatch) → saham batu bara vs pasar** (`riset_33_pelabuhan_batubara.py`).
  HASIL NEGATIF. Pra-registrasi di-commit SEBELUM histori dilihat (7422244); pembagian SENDIRI: latih 2020–2022, uji 2023+ (DIKUNCI).
  18 pelabuhan Kalimantan (~4,2 juta ton/minggu). Sinyal = pertumbuhan tahunan 4 minggu, jeda 2 minggu. U1 minggu depan −0,04% per +0,1
  t −0,2 (147 mg) | U2 4 minggu −0,90% t −1,0 (36 titik). Tes tiruan +0,5% ditemukan tepat. DUA bug ditemukan & diperbaiki sebelum
  hasil final: (1) potongan fungsi #29 kosong (penanda teks muncul lebih awal; jalur tiruan tidak memakainya → cek JALUR ASLI juga);
  (2) cek hapus-2023+ menemukan U2 bocor (jendela 4 minggu melewati batas) → penyaring khusus → IDENTIK.
- **Riset #35 SELESAI: premi ilikuiditas Amihud di IDX (bersih biaya realistis)** (`riset_35_amihud.py`). HASIL NEGATIF.
  Pra-registrasi di-commit sebelum dijalankan (9a774e8). Kerangka #13 (semesta #2, bulanan, biaya 0,4% + spread CS). Latih 160 bulan:
  U1 IC −0,036 t −3,0 (ilikuid sedikit LEBIH BURUK secara peringkat, kebalikan literatur) | U2 beli 20% paling ilikuid kotor +0,49%/bln,
  biaya 0,59%/bln → bersih −0,11% t −0,3 (paruh +0,5/−1,5). Premi (kalau ada) habis dimakan spread. Tes tiruan OK. Hapus 2019+ → IDENTIK.
- **ARAH BARU (21 Nov 2026, setelah riset literatur — baca `docs/belajar_dari_renaissance.md`):** kebanyakan riset #1–#35 menguji
  SATU sinyal untuk timing SATU keranjang → breadth ~1 → menurut hukum Grinold-Kahn (IR = IC × √breadth) hampir pasti gagal (kesalahan
  DESAIN). Yang berhasil justru PENAMPANG saham (S2, model gabungan IC t 4–6). Prioritas: (1) model penampang IDX v2 berbasis ML
  (gradient boosting, 40–80 fitur, uji maju, dinilai sebagai SATU uji; Gu-Kelly-Xiu 2020, Hanauer-Kalsbach 2023 EM), (2) pembalikan
  jangka pendek penampang + aturan "trade hanya kalau untung > biaya", (3) model biaya dari data intraday. Kurangi timing makro 1 keranjang.
- **Riset #36 SELESAI: model penampang IDX v2 (LightGBM, 20 fitur harga/volume, uji maju 2009–2018)** (detail di `private/`).
  TIDAK LOLOS (t bersih realistis +0,4). Ranking KUAT (IC 0,098, t 5,1; ≈ linear, > S2 saja) tapi keuntungan kotor 20% teratas
  habis dimakan biaya. Fitur terpenting = s2 (jarak ke puncak 52 minggu) → konsisten dengan Hanauer-Kalsbach (EM). PELAJARAN METODE:
  parameter LightGBM awal GAGAL tes tiruan non-linear (menghafal derau); pohon dangkal + daun ≥ 1.000 sampel + regularisasi kuat
  dipilih HANYA dengan data tiruan & dibekukan sebelum data asli. MASALAH INTI SEKARANG: mengubah kemampuan meranking menjadi untung
  BERSIH long-only (biaya IDX + tidak bisa short) → riset konstruksi portofolio (penyangga, horizon lebih panjang, saham murah ditransaksikan).
- **Riset #34 SELESAI: kejutan laba → drift saham IDX (post-earnings announcement drift)** (`riset_34_kejutan_laba.py`). BELUM LOLOS
  (searah literatur). Pra-registrasi di-commit sebelum data dilihat (54f3437) + adendum cakupan (114 saham diliput analis). Masuk tutup hari
  bursa ke-2 setelah tanggal pengumuman, tahan 20 hari, abnormal vs keranjang 30. Latih 2005Q4–2018Q4 (1.620 peristiwa, 39 kuartal):
  U1 tertil atas − bawah +1,44% per 20 hari t +2,8 (atas +0,82%, bawah −0,63%; paruh −0,1 / +4,0 = efek muncul 2012+) |
  U2 beli tertil atas bersih 0,8% +0,02% t 0,0. Tes tiruan ±2% ditemukan tepat. Hapus 2019+ → IDENTIK. Data uji tidak dibuka.
  Kandidat FITUR model penampang (hanya saham besar yang diliput analis).
- **Riset #37 SELESAI: konstruksi portofolio sadar biaya untuk model ML #36 (penyangga sS 20/40 + bobot likuiditas, dari Novy-Marx &
  Velikov)** (detail di `private/`). TIDAK LOLOS (t −0,4). Penyangga memangkas perputaran 43% → 21–25% TAPI alpha kotor turun lebih banyak
  (+0,57% → +0,28%/+0,13%); bobot likuiditas paling merusak → keunggulan meranking IDX terkonsentrasi di saham KURANG likuid (= paling mahal).
  PERTANYAAN PENENTU berikutnya: biaya eksekusi NYATA order kecil di IDX (model kita menganggap selalu bayar spread penuh + 0,4%). Kalau
  limit order menghindari sebagian besar spread, biaya ≈ 0,4% × perputaran → bisa membalik kesimpulan. Ukur dari `raw/harian/intraday_idx`
  (bid/ask & bar 1 menit, ke depan) + `daftar_idx` (bid/ask). JANGAN menyimpulkan "tidak bisa untung" sebelum biaya nyata terukur.
- **Riset #38 SELESAI: evaluasi ulang #36/#37/S2 dengan MODEL BIAYA B = 0,4% + 1,2 × tick HISTORIS/harga ASLI** (`biaya_idx.py`;
  detail di `private/`). TIDAK LOLOS: ML bobot sama +0,09%/bln t +0,3 (biaya lama +0,05%). TEMUAN DIAGNOSIS (dari aturan fraksi BEI):
  2004–2013 tick historis 0,84–0,98% ≈ model lama (spread memang lebar, fraksi Rp5/10/25/50); 2014–2018 tick 0,32–0,46% vs model
  0,65–0,88% (model ~1,9x terlalu mahal). KESIMPULAN KUAT: alpha kotor long-only IDX 2009–2018 hanya ~0,5%/bln → spread nol pun t ~1;
  masalahnya ALPHA KECIL di periode itu, BUKAN biaya salah hitung. (S2 di data uji 2019–2026 jauh lebih kuat: alpha berubah antar rezim.)
- **Riset #39 SELESAI: masa pegang lebih panjang (portofolio bertumpuk 3/6 bulan; George-Hwang, Jegadeesh-Titman) untuk ML & S2,
  biaya B** (detail di `private/`). TIDAK LOLOS: ML 6 bulan bersih +0,02%/bln t 0,1. ALPHA MEMUDAR CEPAT: kotor ML +0,57% (1 bln) →
  +0,27% (3 bln) → +0,15% (6 bln). RANGKUMAN #36–#39 (BUKTI KONSISTEN): 4 konstruksi portofolio × 2 model biaya → long-only IDX
  2009–2018 bersih ≈ 0. Kemampuan meranking nyata (IC t 5) tapi terlalu kecil & cepat pudar untuk long-only setelah biaya.
- **Riset #40 SELESAI: proteksi momentum crash untuk S2 (Daniel & Moskowitz 2016: bearish = return pasar 24 bulan < 0)** (detail
  `private/`). BELUM TERBUKTI (daya uji rendah, diakui di depan): 15 bulan bearish 2005–2018; S2 − semesta −1,64%/bln saat bearish vs
  +1,42% normal (t −1,0; didominasi Mar–Apr 2009 −31%/−24%); proteksi − S2 +0,14%/bln t 0,5. Searah literatur (bukti eksternal AS sejak
  1927 kuat). S2 resmi TIDAK diubah; dijadikan paper EKSPERIMEN `s2p` karena kondisi sekarang BEARISH (uji masa depan paling relevan).
- **Riset #41 SELESAI: momentum PENAMPANG kripto (Liu-Tsyvinski-Wu 2022 JF; Coinbase, koin median nilai ≥ $1 juta/hari)** (detail
  `private/`). HASIL NEGATIF. Pembagian sendiri (penampang baru cukup sejak 2021): latih 2021–2023, uji 2024+ DIKUNCI. Return 21 hari →
  minggu depan (jeda 1 hari): IC −0,038 t −2,1 (cenderung BERBALIK, kebalikan LTW yg sampelnya 2014–2018); sepertiga atas bersih −0,48%/mg
  t −1,6 (biaya 0,35%/sisi, putar 40%/mg). Survivorship: hanya koin yg masih diperdagangkan. Hapus 2024+ → IDENTIK.
- **Riset #42 SELESAI: model ML dilatih data GABUNGAN AS + IDX (ide Hanauer-Kalsbach: pooled > per negara), diterapkan ke IDX 2009–2018**
  (detail `private/`). TIDAK LOLOS & lebih buruk: gabungan IC +0,029, bersih −0,51%/bln t −2,2; model AS saja IC +0,001 (tidak transfer);
  IDX saja = #38 persis. Model gabungan didominasi log_harga & porsi hari aktif (bukan s2) = jejak BIAS SURVIVORSHIP data AS (saham kecil
  yang mati hilang → yang tersisa tampak menang). PELAJARAN: data AS kita (100% survivor) TIDAK layak jadi data latih ML; paper memakai
  Datastream dengan daftar saham mati. Jangan ulangi tanpa data delisting.
- **Riset #43 SELESAI: kejutan laba × dekat puncak 52 minggu ("jangkar"; George-Hwang-Li 2014, Kalsbach Bab 3)** (`riset_43_laba_jangkar.py`).
  TIDAK LOLOS. Pra-registrasi di-commit sebelum dijalankan (8ee4376). Latih 2005Q4–2018Q4 (1.620 peristiwa, sel ~6 saham): U1 interaksi
  (atas&dekat − bawah&jauh) +1,92%/20 hari t +2,5 (paruh 0,9/3,3) | U2 beli atas&dekat bersih 0,8% −0,07% t −0,1. Sel: atas&dekat +0,73%,
  atas&jauh +1,03% (sisi beli TIDAK sesuai teori), bawah&jauh −1,19% (efek di sisi short, tidak bisa dipakai). Tes tiruan: pola ditemukan
  t 11,2; tes kosong 7 benih: U1 t −0,3..+2,6 (t 2–3 bisa muncul acak!). Hapus 2019+ → IDENTIK. Data uji tidak dibuka.
- **Riset #44 SELESAI: berita emiten (EmitenNews) × dekat puncak 52 minggu (Kalsbach Bab 3)** (`riset_44_berita_jangkar.py`, `berita_emiten.py`).
  TIDAK LOLOS. Pra-registrasi di-commit sebelum dijalankan (357ffc3); pembagian sendiri: latih sinyal 2021–2023, uji 2024+ DIKUNCI. FN = return
  di hari berita (hari bursa >= tanggal & sesudahnya, dibatasi akhir bulan), NEAR = S2. Latih 32 bln, ~144 saham berita/bln: U1 interaksi
  +1,71%/bln t +1,7 | U2 beli atas&dekat bersih biaya B +0,18% t 0,3 | berita baik − buruk −0,20% t −0,3 (BERITA SENDIRI TIDAK MEMPREDIKSI).
  Sel: atas&dekat +0,97, atas&jauh −1,59, bawah&dekat +1,16, bawah&jauh −0,74 → yang bekerja hanya "dekat puncak" (= S2), bukan interaksi.
  Tes tiruan ±3% → +5,68% t 10,9; tes kosong ≈ 0. Hapus data sesudah latih → IDENTIK. Pencocokan kode: kata umum (bank/bumi/emas/laba...)
  wajib disertai nama perusahaan di judul.
- **Riset #45 SELESAI: net share issuance (Pontiff-Woodgate 2008; McLean-Pontiff-Watanabe 2009) → saham IDX bulan depan**
  (`riset_45_net_issuance.py`). HASIL NEGATIF (daya uji rendah, diakui di depan). Pra-registrasi di-commit sebelum return dilihat (a0bbc7d);
  pembagian sendiri (data saham beredar padat baru 2018Q4): latih sinyal 2019-12..2022-10 (35 bln), uji 2023+ DIKUNCI. NI = log saham
  beredar 12 bulan (median 3 titik, jeda 30 hari), bulan-saham dgn split di jendela DIBUANG (Yahoo tak konsisten soal split).
  Semesta S2, median 133 saham & 14 penerbit (NI > 5%) per bulan. U1 penerbit − tanpa −0,10%/bln t −0,1 | U2 semesta tanpa penerbit −
  semesta +0,08% t +0,8 | U3 IC −0,017 t −1,0. Daya uji: pola tiruan −2%/bln baru t −3,3. Hapus data > 2022 → IDENTIK. Data uji tidak dibuka.
  Uji ulang setelah data saham beredar ke depan menumpuk (bisa juga jadi fitur model penampang).
- **Riset #46 SELESAI: musiman penampang (Heston-Sadka 2008/2010; Keloharju dkk. 2016)** (`riset_46_musiman.py`). HASIL NEGATIF.
  Pra-registrasi di-commit sebelum dijalankan (fa89516). Sinyal = rata-rata return bulan kalender yang sama 1–10 tahun lalu (min 4).
  Latih 2007-07..2018-10 (118 bln, median 86 saham): U1 IC −0,007 t −0,7 | K5−K1 −0,47% t −1,2 | U2 20% teratas bersih −1,33%/bln t −5,5
  (putar 79%, biaya ~1%/bln). Tes tiruan (pola sb 2%) IC t +9,2 tapi bersih t +0,5 → sinyal berperputaran tinggi tak bisa jadi strategi
  long-only IDX; keputusan kedua (fitur ML, IC t > 3) juga GAGAL. Cek potong data: IC & return IDENTIK; biaya beda tipis (0,95 vs 0,98%)
  karena `harga_asli` butuh split SESUDAH 2018 untuk membalik penyesuaian Yahoo (sah, bukan kebocoran). Data uji tidak dibuka.
- **Riset #47 SELESAI: dividend yield (value; Rouwenhorst 1999, Hanauer-Lauterbach 2019)** (`riset_47_dividend_yield.py`). TIDAK LOLOS.
  Pra-registrasi di-commit sebelum dijalankan (742e42b). DY = dividen 12 bln (raw/aksi_idx) / Close; latih 2004-11..2018-10 (160 bln, median
  99 saham, 71 pembagi). U2 (penentu) 20% DY teratas bersih +0,15%/bln t +0,4 (kotor +0,41%, putar 21%, biaya 0,27%) | U1 IC +0,060 t +4,7
  (paruh 3,6/3,1) TAPI sumbernya PEMBAGI vs BUKAN PEMBAGI +1,02%/bln t 2,7; di antara pembagi, K5−K1 +0,08% t 0,1 → besarnya yield tidak
  memprediksi, yang bekerja "membayar dividen atau tidak" (proksi kualitas). IDE BARU (muncul SETELAH lihat data → wajib pra-registrasi baru,
  hitung sbg uji tambahan): fitur "pembagi dividen" untuk model penampang ML / saringan semesta S2. Cek potong data: IC & return IDENTIK
  (biaya beda tipis, sebab sama dgn #46). Data uji tidak dibuka.
- **Riset #48 DIBATALKAN sebelum data uji dibuka: "pembagi dividen" long-only vs semesta (ide #47)** (`riset_48_pembagi_dividen.py`).
  Aturan uji data uji ditulis dulu, lalu ANALISIS DAYA UJI: premi tiruan +1%/bln → bersih hanya t 1,4 (160 bln) karena pembagi ≈ 72% semesta;
  in-sample asli +0,20%/bln t 1,6. Data uji ~93 bln → hampir pasti gagal walau efek nyata → data uji TIDAK dibuka (tidak dihitung sbg uji).
  PELAJARAN: sebelum membuka data uji, SELALU cek daya uji strategi yang akan dinilai. Ide disimpan sbg fitur ML / penyaring semesta.
- **Riset #49 SELESAI: volatilitas rendah long-only (S3 sendiri; Blitz-Pang-van Vliet 2013 EM, Frazzini-Pedersen 2014)**
  (`riset_49_volatilitas_rendah.py`). TIDAK LOLOS. Pra-registrasi di-commit sebelum dijalankan (b4347ae). 20% vol 120 hari terendah, ukuran =
  ALPHA CAPM bersih vs semesta (rf = IRSTCI01IDM156N, galat White). Latih 2004-11..2018-10 (160 bln): beta 0,62; return mentah bersih SAMA dgn
  semesta (+1,22% vs +1,17%/bln); Sharpe 0,40 vs 0,26; alpha kotor +0,57% t 2,9; U1 alpha BERSIH +0,26%/bln t +1,3 (paruh 0,8/1,1; putar 24%,
  biaya 0,31%). Efek klasik terlihat (risiko −40%, return sama) tapi tak signifikan setelah biaya. Cek potong: identik (biaya beda tipis, sebab #46).
  Catatan: berguna sbg portofolio DEFENSIF (bukan alpha); data uji tidak dibuka.
- **Riset #50 SELESAI: momentum SEKTOR long-only (Moskowitz-Grinblatt 1999)** (`riset_50_momentum_sektor.py`). TIDAK LOLOS.
  Pra-registrasi di-commit sebelum dijalankan (c5fbea6). Peta sektor = foto fundamental Yahoo 21 Nov 2026 (11 sektor, STATIS → sedikit info
  masa depan, diakui). Return 12-1 sektor dari rata-rata saham semesta; beli semua saham 3 sektor teratas. Latih 2006-02..2018-10 (113 bln,
  P ~34 saham, putar 21%, biaya 0,28%): IC peringkat sektor +0,132 t +2,9 | kotor P − semesta +0,36%/bln t +1,4 | U1 BERSIH +0,08%/bln
  t +0,3 (paruh −0,9/+1,2); alpha CAPM sama (beta 0,99). Tes tiruan: drift sektor AR(1) → bersih t 5,5. Cek potong: identik. Data uji tidak dibuka.
  POLA BERULANG #36–#50: arah sinyal benar (IC t 3–5) tapi alpha kotor long-only IDX 2005–2018 ≈ 0,3–0,6%/bln ≈ biaya.
- **Riset #51 SELESAI: model ML (#36/#38 + fitur 'pembagi dividen') di REZIM SEKARANG vs S2 sendirian** (detail `private/`). ❌ GERBANG A GAGAL.
  Pra-registrasi di catatan private + dicadangkan sebelum dijalankan. Ukuran = ML − S2 (bukan ML vs pasar), karena data uji S2 2019+ sudah
  dibuka. Validasi 2019–2022 (46 bln): IC ML > S2 (t 4,3 vs 3,2) TAPI 20% teratas ML untung bersih jauh lebih kecil (ML − S2 −0,87%/bln
  t −1,6; terburuk 2021). Data uji 2023+ TIDAK dibuka; `ml` tetap EKSPERIMEN. Pelajaran: IC lebih tinggi ≠ kelompok teratas lebih untung;
  di rezim ritel, S2 murni lebih kuat dari skor campuran. Cek potong: identik.
- **Riset #53 SELESAI: S2 dengan porsi menurut volatilitas (Barroso-Santa-Clara 2015; Moreira-Muir 2017), long-only tanpa utang**
  (`riset_53_s2_volatilitas.py`, pra-reg `docs/prareg_53_s2_volatilitas.md` d0a79d7). ❌ BELUM TERBUKTI. Tes daya uji SEBELUM data asli: dunia palsu
  persis sesuai teori pun alpha t < 1 (porsi dibatasi 1 + Sharpe dasar rendah). Asli 2007-07..2018-10 (128 bln): alpha −0,009%/bln t −0,23;
  Sharpe 0,14 vs 0,15; DD maks −47% vs −50%; porsi rata 0,98. Jendela 126 hari TERLAMBAT (Agu–Sep 2008 porsi masih 1,00). Info: varians 21 hari
  t +0,67. Potong-data identik (biaya beda tipis, sebab #46). S2 resmi TIDAK diubah. Pelajaran: porsi-vol long-only = alat risiko, bukan alpha.
- **Riset #54 SELESAI: arus asing di SBN (kepemilikan non-residen DJPPR) → saham Indonesia** (`riset_54_asing_sbn.py`, pra-reg
  `docs/prareg_54_asing_sbn.md` a8a5fb1). ❌ TIDAK LOLOS (daya uji rendah: tiruan besar pun t 2,3–3,1). Jeda konservatif 7 hari. U1 IDX minggu depan
  t +0,35 | U2 EIDO t +0,32 | U3 bulanan (porsi asing, 2003–2018) t −1,24. Cek kewajaran minggu SAMA t +3,35 (asing masuk ↔ saham naik) → info
  sudah masuk harga minggu itu. Potong-data identik. Uji ulang dgn jeda nyata (~3 hari, ukur dari `pertama_terlihat`) / sbg fitur penampang.
- **Riset #55 SELESAI: beta saham thd arus asing SBN (PENAMPANG mingguan) → saham IDX minggu depan** (`riset_55_beta_asing.py`, pra-reg
  `docs/prareg_55_beta_asing.md` 9d1dd06). ❌ TIDAK LOLOS. 207 mg, ~118 saham: U1 IC searah arus t −0,20 | U2 IC~F t +0,37 | U3 bersih t −0,71.
  AKAR: beta 52 minggu per saham TIDAK persisten (cek minggu sama IC t +0,41; data palsu t +7) → kepekaan per saham tak terukur dgn desain ini.
  Potong-data identik. Uji ulang dgn kelompok kepemilikan asing nyata / beta harian.
- **Riset #56 SELESAI: akhir lock-up 8 bulan IPO IDX (POJK 25/2017; Field-Hanka 2001)** (`riset_56_lockup.py`, pra-reg `docs/prareg_56_lockup.md`
  dac280e). ❌ TIDAK LOLOS & tanpa efek khusus. 134 IPO latih: CAR[−5,+5] −2,35% t −1,91 | [−20,−1] −4,08% t −2,52 | [0,+20] −2,01% t −1,55;
  volume TURUN ×0,50. PLASEBO (efektif + 6 bln) SAMA: −2,59% t −2,13, volume ×0,53 → yang terlihat = kelemahan umum IPO bulan 6–9 (#28), bukan
  tanggal kunci. Daya uji rendah (hanya efek ≳ 6% terdeteksi). Tanggal efektif = perkiraan (penawaran − 1 hari kerja).
- **Riset #57 SELESAI: frog-in-the-pan (Da-Gurun-Warachka 2014; momentum KONTINU)** (`riset_57_frog_in_pan.py`, pra-reg `docs/prareg_57_frog_in_pan.md`
  d9bb718). U1 ✅ IC(−ID, r) di antara pemenang 12-1 +0,065 t +3,83 (paruh 2,2/3,4) | U2 ❌ FIP beli-saja bersih +0,24%/bln t +0,78 (= momentum biasa).
  DIAGNOSIS sesudah hasil: −ID kor +0,28 dgn S2 & +0,30 dgn S3; residual setelah S1/S2/S3 IC +0,027 t +1,80 → sebagian besar = sinyal lama.
  Kandidat FITUR model penampang (ID = tanda(PRET) x (%turun − %naik), 150+ hari). Potong-data: IC identik (biaya beda tipis, sebab #46).
- **Riset #58 SELESAI: laba diumumkan TELAT vs kebiasaan emiten (Givoly-Palmon 1982; deHaan dkk. 2015)** (`riset_58_laba_telat.py`, pra-reg
  `docs/prareg_58_laba_telat.md` 5e84faf). ❌ TIDAK LOLOS (daya uji rendah). 1.249 peristiwa, TELAT ≥ 14 hr cuma 103 (8%; jadwal emiten IDX sangat tetap):
  U1 +1,20%/kuartal t +0,92 (14 kuartal) | U2 t −0,03. Kejutan EPS kelompok telat hanya sedikit lebih buruk (median −3,2% vs −1,8%). Potong-data identik.
- **Riset #59 SELESAI: lead-lag DALAM sektor (Hou 2007; pemimpin = 3 saham paling likuid per sektor)** (`riset_59_lead_lag_sektor.py`,
  pra-reg `docs/prareg_59_lead_lag_sektor.md` 7303390). ❌ TIDAK LOLOS. 126 bln, 8 sektor, ~78 pengikut: U1 IC +0,020 t +1,40 | U2 (kontrol r0 sendiri)
  t +1,21 | U3 bersih −0,74%/bln t −2,25 (biaya 1,07%). INFO: return 1 bulan SENDIRI t +3,56 (= #2). Tes kosong menemukan cacat aturan U3 (|t| meloloskan
  biaya) → diperbaiki jadi t > +3 SEBELUM data asli. Potong-data: IC identik (biaya beda tipis, sebab #46). Uji ulang dgn industri rinci (~70).
- **Riset #60 SELESAI: lonjakan 'tutup di puncak' (mirip ARA: return ≥ +20% & Close = High; magnet Kim-Rhee 1997 vs lotre)** (`riset_60_lonjakan_puncak.py`,
  pra-reg `docs/prareg_60_lonjakan_puncak.md` abe613d). ❌ TIDAK LOLOS, pola LOTRE: 181 peristiwa likuid (2002–2018): +20 hr rata +0,75% tapi MEDIAN −4,0%
  (t −0,08); +60 hr median −5,8% (t +0,10); d+1 +0,58%. Aturan ARA resmi berubah antar tahun (35/25/20 simetris resmi Jan 2017; ARB asimetris 2015 &
  2020–2023; ARB 15% Apr 2025) → definisi bebas-aturan. Potong-data identik.
- **Riset #61 SELESAI: drift sesudah STOCK SPLIT (Ikenberry 1996; Desai-Jain 1997; kontrol momentum Boehme-Danielsen 2007)** (`riset_61_split.py`,
  pra-reg `docs/prareg_61_split.md` 9594072). ❌ TIDAK LOLOS, arah BERLAWANAN literatur (daya uji rendah, diakui di depan: tiruan +5%/60 hr → t 2,4).
  57 split maju (rasio >= 1,5) yang lolos saringan likuiditas 2004–2018; portofolio WAKTU KALENDER (110 bln): U1 vs keranjang 30 −2,45%/bln t −2,27
  (paruh −0,8/−2,7) | U2 vs kuintil momentum sama −2,62%/bln t −2,33 | per peristiwa +60 hr −4,4% (median −3,5%), hari ex +2,1%. Split terjadi setelah
  harga naik (kuintil momentum median 4). Split BALIK hanya 1 yang lolos saringan. Desain diganti ke portofolio kalender SEBELUM data asli (rata-rata
  bulan non-tumpang tindih membuang 2/3 peristiwa). Cek potong-data MENEMUKAN bocor seleksi (syarat jendela 120 hr melihat data 2019) → diperbaiki → IDENTIK.
  Kandidat FITUR 'hindari' model penampang (perlu pra-reg baru; jangan dirayakan: t −2,3 dari 57 peristiwa).
- **Daftar ide berikutnya** (urutan rekomendasi):
    (#7, #8, #9 SUDAH) → #10 volatilitas tersirat opsi (tunggu data beberapa bulan) → riset 'kejutan' rilis makro dengan
    perkiraan pasar Kalshi (tunggu data menumpuk) → proteksi 'momentum crash' S2 (butuh pra-registrasi, lihat private)
- Calon sumber data berikutnya: (daftar lama habis; cari baru, prioritas data 'hanya ke depan' & terkait IDX). (SEC Form 4, kurs ECB, arsip WIKI, Polymarket SUDAH ditambahkan 20 Nov 2026.)
  (Volume short FINRA, logam LME + stok, dan sawit harian SUDAH ditambahkan 19 Nov 2026.)
  Dengan harga harian LME & sawit, riset #3 bisa diuji ulang di horizon MINGGUAN (nikel/timah sejak 2008, sawit sejak 2010).
  Prioritaskan data "hanya ke depan" (tidak bisa diambil mundur).
- **KONTEKS PASAR 21 Nov 2026: IHSG 5.146 = −43,7% dari puncak 9.135 (20 Jan 2026)**; 3 bulan −20,8%, setahun −37,8%; VIX AS 35,9.
  Paper trading S2/s2v/ml mulai 1 Des 2026 DI TENGAH pasar bearish dalam → risiko "momentum crash" (S2 tertinggal tajam saat pasar
  memantul dari dasar, seperti Mar–Apr 2009: −31% & −24% vs semesta). Diteliti di riset #40.
- Pantau: email alarm, jatah menit GitHub (github.com/settings/billing, "$x used / $12.00"), jatah BigQuery.
- **ATURAN RAHASIA STRATEGI (keputusan pengguna 20 Nov 2026):** detail sinyal/strategi yang terbukti MENGUNTUNGKAN
  (skrip, parameter, hasil lengkap) disimpan di folder `private/` (diabaikan git) + cadangan `python simpan_private.py`
  ke gudang HF private (`--ambil` untuk memulihkan). Di repo publik & CLAUDE.md cukup ringkasan umum TANPA detail.
  Riset yang hasilnya negatif/umum boleh tetap publik. S2 (literatur George-Hwang 2004) sudah publik sebelum aturan ini.
- **REPO PUBLIK (keputusan pengguna 20 Nov 2026, menggantikan keputusan 'tetap private'):** menit Actions tak terbatas.
  Konsekuensi: (1) semua kode, CLAUDE.md, log Actions & hasil riset (termasuk strategi S2) bisa dibaca siapa pun -> JANGAN
  tulis data pribadi pengguna di file repo (simpan di memori Claude); (2) GitHub MEMATIKAN jadwal otomatis setelah 60 hari
  tanpa aktivitas repo -> workflow `jaga_aktif.yml` (dibuat atas izin pengguna) commit
  `.github/aktif.txt` tiap tanggal 1 (izin `contents: write`, hanya file itu); (3) gudang Hugging Face TETAP private.
  Riwayat git sudah dicek bersih (60 commit, 20 Nov 2026): tanpa kunci/token/email asli. Versi lama CLAUDE.md di riwayat masih
  memuat catatan pribadi ringan (jenis e-wallet, kutipan, ID project GCP) - risiko rendah, riwayat SENGAJA tidak ditulis ulang
  supaya bukti waktu pra-registrasi riset (commit 1a1d878, a7e92f7) tetap utuh.
- (Catatan lama) **Jatah GitHub Actions (keputusan 20 Nov 2026):** repo TETAP PRIVATE. Pengguna minta DIKABARI kalau mendekati batas.
  Per 20 Nov: $4,62 (~770 menit) terpakai; run harian ~42,5 menit; perkiraan bulan penuh ~1.500–1.600 dari 2.000 menit.
  Pengguna: "nggak usah mikirin menit" → menit BUKAN pertimbangan memilih data/riset & jangan dibahas; cukup pantau
  diam-diam. HANYA kalau perkiraan > ~1.800 menit/bulan atau Compute > ~$10:
  kabari, tawarkan (1) hemat `kumpul_saham_as.py` (~17 menit/hari) atau (2) jadikan publik SETELAH merapikan catatan pribadi
  di CLAUDE.md (repo publik = menit tak terbatas, tapi jadwal mati setelah 60 hari tanpa aktivitas & log Actions publik).
  Riwayat git sudah dicek bersih dari kunci/token (39 commit). Repo `sim-runs` publik, tidak memotong jatah.