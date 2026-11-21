"""
INDEKS VOLATILITAS & SENTIMEN OPSI dari CBOE (file CSV publik cdn.cboe.com; robots.txt www.cboe.com hanya melarang /book/
& laporan volume). Harian, histori panjang, DITIMPA tiap hari.

Isi:
  data/raw/cboe/indeks.parquet   format panjang: indeks, tanggal, buka, tertinggi, terendah, tutup (indeks 1-kolom: buka..terendah kosong)
      VIX (1990+), struktur waktu VIX9D/VIX3M/VIX6M/VIX1Y/VIX1D, VVIX (volatilitas VIX), SKEW & SMILE (risiko ekor),
      VXEEM (volatilitas PASAR BERKEMBANG), VXFXI (China), VXEWZ (Brasil), VXEFA (negara maju non-AS), VXN/RVX/VXD,
      OVX (minyak), GVZ (emas), VXSLV, VXGDX, VXTLT (obligasi AS 20+ thn), VXHYG (obligasi sampah), COR1M/COR3M (korelasi
      tersirat), DSPX (dispersi), VIXEQ, volatilitas saham tunggal (AAPL/AMZN/GOOG/IBM/GS), SPX.
  data/raw/cboe/putcall_arsip.parquet   ARSIP rasio put/call harian (total, ekuitas, indeks, VIX, ETF) s/d Okt 2019
      (sesudahnya CBOE tidak menerbitkan sebagai file).
Cara pakai: python kumpul_cboe.py | --tes (3 indeks, tanpa simpan)
"""
import io
import sys
import time
from pathlib import Path

import pandas as pd
import requests

H = {"User-Agent": "quant-data-collector/1.0 (personal research project)"}
URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/{}_History.csv"
INDEKS = ["VIX", "VIX9D", "VIX3M", "VIX6M", "VIX1Y", "VIX1D", "VVIX", "SKEW", "SMILE", "VXEEM", "VXFXI", "VXEWZ", "VXEFA",
          "VXN", "RVX", "VXD", "OVX", "GVZ", "VXSLV", "VXGDX", "VXTLT", "VXHYG", "COR1M", "COR3M", "DSPX", "VIXEQ",
          "VXAPL", "VXAZN", "VXGOG", "VXIBM", "VXGS", "SPX"]
PUTCALL = {"total": "totalpc", "ekuitas": "equitypc", "indeks": "indexpc", "vix": "vixpc", "etf": "etppc"}
TES = "--tes" in sys.argv
if TES:
    INDEKS = ["VIX", "VXEEM", "SKEW"]


def ambil(url):
    for percobaan in range(4):
        try:
            r = requests.get(url, headers=H, timeout=(15, 60))
            r.raise_for_status()
            return r.text
        except requests.RequestException as e:
            if percobaan == 3:
                raise
            time.sleep(5 * (percobaan + 1))


bag, gagal = [], []
for k in INDEKS:
    try:
        d = pd.read_csv(io.StringIO(ambil(URL.format(k))))
    except Exception as e:
        print(f"⚠️  {k}: {type(e).__name__}: {str(e)[:80]}")
        gagal.append(k)
        continue
    d.columns = [c.strip().upper() for c in d.columns]
    out = pd.DataFrame({"indeks": k, "tanggal": pd.to_datetime(d["DATE"], format="%m/%d/%Y", errors="coerce")})
    if "CLOSE" in d:
        for a, b in [("buka", "OPEN"), ("tertinggi", "HIGH"), ("terendah", "LOW"), ("tutup", "CLOSE")]:
            out[a] = pd.to_numeric(d[b], errors="coerce")
    else:
        nilai = [c for c in d.columns if c != "DATE"][0]
        out["buka"] = out["tertinggi"] = out["terendah"] = float("nan")
        out["tutup"] = pd.to_numeric(d[nilai], errors="coerce")
    bag.append(out.dropna(subset=["tanggal"]))
    time.sleep(0.3)
df = pd.concat(bag, ignore_index=True).drop_duplicates(["indeks", "tanggal"], keep="last")
df["indeks"] = df["indeks"].astype("string")
df["tanggal"] = df["tanggal"].astype("datetime64[ns]")
ringkas = df.groupby("indeks")["tanggal"].agg(["min", "max", "count"])
print(f"✅ {df['indeks'].nunique()} indeks, {len(df):,} baris; terbaru {df['tanggal'].max():%Y-%m-%d}")
akhir = df[df["tanggal"] == df["tanggal"].max()].set_index("indeks")["tutup"]
print("   terakhir: " + ", ".join(f"{k} {akhir[k]:.2f}" for k in ["VIX", "VXEEM", "SKEW"] if k in akhir))
lompat = df.sort_values(["indeks", "tanggal"]).groupby("indeks")["tutup"].pct_change().abs()
print(f"   perubahan harian > 100%: {int((lompat > 1).sum())} titik (cek kualitas)")

pc = []
for nama, f in ({} if TES else PUTCALL).items():
    try:
        teks = ambil(f"https://cdn.cboe.com/resources/options/volume_and_call_put_ratios/{f}.csv")
    except Exception as e:
        print(f"⚠️  put/call {nama}: {type(e).__name__}")
        continue
    baris = teks.splitlines()
    mulai = next(i for i, b in enumerate(baris) if b.upper().startswith("DATE"))       # buang kalimat penafian di atas
    d = pd.read_csv(io.StringIO("\n".join(baris[mulai:])), skipinitialspace=True)
    d.columns = [c.strip().lower().replace(" ", "_").replace("/", "_") for c in d.columns]
    d["tanggal"] = pd.to_datetime(d["date"], format="%m/%d/%Y", errors="coerce")
    d = d.drop(columns=["date"]).dropna(subset=["tanggal"])
    for c in d.columns:
        if c != "tanggal":
            d[c] = pd.to_numeric(d[c], errors="coerce")
    d.insert(0, "jenis", nama)
    pc.append(d)
    print(f"✅ put/call {nama:8}: {len(d):5} hari {d['tanggal'].min():%Y-%m} s/d {d['tanggal'].max():%Y-%m}")
if TES:
    print("🧪 mode tes: tidak disimpan")
    sys.exit()
if gagal and len(gagal) > 5:
    print(f"❌ terlalu banyak gagal: {gagal}")
    sys.exit(1)
folder = Path("data/raw/cboe")
folder.mkdir(parents=True, exist_ok=True)
df.to_parquet(folder / "indeks.parquet", index=False)
if pc:
    p = pd.concat(pc, ignore_index=True)
    p["jenis"] = p["jenis"].astype("string")
    p["tanggal"] = p["tanggal"].astype("datetime64[ns]")
    p.to_parquet(folder / "putcall_arsip.parquet", index=False)
print(f"💾 {folder}/indeks.parquet" + (" + putcall_arsip.parquet" if pc else ""))
