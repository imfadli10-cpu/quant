"""
HASIL OPERASI MONETER Bank Indonesia (lelang SRBI, SUVBI, SVBI, SukBI, Term Deposit, Repo/Reverse Repo SBN, PasBI, FX Swap, DNDF
termasuk TRANSAKSI DNDF JUAL = jejak INTERVENSI KURS BI) -> raw/harian/operasi_moneter
Halaman publik: https://www.bi.go.id/id/publikasi/lelang/operasi-moneter/Default.aspx (robots.txt BI: Allow /).
Halaman daftar = 10 operasi terbaru per halaman; halaman berikut lewat tombol halaman (postback formulir publik, cara sama dgn
kumpul_jisdor.py). Harian: halaman 1-3 (~30 operasi, ~3 hari). Daftar resmi memuat SELURUH histori (20.138 data, 26 Nov 2026) lewat tombol halaman.
Isi file harian (format panjang, angka DISIMPAN SEBAGAI TEKS asli; format Indonesia '39.023,00' & 'Rp18.409' diurai saat riset):
  raw/harian/operasi_moneter/<tanggal UTC>.parquet   url, judul, tanggal_operasi, jenis, tabel_ke, baris, kolom, teks, waktu_ambil
  raw/harian/operasi_moneter/halaman_<tanggal>.parquet url, judul, html (isi halaman asli, cadangan bila pengurai perlu diubah)
Tumpang tindih antar hari disengaja (dobel dibuang saat dipakai, kunci url+tabel_ke+baris+kolom).
Cara pakai: python kumpul_operasi_moneter.py   |   --tes (tanpa simpan)
"""
import io
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

DASAR = "https://www.bi.go.id"
DAFTAR = DASAR + "/id/publikasi/lelang/operasi-moneter/Default.aspx"
H = {"User-Agent": "quant-data-collector/1.0 (personal research project)"}
TES = "--tes" in sys.argv
SEKARANG = datetime.now(timezone.utc)
POLA_ITEM = r'href="(/id/publikasi/lelang/operasi-moneter/Pages/[^"#?]+\.aspx)"'
BULAN = {b: i + 1 for i, b in enumerate(["januari", "februari", "maret", "april", "mei", "juni", "juli", "agustus", "september",
                                          "oktober", "november", "desember"])}
JENIS = [("DNDF Jual", r"dndf[\s-]*jual"), ("DNDF Beli", r"dndf[\s-]*beli"), ("Rollover DNDF", r"rollover[\s-]*dndf"), ("DNDF", r"dndf"),
         ("SRBI", r"\bsrbi\b"), ("SUVBI", r"suvbi"), ("SVBI", r"svbi"), ("SukBI", r"sukbi"), ("FX Swap", r"fx[\s-]*swap"),
         ("Reverse Repo SBN", r"\brr[\s-]*sbn|reverse[\s-]*repo"), ("Repo", r"\brepo\b"), ("PasBI", r"pasbi"),
         ("Term Deposit Valas", r"td[\s-]*valas|term[\s-]*deposit[\s-]*valas"), ("Term Deposit", r"\btd\b|term[\s-]*deposit"),
         ("BI FRN", r"floating\s*rate|bi\s*frn"), ("Spot Valas", r"\bspot\s+[a-z]{3}\b"), ("Swap Valas", r"\bswap\s+[a-z]{3}\b"),
         ("SBI", r"\bsbi\b"), ("Lainnya", r".")]


def minta(sesi, metode, url, **k):
    for coba in range(4):
        try:
            r = sesi.request(metode, url, headers=H, timeout=(20, 120), **k)
            if r.status_code == 200:
                return r
            print(f"   ⚠️ HTTP {r.status_code} {url[-60:]}")
            if 400 <= r.status_code < 500 and r.status_code != 429:
                return None
        except requests.RequestException as e:
            print(f"   🔌 {type(e).__name__}")
        time.sleep(10 * (coba + 1))
    return None


JUDUL = {}       # url -> teks tautan di daftar resmi


def tautan(html):
    for m in re.finditer(POLA_ITEM + r"[^>]*>\s*([^<]{5,200})", html):
        JUDUL.setdefault(m.group(1), re.sub(r"\s+", " ", m.group(2)).strip())
    return list(dict.fromkeys(re.findall(POLA_ITEM, html)))


def tanggal_dari(judul):
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", judul)
    if m and m.group(2).lower() in BULAN:
        return pd.Timestamp(int(m.group(3)), BULAN[m.group(2).lower()], int(m.group(1)))
    return pd.NaT


def jenis_dari(judul):
    t = judul.lower()
    for nama, pola in JENIS:
        if re.search(pola, t):
            return nama


def judul_halaman(html):
    m = re.search(r"<title>\s*(.*?)\s*</title>", html, re.S | re.I)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


