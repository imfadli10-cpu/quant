# Pra-registrasi #55: kepekaan saham terhadap arus asing SBN (penampang, mingguan)

Ditulis 26 Nov 2026 SEBELUM hubungan beta-asing dengan return saham asli dihitung. Detail desain di docstring `riset_55_beta_asing.py`.

- Dugaan: saham yang historis paling peka terhadap arus asing SBN (beta 52 minggu thd arus 1 minggu) menyusul arah arus 4 minggu
  terakhir (sinyal F #54) di minggu depan. Perkiraan jujur |t| < 2 (info makro jelas biasanya diserap minggu yang sama, #54).
- Uji (|t| > 3, dua arah): U1 rata-rata tanda(F) x IC(beta, return w+1); U2 IC ~ F (t White); U3 beli 20% skor teratas bersih 0,4%.
- Latih: minggu target berakhir <= 2018-12-31 (2014-10 .. 2018-12, ~219 minggu, ~120 saham). Data uji 2019+ DIKUNCI.
- Keputusan: lolos U1 atau U2 = kandidat FITUR model penampang (bukan strategi sendiri); U3 informasi.

## Tes kode (data palsu, arus asing ASLI, harga palsu dgn beta tetap per saham)
| Tes | cek beta minggu sama | U1 | U2 | U3 bersih |
|---|---|---|---|---|
| kosong | t +7,3 | t −0,02 | t −1,56 | t −1,65 |
| pola 0,5% x beta x F | t +5,8 | t +5,87 | t +4,31 | t +2,66 |
| pola 0,2% | t +6,8 | t +2,74 | t +1,15 | t +0,36 |

Daya uji: efek sebesar 0,5% per unit beta x arus terdeteksi; 0,2% tidak.
