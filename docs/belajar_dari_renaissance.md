# Belajar dari Renaissance & literatur quant (riset 21 Nov 2026)

Tujuan: berhenti jadi "katak dalam tempurung". Apa yang BENAR-BENAR membuat Renaissance (Medallion) sukses, apa kata paper
akademik terbaik, dan apa artinya untuk proyek ini (trader perorangan, IDX, tanpa leverage besar, tanpa short).

## 1. Fakta tentang Medallion (sumber sekunder; strategi asli tidak pernah dipublikasikan)
- Return ~63–66%/thn sebelum biaya (1988–2018), ~37–39% setelah biaya; beta pasar & faktor NEGATIF (Cornell 2019,
  "Medallion Fund: The Ultimate Counterexample?"): bukan kompensasi risiko.
- Ribuan posisi long DAN short jangka PENDEK (jam s/d 1–2 minggu), benar hanya ~50,75% (Mercer via Zuckerman), tapi
  atas JUTAAN transaksi.
- LEVERAGE besar: rata-rata ~12,5x, sampai ~20x (Zuckerman). "An overlooked key is ample and cheap leverage."
- Biaya eksekusi sangat rendah (infrastruktur sendiri); kapasitas dibatasi (~$10 miliar, laba dibagikan tiap tahun).
- Sejarah metode: model Markov/HMM (Baum, Ax), lalu Berlekamp & Laufer merombak sistem (1989–1990) ke perdagangan jangka
  pendek; kemudian regresi/kernel & banyak sinyal digabung dalam SATU sistem; data dikumpulkan & DIBERSIHKAN obsesif.
- Simons: "The computer has its opinions and we slavishly follow them." Model menggantikan analisis fundamental.

## 2. Apa kata paper (yang relevan untuk kita)
1. **Hukum Dasar Manajemen Aktif** (Grinold & Kahn): IR = IC × √(jumlah taruhan INDEPENDEN). Sinyal lemah (IC 0,02–0,05)
   hanya berguna kalau dipakai di BANYAK taruhan independen (banyak saham × sering). Ini inti "banyak sinyal lemah".
2. **Batas t > 3** (Harvey, Liu & Zhu 2016, RFS): karena ratusan peneliti mencari faktor, ambang 2 terlalu rendah;
   sebagian besar "temuan" adalah kebetulan. (Proyek ini sudah memakai t > 3.)
3. **Machine learning menggabungkan banyak sinyal** (Gu, Kelly & Xiu 2020, RFS): pohon (boosting/random forest) &
   jaringan saraf mengalahkan regresi linear karena menangkap INTERAKSI non-linear; prediktor dominan = momentum, likuiditas,
   volatilitas. **Di pasar berkembang** (Hanauer & Kalsbach 2023, Emerging Markets Review): 32 negara, 36 variabel, ML
   mengungguli linear, tetap untung setelah biaya & larangan short, TIDAK melemah seiring waktu; model yang dilatih di
   pasar maju memprediksi pasar berkembang hampir sama baik.
4. **101 Formulaic Alphas** (Kakushadze 2016, WorldQuant): 101 sinyal nyata berhorizon 0,6–6,4 hari, korelasi antar
   sinyal rata-rata hanya ~16% → digabung = keuntungan stabil. Masalah: terlalu banyak variabel, terlalu sedikit data.
5. **Statistical arbitrage** (Avellaneda & Lee 2010): residu return saham (setelah faktor/sektor dihilangkan) cenderung
   BALIK (mean reversion); Sharpe 1,44 setelah biaya 1997–2007, MELEMAH setelah dipublikasikan (0,9; replikasi 2013–2016 0,54).
6. **López de Prado** (Advances in Financial ML): purged/embargoed cross-validation, Deflated Sharpe Ratio (koreksi
   banyak percobaan), meta-labeling; kebanyakan dana ML gagal karena backtest overfitting.
7. **IDX**: studi lokal menemukan PEMBALIKAN jangka pendek (overnight reversal, winner/loser reversal, reversal intraday),
   tapi belum ada yang menguji BERSIH biaya realistis.

## 3. Diagnosis jujur proyek kita (riset #1–#35)
- Sebagian besar riset menguji SATU sinyal untuk MEMILIH WAKTU (timing) SATU keranjang/indeks (makro, cuaca, gempa, TGA,
  VIX...). Menurut hukum Grinold-Kahn, "breadth" = 1 keranjang × ~12–52 keputusan/tahun → IR mustahil tinggi walau sinyalnya
  benar. Itu sebabnya hampir semua gagal: KESALAHAN DESAIN, bukan cuma "pasar efisien".
- Yang berhasil (S2, IC model gabungan t 4–6) justru PENAMPANG SAHAM (memilih saham relatif satu sama lain) = breadth besar.
- Hambatan utama di IDX = BIAYA (komisi 0,4% + spread 0,5–0,9%) dan TIDAK BISA SHORT → horizon terlalu pendek dibunuh biaya.
- Yang TIDAK bisa ditiru: leverage 12–20x, short, eksekusi murah, ilmuwan ratusan orang, data berbayar.

