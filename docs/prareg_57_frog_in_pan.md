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

## HASIL data asli (27 Nov 2026)
158 bulan (2004-12 .. 2018-10), semesta median 98, FIP 20 saham.
- **U1 ✅ LOLOS**: IC(−ID, r) di antara pemenang +0,065 t +3,83 (paruh +2,2/+3,4) — momentum kontinu lebih unggul, searah DGW.
- U2 ❌: FIP bersih − semesta +0,24%/bln t +0,78 (kotor +0,63%, biaya 0,39%); momentum biasa +0,26% t +0,65; FIP − momentum −0,03% t −0,08.
- IC −ID seluruh semesta +0,019 t +1,46 (info).
- --potong-data: IC & return kotor IDENTIK; biaya beda tipis (0,389 vs 0,404%) = sebab sama dgn #46 (split sesudah 2018 utk harga_asli).
- DIAGNOSIS (SESUDAH melihat hasil, bukan pra-registrasi): −ID berkorelasi +0,28 dgn S2 & +0,30 dgn S3 (di antara pemenang); IC pemenang S2
  t +4,58, S3 t +3,42; IC −ID SETELAH dikurangi S1/S2/S3 (residual peringkat) +0,027 t +1,80 → sebagian besar kekuatan ID = tumpang tindih dgn
  sinyal yang sudah ada; tambahan informasinya BELUM terbukti.
- Keputusan sesuai aturan: ID = kandidat FITUR model penampang (nilai tambah harus dibuktikan di model gabungan, uji maju). Data uji tidak dibuka.
