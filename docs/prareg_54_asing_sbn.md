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

## HASIL DATA ASLI (26 Nov 2026) — ❌ TIDAK LOLOS (belum terbukti pada daya uji rendah)
- U1 IDX minggu depan +0,07% per +1% arus, t +0,35 (242 mg) | U2 EIDO +0,09%, t +0,32 (254 mg) | U3 bulanan −0,91% per +1 pp, t −1,24 (179 bln).
- Versi swasta saja (tanpa pemerintah & bank sentral asing): t +0,06 / −0,08.
- CEK KEWAJARAN lolos: arus minggu yang SAMA ↔ keranjang minggu yang sama +1,20% per +1%, t +3,35 → data bermakna (asing masuk SBN saat
  saham naik), tetapi informasinya SUDAH masuk harga di minggu yang sama (sesuai EMFT 2020). Tidak ada keterlambatan yang bisa dipakai
  dgn jeda konservatif 7 hari.
- Cek `--potong-data`: IDENTIK. (Paruh pertama U1 'nan' = ada minggu tanpa return keranjang di paruh itu; info saja.)
- Tafsiran: belum terbukti sebagai sinyal timing. Data tetap berguna: (a) jeda nyata ~3 hari (bukan 7) bisa diuji ulang setelah jeda terbit
  terukur dari `pertama_terlihat` ke depan; (b) fitur rezim/risiko; (c) penampang (saham yg disukai asing × arus) = desain lain.