## 3b. BUKTI & STATUS VERIFIKASI (diperiksa 21 Nov 2026 atas permintaan pengguna: "jangan dari asumsi")
**Bukti dengan data/simulasi sendiri** (`cek_daya_uji.py`, bisa diulang):
- Agar uji timing bulanan 2003–2018 (190 bulan) lolos t > 3, sinyal harus berkorelasi ≥ 0,218 dengan return bulan depan
  (R² ≥ 4,7%). Mingguan ≥ 0,106; harian ≥ 0,048.
- Sinyal timing yang NYATA (IC 0,05) diuji pada 190 bulan: t rata-rata 0,77, lolos t > 3 hanya 2,2% percobaan.
- Sinyal penampang dengan IC SAMA (0,05) pada 100 saham × 190 bulan: t rata-rata 6,8, lolos 100%.
**Bukti eksternal bahwa sinyal timing makro memang lemah**: Welch & Goyal (2008, RFS 21:1455–1508): tidak satu pun dari
  puluhan prediktor klasik mengalahkan rata-rata historis di luar sampel; R² luar sampel umumnya NEGATIF (replikasi
  dividend-price: −2% s/d −15%). Bantahan Campbell & Thompson (2008): dengan batasan teori, perbaikan kecil.
**Hanauer & Kalsbach (2023)**: (lihat teks lengkap di bawah; ringkasan Robeco awal): Dari artikel Robeco (ditulis
  Hanauer & Swinkels, 2023) yang TERVERIFIKASI: >15.000 saham, 32 negara, 1990–2021, 36 karakteristik, uji luar sampel
  2002–2021; long-short (5 portofolio, bobot kapitalisasi) linear ~0,8%/bln, pohon ~1,0%, jaringan saraf & gabungan ~1,2%;
  alpha atas faktor: linear ~0,2%, pohon 0,5%, NN/gabungan 0,7%/bln; "even accounting for transaction costs and
  short-selling constraints ... significant net outperformance" (TANPA angka biaya). **Prediktor terpenting: "price to its
  52-week high", idiosyncratic volatility, turnover** → = S2 kita (konfirmasi INDEPENDEN). BELUM TERVERIFIKASI (hanya
  ringkasan pihak ketiga): "tidak melemah seiring waktu", "berlaku di saham besar saja", apakah INDONESIA termasuk sampel.
**Hanauer & Kalsbach — TEKS LENGKAP DIBACA 21 Nov 2026** (Bab 2 disertasi Kalsbach, TUM 2023; PDF lokal docs/paper/, tidak di repo):
- Sampel: 15.152 saham, 32 negara EM, Jul 1990–Des 2021, uji luar sampel 2002–2021, 36 karakteristik; **INDONESIA TERMASUK**
  (Tabel 2.1: 649 saham, rata-rata 150/bulan, 1990-07 s/d 2021-12). Mikrocap (3% kapitalisasi terbawah) DIBUANG.
- Long-short bobot sama (Tabel 2.3): OLS 1,38%/bln t 7,8 | GBRT 1,82% t 11,6 | NN 1,84–1,91% | ENS 1,86% t 11,8. Bobot kapitalisasi
  kira-kira 2/3-nya. Turnover ~90–100%/bln (long-short).
- Prediktor terpenting (Gbr 2.1/B.1): LTurnover, Idiovol, **P2P52WH (= S2)**, r12-2, r2-1, Illiqu, ukuran. Profitabilitas/intangible lemah.
- "we cannot observe a decline in predictability over time" (TERVERIFIKASI). Drawdown terbesar 2009 = momentum crash (sama dengan S2 kita).
- **LONG-ONLY, HANYA SAHAM BESAR, SETELAH BIAYA** (Tabel 2.9, biaya = ½ spread estimator EDGE): kotor top kuintil − pasar ENS +0,78%/bln
  (bobot sama), turnover 45%/bln; penyangga beli 10% / tahan 30%: turnover 27,5%, bersih **+0,59%/bln t 5,6** (bobot kapitalisasi +0,34% t 3,3).
  Biaya konservatif 100 bps sekali jalan (Tabel B.12): hanya ENS + penyangga yang signifikan, +0,23% (bobot kap.) / +0,51% (bobot sama).
- **Model dilatih gabungan banyak negara > dilatih per negara** (Tabel B.9: Indonesia dkk, ENS pooled 1,18% vs lokal 0,92%); model yang
  dilatih HANYA di pasar maju memprediksi EM hampir sama baik (Tabel 2.4 Panel E).
- Bab 3 (Kalsbach-Windmüller): BERITA spesifik emiten × dekat puncak 52 minggu → alpha 1,47%/bln t 4,7 (berita baik + dekat puncak = reaksi
  kurang); efek terutama di saham batas-arbitrase tinggi & berita TIDAK terjadwal.
