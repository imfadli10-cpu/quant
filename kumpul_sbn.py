"""
Foto HARIAN imbal hasil (yield) Surat Berharga Negara Indonesia & obligasi korporasi dari PHEI (data "hanya ke depan").

PHEI (Penilai Harga Efek Indonesia, lembaga resmi penilai harga obligasi) menerbitkan tiap hari bursa:
  - kurva   : Indonesia Government Securities Yield Curve (IGSYC), tenor 0,1-30 tahun
  - sbn     : seri benchmark SUN (FR...)            - sbsn: seri benchmark sukuk negara (PBS...)
  - ritel   : seri ritel (ORI, SBR, ST, SR...)      - korporasi: yield korporasi per tenor & peringkat (IGS, AAA, AA, A, BBB)
Halaman memuat "hari ini" & "kemarin" -> dua tanggal per foto. Histori gratis tidak tersedia -> wajib difoto tiap hari.
Kegunaan: suku bunga & risiko kredit Indonesia (selisih korporasi - pemerintah = stres kredit), kemiringan kurva (resesi),
reaksi pasar obligasi lokal terhadap The Fed / rupiah. Sumber: https://www.phei.co.id/Data/HPW-dan-Imbal-Hasil
(robots.txt mengizinkan halaman Data). Angka berformat Indonesia (koma = desimal).

Isi: data/raw/harian/sbn/<tanggal UTC>.parquet, format panjang:
  tanggal_data, hari (hari_ini/kemarin), kelompok, nama, peringkat, tenor_thn, yield_pct, harga_pct, kupon_pct, waktu_ambil
Cara pakai:  python kumpul_sbn.py      |   python kumpul_sbn.py --tes   (tanpa simpan)
"""
import io
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

URL = "https://www.phei.co.id/Data/HPW-dan-Imbal-Hasil"
HEADER = {"User-Agent": "quant-data-collector/1.0 (personal research project)"}
SEKARANG = datetime.now(timezone.utc)
TES = "--tes" in sys.argv
BULAN = {b: i + 1 for i, b in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                          "september", "october", "november", "december"])}


def ambil():
    for percobaan in range(4):
        try:
            r = requests.get(URL, headers=HEADER, timeout=(15, 60))
            r.raise_for_status()
            return r.text
        except requests.RequestException as e:
            if percobaan == 3:
                raise
            print(f"   ⚠️  {type(e).__name__}, coba lagi")
            time.sleep(10 * (percobaan + 1))


html = ambil()
m = re.search(r"Yield Curve\s*per\s*(\d{1,2})-([A-Za-z]+)-(\d{4})", re.sub(r"<[^>]+>", " ", html))
if not m:
    sys.exit("❌ tanggal kurva tidak ditemukan (format halaman berubah?)")
tgl = pd.Timestamp(int(m.group(3)), BULAN[m.group(2).lower()], int(m.group(1)))
tabel = pd.read_html(io.StringIO(html), decimal=",", thousands=".")
print(f"📄 {len(tabel)} tabel, kurva per {tgl:%Y-%m-%d}")

baris = []
# Prinsip: kenali tabel dari NAMA KOLOM-nya, bukan urutannya (urutan halaman bisa berubah)
for t in tabel:
    t = t.loc[:, [c for c in t.columns if not str(c).startswith("Unnamed")]]
    kol = [str(c) for c in t.columns]
    if kol == ["Tenor Year", "Today", "Yesterday"]:                       # kurva IGSYC (2 potongan)
        for _, r in t.iterrows():
            for hari, k in [("hari_ini", "Today"), ("kemarin", "Yesterday")]:
                baris.append({"hari": hari, "kelompok": "kurva", "nama": f"IGSYC {r['Tenor Year']:g}",
                              "tenor_thn": float(r["Tenor Year"]), "yield_pct": float(r[k])})
    elif "Series" in kol and "Today Yield (%)" in kol:                     # seri benchmark / ritel
        for _, r in t.iterrows():
            nama = str(r["Series"])
            kel = "sbsn" if nama.startswith("PBS") else ("sbn" if nama.startswith("FR") else "ritel")
            for hari, y, h in [("hari_ini", "Today Yield (%)", "Today Price (%)"),
                               ("kemarin", "Yesterday Yield (%)", "Yesterday Price (%)")]:
                baris.append({"hari": hari, "kelompok": kel, "nama": nama, "tenor_thn": float(r["TTM (Y)"]),
                              "yield_pct": float(r[y]), "harga_pct": float(r[h]), "kupon_pct": float(r["Coupon (%)"])})
    elif kol and kol[0] == "Tenor (Year)" and "AAA" in kol:                # korporasi per peringkat (hari ini saja)
        for _, r in t.iterrows():
            for pr in kol[1:]:
                baris.append({"hari": "hari_ini", "kelompok": "korporasi", "nama": f"{pr} {r['Tenor (Year)']:g}",
                              "peringkat": pr, "tenor_thn": float(r["Tenor (Year)"]), "yield_pct": float(r[pr])})

d = pd.DataFrame(baris)
for k in ["peringkat", "harga_pct", "kupon_pct"]:
    if k not in d:
        d[k] = None
d.insert(0, "tanggal_data", tgl)
d["waktu_ambil"] = pd.Timestamp(SEKARANG).tz_localize(None)
for k in ["tanggal_data", "waktu_ambil"]:
    d[k] = pd.to_datetime(d[k]).astype("datetime64[ns]")
for k in ["hari", "kelompok", "nama", "peringkat"]:
    d[k] = d[k].astype("string")
for k in ["tenor_thn", "yield_pct", "harga_pct", "kupon_pct"]:
    d[k] = pd.to_numeric(d[k], errors="coerce").astype("float64")

# Cek kewajaran: yield SBN 1-20% ; harga 50-150% ; kurva >= 15 tenor ; semua kelompok ada
jumlah = d.groupby("kelompok").size().to_dict()
aneh = d[(d["yield_pct"] < 1) | (d["yield_pct"] > 20)]
aneh_harga = d[d["harga_pct"].notna() & ((d["harga_pct"] < 50) | (d["harga_pct"] > 150))]
print(f"✅ {len(d)} baris: {jumlah}")
kurva = d[(d["kelompok"] == "kurva") & (d["hari"] == "hari_ini")].set_index("tenor_thn")["yield_pct"]
print(f"   kurva hari ini: 1 thn {kurva.get(1.0, float('nan')):.3f}% | 5 thn {kurva.get(5.0, float('nan')):.3f}% | "
      f"10 thn {kurva.get(10.0, float('nan')):.3f}% | 30 thn {kurva.get(30.0, float('nan')):.3f}%")
masalah = []
if len(kurva) < 15:
    masalah.append(f"kurva cuma {len(kurva)} tenor")
if len(aneh) or len(aneh_harga):
    masalah.append(f"{len(aneh)} yield & {len(aneh_harga)} harga di luar batas wajar")
for k in ["kurva", "sbn", "sbsn", "ritel", "korporasi"]:
    if k not in jumlah:
        masalah.append(f"kelompok {k} tidak ada")
if masalah:
    print("❌ " + "; ".join(masalah) + " -> tidak disimpan")
    sys.exit(1)
if TES:
    print(d[d["kelompok"] == "sbn"].head(4).to_string(index=False))
    print("🧪 mode tes: tidak disimpan")
    sys.exit()
folder = Path("data/raw/harian/sbn")
folder.mkdir(parents=True, exist_ok=True)
d.to_parquet(folder / f"{SEKARANG.date().isoformat()}.parquet", index=False)
print(f"💾 {folder}/{SEKARANG.date().isoformat()}.parquet")
