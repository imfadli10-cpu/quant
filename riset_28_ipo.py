"""
RISET #28: KINERJA SAHAM IPO INDONESIA SETELAH 'DEMAM' AWAL (e-IPO + harga Yahoo)
=============================================================================

DUGAAN (ditulis 2026-11-21 SEBELUM data detail IPO lengkap & SEBELUM harga IPO dilihat; di-commit sebelum dijalankan)
---------------------------------------------------------------------------------------------------------------
Ritter (1991) & banyak studi pasar berkembang: saham IPO melonjak di hari-hari awal (di IDX sering ARA berturut-turut),
lalu KINERJA JANGKA PANJANGNYA BURUK dibanding pasar (euforia ritel mereda, saham pengendali bebas dijual setelah
masa kunci). Dugaan: membeli saham IPO di tutup hari bursa ke-5 setelah pencatatan lalu menahan 120 hari bursa
(~6 bulan) memberi return LEBIH RENDAH dari keranjang 30 saham paling likuid.
  H2: IPO kecil (nilai penawaran = saham ditawarkan x harga final, di bawah median) lebih buruk dari IPO besar.
Kegunaan kalau terbukti: HINDARI saham IPO baru (filter risiko), bukan strategi beli. (Short tidak bisa di IDX.)

PEMBAGIAN DATA SENDIRI (ditetapkan sekarang; semua e-IPO ada di periode 2020+, aturan global 2019+ tidak bisa dipakai):
  LATIH = IPO dengan tanggal pencatatan <= 2023-06-30 ; UJI = sesudahnya (DIKUNCI, --buka-uji hanya sekali kalau latih lolos).
DATA: e-IPO `raw/ipo/detail.parquet` status Closed dengan tanggal pencatatan & harga final; harga harian Yahoo
  (`data/raw/harga_idx/<KODE>.parquet` atau `bersih/harga_idx`). IPO tanpa harga Yahoo dilaporkan (survivorship).
UJI (2; |t| > 3; t = rata-rata antar IPO / (sb/akar n)):
  U1 selisih return (IPO d5 -> d125) - (keranjang 30 periode sama). Dugaan: NEGATIF.
  U2 selisih U1 antara IPO KECIL dan BESAR (t Welch). Dugaan: kecil lebih negatif.
Diagnosis: return hari pertama (harga final -> tutup hari 1) & hari 1-5, jumlah hari ARA, porsi IPO tanpa harga.
Uji kode: --tes-tiruan (IPO tiruan dengan -10% selama pegang) & --tes-kosong.
"""
