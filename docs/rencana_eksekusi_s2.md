# Rencana eksekusi S2: dari paper trading ke uang sungguhan

Disusun 22 Nov 2026. Semua angka berasal dari data uji 2019-01 s/d 2026-09 (93 bulan) yang sudah dibuka sekali di riset #12b.
Aturan S2 **tidak diubah**. Angkanya deskriptif, bukan uji baru. Biaya memakai model B (0,4% + 1,2 × tick/harga).

## 1. Apa itu S2 (singkat)

- Setiap akhir bulan, ambil semua saham IDX dengan harga ≥ Rp100, median nilai transaksi 60 hari ≥ Rp1 miliar, dan aktif ≥ 80% hari bursa (= "semesta", ~200–240 saham).
- Urutkan berdasarkan **harga / harga tertinggi 250 hari** (dekat puncak 52 minggu).
- Beli **20% teratas**, bobot sama, di harga tutup hari bursa pertama bulan berikutnya. Tahan 1 bulan, lalu ulangi.
- Jumlah saham: median **40** (21–69); per 13 Nov 2026 ada **48**. Perputaran ~40%/bulan, artinya ~16–20 saham berganti tiap bulan.

## 2. Apa yang bisa diharapkan (jujur, termasuk sisi buruk)

| | S2 (bersih biaya) | Semesta (bobot sama) |
|---|---|---|
| Rata-rata per bulan | +1,61% | +0,40% |
| Per tahun (majemuk) | **+18,5%** | +1,9% |
| Penurunan terdalam dari puncak | **−29,2%** (s/d Mei 2026) | −44,2% (COVID) |
| Bulan terburuk | −13,8% (Des 2025) | −21,3% (Feb 2020) |
| Bulan rugi | 35% | 44% |

Per tahun, S2 absolut vs semesta:

| Tahun | S2 | Semesta |
|---|---|---|
| 2019 | −6,9% | −19,8% |
| 2020 | +17,8% | +31,8% |
| 2021 | +68,8% | +21,9% |
| 2022 | +19,4% | −9,8% |
| 2023 | +4,0% | −4,3% |
| 2024 | +22,1% | +1,4% |
| 2025 | +54,3% | +41,0% |
| 2026 s/d Sep | −14,1% | −27,4% |

Yang harus diterima sejak awal:
- **S2 bisa rugi dalam angka absolut** (2019, 2026). Keunggulannya relatif terhadap pasar, bukan jaminan untung.
- **Tertinggal dari pasar bisa lama dan dalam.** Kasus terburuk: tertinggal −31% (puncak Jan 2021) saat pasar memantul dari dasar COVID ("momentum crash"; bulan terburuk Okt 2020 −16,3% relatif). Kondisi sekarang (IHSG −44% dari puncak) mirip awal situasi itu.
- t = 2,9 artinya **kandidat kuat, bukan bukti pasti**. Rezim bisa berubah; S2 pernah "kering" 2011–2017.

## 3. Paper trading TIDAK bisa membuktikan S2 dalam 6 bulan

Naik-turun relatif S2 ±4%/bulan, jauh lebih besar dari keunggulan rata-ratanya (+1,2%/bulan). Walaupun S2 benar-benar bekerja, peluang S2 kalah dari pasar dalam satu jendela adalah:

| Jendela | Peluang kalah (teori) | Yang terjadi 2019–2026 |
|---|---|---|
| 3 bulan | 30% | 25% |
| 6 bulan | 23% | 17% |
| 12 bulan | 15% | 9% |

Maka paper trading **bukan** untuk "membuktikan untung". Tujuannya:
1. Memastikan pencatatan & aturan berjalan benar (tanpa melihat masa depan).
2. Mengukur **biaya nyata** (foto bid/ask jam bursa, mulai 23 Nov 2026) vs model biaya.
3. Mengukur masalah eksekusi: saham terkunci ARA saat mau beli, ARB saat mau jual, saham tersuspensi.
4. Membiasakan diri dengan disiplin bulanan (termasuk saat rugi).

## 4. Modal dan jumlah lot

IDX: 1 lot = 100 lembar, tanpa pecahan. Dari pilihan 13 Nov 2026 (48 saham, harga median Rp1.502, termahal Rp24.975 = Rp2,5 juta/lot):

