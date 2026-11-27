"""
HASIL OPERASI MONETER Bank Indonesia (lelang SRBI, SUVBI, SVBI, SukBI, Term Deposit, Repo/Reverse Repo SBN, PasBI, FX Swap, DNDF
termasuk TRANSAKSI DNDF JUAL = jejak INTERVENSI KURS BI) -> raw/harian/operasi_moneter  (+ histori sejak 2019 -> raw/histori/operasi_moneter)
Halaman publik: https://www.bi.go.id/id/publikasi/lelang/operasi-moneter/Default.aspx (robots.txt BI: Allow /).
Halaman daftar = 10 operasi terbaru per halaman; halaman berikut lewat tombol halaman (postback formulir publik, cara sama dgn
kumpul_jisdor.py). Harian: halaman 1-3 (~30 operasi, ~3 hari).
HISTORI (--histori): formulir FILTER RESMI halaman daftar (kotak 'Dari Tanggal'/'Sampai Tanggal', format dd/mm/yyyy, tombol 'Cari')
  per BULAN, lalu tombol 'Next' sampai habis. Daftar resmi baru dimulai 2019 (filter 2010-2018 kosong; dicek 27 Nov 2026).
  Maret 2020 = 165 operasi (COVID). Cek: jumlah tautan unik per bulan = label 'Menampilkan .. dari N data' (beda -> dicetak).
  Simpan per TAHUN: raw/histori/operasi_moneter/<tahun>.parquet & halaman_<tahun>.parquet, upload tiap tahun -> bisa dilanjutkan
  (tahun yang sudah ada di gudang dilewati, kecuali tahun berjalan). ~4.000+ halaman hasil x jeda 2 dtk ~ 3-4 jam (workflow MANUAL).
Isi file (format panjang, angka DISIMPAN SEBAGAI TEKS asli; format Indonesia '39.023,00' & 'Rp18.409' diurai saat riset):
  <tanggal|tahun>.parquet   url, judul, tanggal_operasi, jenis, tabel_ke, baris, kolom, teks, header, waktu_ambil
  halaman_<..>.parquet      url, judul, html (potongan <table> halaman asli, cadangan bila pengurai perlu diubah)
JEBAKAN: judul di daftar memuat '&#160;' & karakter tak terlihat (U+200B) di tengah kata ('H​asil') -> dibersihkan sebelum
  tanggal/jenis diurai. Tumpang tindih antar hari disengaja (dobel dibuang saat dipakai, kunci url+tabel_ke+baris+kolom).
Cara pakai: python kumpul_operasi_moneter.py   |   --tes (tanpa simpan)   |   --histori [--tes = 1 bulan, tanpa simpan]
"""
import html as htmllib
import io
import os
import re
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

DASAR = "https://www.bi.go.id"
DAFTAR = DASAR + "/id/publikasi/lelang/operasi-moneter/Default.aspx"
H = {"User-Agent": "quant-data-collector/1.0 (personal research project)"}
TES, HISTORI = "--tes" in sys.argv, "--histori" in sys.argv
SEKARANG = datetime.now(timezone.utc)
REPO = "fadli-sparks/quant-data"
P = "ctl00$ctl51$g_7479a363_e1c8_4b39_9580_d8d6eed7b2fe$ctl00$"          # awalan nama kontrol formulir daftar
NEXT = P + "DataPagerLaporan$ctl02$ctl00"
POLA_ITEM = r'href="(/id/publikasi/lelang/operasi-moneter/Pages/[^"#?]+\.aspx)"'
BULAN = {b: i + 1 for i, b in enumerate(["januari", "februari", "maret", "april", "mei", "juni", "juli", "agustus", "september",
                                          "oktober", "november", "desember"])}
