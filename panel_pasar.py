"""
PANEL PASAR & KOMODITAS -> tabel bulanan panjang (riset #52 langkah 1). Skema sama: seri, kode, judul, frek, bulan, tersedia, nilai, pit.

ATURAN (ditetapkan 23 Nov 2026 SEBELUM melihat hubungan apa pun dengan return saham):
- Harga pasar praktis tidak direvisi -> pit = True, KECUALI Fama-French (Ken French kadang merevisi histori) & World Bank (pit=False).
- Yahoo raw/harga: SEMUA aset KECUALI saham individual (BBCA/BBRI/TLKM = sasaran, bukan variabel) & USDIDR (Yahoo IDR=X RUSAK, bagian 8;
  pakai ECB/JISDOR). Per bulan: RATA-RATA Close (kontrak berjangka '=F' melompat saat ganti kontrak -> rata bulanan meredam) & Close
  TERAKHIR. Minimal 10 hari data per bulan. tersedia = akhir bulan + 1 hari (pasar AS tutup setelah malam WIB).
- LME (westmetall): rata harga tunai, stok MEDIAN bulanan (tahan titik rusak, mis. nikel Apr 2012), spread (3 bln - tunai)/tunai rata
  bulanan (contango > 0 / backwardation < 0). +1 hari.
- Kurs ECB: rata per_usd bulanan semua mata uang. +1 hari. JISDOR: rata bulanan (ditetapkan 10:00 WIB) +0 hari (akhir bulan).
- CBOE indeks: rata 'tutup' bulanan; nilai <= 0 dibuang; titik > 5x atau < 0,2x median 21 hari SEBELUMNYA dibuang (hanya melihat ke belakang;
  menangkap VXHYG 2017-2018 rusak, DSPX 0). +1 hari.
- Put/call: rata rasio bulanan; arsip 2006-2019-10 (jenis total/ekuitas/indeks/etf/vix) DISAMBUNG dgn data baru 2019-10+ (TOTAL/EQUITY/
  INDEX/EXCHANGE TRADED PRODUCTS/CBOE VOLATILITY INDEX (VIX)); tidak tumpang tindih (arsip berakhir 4 Okt, baru mulai 7 Okt 2019). Produk
  baru lain (SPX, MXEF...) hanya 2019+. +1 hari.
- Fama-French harian AS: return bulanan = produk(1+r)-1 per faktor; terbit dgn jeda ~1-2 bln -> tersedia akhir bulan + 2 bln, pit=False.
- World Bank Pink Sheet bulanan (71 komoditas + 16 indeks): terbit ~awal bulan berikutnya -> akhir bulan + 10 hari, pit=False (revisi kecil).

CEK (26 Nov 2026): VIX 2008-11 62,7 & 2020-03 57,7; WTI akhir Apr 2020 18,84; nikel LME 2022-04; FF pasar 2008-10 -17,2%, 2020-03 -13,4%;
  World Bank vs LME (nikel/timah/tembaga) rasio median 0,999-1,000; 28 lompatan bulanan ekstrem (14 = Mar 2020, 12 = 1973-1979, sisanya COR1M 2018-02 & stok timah LME 2019-06).
  Bolong: platinum 18 bln, paladium 13 bln (Yahoo). Beberapa mata uang/komoditas BERHENTI (RUB 2022, BGN 2025, jelai/sorgum 2020...).

  python panel_pasar.py -> data/olah/panel_pasar.parquet + data/olah/panel_pasar_ringkas.parquet
"""
import glob
import re
from pathlib import Path

import numpy as np
import pandas as pd

KELUAR = []
AWAL_BULAN_INI = pd.Timestamp.today().to_period("M").to_timestamp()


def tambah(kode, judul, s, jeda_bulan=0, jeda_hari=1, pit=True):
    s = s.dropna()
    s = s[s.index < AWAL_BULAN_INI]
    if s.empty:
        return
    p = pd.PeriodIndex(s.index, freq="M")
    KELUAR.append(pd.DataFrame({"seri": "PASAR|" + kode, "kode": kode, "judul": judul, "frek": "M",
                                "bulan": p.to_timestamp(how="end").normalize().astype("datetime64[ns]"),
                                "tersedia": ((p + jeda_bulan).to_timestamp(how="end").normalize() + pd.Timedelta(days=jeda_hari)).astype("datetime64[ns]"),
                                "nilai": s.values.astype(float), "pit": pit}))


