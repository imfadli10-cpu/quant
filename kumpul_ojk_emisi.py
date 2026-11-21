"""
OJK "Ikhtisar Perkembangan Emisi Efek & Aksi Korporasi" MINGGUAN (ojk.go.id, kanal Pasar Modal > Data dan Statistik; tanpa robots.txt
= tanpa larangan; hanya halaman & lampiran yang DITAUTKAN di halaman publik). Isi tiap file KUMULATIF sejak awal tahun:
IPO (tgl efektif, jumlah saham, nilai, tgl listing), Penawaran Umum Terbatas / RIGHT ISSUE, EBUS (obligasi/sukuk), PUB EBUS tahap I & II+,
dan AKSI KORPORASI (PMTHMETD = private placement, Transaksi Material, Merger, Go Private, Perubahan/Penambahan Kegiatan Usaha) + tgl RUPS/efektif.
Deretan file mingguan = point-in-time (kapan peristiwa pertama tercatat). Halaman utama hanya menautkan ~5 bulan terakhir -> HANYA KE DEPAN
(mulai Jul 2026).

  python kumpul_ojk_emisi.py        -> data/raw/ojk_emisi/arsip/<nama file>.xlsx (hanya yang BARU) + data/raw/ojk_emisi/urai/<nama>.parquet
                                       (format panjang: file, minggu_ke, bulan, tahun, lembar, bagian, sub_bagian, no, kolom, nilai [teks])
  python kumpul_ojk_emisi.py --tes  -> unduh & urai 1 file terbaru, tanpa simpan
Butuh HF_TOKEN untuk mengetahui file yang sudah ada di gudang (tanpa token: anggap belum ada -> unduh semua yang ditautkan).
"""
import html
import io
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote, unquote

import pandas as pd
import requests

DASAR = "https://www.ojk.go.id"
UTAMA = DASAR + "/id/kanal/pasar-modal/data-dan-statistik/statistik-pasar-modal/Default.aspx"
H = {"User-Agent": "quant-data-collector/1.0 (personal research project)"}
OUT = Path("data/raw/ojk_emisi")
TES = "--tes" in sys.argv
BULAN = {b: i + 1 for i, b in enumerate(["JANUARI", "FEBRUARI", "MARET", "APRIL", "MEI", "JUNI", "JULI", "AGUSTUS", "SEPTEMBER",
                                          "OKTOBER", "NOVEMBER", "DESEMBER"])}


def ambil(url, biner=False):
    for coba in range(4):
        try:
            r = requests.get(url, headers=H, timeout=240)
            if r.status_code == 200:
                return r.content if biner else r.text
            print(f"   ⚠️ HTTP {r.status_code}: {url[-80:]}")
            if 400 <= r.status_code < 500 and r.status_code != 429:
                return None
        except Exception as e:
            print(f"   🔌 {type(e).__name__}: {url[-80:]}")
        time.sleep(15 * (coba + 1))
    return None


def urai(isi, nama):
    m = re.search(r"MINGGU KE-(\d)\s+([A-Z]+)\s+(\d{4})", nama.upper())
    minggu, bulan, tahun = (int(m.group(1)), BULAN.get(m.group(2)), int(m.group(3))) if m else (None, None, None)
    baris = []
    for lembar, d in pd.read_excel(io.BytesIO(isi), sheet_name=None, header=None, dtype=object).items():
        if not lembar.strip().endswith("-id"):
            continue
        bagian, sub, kepala = None, None, {}
        for _, r in d.iterrows():
            c1 = r.iloc[1] if len(r) > 1 else None
            if isinstance(c1, str) and c1.strip().startswith("Perusahaan yang melakukan"):
                bagian, sub, kepala = c1.strip(), None, {}
            elif isinstance(c1, str) and c1.strip() == "No":
                kepala = {j: str(v).strip() for j, v in r.items() if pd.notna(v) and j != 1}
            elif isinstance(c1, str) and c1.strip().startswith("Tahap"):
                sub = c1.strip()
            elif bagian and kepala and pd.notna(c1) and re.fullmatch(r"\d+(\.0)?", str(c1).strip()):
                for j, lab in kepala.items():
                    v = r.iloc[j] if j < len(r) else None
                    if pd.notna(v):
                        baris.append((lembar.strip(), bagian, sub, int(float(c1)), lab, str(v).strip()))
    df = pd.DataFrame(baris, columns=["lembar", "bagian", "sub_bagian", "no", "kolom", "nilai"])
    df.insert(0, "file", nama)
    df.insert(1, "minggu_ke", minggu)
    df.insert(2, "bulan", bulan)
    df.insert(3, "tahun", tahun)
    return df


utama = ambil(UTAMA)
if utama is None:
    print("❌ halaman utama OJK tidak bisa dibuka")
    sys.exit(1)
halaman = sorted({html.unescape(x) for x in re.findall(r'href="([^"]*Ikhtisar-Perkembangan-Emisi[^"]*\.aspx)"', utama)})
print(f"   {len(halaman)} halaman bulan ditautkan")
berkas = {}
for p in halaman:
    t = ambil(DASAR + quote(p, safe="/:%&=?-._~"))
    if t is None:
        continue
    for x in re.findall(r'href="([^"]*Documents/[^"]*\.xlsx)"', t, re.I):
        nama = unquote(html.unescape(x)).rsplit("/", 1)[-1]
        berkas.setdefault(nama, DASAR + quote(unquote(html.unescape(x)), safe="/:"))
    time.sleep(2)
print(f"   {len(berkas)} file xlsx mingguan ditautkan")
if not berkas:
    print("❌ tidak ada file -> struktur halaman berubah?")
    sys.exit(1)

sudah = set()
token = os.environ.get("HF_TOKEN") or (Path("kunci_hf.txt").read_text().strip() if Path("kunci_hf.txt").exists() else None)
if token and not TES:
    from huggingface_hub import HfApi
    sudah = {f.rsplit("/", 1)[-1] for f in HfApi(token=token).list_repo_files("fadli-sparks/quant-data", repo_type="dataset")
             if f.startswith("raw/ojk_emisi/arsip/")}
baru = sorted(set(berkas) - sudah)
if TES:
    baru = baru[-1:]
print(f"   sudah di gudang {len(sudah)}, baru {len(baru)}")
gagal = 0
for nama in baru:
    isi = ambil(berkas[nama], biner=True)
    if isi is None or isi[:2] != b"PK":
        print(f"   ❌ gagal/bukan xlsx: {nama}")
        gagal += 1
        continue
    d = urai(isi, nama)
    ringkas = d.drop_duplicates(["bagian", "no"]).groupby("bagian").size().to_dict()
    print(f"   ✅ {nama}: {len(d)} sel; {ringkas}", flush=True)
    if len(d) < 20:
        print("   ❌ isi terlalu sedikit -> format berubah?")
        gagal += 1
        continue
    if TES:
        print(d[d["bagian"].str.contains("Aksi")].head(8).to_string())
        sys.exit(0)
    (OUT / "arsip").mkdir(parents=True, exist_ok=True)
    (OUT / "urai").mkdir(parents=True, exist_ok=True)
    (OUT / "arsip" / nama).write_bytes(isi)
    d.to_parquet(OUT / "urai" / (nama[:-5] + ".parquet"), index=False)
    time.sleep(2)
if gagal and gagal == len(baru):
    sys.exit(1)
print("✅ selesai")
