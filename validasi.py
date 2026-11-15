import pandas as pd
from pathlib import Path

hari_ini = pd.Timestamp.today().normalize()
BATAS_BASI = {"makro": 120, "cuaca": 30}   # dalam hari; selain itu pakai 10

hasil = []
for file in sorted(Path("data/raw").rglob("*.parquet")):
    df = pd.read_parquet(file)
    kategori = file.parent.name
    idx = pd.to_datetime(df.index)

    info = {
        "kategori": kategori,
        "nama": file.stem,
        "baris": len(df),
        "mulai": idx.min().date(),
        "akhir": idx.max().date(),
        "basi_hari": (hari_ini - idx.max()).days,
        "nilai_kosong": int(df.isna().sum().sum()),
        "tanggal_dobel": int(idx.duplicated().sum()),
    }

    masalah = []
    if info["basi_hari"] > BATAS_BASI.get(kategori, 10):
        masalah.append(f"basi {info['basi_hari']} hari")
    if info["tanggal_dobel"]:
        masalah.append("tanggal dobel")
    if info["nilai_kosong"]:
        masalah.append(f"{info['nilai_kosong']} nilai kosong")

    if "Close" in df.columns:          # pemeriksaan khusus data harga
        close = df["Close"].dropna()
        if (close <= 0).any():
            masalah.append("harga <= 0")
        lompat = int((close.pct_change().abs() > 0.5).sum())
        if lompat:
            masalah.append(f"{lompat}x lompatan >50%")
        if "Volume" in df.columns and kategori == "harga_idx":
            persen_nol = (df["Volume"] == 0).mean()
            if persen_nol > 0.3:
                masalah.append(f"tidak ada transaksi {persen_nol:.0%} hari")

    info["masalah"] = "; ".join(masalah) if masalah else "OK"
    hasil.append(info)

laporan = pd.DataFrame(hasil)
laporan.to_csv("data/ref/laporan_validasi.csv", index=False)

# ===== Ringkasan di layar =====
print("=== LAPORAN KESEHATAN GUDANG DATA ===\n")
for kategori, grup in laporan.groupby("kategori"):
    ok = (grup["masalah"] == "OK").sum()
    print(f"{kategori:12} : {len(grup):4} file, {ok:4} OK, {len(grup) - ok:4} bermasalah")

ukuran = sum(f.stat().st_size for f in Path("data").rglob("*")) / 1e6
print(f"\nTotal ukuran data: {ukuran:.1f} MB")

bermasalah = laporan[laporan["masalah"] != "OK"]
print(f"\nContoh file bermasalah (total {len(bermasalah)}):")
print(bermasalah[["kategori", "nama", "akhir", "masalah"]].head(20).to_string(index=False))
print("\nLaporan lengkap: data/ref/laporan_validasi.csv")