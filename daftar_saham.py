"""
Daftar kode saham IDX bersama untuk semua collector & paper trading.

= ref/daftar_saham.xlsx (daftar awal, diunduh manual sekali)  GABUNG  ref/daftar_saham_tambahan.csv (kode baru yang
  muncul di daftar Yahoo setelahnya, ditambahkan otomatis oleh kumpul_daftar_idx.py; tidak pernah dikurangi).
File lokal dipakai kalau ada (di server, kumpul_daftar_idx.py menulisnya lebih dulu), kalau tidak diunduh dari gudang.
"""
import os
from pathlib import Path

import pandas as pd

REPO = "fadli-sparks/quant-data"


def _berkas(nama):
    lokal = Path("data/ref") / nama
    if lokal.exists():
        return lokal
    from huggingface_hub import HfApi, hf_hub_download
    token = os.environ.get("HF_TOKEN") or Path("kunci_hf.txt").read_text().strip()
    if not HfApi(token=token).file_exists(REPO, f"ref/{nama}", repo_type="dataset"):
        return None
    return Path(hf_hub_download(REPO, f"ref/{nama}", repo_type="dataset", token=token))


def wikidata_idx():
    """Peta perusahaan yang tercatat di Bursa Efek Indonesia (Wikidata Q1661737): kode, nama, artikel Wikipedia
    (judul id & en), tanggal mulai tercatat. Hasil: DataFrame (1 baris per kode)."""
    import time
    from urllib.parse import unquote
    import requests
    q = """SELECT ?perusahaan ?perusahaanLabel ?kode ?mulai ?artikel_id ?artikel_en WHERE {
      ?perusahaan p:P414 ?bursa . ?bursa ps:P414 wd:Q1661737 .
      OPTIONAL { ?bursa pq:P249 ?kode . } OPTIONAL { ?bursa pq:P580 ?mulai . }
      OPTIONAL { ?artikel_id schema:about ?perusahaan ; schema:isPartOf <https://id.wikipedia.org/> . }
      OPTIONAL { ?artikel_en schema:about ?perusahaan ; schema:isPartOf <https://en.wikipedia.org/> . }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "id,en". } }"""
    header = {"User-Agent": "quant-data-collector/1.0 (personal research project)",
              "Accept": "application/sparql-results+json"}
    for percobaan in range(4):
        try:
            r = requests.get("https://query.wikidata.org/sparql", params={"query": q}, headers=header, timeout=120)
            r.raise_for_status()
            break
        except requests.exceptions.RequestException as e:
            print(f"   🔌 Wikidata: {type(e).__name__}, coba lagi...")
            time.sleep(20 * (percobaan + 1))
    else:
        raise RuntimeError("Wikidata gagal 4x")
    d = pd.DataFrame([{k: v["value"] for k, v in b.items()} for b in r.json()["results"]["bindings"]])
    d = d.reindex(columns=["perusahaan", "perusahaanLabel", "kode", "mulai", "artikel_id", "artikel_en"])
    d["kode"] = (d["kode"].fillna("").str.upper().str.replace(".JK", "", regex=False)
                 .str.replace("IDX:", "", regex=False).str.strip())
    d = d[d["kode"].str.fullmatch(r"[A-Z]{4}")]              # kode saham IDX = 4 huruf (buang reksa dana 'R-...')
    for k in ["artikel_id", "artikel_en"]:
        d[k] = d[k].fillna("").map(lambda u: unquote(u.rsplit("/wiki/", 1)[-1]) if u else "")
    d["mulai"] = pd.to_datetime(d["mulai"], errors="coerce", utc=True).dt.tz_localize(None).astype("datetime64[ns]")
    d = d.rename(columns={"perusahaan": "qid", "perusahaanLabel": "nama"})
    d["qid"] = d["qid"].str.rsplit("/", n=1).str[-1]
    return d.drop_duplicates("kode").reset_index(drop=True)


def kode_idx(akhiran=".JK", termasuk_etf=False):
    """Kode IDX (urut), mis. ['AALI.JK', ...]. akhiran='' untuk kode polos.
    termasuk_etf=False (bawaan): hanya SAHAM -> dipakai paper trading & fundamental (semesta S2 tetap identik riset #12).
    termasuk_etf=True: saham + ETF yang tercatat di IDX -> dipakai collector harga harian."""
    d = pd.read_excel(_berkas("daftar_saham.xlsx"), dtype=str, keep_default_na=False)   # 'NA' jangan jadi kosong
    kolom = [c for c in d.columns if "kode" in str(c).lower()][0]
    kode = {k.strip() for k in d[kolom] if k.strip()}
    tambahan = _berkas("daftar_saham_tambahan.csv")
    if tambahan is not None:
        t = pd.read_csv(tambahan, dtype=str, keep_default_na=False)
        if "jenis" in t.columns and not termasuk_etf:
            t = t[t["jenis"] != "etf"]
        kode |= {k.strip() for k in t["kode"] if k.strip()}
    return sorted(f"{k}{akhiran}" for k in kode)
