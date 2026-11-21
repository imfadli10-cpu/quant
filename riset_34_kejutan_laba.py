"""
RISET #34: KEJUTAN LABA -> 'DRIFT' SAHAM IDX SETELAH PENGUMUMAN (post-earnings announcement drift), data LATIH saja
==============================================================================================================

DUGAAN (ditulis 2026-11-21 SEBELUM data laba lengkap dilihat; di-commit sebelum dijalankan)
----------------------------------------------------------------------------------------
Bernard & Thomas (1989) dan ratusan replikasi: saham dengan kejutan laba POSITIF terus mengungguli saham dengan kejutan
NEGATIF selama beberapa minggu-bulan setelah pengumuman (investor bereaksi kurang terhadap informasi laba). Efek lebih kuat
di pasar dengan banyak investor ritel & sedikit analis -> IDX kandidat bagus.
Perkiraan jujur: data kejutan Yahoo untuk IDX berisik (sebagian perkiraan beda skala/mata uang); biaya IDX tinggi.

DATA: `raw/laba_idx/semua.parquet` (Yahoo): eps_perkiraan, eps_aktual, tanggal pengumuman (waktu WIB).
  Kejutan = (aktual - perkiraan) / |perkiraan|, hanya baris dengan keduanya ada & perkiraan != 0.
WAKTU (konservatif; jam Yahoo tidak bisa dipercaya): MASUK = tutup hari bursa ke-2 setelah TANGGAL pengumuman (WIB),
  KELUAR = 20 hari bursa kemudian. Abnormal = return saham - return keranjang 30 saham paling likuid (riset #4/#15) periode sama.
SEMESTA: saham dengan median nilai transaksi 60 hari >= Rp1 miliar & harga >= Rp100 di hari MASUK (data sampai hari itu).
KELOMPOK: per kuartal kalender pengumuman, kejutan dibagi 3 (tertil) di antara peristiwa semesta (minimal 15 peristiwa/kuartal).
UJI (2; |t| > 3; t antar kuartal = rata-rata / (sb/akar n) -> peristiwa dalam kuartal yang sama tidak dianggap independen):
  U1 (TERTIL ATAS - TERTIL BAWAH) abnormal 20 hari, rata-rata per kuartal.
  U2 STRATEGI bisa dijalankan: beli TERTIL ATAS saja, abnormal 20 hari dikurangi biaya bolak-balik 0,8% (komisi 0,4% + spread).
LATIH: peristiwa dengan hari KELUAR <= 2018-12-31. UJI 2019+ DIKUNCI (--buka-uji sekali kalau latih lolos).
Uji kode: --tes-tiruan (abnormal +2% tertil atas, -2% bawah) & --tes-kosong.
"""
