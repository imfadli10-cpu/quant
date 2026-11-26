# Pra-registrasi #58: pengumuman laba yang telat (vs kebiasaan emiten) -> saham IDX 20 hari

Ditulis 27 Nov 2026 SEBELUM hubungan keterlambatan-return dihitung. Detail di docstring `riset_58_laba_telat.py`.
Literatur: Givoly-Palmon 1982; Begley-Fischer 1998; deHaan-Shevlin-Thornock 2015.
- Telat = tanggal − pengumuman terdekat setahun lalu (±45 hr) − 365; TELAT >= +14 hari. Masuk hari bursa ke-2, tahan 20 hari, vs keranjang 30.
- U1 TELAT − tidak telat per kuartal; U2 kemiringan per +10 hari (Fama-MacBeth). |t| > 3, dugaan negatif. Latih s/d 2018, uji DIKUNCI.

## Tes kode (60 saham palsu x kuartal, 3.038 peristiwa)
| Tes | U1 | U2 |
|---|---|---|
| kosong | +0,33% t +0,73 | t +1,36 |
| pola −2%/20 hr utk TELAT | −1,68% t −3,78 | t −2,04 |
Daya uji: efek −2% baru pas-pasan terdeteksi; data asli (saham diliput analis) kemungkinan lebih sedikit peristiwa.

## HASIL data asli (27 Nov 2026) — ❌ tidak lolos (daya uji rendah)
1.249 peristiwa berpasangan (2005-10 .. 2018-11), TELAT hanya 103 (8%; median telat 0 hari = jadwal emiten IDX sangat tetap).
- U1 TELAT − tidak telat +1,20%/kuartal t +0,92 (hanya 14 kuartal memenuhi syarat; paruh −0,1/+1,1) | U2 kemiringan −0,006% per 10 hr t −0,03.
- Info: rata-rata gabungan TELAT −0,75% vs lainnya +0,21%; DIPERCEPAT −0,85% (112). Kejutan EPS median TELAT −3,2% vs −1,8%; porsi negatif 55% vs 54%
  → kabar buruk di kelompok telat hanya sedikit lebih banyak.
- --potong-data (semua data > 2018 dibuang sebelum dibaca): IDENTIK. Data uji tidak dibuka.
- Belum terbukti; uji ulang kalau ada tanggal pengumuman untuk SEMUA emiten (bukan hanya yang diliput analis), mis. dari laporan keuangan IDX.
