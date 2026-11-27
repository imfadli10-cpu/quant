# Pra-registrasi riset #64: anjlok & TUTUP DI TERENDAH (mirip ARB) → saham IDX 20/60 hari sesudahnya

Ditulis 27 Nov 2026 SEBELUM return sesudah peristiwa dilihat (cermin #60 yang menguji sisi atas).

## Dugaan & alasan (DUA ARAH, teori bertentangan)
- (−) BERLANJUT: batas harga memotong tekanan jual → harga terus turun hari-hari berikutnya (Kim-Rhee 1997 JF, Tokyo; Chen-Rui-Wang 2005,
  China: batas bawah diikuti lanjutan); kabar buruk diserap lambat (ritel menjual bertahap).
- (+) MEMANTUL: penurunan tajam tanpa kabar = tekanan likuiditas / panik → berbalik (Bremer-Sweeney 1991 JF: turun ≥ 10% sehari memantul;
  Cox-Peterson 1994; Nagel 2012: pemberi likuiditas dibayar). Di IDX ritel yang panik + margin call → pantulan masuk akal.
- Perkiraan jujur: pantulan 1–5 hari (sebagian tak bisa dibeli karena masih terkunci), sesudahnya ±0; |t| < 3.

## Peristiwa (aturan BEBAS dari batas ARB resmi yang berubah: asimetris 2015 & 2020–2023, 15% sejak Apr 2025)
- d0: Close/Close(d−1) − 1 <= −10% DAN Close <= Low × 1,0001 (tutup di terendah) DAN Volume > 0; harga Yahoo dibersihkan `bersih_idx`.
- Syarat saham (s/d d−1): harga >= Rp100, median nilai transaksi 60 hari >= Rp1 M, >= 80% hari aktif 250 hari. 1 peristiwa/saham/20 hari bursa.
- MASUK: tutup hari pertama k = 1..5 sesudah d0 yang BUKAN hari 'anjlok >= 10% & tutup di terendah' (masih terkunci = tak bisa dibeli wajar).

## Uji (|t| > 3, dua arah) — PORTOFOLIO WAKTU KALENDER (seperti #61)
- Tiap hari: rata-rata abnormal harian (saham − keranjang 30 likuid) peristiwa yang sedang di hari 1..H sesudah masuk; dijumlah per bulan
  kalender (bulan >= 5 hari aktif); t antar bulan.  U1: H = 20.  U2: H = 60.
- Info: rata-rata/median per peristiwa +20/+60 (vs keranjang), return d0→d+1 (tak bisa dibeli), porsi masuk tertunda, per tahun, paruh.
- Kalau U1/U2 positif & lolos: strategi beli-saja dinilai TERPISAH dgn biaya B (bukan di sini). Data uji 2019+ DIKUNCI.

## Uji kode
`--tes-tiruan` (return harian palsu + drift 5%/H) & `--tes-kosong`; `--potong-data` → IDENTIK. Daya uji dilaporkan sebelum data asli.

## Hasil tes kode (SEBELUM data asli)
285 peristiwa 2002-03..2018-09 (146 saham), masuk tertunda 3%; bulan kalender aktif U1 137, U2 180. Tiruan drift +5%/20 hari (derau harian 3%):
U1 t +2,86 (DAYA UJI U1 RENDAH), U2 t +6,40; acak: U1 −1,51, U2 −0,23. Desain TIDAK diubah.
