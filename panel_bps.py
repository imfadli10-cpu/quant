"""
PANEL BPS -> tabel bulanan panjang untuk mesin penyaring massal (riset #52, langkah 1).
Sumber: data/raw/histori/bps/bagian_*.parquet (1.764 variabel, 6,67 juta baris; histori SUDAH direvisi BPS, bukan versi saat terbit).

ATURAN (ditetapkan 22 Nov 2026 SEBELUM melihat hubungan apa pun dengan return saham):
- periode di-strip (9.006 baris 'Februari ' berspasi). Bulan -> bulan itu. 'Triwulan I..IV' -> Mar/Jun/Sep/Des (frek Q).
  'Semester 1 (Maret)' -> Mar, 'Semester 2 (September)' -> Sep (frek S). 'Tahun'/'Tahunan'/'Jumlah' -> Des (frek Y).
  Mingguan ('Januari_I' dst., 25 baris/minggu) DIBUANG (terlalu sedikit).
- Tahun > 2026 DIBUANG (proyeksi penduduk sampai 2035 = bukan data nyata).
- seri = var_id | wilayah | kategori. Duplikat (seri, bulan, frek) -> nilai terakhir (dilaporkan jumlahnya).
- KETERSEDIAAN (jeda terbit KONSERVATIF; tanggal rilis asli tidak tercatat): data bulan m dianggap DIKETAHUI pada akhir bulan
  m + JEDA[frek]: M = 2 bulan (inflasi terbit tgl 1, ekspor ~tgl 15, hotel ~2 bln), Q = 3, S = 3, Y = 12.
- Tahun dasar BERGANTI (IHK 2012->2018 thn 2019/2020, NTP 2012->2018 thn 2019, IHPB 2018->2023): seri lama & baru = var_id BERBEDA.
  Panel ini menyimpan LEVEL per var_id apa adanya; transformasi ke pertumbuhan & penyambungan dilakukan di langkah penyaring.

  python panel_bps.py   -> data/olah/panel_bps.parquet (seri, var_id, judul, satuan, wilayah, kategori, frek, bulan, tersedia, nilai)
                           + data/olah/panel_bps_ringkas.parquet (1 baris per seri: frek, awal, akhir, n, n_2005_2018)
"""
import glob
from pathlib import Path

import pandas as pd

BULAN = {b: i + 1 for i, b in enumerate(["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September",
                                          "Oktober", "November", "Desember"])}
PETA_LAIN = {"Triwulan I": ("Q", 3), "Triwulan II": ("Q", 6), "Triwulan III": ("Q", 9), "Triwulan IV": ("Q", 12),
             "Semester 1 (Maret)": ("S", 3), "Semester 2 (September)": ("S", 9),
             "Tahun": ("Y", 12), "Tahunan": ("Y", 12), "Jumlah": ("Y", 12)}
JEDA = {"M": 2, "Q": 3, "S": 3, "Y": 12}
TAHUN_MAKS = 2026

d = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob("data/raw/histori/bps/bagian_*.parquet"))], ignore_index=True)
d["var_id"] = d["var_id"].astype(str)
# PERBAIKAN KODE (22 Nov 2026): 57 variabel berlabel wilayah berjenjang/berulang diunduh ulang dgn KODE (kumpul_bps.py --ulang)
pk = Path("data/raw/histori/bps/perbaikan_kode.parquet")
if pk.exists():
    b = pd.read_parquet(pk)
    b["var_id"] = b["var_id"].astype(str)
    lama = d["var_id"].isin(set(b["var_id"]))
    print(f"   perbaikan kode: {b['var_id'].nunique()} variabel ({lama.sum():,} baris lama -> {len(b):,} baris berkode)")
    b["wilayah"] = b["wilayah"].astype("string") + " [w" + b["kode_wilayah"].astype("string") + "]"
    b["kategori"] = b["kategori"].astype("string") + " [k" + b["kode_kategori"].astype("string") + "]"
    d = pd.concat([d[~lama], b[d.columns.intersection(b.columns)]], ignore_index=True)
