"""
RISET #24: TITIK API KEBAKARAN (satelit NASA) -> SAHAM SAWIT IDX vs PASAR, data LATIH saja
========================================================================================

DUGAAN (ditulis 2026-11-20 SEBELUM data histori titik api diunduh/dilihat; di-commit sebelum dijalankan)
----------------------------------------------------------------------------------------------------
Dua teori yang arahnya BERLAWANAN (maka semua uji dua arah):
  (a) RISIKO: kebakaran besar di Sumatra/Kalimantan = sorotan pemerintah & internasional pada perusahaan perkebunan
      (izin dicabut, denda, boikot) + asap mengganggu operasi -> saham sawit TERTINGGAL pasar sesudahnya.
  (b) PASOKAN: kebakaran = kemarau panjang -> produksi sawit 6-12 bulan kemudian turun -> harga CPO naik -> saham sawit
      MENGUNGGULI pasar (riset #16: ONI -> sawit tidak terbukti, tapi titik api lebih langsung dari ONI).
Perkiraan jujur: informasi titik api tersedia publik (peta FIRMS), pasar mungkin sudah menyerapnya. t < 2.

DATA: MODIS_SP (1 km, konsisten 2000-11..2018), titik api di Sumatra (bujur 95-106, lintang -6..6) + Kalimantan
  (bujur 108-119, lintang -4,5..4,5), confidence >= 30. FIRMS NRT tersedia ~3 jam setelah satelit lewat -> data hari d
  diketahui sebelum IDX buka hari d+1.
  Keranjang SAWIT = AALI, LSIP, SGRO, SIMP, BWPT (riset #3/#16), bobot sama; PASAR = keranjang 30 saham paling likuid
  (riset #4/#15). Target = return SAWIT - PASAR.
  Anomali api minggu w = log(1 + jumlah titik minggu w) - rata-rata log(1 + jumlah) minggu-ke-sama (minggu ISO) di 5 tahun
  SEBELUMNYA (musim kemarau Agu-Okt selalu ramai; yang dihitung kelebihannya). Bulanan sama dengan bulan kalender.
UJI (3; dua arah; |t| > 3):
  U1 MINGGUAN: anomali minggu w -> SAWIT-PASAR minggu w+1 (beli tutup hari bursa pertama w+1), t robust White.
  U2 BULANAN: anomali bulan m -> SAWIT-PASAR bulan m+1, t robust White.
  U3 6 BULAN (teori b): anomali bulan m -> SAWIT-PASAR bulan m+1..m+6; jendela tumpang tindih -> t = TERKECIL antara
     Newey-West(6) dan regresi tanpa tumpang tindih (pelajaran riset #16).
Data uji 2019+ DIKUNCI. Uji kode: --tes-tiruan & --tes-kosong (anomali palsu, return palsu dengan/ tanpa pola).
"""