JENIS = [("DNDF Jual", r"dndf[\s-]*jual"), ("DNDF Beli", r"dndf[\s-]*beli"), ("Rollover DNDF", r"rollover[\s-]*dndf"), ("DNDF", r"dndf"),
         ("SRBI", r"\bsrbi\b"), ("SUVBI", r"suvbi"), ("SVBI", r"svbi"), ("SukBI", r"sukbi"), ("FX Swap", r"fx[\s-]*swap"),
         ("Reverse Repo SBN", r"\brr[\s-]*sbn|reverse[\s-]*repo"), ("Repo", r"\brepo\b"), ("PasBI", r"pasbi"),
         ("Term Deposit Valas", r"td[\s-]*valas|term[\s-]*deposit[\s-]*valas"), ("Term Deposit", r"\btd\b|term[\s-]*deposit"),
         ("BI FRN", r"floating\s*rate|bi[\s-]*frn"), ("Spot Valas", r"\bspot\s+[a-z]{3}\b"), ("Swap Valas", r"\bswap\s+[a-z]{3}\b"),
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


def bersih_judul(s):
    s = htmllib.unescape(s).replace("​", "").replace("﻿", "").replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


JUDUL = {}       # url -> teks tautan di daftar resmi


def tautan(html):
    for m in re.finditer(POLA_ITEM + r"[^>]*>\s*([^<]{5,200})", html):
        j = bersih_judul(m.group(2))
        if j:
            JUDUL.setdefault(m.group(1), j)
    return list(dict.fromkeys(re.findall(POLA_ITEM, html)))


def tanggal_dari(judul):
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", judul)
    if m and m.group(2).lower() in BULAN:
        try:
            return pd.Timestamp(int(m.group(3)), BULAN[m.group(2).lower()], int(m.group(1)))
        except ValueError:
            return pd.NaT
    return pd.NaT


def jenis_dari(judul):
    t = judul.lower()
    for nama, pola in JENIS:
        if re.search(pola, t):
            return nama


def hidden(html):
    return {i["name"]: i.get("value", "") for i in BeautifulSoup(html, "lxml").find_all("input", {"type": "hidden"}) if i.get("name")}


def urai_operasi(sesi, daftar_url):
    """Buka tiap halaman hasil -> (baris sel tabel, potongan html)."""
    baris, halaman = [], []
    for n, u in enumerate(dict.fromkeys(daftar_url)):
        r = minta(sesi, "GET", DASAR + u)
        time.sleep(2)
        if r is None:
            continue
        html = r.text
        judul = JUDUL.get(u) or u.split("/")[-1].removesuffix(".aspx").replace("-", " ")     # <title> halaman kadang generik
        # cadangan: HANYA potongan <table> (halaman utuh ~300 KB terlalu besar)
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
        if HISTORI and (n + 1) % 100 == 0:
            print(f"      ... {n + 1} halaman hasil dibuka")
    return baris, halaman


def rapikan(baris):
    d = pd.DataFrame(baris)
    if d.empty:
        return d
    d["tanggal_operasi"] = d["judul"].map(tanggal_dari).astype("datetime64[ns]")
    d["jenis"] = d["judul"].map(jenis_dari)
    d["waktu_ambil"] = pd.Timestamp(SEKARANG).tz_localize(None).floor("s")
    for k in ["url", "judul", "teks", "header", "jenis"]:
        d[k] = d[k].astype("string")
    return d


def ringkas(d):
    ring = d.groupby(["jenis"])["url"].nunique().sort_values(ascending=False)
    print(f"✅ {d['url'].nunique()} operasi, {len(d):,} sel tabel; {d['tanggal_operasi'].min():%Y-%m-%d} s/d {d['tanggal_operasi'].max():%Y-%m-%d}"
          f" (tanpa tanggal: {d.drop_duplicates('url')['tanggal_operasi'].isna().sum()})")
    print("   " + " | ".join(f"{k} {v}" for k, v in ring.items()))
    for j in sorted(d.loc[d["jenis"] == "Lainnya", "judul"].unique())[:20]:
        print(f"   (jenis Lainnya) {j}")
    dn = d[d["jenis"] == "DNDF Jual"]
    if len(dn):
        u0 = dn["url"].iloc[0]
        x = dn[(dn["url"] == u0) & (dn["tabel_ke"] == 0)]
        print(f"   contoh DNDF jual: {' ; '.join(x.groupby('baris')['teks'].apply(' / '.join).tolist()[:3])}")


def daftar_bulan(sesi, th, bl):
    """Tautan semua operasi di satu bulan lewat filter tanggal resmi + tombol Next. Kembali (tautan, label_N)."""
    akhir = (pd.Timestamp(th, bl, 1) + pd.offsets.MonthEnd(0)).day
    isian = {P + "TextBoxSearch": "", P + "TextBoxDateStart": f"01/{bl:02d}/{th}", P + "TextBoxDateEnd": f"{akhir:02d}/{bl:02d}/{th}"}
    r = minta(sesi, "GET", DAFTAR)
    if r is None:
        return None, None
    data = hidden(r.text)
    data.update({"__EVENTTARGET": "", "__EVENTARGUMENT": "", **isian, P + "ButtonFilter": "Cari"})
    r = minta(sesi, "POST", DAFTAR, data=data)
    time.sleep(1.5)
    semua, label = [], None
    for _ in range(200):
        if r is None:
            return None, label
        t = r.text
        m = re.search(r"Menampilkan\s*\d+\s*\D\s*\d+\s*dari\s*(\d+)\s*data", t)
        if m is None:                               # tidak ada operasi di bulan ini
            return semua, 0
        label = int(m.group(1))
        semua += [u for u in tautan(t) if u not in semua]
        tombol = re.search(r'name="' + re.escape(NEXT) + r'"[^>]*>', t)
        if tombol is None or "disabled" in tombol.group(0) or len(semua) >= label:
            break
        data = hidden(t)
        data.update({"__EVENTTARGET": "", "__EVENTARGUMENT": "", **isian, NEXT + ".x": "8", NEXT + ".y": "8"})
        r = minta(sesi, "POST", DAFTAR, data=data)
        time.sleep(1.5)
    return semua, label


sesi = requests.Session()

# ===================== HISTORI =====================
if HISTORI:
    hari_ini = SEKARANG.date()
    folder = Path("data/raw/histori/operasi_moneter")
    folder.mkdir(parents=True, exist_ok=True)
    if TES:
        tautan_bln, label = daftar_bulan(sesi, 2020, 3)
        print(f"🧪 Maret 2020: {len(tautan_bln or [])} tautan (label {label}); membuka 12 halaman hasil pertama + 12 terakhir")
        b, _ = urai_operasi(sesi, (tautan_bln or [])[:12] + (tautan_bln or [])[-12:])
        d = rapikan(b)
        if d.empty:
            print("❌ tidak ada tabel")
            sys.exit(1)
        ringkas(d)
        print(d.drop_duplicates("url")[["judul", "tanggal_operasi", "jenis"]].to_string())
        print("🧪 mode tes: tidak disimpan")
        sys.exit()
    from huggingface_hub import HfApi
    api_hf = HfApi(token=os.environ.get("HF_TOKEN") or Path("kunci_hf.txt").read_text().strip())
    sudah = {Path(x).name for x in api_hf.list_repo_files(REPO, repo_type="dataset") if x.startswith("raw/histori/operasi_moneter/")}
    print(f"☁️  {len(sudah)} file histori operasi moneter sudah di gudang (tahun itu dilewati, kecuali tahun berjalan)")

    def unggah(f):
        for _ in range(6):
            try:
                api_hf.upload_file(path_or_fileobj=str(f), path_in_repo=f"raw/histori/operasi_moneter/{f.name}", repo_id=REPO,
                                   repo_type="dataset", commit_message=f"Upload raw/histori/operasi_moneter/{f.name}")
                return
            except Exception as e:
                print(f"   ⚠️  upload {f.name}: {type(e).__name__}, tunggu 2 menit")
                time.sleep(120)
        raise RuntimeError(f"upload {f.name} gagal terus")

    for th in range(2019, hari_ini.year + 1):
        f, fh = folder / f"{th}.parquet", folder / f"halaman_{th}.parquet"
        if (f.exists() or f.name in sudah) and th < hari_ini.year:
            print(f"   {th}: sudah ada, dilewati")
            continue
        t0, tautan_th, selisih = time.time(), [], []
        for bl in range(1, 13):
            if date(th, bl, 1) > hari_ini:
                break
            tb, label = daftar_bulan(sesi, th, bl)
            if tb is None:
                raise RuntimeError(f"daftar {th}-{bl:02d} gagal dibuka (jangan simpan tahun yang bolong)")
            if label != len(tb):
                selisih.append(f"{th}-{bl:02d}: {len(tb)} tautan vs label {label}")
            tautan_th += [u for u in tb if u not in tautan_th]
            print(f"   {th}-{bl:02d}: {len(tb)} operasi (label {label})")
        b, hal = urai_operasi(sesi, tautan_th)
        d = rapikan(b)
        if d.empty:
            print(f"   {th}: kosong")
            continue
        ringkas(d)
        tanpa_tabel = len(set(tautan_th) - set(d["url"]))
        print(f"   {th}: {len(tautan_th)} tautan, {d['url'].nunique()} berisi tabel, {tanpa_tabel} tanpa tabel")
        for s in selisih:
            print(f"   ⚠️ jumlah tautan beda dgn label: {s}")
        d.to_parquet(f, index=False)
        pd.DataFrame(hal).astype("string").to_parquet(fh, index=False)
        unggah(f)
        unggah(fh)
        print(f"   💾☁️  {th}: {d['url'].nunique()} operasi, {len(d):,} sel ({(time.time() - t0) / 60:.0f} menit)")
    print("✅ histori operasi moneter selesai")
    sys.exit()

# ===================== HARIAN =====================
r = minta(sesi, "GET", DAFTAR)
if r is None:
    print("❌ halaman daftar tidak bisa dibuka")
    sys.exit(1)
semua = tautan(r.text)
info = re.search(r"Menampilkan\s*\d+\s*\D\s*\d+\s*dari\s*(\d+)\s*data", r.text)
print(f"📋 halaman 1: {len(semua)} operasi (daftar resmi memuat {info.group(1) if info else '?'} data)")
# halaman 2..n: tombol halaman (postback formulir publik)
pager = re.findall(r"__doPostBack\(&#39;([^&]+DataPagerLaporan\$ctl01\$ctl0\d)&#39;", r.text)
html_daftar = r.text
for target in list(dict.fromkeys(pager))[:2]:            # harian: halaman 2-3 saja (~30 operasi terbaru, ~3 hari)
    data = hidden(html_daftar)
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

baris, halaman = urai_operasi(sesi, semua)
d = rapikan(baris)
if d.empty:
    print("❌ tidak ada tabel hasil terbaca")
    sys.exit(1)
ringkas(d)
if TES:
    print("🧪 mode tes: tidak disimpan")
    sys.exit()
folder = Path("data/raw/harian/operasi_moneter")
folder.mkdir(parents=True, exist_ok=True)
tgl = SEKARANG.date().isoformat()
d.to_parquet(folder / f"{tgl}.parquet", index=False)
pd.DataFrame(halaman).astype("string").to_parquet(folder / f"halaman_{tgl}.parquet", index=False)
print(f"💾 {folder}/{tgl}.parquet")
