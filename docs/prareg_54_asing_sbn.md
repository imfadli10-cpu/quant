# Pra-registrasi riset #54: arus asing di SBN → saham Indonesia (data latih saja)

Ditulis 26 Nov 2026 SEBELUM hubungan kepemilikan SBN dengan return saham dilihat. Aturan lengkap: docstring `riset_54_asing_sbn.py`.
Sebelum menulis, yang dilihat dari data hanya KETERSEDIAAN (jumlah tanggal per tahun/jenis) & sb sinyal (0,84%/4 mg), bukan return.

## Dugaan & bacaan
- Arus asing di obligasi Indonesia MENDAHULUI arus asing di saham (studi data harian, journal.ipb.ac.id abq 74168) → dugaan POSITIF.
- Bantahan: arus EM berkorelasi dgn return periode sama, lemah memprediksi (EMFT 2020, v56 i2 p260); kepemilikan asing SBN digerakkan
  faktor global (IMF Selected Issues 2023); riset #19 (TIC) negatif. Perkiraan jujur t < 2.

## Uji (3; |t| robust > 3; dua arah)
- U1 arus non-residen 4 minggu (% SBN beredar, jeda 7 hari, dibatasi ±3) → keranjang 30 likuid IDX minggu depan (2014-02..2018-12).
- U2 sama → EIDO minggu depan.
- U3 perubahan porsi asing bulan m (pp) → keranjang bulan m+2 (2003..2018; SUN s/d 2009, SBN 2010+).
- Info: arus minggu yang sama (cek kewajaran), versi swasta saja, paruh waktu.

## Tes kode (data palsu, SEBELUM data asli)
| Tes | U1 t | U2 t | U3 t |
|---|---|---|---|
| kosong | −0,21 | +1,06 | −1,41 |
| tiruan (+0,5%/mg per +1% arus; +2%/bln per +1 pp) | +2,26 | +3,12 | +2,64 |

DAYA UJI RENDAH: efek tiruan sebesar itu (≈ 0,4% per minggu per 1 sb sinyal = besar) pun hanya t 2,3–3,1. Hasil negatif = "tidak terdeteksi
pada daya uji ini", BUKAN bukti tidak ada. Bug ditemukan tes: selisih Period bulanan memberi offset (bukan 1) → U3 kosong; diperbaiki sebelum data asli.
