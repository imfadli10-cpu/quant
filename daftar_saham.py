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


def kode_idx(akhiran=".JK"):
    """Semua kode saham IDX (urut), mis. ['AALI.JK', ...]. akhiran='' untuk kode polos."""
    d = pd.read_excel(_berkas("daftar_saham.xlsx"), dtype=str, keep_default_na=False)   # 'NA' jangan jadi kosong
    kolom = [c for c in d.columns if "kode" in str(c).lower()][0]
    kode = {k.strip() for k in d[kolom] if k.strip()}
    tambahan = _berkas("daftar_saham_tambahan.csv")
    if tambahan is not None:
        t = pd.read_csv(tambahan, dtype=str, keep_default_na=False)
        kode |= {k.strip() for k in t["kode"] if k.strip()}
    return sorted(f"{k}{akhiran}" for k in kode)
