"""
ALFRED (arsip vintage FRED, St. Louis Fed): SEMUA versi angka setiap seri makro di ambil_makro.py -> angka sebagaimana DIKETAHUI pada
tanggal tertentu (point-in-time), termasuk rilis pertama sebelum revisi. + JADWAL RILIS (tanggal terbit historis & yang dijadwalkan).
Kenapa: riset makro yang memakai angka TERREVISI = kebocoran halus (pasar dulu belum tahu revisinya); 'kejutan rilis' butuh rilis pertama.
Kunci FRED yang sama (FRED_API_KEY / kunci_fred.txt). ~200 seri + jadwal, ~5-10 menit, DITIMPA tiap jalan (arsip ALFRED sendiri kumulatif).

  python kumpul_alfred.py        -> data/raw/alfred/vintage/<KODE>.parquet (tanggal, berlaku_mulai, berlaku_sampai [NaT = masih berlaku], nilai)
                                    data/raw/alfred/seri_rilis.parquet (kode -> release_id, nama rilis)
                                    data/raw/alfred/jadwal_rilis.parquet (release_id, nama_rilis, tanggal_rilis)
  python kumpul_alfred.py --tes  -> 3 seri, tanpa simpan
Cara pakai riset: nilai yang diketahui pada tanggal D = baris dengan berlaku_mulai <= D dan (berlaku_sampai >= D atau NaT).
"""
import os
import sys
import time
from pathlib import Path

import pandas as pd
import requests

KUNCI = os.environ.get("FRED_API_KEY") or Path("kunci_fred.txt").read_text().strip()
B = "https://api.stlouisfed.org/fred/"
TES = "--tes" in sys.argv
OUT = Path("data/raw/alfred")

kode_makro = Path("ambil_makro.py").read_text(encoding="utf-8").split("folder = Path(")[0]
g = {}
exec(compile(kode_makro.replace('KUNCI = os.environ.get("FRED_API_KEY") or Path("kunci_fred.txt").read_text().strip()', ""), "ambil_makro_seri", "exec"), g)
TAMBAHAN = ["GDPC1", "GDP", "PCEPI", "PCE", "PPIFIS", "CES0500000003", "CIVPART", "DGORDER", "UMCSENT", "TCU", "BUSLOANS", "TOTALSL"]
SERI = list(dict.fromkeys(list(g["SERI"]) + TAMBAHAN))
if TES:
    SERI = ["PAYEMS", "IDNCPIALLMINMEI", "DGS10"]


def minta(ujung, **p):
    p.update({"api_key": KUNCI, "file_type": "json"})
    for coba in range(5):
        try:
            r = requests.get(B + ujung, params=p, timeout=120)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                time.sleep(30)
                continue
            if r.status_code == 400 and "maximum number of vintage dates" in r.text:
                return {"_terlalu_banyak": True}
            if 400 <= r.status_code < 500:
                print(f"   ⚠️ {ujung} {p.get('series_id', p.get('release_id'))}: HTTP {r.status_code}")
                return None
        except Exception as e:
            print(f"   🔌 {type(e).__name__}")
        time.sleep(5 * (coba + 1))
    return None


def semua_halaman(ujung, kunci, batas, **p):
    hasil, offset = [], 0
    while True:
        j = minta(ujung, limit=batas, offset=offset, **p)
        if j is None or j.get("_terlalu_banyak"):
            return j
        hasil += j[kunci]
        offset += batas
        if offset >= int(j.get("count", 0)):
            return hasil
        time.sleep(0.6)


def tgl(x):
    return pd.to_datetime(x.where(~x.isin(["9999-12-31", "1776-07-04"])), errors="coerce").astype("datetime64[ns]")


(OUT / "vintage").mkdir(parents=True, exist_ok=True)
t0, rilis, gagal, lewati, total = time.time(), [], [], [], 0
for k in SERI:
    obs = semua_halaman("series/observations", "observations", 100000, series_id=k,
                        realtime_start="1776-07-04", realtime_end="9999-12-31")
    if isinstance(obs, dict):              # seri harian > 2.000 vintage (data pasar, praktis tidak direvisi) -> dilewati
        lewati.append(k)
        continue
    if not obs:
        gagal.append(k)
        continue
    d = pd.DataFrame(obs)
    d = pd.DataFrame({"tanggal": tgl(d["date"]), "berlaku_mulai": tgl(d["realtime_start"]), "berlaku_sampai": tgl(d["realtime_end"]),
                      "nilai": pd.to_numeric(d["value"], errors="coerce")})
    total += len(d)
    r = minta("series/release", series_id=k)
    if r and r.get("releases"):
        rilis.append({"kode": k, "release_id": int(r["releases"][0]["id"]), "nama_rilis": r["releases"][0]["name"]})
    n_versi = d["berlaku_mulai"].nunique()
    if TES:
        print(f"   {k}: {len(d):,} baris, {n_versi} vintage; rilis {rilis[-1]['nama_rilis'] if rilis else '-'}")
        print(d.tail(3).to_string())
    else:
        d.to_parquet(OUT / "vintage" / f"{k}.parquet", index=False)
    time.sleep(0.6)
print(f"✅ vintage: {len(SERI) - len(gagal) - len(lewati)}/{len(SERI)} seri, {total:,} baris ({time.time() - t0:.0f} dtk); "
      f"dilewati (harian > 2.000 vintage) {len(lewati)}; gagal: {gagal[:10]}")
sr = pd.DataFrame(rilis)
jadwal = []
for rid, nama in sr.drop_duplicates("release_id")[["release_id", "nama_rilis"]].itertuples(index=False):
    dt = semua_halaman("release/dates", "release_dates", 10000, release_id=rid, realtime_start="1776-07-04",
                       realtime_end="9999-12-31", include_release_dates_with_no_data="true", sort_order="asc")
    if dt:
        jadwal += [{"release_id": rid, "nama_rilis": nama, "tanggal_rilis": x["date"]} for x in dt]
    time.sleep(0.6)
jd = pd.DataFrame(jadwal)
jd["tanggal_rilis"] = pd.to_datetime(jd["tanggal_rilis"]).astype("datetime64[ns]")
print(f"✅ jadwal: {jd['release_id'].nunique()} rilis, {len(jd):,} tanggal, s/d {jd['tanggal_rilis'].max():%Y-%m-%d} "
      f"({(jd['tanggal_rilis'] > pd.Timestamp.now()).sum()} terjadwal ke depan)")
if TES:
    print(jd.tail(5).to_string())
    sys.exit(0)
if len(gagal) > 0.2 * len(SERI):
    print("❌ terlalu banyak seri gagal")
    sys.exit(1)
sr.to_parquet(OUT / "seri_rilis.parquet", index=False)
jd.to_parquet(OUT / "jadwal_rilis.parquet", index=False)
print(f"💾 {OUT}")
