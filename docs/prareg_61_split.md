# Pra-registrasi riset #61: drift sesudah STOCK SPLIT di IDX

Ditulis 27 Nov 2026 SEBELUM return sesudah split dilihat (yang sudah dilihat: hanya JUMLAH split per tahun & sebaran rasio di `raw/aksi_idx`).

## Dugaan & alasan
- Ikenberry-Rankine-Stice 1996 (JFQA), Desai-Jain 1997 (JB): saham yang split mengungguli pasar ~+7–8% setahun sesudahnya
  (manajer memberi sinyal optimisme; investor bereaksi kurang). Split BALIK (reverse) sebaliknya: tertinggal.
- Di IDX: investor ritel dominan & suka harga per lembar murah (lot 100 lembar) → split menambah permintaan ritel & likuiditas.
- Bantahan: Boehme-Danielsen 2007 (JFQA): drift sesudah split HILANG setelah dikontrol momentum (split terjadi setelah harga naik).
  Byun-Rozeff 2003: drift kecil & rapuh terhadap metode. Perkiraan jujur: U1 positif, t 1–2,5; U2 (kontrol momentum) lebih lemah.

## Data & peristiwa
- `raw/aksi_idx/semua.parquet` (Yahoo): kolom `split` = rasio. SPLIT MAJU = rasio >= 1,5 (rasio 1,02–1,4 kebanyakan
  rights issue/saham bonus yang dicatat Yahoo sebagai split → dibuang). Split balik = rasio <= 0,67 (hanya info, ~23 peristiwa).
- d0 = tanggal EX (hari bursa pertama >= tanggal). Masuk = tutup d0 (tanggal ex diumumkan jauh sebelumnya lewat RUPS/keterbukaan
  informasi → bisa dieksekusi). Harga = Adj Close Yahoo (disesuaikan split), dibersihkan `bersih_idx`.
- Syarat saham (dihitung s/d d−1): median nilai transaksi 60 hari >= Rp1 M, >= 80% hari aktif 250 hari; harga tutup d0 >= Rp100.
  Satu peristiwa per saham per 60 hari bursa. Kedua jendela berakhir <= 2018-12-31 (data uji 2019+ DIKUNCI).

## Uji (|t| > 3, dua arah) — PORTOFOLIO WAKTU KALENDER (Jaffe 1974; Mitchell-Stafford 2000)
Tiap hari bursa: rata-rata abnormal HARIAN semua saham yang sedang di hari 1..60 sesudah masuk; dijumlah per bulan kalender
(bulan dgn >= 5 hari aktif); t antar bulan. Semua peristiwa terpakai, tanpa tumpang tindih.
- U1: abnormal harian = return saham − keranjang 30 likuid. Dugaan +.
- U2: abnormal harian = return saham − rata-rata return saham lain yang lolos syarat di KUINTIL momentum yang sama (return 250 hari
  s/d d0, kelompok ditetapkan di d0). Dugaan + (lebih lemah).
- Info: rata-rata/median per peristiwa +20/+60/+120 hari (vs keranjang), return hari ex, split balik (kalender), paruh waktu, jumlah per tahun.
- Strategi long-only (kalau U1/U2 lolos) dinilai terpisah dgn biaya B; TIDAK dinilai di sini.

CATATAN PERUBAHAN DESAIN (sebelum data asli dilihat): rancangan awal = rata-rata per bulan peristiwa + hanya bulan non-tumpang tindih
(tiap 3 bulan). Tes kode menunjukkan itu membuang ~2/3 peristiwa (tiruan +5% → t 1,3) → diganti portofolio kalender (baku literatur).
DAYA UJI (diakui di depan): hanya ~57 split maju lolos saringan likuiditas 2004–2018; tiruan +5%/60 hari (derau harian 3%) → t +2,4;
acak → t +1,0. Efek sebesar literatur (~+2% per 60 hari) praktis TIDAK terdeteksi. Hasil negatif = "belum terbukti, daya uji rendah".

## Uji kode
`--tes-tiruan` (abnormal peristiwa diganti derau + 5%) harus terdeteksi; `--tes-kosong` (derau) ≈ 0; `--potong-data` → IDENTIK.
