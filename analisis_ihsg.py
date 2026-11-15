import pandas as pd
import matplotlib.pyplot as plt

# Baca data dari gudang
df = pd.read_parquet("data/raw/harga/IHSG.parquet")

# Hitung return harian: berapa persen naik/turun dibanding kemarin
df["return"] = df["Close"].pct_change()

r = df["return"].dropna()
print("=== STATISTIK IHSG ===")
print(f"Jumlah hari          : {len(r)}")
print(f"Rata-rata return/hari: {r.mean()*100:.3f}%")
print(f"Rata-rata return/thn : {r.mean()*252*100:.1f}%")
print(f"Volatilitas/tahun    : {r.std()*(252**0.5)*100:.1f}%")
print(f"Hari naik            : {(r > 0).mean()*100:.1f}%")
print(f"Hari terbaik         : {r.max()*100:.1f}% pada {r.idxmax().date()}")
print(f"Hari terburuk        : {r.min()*100:.1f}% pada {r.idxmin().date()}")

# Pertanyaan quant pertamamu:
# Kalau hari ini naik, apakah besok cenderung naik juga?
korelasi = r.corr(r.shift(1))
print(f"\nKorelasi return hari ini vs kemarin: {korelasi:.3f}")

# Grafik harga, skala log supaya pergerakan lama tetap terlihat
df["Close"].plot(logy=True, figsize=(12, 5), title="IHSG sejak 1990 (skala log)")
plt.savefig("ihsg.png", dpi=120)
print("\nGrafik tersimpan ke ihsg.png")