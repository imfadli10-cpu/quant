"""
IMF IMTS (dulu DOTS: Direction of Trade Statistics) -> PERDAGANGAN BARANG BULANAN Indonesia dgn SETIAP negara mitra, DUA SISI, sejak 1960
Sumber: API SDMX resmi IMF (api.imf.org/external/sdmx/2.1, tanpa kunci; robots.txt server API tidak tersedia/502).
  (a) laporan INDONESIA:  kunci 'IDN...M'  -> ekspor FOB, impor CIF/FOB, neraca, per mitra (243 mitra)
  (b) laporan MITRA (data CERMIN): '..IDN.M' -> mis. bea cukai CHINA mencatat impor dari Indonesia (236 pelapor) = sumber independen dari BPS.
Indikator: XG_FOB_USD (ekspor), MG_CIF_USD / MG_FOB_USD (impor), TBG_USD (neraca); USD (kolom SCALE = pangkat 10 tampilan, nilai OBS_VALUE = USD penuh).
TELAT ~4 bulan (27 Nov 2026: data terakhir 2026-M07) -> kalah segar dari BPS; nilai utamanya = histori panjang & sisi mitra (cermin).
IMF merevisi & menimpa -> simpan SETIAP versi baru (sidik sha256 isi) = point-in-time MULAI 27 Nov 2026 (pola kumpul_usda_psd.py).
SIMPAN (langsung ke gudang, satu commit atomik):
  raw/imf_dagang/versi/<tgl ambil>__<sha8>.parquet  pelapor, indikator, mitra, bulan (datetime awal bulan), nilai_usd, update_date (teks IMF)
  raw/imf_dagang/indeks.parquet                    sha256, baris, bulan_terakhir, waktu_ambil, jalur
Unduhan ~2 x 185 MB CSV (~1,5 menit). Gagal membaca indeks yang ADA -> berhenti.
Cara pakai: python kumpul_imf_dagang.py  |  --tes (unduh & ringkas, tanpa simpan)
"""
import hashlib
import io
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

DASAR = "https://api.imf.org/external/sdmx/2.1/data/IMF.STA,IMTS/"
H = {"User-Agent": "quant-data-collector/1.0 (personal research project)", "Accept": "application/vnd.sdmx.data+csv;version=1.0.0"}
REPO = "fadli-sparks/quant-data"
TES = "--tes" in sys.argv
SEKARANG = datetime.now(timezone.utc)
KOLOM = ["COUNTRY", "INDICATOR", "COUNTERPART_COUNTRY", "TIME_PERIOD", "OBS_VALUE", "UPDATE_DATE"]
KOLOM_INDEKS = ["sha256", "baris", "bulan_terakhir", "waktu_ambil", "jalur"]


def unduh(kunci):
    for coba in range(4):
        try:
            r = requests.get(DASAR + kunci, headers=H, timeout=(30, 900))
            if r.status_code == 200 and len(r.content) > 1_000_000:
                return pd.read_csv(io.BytesIO(r.content), dtype=str, keep_default_na=False, usecols=KOLOM)
            print(f"   ⚠️ {kunci}: HTTP {r.status_code}, {len(r.content):,} byte")
        except requests.RequestException as e:
            print(f"   🔌 {kunci}: {type(e).__name__}")
        time.sleep(30 * (coba + 1))
    return None


bag = []
for kunci in ("IDN...M", "..IDN.M"):
    t0 = time.time()
    x = unduh(kunci)
    if x is None:
        print(f"❌ {kunci} gagal diunduh")
        sys.exit(1)
    print(f"   {kunci}: {len(x):,} baris ({time.time() - t0:.0f} dtk)")
    bag.append(x)
d = pd.concat(bag, ignore_index=True)
d = d[(d["COUNTRY"] != "") & (d["TIME_PERIOD"] != "")]
d = d.drop_duplicates(["COUNTRY", "INDICATOR", "COUNTERPART_COUNTRY", "TIME_PERIOD"], keep="last")
d = pd.DataFrame({"pelapor": d["COUNTRY"], "indikator": d["INDICATOR"], "mitra": d["COUNTERPART_COUNTRY"],
                  "bulan": pd.to_datetime(d["TIME_PERIOD"].str.replace("-M", "-", regex=False) + "-01", errors="coerce"),
                  "nilai_usd": pd.to_numeric(d["OBS_VALUE"], errors="coerce"), "update_date": d["UPDATE_DATE"]})