def bulanan(s, fungsi="mean", minimal=10):
    s = s.dropna()
    g = s.groupby(s.index.to_period("M"))
    hasil = getattr(g, fungsi)()[g.count() >= minimal]
    hasil.index = hasil.index.to_timestamp()
    return hasil


def nama(x):
    return re.sub(r"[^a-z0-9]+", "_", str(x).lower()).strip("_")


# ===== Yahoo: indeks, komoditas berjangka, VIX, DXY, yield, kripto =====
for f in sorted(glob.glob("data/raw/harga/*.parquet")):
    k = Path(f).stem
    if k in ("BBCA", "BBRI", "TLKM", "USDIDR"):
        continue
    d = pd.read_parquet(f)
    d.index = pd.DatetimeIndex(d.index).tz_localize(None).normalize().astype("datetime64[ns]")
    c = d["Close"].where(d["Close"] != 0)
    c = c[~c.index.duplicated(keep="last")]
    tambah(f"yahoo_{k.lower()}_rata", f"{k}: rata Close bulanan (Yahoo)", bulanan(c, "mean"))
    tambah(f"yahoo_{k.lower()}_akhir", f"{k}: Close terakhir bulan (Yahoo)", bulanan(c, "last"))

# ===== LME =====
lme = pd.read_parquet("data/raw/histori/lme/semua.parquet")
lme["tanggal"] = pd.to_datetime(lme["tanggal"])
for logam, x in lme.groupby("logam"):
    x = x.set_index("tanggal").sort_index()
    tambah(f"lme_{logam}_tunai", f"LME {logam}: rata harga tunai", bulanan(x["harga_tunai"], "mean"))
    tambah(f"lme_{logam}_stok", f"LME {logam}: stok gudang (median bulanan)", bulanan(x["stok"], "median"))
    spread = (x["harga_3bulan"] - x["harga_tunai"]) / x["harga_tunai"]
    tambah(f"lme_{logam}_spread3b", f"LME {logam}: spread (3 bln - tunai)/tunai (contango > 0)", bulanan(spread, "mean"))

# ===== Kurs ECB & JISDOR =====
ecb = pd.read_parquet("data/raw/kurs_ecb/semua.parquet")
ecb["tanggal"] = pd.to_datetime(ecb["tanggal"])
for mu, x in ecb.groupby("mata_uang"):
    if mu == "USD":
        continue
    tambah(f"kurs_ecb_{mu.lower()}", f"Kurs ECB {mu} per USD (rata bulanan)", bulanan(x.set_index("tanggal")["per_usd"], "mean"))
eur = ecb[ecb["mata_uang"] == "USD"].set_index("tanggal")["per_eur"]
tambah("kurs_ecb_usd_per_eur", "Kurs ECB USD per EUR (rata bulanan)", bulanan(eur, "mean"))
j = pd.read_parquet("data/raw/histori/jisdor/semua.parquet")
tambah("kurs_jisdor", "Kurs JISDOR USD/IDR (rata bulanan, 10:00 WIB)", bulanan(j.set_index(pd.to_datetime(j["tanggal"]))["kurs"], "mean"), jeda_hari=0)

# ===== CBOE indeks =====
cb = pd.read_parquet("data/raw/cboe/indeks.parquet")
cb["tanggal"] = pd.to_datetime(cb["tanggal"])
for ind, x in cb.groupby("indeks"):
    s = x.set_index("tanggal")["tutup"].sort_index()
    s = s[~s.index.duplicated(keep="last")].where(lambda v: v > 0)
    med = s.rolling(21, min_periods=10).median().shift(1)                 # hanya masa lalu
    rusak = (s > 5 * med) | (s < 0.2 * med)
    tambah(f"cboe_{nama(ind)}", f"CBOE {ind}: rata tutup bulanan (titik rusak dibuang)", bulanan(s.where(~rusak), "mean"))

