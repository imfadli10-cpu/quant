# Pra-registrasi riset #63: "tarik-menarik" overnight vs siang (Lou-Polk-Skouras 2019) di IDX

Ditulis 27 Nov 2026 SEBELUM hubungan sinyal-return dihitung.

## Dugaan & alasan
- Lou-Polk-Skouras 2019 (JFE, "A tug of war: overnight versus intraday expected returns"): klien yang berbeda dominan di waktu berbeda —
  ritel/perhatian di PEMBUKAAN (overnight), institusi di SIANG hari. Return overnight per saham PERSISTEN secara penampang (momentum
  overnight), dan saham dgn return overnight 12 bulan tinggi terus berkinerja (komponen overnight) sementara komponen siang berbalik.
  Akbas-Boehmer-Jiang-Koch 2022 (JFE): overnight return berturut-turut = jejak perhatian/ritel.
- IDX ritel dominan + lelang PRA-PEMBUKAAN (harga Open Yahoo ≈ hasil pra-pembukaan) → tekanan beli ritel tercatat di Open. Dugaan:
  ON12 (jumlah log return overnight 12 bulan) MEMPREDIKSI return bulan depan secara POSITIF.
- Bantahan: (1) LPS menemukan sebagian keuntungan HANYA di komponen overnight (tidak bisa ditangkap long-only bulanan tanpa jual di buka /
  beli di tutup tiap hari); (2) Open Yahoo IDX bisa berderau (saham sepi: Open = tutup kemarin); (3) ON12 berkorelasi dgn momentum S1.
  Perkiraan jujur: U1 t 1–3, U2 lebih lemah, U3 gagal.

## Definisi
- overnight_t = (Open_t × Adj_t/Close_t) / Adj_{t−1} − 1 (Open disesuaikan dividen dgn faktor yang sama dgn Close → ex-dividen tidak
  tercatat sebagai turun palsu). Hanya hari AKTIF (volume > 0) & harga bersih (`bersih_idx`, sama dgn #12); |overnight| > 35% dibuang (salah data).
  siang_t = Close_t/Open_t − 1 (info).
- ON12 = Σ log(1+overnight) di jendela (akhir bulan m−12, akhir bulan m]; butuh >= 150 hari sah. Diketahui di akhir bulan m (tidak bocor).

## Uji (kerangka #13: semesta #2, sinyal akhir bulan, beli tutup hari bursa pertama m+1, tahan 1 bulan, biaya B)
- U1 (|t| > 3, dugaan +): IC peringkat(ON12, ret_pegang), rata-rata per bulan.
- U2 (|t| > 3, dugaan +): Fama-MacBeth peringkat: ret ~ ON12 + S1 (12-1) + S2 (dekat puncak 52 mg); t koefisien ON12.
- U3 (t > +3): beli 20% ON12 teratas (bobot sama) BERSIH biaya B − semesta.
- Info: IC komponen siang 12 bulan (dugaan −), korelasi ON12–S1, porsi hari aktif dgn overnight tepat 0, paruh waktu.

## Uji kode
`--tes-tiruan` (return palsu + 2% × z(ON12)) terdeteksi; `--tes-kosong` ≈ 0; `--potong-data` → IDENTIK. Data uji 2019+ DIKUNCI.

## Hasil tes kode (SEBELUM data asli)
158 bulan latih (2004-12..2018-10), semesta median 98. Tiruan +2% × z(ON12) → U1 t +17,3, U2 t +11,2, U3 t +11,6; acak → U1 +0,42, U2 +0,69,
U3 −2,16 (biaya 0,33%/bln). DATA: 33% hari aktif punya overnight TEPAT 0 (Open Yahoo = tutup kemarin, kemungkinan pra-pembukaan tak terjadi
transaksi / data Yahoo) → derau mengencerkan sinyal; korelasi peringkat ON12–S1 +0,42 (U2 penting). Desain TIDAK diubah.
