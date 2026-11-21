"""
HASIL LELANG SURAT BERHARGA NEGARA (SUN & SBSN/sukuk) dari situs DJPPR Kemenkeu (data "hanya ke depan").

Cara (pilihan pengguna 21 Nov 2026: HANYA yang tampil untuk umum, seperti orang membuka beranda tiap hari):
  1) baca daftar berita di BERANDA DJPPR (konten yang sama dengan yang dimuat browser),
  2) untuk berita berjudul "Hasil Lelang ...", buka halaman berita itu,
  3) urai tabelnya: penawaran masuk, nominal dimenangkan, yield rata-rata tertimbang & tertinggi, bid-to-cover per seri.
TIDAK mendaftar seluruh isi situs lewat endpoint pencarian internal (ditolak sebagai akses tidak sah; jangan dilakukan).
Beranda hanya menampilkan ~1 hasil lelang terbaru (lelang tiap Selasa, SUN & SBSN bergantian) -> WAJIB jalan tiap hari.

Kegunaan: minat investor pada utang pemerintah Indonesia (bid-to-cover tinggi = permintaan kuat), yield hasil lelang
= sinyal biaya dana & sentimen investor asing/domestik. Versi Indonesia riset #20 (lelang Treasury AS).

Isi (tanggal UTC server):
  data/raw/harian/lelang_sbn/<tanggal>.parquet          format panjang: tanggal_lelang, jenis (SUN/SBSN), judul, seri,
                                                        pos (label baris), teks (sel asli), nilai (angka; Rp dalam TRILIUN,
                                                        persen dalam %, rasio apa adanya), + baris seri 'TOTAL' dari kalimat
  data/raw/harian/lelang_sbn/halaman_<tanggal>.parquet  HTML asli tiap halaman (untuk mengurai ulang kalau format berubah)
Cara pakai:  python kumpul_lelang_sbn.py      |   python kumpul_lelang_sbn.py --tes   (tanpa simpan)
"""
import io
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

API = "https://api-djppr.kemenkeu.go.id/web/api/v1/page"      # alamat yang dipakai situs djppr.kemenkeu.go.id sendiri
HEADER = {"User-Agent": "quant-data-collector/1.0 (personal research project)"}
SEKARANG = datetime.now(timezone.utc)
TES = "--tes" in sys.argv
BULAN = {b: i + 1 for i, b in enumerate(["januari", "februari", "maret", "april", "mei", "juni", "juli", "agustus",
                                          "september", "oktober", "november", "desember"])}


def minta(params=None):
    for percobaan in range(4):
        try:
            r = requests.get(API, params=params, headers=HEADER, timeout=(15, 60))
            r.raise_for_status()
            return r.json()["Data"]
        except (requests.RequestException, ValueError, KeyError) as e:
            if percobaan == 3:
                raise
            print(f"   ⚠️  {type(e).__name__}, coba lagi")
            time.sleep(10 * (percobaan + 1))


def kumpulkan_item(o, keluar):
    """Cari semua item berita (dict yang punya kunci '@LinkBerita' atau '@Konten') di dalam JSON halaman."""
    if isinstance(o, dict):
        if "@LinkBerita" in o or "@Konten" in o:
            keluar.append(o)
        for v in o.values():
            kumpulkan_item(v, keluar)
    elif isinstance(o, list):
        for v in o:
            kumpulkan_item(v, keluar)
    return keluar


def angka_indonesia(teks):
    """'Rp2,775 triliun' -> 2.775 ; '6,19680%' -> 6.1968 ; '5,55' -> 5.55 ; 'Rp20.104.300.000.000,00' -> 20.1043 (triliun)."""
    t = str(teks).strip().replace("\xa0", " ")
    if t in ("", "-", "nan") or not re.search(r"\d", t):
        return float("nan")
    m = re.search(r"(\d[\d.]*(?:,\d+)?)", t)
    x = float(m.group(1).replace(".", "").replace(",", "."))
    kecil = t.lower()
    if "triliun" in kecil:
        return x
    if "miliar" in kecil:
        return x / 1000
    if kecil.startswith("rp") and x > 1e9:          # rupiah penuh -> triliun
        return x / 1e12
    return x


def tanggal_dari_judul(judul):
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", judul or "")
    if not m or m.group(2).lower() not in BULAN:
        return pd.NaT
    return pd.Timestamp(int(m.group(3)), BULAN[m.group(2).lower()], int(m.group(1)))


