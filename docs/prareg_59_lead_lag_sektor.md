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

## HASIL data asli (27 Nov 2026) — ❌ tidak lolos
126 bulan (2005-04 .. 2018-10), median 8 sektor, 78 pengikut/bulan.
- U1 IC(L_s, r) +0,020 t +1,40 (paruh +1,6/+0,3) | U2 koef L_s (kontrol r0 sendiri) +0,017 t +1,21 | U3 bersih −0,74%/bln t −2,25
  (kotor +0,33%, biaya 1,07% = rotasi sektor bulanan mahal).
- Info: koef return 1 bulan SENDIRI +0,060 t +3,56 (= kelanjutan 1 bulan #2 terkonfirmasi, kerangka berbeda).
- --potong-data: IC & kotor IDENTIK; biaya beda tipis (1,069 vs 1,099%) = sebab sama dgn #46. Data uji tidak dibuka.
- Arah searah Hou 2007 tapi belum terbukti; peta sektor statis & hanya 8 sektor (granularitas kasar; Hou memakai industri rinci).
  Uji ulang dgn klasifikasi lebih rinci (industry Yahoo, ~70) bila dipra-registrasi terpisah.