# ===== Put/call (arsip + baru) =====
arsip = pd.read_parquet("data/raw/cboe/putcall_arsip.parquet")
arsip["tanggal"] = pd.to_datetime(arsip["tanggal"])
arsip["rasio"] = arsip["p_c_ratio"].fillna(arsip.get("vix_put_call_ratio"))
baru = pd.read_parquet("data/raw/histori/putcall/semua.parquet")
baru = baru[baru["ukuran"] == "RASIO"]
peta = {"total": "TOTAL", "ekuitas": "EQUITY", "indeks": "INDEX", "etf": "EXCHANGE TRADED PRODUCTS", "vix": "CBOE VOLATILITY INDEX (VIX)"}
for lama_n, baru_n in peta.items():
    a = arsip[arsip["jenis"] == lama_n].set_index("tanggal")["rasio"]
    b = baru[baru["produk"] == baru_n].set_index(pd.to_datetime(baru.loc[baru["produk"] == baru_n, "tanggal"]))["rasio"]
    s = pd.concat([a, b]).sort_index()
    s = s[~s.index.duplicated(keep="last")].where(lambda v: v > 0)
    tambah(f"putcall_{lama_n}", f"Put/call {baru_n} (rata bulanan; arsip 2006-2019 + baru)", bulanan(s, "mean"))
for prod in sorted(set(baru["produk"]) - set(peta.values())):
    x = baru[baru["produk"] == prod]
    s = x.set_index(pd.to_datetime(x["tanggal"]))["rasio"].where(lambda v: v > 0)
    tambah(f"putcall_{nama(prod)}", f"Put/call {prod} (2019+)", bulanan(s, "mean"))

# ===== Fama-French =====
for f in ["ff5_harian", "momentum_harian"]:
    d = pd.read_parquet(f"data/raw/riset/{f}.parquet")
    d.index = pd.to_datetime(d["tanggal"].astype(str), format="%Y%m%d") if d["tanggal"].dtype.kind in "iu" else pd.to_datetime(d["tanggal"])
    for kol in [c for c in d.columns if c not in ("tanggal", "RF")]:
        r = d[kol].astype(float)
        m = (1 + r).groupby(r.index.to_period("M")).prod() - 1
        m.index = m.index.to_timestamp()
        tambah(f"ff_{nama(kol)}", f"Fama-French AS {kol} (return bulanan)", m, jeda_bulan=2, jeda_hari=0, pit=False)

# ===== World Bank Pink Sheet =====
for f, awalan in [("harga_bulanan", "wb"), ("indeks_bulanan", "wbi")]:
    d = pd.read_parquet(f"data/raw/worldbank/{f}.parquet")
    d["bulan"] = pd.to_datetime(d["bulan"])
    for kom, x in d.groupby("komoditas"):
        s = pd.to_numeric(x.set_index("bulan")["harga"], errors="coerce")
        s = s[~s.index.duplicated(keep="last")].where(lambda v: v > 0)      # 0 = kosong (beras Thai 25% Mar-Jun 2008), bukan harga
        tambah(f"{awalan}_{nama(kom)}", f"World Bank {kom} {x['satuan'].iloc[0]}", s, jeda_hari=10, pit=False)

out = pd.concat(KELUAR, ignore_index=True)
for k in ["seri", "kode", "judul", "frek"]:
    out[k] = out[k].astype("string")
out["pit"] = out["pit"].astype(bool)
dup = out.duplicated(["seri", "bulan"]).sum()
assert dup == 0, f"{dup} dobel"
assert (out["tersedia"] >= out["bulan"]).all()
Path("data/olah").mkdir(parents=True, exist_ok=True)
out.to_parquet("data/olah/panel_pasar.parquet", index=False)
r = out.groupby("seri").agg(judul=("judul", "first"), awal=("bulan", "min"), akhir=("bulan", "max"), n=("nilai", "size"),
                            n_latih=("bulan", lambda s: ((s >= "2005-01-01") & (s <= "2018-12-31")).sum()))
r.to_parquet("data/olah/panel_pasar_ringkas.parquet")
print(f"✅ panel pasar: {out['seri'].nunique()} seri, {len(out):,} baris; cukup di latih (>= 120 bln): {(r['n_latih'] >= 120).sum()}")
print("   kelompok:", out.drop_duplicates("seri")["kode"].str.split("_").str[0].value_counts().to_dict())
