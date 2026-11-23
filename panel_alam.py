"""
PANEL ALAM -> tabel bulanan panjang (riset #52 langkah 1): cuaca 15 kota, iklim (ONI/SOI/MEI/DMI/Nino mingguan), matahari & geomagnetik,
gempa, titik api. Skema sama dgn panel_bps/panel_fred: seri, kode, judul, frek, bulan, tersedia, nilai, pit.

ATURAN (ditetapkan 23 Nov 2026 SEBELUM melihat hubungan apa pun dengan return saham):
- 'bulan' = akhir bulan data; 'tersedia' = kapan angka itu bisa diketahui (jeda konservatif):
  cuaca (reanalisis Open-Meteo/ERA5, ~5 hari jeda) +7 hari | ONI (rata 3 bln ditandai bulan TENGAH -> lengkap setelah bulan berikutnya,
  terbit ~awal bulan sesudahnya) akhir bulan label + 2 bln + 10 hari | SOI, MEI (MEI ditandai bulan KEDUA musim 2 bln) +1 bln + 10 hari |
  DMI/IOD (terlambat ~6 bln) +6 bln | Nino mingguan (rata bulanan anomali) +7 hari | geomagnetik/matahari (GFZ nowcast) +5 hari |
  gempa USGS +2 hari | titik api (MODIS/VIIRS 'SP' = arsip diproses ulang; saat itu tersedia versi NRT jumlahnya serupa) +7 hari.
- pit = False untuk SEMUA seri di panel ini: nilai = versi arsip terkini (reanalisis/revisi), bukan angka yang dilihat saat itu.
  Foto harian kita (raw/harian/iklim, cuaca, api, gempa) baru mulai Nov 2026 -> point-in-time sungguhan hanya ke depan.
- Cuaca per kota: rata suhu maks & min, jumlah hujan, rata sinar matahari (jam/hari; sumber dalam DETIK), angin maks, jumlah hari
  hujan lebat (>= 20 mm). Bulan dgn < 25 hari data DIBUANG (bulan berjalan / data bolong).
- Geomagnetik: rata Ap harian, maks Ap, jumlah hari badai (Ap >= 48), rata bintik matahari, rata F10.7 (diamati).
- Gempa (katalog USGS M4.5+ global sejak 1990): kotak Indonesia (bujur 94-142, lintang -11..7): jumlah M>=5, magnitudo maks, energi
  log10(sum 10^(1,5 M)); global: jumlah M>=6. Hanya type == 'earthquake'.
- Titik api (confidence MODIS >= 30; VIIRS 'n'/'h'): kotak FIRMS kita, Sumatra (bujur 95-106,5), Kalimantan (108-119, lintang -4,5..7):
  jumlah titik & jumlah FRP (daya radiatif, MW). Bulan TERAKHIR arsip SP bisa belum lengkap -> ditandai di ringkasan (cek manual).
- Bulan BERJALAN (saat panel dibangun) selalu DIBUANG (belum lengkap).
CEK KEWAJARAN (23 Nov 2026): gempa maks Aceh 2004-12 M9,1 / Nias 2005-03 M8,6 / Bengkulu 2007-09 M8,4 / Biak 1996-02 M8,1; titik api MODIS
2015-09 (61.986) & 2015-10 > 2006-10 > 2002-08 > 2019-09; hujan Jakarta 2002-01 & 2020-01 (banjir besar); ONI 2015-12 +2,59, 1997-12 +2,37,
2026-09 +2,46; DMI 1997-11, 2019-10; bintik matahari 30 bln tertinggi SEMUA sebelum 1995 = BENAR (siklus 19/21/22 lebih kuat; rata thn
1958 262 vs 2024 155); Ap harian maks 2003-10 = 204 (Halloween), 2024-05 = 271. Arsip SP: MODIS s/d 2026-08, VIIRS s/d 2026-07.

  python panel_alam.py -> data/olah/panel_alam.parquet + data/olah/panel_alam_ringkas.parquet
"""
import glob
from pathlib import Path

import numpy as np
import pandas as pd

KELUAR = []


