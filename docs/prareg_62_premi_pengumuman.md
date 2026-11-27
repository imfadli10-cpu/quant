# Pra-registrasi riset #62: premi BULAN PENGUMUMAN LABA di IDX

Ditulis 27 Nov 2026 SEBELUM return dilihat (yang sudah dilihat: jumlah pengumuman per tahun & per bulan kalender di `raw/laba_idx`).

## Dugaan & alasan
- Beaver 1968; Frazzini-Lamont 2007 (NBER); Barber-De George-Lehavy-Trueman 2013 (JFE, 18 negara): saham yang DIJADWALKAN mengumumkan laba
  di bulan depan memberi return lebih tinggi bulan itu (+~0,5–1%/bln). Penjelasan: risiko pengumuman yang tak bisa didiversifikasi, dan
  perhatian investor yang melonjak di sekitar pengumuman (pembeli ritel lebih banyak daripada penjual; tidak bisa short mudah).
- Di IDX jadwal emiten sangat tetap (#58: hanya 8% pengumuman >= 14 hari lebih lambat dari tahun lalu) → bulan pengumuman bisa diramal
  dari bulan yang sama tahun lalu TANPA informasi masa depan. Ritel dominan → tekanan beli perhatian masuk akal.
- Bantahan: cakupan Yahoo hanya ~40–60 saham besar/tahun; pengumuman menumpuk di Apr/Jul/Okt (pembanding tipis di bulan itu);
  #22 (bulan dividen, mekanisme mirip) GAGAL. Perkiraan jujur: U1 positif, t 1–2,5; U2 gagal (perputaran tinggi).

## Desain (kerangka #13: semesta #2 `lolos`, sinyal akhir bulan i, beli tutup hari bursa pertama bulan i+1, jual hari bursa pertama i+2)
- Bulan target T = bulan kalender i+1. DIRAMAL MENGUMUMKAN = saham punya pengumuman laba (eps_aktual terisi) di bulan kalender T−12.
- Kelompok banding = saham TERLIPUT: punya >= 1 pengumuman di 24 bulan sebelum akhir bulan i (tanggal <= akhir bulan i), di semesta `lolos`.
- Bulan dipakai kalau >= 5 saham di tiap kelompok. Keluar (tanggal jual) <= 2018-12-31; data uji 2019+ DIKUNCI.

## Uji
- U1 (|t| > 3, dua arah; dugaan +): rata-rata per bulan [return diramal-mengumumkan − return terliput lain], t antar bulan.
- U2 (strategi, t > +3 saja): beli semua saham diramal-mengumumkan (bobot sama), BERSIH biaya B (0,4% + 1,2 × tick historis) − semesta.
- Info: tingkat ketepatan ramalan (porsi yang benar mengumumkan di T), per musim (Mar–Apr / Jul–Agu / Okt–Nov / lainnya), paruh waktu.

## Uji kode
`--tes-tiruan` (return palsu + 2% bagi diramal-mengumumkan) harus terdeteksi; `--tes-kosong` ≈ 0; `--potong-data` → IDENTIK. Daya uji dilaporkan.

## Hasil tes kode (SEBELUM data asli)
87 bulan latih terpakai (2006-02..2018-09), median 13 diramal vs 27 banding; ketepatan ramalan 57% (tanggal Yahoo tak lengkap).
Tiruan +2%/bln → U1 t +4,69; acak → t −0,24; U2 acak −0,91% t −2,65 (biaya 0,78%/bln: keranjang berganti tiap bulan → aturan t > +3 benar).
DAYA UJI: efek sebesar literatur (+0,5–1%/bln) → perkiraan t U1 hanya ~1–2,3. Hasil negatif = "belum terbukti, daya uji terbatas".
