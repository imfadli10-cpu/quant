"""
AKTIVITAS PELABUHAN & JALUR PELAYARAN HARIAN dari IMF PortWatch (sinyal kapal AIS; data terbuka IMF + UN Global Platform).

Kenapa: perdagangan fisik nyata, harian, sebelum data BPS/bea cukai terbit (BPS ekspor-impor telat ~1 bulan).
Contoh: kapal curah kering di Balikpapan/Samarinda/Tanjung Redeb (batu bara), Morowali/Kendari (nikel), Dumai/Belawan
(sawit), kontainer di Tanjung Priok/Surabaya (konsumsi & manufaktur), lalu lintas Selat Malaka. SEMUA pelabuhan dunia
(~1.600) disimpan (prinsip: data sebanyak mungkin). Atribusi: IMF PortWatch.

Sumber (API resmi; portal portwatch.imf.org tombol "ACCESS API"; ArcGIS FeatureServer, maks 1.000 baris per permintaan):
  Daily_Ports_Data       : per pelabuhan per hari: portcalls (jumlah kapal singgah) per jenis kapal + perkiraan
                           import/export (ton metrik) per jenis. Sejak 2019-01-01, terlambat ~1 minggu.
  Daily_Chokepoints_Data : per jalur sempit (Selat Malaka, Sunda, Lombok, Suez, Panama, Hormuz, ...): jumlah kapal
                           transit & kapasitas per jenis.
Isi:
  data/raw/harian/pelabuhan/<tanggal UTC>.parquet       mode harian: 30 hari terakhir semua pelabuhan
  data/raw/harian/jalur_kapal/<tanggal UTC>.parquet     mode harian: 30 hari terakhir semua jalur
  data/raw/histori/pelabuhan/<tahun>.parquet            --histori (upload tiap tahun, bisa dilanjutkan)
  data/raw/histori/jalur_kapal/semua.parquet            --histori
Cara pakai:  python kumpul_pelabuhan.py | --tes | --histori
"""
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

B = "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/ArcGIS/rest/services"
HEADER = {"User-Agent": "quant-data-collector/1.0 (personal research project)"}
HARI_INI = datetime.now(timezone.utc).date()
TES, HISTORI = "--tes" in sys.argv, "--histori" in sys.argv


def minta(layanan, params):
    for percobaan in range(6):
        try:
            r = requests.get(f"{B}/{layanan}/FeatureServer/0/query", params={"f": "json", **params},
                             headers=HEADER, timeout=(15, 180))
            r.raise_for_status()
            j = r.json()
            if "error" in j:
                raise RuntimeError(str(j["error"])[:200])
            return j
        except (requests.RequestException, RuntimeError, ValueError) as e:
            if percobaan == 5:
                raise
            print(f"   ⚠️  {layanan}: {type(e).__name__}: {str(e)[:100]}, coba lagi")
            time.sleep(10 * (percobaan + 1))


def ambil(layanan, mulai, akhir, per_halaman):
    """Semua baris dengan mulai <= date <= akhir, halaman demi halaman (urut ObjectId)."""
    where = f"date >= DATE '{mulai}' AND date <= DATE '{akhir}'"
    bag, offset = [], 0
    while True:
        j = minta(layanan, {"where": where, "outFields": "*", "returnGeometry": "false", "orderByFields": "ObjectId",
                            "resultOffset": offset, "resultRecordCount": per_halaman})
        fitur = j.get("features", [])
        bag += [f["attributes"] for f in fitur]
        if len(fitur) < per_halaman and not j.get("exceededTransferLimit"):
            break
        offset += len(fitur)
        if TES and offset >= 2000:
            break
        time.sleep(0.2)
    d = pd.DataFrame(bag)
    if d.empty:
        return d
    d = d.drop(columns=[k for k in ["ObjectId", "year", "month", "day"] if k in d])
    d["date"] = pd.to_datetime(d["date"]).astype("datetime64[ns]")
    for k in d.columns:
        if d[k].dtype == object:
            d[k] = d[k].astype("string")
    return d.drop_duplicates(["date", "portid"]).sort_values(["date", "portid"]).reset_index(drop=True)


