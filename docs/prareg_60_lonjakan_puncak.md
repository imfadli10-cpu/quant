# Pra-registrasi #60: lonjakan 'tutup di puncak' (mirip ARA) -> saham IDX 20/60 hari

Ditulis 27 Nov 2026 SEBELUM return sesudah peristiwa dilihat. Detail di docstring `riset_60_lonjakan_puncak.py`.
Teori dua arah: magnet/penemuan harga tertunda (Kim-Rhee 1997) vs reaksi berlebihan/lotre (Bali-Cakici-Whitelaw 2011).
- Peristiwa: return >= +20% & Close = High & volume > 0, saham lolos saringan #2 (dihitung s/d d-1); bebas dari aturan ARA resmi yang
  berubah antar tahun (35/25/20 simetris resmi baru Jan 2017; ARB asimetris 2015 & 2020-2023).
- Masuk: tutup hari pertama sesudah d0 yang tidak terkunci (<= 5 hari). U1 abnormal +20 hari, U2 +60 hari, vs keranjang 30, rata-rata per bulan.
- |t| > 3 dua arah. Latih: jendela 60 hari berakhir <= 2018-12-31. Data uji DIKUNCI.

## Tes kode (peristiwa asli, abnormal diganti palsu)
181 peristiwa (2002-04 .. 2018-09), 102 saham, 95 bulan; masuk tertunda 6%.
| Tes | U1 | U2 |
|---|---|---|
| kosong | +1,65% t +0,50 | t +1,60 |
| +5% | +6,65% t +4,59 | t +2,99 |
Daya uji: hanya efek ~5%+ per 20 hari yang terdeteksi (peristiwa likuid jarang).
