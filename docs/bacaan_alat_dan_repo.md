# Bacaan: plugin/skill Claude Code & dua repo rujukan (23 Nov 2026)

Tujuan: menilai alat & bahan belajar yang ditanyakan pengguna, dengan kacamata proyek ini (riset data IDX, gratis, repo PUBLIK,
kunci API di laptop, aturan "jangan menembus situs yang memblokir program").

## 1. Plugin/skill yang dicek (sumber: pencarian web 23 Nov 2026; angka bintang di berbagai situs TIDAK konsisten)

| Nama | Pembuat utama (repo) | Isinya | Penilaian untuk proyek ini |
|---|---|---|---|
| graphify | Graphify-Labs/graphify (pip `graphifyy`) | Membuat "peta pengetahuan" kode; memasang hook PreToolUse + menulis bagian di CLAUDE.md | ❌ Tidak perlu. Kode kita = skrip riset kecil; hook & tulisan otomatis ke CLAUDE.md bisa mengacaukan catatan serah terima. |
| OmniRoute | diegosouzapw/OmniRoute | Gerbang AI: meneruskan permintaan ke ~350 penyedia model (termasuk yang "gratis") lewat satu alamat lokal | ❌ Hindari. Kode, catatan & potensi kunci API bisa terkirim ke penyedia pihak ketiga yang tidak jelas. |
| ponytail | DietrichGebert/ponytail (MIT) | Membuat agen memakai ulang kode/fitur bawaan sebelum menulis kode baru | ⚪ Manfaat kecil; menurut pembuatnya TIDAK tampil di panel chat VS Code (yang kita pakai). |
| Agent Reach | Panniantong/Agent-Reach (MIT) | Memberi agen akses ke ~15 platform internet lewat CLI/API, bisa memakai cookie/token | ❌ Hindari. Beberapa varian ditandai mencurigakan/gagal audit keamanan; bertentangan dengan aturan tidak menembus situs. |
| Understand Anything | Lum1104 / Egonex-AI (MIT) | Peta pengetahuan + dasbor kode, pipeline multi-agen | ❌ Tidak perlu; analisis awal sangat boros token. |
| last30days | mvanhorn/last30days-skill (MIT) | Merangkum topik dari Reddit/X/HN/Polymarket/GitHub 30 hari terakhir | ⚪ Riset sekali lihat, bukan pengumpulan data yang bisa diuji ulang. Mungkin berguna untuk ide, bukan untuk sinyal. |
| career-ops | santifer/career-ops (MIT) | Sistem pencarian kerja berbasis AI | ❌ Tidak relevan. |
| Headroom | chopratejas / headroomlabs-ai (pip `headroom-ai`) | Proksi lokal yang memampatkan konteks sebelum dikirim ke model (klaim hemat 50–90%) | ⚠️ Bisa menghemat kredit, TAPI semua lalu lintas Claude Code lewat proksi pihak ketiga & pemampatan bisa membuang detail kecil (bertentangan dgn prinsip "teliti hal kecil"). Belum disarankan. |
| REA | morluto/rea ("Reverse Engineer Anything") | Alat bongkar-balik aplikasi untuk agen | ❌ Hindari; membongkar aplikasi/situs (mis. aplikasi bursa) melanggar aturan kita. |

Prinsip umum: setiap plugin menjalankan kode di laptop dengan akses ke folder proyek (termasuk `kunci_*.txt`) dan menambah konteks
(kredit). Pasang hanya yang jelas manfaatnya, dari pembuat jelas, setelah membaca kodenya.

## 2. Machine Learning for Trading, edisi 3 (Stefan Jansen) — github.com/stefan-jansen/machine-learning-for-trading

Kode MIT; isi buku berhak cipta. 27 bab + 9 studi kasus dengan SATU alur: data → riset → "batas bukti" (evidence boundary:
eksplorasi vs konfirmasi) → produksi → umpan balik (latih ulang / jeda / pensiunkan strategi saat keunggulan memudar).
112 "primer" gratis di ml4trading.io/primer (tanpa daftar). Pemasangan penuh butuh ~16 GB & WSL2 di Windows → TIDAK dipasang;
dibaca per bab sesuai kebutuhan.