| Modal | Jatah/saham | Saham tak terbeli (jatah < 1 lot) | Modal terpakai |
|---|---|---|---|
| Rp5 juta | Rp0,10 jt | 29 dari 48 | 33% |
| Rp10 juta | Rp0,21 jt | 19 | 50% |
| Rp25 juta | Rp0,52 jt | 8 | 74% |
| Rp50 juta | Rp1,04 jt | 3 | 85% |
| Rp100 juta | Rp2,08 jt | 2 | 90% |
| Rp500 juta | Rp10,4 jt | 0 | 99% |

**S2 penuh butuh kira-kira ≥ Rp50–100 juta.** Untuk modal lebih kecil, pakai **S2 subset lengket**:
- Pegang k saham dari daftar S2 (dipilih ACAK, bukan "yang paling disukai"; memilih sendiri = strategi baru yang belum diuji).
- Saham dipegang selama masih ada di daftar S2. Yang keluar dijual, kursinya diisi acak dari saham baru di daftar.
- Harapan keuntungan **sama**; yang bertambah hanya naik-turunnya (simulasi 300 kali, data uji):

| k saham | Rata relatif/bln | Rentang 5–95% (8 tahun) | Peluang kalah 12 bulan |
|---|---|---|---|
| semua (~40) | +1,20% | – | 9% |
| 20 | +1,22% | +0,77..+1,67% | 18% |
| 16 | +1,17% | +0,62..+1,74% | 20% |
| 12 | +1,22% | +0,58..+1,94% | 22% |
| 8 | +1,17% | +0,34..+2,05% | 27% |

Saran: **k ≥ 12**. Di bawah 12, hasil sangat bergantung keberuntungan undian.

Analisis modal sangat kecil (lot dengan harga asli, hanya saham terjangkau) ada di `private/` (berisi angka modal pribadi).
Catatan umum: dengan modal kecil, subset terpaksa condong ke saham MURAH → hasil historis yang tampak lebih bagus adalah ciri periode
2019–2026, bukan aturan; risikonya (turun dalam, sering kalah dari pasar) yang harus dipegang.

Rekening saham: butuh KTP + rekening bank atas nama sendiri; setor ke RDN lewat transfer bank / virtual account (m-banking cukup;
tidak perlu kartu kredit/debit/PayPal). Pilih broker anggota BEI & terdaftar OJK, biaya ~0,15%/0,25%, tanpa biaya minimum per transaksi.

Kapasitas bukan masalah untuk modal perorangan: dengan batas 5% nilai transaksi harian, satu transaksi bisa Rp1,7–3,4 miliar per saham.

## 5. Tahapan (kriteria ditetapkan SEKARANG, sebelum hasil paper trading terlihat)

**Fase 0 — Paper trading saja (Des 2026 – minimal Feb 2027, 3 bulan).**
Tidak ada uang sungguhan. Claude memeriksa tiap bulan: pilihan tercatat sebelum hari beli, hasil dihitung, biaya nyata dibandingkan model.

**Syarat masuk Fase 1** (SEMUA harus terpenuhi; TIDAK memakai untung/rugi paper trading, karena 3 bulan terlalu pendek untuk menilai):
1. 3 bulan pencatatan tanpa kesalahan (dicatat sebelum beli, tidak ada catatan lama yang berubah).
2. Biaya nyata hasil foto spread jam bursa ≤ 1,5 × model biaya B (pra-registrasi kalibrasi Des 2026).
3. Porsi saham pilihan yang tak bisa dibeli (ARA terkunci / suspensi) ≤ 10%.
4. Pengguna siap secara mental menahan penurunan −30% tanpa panik menjual di tengah jalan.

**Fase 1 — Uang kecil (paling cepat Mar 2027).**
Modal yang **benar-benar siap hilang**. S2 subset lengket k = 12–16 (atau penuh bila modal ≥ Rp50 juta). Paper trading tetap jalan berdampingan sebagai pembanding.

**Fase 2 — Tambah modal (paling cepat setelah 12 bulan uang sungguhan).**
Hanya bila Fase 1 berjalan sesuai aturan dan aturan berhenti di bawah tidak terpicu.

