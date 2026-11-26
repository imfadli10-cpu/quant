"""
NAB & UNIT PENYERTAAN SETIAP REKSA DANA per akhir bulan (OJK, sumber: laporan harian bank kustodian) -> raw/reksadana_ojk
Halaman PUBLIK resmi: https://reksadana.ojk.go.id/Public/StatistikNABReksadanaPublic.aspx -> tombol 'Lihat' tiap bulan membuka
StatistikNABReksadanaPublicDetail.aspx?year=Y&month=M (tabel DevExpress 10 baris/halaman; pilihan 'Page size: All' tersedia untuk pengunjung
= callback grid 'PAGERONCLICK|PSP-1', persis yang dikirim browser). ojk.go.id tanpa robots.txt. Server lambat (~30 dtk/halaman) -> jeda 3 dtk.
ISI: 1 baris = 1 reksa dana x bulan (TERMASUK reksa dana NAB 0 = bubar/belum aktif -> bebas bias penyintas). Sejak 2013-01 (~710 RD) s/d bulan
  lalu (~2.160 RD). Terbit mulai tanggal 8 bulan berikutnya (menurut OJK) & bisa dikoreksi bank kustodian -> SETIAP VERSI disimpan.
  Arus dana bersih RD i bulan m ~ (unit(m) - unit(m-1)) x NAB/unit -> permintaan investor domestik per jenis (saham, pendapatan tetap, ...).
  NAB RD valas sudah dikonversi OJK ke Rupiah (kurs tengah BI). Total NAB sejak Okt 2021 termasuk 'produk investasi lainnya' (catatan OJK).
SIMPAN:
  raw/reksadana_ojk/bulan/<YYYY-MM>__<sha8>.parquet  bulan, nama_mi, bank_kustodian, produk, tipe, denominasi, nab_rp, unit, waktu_ambil
  raw/reksadana_ojk/indeks.parquet                    bulan, jalur, sha256, jumlah_rd, total_nab, total_unit, waktu_ambil (semua versi)
CEK: jumlah baris = 'N items' halaman; jumlah NAB & unit = baris [Total] resmi (selisih <= 1 Rp per RD); gagal = bulan itu TIDAK disimpan.
MODE: (bawaan) bulan yang BELUM ada di gudang (urut lama->baru, batas waktu ANGGARAN_MENIT, default 45) + segarkan 3 bulan terakhir;
  upload atomik tiap 12 bulan.   --tes : 2 bulan contoh, tanpa simpan.
"""
import hashlib
import io
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

DASAR = "https://reksadana.ojk.go.id/Public/StatistikNABReksadanaPublicDetail.aspx?year={}&month={}"
UID = "ctl00$cpContent2$grdNABReksadana2"
H = {"User-Agent": "quant-data-collector/1.0 (personal research project)"}
REPO = "fadli-sparks/quant-data"
TES = "--tes" in sys.argv
ANGGARAN = float(os.environ.get("ANGGARAN_MENIT", "45")) * 60
SEKARANG = datetime.now(timezone.utc)
WAKTU = pd.Timestamp(SEKARANG).tz_localize(None).floor("s")
MULAI = time.time()
KOLOM = ["nama_mi", "bank_kustodian", "produk", "tipe", "denominasi", "nab_rp", "unit"]


def angka(s):
    s = str(s).strip()
    return float(s.replace(".", "").replace(",", ".")) if re.search(r"\d", s) else float("nan")


def minta(sesi, metode, url, **k):
    for coba in range(4):
        try:
            r = sesi.request(metode, url, headers=H, timeout=(30, 600), **k)
            if r.status_code == 200 and "HttpUnhandledException" not in r.text[:300]:
                return r
            print(f"   ⚠️ HTTP {r.status_code} {r.text[:80]!r}")
            if 400 <= r.status_code < 500 and r.status_code != 429:
                return None
        except requests.RequestException as e:
            print(f"   🔌 {type(e).__name__}")
        time.sleep(15 * (coba + 1))
    return None


