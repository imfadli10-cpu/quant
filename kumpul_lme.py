"""
Harga resmi harian LME (London Metal Exchange) + stok gudang LME untuk 6 logam dasar.

Logam: nikel, timah, tembaga, aluminium, seng, timbal.
Kolom: harga_tunai (cash-settlement, USD/ton), harga_3bulan (kontrak 3 bulan), stok (ton di gudang LME).
Kenapa penting: Indonesia produsen nikel & timah terbesar dunia (INCO, ANTM, TINS, NCKL, MBMA).
Stok gudang = data "aneh" yang jarang dipakai: stok turun tajam sering tanda pasokan ketat.

Sumber: tabel publik westmetall.com (robots.txt tidak melarang). Histori tersedia sejak 2008.

Cara pakai:
  python kumpul_lme.py            -> 40 hari terakhir -> data/raw/harian/lme/<tanggal UTC>.parquet
  python kumpul_lme.py --histori  -> semua sejak 2008 -> data/raw/histori/lme/semua.parquet
                                     (lalu upload: python upload_satu.py data/raw/histori/lme)
  python kumpul_lme.py --tes      -> cek cepat tahun ini, tanpa simpan
"""
import io
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

URL = "https://www.westmetall.com/en/markdaten.php"
HEADER = {"User-Agent": "quant-data-collector/1.0 (personal research project)"}
LOGAM = {"nikel": "LME_Ni_cash", "timah": "LME_Sn_cash", "tembaga": "LME_Cu_cash",
         "aluminium": "LME_Al_cash", "seng": "LME_Zn_cash", "timbal": "LME_Pb_cash"}
AWAL_HISTORI = 2008
JEDA = 2                                         # detik antar permintaan (sopan ke server kecil)
HARI_INI = datetime.now(timezone.utc).date()     # tanggal file = tanggal UTC server (aturan proyek)


def ambil_tahun(nama, field, tahun):
    """Satu tabel (1 logam, 1 tahun) -> DataFrame rapi, atau None kalau gagal/kosong."""
    for percobaan in range(4):
        try:
            r = requests.get(URL, params={"action": "table", "field": field, "year": tahun},
                             headers=HEADER, timeout=60)
            r.raise_for_status()
            break
        except requests.exceptions.RequestException as e:
            print(f"   🔌 {nama} {tahun}: {type(e).__name__}, coba lagi...")
            time.sleep(10 * (percobaan + 1))
    else:
        print(f"   ⚠️  {nama} {tahun}: gagal 4x")
        return None
    try:
        t = pd.read_html(io.StringIO(r.text))[0]
    except (ValueError, IndexError):
        return None
    if t.empty or t.shape[1] < 4:
        return None
    t = t.iloc[:, :4].astype(str)
    t.columns = ["tanggal", "harga_tunai", "harga_3bulan", "stok"]
    # Di tengah tabel ada baris judul berulang (pemisah bulan): tanggalnya tidak terbaca -> dibuang
    t["tanggal"] = pd.to_datetime(t["tanggal"].str.strip(), format="%d. %B %Y", errors="coerce")
    t = t.dropna(subset=["tanggal"])
    for k in ["harga_tunai", "harga_3bulan", "stok"]:
        t[k] = pd.to_numeric(t[k].str.replace(",", "", regex=False), errors="coerce").astype("float64")
    t["tanggal"] = t["tanggal"].astype("datetime64[ns]")
    t.insert(1, "logam", nama)
    return t


def ambil(tahun_list):
    bagian = []
    for nama, field in LOGAM.items():
        for tahun in tahun_list:
            t = ambil_tahun(nama, field, tahun)
            if t is not None:
                bagian.append(t)
            time.sleep(JEDA)
    if not bagian:
        return None
    df = pd.concat(bagian, ignore_index=True)
    df = df.drop_duplicates(["tanggal", "logam"], keep="first").sort_values(["logam", "tanggal"])
    return df.reset_index(drop=True)


def ringkas(df):
    per = df.groupby("logam")["tanggal"].agg(["min", "max", "count"])
    teks = ", ".join(f"{l} {r['count']}" for l, r in per.iterrows())
    return (f"{len(df):,} baris, {df['tanggal'].min().date()} s/d {df['tanggal'].max().date()} "
            f"(hari per logam: {teks})")


if "--tes" in sys.argv:
    df = ambil([HARI_INI.year])
    print(f"🧪 {ringkas(df)}")
    print(df.dtypes.to_string())
    print(df.groupby("logam").tail(1).to_string(index=False))
    print("Nilai kosong per kolom:", df.isna().sum().to_dict())
    sys.exit()

if "--histori" in sys.argv:
    df = ambil(range(AWAL_HISTORI, HARI_INI.year + 1))
    folder = Path("data/raw/histori/lme")
    folder.mkdir(parents=True, exist_ok=True)
    df.to_parquet(folder / "semua.parquet", index=False)
    print(f"✅ histori LME: {ringkas(df)}")
    print("   Upload: python upload_satu.py data/raw/histori/lme")
    sys.exit()

# Harian: tahun ini (+ tahun lalu kalau awal Januari), simpan 40 hari terakhir (sengaja tumpang tindih)
tahun = [HARI_INI.year] if HARI_INI.month > 1 else [HARI_INI.year - 1, HARI_INI.year]
df = ambil(tahun)
if df is None:
    print("❌ lme: tidak ada data sama sekali")
    sys.exit(1)
df = df[df["tanggal"] >= pd.Timestamp(HARI_INI - timedelta(days=40))]
folder = Path("data/raw/harian/lme")
folder.mkdir(parents=True, exist_ok=True)
df.to_parquet(folder / f"{HARI_INI.isoformat()}.parquet", index=False)
print(f"✅ lme: {ringkas(df)}")
