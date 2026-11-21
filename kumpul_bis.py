"""
BIS (Bank for International Settlements) - unduhan massal resmi (https://data.bis.org/static/bulk/<DATASET>_csv_flat.zip;
robots.txt data.bis.org: Allow /). Semua negara (termasuk Indonesia), DITIMPA tiap minggu.

Dataset:
  WS_GLI          Global Liquidity Indicators: kredit dolar/euro/yen lintas batas ke peminjam tiap negara (likuiditas global)
  WS_CREDIT_GAP   celah kredit terhadap PDB (peringatan dini krisis perbankan)
  WS_DSR          rasio beban utang (debt service ratio) sektor swasta
  WS_TC           total kredit ke sektor non-keuangan
  WS_CBPOL        suku bunga kebijakan bank sentral (HARIAN & bulanan)
  WS_CBTA         total aset bank sentral
  WS_EER          nilai tukar efektif nominal & riil (harian/bulanan)
  WS_XRU          kurs terhadap USD (harian/bulanan/tahunan)
  WS_SPP          harga properti residensial
  WS_LONG_CPI     indeks harga konsumen jangka panjang
  (WS_LBS_D_PUB 365 MB & WS_DEBT_SEC2_PUB 147 MB SENGAJA belum diambil: sangat besar; tambahkan kalau riset butuh.)
Isi: data/raw/bis/<DATASET>.parquet; nama kolom = kode dimensi (huruf kecil, tanpa label), nilai sel 'KODE: Label' dipisah:
  kolom <dim> = kode, <dim>_label = label. obs_value -> angka.
Cara pakai: python kumpul_bis.py | --tes (2 dataset kecil, tanpa simpan)
"""
import io
import sys
import time
import zipfile
from pathlib import Path

import pandas as pd
import requests

H = {"User-Agent": "quant-data-collector/1.0 (personal research project)"}
URL = "https://data.bis.org/static/bulk/{}_csv_flat.zip"
DATASET = ["WS_GLI", "WS_CREDIT_GAP", "WS_DSR", "WS_TC", "WS_CBPOL", "WS_CBTA", "WS_EER", "WS_XRU", "WS_SPP", "WS_LONG_CPI"]
TES = "--tes" in sys.argv
if TES:
    DATASET = ["WS_GLI", "WS_DSR"]
BUANG = {"structure", "structure_id", "action"}


def ambil(url):
    for percobaan in range(4):
        try:
            r = requests.get(url, headers=H, timeout=(20, 600))
            r.raise_for_status()
            return r.content
        except requests.RequestException:
            if percobaan == 3:
                raise
            time.sleep(20 * (percobaan + 1))


def rapikan(d):
    keluar = {}
    for k in d.columns:
        kode = k.split(":")[0].strip().lower()
        if kode in BUANG:
            continue
        isi = d[k]
        if kode in ("obs_value", "obs_pre_break"):
            keluar[kode] = pd.to_numeric(isi.replace("", None), errors="coerce").astype("float64")
        elif kode in ("time_period", "title", "unit_mult", "decimals"):
            keluar[kode] = isi.astype("string")
        else:
            unik = pd.Series(isi.unique())                       # pecah 'KODE: Label' hanya untuk nilai unik (jauh lebih cepat)
            pecah = unik.str.split(": ", n=1, expand=True)
            peta_kode = dict(zip(unik, pecah[0]))
            keluar[kode] = isi.map(peta_kode).astype("string")
            if pecah.shape[1] > 1:
                keluar[kode + "_label"] = isi.map(dict(zip(unik, pecah[1]))).astype("string")
    return pd.DataFrame(keluar)


folder = Path("data/raw/bis")
gagal = []
for ds in DATASET:
    t0 = time.time()
    try:
        z = zipfile.ZipFile(io.BytesIO(ambil(URL.format(ds))))
        d = pd.read_csv(z.open(z.namelist()[0]), dtype=str, keep_default_na=False, low_memory=False)
        d = rapikan(d)
    except Exception as e:
        print(f"⚠️  {ds}: {type(e).__name__}: {str(e)[:120]}")
        gagal.append(ds)
        continue
    negara = [k for k in d.columns if k.endswith("_cty") or k in ("ref_area", "borrowers_cty")]
    idn = sum((d[k] == "ID").sum() for k in negara)
    print(f"✅ {ds:14} {len(d):10,} baris | periode {d['time_period'].min()} s/d {d['time_period'].max()} | "
          f"baris Indonesia {idn:,} ({time.time() - t0:.0f} dtk)")
    if not TES:
        folder.mkdir(parents=True, exist_ok=True)
        d.to_parquet(folder / f"{ds}.parquet", index=False)
if TES:
    print("🧪 mode tes: tidak disimpan")
elif gagal and len(gagal) > 3:
    print(f"❌ terlalu banyak gagal: {gagal}")
    sys.exit(1)
