# Pra-registrasi #59: lead-lag dalam sektor (Hou 2007) di IDX

Ditulis 27 Nov 2026 SEBELUM hubungan pemimpin-pengikut dihitung pada data asli. Detail di docstring `riset_59_lead_lag_sektor.py`.
- Pemimpin = 3 saham paling likuid per sektor (sektor >= 6 saham semesta); L_s = rata-rata return bulan ini pemimpin (harga akhir bulan, tanpa bocor).
- U1 IC(L_s, return bulan depan pengikut); U2 Fama-MacBeth koef L_s dikontrol return 1 bulan sendiri; U3 beli pengikut sepertiga sektor teratas
  bersih biaya B − semesta. Lolos: U1/U2 |t| > 3 (= kandidat fitur), U3 t > +3. Latih s/d 2018-10, data uji DIKUNCI.

## Tes kode
| Tes | U1 | U2 | U3 bersih |
|---|---|---|---|
| kosong | −0,003 t −0,26 | t −0,41 | −1,14%/bln t −4,27 (= biaya 1,07%) |
| tiruan (+0,3 x L_s) | +0,150 t +11,2 | t +10,6 | +1,34% t +4,98 |
PERBAIKAN SEBELUM DATA ASLI: aturan U3 semula |t| > 3 → tes kosong 'lolos' krn biaya → diubah jadi t > +3.
