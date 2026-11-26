# Pra-registrasi riset #52b: GABUNGAN banyak sinyal lemah "data aneh" (satu uji)

Ditulis 26 Nov 2026 SAAT #52 (penyaringan per-variabel) sedang berjalan pada data asli, SEBELUM hasilnya terlihat. Di-commit sebelum
satu pun angka #52 asli dibaca. Alasan: tes kode #52 (bagian 7 prareg #52) menunjukkan uji per-variabel + BH hampir pasti tidak bisa
menemukan efek realistis (IC 0,01–0,06 → t < 3 per variabel). Renaissance: banyak sinyal lemah DIGABUNG (Grinold-Kahn: IR ≈ IC × √breadth).

## Desain (memakai konstruksi #52 apa adanya: berita z_v(t), beta keluarga A, semesta & return kerangka #13)
1. Skor per variabel s_v,i(t) = beta_A,v,i(t) × z_v(t) (hanya bulan z_v(t) ≠ 0), diubah jadi peringkat persentil penampang − 0,5.
2. IC historis per variabel IC_v(τ) dihitung seperti #52. Pada bulan sinyal t, HANYA IC_v(τ) dgn return SUDAH terealisasi (τ ≤ t − 2) boleh dipakai.
3. Bobot maju-bertahap: w_v(t) = rata-rata IC_v(τ) atas SEMUA τ ≤ t − 2 yang tersedia (min 24 bulan IC; bila kurang w = 0). Tanpa pemilihan,
   tanpa ambang: variabel lemah otomatis berbobot kecil, arah dipelajari dari masa lalu.
4. Skor gabungan G_i(t) = Σ_v w_v(t) × (peringkat_v,i(t) − 0,5) / Σ_v |w_v(t)| atas variabel ber-berita bulan t.
5. UJI PENENTU (SATU): IC peringkat bulanan G(t) vs ret_pegang[t] − rata semesta, bulan sinyal 2005-01..(jual ≤ 2018-12-31).
   LOLOS bila t > 3 (satu uji, tidak perlu koreksi uji ganda). Info: paruh waktu, versi hanya pit=True, korelasi G dgn S2, IC G setelah
   S2 dikendalikan (residual peringkat), 5 kelompok G (K5−K1, kotor).
6. Bila lolos → validasi 2019–2022 SEKALI: IC G > 0 dan t > 2. 2023+ tetap dikunci (uji akhir vs S2, pra-registrasi terpisah).
   Bila gagal → "belum terbukti dgn gabungan linear maju-bertahap", bukan "data aneh tak berguna".

## Tes kode WAJIB sebelum data asli
- Return palsu tanpa pola: t G ≈ 0 (|t| < 2).
- Return palsu dgn 21 variabel tertanam (tes tiruan #52): G harus t > 3 walau tiap variabel sendiri-sendiri t < 3.
- Potong data 2018-12-31: IDENTIK.

## Keterbatasan
Bobot = rata IC masa lalu (berderau; tanpa penyusutan selain bobot kecil alami). Variabel berkorelasi tinggi (provinsi × komoditas) ikut
terhitung berkali-kali → kelompok besar mendominasi; diakui, tidak dikoreksi (koreksi = desain lain). Survivorship IDX & pit=False seperti #52.

## Amandemen (26 Nov 2026, SEBELUM #52b dijalankan pada data asli)
Tes kode (`--cepat`, 1.321 variabel) menunjukkan bobot "rata IC masa lalu" melarutkan sinyal di antara ratusan variabel derau
(median 187 variabel berbobot/bulan). Diganti PENYUSUTAN James-Stein: w_v(t) = rata IC × max(0, 1 − 4/t_v²), t_v = t IC masa lalu (≥ 24 bulan).
Hasil tes (versi tersusut): kosong t −0,44 (terkalibrasi); tiruan t +8,30 (median 27 variabel berbobot). Versi lama: kosong +0,01, tiruan +8,58.
TEMUAN DAYA UJI: tes tiruan terdeteksi terutama lewat jalur "berita persisten" (gamma = 0 pun t +7,6) — sebagian ARTEFAK pembuat data palsu
(perubahan rata-rata bulanan berautokorelasi, Working 1960). Dgn berita tertanam ACAK (`--z-acak`, hanya reaksi tertunda gamma 0,005–0,015):
versi lama t −0,94, tersusut t −1,27 → reaksi tertunda IC ≤ ~0,06 TIDAK bisa dibuktikan dgn ~100 bulan × ~50 saham. Hasil negatif #52b =
"tidak terdeteksi pada daya uji ini", BUKAN bukti tidak ada. Kriteria LOLOS (t > 3, satu uji) TIDAK diubah.
Kejujuran: kode penyusutan ditulis sebelum hasil #52 asli terlihat; sebelum amandemen ini di-commit, daftar 20 t terbesar cek potong-data #52
sempat terbaca sekilas (tidak ada yang lolos BH di daftar itu). Desain tidak diubah karena itu.

## HASIL DATA ASLI (26 Nov 2026) — ❌ TIDAK LOLOS (belum terbukti pada daya uji ini)
- 13.527 variabel, bobot tersusut; median 110 variabel berbobot per bulan (maks 278). Evaluasi 102 bulan (bulan awal belum punya bobot).
- [semua] IC G +0,0035 t +0,27 (paruh +1,05 / −0,67); setelah S2 dikendalikan −0,0018 t −0,15; K5−K1 kotor −0,39%/bln t −0,81; kor G vs S2 +0,08.
- [pit saja] IC −0,0046 t −0,33. Data uji 2019+ TIDAK dibuka.
- Tafsiran jujur: gabungan linear maju-bertahap dari ~13 ribu variabel "data aneh" tidak memberi kemampuan meranking saham IDX bulan depan
  di 2005–2018 yang bisa dibedakan dari nol. Daya uji terbatas (tes `--z-acak`: reaksi tertunda IC ≤ 0,06 tak terdeteksi) → TIDAK berarti
  variabel tak berguna; mungkin berguna di horizon lain (harian/mingguan), untuk sektor tertentu (desain terarah dgn mekanisme jelas:
  komoditas → emiten produsennya), sebagai pengatur RISIKO/rezim, atau dengan data yang lebih panjang ke depan.
- Cek `--potong-data`: IDENTIK (semua angka sama persis).