sesi = requests.Session()
r = minta(sesi, "GET", DAFTAR)
if r is None:
    print("❌ halaman daftar tidak bisa dibuka")
    sys.exit(1)
semua = tautan(r.text)
info = re.search(r"Menampilkan\s*\d+\s*[–-]\s*\d+\s*dari\s*(\d+)\s*data", r.text)
print(f"📋 halaman 1: {len(semua)} operasi (daftar resmi memuat {info.group(1) if info else '?'} data)")
# halaman 2..n: tombol halaman (postback formulir publik)
pager = re.findall(r"__doPostBack\(&#39;([^&]+DataPagerLaporan\$ctl01\$ctl0\d)&#39;", r.text)
html_daftar = r.text
for target in list(dict.fromkeys(pager))[:2]:            # harian: halaman 2-3 saja (~30 operasi terbaru, ~3 hari)
    data = {m.group(1): m.group(2) for m in re.finditer(r'<input type="hidden" name="([^"]+)" id="[^"]*" value="([^"]*)"', html_daftar)}
    if "__VIEWSTATE" not in data:
        break
    data.update({"__EVENTTARGET": target, "__EVENTARGUMENT": ""})
    r2 = minta(sesi, "POST", DAFTAR, data=data)
    time.sleep(2)
    if r2 is None:
        continue
    t2 = tautan(r2.text)
    baru = [u for u in t2 if u not in semua]
    print(f"   halaman berikut: {len(t2)} operasi ({len(baru)} baru)")
    semua += baru

baris, halaman, antre, dilihat = [], [], list(semua), set()
while antre:
    u = antre.pop(0)
    if u in dilihat:
        continue
    dilihat.add(u)
    r = minta(sesi, "GET", DASAR + u)
    time.sleep(2)
    if r is None:
        continue
    html = r.text
    judul = JUDUL.get(u) or u.split("/")[-1].removesuffix(".aspx").replace("-", " ")     # <title> halaman kadang generik
    # cadangan: HANYA potongan <table> (halaman utuh ~300 KB -> ~10 MB/hari terlalu besar)
    halaman.append({"url": u, "judul": judul, "html": "\n".join(re.findall(r"<table.*?</table>", html, re.S | re.I))})
    try:
        tabel = pd.read_html(io.StringIO(html), thousands=None, decimal="|")
    except ValueError:
        tabel = []
    ke = 0
    for t in tabel:
        isi = [str(x) for x in t.values.ravel().tolist()]
        if sum(bool(re.match(r"\s*(hasil|pengumuman)\b", x, re.I)) for x in isi) >= max(2, len(isi) // 3):
            continue                                # kotak daftar "terkait", bukan tabel hasil
        for i in range(t.shape[0]):
            for j in range(t.shape[1]):
                v = t.iat[i, j]
                if pd.isna(v):
                    continue
                baris.append({"url": u, "judul": judul, "tabel_ke": ke, "baris": i, "kolom": j,
                              "teks": re.sub(r"\s+", " ", str(v)).strip(), "header": " | ".join(map(str, t.columns))[:300]})
        ke += 1

d = pd.DataFrame(baris)
if d.empty:
    print("❌ tidak ada tabel hasil terbaca")
    sys.exit(1)
d["tanggal_operasi"] = d["judul"].map(tanggal_dari).astype("datetime64[ns]")
d["jenis"] = d["judul"].map(jenis_dari)
d["waktu_ambil"] = pd.Timestamp(SEKARANG).tz_localize(None).floor("s")
for k in ["url", "judul", "teks", "header", "jenis"]:
    d[k] = d[k].astype("string")
ring = d.groupby(["jenis"])["url"].nunique().sort_values(ascending=False)
print(f"✅ {d['url'].nunique()} operasi, {len(d):,} sel tabel; {d['tanggal_operasi'].min():%Y-%m-%d} s/d {d['tanggal_operasi'].max():%Y-%m-%d}")
print("   " + " | ".join(f"{k} {v}" for k, v in ring.items()))
for j in sorted(d.loc[d["jenis"] == "Lainnya", "judul"].unique()):
    print(f"   (jenis Lainnya) {j}")
dn = d[d["jenis"] == "DNDF Jual"]
if len(dn):
    print(f"   contoh DNDF jual: {' ; '.join(dn[dn['tabel_ke'] == 0].groupby('baris')['teks'].apply(' / '.join).tolist()[:3])}")
if TES:
    print("🧪 mode tes: tidak disimpan")
    sys.exit()
folder = Path("data/raw/harian/operasi_moneter")
folder.mkdir(parents=True, exist_ok=True)
tgl = SEKARANG.date().isoformat()
d.to_parquet(folder / f"{tgl}.parquet", index=False)
pd.DataFrame(halaman).astype("string").to_parquet(folder / f"halaman_{tgl}.parquet", index=False)
print(f"💾 {folder}/{tgl}.parquet")