**Aturan BERHENTI** (berlaku di semua fase):
- **(Diganti 26 Nov 2026, SEBELUM paper trading mulai; pengguna menyerahkan pilihannya ke Claude dan boleh mengubahnya.)**
  Kinerja SELALU dinilai dari portofolio paper **S2 penuh**, bukan dari subset pribadi (subset terlalu berderau untuk menilai strategi).
  1. **Lampu kuning:** rata-rata relatif 12 bulan < −1%/bulan → periksa data, biaya & eksekusi. Tidak ada jual paksa.
  2. **Lampu merah:** rata-rata relatif **24 bulan < −0,5%/bulan** → berhenti MENAMBAH uang & evaluasi menyeluruh; tidak otomatis menjual.
  3. **Batas keras:** nilai portofolio uang sungguhan turun **50% dari puncaknya** (setoran baru tidak dihitung sebagai untung) → jual semua, berhenti.
  Simulasi 5 tahun (20.000 kali; S2 penuh sb 3,99%) aturan 12 bln < −1% → 24 bln < −0,5%: alarm palsu bila S2 hidup +1,2%/bln 34% → 13%; terdeteksi bila
  S2 mati (0%) 89% → 76%; bila merugi −0,5%/bln 98% → 94%. Aturan 36 bln < 0 setara (14%/81%) tetapi butuh 3 tahun data. Batas keras untuk 8 saham:
  peluang tersentuh 5 tahun walau S2 bekerja seperti 2019–2026: −30% 65%, −40% 34%, −50% 13%.
  ASUMSI: return bulanan saling bebas & normal, tanpa momentum crash → kenyataan bisa LEBIH BURUK. Dipilih dari simulasi ini; aturan baru sengaja
  TIDAK dicocokkan ke kejadian 2019–2026. Aturan lama (12 bln < −1% = hentikan, "~3%") salah hitung: 3% hanya untuk SATU jendela, dan aturan itu
  pernah terpicu Okt 2020–Mar 2021 tepat sebelum S2 unggul +2,8%/bln.
- Kesalahan sistem yang membuat pilihan tercatat setelah hari beli → hentikan sampai diperbaiki.
- Jangan pernah menambah modal untuk "membalas" kerugian.

## 6. Cara eksekusi praktis (tiap bulan)

1. **Akhir bulan (malam hari bursa terakhir):** daftar S2 tercatat otomatis (`raw/paper_trading/s2_pilihan`). Claude menyiapkan daftar beli/jual + jumlah lot.
2. **Hari bursa pertama bulan berikutnya:** jual saham yang keluar dari daftar & beli yang masuk. Riset memakai harga TUTUP → order di **sesi pra-penutupan** (sekitar 15:50–16:00 WIB; cek jadwal di aplikasi broker) agar mendapat harga penutupan. Alternatif: limit order di sekitar harga terakhir pada sore hari.
3. **Saham terkunci ARA** (antrean jual kosong): jangan kejar; lewati bulan itu (sesuai uji #12c, ~0,1–0,2% kasus).
4. **Saham ARB saat mau dijual:** coba lagi hari berikutnya.
5. **Biaya broker** umumnya ~0,15% beli / ~0,25% jual (sudah termasuk PPh final 0,1%) ≈ asumsi riset 0,4% bolak-balik. Pilih broker tanpa biaya minimum per transaksi (order kecil).
6. Catat semua transaksi nyata (tanggal, harga, lot, biaya) → Claude membandingkan dengan paper trading untuk mengukur biaya nyata.

## 7. Risiko yang masih belum tertutup

- **Survivorship IDX:** daftar saham hanya yang masih tercatat; saham kecil yang delisting tidak ada di data uji → hasil historis sedikit terlalu bagus.
- **Momentum crash:** pasar sekarang bearish dalam. Portofolio eksperimen `s2p` (pegang semua semesta saat bearish) dicatat berdampingan untuk dipelajari, BUKAN pengganti S2.
- **Konsentrasi saham kurang likuid:** keunggulan S2 hilang di 50 saham paling likuid (#12b). Spread nyata bisa lebih besar dari model untuk saham-saham kecil di daftar.
- **Satu titik gagal data:** harga dari Yahoo (`yfinance`). Kalau rusak, rencana darurat: unduh manual "Ringkasan Saham" dari situs IDX.
