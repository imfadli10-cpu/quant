"""
IPO SAHAM INDONESIA dari e-IPO (e-ipo.co.id, sistem penawaran umum elektronik resmi milik BEI; robots.txt: Allow /).
Hanya halaman PUBLIK (tanpa login): daftar IPO (/id/ipo/index?page=N) & halaman detail tiap IPO.

Isi per IPO: kode, nama, status (Pre-Effective/Book Building/Waiting For Offering/Offering/Allotment/Closed/Postponed/
Canceled), syariah, sektor/subsektor, saham ditawarkan (lembar & lot), % dari total saham dicatatkan, partisipan admin,
PENJAMIN EMISI, jadwal (book building + rentang harga, penawaran umum + harga final, penjatahan, distribusi, pencatatan).
Kegunaan: kalender IPO (pasokan saham baru menyedot dana ritel), reputasi penjamin emisi vs kinerja hari pertama (ARA),
ukuran IPO vs return. Harga setelah listing ada di data harga harian (kode emiten).

Hasil:
  data/raw/ipo/daftar/<tanggal UTC>.parquet   foto kartu daftar IPO hari ini (status berubah dari hari ke hari)
  data/raw/ipo/detail.parquet                 1 baris per IPO (DITIMPA; detail terbaru) + waktu_ambil
Cara pakai:
  python kumpul_ipo.py            -> harian: semua halaman daftar + detail IPO yang BELUM selesai/batal (dan yang baru)
  python kumpul_ipo.py --histori  -> detail SEMUA IPO (sekali; ~5-8 menit)
  python kumpul_ipo.py --tes      -> 1 halaman daftar + 2 detail, tanpa simpan
"""
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

DASAR = "https://e-ipo.co.id"
HEADER = {"User-Agent": "quant-data-collector/1.0 (personal research project)"}
SEKARANG = datetime.now(timezone.utc)
TES, HISTORI = "--tes" in sys.argv, "--histori" in sys.argv
JEDA = 1.5
SELESAI = {"Closed", "Canceled"}
BULAN = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "mei": 5, "jun": 6, "jul": 7, "aug": 8, "agu": 8, "agt": 8,
         "sep": 9, "oct": 10, "okt": 10, "nov": 11, "dec": 12, "des": 12}


def ambil(url):
    for percobaan in range(4):
        try:
            r = requests.get(url, headers=HEADER, timeout=(15, 60))
            r.raise_for_status()
            if "<title>Login | e-IPO</title>" in r.text:
                raise RuntimeError("halaman meminta login (bukan publik) -> tidak diambil")
            return r.text
        except requests.RequestException as e:
            if percobaan == 3:
                raise
            print(f"   ⚠️  {type(e).__name__}, coba lagi")
            time.sleep(10 * (percobaan + 1))


def teks_pipa(html):
    html = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)
    t = re.sub(r"<[^>]+>", " | ", html).replace("&nbsp;", " ").replace("&amp;", "&")
    t = re.sub(r"\s+", " ", t)
    return re.sub(r"(\s*\|\s*)+", " | ", t)


def tanggal(s):
    m = re.search(r"(\d{1,2})\s+([A-Za-z]{3,})\s+(\d{4})", s or "")
    if not m or m.group(2)[:3].lower() not in BULAN:
        return pd.NaT
    return pd.Timestamp(int(m.group(3)), BULAN[m.group(2)[:3].lower()], int(m.group(1)))


def rupiah(s):
    m = re.findall(r"Rp\s*([\d.]+)", s or "")
    return [float(x.replace(".", "")) for x in m]


def angka(s):
    m = re.search(r"([\d.]+(?:,\d+)?)", s or "")
    return float(m.group(1).replace(".", "").replace(",", ".")) if m else float("nan")


def persen(s):
    """Persen bisa '30', '30,3' ATAU '30.3' (titik = desimal di sini, bukan ribuan)."""
    m = re.search(r"(\d+(?:[.,]\d+)?)", s or "")
    return float(m.group(1).replace(",", ".")) if m else float("nan")