def ambil_bulan(th, bl):
    """-> (DataFrame, total_resmi) atau (None, alasan)."""
    sesi = requests.Session()
    url = DASAR.format(th, bl)
    r = minta(sesi, "GET", url)
    if r is None:
        return None, "halaman tidak terbuka"
    m = re.search(r"Page \d+ of \d+ \((\d+) items\)", r.text)
    if not m:
        return None, "kosong (belum terbit?)"
    n_items = int(m.group(1))
    b = BeautifulSoup(r.text, "lxml")
    data = {i.get("name"): i.get("value", "") for i in b.find_all("input") if i.get("name") and i.get("type") == "hidden"}
    kv = data.get(UID + "$DXKVInput", "")
    ser = "12|PAGERONCLICK5|PSP-1"
    data.update({"__CALLBACKID": UID, "__CALLBACKPARAM": f"c0:KV|{len(kv)};{kv};GB|{len(ser)};{ser};"})
    time.sleep(3)
    r2 = minta(sesi, "POST", url, data=data)
    if r2 is None:
        return None, "callback 'All' gagal"
    m2 = re.search(r"'result':'(.*?)'(?:,'|\}\))", r2.text, re.S)
    if not m2:
        return None, "format callback berubah"
    x = m2.group(1).replace("\\r\\n", "\n").replace("\\t", "").replace("\\'", "'")
    rows = [[td.get_text(" ", strip=True) for td in tr.find_all("td", recursive=False)]
            for tr in BeautifulSoup(x, "lxml").find_all("tr", class_=re.compile("dxgvDataRow"))]
    rows = [rw for rw in rows if len(rw) == 7]
    if len(rows) != n_items:
        return None, f"{len(rows)} baris terbaca vs {n_items} items"
    d = pd.DataFrame(rows, columns=KOLOM)
    d["nab_rp"], d["unit"] = d["nab_rp"].map(angka), d["unit"].map(angka)
    # baris [Total] resmi: dari halaman pertama (footer)
    teks = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r.text))
    t = re.search(r"\[Total\]\s*([\d.,]+)\s*([\d.,]+)", teks)
    if not t:
        return None, "baris [Total] tidak ada"
    tot_nab, tot_unit = angka(t.group(1)), angka(t.group(2))
    if abs(d["nab_rp"].sum() - tot_nab) > max(1.0 * len(d), 1e-9 * tot_nab) or abs(d["unit"].sum() - tot_unit) > max(1.0 * len(d), 1e-9 * tot_unit):
        return None, f"jumlah != [Total] (NAB {d['nab_rp'].sum():,.0f} vs {tot_nab:,.0f})"
    d.insert(0, "bulan", pd.Timestamp(th, bl, 1).to_period("M").to_timestamp().to_datetime64())
    d["bulan"] = d["bulan"].astype("datetime64[ns]")
    for k in KOLOM[:5]:
        d[k] = d[k].astype("string")
    d["waktu_ambil"] = WAKTU
    return d, (tot_nab, tot_unit)


def sidik(d):
    isi = d.drop(columns=["waktu_ambil"]).sort_values(KOLOM[:3]).to_csv(index=False).encode()
    return hashlib.sha256(isi).hexdigest()


akhir = (pd.Timestamp(SEKARANG.date()).to_period("M") - 1)
semua_bulan = list(pd.period_range("2013-01", akhir, freq="M"))
if TES:
    for p in [semua_bulan[0], semua_bulan[-1]]:
        t0 = time.time()
        d, info = ambil_bulan(p.year, p.month)
        if d is None:
            print(f"❌ {p}: {info}")
            continue
        print(f"✅ {p}: {len(d)} RD, NAB Rp{info[0] / 1e12:,.2f} T, unit {info[1] / 1e9:,.2f} miliar, {time.time() - t0:.0f} dtk | "
              + ", ".join(f"{k} {v}" for k, v in d['tipe'].value_counts().head(5).items()))
    print("🧪 mode tes: tidak disimpan")
    sys.exit()

from huggingface_hub import CommitOperationAdd, HfApi, hf_hub_download
token = os.environ.get("HF_TOKEN") or Path("kunci_hf.txt").read_text().strip()
api = HfApi(token=token)
try:
    indeks = pd.read_parquet(hf_hub_download(REPO, "raw/reksadana_ojk/indeks.parquet", repo_type="dataset", token=token))
