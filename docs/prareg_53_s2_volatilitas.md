# Pra-registrasi riset #53: S2 dengan porsi menurut volatilitas (long-only, tanpa utang)

Ditulis 26 Nov 2026 SEBELUM return strategi ini dihitung pada data asli. Skrip: `riset_53_s2_volatilitas.py` (aturan lengkap di docstring).

## Dasar literatur
- Barroso & Santa-Clara (2015 JFE): volatilitas momentum mudah ditebak (6 bulan return harian), return tidak naik saat bergejolak
  → skala posisi = target / vol menaikkan Sharpe & memotong crash.
- Moreira & Muir (2017 JF): sama untuk pasar & banyak faktor; uji = alpha portofolio terkelola terhadap portofolio asli.
- Bantahan (diakui di depan): Cederburg, O'Doherty, Wang & Yan (2020 JFE): 103 strategi, versi real-time umumnya TIDAK mengalahkan
  aslinya; Barroso & Detzel: hanya saat likuiditas tinggi. DeMiguel dkk. (2024 JF): versi multifaktor bersyarat lebih baik.
- S2 long-only → volatilitasnya sebagian besar volatilitas PASAR, bukan WML long-short → dugaan awal: efek kecil.

## Aturan (dari paper, tanpa penyetelan)
- Basis = S2 resmi (kerangka #13), biaya B (0,4% + 1,2 × tick historis/harga asli).
- sig_hat(t) = sb return harian portofolio S2 yang dipegang, 126 hari bursa s/d t (min 100), × √250.
- sig_ref(t) = median semua sig_hat(τ ≤ t) (berkembang; min 12 nilai).
- porsi e = min(1, sig_ref / sig_hat); sisa di kas berbunga rf (IRSTCI01IDM156N/1200).
- UJI PENENTU (SATU): (M − rf) = a + b (S − rf), White HC0, LOLOS bila t(a) > 3.
- Info: Sharpe, drawdown maks, porsi, 6 bulan terburuk, paruh, rf = 0, vol semesta, varians 21 hari.
- Lolos → paper trading baru `s2vol`. Gagal → "belum terbukti"; S2 resmi TIDAK diubah. Data uji 2019+ tidak dibuka.

## Hasil tes kode & DAYA UJI (data palsu, SEBELUM data asli)
| Tes | sd log-vol | porsi rata | alpha | t |
|---|---|---|---|---|
| kosong (vol tanpa kelompok) | 0,35 | 0,98 | +0,000%/bln | +0,01 |
| tiruan (vol berkelompok φ 0,99, rata tetap) | 0,35 | 0,92 | +0,043%/bln | +0,56 |
| tiruan | 0,60 | 0,88 | +0,034%/bln | +0,29 |
| kosong | 0,60 | 0,96 | −0,035%/bln | −1,09 |

KESIMPULAN DAYA UJI: walau dunia palsu PERSIS sesuai teori, alpha t < 1. Sebab: porsi dibatasi 1 (tanpa utang) → rata 0,88–0,92, dan
Sharpe dasar S2 rendah (0,15–0,25 bersih) → keuntungan teoretis volatility timing (∝ Sharpe × variasi porsi) sangat kecil untuk
128 bulan. Drawdown maks turun (−35% → −32%; −33% → −29%) = efek RISIKO mekanis yang memang terlihat.
→ Uji penentu TIDAK diubah, tetapi hasil asli dibaca sebagai INFORMASI RISIKO; hasil negatif BUKAN bukti tidak berguna.
Pelajaran: pengaturan porsi long-only tanpa utang adalah alat RISIKO (drawdown), bukan sumber alpha yang bisa dibuktikan dgn ~10 tahun data.