def daftar_halaman(n):
    html = ambil(f"{DASAR}/id/ipo/index?page={n}&per-page=12")
    kartu = []
    tautan = list(dict.fromkeys(re.findall(r'href="(/id/ipo/(\d+)/[^"]+)"', html)))
    t = teks_pipa(html)
    t = t[t.find("Tanggal Selesai") + len("Tanggal Selesai"):]     # buang menu filter (berisi nama-nama status)
    for url, i in tautan:
        kartu.append({"id": int(i), "url": DASAR + url})
    # status + kode per kartu: pola 'Status | PT ... (KODE)' berurutan sesuai tautan
    status = re.findall(r"\| (Pre-Effective|Book Building|Waiting For Offering|Offering|Allotment|Closed|Postponed|Canceled) \| "
                        r"(.+?) \(([A-Z0-9\-]+)\)", t)
    for k, (st, nama, kode) in zip(kartu, status):
        k.update({"status": st, "nama": nama.strip(), "kode": kode})
    return kartu


def detail(url):
    t = teks_pipa(ambil(url))

    def setelah(label, n=1):
        m = re.search(re.escape(label) + r" \| ((?:[^|]+\| ){%d})" % n, t)
        return m.group(1).split(" | ")[:n] if m else [""] * n

    bb_tgl, bb_harga = setelah("Book Building", 2)
    po_tgl, po_harga = setelah("Penawaran Umum", 2)
    tgl_bb = re.findall(r"\d{1,2} [A-Za-z]{3,} \d{4}", bb_tgl)
    tgl_po = re.findall(r"\d{1,2} [A-Za-z]{3,} \d{4}", po_tgl)
    rentang = rupiah(bb_harga)
    m_jatah = re.search(r"Penjatahan(?: \([^)]*\))? \| (\d{1,2} [A-Za-z]{3,} \d{4})", t)
    return {
        "kode_emiten": setelah("Kode Emiten")[0].strip(),
        "sektor": setelah("Sektor")[0].strip(), "subsektor": setelah("Subsektor")[0].strip(),
        "bidang_usaha": setelah("Bidang usaha")[0].strip()[:300],
        "saham_ditawarkan": angka(setelah("Jumlah Saham Ditawarkan")[0]),
        "persen_dari_total": persen(setelah("% dari Total Saham Dicatatkan")[0]),
        "partisipan_admin": setelah("Partisipan Admin")[0].strip(),
        "penjamin_emisi": setelah("Penjamin Emisi Efek")[0].strip(),
        "bookbuilding_mulai": tanggal(tgl_bb[0]) if tgl_bb else pd.NaT,
        "bookbuilding_selesai": tanggal(tgl_bb[-1]) if tgl_bb else pd.NaT,
        "harga_bawah": rentang[0] if rentang else float("nan"),
        "harga_atas": rentang[-1] if rentang else float("nan"),
        "penawaran_mulai": tanggal(tgl_po[0]) if tgl_po else pd.NaT,
        "penawaran_selesai": tanggal(tgl_po[-1]) if tgl_po else pd.NaT,
        "harga_final": (rupiah(po_harga) or [float("nan")])[0],
        "penjatahan": tanggal(m_jatah.group(1)) if m_jatah else pd.NaT,
        "distribusi": tanggal(setelah("Distribusi")[0]),
        "pencatatan": tanggal(setelah("Tanggal Pencatatan")[0]),
        "syariah": " Syariah " in t[:3000],
    }


# ===== 1) semua halaman daftar =====
kartu, n = [], 1
while True:
    k = daftar_halaman(n)
    baru = [x for x in k if x["id"] not in {y["id"] for y in kartu}]
    if not baru:
        break
    kartu += baru
    if TES or n >= 60:
        break
    n += 1
    time.sleep(JEDA)
