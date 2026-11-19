# Proyek Quant: Gudang Data & Riset Trading

## Tentang pengguna
- Pemula dalam pemrograman. SELALU jawab dalam **Bahasa Indonesia**, jelaskan istilah baru dengan sederhana.
- Berikan **file/kode lengkap**, jangan potongan yang harus disisipkan manual.
- **Uji dulu** setiap perubahan sebelum menyuruh push. Jalankan sendiri perintahnya kalau bisa.
- Laptop Windows (PowerShell), Python 3.13 di `D:\quant\.venv` (aktifkan: `.venv\Scripts\activate`).
- Drive C hampir penuh: semua data & cache di D atau cloud.

## Tujuan
Meniru CARA BERPIKIR Renaissance Technologies (bukan skalanya): kumpulkan data sangat luas
(termasuk data "aneh"), bersihkan dengan teliti, cari banyak sinyal lemah dengan statistik ketat,
gabungkan, uji dengan biaya transaksi. Medan realistis: horizon hari–minggu, pasar Indonesia.

## Arsitektur (gratis, tanpa kartu kredit)
- **Kode**: GitHub private `imfadli10-cpu/quant`.
- **Data**: Hugging Face dataset private `fadli-sparks/quant-data` (`raw/` mentah, `bersih/` siap pakai).
- **Otomatisasi**: GitHub Actions (jatah 2.000 menit/bulan untuk repo private).
- **BigQuery Sandbox**: project `potent-duality-512213-u4`, service account `quant-collector`. Pagar 5 GB/query.

## Workflow (.github/workflows/)
- `harian.yml`: 00:17 UTC (07:17 WIB) tiap hari. Semua collector harian (`continue-on-error: true`),
  lalu `upload_ke_cloud.py`, `buat_katalog.py`, `validasi_harian.py` (gagal = email alarm).
- `fundamental.yml`: tanggal 2 tiap bulan. `kumpul_sec.py` + `kumpul_bps.py` (3 tahun terakhir).
- `gabung.yml`: tiap Minggu. `gabung.py` → `bersih/harga_idx.parquet`, `bersih/saham_as.parquet`.
- `histori_as.yml`, `histori_bps.yml`: manual, sekali jalan (sudah selesai 100%).

## Rahasia (JANGAN PERNAH di-commit)
- Lokal: `kunci_fred.txt`, `kunci_hf.txt`, `kunci_gcp.json`, `kunci_sec.txt`, `kunci_bps.txt` (diabaikan `.gitignore`).
- GitHub Secrets: `FRED_API_KEY`, `HF_TOKEN`, `GCP_KEY_JSON`, `SEC_USER_AGENT`, `BPS_KEY`.
- Pola kode: `os.environ.get("NAMA") or Path("kunci_x.txt").read_text().strip()`.
- Selalu `git status` sebelum `git add`: pastikan tidak ada file `kunci_*`.

## Pola menambah sumber data baru
1. Collector `kumpul_xxx.py` (simpan ke `data/raw/harian/<nama>/<tanggal>.parquet`, ambil N hari terakhir supaya tumpang tindih).
2. Langkah di `harian.yml` dengan `continue-on-error: true`.
3. Baris `cek(...)` di `validasi_harian.py`.
4. Baris keterangan di kamus `INFO` di `buat_katalog.py`.
Data "hanya ke depan" (opsi, daftar saham harian) harus dimulai sedini mungkin.

## Jebakan yang SUDAH ditemukan (jangan diulang)
- **JANGAN jalankan `upload_ke_cloud.py` dari laptop**: bisa menimpa file server dengan file tes. Pakai `upload_satu.py <jalur>`.
- Tanggal file harian = tanggal UTC server. Jadwal harus mulai setelah 00:00 UTC (dulu alarm palsu karena lewat tengah malam).
- BigQuery `to_dataframe()` → kolom `dbdate`: ubah ke datetime standar sebelum disimpan.
- pandas membaca kode saham "NA" sebagai kosong: pakai `keep_default_na=False, dtype=str`.
- Tanggal dari sumber berbeda punya presisi/zona waktu beda (ms vs us, tz): samakan dulu sebelum `merge_asof`.
  JANGAN pakai `.values` pada tanggal ber-zona waktu (menggeser satu hari diam-diam).
- Koneksi Python ke Hugging Face dari laptop kadang putus: nyalakan Cloudflare WARP. Situs Indonesia (BPS) lebih cepat tanpa WARP.
- BPS API: parameter `th` wajib, maksimal 3 tahun per permintaan, kode tahun = tahun − 1900.
- SEC wajib User-Agent berisi nama+email (di secret). Data SEC campur tipe: paksa tipe kolom.
- Situs IDX diblokir Cloudflare untuk program otomatis: JANGAN menembus/menyamar (keputusan pengguna).
- Open-Meteo & Wikipedia membatasi kecepatan: beri jeda + coba ulang. Satu permintaan banyak kota untuk Open-Meteo.
- Python di Actions: set `PYTHONUNBUFFERED=1` supaya log langsung tampil; upload per bagian untuk pekerjaan panjang.

## Aturan riset
- Data latih s/d 2018-12-31, data uji 2019+ DIKUNCI (buka sekali di akhir dengan `--buka-uji`).
- Ambang t > 3. Uji di instrumen yang BISA dibeli. Selalu potong biaya (asumsi IDX 0,4% bolak-balik).
- Tulis dugaan + alasan logis SEBELUM melihat data.

## Status riset
- **#1 EIDO → IHSG besok** (`riset_01_eido.py`, `riset_01b_cek.py`): IHSG t=10,5 tapi sebagian besar
  ilusi indeks basi. Saham likuid lemah (BBRI t=4,8, lainnya ~2) dan RUGI setelah biaya. Data uji tidak dibuka.
  Kesimpulan: tidak layak sebagai strategi tunggal; mungkin berguna sebagai salah satu sinyal gabungan.
- Berikutnya (daftar ide): #2 momentum saham IDX, #3 komoditas (nikel/timah/batu bara/sawit) → saham terkait,
  #4 kurs & DXY → IHSG, #5 saham "tidur" telat bereaksi, #6 COT ekstrem, #7 Wikipedia → volatilitas crypto.
- Penggabungan ke `bersih/` baru untuk harga saham IDX & AS; sumber lain belum.