"""
BUKTI (bukan asumsi): kenapa uji TIMING 1 keranjang hampir pasti gagal walau sinyalnya nyata, sedangkan sinyal PENAMPANG
(memilih saham) dengan kekuatan sama mudah terdeteksi. Simulasi Monte Carlo, bisa diulang: python cek_daya_uji.py

Hasil 21 Nov 2026 (benih acak 0):
  IC minimum agar t > 3: bulanan 190 bln 0,218 | mingguan 800 mg 0,106 | harian 3.900 hr 0,048
  Sinyal timing NYATA IC 0,05 pada 190 bulan: t rata-rata 0,77, lolos t>3 hanya 2,2% percobaan
  Sinyal penampang IC 0,05, 100 saham x 190 bulan: t rata-rata 6,8, lolos t>3 100% percobaan
Catatan jujur: saham saling berkorelasi -> taruhan independen < 100; IC per bulan antar-saham sudah menyaring gerak pasar
bersama, jadi dampaknya kecil tapi ada. Simulasi ini menganggap saham independen (batas atas daya uji penampang).
"""
import numpy as np

acak = np.random.default_rng(0)
print("IC minimum agar t > 3 (t ≈ IC x akar n):")
for nama, n in [("bulanan 190", 190), ("mingguan 800", 800), ("harian 3900", 3900)]:
    print(f"   {nama:14}: {3 / np.sqrt(n):.3f}")

ts = []
for _ in range(1000):
    x = acak.normal(size=190)
    y = 0.05 * x + np.sqrt(1 - 0.05 ** 2) * acak.normal(size=190)
    r = np.corrcoef(x, y)[0, 1]
    ts.append(r * np.sqrt(188) / np.sqrt(1 - r * r))
ts = np.array(ts)
print(f"Timing IC 0,05, 190 bulan: t rata-rata {ts.mean():.2f}, lolos t>3 {np.mean(ts > 3):.1%}")

ts = []
for _ in range(300):
    ic = []
    for m in range(190):
        x = acak.normal(size=100)
        y = 0.05 * x + np.sqrt(1 - 0.05 ** 2) * acak.normal(size=100)
        ic.append(np.corrcoef(x, y)[0, 1])
    ic = np.array(ic)
    ts.append(ic.mean() / (ic.std(ddof=1) / np.sqrt(190)))
ts = np.array(ts)
print(f"Penampang IC 0,05, 100 saham x 190 bulan: t rata-rata {ts.mean():.2f}, lolos t>3 {np.mean(ts > 3):.1%}")
