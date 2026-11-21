"""
CBOE DAILY MARKET STATISTICS (opsi AS): rasio PUT/CALL + volume & open interest call/put per produk (total, indeks, ETP, ekuitas, VIX, SPX,
MXEF pasar berkembang, dll.). Sumber: JSON publik cdn.cboe.com/data/us/options/market_statistics/daily/<YYYY-MM-DD>_daily_options
(robots www.cboe.com hanya melarang /book/ & */market_statistics/volume_reports/). Tersedia sejak ~akhir Okt 2019 = PERSIS menyambung
arsip lama raw/cboe/putcall_arsip (2006 - 2019-10). Hari libur/akhir pekan = 403 (wajar, dilewati).

  python kumpul_putcall.py            harian: 10 hari kalender terakhir -> data/raw/harian/putcall/<tanggal UTC>.parquet
  python kumpul_putcall.py --histori  sejak 2019-10-01 -> data/raw/histori/putcall/semua.parquet (sekali; ~1.800 permintaan, ~15 menit)
  python kumpul_putcall.py --tes      3 hari terakhir, tanpa simpan
Format panjang: tanggal, produk, ukuran ('VOLUME' / 'OPEN INTEREST' / 'RASIO'), call, put, total, rasio (rasio hanya utk ukuran 'RASIO').
"""
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

URL = "https://cdn.cboe.com/data/us/options/market_statistics/daily/{}_daily_options"
H = {"User-Agent": "quant-data-collector/1.0 (personal research project)"}
HISTORI, TES = "--histori" in sys.argv, "--tes" in sys.argv
SEKARANG = datetime.now(timezone.utc)


def ambil(tgl):
    for coba in range(3):
        try:
            r = requests.get(URL.format(tgl.isoformat()), headers=H, timeout=60)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (403, 404):
                return None                       # bukan hari bursa / belum terbit
            print(f"   ⚠️ {tgl}: HTTP {r.status_code}")
        except Exception as e:
            print(f"   🔌 {tgl}: {type(e).__name__}")
        time.sleep(5 * (coba + 1))
    return "GAGAL"


def urai(tgl, j):
    baris = []
    for x in j.get("ratios", []):
        nama = x["name"].replace(" PUT/CALL RATIO", "")
        baris.append((tgl, nama, "RASIO", None, None, None, pd.to_numeric(x.get("value"), errors="coerce")))
    for produk, isi in j.items():
        if produk == "ratios" or not isinstance(isi, list):
            continue
        for x in isi:
            baris.append((tgl, produk, x.get("name"), x.get("call"), x.get("put"), x.get("total"), None))
    return baris


hari_ini = SEKARANG.date()
if HISTORI:
    mulai = date(2019, 10, 1)
else:
    mulai = hari_ini - timedelta(days=3 if TES else 10)
semua, kosong, gagal = [], 0, []
t = mulai
while t <= hari_ini:
    if t.weekday() < 5:
        j = ambil(t)
        if j == "GAGAL":
            gagal.append(t)
        elif j is None:
            kosong += 1
        else:
            semua += urai(pd.Timestamp(t), j)
        time.sleep(0.3)
        if HISTORI and t.day == 1 and t.month in (1, 7):
            print(f"   {t}: {len(semua):,} baris", flush=True)
    t += timedelta(days=1)
df = pd.DataFrame(semua, columns=["tanggal", "produk", "ukuran", "call", "put", "total", "rasio"])
for k in ["call", "put", "total", "rasio"]:
    df[k] = pd.to_numeric(df[k], errors="coerce").astype("float64")
df["tanggal"] = pd.to_datetime(df["tanggal"]).astype("datetime64[ns]")
for k in ["produk", "ukuran"]:
    df[k] = df[k].astype("string")
# rasio tepat 0 = tidak ada put (sering 0/0 saat produk tidak diperdagangkan, mis. 2025-01-09 hari berkabung Carter: hanya sesi
# pendek opsi INDEKS, opsi ekuitas tutup -> EQUITY tercatat 0,00) -> tidak informatif -> dikosongkan
df.loc[(df["ukuran"] == "RASIO") & (df["rasio"] == 0), "rasio"] = float("nan")
n_hari = df["tanggal"].nunique()
print(f"✅ put/call CBOE: {n_hari} hari, {len(df):,} baris; hari kosong (libur/akhir) {kosong}; gagal {len(gagal)} {gagal[:5]}")
if n_hari == 0 or len(gagal) > max(3, 0.02 * (n_hari + len(gagal))):
    print("❌ terlalu banyak gagal / kosong")
    sys.exit(1)
tot = df[(df["produk"] == "TOTAL") & (df["ukuran"] == "RASIO")].set_index("tanggal")["rasio"]
print(f"   rasio TOTAL: terakhir {tot.iloc[-1]:.2f} ({tot.index[-1]:%Y-%m-%d}), median {tot.median():.2f}, min {tot.min():.2f}, maks {tot.max():.2f}")
if TES:
    print(df[df["ukuran"] == "RASIO"].tail(8).to_string())
    sys.exit(0)
f = Path("data/raw/histori/putcall/semua.parquet") if HISTORI else Path(f"data/raw/harian/putcall/{hari_ini.isoformat()}.parquet")
f.parent.mkdir(parents=True, exist_ok=True)
df.to_parquet(f, index=False)
print(f"💾 {f}")