**Implikasi untuk kita** (perbandingan jujur): IC model kita (0,098) & prediktor utama SEJALAN dengan paper. Bedanya: (1) paper 2002–2021
  rata-rata 32 negara, kita 2009–2018 Indonesia saja (alpha IDX periode itu kecil); (2) kita hanya 20 fitur harga/volume (paper 36 termasuk
  fundamental); (3) kita latih di ~100 saham IDX saja — paper menunjukkan DATA GABUNGAN lebih baik → IDE: latih model di 12.000+ saham AS
  (bersih/saham_as) / gabungan, terapkan ke IDX; (4) paper pakai EDGE (Ardia-Guidotti-Kroencke 2022) utk spread → ganti Corwin-Schultz;
  (5) Bab 3 → riset berita (raw/harian/berita kode_disebut) × S2 begitu data berita menumpuk.

**Koreksi atas klaim sendiri**: desain "breadth ~1" menjelaskan kegagalan riset TIMING, TAPI tidak semua kegagalan:
  riset PENAMPANG #14 (perhatian), #22 (dividen), #35 (ilikuiditas) juga gagal → biaya IDX & sinyal lemah tetap penghalang nyata.
**Klaim Renaissance** (leverage 12,5–20x, 50,75%, ~66%/thn) bersumber dari buku Zuckerman & laporan media (sekunder);
  tidak ada dokumen resmi Renaissance. Return Medallion dari lampiran buku tersebut (dipakai Cornell 2019).

## 3c. Paper biaya transaksi (DIBACA LANGSUNG dari PDF, 21 Nov 2026)
**Novy-Marx & Velikov (2014/2016 RFS), "A Taxonomy of Anomalies and Their Trading Costs"** (NBER w20721):
- "equal-weighted portfolio results ... are misleading and should be viewed skeptically"; biaya strategi bobot-sama 2–3x
  strategi bobot-kapitalisasi. (SEMUA strategi kita bobot-sama!)
- Biaya bolak-balik strategi bobot-kapitalisasi rata-rata > 50 bps; biaya mengurangi spread > 1% dari perputaran bulanan satu sisi.
- "only two of the strategies that have more than 50% one-sided monthly turnover have significant net spreads". S2 kita ~48–50%.
- Aturan penyangga sS (buy/hold spread): beli kalau masuk S% teratas, tahan selama masih di s% teratas (10%/20% untuk perputaran
  sedang; 10%/50% untuk tinggi). Rata-rata 23 anomali: perputaran −41%, biaya −42%, return bersih NAIK. "the single most effective
  simple cost mitigation strategy". Momentum (Tabel 5): bersih 0,51%/bln t 2,87 (penyangga) vs 0,31 t 1,82 (saham murah) vs 0,37
  t 2,34 (rebalancing bertahap triwulanan); t bersih naik ~2,5 → ~4 saat penyangga diperlebar (Gambar 5).
- PEMBALIKAN JANGKA PENDEK mati setelah biaya bahkan dengan penghematan: bersih −0,65%/bln (Tabel 7) → riset "reversal"
  di IDX (biaya lebih mahal) DITURUNKAN prioritasnya. Musiman juga mati (−0,72%/bln). PEAD versi CAR3 bertahan (0,62% t 2,97).
**Gârleanu & Pedersen (2013 JF), "Dynamic Trading with Predictable Returns and Transaction Costs"** (abstrak terverifikasi;
  isi PDF tidak terbaca): "aim in front of the target", "trade partially towards the current aim"; prediktor yang lebih lambat
  memudar mendapat bobot lebih besar.

## 4. Arah baru (prioritas)
1. **Model penampang IDX versi 2 (ML)**: 40–80 fitur (momentum berbagai jendela, pembalikan 1 minggu/1 bulan, jarak ke
   puncak 52 mg, volatilitas, max return, volume & lonjakan volume, likuiditas, kejutan laba, perhatian Wikipedia, musiman,
   sektor, fundamental ke depan), target = peringkat return bulan depan; gradient boosting vs linear; uji maju bertahap
   (dilatih ulang tiap tahun, purge/embargo), dinilai SEBAGAI SATU UJI (bukan 80 uji). Portofolio long-only top-N dengan
   aturan penyangga (hemat biaya) & biaya realistis.
2. ~~Pembalikan jangka pendek~~ DITURUNKAN: Novy-Marx & Velikov Tabel 7 = bersih negatif di AS walau biaya ditekan.
3. **Model biaya & eksekusi** dari data intraday 1 menit (ke depan): spread nyata, dampak harga per ukuran order.
4. Kurangi riset timing makro satu-keranjang (breadth rendah) kecuali sebagai fitur di model gabungan.
5. Paper trading tetap hakim akhir (2019+ sudah terpakai untuk S2).

## Sumber
Cornell (2019) SSRN 3504766; Zuckerman (2019) The Man Who Solved the Market; Grinold & Kahn, Active Portfolio Management;
Harvey, Liu & Zhu (2016) RFS 29(1); Gu, Kelly & Xiu (2020) RFS 33(5) / NBER w25398; Hanauer & Kalsbach (2023) Emerging
Markets Review 55, 101022; Kakushadze (2016) arXiv 1601.00991; Avellaneda & Lee (2010) Quantitative Finance 10(7);
López de Prado (2018) Advances in Financial Machine Learning (Wiley).
