"""
Transaksi ORANG DALAM perusahaan AS (SEC Form 3/4/5, "Insider Transactions Data Sets"), per kuartal sejak 2006.

Apa ini: direktur, eksekutif (CEO/CFO), dan pemegang >10% wajib melapor ke SEC setiap membeli/menjual saham
perusahaannya sendiri. Riset akademik: PEMBELIAN orang dalam (kode P) dengan uang pribadi cenderung diikuti
kenaikan harga beberapa bulan berikutnya. Data mencakup perusahaan yang sudah mati (tanpa survivorship bias).

Isi per kuartal (1 baris = 1 transaksi saham biasa / non-derivatif), gabungan 3 tabel SEC:
  tanggal_lapor (FILING_DATE = saat informasi PUBLIK -> pakai ini di riset!), tanggal_transaksi, jenis_form,
  cik_emiten, nama_emiten, kode (ticker), rencana_10b5_1 (1 = penjualan terjadwal, bukan sinyal),
  pemilik (nama, cik, hubungan, jabatan; digabung "; " kalau > 1 pelapor), kode_transaksi (P=beli, S=jual, A=hibah,
  M=konversi opsi, F=bayar pajak, G=hadiah, ...), lembar, harga, beli_atau_jual (A/D), lembar_setelah, langsung_atau_tidak.
  Alamat pelapor SENGAJA tidak disimpan (data pribadi, tidak berguna untuk riset).

Sumber: halaman indeks SEC (tautan dibaca dari halaman, karena lokasi file pernah pindah di 2026).
User-Agent wajib nama+email: secret SEC_USER_AGENT / file kunci_sec.txt.

Cara pakai:
  python kumpul_insider_sec.py         -> semua kuartal yang belum ada di gudang + 2 kuartal terbaru (ditimpa,
                                          karena SEC kadang memperbarui) -> upload per kuartal ke raw/insider_sec/
  python kumpul_insider_sec.py --tes   -> 1 kuartal terbaru + 1 kuartal tertua, tanpa simpan/upload
"""
import io
import os
import re
import sys
import time
import zipfile
from pathlib import Path

import pandas as pd
import requests

REPO = "fadli-sparks/quant-data"
INDEKS = "https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets"
FOLDER_REPO = "raw/insider_sec"
TES = "--tes" in sys.argv
UA = os.environ.get("SEC_USER_AGENT") or Path("kunci_sec.txt").read_text().strip()
sesi = requests.Session()
sesi.headers.update({"User-Agent": UA, "Accept-Encoding": "gzip, deflate"})


def ambil(url, sebagai_teks=False):
    for percobaan in range(5):
        try:
            r = sesi.get(url, timeout=180)
            if r.status_code == 429:
                time.sleep(30)
                continue
            r.raise_for_status()
            return r.text if sebagai_teks else r.content
        except requests.exceptions.RequestException as e:
            print(f"   🔌 {type(e).__name__}, coba lagi...")
            time.sleep(10 * (percobaan + 1))
    raise RuntimeError(f"Gagal mengunduh {url}")


def daftar_kuartal():
    """{'2026q3': url, ...} dibaca dari halaman indeks SEC."""
    html = ambil(INDEKS, sebagai_teks=True)
    tautan = re.findall(r'href="([^"]*?(\d{4}q[1-4])_form345\.zip)"', html)
    hasil = {q: ("https://www.sec.gov" + u if u.startswith("/") else u) for u, q in tautan}
    if len(hasil) < 70:
        raise RuntimeError(f"Halaman indeks SEC berubah? Hanya {len(hasil)} kuartal ditemukan")
    return dict(sorted(hasil.items()))


def baca_tsv(z, nama, kolom):
    """Kolom yang tidak ada di arsip lama (mis. AFF10B5ONE baru ada sejak ~2023) diisi kosong."""
    nama_asli = next(n for n in z.namelist() if n.upper() == nama)
    d = pd.read_csv(z.open(nama_asli), sep="\t", dtype=str, keep_default_na=False,
                    usecols=lambda c: c in kolom, quoting=3, on_bad_lines="warn")
    return d.reindex(columns=kolom, fill_value="")