d = d.dropna(subset=["bulan"]).sort_values(["pelapor", "mitra", "indikator", "bulan"]).reset_index(drop=True)
d["bulan"] = d["bulan"].astype("datetime64[ns]")
for k in ("pelapor", "indikator", "mitra", "update_date"):
    d[k] = d[k].astype("string")
sidik = hashlib.sha256(pd.util.hash_pandas_object(d.drop(columns="update_date"), index=False).values.tobytes()).hexdigest()
cek = d[(d["pelapor"] == "IDN") & (d["mitra"] == "CHN") & (d["indikator"] == "XG_FOB_USD")].tail(1)
cermin = d[(d["pelapor"] == "CHN") & (d["mitra"] == "IDN") & (d["indikator"] == "MG_CIF_USD")].tail(1)
print(f"✅ {len(d):,} baris; pelapor {d['pelapor'].nunique()}, mitra {d['mitra'].nunique()}; {d['bulan'].min():%Y-%m}..{d['bulan'].max():%Y-%m}")
if len(cek) and len(cermin):
    print(f"   ekspor IDN->CHN {cek['bulan'].iloc[0]:%Y-%m} US${cek['nilai_usd'].iloc[0] / 1e9:.2f} M | cermin: impor CHN dari IDN "
          f"{cermin['bulan'].iloc[0]:%Y-%m} US${cermin['nilai_usd'].iloc[0] / 1e9:.2f} M")
if len(d) < 300_000 or cek.empty:
    print("❌ isi terlalu sedikit -> curigai format/API berubah")
    sys.exit(1)
if TES:
    print("🧪 mode tes: tidak disimpan")
    sys.exit()

from huggingface_hub import CommitOperationAdd, HfApi, hf_hub_download
token = os.environ.get("HF_TOKEN") or Path("kunci_hf.txt").read_text().strip()
api = HfApi(token=token)
try:
    lama = pd.read_parquet(hf_hub_download(REPO, "raw/imf_dagang/indeks.parquet", repo_type="dataset", token=token))
except Exception as e:
    if "404" not in str(e) and "EntryNotFound" not in type(e).__name__:
        raise                                        # indeks ADA tapi gagal dibaca -> berhenti
    lama = pd.DataFrame(columns=KOLOM_INDEKS)
if len(lama) and sidik in set(lama["sha256"]):
    print(f"✅ isi sama dgn versi tersimpan ({len(lama)} versi) -> tidak ada yang diunggah")
    sys.exit()
jalur = f"raw/imf_dagang/versi/{SEKARANG:%Y-%m-%d}__{sidik[:8]}.parquet"
lokal = Path("data") / jalur
lokal.parent.mkdir(parents=True, exist_ok=True)
d.to_parquet(lokal, index=False)
print(f"💾 {lokal} ({lokal.stat().st_size / 1e6:.1f} MB)")
baru = pd.DataFrame([{"sha256": sidik, "baris": len(d), "bulan_terakhir": d["bulan"].max(),
                      "waktu_ambil": pd.Timestamp(SEKARANG).tz_localize(None).floor("s"), "jalur": jalur}])
indeks = pd.concat([lama, baru], ignore_index=True) if len(lama) else baru
for k in ("bulan_terakhir", "waktu_ambil"):
    indeks[k] = pd.to_datetime(indeks[k]).astype("datetime64[ns]")
indeks["baris"] = indeks["baris"].astype("int64")
for k in ("sha256", "jalur"):
    indeks[k] = indeks[k].astype("string")
Path("data/raw/imf_dagang").mkdir(parents=True, exist_ok=True)
indeks.to_parquet("data/raw/imf_dagang/indeks.parquet", index=False)
ops = [CommitOperationAdd(path_in_repo=jalur, path_or_fileobj=str(lokal)),
       CommitOperationAdd(path_in_repo="raw/imf_dagang/indeks.parquet", path_or_fileobj="data/raw/imf_dagang/indeks.parquet")]
for percobaan in range(4):
    try:
        api.create_commit(repo_id=REPO, repo_type="dataset", operations=ops, commit_message=f"IMF IMTS versi {SEKARANG:%Y-%m-%d}")
        break
    except Exception as e:
        if percobaan == 3:
            raise
        print(f"   ⚠️ upload gagal ({type(e).__name__}), coba lagi")
        time.sleep(60 * (percobaan + 1))
print(f"☁️  indeks {len(indeks)} versi di gudang")
