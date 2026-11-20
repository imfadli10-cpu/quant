"""
INDEKS IKLIM GLOBAL yang memengaruhi ekonomi Indonesia (NOAA, gratis, tanpa kunci).

Kenapa: El Nino -> kemarau panjang di Indonesia -> produksi sawit turun (jeda 6-12 bulan), panen padi terganggu, harga
pangan & inflasi naik, kebakaran hutan. IOD positif (Indian Ocean Dipole) memperkuat efek kering. La Nina kebalikannya.
Seri:
  oni     : Oceanic Nino Index, anomali suhu laut Nino 3.4 rata-rata 3 bulan (sejak 1950), ditandai di BULAN TENGAH
            (DJF -> Januari). >= +0,5 = El Nino, <= -0,5 = La Nina.                        (CPC oni.ascii.txt)
  soi     : Southern Oscillation Index terstandar, bulanan (sejak 1951). Negatif = El Nino.   (CPC soi, tabel STANDARDIZED)
  mei     : Multivariate ENSO Index v2, musim 2 bulan (sejak 1979), ditandai di bulan KEDUA. (PSL meiv2.data)
  dmi     : Dipole Mode Index (IOD), bulanan (sejak 1870). Positif = Indonesia lebih kering.  (PSL dmi.had.long.data)
  nino_mg : suhu laut & anomali MINGGUAN Nino 1+2, 3, 3.4, 4 (sejak Sep 1981) - paling cepat terbit. (CPC wksst9120.for)
WAKTU TERBIT (penting untuk riset, hindari mengintip masa depan): ONI/SOI/MEI/DMI terbit ~awal-pertengahan bulan berikutnya
  dan BISA DIREVISI; mingguan terbit beberapa hari setelah minggu itu. Simpan foto harian -> bisa tahu versi yang ada saat itu.
Isi: data/raw/iklim/<seri>.parquet (histori lengkap, ditimpa) + data/raw/harian/iklim/<tanggal UTC>.parquet
     (foto 36 bulan terakhir semua seri, format panjang seri/tanggal/kolom/nilai -> melacak revisi & untuk validasi).
Cara pakai: python kumpul_iklim.py [--tes]
"""
import re
import sys
import time
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd
import requests

UA = {"User-Agent": "quant-data-collector/1.0 (personal research project)"}
URL = {"oni": "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt",
       "soi": "https://www.cpc.ncep.noaa.gov/data/indices/soi",
       "mei": "https://psl.noaa.gov/enso/mei/data/meiv2.data",
       "dmi": "https://psl.noaa.gov/gcos_wgsp/Timeseries/Data/dmi.had.long.data",
       "nino_mg": "https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for"}
SEKARANG = datetime.now(timezone.utc)
MUSIM_ONI = {"DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6, "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10,
             "OND": 11, "NDJ": 12}


def ambil(url):
    for percobaan in range(4):
        try:
            r = requests.get(url, headers=UA, timeout=60)
            r.raise_for_status()
            return r.text
        except requests.exceptions.RequestException as e:
            print(f"   🔌 {type(e).__name__}, coba lagi...")
            time.sleep(15 * (percobaan + 1))
    raise RuntimeError(f"gagal: {url}")


def kosongkan(x):
    return np.where(np.asarray(x, dtype=float) <= -99, np.nan, x)


def baca_oni(t):
    d = pd.read_csv(StringIO(t), sep=r"\s+")
    d["tanggal"] = pd.to_datetime(dict(year=d["YR"], month=d["SEAS"].map(MUSIM_ONI), day=1))
    return pd.DataFrame({"tanggal": d["tanggal"], "nilai": d["ANOM"].astype(float), "suhu": d["TOTAL"].astype(float)})