Bab yang langsung mengisi celah kita:
- **Bab 7 (tugas belajar):** kontrol uji ganda **BH-FDR** & **Deflated Sharpe Ratio** → wajib untuk mesin penyaring massal #52.
- **Bab 9 (fitur dari model):** filter **Kalman**, fitur spektral **Fourier & wavelet**, **GARCH**, probabilitas rezim **HMM** —
  semua dibuat *point-in-time* → inilah "metode lintas ilmu" (pemrosesan sinyal, rantai Markov tersembunyi) yang kita butuhkan.
- **Bab 15 (ML kausal):** Double ML, Bayesian Structural Time Series, penemuan kausal **PCMCI** (berasal dari ilmu iklim, Runge dkk.),
  NOTEARS, VAR-LiNGAM → alat untuk menguji "variabel aneh (cuaca/iklim) → saham" tanpa tertipu korelasi palsu.
- **Bab 16:** backtest sebagai upaya MEMBANTAH; **Rademacher Anti-Serum**, **White's Reality Check**.
- **Bab 18 (biaya transaksi)** & **Bab 19 (risiko: overlay adaptif, kill switch)** → kalibrasi biaya dari foto spread & #53.
- **Bab 20:** "IC-Sharpe decorrelation" = IC tinggi tidak menjamin Sharpe tinggi → SAMA dengan temuan kita di #12 & #51.
- **Bab 5:** data sintetis (TimeGAN dll.) untuk validasi saat histori pendek (data ke depan kita baru beberapa minggu).
- **Bab 4:** data alternatif termasuk pasar prediksi (Kalshi, Polymarket) — sudah kita kumpulkan.

## 3. awesome-quant — github.com/wilsonfreitas/awesome-quant

Daftar sangat panjang; banyak entri baru yang tidak teruji/promosi → pilih yang mapan. Yang relevan:
- **tsfresh** (ekstraksi fitur deret waktu otomatis + uji relevansi) → calon mesin fitur untuk ribuan seri BPS/FRED.
- **statsmodels / arch** (sudah dipakai), **alphalens-reloaded** (analisis faktor penampang; versi Jansen).
- **purgedcv** (purged & combinatorial purged cross-validation; López de Prado) → uji maju tanpa kebocoran label tumpang tindih.
- **pit-release-gate** (kebocoran akibat data yang terbit tidak serentak antar emiten) → relevan untuk data fundamental & BPS.
- **OmniOracle** (penyaringan hubungan antar 500+ seri FRED/World Bank/EIA/NOAA dgn mutual information) → ide sama dgn #52; repo
  belum dikenal → baca kodenya dulu sebagai ide, JANGAN dipakai mentah.
- **Robert Carver (systematictradingexamples, pysystemtrade)** → pengaturan porsi menurut volatilitas = bahan #53.
- **Tidy Finance** (riset keuangan empiris transparan), **Advances in Financial ML (López de Prado)** jawaban latihan.
- Kalender bursa (bagian "Calendars & Market Hours") → kalender libur IDX resmi untuk validasi hari bursa.

## 4. Tindak lanjut (masuk daftar periksa CLAUDE.md)
1. #52: pakai **BH-FDR + Deflated Sharpe** (Bab 7) sebagai pengaman uji ganda; pertimbangkan **tsfresh** untuk fitur otomatis.
2. Metode lintas ilmu pertama yang dicoba: **HMM rezim, wavelet/spektral, PCMCI** (Bab 9 & 15) — baca primer/notebook bab terkait dulu.
3. #53: baca Carver (volatility targeting) + Bab 19 ML4T sebelum pra-registrasi.
4. Kalibrasi biaya (Des 2026): Bab 18 ML4T (estimasi spread & breakeven cost).