def tambah(kode, judul, s, jeda_bulan=0, jeda_hari=0, frek="M"):
    s = s.dropna()
    s = s[s.index < pd.Timestamp.today().to_period("M").to_timestamp()]   # bulan BERJALAN belum lengkap (gempa/nino Nov 2026 separuh)
    if s.empty:
        return
    bulan = pd.PeriodIndex(s.index, freq="M").to_timestamp(how="end").normalize().astype("datetime64[ns]")
    tersedia = (pd.PeriodIndex(s.index, freq="M") + jeda_bulan).to_timestamp(how="end").normalize() + pd.Timedelta(days=jeda_hari)
    KELUAR.append(pd.DataFrame({"seri": "ALAM|" + kode, "kode": kode, "judul": judul, "frek": frek, "bulan": bulan,
                                "tersedia": tersedia.astype("datetime64[ns]"), "nilai": s.values.astype(float), "pit": False}))


# ===== cuaca 15 kota =====
for f in sorted(glob.glob("data/raw/cuaca/*.parquet")):
    kota = Path(f).stem
    d = pd.read_parquet(f)
    d.index = pd.DatetimeIndex(d.index).tz_localize(None).normalize()
    d = d[~d.index.duplicated(keep="last")]
    g = d.groupby(d.index.to_period("M"))
    cukup = g["precipitation_sum"].count() >= 25
    agg = {"tmax": g["temperature_2m_max"].mean(), "tmin": g["temperature_2m_min"].mean(),
           "hujan": g["precipitation_sum"].sum(min_count=25), "sinar_jam": g["sunshine_duration"].mean() / 3600,
           "angin_maks": g["wind_speed_10m_max"].max(), "hari_hujan_lebat": g["precipitation_sum"].apply(lambda x: (x >= 20).sum())}
    ket = {"tmax": "rata suhu maks (C)", "tmin": "rata suhu min (C)", "hujan": "jumlah hujan (mm)", "sinar_jam": "rata sinar matahari (jam/hari)",
           "angin_maks": "angin maks (km/j)", "hari_hujan_lebat": "hari hujan >= 20 mm"}
    for k, s in agg.items():
        s = s[cukup]
        s.index = s.index.to_timestamp()
        tambah(f"cuaca_{kota}_{k}", f"Cuaca {kota}: {ket[k]}", s, jeda_hari=7)

# ===== iklim =====
aturan_iklim = {"oni": (2, 10, "ONI El Nino (rata 3 bln, ditandai bulan tengah)"), "soi": (1, 10, "SOI (negatif = El Nino)"),
                "mei": (1, 10, "MEI v2 (ditandai bulan kedua)"), "dmi": (6, 0, "DMI/IOD (positif = Indonesia kering; terlambat ~6 bln)")}
for k, (jb, jh, judul) in aturan_iklim.items():
    d = pd.read_parquet(f"data/raw/iklim/{k}.parquet")
    s = d.set_index(pd.to_datetime(d["tanggal"]))["nilai"]
    s = s[(s > -50) & (s < 50)]                       # kode kosong (-999.9/-9999) yang lolos
    tambah(f"iklim_{k}", judul, s, jeda_bulan=jb, jeda_hari=jh)
nm = pd.read_parquet("data/raw/iklim/nino_mg.parquet")
nm.index = pd.to_datetime(nm["tanggal"])
for kol in ["nino12_anomali", "nino3_anomali", "nino34_anomali", "nino4_anomali"]:
    g = nm[kol].where(nm[kol] > -50).groupby(nm.index.to_period("M"))
    s = g.mean()[g.count() >= 3]
    s.index = s.index.to_timestamp()
    tambah(f"iklim_{kol}_mg", f"Anomali suhu laut {kol.split('_')[0]} (rata mingguan)", s, jeda_hari=7)

# ===== geomagnetik & matahari =====
gm = pd.read_parquet("data/raw/alam/geomagnetik_matahari.parquet")
gm.index = pd.to_datetime(gm["tanggal"])
for k, c in [("Ap", "Ap"), ("bintik", "bintik_matahari"), ("f107", "f107_obs")]:
    gm[c] = gm[c].where(gm[c] >= 0)
g = gm.groupby(gm.index.to_period("M"))
for k, s, judul in [("ap_rata", g["Ap"].mean(), "rata Ap harian (geomagnetik)"), ("ap_maks", g["Ap"].max(), "Ap harian maks"),
                    ("hari_badai", g["Ap"].apply(lambda x: (x >= 48).sum()), "hari badai geomagnetik (Ap >= 48)"),
                    ("bintik", g["bintik_matahari"].mean(), "rata bintik matahari"), ("f107", g["f107_obs"].mean(), "rata fluks radio F10.7")]:
    s = s[g["Ap"].count() >= 25]
    s.index = s.index.to_timestamp()
    tambah(f"matahari_{k}", judul, s, jeda_hari=5)

