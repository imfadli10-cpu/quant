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