def tanggal(s):
    return pd.to_datetime(s.str.strip().str.title(), format="%d-%b-%Y", errors="coerce").astype("datetime64[ns]")


def olah(isi_zip):
    z = zipfile.ZipFile(io.BytesIO(isi_zip))
    sub = baca_tsv(z, "SUBMISSION.TSV", ["ACCESSION_NUMBER", "FILING_DATE", "PERIOD_OF_REPORT", "DOCUMENT_TYPE",
                                         "ISSUERCIK", "ISSUERNAME", "ISSUERTRADINGSYMBOL", "AFF10B5ONE"])
    pem = baca_tsv(z, "REPORTINGOWNER.TSV", ["ACCESSION_NUMBER", "RPTOWNERCIK", "RPTOWNERNAME",
                                            "RPTOWNER_RELATIONSHIP", "RPTOWNER_TITLE"])
    trx = baca_tsv(z, "NONDERIV_TRANS.TSV", ["ACCESSION_NUMBER", "NONDERIV_TRANS_SK", "SECURITY_TITLE", "TRANS_DATE",
                                            "TRANS_CODE", "TRANS_SHARES", "TRANS_PRICEPERSHARE",
                                            "TRANS_ACQUIRED_DISP_CD", "SHRS_OWND_FOLWNG_TRANS",
                                            "DIRECT_INDIRECT_OWNERSHIP"])
    # Satu laporan bisa punya beberapa pelapor (mis. dana + manajernya): gabungkan jadi satu baris
    pem = pem.groupby("ACCESSION_NUMBER", as_index=False).agg(
        {k: lambda s: "; ".join(dict.fromkeys(x for x in s if x)) for k in
         ["RPTOWNERCIK", "RPTOWNERNAME", "RPTOWNER_RELATIONSHIP", "RPTOWNER_TITLE"]})
    df = trx.merge(sub, on="ACCESSION_NUMBER", how="left").merge(pem, on="ACCESSION_NUMBER", how="left")
    df = df.rename(columns={
        "ACCESSION_NUMBER": "no_laporan", "NONDERIV_TRANS_SK": "id_transaksi", "SECURITY_TITLE": "jenis_efek",
        "FILING_DATE": "tanggal_lapor", "PERIOD_OF_REPORT": "periode_laporan", "TRANS_DATE": "tanggal_transaksi",
        "DOCUMENT_TYPE": "jenis_form", "ISSUERCIK": "cik_emiten", "ISSUERNAME": "nama_emiten",
        "ISSUERTRADINGSYMBOL": "kode", "AFF10B5ONE": "rencana_10b5_1", "RPTOWNERCIK": "cik_pemilik",
        "RPTOWNERNAME": "nama_pemilik", "RPTOWNER_RELATIONSHIP": "hubungan", "RPTOWNER_TITLE": "jabatan",
        "TRANS_CODE": "kode_transaksi", "TRANS_SHARES": "lembar", "TRANS_PRICEPERSHARE": "harga",
        "TRANS_ACQUIRED_DISP_CD": "beli_atau_jual", "SHRS_OWND_FOLWNG_TRANS": "lembar_setelah",
        "DIRECT_INDIRECT_OWNERSHIP": "langsung_atau_tidak"})
    for k in ["tanggal_lapor", "periode_laporan", "tanggal_transaksi"]:
        df[k] = tanggal(df[k].fillna(""))
    for k in ["lembar", "harga", "lembar_setelah"]:
        df[k] = pd.to_numeric(df[k], errors="coerce").astype("float64")
    df["kode"] = df["kode"].fillna("").str.strip().str.upper()
    # SEC menulis penanda 10b5-1 tidak seragam ("1"/"true", "0"/"false"); kosong = kolom belum ada (sebelum ~2023)
    df["rencana_10b5_1"] = (df["rencana_10b5_1"].fillna("").str.strip().str.lower()
                            .map({"1": "1", "true": "1", "0": "0", "false": "0"}).fillna(""))
    teks = [c for c in df.columns if df[c].dtype == object or str(df[c].dtype).startswith("str")]
    for k in teks:
        df[k] = df[k].fillna("").astype("string")
    urutan = ["no_laporan", "id_transaksi", "tanggal_lapor", "tanggal_transaksi", "periode_laporan", "jenis_form",
              "cik_emiten", "nama_emiten", "kode", "rencana_10b5_1", "cik_pemilik", "nama_pemilik", "hubungan",
              "jabatan", "jenis_efek", "kode_transaksi", "lembar", "harga", "beli_atau_jual", "lembar_setelah",
              "langsung_atau_tidak"]
    return df[urutan]


