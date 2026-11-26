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

## HASIL data asli (27 Nov 2026) — ❌ tidak lolos; pola "LOTRE"
181 peristiwa, 102 saham, 95 bulan.
- U1 +20 hari: rata-rata +0,75% TAPI median −4,02%; per bulan t −0,08 (paruh −0,2/+0,1).
- U2 +60 hari: rata-rata −0,29%, median −5,81%; t +0,10 (30 bln non-tumpang tindih).
- Lanjutan d0 → d+1 (tak bisa dibeli): +0,58% (median 0,00%); masuk tertunda (terkunci) 6%.
- --potong-data: IDENTIK. Data uji tidak dibuka.
- Tafsiran: kebanyakan lonjakan berbalik (median negatif), sebagian kecil melambung → rata-rata ≈ 0 (sama dgn IPO #28). Tidak ada magnet yg bisa
  dibeli & tidak ada pembalikan rata-rata yg bisa dipakai long-only. Daya uji rendah (181 peristiwa likuid). Ukuran median/kuantil (bukan rata-rata)
  bisa jadi fitur risiko (hindari) di model penampang — perlu pra-registrasi sendiri.