def ringkas(nama, d):
    if d.empty:
        return f"{nama}: 0 baris"
    idn = d[d["ISO3"] == "IDN"] if "ISO3" in d else d.iloc[0:0]
    return (f"{nama}: {len(d):,} baris, {d['portid'].nunique():,} lokasi, {d['date'].min():%Y-%m-%d} s/d "
            f"{d['date'].max():%Y-%m-%d}" + (f" | Indonesia {idn['portid'].nunique()} pelabuhan" if len(idn) else ""))


if not HISTORI:
    mulai = (HARI_INI - timedelta(days=30)).isoformat()
    pel = ambil("Daily_Ports_Data", mulai, HARI_INI.isoformat(), 1000)
    jal = ambil("Daily_Chokepoints_Data", mulai, HARI_INI.isoformat(), 10000)
    print("✅ " + ringkas("pelabuhan", pel))
    print("✅ " + ringkas("jalur_kapal", jal))
    if TES:
        prio = pel[pel["portname"].isin(["Tanjung Priok", "Balikpapan", "Indonesia Morowali Industrial Park"])]
        print(prio.groupby("portname")[["portcalls", "import", "export"]].mean().round(1).to_string())
        print(jal.groupby("portname")["n_total"].mean().round(1).sort_values(ascending=False).head(8).to_string())
        print("🧪 mode tes: tidak disimpan")
        sys.exit()
    if len(pel) < 10000 or jal.empty:
        print("❌ data terlalu sedikit -> tidak disimpan")
        sys.exit(1)
    for nama, d in [("pelabuhan", pel), ("jalur_kapal", jal)]:
        f = Path(f"data/raw/harian/{nama}")
        f.mkdir(parents=True, exist_ok=True)
        d.to_parquet(f / f"{HARI_INI.isoformat()}.parquet", index=False)
    print("💾 data/raw/harian/pelabuhan & jalur_kapal")
    sys.exit()

# ===== Histori =====
from huggingface_hub import HfApi
api_hf = HfApi(token=os.environ.get("HF_TOKEN") or Path("kunci_hf.txt").read_text().strip())
REPO = "fadli-sparks/quant-data"
sudah = set(api_hf.list_repo_files(REPO, repo_type="dataset"))


def unggah(f, tujuan):
    for _ in range(6):
        try:
            api_hf.upload_file(path_or_fileobj=str(f), path_in_repo=tujuan, repo_id=REPO, repo_type="dataset",
                               commit_message=f"Upload {tujuan}")
            return
        except Exception as e:
            print(f"   ⚠️  upload {tujuan}: {type(e).__name__}, tunggu 2 menit")
            time.sleep(120)
    raise RuntimeError(f"upload {tujuan} gagal terus")


folder = Path("data/raw/histori/pelabuhan")
folder.mkdir(parents=True, exist_ok=True)
for th in range(2019, HARI_INI.year + 1):
    tujuan = f"raw/histori/pelabuhan/{th}.parquet"
    if tujuan in sudah and th < HARI_INI.year:
        continue
    t0 = time.time()
    bag = []
    for bl in range(1, 13):                       # per bulan supaya tiap kueri tidak terlalu besar
        awal = pd.Timestamp(th, bl, 1)
        if awal.date() > HARI_INI:
            break
        akhir = (awal + pd.offsets.MonthEnd(0)).date()
        bag.append(ambil("Daily_Ports_Data", awal.date().isoformat(), akhir.isoformat(), 1000))
    d = pd.concat([b for b in bag if not b.empty], ignore_index=True)
    f = folder / f"{th}.parquet"
    d.to_parquet(f, index=False)
    unggah(f, tujuan)
    print(f"   💾☁️  {ringkas(f'pelabuhan {th}', d)} ({time.time() - t0:.0f} detik)")

jal = ambil("Daily_Chokepoints_Data", "2019-01-01", HARI_INI.isoformat(), 10000)
f = Path("data/raw/histori/jalur_kapal")
f.mkdir(parents=True, exist_ok=True)
jal.to_parquet(f / "semua.parquet", index=False)
unggah(f / "semua.parquet", "raw/histori/jalur_kapal/semua.parquet")
print(f"   💾☁️  {ringkas('jalur_kapal', jal)}")
print("✅ histori selesai")
