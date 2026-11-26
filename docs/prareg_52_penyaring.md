# Pra-registrasi riset #52: MESIN PENYARING MASSAL "data aneh" (penampang saham IDX)

Ditulis 26 Nov 2026, SEBELUM satu pun return saham dihubungkan dengan variabel panel. Di-commit sebelum dijalankan pada data asli.
Yang boleh dilakukan sebelum commit ini: membangun panel (selesai) & menjalankan kode pada return PALSU (`--tes-tiruan`, `--tes-kosong`).

## 1. Pertanyaan
Riset #3–#33 menguji variabel makro/alam sebagai TIMING SATU keranjang (breadth ~1) dan hampir semuanya gagal. Hukum Grinold-Kahn:
IR ≈ IC × √breadth → variabel yang sama bisa berguna kalau dipakai PENAMPANG (membedakan saham satu dengan yang lain).
Dugaan: saham yang PEKA terhadap suatu variabel (cuaca, harga pangan, kredit bank, posisi spekulan, likuiditas global...) bereaksi
LAMBAT terhadap berita variabel itu (difusi informasi bertahap: Hong-Stein 1999; Hong-Torous-Valkanov 2007 "industries lead";
Menzly-Ozbas 2010; Cohen-Frazzini 2008 "economic links"). Investor jarang memperhatikan variabel yang "tidak berhubungan" → reaksi
lebih lambat (DellaVigna-Pollet 2009, perhatian terbatas). Alasan pengguna: Renaissance mencari banyak sinyal lemah dari data aneh.

## 2. Data
- Saham & return: kerangka riset #13 (semesta S2 `lolos`: harga ≥ Rp100, median nilai transaksi 60 hari ≥ Rp1 M, ≥ 80% hari aktif;
  harga dibersihkan `bersih_idx`). `ret_pegang[t]` = tutup hari bursa pertama bulan t+1 → tutup hari bursa pertama bulan t+2.
- Variabel: SEMUA seri di `data/olah/panel_*.parquet` (bps, bps_sambung, fred, alam, pasar, lain, seki).
  Nilai dipakai di sinyal akhir bulan t HANYA bila `tersedia` ≤ akhir bulan t + 1 hari (dibeli di tutup hari bursa pertama t+1).

## 3. Konstruksi (ditetapkan sekarang, tidak diubah setelah melihat hasil)
- BERITA Δx(t): bila di bulan t terbit pengamatan BARU (bulan pengamatan lebih baru dari yang tersedia di akhir t−1), Δx(t) = perubahan
  pengamatan terbaru terhadap pengamatan sebelumnya dari seri yang sama: log-rasio bila seluruh seri > 0, selisih biasa bila tidak.
  panel_fred & panel_bps_sambung: pakai `tumbuh1` yang sudah dihitung di dalam vintage/segmen (bila seri tidak selalu positif → selisih `nilai`).
  Tidak ada pengamatan baru → Δx(t) = 0 (bulan itu tidak dinilai). Δx diubah jadi z dengan simpangan baku Δx≠0 MASA LALU (min 12 berita),
  DIPOTONG ±3 (pelajaran #30).
- Return kontemporer bulan j: rc(j) = ret_pegang[j−1] (≈ bulan j), dikurangi rata-rata semesta bulan itu.
- KELUARGA A (utama, "peka lalu telat"): beta_i(t) = kemiringan rc_i(j) terhadap z(j), j = t−60..t−1 (min 36 bulan return & 12 berita).
  Skor s_i(t) = beta_i(t) × z(t).
- KELUARGA B ("prediktif langsung"): beta_i(t) = kemiringan r_i(j+1) [= ret_pegang[j], dikurangi rata semesta] terhadap z(j), hanya pasangan
  yang SUDAH terealisasi sebelum akhir bulan t (j+1 ≤ t−1), jendela 60 bulan, min 36. Skor = beta × z(t).
- Ukuran per variabel × keluarga: IC peringkat (Spearman) bulanan antara s(t) dan ret_pegang[t] − rata semesta, di bulan z(t) ≠ 0 dan
  ≥ 30 saham punya skor. t = rata IC / (sb/√n). Diuji hanya bila ≥ 40 bulan IC di periode latih.

## 4. Periode & keputusan
- LATIH (penyaringan): bulan sinyal yang tanggal JUAL ≤ 2018-12-31 (aturan kerangka). Sinyal pertama paling awal ~2003 (butuh 36 bln beta).
- Koreksi uji ganda: Benjamini-Hochberg q = 0,05 atas SEMUA uji (A ∪ B, semua variabel yang memenuhi syarat), p dua arah dari t (normal).
  Jumlah uji dilaporkan. Ini menggantikan |t| > 3 (dengan ribuan uji, BH lebih ketat: ambang efektif |t| ≈ 4+).
- VALIDASI 2019–2022 (dibuka HANYA untuk variabel yang lolos BH; bulan beli ≥ 2019-01-01 dan jual ≤ 2022-12-31):
  skor gabungan = rata-rata peringkat skor variabel lolos (arah = tanda IC latih), dibobot sama. LOLOS VALIDASI bila IC gabungan > 0 dan
  t > 2. Juga dilaporkan per variabel (informasi). 2023+ TETAP DIKUNCI untuk uji akhir model gabungan vs S2 (pra-registrasi terpisah).
- Bila 0 variabel lolos BH: hasil = "belum terbukti dengan uji penampang ini (desain, periode, daya uji X)", BUKAN "variabel tidak berguna"
  (prinsip pengguna 22 Nov 2026). Laporkan juga 20 t terbesar & sebaran t vs sebaran acak (berapa |t| > 3 yang diharapkan kebetulan).

## 5. Daya uji & tes kode (WAJIB sebelum data asli; hasil dicatat di docstring skrip)
- `--tes-kosong`: return palsu acak tanpa hubungan → jumlah lolos BH harus ≈ 0 (≤ q × jumlah, praktis 0–2).
- `--tes-tiruan`: return palsu dengan 20 variabel TERTANAM (r(t+1) mengandung γ × beta_i × z(t), beta_i sungguhan dari kepekaan tertanam)
  → laporkan berapa dari 20 ditemukan dan berapa temuan palsu, untuk IC tertanam ~0,03 / 0,05 / 0,08.
- `--potong-data`: semua file dipotong 2018-12-31 → hasil latih IDENTIK (cek kebocoran).

## 6. Keterbatasan yang diakui di depan
- Survivorship IDX (daftar saham = yang masih tercatat). Data BPS/SEKI/alam/BIS = versi TERREVISI (pit=False) → temuan dari seri pit=False
  dilaporkan terpisah & dicurigai lebih dulu. Variabel sangat berkorelasi (34 provinsi × komoditas) → BH tetap sah di bawah ketergantungan
  positif, tapi temuan berkelompok = SATU ide. Beta per saham dari 60 bulan berderau → daya uji terbatas; dilaporkan lewat tes tiruan.
- Ini uji PERINGKAT (IC), belum strategi bersih biaya; variabel lolos menjadi FITUR model gabungan (#21/#36 gaya) dgn pra-registrasi sendiri.