# ===== gempa =====
gp = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob("data/raw/histori/gempa/*.parquet"))], ignore_index=True)
gp = gp[gp["type"] == "earthquake"].drop_duplicates("id")
gp["waktu"] = pd.to_datetime(gp["time"], utc=True).dt.tz_localize(None)
gp["bln"] = gp["waktu"].dt.to_period("M")
semua_bln = pd.period_range(gp["bln"].min(), gp["bln"].max(), freq="M")
idn = gp[gp["longitude"].between(94, 142) & gp["latitude"].between(-11, 7)]
for k, s, judul in [("idn_m5", idn[idn["mag"] >= 5].groupby("bln").size(), "jumlah gempa M>=5 kotak Indonesia"),
                    ("idn_maks", idn.groupby("bln")["mag"].max(), "magnitudo maks kotak Indonesia"),
                    ("idn_energi", np.log10(idn.groupby("bln")["mag"].apply(lambda m: (10 ** (1.5 * m)).sum())), "log10 energi gempa Indonesia"),
                    ("global_m6", gp[gp["mag"] >= 6].groupby("bln").size(), "jumlah gempa M>=6 global")]:
    s = s.reindex(semua_bln, fill_value=0 if k in ("idn_m5", "global_m6") else np.nan)
    s.index = s.index.to_timestamp()
    tambah(f"gempa_{k}", judul, s, jeda_hari=2)

# ===== titik api =====
for sumber, syarat in [("MODIS_SP", lambda d: pd.to_numeric(d["confidence"], errors="coerce") >= 30),
                       ("VIIRS_SNPP_SP", lambda d: d["confidence"].astype(str).isin(["n", "h", "nominal", "high"]))]:
    fs = sorted(glob.glob(f"data/raw/histori/api/{sumber}_*.parquet"))
    if not fs:
        continue
    a = pd.concat([pd.read_parquet(f, columns=["latitude", "longitude", "acq_date", "confidence", "frp"]) for f in fs], ignore_index=True)
    a = a[syarat(a)]
    a["bln"] = pd.to_datetime(a["acq_date"]).dt.to_period("M")
    rentang = pd.period_range(a["bln"].min(), a["bln"].max(), freq="M")
    wilayah = {"semua": a, "sumatra": a[a["longitude"].between(95, 106.5)],
               "kalimantan": a[a["longitude"].between(108, 119) & a["latitude"].between(-4.5, 7)]}
    for w, x in wilayah.items():
        for k, s in [("jumlah", x.groupby("bln").size()), ("frp", x.groupby("bln")["frp"].sum())]:
            s = s.reindex(rentang, fill_value=0)
            s.index = s.index.to_timestamp()
            tambah(f"api_{sumber.split('_')[0].lower()}_{w}_{k}", f"Titik api {sumber} {w}: {'jumlah titik' if k == 'jumlah' else 'jumlah FRP (MW)'}",
                   s, jeda_hari=7)

out = pd.concat(KELUAR, ignore_index=True)
for k in ["seri", "kode", "judul", "frek"]:
    out[k] = out[k].astype("string")
out["pit"] = out["pit"].astype(bool)
dup = out.duplicated(["seri", "bulan"]).sum()
assert dup == 0, f"{dup} dobel"
assert (out["tersedia"] > out["bulan"]).all(), "ada nilai tersedia sebelum/sama dgn akhir bulannya"
Path("data/olah").mkdir(parents=True, exist_ok=True)
out.to_parquet("data/olah/panel_alam.parquet", index=False)
r = out.groupby("seri").agg(judul=("judul", "first"), awal=("bulan", "min"), akhir=("bulan", "max"), n=("nilai", "size"),
                            n_latih=("bulan", lambda s: ((s >= "2005-01-01") & (s <= "2018-12-31")).sum()))
r.to_parquet("data/olah/panel_alam_ringkas.parquet")
print(f"✅ panel alam: {out['seri'].nunique()} seri, {len(out):,} baris; seri cukup di latih (>= 120 bln): {(r['n_latih'] >= 120).sum()}")
print("   kelompok:", out.drop_duplicates("seri")["kode"].str.split("_").str[0].value_counts().to_dict())
