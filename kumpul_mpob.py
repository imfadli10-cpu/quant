"""
STATISTIK BULANAN SAWIT MALAYSIA (MPOB, bepi.mpob.gov.my; robots mpob.gov.my 'Disallow:' kosong = tanpa larangan) -> raw/harian/mpob
Malaysia = produsen sawit no. 2 dunia; angka STOK MPOB (~tgl 10 tiap bulan) terkenal menggerakkan harga CPO -> bahan riset saham sawit IDX.
Dua laporan publik (dimuat situs lewat iframe stat/web_report1.php; URL iframe dibaca dari halaman menu, TIDAK ditebak):
  'bulanan'  = Monthly Release terbaru: bulan lalu (r = revisi) & bulan ini (p = awal) per negara bagian: produksi CPO/PK/CPKO/PKC, STOK CPO &
               processed palm oil, ekspor (palm oil, PKO, PKC, oleokimia, biodiesel), impor, harga TBS (FFB RM, 1% OER).
  'ringkasan'= Summary tahun berjalan: tabel bulanan Des tahun lalu .. bulan terakhir (produksi, STOK AKHIR, ekspor, impor, harga TBS).
Histori tahun lalu TIDAK ada di laporan ini (hanya PDF 'Overview of Industry' tahunan 2016-2025, belum diurai) -> HANYA KE DEPAN (mulai 27 Nov 2026).
Foto HARIAN (2-4 permintaan) = tahu KAPAN angka bulan baru terbit & versi sebelum revisi (point-in-time).
SIMPAN raw/harian/mpob/<tanggal UTC>.parquet  format panjang: laporan, url, bagian, baris, kolom, teks, nilai, waktu_ambil
  angka '(4,026)' = negatif; sel kosong dibuang. 'kolom' = judul kolom (mis. 'Oct (p)', 'SEPTEMBER(r)'); baris yang jumlah selnya tidak cocok
  dgn judul (sel gabungan, mis. impor CPO) disimpan dgn kolom 'sel_<j>' (JANGAN dipetakan ke bulan tanpa dicek).
Cara pakai: python kumpul_mpob.py  |  --tes (tanpa simpan)
"""
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

DASAR = "https://bepi.mpob.gov.my"
H = {"User-Agent": "quant-data-collector/1.0 (personal research project)"}
TES = "--tes" in sys.argv
SEKARANG = datetime.now(timezone.utc)
WAKTU = pd.Timestamp(SEKARANG).tz_localize(None).floor("s")


def minta(url):
    for coba in range(4):
        try:
            r = requests.get(url, headers=H, timeout=(20, 120))
            if r.status_code == 200:
                return r.text
            print(f"   ⚠️ HTTP {r.status_code} {url[-70:]}")
            if 400 <= r.status_code < 500 and r.status_code != 429:
                return None
        except requests.RequestException as e:
            print(f"   🔌 {type(e).__name__}")
        time.sleep(10 * (coba + 1))
    return None


def angka(s):
    s = str(s).strip()
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()").replace(",", "")
    try:
        v = float(s)
    except ValueError:
        return np.nan
    return -v if neg else v


def iframe_dari(menu, pola_artikel):
    h = minta(DASAR + menu)
    if h is None:
        return None
    m = re.search(r'href="(' + pola_artikel + r'[^"]+)"', h)
    if not m:
        return None
    time.sleep(2)
    h2 = minta(DASAR + m.group(1))
    s = re.search(r'<iframe[^>]+src="([^"]*web_report[^"]+)"', h2 or "")
    return (DASAR + "/" + s.group(1).replace("&amp;", "&").lstrip("/.").lstrip("/")) if s else None


def urai(nama, url):
    h = minta(url)
    if h is None:
        return []
    out, bagian, sub = [], "", ""
    tabel = BeautifulSoup(h, "lxml").find_all("table")
    if not tabel:
        return []
    rows = [[c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"], recursive=False)] for tr in tabel[0].find_all("tr")]
    rows = [r for r in rows if r and len(" ".join(r)) < 600]
    judul = None
    for r in rows:
        isi = [x for x in r[1:] if x]
        if judul is None and len(r) >= 3 and r[0] == "" and isi:
            judul = r[1:]
            if any("DIFFERENCE" in x.upper() for x in judul):    # laporan bulanan: DIFFERENCE = 2 sel (jumlah & %)
                judul = [x for x in judul if "DIFFERENCE" not in x.upper()] + ["selisih", "selisih_pct"]
            continue
        lab = r[0]
        if lab and not isi:                       # judul bagian / subjudul produk
            if re.search(r"TONNES|PRICE|STOCK|EXPORT|IMPORT|PRODUCTION", lab, re.I):
                bagian, sub = lab, ""
            elif lab.isupper():
                sub = lab
            continue
        if not lab or not isi or re.fullmatch(r"\([a-z]\)|QUANTITY", lab):     # catatan kaki (p)(q)(r)(s) & sub-judul
            continue
        if lab.isupper():                         # baris produk ber-angka (mis. PALM KERNEL) -> bukan anak subjudul sebelumnya
            sub = ""
        cocok = judul is not None and len(r) - 1 == len(judul)
        for j, v in enumerate(r[1:]):
            if not v:
                continue
            out.append({"laporan": nama, "url": url, "bagian": bagian, "baris": f"{sub} | {lab}" if sub else lab,
                        "kolom": judul[j] if cocok else f"sel_{j}", "teks": v, "nilai": angka(v)})
    return out


laporan = {"bulanan": iframe_dari("/index.php/monthly-release", r"/index\.php/monthly-release/\d+"),
           "ringkasan": iframe_dari("/index.php/summary-2", r"/index\.php/summary-2/\d+")}
baris = []
for nama, url in laporan.items():
    if url is None:
        print(f"❌ {nama}: iframe laporan tidak ditemukan")
        continue
    b = urai(nama, url)
    print(f"   {nama}: {url.split('?')[-1]} -> {len(b)} sel")
    baris += b
    time.sleep(2)
d = pd.DataFrame(baris)
if d.empty:
    print("❌ tidak ada data MPOB")
    sys.exit(1)
for k in ("laporan", "url", "bagian", "baris", "kolom", "teks"):
    d[k] = d[k].astype("string")
d["waktu_ambil"] = WAKTU
r = d[(d["laporan"] == "ringkasan")]
stok = r[r["bagian"].str.contains("STOCK", na=False) & (r["baris"] == "Palm Oil")]
if len(stok):
    print("✅ stok palm oil (ringkasan): " + " | ".join(f"{k} {v / 1e6:.2f} jt t" for k, v in zip(stok["kolom"], stok["nilai"])))
else:
    print("⚠️ baris stok palm oil tidak ditemukan di ringkasan -> cek format")
print(f"   {len(d)} sel; kolom tak terpetakan (sel gabungan): {(d['kolom'].str.startswith('sel_')).sum()}")
if TES:
    print(d.head(15).to_string())
    print("🧪 mode tes: tidak disimpan")
    sys.exit()
f = Path(f"data/raw/harian/mpob/{SEKARANG.date().isoformat()}.parquet")
f.parent.mkdir(parents=True, exist_ok=True)
d.to_parquet(f, index=False)
print(f"💾 {f}")