except Exception as e:
    if "404" not in str(e) and "EntryNotFound" not in type(e).__name__:
        raise                                   # gagal membaca indeks yang ADA -> berhenti (jangan timpa riwayat)
    indeks = pd.DataFrame(columns=["bulan", "jalur", "sha256", "jumlah_rd", "total_nab", "total_unit", "waktu_ambil"])
ada = set(pd.to_datetime(indeks["bulan"]).dt.to_period("M")) if len(indeks) else set()
sidik_ada = set(indeks["sha256"]) if len(indeks) else set()
antre = [p for p in semua_bulan if p not in ada] + [p for p in semua_bulan[-3:] if p in ada]
print(f"📋 {len(ada)} bulan sudah di gudang; antre {len(antre)} (belum ada {len([p for p in antre if p not in ada])} + segarkan 3 terakhir)")

folder = Path("data/raw/reksadana_ojk/bulan")
folder.mkdir(parents=True, exist_ok=True)
ops, baris_indeks, gagal = [], [], []


def unggah():
    global ops, baris_indeks, indeks
    if not ops:
        return
    baru = pd.DataFrame(baris_indeks)
    gab = pd.concat([indeks, baru], ignore_index=True) if len(indeks) else baru
    gab["bulan"] = pd.to_datetime(gab["bulan"]).astype("datetime64[ns]")
    gab["waktu_ambil"] = pd.to_datetime(gab["waktu_ambil"]).astype("datetime64[ns]")
    for k in ("jalur", "sha256"):
        gab[k] = gab[k].astype("string")
    gab = gab.sort_values(["bulan", "waktu_ambil"]).reset_index(drop=True)
    gab.to_parquet("data/raw/reksadana_ojk/indeks.parquet", index=False)
    semua_ops = ops + [CommitOperationAdd(path_in_repo="raw/reksadana_ojk/indeks.parquet",
                                          path_or_fileobj="data/raw/reksadana_ojk/indeks.parquet")]
    for coba in range(4):
        try:
            api.create_commit(repo_id=REPO, repo_type="dataset", operations=semua_ops,
                              commit_message=f"Reksa dana OJK {SEKARANG:%Y-%m-%d}: {len(ops)} versi bulan")
            break
        except Exception as e:
            if coba == 3:
                raise
            print(f"   ⚠️ upload gagal ({type(e).__name__}), coba lagi")
            time.sleep(60 * (coba + 1))
    print(f"☁️  {len(ops)} versi bulan + indeks ({len(gab)} baris) di gudang")
    indeks, ops, baris_indeks = gab, [], []


for p in antre:
    if time.time() - MULAI > ANGGARAN:
        print(f"⏱️ anggaran {ANGGARAN / 60:.0f} menit habis; sisanya run berikutnya")
        break
    d, info = ambil_bulan(p.year, p.month)
    if d is None:
        print(f"   ❌ {p}: {info}")
        gagal.append(f"{p}: {info}")
        continue
    sh = sidik(d)
    if sh in sidik_ada:
        print(f"   = {p}: tidak berubah ({len(d)} RD)")
        continue
    jalur = f"raw/reksadana_ojk/bulan/{p}__{sh[:8]}.parquet"
    lokal = folder / f"{p}__{sh[:8]}.parquet"
    d.to_parquet(lokal, index=False)
    ops.append(CommitOperationAdd(path_in_repo=jalur, path_or_fileobj=str(lokal)))
    baris_indeks.append({"bulan": p.to_timestamp(), "jalur": jalur, "sha256": sh, "jumlah_rd": len(d), "total_nab": info[0],
                         "total_unit": info[1], "waktu_ambil": WAKTU})
    sidik_ada.add(sh)
    print(f"   ✅ {p}: {len(d)} RD, NAB Rp{info[0] / 1e12:,.2f} T{' (VERSI BARU / revisi)' if p in ada else ''}  [{(time.time() - MULAI) / 60:.0f} mnt]")
    if len(ops) >= 12:
        unggah()
    time.sleep(3)
unggah()
# 'kosong (belum terbit?)' untuk bulan terakhir = normal sebelum tgl ~8; selain itu = masalah
masalah = [g for g in gagal if not (g.startswith(str(akhir)) and "kosong" in g)]
if masalah:
    print("❌ " + " | ".join(masalah))
    sys.exit(1)
