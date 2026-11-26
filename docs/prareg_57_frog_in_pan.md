# Pra-registrasi #57: "frog-in-the-pan" (Da, Gurun & Warachka 2014) di IDX

Ditulis 27 Nov 2026 SEBELUM ukuran kontinuitas dihitung pada data IDX asli. Detail di docstring `riset_57_frog_in_pan.py`.
- ID = tanda(PRET 12-1) x (%hari turun − %hari naik) di jendela pembentukan; ID kecil = momentum KONTINU.
- U1: IC(−ID, return bulan depan) di antara pemenang (S1 40% teratas), dugaan +. U2 (penentu strategi): FIP = pemenang dgn ID <= median,
  bersih biaya B − semesta. |t| > 3. Latih 2004-12..2018-10, data uji 2019+ DIKUNCI.
- Lolos U1 = kandidat FITUR model penampang; lolos U2 = kandidat paper trading (pra-registrasi data uji terpisah).

## Tes kode
| Tes | U1 IC pemenang | U2 FIP bersih − semesta | FIP − momentum biasa |
|---|---|---|---|
| kosong (return acak) | −0,029 t −1,88 | −0,47% t −2,60 (= biaya 0,39%) | t −1,97 |
| tiruan (+2% x z(−ID) pemenang) | +0,161 t +10,0 | +1,01% t +5,52 | t +4,46 |
