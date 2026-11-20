"""
Judul berita keuangan/ekonomi Indonesia dari feed RSS resmi media (data "hanya ke depan": feed hanya memuat berita
terbaru; yang tidak difoto hilang). Dijalankan tiap 4 jam (workflow berita.yml) karena Kontan hanya menyimpan ~7 jam.

HANYA feed yang robots.txt-nya MENGIZINKAN program (dicek 20 Nov 2026):
  kontan_investasi, antara_bursa, antara_ekonomi, tempo_bisnis, liputan6_bisnis
  TIDAK dipakai: CNBC Indonesia & IDX Channel (robots.txt melarang), Bisnis.com (menolak 403). JANGAN ditembus.

Isi: data/raw/harian/berita/<tanggal UTC>.parquet (file hari itu DIGABUNG dengan foto sebelumnya di hari yang sama,
  dobel dibuang menurut tautan). Kolom: sumber, judul, ringkasan (tanpa HTML, maks 500 huruf), tautan, waktu_terbit (UTC),
  waktu_ambil (UTC), kode_disebut (kode saham IDX yang muncul di judul/ringkasan, dipisah koma).
Pengaman: kalau file hari ini SUDAH ada di gudang tapi gagal dibaca -> berhenti (jangan menimpa).
Cara pakai: python kumpul_berita.py [--tes]
"""
import html
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import pandas as pd
import requests

REPO = "fadli-sparks/quant-data"
UA = {"User-Agent": "quant-data-collector/1.0 (personal research project)"}
FEED = {"kontan_investasi": "https://investasi.kontan.co.id/rss",
        "antara_bursa": "https://www.antaranews.com/rss/ekonomi-bursa.xml",
        "antara_ekonomi": "https://www.antaranews.com/rss/ekonomi.xml",
        "tempo_bisnis": "https://rss.tempo.co/bisnis",
        "liputan6_bisnis": "https://feed.liputan6.com/rss/bisnis"}
SEKARANG = datetime.now(timezone.utc).replace(tzinfo=None)
TES = "--tes" in sys.argv


def bersih(teks):
    teks = html.unescape(re.sub(r"<[^>]+>", " ", teks or ""))
    return re.sub(r"\s+", " ", teks).strip()


def waktu(s):
    try:
        t = parsedate_to_datetime(s)
        return (t.astimezone(timezone.utc).replace(tzinfo=None) if t.tzinfo else t)
    except (TypeError, ValueError):
        return pd.NaT


baris, gagal, status = [], [], []
for sumber, url in FEED.items():
    kode_http, alasan = None, ""
    for percobaan in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=30)
            kode_http = r.status_code
            r.raise_for_status()
            item = ET.fromstring(r.content).findall(".//item")
            alasan = ""
            break
        except Exception as e:
            item = None
            alasan = f"{type(e).__name__}: {str(e)[:120]}"
            time.sleep(5 * (percobaan + 1))
    status.append({"waktu_ambil": SEKARANG, "sumber": sumber, "kode_http": kode_http,
                   "jumlah": len(item) if item is not None else 0, "alasan": alasan})
    if item is None:
        gagal.append(sumber)
        print(f"   ⚠️  {sumber}: HTTP {kode_http} | {alasan}")
        continue
    for i in item:
        baris.append({"sumber": sumber, "judul": bersih(i.findtext("title")),
                      "ringkasan": bersih(i.findtext("description"))[:500], "tautan": (i.findtext("link") or "").strip(),
                      "waktu_terbit": waktu(i.findtext("pubDate")), "waktu_ambil": SEKARANG})
    time.sleep(1)
baru = pd.DataFrame(baris)
if baru.empty:
    print(f"❌ berita: tidak ada feed yang berhasil ({gagal})")
    sys.exit(1)

# Kode saham IDX yang disebut (4 huruf kapital yang cocok dengan daftar kode)
try:
    from daftar_saham import kode_idx
    kode = set(kode_idx(akhiran="", termasuk_etf=True))
except Exception as e:
    print(f"⚠️  daftar kode tidak terbaca ({type(e).__name__}), kode_disebut dikosongkan")
    kode = set()
UMUM = {"YANG", "DARI", "AKAN", "PADA", "OJK", "BUMN", "IHSG", "USD"}     # kata umum huruf kapital yang bukan saham
def sebut(teks):
    return ",".join(sorted({k for k in re.findall(r"\b[A-Z]{4}\b", teks) if k in kode and k not in UMUM}))
baru["kode_disebut"] = (baru["judul"] + " " + baru["ringkasan"]).map(sebut)
for k in ["sumber", "judul", "ringkasan", "tautan", "kode_disebut"]:
    baru[k] = baru[k].astype("string")
for k in ["waktu_terbit", "waktu_ambil"]:
    baru[k] = pd.to_datetime(baru[k]).astype("datetime64[ns]")
print(f"📥 {len(baru)} berita dari {baru['sumber'].nunique()} sumber (gagal: {gagal or '-'}) | "
      f"menyebut kode saham: {(baru['kode_disebut'] != '').sum()}")
if TES:
    print(baru.groupby("sumber").agg(n=("judul", "size"), terbaru=("waktu_terbit", "max")).to_string())
    print(baru.loc[baru["kode_disebut"] != "", ["kode_disebut", "judul"]].head(8).to_string())
    sys.exit()

# Gabung dengan foto sebelumnya HARI INI (file harian = tanggal UTC)
nama = f"{SEKARANG.date().isoformat()}.parquet"
lama = None
from huggingface_hub import HfApi, hf_hub_download
token = os.environ.get("HF_TOKEN") or Path("kunci_hf.txt").read_text().strip()
api = HfApi(token=token)
jalur = f"raw/harian/berita/{nama}"
if api.file_exists(REPO, jalur, repo_type="dataset"):
    for percobaan in range(3):
        try:
            lama = pd.read_parquet(hf_hub_download(REPO, jalur, repo_type="dataset", token=token, force_download=True))
            break
        except Exception as e:
            time.sleep(10)
    if lama is None:
        print("❌ file hari ini ada di gudang tapi gagal dibaca -> berhenti supaya tidak tertimpa")
        sys.exit(1)
gabung = pd.concat([lama, baru], ignore_index=True) if lama is not None else baru
gabung = gabung.sort_values("waktu_ambil").drop_duplicates("tautan", keep="first").reset_index(drop=True)
folder = Path("data/raw/harian/berita")
folder.mkdir(parents=True, exist_ok=True)
gabung.to_parquet(folder / nama, index=False)
# Catatan status tiap sumber per jalan (supaya kegagalan, mis. diblokir dari server, bisa dicek tanpa membuka log)
f_status = folder / f"status_{SEKARANG.date().isoformat()}.parquet"
st = pd.DataFrame(status)
st["waktu_ambil"] = pd.to_datetime(st["waktu_ambil"]).astype("datetime64[ns]")
jalur_status = f"raw/harian/berita/{f_status.name}"
if api.file_exists(REPO, jalur_status, repo_type="dataset"):
    try:
        st = pd.concat([pd.read_parquet(hf_hub_download(REPO, jalur_status, repo_type="dataset", token=token,
                                                        force_download=True)), st], ignore_index=True)
    except Exception as e:
        print(f"⚠️  status lama tidak terbaca ({type(e).__name__}); hanya status jalan ini yang disimpan")
st.to_parquet(f_status, index=False)
print(f"✅ berita: {len(gabung)} berita unik hari ini ({len(gabung) - (len(lama) if lama is not None else 0)} baru) -> {folder / nama}")
