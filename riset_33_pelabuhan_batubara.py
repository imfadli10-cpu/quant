"""
RISET #33: EKSPOR CURAH KERING PELABUHAN KALIMANTAN (IMF PortWatch, sinyal kapal) -> SAHAM BATU BARA IDX vs PASAR
==============================================================================================================

DUGAAN (ditulis 2026-11-21 SEBELUM histori pelabuhan selesai diunduh & SEBELUM dilihat; di-commit sebelum dijalankan)
-------------------------------------------------------------------------------------------------------------------
Batu bara Indonesia diekspor lewat pelabuhan & titik muat di Kalimantan dengan kapal CURAH KERING. Volume muat dari data kapal
(AIS) terlihat ~1 minggu setelah kejadian, jauh sebelum laporan produksi kuartalan emiten & data ekspor BPS (~1 bulan).
  H: pertumbuhan volume ekspor curah kering Kalimantan (dibanding tahun lalu) -> saham batu bara lebih baik dari pasar
     sesudahnya (pasar belum menyerap informasi volume). Dua arah diuji (volume tinggi bisa juga berarti harga sedang jatuh).
Perkiraan jujur: harga batu bara (Newcastle) mendominasi saham batu bara & volume relatif stabil; saya kira t < 2.

DATA: PortWatch `raw/histori/pelabuhan/<tahun>` + harian; pelabuhan Indonesia (ISO3 IDN) di kotak KALIMANTAN (bujur 108..119,
  lintang -4,5..4,5; koordinat dari layanan PortWatch_ports_database); kolom export_dry_bulk (ton) dijumlah per minggu.
  SINYAL minggu w = log(jumlah 4 minggu s/d w-2) - log(jumlah 4 minggu yang sama setahun lalu) (jeda 2 minggu: data PortWatch
  terlambat ~1 minggu; pertumbuhan tahunan menghapus musim).
  TARGET: keranjang batu bara (PTBA, ITMG, ADRO, BUMI, INDY, HRUM; yang punya harga) - keranjang 30 saham paling likuid.
PEMBAGIAN SENDIRI (semua data PortWatch >= 2019; ditetapkan sekarang): LATIH minggu sinyal 2020-01..2022-12 (2019 habis untuk
  pertumbuhan tahunan), UJI 2023+ DIKUNCI (--buka-uji sekali, hanya kalau latih lolos).
UJI (2; |t| > 3; dua arah):
  U1 (BATUBARA - PASAR) minggu w+1 pada sinyal (t robust White).
  U2 (BATUBARA - PASAR) 4 minggu w+1..w+4 TANPA tumpang tindih (tiap minggu ke-4) pada sinyal.
Uji kode: --tes-tiruan & --tes-kosong.
"""