daftar = pd.DataFrame(kartu)
print(f"📋 {len(daftar)} IPO di {n} halaman daftar | status: {daftar['status'].value_counts().to_dict()}")

# ===== 2) detail =====
folder = Path("data/raw/ipo")
lama = pd.DataFrame()
if not TES and not HISTORI:
    from huggingface_hub import hf_hub_download
    try:
        lama = pd.read_parquet(hf_hub_download("fadli-sparks/quant-data", "raw/ipo/detail.parquet", repo_type="dataset",
                                               token=os.environ.get("HF_TOKEN") or Path("kunci_hf.txt").read_text().strip()))
    except Exception as e:
        if "404" not in str(e) and "EntryNotFound" not in type(e).__name__:
            raise
if TES:
    perlu = pd.concat([daftar.head(2), daftar[daftar["status"] == "Closed"].head(2)])
elif HISTORI or lama.empty:
    perlu = daftar
else:
    sudah_selesai = set(lama.loc[lama["status"].isin(SELESAI), "id"])
    perlu = daftar[~daftar["id"].isin(sudah_selesai)]
print(f"🔎 ambil detail {len(perlu)} IPO...")
baris = []
for _, r in perlu.iterrows():
    try:
        baris.append({**r.to_dict(), **detail(r["url"])})
    except Exception as e:
        print(f"   ⚠️  {r['url']}: {type(e).__name__}: {str(e)[:80]}")
    time.sleep(JEDA)
d = pd.DataFrame(baris)
d["waktu_ambil"] = pd.Timestamp(SEKARANG).tz_localize(None)
if not lama.empty:
    d = pd.concat([lama[~lama["id"].isin(d["id"])], d], ignore_index=True)
for k in [c for c in d.columns if c in ("bookbuilding_mulai", "bookbuilding_selesai", "penawaran_mulai", "penawaran_selesai",
                                        "penjatahan", "distribusi", "pencatatan", "waktu_ambil")]:
    d[k] = pd.to_datetime(d[k]).astype("datetime64[ns]")
for k in d.columns:
    if d[k].dtype == object:
        d[k] = d[k].astype("string")
d = d.sort_values("id").reset_index(drop=True)

tutup = d[d["status"] == "Closed"]
print(f"✅ detail {len(d)} IPO | Closed {len(tutup)}: harga final terisi {tutup['harga_final'].notna().mean():.0%}, "
      f"pencatatan terisi {tutup['pencatatan'].notna().mean():.0%}, penjamin terisi {(tutup['penjamin_emisi'].str.len() > 0).mean():.0%}")
if len(tutup):
    print(f"   pencatatan {tutup['pencatatan'].min():%Y-%m-%d} s/d {tutup['pencatatan'].max():%Y-%m-%d} | "
          f"penjamin terbanyak: {tutup['penjamin_emisi'].value_counts().head(3).to_dict()}")
if TES:
    kol = ["id", "kode", "status", "kode_emiten", "sektor", "saham_ditawarkan", "persen_dari_total", "penjamin_emisi",
           "bookbuilding_mulai", "harga_bawah", "harga_atas", "penawaran_selesai", "harga_final", "pencatatan", "syariah"]
    print(d[kol].T.to_string())
    print("🧪 mode tes: tidak disimpan")
    sys.exit()
(folder / "daftar").mkdir(parents=True, exist_ok=True)
daftar["waktu_ambil"] = pd.Timestamp(SEKARANG).tz_localize(None)
daftar["waktu_ambil"] = daftar["waktu_ambil"].astype("datetime64[ns]")
for k in ["url", "status", "nama", "kode"]:
    daftar[k] = daftar[k].astype("string")
daftar.to_parquet(folder / "daftar" / f"{SEKARANG.date().isoformat()}.parquet", index=False)
d.to_parquet(folder / "detail.parquet", index=False)
print(f"💾 {folder}/daftar/{SEKARANG.date().isoformat()}.parquet + detail.parquet")
