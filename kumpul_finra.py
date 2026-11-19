"""
Volume SHORT harian semua saham AS dari FINRA (Reg SHO daily short sale volume).

Apa ini: setiap hari FINRA melaporkan, untuk ~12.000 kode saham AS, berapa lembar yang
dijual SHORT (menjual saham pinjaman, bertaruh harga turun) dibanding total volume
yang dilaporkan ke FINRA. Rasio short tinggi = banyak pihak bertaruh turun (atau market maker
sedang menyediakan likuiditas). Sering dipakai sebagai sinyal sentimen.

Sumber: https://cdn.finra.org/equity/regsho/daily/CNMSshvolYYYYMMDD.txt
Histori di server FINRA hanya tersedia sejak 1 Agustus 2018 (file lebih lama ditolak 403).

Cara pakai:
  python kumpul_finra.py              -> 10 hari terakhir -> data/raw/harian/finra_short/<tanggal UTC>.parquet
  python kumpul_finra.py --histori    -> semua sejak 2018-08-01, 1 file per tahun -> data/raw/histori/finra_short/
                                         (+ upload tiap tahun ke Hugging Face, bisa dilanjutkan kalau terputus)
  python kumpul_finra.py --tes        -> 5 hari terakhir, tanpa simpan (cek cepat di laptop)
"""
import io
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

URL = "https://cdn.finra.org/equity/regsho/daily/CNMSshvol{}.txt"
HEADER = {"User-Agent": "Mozilla/5.0 (quant-data-collector; personal research)"}
AWAL_HISTORI = date(2018, 8, 1)
REPO = "fadli-sparks/quant-data"
HARI_INI = datetime.now(timezone.utc).date()      # tanggal file = tanggal UTC server (aturan proyek)
NAMA_KOLOM = {"Date": "tanggal", "Symbol": "kode", "ShortVolume": "volume_short",
              "ShortExemptVolume": "volume_short_dikecualikan", "TotalVolume": "volume_total", "Market": "pasar"}

sesi = requests.Session()
sesi.headers.update(HEADER)


def ambil_hari(tgl):
    """Unduh satu hari. Hasil: DataFrame, atau None kalau hari libur/belum terbit (403/404)."""
    for percobaan in range(4):
        try:
            r = sesi.get(URL.format(tgl.strftime("%Y%m%d")), timeout=60)
            if r.status_code in (403, 404):
                return None                       # libur / akhir pekan / belum terbit
            r.raise_for_status()
            break
        except requests.exceptions.RequestException as e:
            print(f"   🔌 {tgl}: {type(e).__name__}, coba lagi...")
            time.sleep(5 * (percobaan + 1))
    else:
        print(f"   ⚠️  {tgl}: gagal 4x, dilewati")
        return None

    # dtype=str + keep_default_na=False: kode saham "NA" jangan dibaca sebagai kosong
    df = pd.read_csv(io.StringIO(r.text), sep="|", dtype=str, keep_default_na=False)
    df = df[df["Symbol"] != ""]                   # buang baris penutup (hanya berisi jumlah baris)
    df = df[df["Date"].str.fullmatch(r"\d{8}")]
    df = df.rename(columns=NAMA_KOLOM)
    df["tanggal"] = pd.to_datetime(df["tanggal"], format="%Y%m%d").astype("datetime64[ns]")
    for k in ["volume_short", "volume_short_dikecualikan", "volume_total"]:
        df[k] = pd.to_numeric(df[k], errors="coerce").astype("float64")
    df["kode"] = df["kode"].astype(str)
    df["pasar"] = df["pasar"].astype(str)
    return df[list(NAMA_KOLOM.values())]


def ambil_rentang(mulai, selesai, jeda=0.2):
    bagian = []
    tgl = mulai
    while tgl <= selesai:
        if tgl.weekday() < 5:                     # bursa AS hanya Senin-Jumat
            df = ambil_hari(tgl)
            if df is not None:
                bagian.append(df)
            time.sleep(jeda)
        tgl += timedelta(days=1)
    return pd.concat(bagian, ignore_index=True) if bagian else None


def ringkas(df):
    return (f"{len(df):,} baris, {df['tanggal'].nunique()} hari, {df['kode'].nunique():,} kode, "
            f"{df['tanggal'].min().date()} s/d {df['tanggal'].max().date()}")


# ===== Mode tes: cek cepat tanpa menyimpan =====
if "--tes" in sys.argv:
    df = ambil_rentang(HARI_INI - timedelta(days=7), HARI_INI)
    print(f"🧪 {ringkas(df)}")
    print(df.dtypes.to_string())
    contoh = df[df["kode"].isin(["AAPL", "NA", "EIDO"])].tail(6)
    print(contoh.to_string(index=False))
    rasio = (df["volume_short"] / df["volume_total"]).describe()
    print(f"\nRasio short (short/total): median {rasio['50%']:.1%}, min {rasio['min']:.1%}, maks {rasio['max']:.1%}")
    sys.exit()

# ===== Mode histori: sejak 2018-08-01, 1 file per tahun, upload tiap tahun =====
if "--histori" in sys.argv:
    from huggingface_hub import HfApi
    token = os.environ.get("HF_TOKEN") or Path("kunci_hf.txt").read_text().strip()
    api = HfApi(token=token)
    sudah = set(api.list_repo_files(REPO, repo_type="dataset"))
    folder = Path("data/raw/histori/finra_short")
    folder.mkdir(parents=True, exist_ok=True)

    for tahun in range(AWAL_HISTORI.year, HARI_INI.year + 1):
        jalur_repo = f"raw/histori/finra_short/{tahun}.parquet"
        # Tahun yang sudah lewat & sudah ter-upload: lewati (bisa dilanjutkan kalau terputus).
        # Tahun berjalan selalu diambil ulang (sampai kemarin).
        if jalur_repo in sudah and tahun < HARI_INI.year:
            print(f"⏭️  {tahun}: sudah ada di gudang")
            continue
        mulai = max(date(tahun, 1, 1), AWAL_HISTORI)
        selesai = min(date(tahun, 12, 31), HARI_INI)
        print(f"⬇️  {tahun}: {mulai} s/d {selesai} ...")
        df = ambil_rentang(mulai, selesai)
        if df is None:
            print(f"⚠️  {tahun}: tidak ada data")
            continue
        file = folder / f"{tahun}.parquet"
        df.to_parquet(file, index=False)
        print(f"✅ {tahun}: {ringkas(df)} ({file.stat().st_size / 1e6:.1f} MB)")
        api.upload_file(path_or_fileobj=str(file), path_in_repo=jalur_repo, repo_id=REPO,
                        repo_type="dataset", commit_message=f"Histori FINRA short {tahun}")
        print(f"   ☁️  ter-upload → {jalur_repo}")
    sys.exit()

# ===== Mode harian: 10 hari terakhir (sengaja tumpang tindih) =====
df = ambil_rentang(HARI_INI - timedelta(days=10), HARI_INI)
if df is None:
    print("❌ finra_short: tidak ada data sama sekali")
    sys.exit(1)
folder = Path("data/raw/harian/finra_short")
folder.mkdir(parents=True, exist_ok=True)
df.to_parquet(folder / f"{HARI_INI.isoformat()}.parquet", index=False)
print(f"✅ finra_short: {ringkas(df)}")