else:
    print("   ⚠️ perbaikan_kode.parquet TIDAK ADA -> 57 variabel berlabel berulang akan TERCAMPUR")
d["wilayah"] = d["wilayah"].astype("string").str.replace(r"<[^>]+>", "", regex=True)     # tag HTML BPS (<b>...)
n0 = len(d)
d["periode"] = d["periode"].astype("string").str.strip()
frek = d["periode"].map(lambda p: "M" if p in BULAN else PETA_LAIN.get(p, (None, None))[0])
bln = d["periode"].map(lambda p: BULAN.get(p, PETA_LAIN.get(p, (None, None))[1]))
d["frek"], d["bln"] = frek, bln
buang_periode = d["frek"].isna()
print(f"   baris awal {n0:,}; periode tak dikenali (mingguan dll.) dibuang {buang_periode.sum():,}: "
      f"{d.loc[buang_periode, 'periode'].value_counts().head(4).to_dict()}")
d = d[~buang_periode]
proyeksi = d["tahun"] > TAHUN_MAKS
print(f"   tahun > {TAHUN_MAKS} (proyeksi) dibuang {proyeksi.sum():,}")
d = d[~proyeksi & d["tahun"].notna() & d["nilai"].notna()]
for k in ["wilayah", "kategori"]:
    d[k] = d[k].astype("string").fillna("-").str.strip()
d["seri"] = d["var_id"].astype("string") + "|" + d["wilayah"] + "|" + d["kategori"]
d["bulan"] = pd.PeriodIndex.from_fields(year=d["tahun"].astype(int), month=d["bln"].astype(int), freq="M")
dup = d.duplicated(["seri", "frek", "bulan"], keep="last")
print(f"   duplikat (seri, frek, bulan) dibuang {dup.sum():,} (nilai terakhir dipakai)")
d = d[~dup]
d["tersedia"] = d["bulan"] + d["frek"].map(JEDA).astype(int)
out = d[["seri", "var_id", "judul", "satuan", "wilayah", "kategori", "frek", "bulan", "tersedia", "nilai"]].reset_index(drop=True)
out["bulan"] = out["bulan"].dt.to_timestamp(how="end").dt.normalize().astype("datetime64[ns]")
out["tersedia"] = out["tersedia"].dt.to_timestamp(how="end").dt.normalize().astype("datetime64[ns]")
for k in ["seri", "var_id", "judul", "satuan", "wilayah", "kategori", "frek"]:
    out[k] = out[k].astype("string")
Path("data/olah").mkdir(parents=True, exist_ok=True)
out.to_parquet("data/olah/panel_bps.parquet", index=False)

r = out.groupby("seri").agg(var_id=("var_id", "first"), judul=("judul", "first"), wilayah=("wilayah", "first"), frek=("frek", "first"),
                            awal=("bulan", "min"), akhir=("bulan", "max"), n=("nilai", "size"),
                            n_latih=("bulan", lambda s: ((s >= "2005-01-01") & (s <= "2018-12-31")).sum()))
campur = out.groupby("seri")["frek"].nunique()
r["campur_frek"] = campur.reindex(r.index) > 1
r.to_parquet("data/olah/panel_bps_ringkas.parquet")
print(f"✅ panel BPS: {len(out):,} baris, {out['seri'].nunique():,} seri ({out['var_id'].nunique()} variabel); "
      f"frek: {out.drop_duplicates('seri')['frek'].value_counts().to_dict()}")
for f, minimal in [("M", 120), ("Q", 40), ("S", 20), ("Y", 10)]:
    x = r[(r["frek"] == f)]
    print(f"   {f}: {len(x):,} seri; cukup di latih 2005-2018 (>= {minimal} titik): {(x['n_latih'] >= minimal).sum():,} seri "
          f"dari {x.loc[x['n_latih'] >= minimal, 'var_id'].nunique()} variabel")
print(f"   seri dgn >1 frekuensi (seri sama dilaporkan bulanan & tahunan): {r['campur_frek'].sum():,}")
