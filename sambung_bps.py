"""
SAMBUNG SERI BPS BEDA TAHUN DASAR lewat PERTUMBUHAN (riset #52 langkah 1a). Level TIDAK disambung.
ATURAN (ditetapkan 26 Nov 2026 SEBELUM melihat hasil): seri LAMA dipakai s/d akhir hidupnya, lalu seri BARU (angka dasar baru untuk masa
lalu belum ada saat itu -> memakainya = bocor). Pertumbuhan dihitung DI DALAM masing-masing seri (seri baru memakai histori sendiri).
DITERIMA bila tumpang tindih >= 6 titik pertumbuhan DAN korelasi >= 0,7 (M: 1 bulan; Q: 4 triwulan). Gagal -> TIDAK disambung (dilaporkan).
IHPB tidak punya tumpang tindih -> digabung dengan CELAH (uji=False), tidak pernah dijembatani. Kelompok IHK/inflasi 2012/2018/2022 TIDAK
disambung: pengelompokan berubah 7 -> 11 kelompok. Inflasi umum (var 1) sudah menerus.
  python sambung_bps.py -> data/olah/panel_bps_sambung.parquet + _ringkas
"""
from pathlib import Path
import numpy as np
import pandas as pd

P = pd.read_parquet("data/olah/panel_bps.parquet")
P = P[P["frek"].isin(["M", "Q"])]
P["w"], P["k"] = P["wilayah"].str.strip(), P["kategori"].str.strip()


def ambil(var, w, k, frek):
    x = P[(P["var_id"] == var) & (P["frek"] == frek) & (P["k"] == k)]
    if w.startswith("[w"):
        x = x[x["w"].str.endswith(w)]
    elif w.endswith("*"):
        x = x[x["w"].str.startswith(w[:-1])]
    else:
        x = x[x["w"] == w]
    assert x["seri"].nunique() <= 1, (var, w, k, x["seri"].unique()[:3])
    return x.set_index(pd.PeriodIndex(x["bulan"], freq="M")).sort_index()


def tumbuh(x, L):
    v = x["nilai"].astype(float)
    l = v.reindex(v.index - L); l.index = v.index
    return pd.Series(np.where((v > 0) & (l > 0), np.log(v / l), np.nan), index=v.index)


def pasangan():
    x = P[(P["var_id"] == "10") & (P["frek"] == "M")]
    for w, k in x[["w", "k"]].drop_duplicates().itertuples(index=False):
        yield f"NTP provinsi|{w}|{k}", "M", [("10", w, k), ("1741", w, k)], True
    for nm, a, b in [("IT", "INDEKS HARGA YANG DITERIMA PETANI", "1. INDEKS HARGA YANG DITERIMA PETANI"), ("IB", "INDEKS HARGA YANG DIBAYAR PETANI", "2. INDEKS HARGA YANG DIBAYAR PETANI"),
                     ("NTP", "NILAI TUKAR PETANI", "3. NILAI TUKAR PETANI"), ("NTUP", "NILAI TUKAR USAHA PERTANIAN", "4. NILAI TUKAR USAHA PERTANIAN")]:
        yield f"NTP nasional|{nm}", "M", [("13", a, "NTP"), ("1717", b, "Indeks")], True
    for lama, baru, j in [("1634", "1956", "riil"), ("1624", "1955", "nominal")]:
        for nm, a, b in [("konsumsi RT", 100, 100), ("konsumsi pemerintah", 200, 300), ("PMTB", 300, 400), ("bangunan", 301, 410), ("ekspor", 500, 600), ("ekspor barang", 501, 610),
                         ("ekspor jasa", 502, 620), ("impor", 600, 700), ("impor barang", 601, 710), ("impor jasa", 602, 720), ("PDB", 800, 800)]:
            yield f"PDB {j}|{nm}", "Q", [(lama, f"[w{a}]", "Tidak ada [k0]"), (baru, f"[w{b}]", "Tidak ada [k0]")], True
    for j, ka, kb in [("riil", "Harga Konstan 2000", "Harga Konstan 2010"), ("nominal", "Harga Berlaku", "Harga Berlaku")]:
        for a, b in [("1.PERTANIAN*", "A. Pertanian*"), ("2.PERTAMBANGAN*", "B. Pertambangan*"), ("3.INDUSTRI*", "C. Industri*"), ("5.KONSTRUKSI*", "F. Konstruksi*")]:
            yield f"PDB sektor {j}|{b[3:-1]}", "Q", [("8", a, ka), ("65", b, kb)], True
    for a, b in [("1.Pertanian", "1.Pertanian"), ("2.Pertambangan dan Penggalian",) * 2, ("3.Industri",) * 2]:
        yield f"IHPB|{a}", "M", [("24", a, "Tidak ada"), ("1721", b, "Tidak ada")], False


keluar, ring = [], []
for nama, frek, segmen, uji in pasangan():
    x = [ambil(v, w, k, frek) for v, w, k in segmen]
    if any(s.empty for s in x):
        ring.append({"nama": nama, "status": "salah satu kosong"}); continue
    L1, L12 = (1, 12) if frek == "M" else (3, 12)
    g = pd.concat([tumbuh(s, L1 if frek == "M" else L12) for s in x], axis=1, keys=["a", "b"]).dropna()
    kor = g["a"].corr(g["b"]) if len(g) >= 6 else np.nan
    beda = (g["b"] - g["a"]).abs().median() if len(g) else np.nan
    if uji and not (len(g) >= 6 and kor >= 0.7):
        ring.append({"nama": nama, "status": "GAGAL uji", "n": len(g), "kor": kor, "beda": beda}); continue
    batas = x[0].index.max()
    for s, pilih in [(x[0], x[0].index <= batas), (x[1], x[1].index > batas)]:
        d = pd.DataFrame({"bulan": s["bulan"].values, "tersedia": s["tersedia"].values, "tumbuh1": tumbuh(s, L1).values, "tumbuh12": tumbuh(s, L12).values, "var_id": s["var_id"].values})[pilih]
        keluar.append(d.assign(seri="BPSS|" + nama, judul=nama, frek=frek, uji=uji))
    ring.append({"nama": nama, "status": "disambung" if uji else "gabung dgn celah", "n": len(g), "kor": kor, "beda": beda, "akhir_lama": str(batas)})
o = pd.concat(keluar, ignore_index=True).dropna(subset=["tumbuh1", "tumbuh12"], how="all")
assert not o.duplicated(["seri", "bulan"]).any()
assert (o["tersedia"] > o["bulan"]).all()
o.to_parquet("data/olah/panel_bps_sambung.parquet", index=False)
r = pd.DataFrame(ring); r.to_parquet("data/olah/panel_bps_sambung_ringkas.parquet", index=False)
print("status:", r["status"].value_counts().to_dict(), "| seri", o["seri"].nunique(), "| baris", len(o))
r["kel"] = r["nama"].str.split("|").str[0]
print(r.groupby(["kel", "status"]).agg(seri=("nama", "size"), n=("n", "median"), kor_med=("kor", "median"), kor_min=("kor", "min"), beda=("beda", "median")).round(4).to_string())
print(r[~r["kel"].eq("NTP provinsi")].round(3).to_string())
