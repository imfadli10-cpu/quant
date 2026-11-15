import time
import pandas as pd
import yfinance as yf
from pathlib import Path

# Baca daftar saham dari file Excel IDX
daftar = pd.read_excel("data/ref/daftar_saham.xlsx")
kolom_kode = [c for c in daftar.columns if "kode" in str(c).lower()][0]
semua_kode = daftar[kolom_kode].dropna().astype(str).str.strip().tolist()
print(f"Ditemukan {len(semua_kode)} saham di daftar\n")

folder = Path("data/raw/harga_idx")
folder.mkdir(parents=True, exist_ok=True)

gagal = []
for i, kode in enumerate(semua_kode, start=1):
    file = folder / f"{kode}.parquet"
    if file.exists():          # Sudah pernah diambil? Lewati
        continue
    try:
        df = yf.download(f"{kode}.JK", period="max", interval="1d",
                         auto_adjust=False, progress=False,
                         multi_level_index=False)
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        gagal.append(kode)
        print(f"[{i}/{len(semua_kode)}] ❌ {kode}")
        continue

    df.to_parquet(file)
    print(f"[{i}/{len(semua_kode)}] ✅ {kode}: {len(df)} hari sejak {df.index[0].date()}")
    time.sleep(0.5)            # Jeda supaya tidak diblokir Yahoo

pd.Series(gagal, name="kode").to_csv("data/ref/gagal_idx.csv", index=False)
print(f"\nSelesai! Gagal: {len(gagal)} saham (lihat data/ref/gagal_idx.csv)")