def baca_tabel_tahun_bulan(baris_data, lebar=None, bulan_geser=0):
    """Baris 'TAHUN v1..v12'. lebar=None -> dipisah spasi; lebar=6 -> kolom lebar tetap (SOI)."""
    hasil = []
    for b in baris_data:
        if lebar:
            if not re.match(r"^\d{4}", b):
                continue
            th = int(b[:4])
            nilai = [b[4 + i * lebar: 4 + (i + 1) * lebar] for i in range(12)]
        else:
            p = b.split()
            if len(p) != 13 or not re.fullmatch(r"\d{4}", p[0]):
                continue
            th, nilai = int(p[0]), p[1:]
        for i, v in enumerate(nilai):
            try:
                hasil.append((pd.Timestamp(th, i + 1, 1), float(v)))
            except ValueError:
                pass
    d = pd.DataFrame(hasil, columns=["tanggal", "nilai"])
    d["nilai"] = kosongkan(d["nilai"])
    return d.dropna().sort_values("tanggal").reset_index(drop=True)


def baca_soi(t):
    baris = t.splitlines()
    mulai = next(i for i, b in enumerate(baris) if "STANDARDIZED" in b)
    return baca_tabel_tahun_bulan(baris[mulai:], lebar=6)


def baca_mei(t):
    d = baca_tabel_tahun_bulan(t.splitlines()[1:])
    d["tanggal"] = d["tanggal"] + pd.offsets.MonthBegin(1)      # musim 'DJ' (Des-Jan) -> ditandai Januari (bulan kedua)
    return d


def baca_dmi(t):
    return baca_tabel_tahun_bulan(t.splitlines()[1:])


def baca_nino_mg(t):
    hasil = []
    for b in t.splitlines():
        m = re.match(r"^\s*(\d{2}[A-Z]{3}\d{4})(.*)$", b)
        if not m:
            continue
        angka = re.findall(r"-?\d+\.\d", m.group(2))
        if len(angka) != 8:
            continue
        hasil.append([pd.to_datetime(m.group(1), format="%d%b%Y")] + [float(a) for a in angka])
    kolom = ["tanggal"] + [f"{z}_{k}" for z in ["nino12", "nino3", "nino34", "nino4"] for k in ["suhu", "anomali"]]
    d = pd.DataFrame(hasil, columns=kolom)
    d["nilai"] = d["nino34_anomali"]
    return d


BACA = {"oni": baca_oni, "soi": baca_soi, "mei": baca_mei, "dmi": baca_dmi, "nino_mg": baca_nino_mg}
hasil, gagal = {}, []
for seri, url in URL.items():
    try:
        d = BACA[seri](ambil(url))
        d["tanggal"] = pd.to_datetime(d["tanggal"]).astype("datetime64[ns]")
        for c in d.columns:
            if c != "tanggal":
                d[c] = d[c].astype("float64")
        hasil[seri] = d
        print(f"✅ {seri:8} {len(d):6} baris, {d['tanggal'].min().date()} s/d {d['tanggal'].max().date()}, "
              f"terakhir {d['nilai'].iloc[-1]:+.2f}")
    except Exception as e:
        gagal.append(seri)
        print(f"⚠️  {seri}: {type(e).__name__}: {str(e)[:100]}")
    time.sleep(1)
if not hasil:
    sys.exit(1)
if "--tes" in sys.argv:
    sys.exit()

folder = Path("data/raw/iklim")
folder.mkdir(parents=True, exist_ok=True)
for seri, d in hasil.items():
    d.to_parquet(folder / f"{seri}.parquet", index=False)
batas = pd.Timestamp(SEKARANG.date()) - pd.DateOffset(months=36)
foto = pd.concat([d[d["tanggal"] >= batas].melt(id_vars="tanggal", var_name="kolom", value_name="isi").assign(seri=seri)
                  for seri, d in hasil.items()], ignore_index=True).rename(columns={"isi": "nilai"})
foto["waktu_ambil"] = pd.Timestamp(SEKARANG.replace(tzinfo=None)).floor("s")
foto = foto.astype({"seri": "string", "kolom": "string"})
foto["waktu_ambil"] = foto["waktu_ambil"].astype("datetime64[ns]")
harian = Path("data/raw/harian/iklim")
harian.mkdir(parents=True, exist_ok=True)
foto.to_parquet(harian / f"{SEKARANG.date().isoformat()}.parquet", index=False)
print(f"💾 data/raw/iklim/ ({len(hasil)} seri) + foto harian {len(foto)} baris" + (f" | GAGAL: {gagal}" if gagal else ""))
if gagal:
    sys.exit(1)