def ringkas(df):
    beli = (df["kode_transaksi"] == "P").sum()
    jual = (df["kode_transaksi"] == "S").sum()
    return (f"{len(df):,} transaksi, {df['kode'].nunique():,} kode, lapor {df['tanggal_lapor'].min().date()} s/d "
            f"{df['tanggal_lapor'].max().date()}, beli(P) {beli:,}, jual(S) {jual:,}, "
            f"tanggal kosong {df['tanggal_lapor'].isna().sum()}")


kuartal = daftar_kuartal()
print(f"📋 {len(kuartal)} kuartal tersedia di SEC: {next(iter(kuartal))} s/d {list(kuartal)[-1]}")

if TES:
    for q in [list(kuartal)[0], list(kuartal)[-1]]:
        df = olah(ambil(kuartal[q]))
        print(f"🧪 {q}: {ringkas(df)}")
        print(df.dtypes.to_string())
        print(df[df["kode_transaksi"] == "P"].head(3).T.to_string())
    sys.exit()

from huggingface_hub import HfApi
token = os.environ.get("HF_TOKEN") or Path("kunci_hf.txt").read_text().strip()
api = HfApi(token=token)
sudah = {Path(f).stem for f in api.list_repo_files(REPO, repo_type="dataset") if f.startswith(FOLDER_REPO + "/")}
terbaru = set(list(kuartal)[-2:])                    # selalu diperbarui (SEC kadang menambah laporan telat)
folder = Path("data/raw/insider_sec")
folder.mkdir(parents=True, exist_ok=True)
PER_UPLOAD = 10            # Hugging Face membatasi jumlah commit (429): upload 10 kuartal sekaligus


def upload_kelompok(daftar):
    """Upload beberapa file kuartal dalam SATU commit; kalau dibatasi (429), tunggu 2 menit lalu coba lagi."""
    for percobaan in range(6):
        try:
            api.upload_folder(folder_path=str(folder), path_in_repo=FOLDER_REPO, repo_id=REPO, repo_type="dataset",
                              allow_patterns=[f"{q}.parquet" for q in daftar],
                              commit_message=f"Insider SEC {daftar[0]}..{daftar[-1]}")
            print(f"   ☁️  ter-upload: {daftar[0]} s/d {daftar[-1]} ({len(daftar)} kuartal)")
            return True
        except Exception as e:
            print(f"   ⏳ upload gagal ({type(e).__name__}: {str(e)[:80]}), tunggu 2 menit... ({percobaan + 1}/6)")
            time.sleep(120)
    return False


gagal, antre = [], []
for q, url in kuartal.items():
    if q in sudah and q not in terbaru:
        continue
    try:
        df = olah(ambil(url))
    except Exception as e:
        print(f"⚠️  {q}: {type(e).__name__}: {str(e)[:100]}")
        gagal.append(q)
        continue
    file = folder / f"{q}.parquet"
    df.to_parquet(file, index=False)
    print(f"✅ {q}: {ringkas(df)} ({file.stat().st_size / 1e6:.1f} MB)")
    antre.append(q)
    if len(antre) >= PER_UPLOAD:
        if not upload_kelompok(antre):
            gagal += antre
        antre = []
    time.sleep(1)                                    # sopan ke server SEC (batas 10 permintaan/detik)
if antre and not upload_kelompok(antre):
    gagal += antre
if gagal:
    print(f"❌ {len(gagal)} kuartal gagal: {gagal}")
    sys.exit(1)
print("🎉 Selesai")