def urai(judul, html):
    jenis = "SBSN" if re.search(r"syariah|sukuk|sbsn", judul, re.I) else "SUN"
    tgl = tanggal_dari_judul(judul)
    baris = []
    tabel = pd.read_html(io.StringIO(html), thousands=None, decimal="|")     # semua sel tetap TEKS; diurai sendiri
    for t in tabel:
        t = t.astype(str)
        idx_seri = next((i for i in range(min(3, len(t))) if re.search(r"(FR|PBS|SPN|SPNS|VR|SR|ST|ORI)\d", " ".join(t.iloc[i]))), None)
        if idx_seri is None:
            continue
        seri = list(t.iloc[idx_seri])
        for i in range(idx_seri + 1, len(t)):
            pos = t.iloc[i, 0]
            for j in range(1, t.shape[1]):
                baris.append({"seri": seri[j], "pos": pos, "teks": t.iloc[i, j]})
    teks_polos = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
    for pos, pola in [("Total penawaran yang masuk", r"[Tt]otal penawaran yang masuk sebesar\s*(Rp[\d.,]+)"),
                      ("Total nominal dimenangkan", r"total nominal yang dimenangkan.*?adalah\s*(Rp[\d.,]+)")]:
        m = re.search(pola, teks_polos)
        if m:
            baris.append({"seri": "TOTAL", "pos": pos, "teks": m.group(1)})
    d = pd.DataFrame(baris)
    if d.empty:
        return d
    d["nilai"] = d["teks"].map(angka_indonesia).where(~d["pos"].str.contains("tanggal", case=False))   # baris tanggal = teks
    d.insert(0, "judul", judul)
    d.insert(0, "jenis", jenis)
    d.insert(0, "tanggal_lelang", tgl)
    return d


beranda = minta()
item = kumpulkan_item(json.loads(beranda["PageContentLive"]), [])
hasil_berita = [x for x in item if re.search(r"hasil\s+lelang", x.get("@JudulBerita") or "", re.I)]
print(f"📰 {len(item)} item di beranda, {len(hasil_berita)} berita 'Hasil Lelang'")

semua, halaman = [], []
for x in hasil_berita:
    slug = (x.get("@LinkBerita") or "").lstrip("/")
    p = minta({"url": slug})
    isi = kumpulkan_item(json.loads(p["PageContentLive"] or "[]"), [])
    konten = next((k.get("@Konten") for k in isi if k.get("@Konten")), None)
    if not konten:
        print(f"   ⚠️  {slug}: konten tidak ditemukan (format berubah?)")
        continue
    d = urai(x["@JudulBerita"], konten)
    halaman.append({"slug": slug, "judul": x["@JudulBerita"], "tanggal_berita": x.get("@Tanggal"), "konten_html": konten})
    if d.empty:
        print(f"   ⚠️  {slug}: tabel tidak terurai")
        continue
    semua.append(d)
    btc = d[d["pos"].str.contains("bid", case=False)].set_index("seri")["nilai"].dropna()
    tot = d[d["seri"] == "TOTAL"].set_index("pos")["nilai"]
    print(f"   ✅ {x['@JudulBerita'][:70]}: {d['seri'].nunique() - 1} seri | penawaran Rp{tot.get('Total penawaran yang masuk', float('nan')):.2f} T, "
          f"dimenangkan Rp{tot.get('Total nominal dimenangkan', float('nan')):.2f} T | bid-to-cover {btc.round(2).to_dict()}")
    time.sleep(2)

if not semua:
    print("ℹ️  Tidak ada hasil lelang yang terurai di beranda hari ini -> tidak ada file (bukan error)")
    sys.exit(0)
df = pd.concat(semua, ignore_index=True)
df["tanggal_lelang"] = pd.to_datetime(df["tanggal_lelang"]).astype("datetime64[ns]")
df["waktu_ambil"] = pd.Timestamp(SEKARANG).tz_localize(None)
df["waktu_ambil"] = df["waktu_ambil"].astype("datetime64[ns]")
for k in ["jenis", "judul", "seri", "pos", "teks"]:
    df[k] = df[k].astype("string")
hal = pd.DataFrame(halaman).astype("string")
# Cek kewajaran: bid-to-cover 0,5-20 ; yield 0-20% ; nominal per seri < 100 triliun
btc = df[df["pos"].str.contains("bid", case=False)]["nilai"].dropna()
yld = df[df["pos"].str.contains("yield", case=False)]["nilai"].dropna()
masalah = []
if len(btc) and not btc.between(0.5, 20).all():
    masalah.append(f"bid-to-cover di luar 0,5-20: {btc[~btc.between(0.5, 20)].tolist()}")
if len(yld) and not yld.between(0, 20).all():
    masalah.append(f"yield di luar 0-20%: {yld[~yld.between(0, 20)].tolist()}")
if masalah:
    print("❌ " + "; ".join(masalah) + " -> tidak disimpan")
    sys.exit(1)
print(f"✅ {len(df)} baris dari {df['judul'].nunique()} lelang")
if TES:
    print(df.head(12).to_string(index=False))
    print("🧪 mode tes: tidak disimpan")
    sys.exit()
folder = Path("data/raw/harian/lelang_sbn")
folder.mkdir(parents=True, exist_ok=True)
tgl = SEKARANG.date().isoformat()
df.to_parquet(folder / f"{tgl}.parquet", index=False)
hal.to_parquet(folder / f"halaman_{tgl}.parquet", index=False)
print(f"💾 {folder}/{tgl}.parquet + halaman_{tgl}.parquet")
