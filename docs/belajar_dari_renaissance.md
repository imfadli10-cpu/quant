# Belajar dari Renaissance & literatur quant (riset 21 Nov 2026)

Tujuan: berhenti jadi "katak dalam tempurung". Apa yang BENAR-BENAR membuat Renaissance (Medallion) sukses, apa kata paper
akademik terbaik, dan apa artinya untuk proyek ini (trader perorangan, IDX, tanpa leverage besar, tanpa short).

## 1. Fakta tentang Medallion (sumber sekunder; strategi asli tidak pernah dipublikasikan)
- Return ~63–66%/thn sebelum biaya (1988–2018), ~37–39% setelah biaya; beta pasar & faktor NEGATIF (Cornell 2019,
  "Medallion Fund: The Ultimate Counterexample?"): bukan kompensasi risiko.
- Ribuan posisi long DAN short jangka PENDEK (jam s/d 1–2 minggu), benar hanya ~50,75% (Mercer via Zuckerman), tapi
  atas JUTAAN transaksi.
- LEVERAGE besar: rata-rata ~12,5x, sampai ~20x (Zuckerman). "An overlooked key is ample and cheap leverage."
- Biaya eksekusi sangat rendah (infrastruktur sendiri); kapasitas dibatasi (~$10 miliar, laba dibagikan tiap tahun).
- Sejarah metode: model Markov/HMM (Baum, Ax), lalu Berlekamp & Laufer merombak sistem (1989–1990) ke perdagangan jangka
  pendek; kemudian regresi/kernel & banyak sinyal digabung dalam SATU sistem; data dikumpulkan & DIBERSIHKAN obsesif.
- Simons: "The computer has its opinions and we slavishly follow them." Model menggantikan analisis fundamental.

## 2. Apa kata paper (yang relevan untuk kita)
1. **Hukum Dasar Manajemen Aktif** (Grinold & Kahn): IR = IC × √(jumlah taruhan INDEPENDEN). Sinyal lemah (IC 0,02–0,05)
   hanya berguna kalau dipakai di BANYAK taruhan independen (banyak saham × sering). Ini inti "banyak sinyal lemah".
2. **Batas t > 3** (Harvey, Liu & Zhu 2016, RFS): karena ratusan peneliti mencari faktor, ambang 2 terlalu rendah;
   sebagian besar "temuan" adalah kebetulan. (Proyek ini sudah memakai t > 3.)
3. **Machine learning menggabungkan banyak sinyal** (Gu, Kelly & Xiu 2020, RFS): pohon (boosting/random forest) &
   jaringan saraf mengalahkan regresi linear karena menangkap INTERAKSI non-linear; prediktor dominan = momentum, likuiditas,
   volatilitas. **Di pasar berkembang** (Hanauer & Kalsbach 2023, Emerging Markets Review): 32 negara, 36 variabel, ML
   mengungguli linear, tetap untung setelah biaya & larangan short, TIDAK melemah seiring waktu; model yang dilatih di
   pasar maju memprediksi pasar berkembang hampir sama baik.
4. **101 Formulaic Alphas** (Kakushadze 2016, WorldQuant): 101 sinyal nyata berhorizon 0,6–6,4 hari, korelasi antar
   sinyal rata-rata hanya ~16% → digabung = keuntungan stabil. Masalah: terlalu banyak variabel, terlalu sedikit data.
5. **Statistical arbitrage** (Avellaneda & Lee 2010): residu return saham (setelah faktor/sektor dihilangkan) cenderung
   BALIK (mean reversion); Sharpe 1,44 setelah biaya 1997–2007, MELEMAH setelah dipublikasikan (0,9; replikasi 2013–2016 0,54).
6. **López de Prado** (Advances in Financial ML): purged/embargoed cross-validation, Deflated Sharpe Ratio (koreksi
   banyak percobaan), meta-labeling; kebanyakan dana ML gagal karena backtest overfitting.
7. **IDX**: studi lokal menemukan PEMBALIKAN jangka pendek (overnight reversal, winner/loser reversal, reversal intraday),
   tapi belum ada yang menguji BERSIH biaya realistis.

## 3. Diagnosis jujur proyek kita (riset #1–#35)
- Sebagian besar riset menguji SATU sinyal untuk MEMILIH WAKTU (timing) SATU keranjang/indeks (makro, cuaca, gempa, TGA,
  VIX...). Menurut hukum Grinold-Kahn, "breadth" = 1 keranjang × ~12–52 keputusan/tahun → IR mustahil tinggi walau sinyalnya
  benar. Itu sebabnya hampir semua gagal: KESALAHAN DESAIN, bukan cuma "pasar efisien".
- Yang berhasil (S2, IC model gabungan t 4–6) justru PENAMPANG SAHAM (memilih saham relatif satu sama lain) = breadth besar.
- Hambatan utama di IDX = BIAYA (komisi 0,4% + spread 0,5–0,9%) dan TIDAK BISA SHORT → horizon terlalu pendek dibunuh biaya.
- Yang TIDAK bisa ditiru: leverage 12–20x, short, eksekusi murah, ilmuwan ratusan orang, data berbayar.

## 4. Arah baru (prioritas)
1. **Model penampang IDX versi 2 (ML)**: 40–80 fitur (momentum berbagai jendela, pembalikan 1 minggu/1 bulan, jarak ke
   puncak 52 mg, volatilitas, max return, volume & lonjakan volume, likuiditas, kejutan laba, perhatian Wikipedia, musiman,
   sektor, fundamental ke depan), target = peringkat return bulan depan; gradient boosting vs linear; uji maju bertahap
   (dilatih ulang tiap tahun, purge/embargo), dinilai SEBAGAI SATU UJI (bukan 80 uji). Portofolio long-only top-N dengan
   aturan penyangga (hemat biaya) & biaya realistis.
2. **Pembalikan jangka pendek penampang IDX** (mingguan, banyak saham, bukan keranjang) dengan aturan "trade hanya kalau
   perkiraan untung > biaya".
3. **Model biaya & eksekusi** dari data intraday 1 menit (ke depan): spread nyata, dampak harga per ukuran order.
4. Kurangi riset timing makro satu-keranjang (breadth rendah) kecuali sebagai fitur di model gabungan.
5. Paper trading tetap hakim akhir (2019+ sudah terpakai untuk S2).

## Sumber
Cornell (2019) SSRN 3504766; Zuckerman (2019) The Man Who Solved the Market; Grinold & Kahn, Active Portfolio Management;
Harvey, Liu & Zhu (2016) RFS 29(1); Gu, Kelly & Xiu (2020) RFS 33(5) / NBER w25398; Hanauer & Kalsbach (2023) Emerging
Markets Review 55, 101022; Kakushadze (2016) arXiv 1601.00991; Avellaneda & Lee (2010) Quantitative Finance 10(7);
López de Prado (2018) Advances in Financial Machine Learning (Wiley).
