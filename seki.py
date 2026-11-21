"""
Pengurai tabel SEKI Bank Indonesia (file .xls dari kumpul_seki.py) -> seri BULANAN.

Tabel SEKI terbagi ke beberapa lembar per periode (mis. 'Th 2001-2003', 'Th 2004-2009', 'I.1') dengan DUA format header:
  (a) satu baris berisi TANGGAL bulanan (datetime) per kolom (lembar lama; kadang ada sel 1900-01-01 = sampah -> diabaikan);
  (b) baris TAHUN (hanya terisi di awal tiap tahun -> diisi ke kanan) + baris NAMA BULAN ('Jan', 'Mei', 'Sep*' ...) (lembar baru).
Label baris dicari di 4 kolom pertama (posisinya bergeser antar lembar). Lembar yang lebih belakang menimpa bulan yang sama
(revisi terbaru menang). Angka '-' / teks -> kosong.

Pakai:
  from seki import seri_bulanan
  m2 = seri_bulanan("data/raw/seki/2026-11-21/TABEL1_1.xls", r"uang beredar luas|broad money")
"""
import re
import warnings

import numpy as np
import pandas as pd

BULAN = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "mei": 5, "jun": 6, "jul": 7, "aug": 8, "agt": 8, "agu": 8,
         "agus": 8, "ags": 8, "sep": 9, "oct": 10, "okt": 10, "nov": 11, "dec": 12, "des": 12}


def _tanggal(c):
    if hasattr(c, "year") and hasattr(c, "month") and not pd.isna(c) and 1950 <= c.year <= 2100:
        return pd.Timestamp(c.year, c.month, 1)
    return None


def _nama_bulan(c):
    if not isinstance(c, str):
        return None
    k = re.sub(r"[^a-z]", "", c.strip().lower())
    return BULAN.get(k[:4]) or BULAN.get(k[:3]) if 3 <= len(k) <= 9 else None


def _tahun(c):
    m = re.match(r"^\s*(19[5-9]\d|20\d\d)", str(c)) if pd.notna(c) else None
    return int(m.group(1)) if m else None


def peta_kolom(v):
    """(baris_header_terakhir, {kolom: Timestamp bulan}) atau (None, {})."""
    batas = min(15, len(v))
    # Format (b): baris nama bulan + baris tahun di atasnya
    for i in range(1, batas):
        bl = [_nama_bulan(c) for c in v.iloc[i].tolist()]
        if sum(b is not None for b in bl) >= 6:
            for a in range(i - 1, max(-1, i - 4), -1):
                th = [_tahun(c) if not isinstance(c, str) or re.match(r"^\s*\d{4}", c) else None for c in v.iloc[a].tolist()]
                if sum(t is not None for t in th) == 0:
                    continue
                # Kelompokkan kolom bulan jadi BLOK tahun: blok baru tiap kali nomor bulan TURUN (Des -> Jan).
                # Label tahun bisa di kolom pertama ATAU terakhir blok (lembar 'I.1' menaruhnya di kolom terakhir)
                # -> tahun blok = label tahun yang berada di rentang kolom blok itu.
                kol = [(j, b) for j, b in enumerate(bl) if b is not None]
                blok, kini = [], []
                for j, b in kol:
                    if kini and b <= kini[-1][1]:
                        blok.append(kini)
                        kini = []
                    kini.append((j, b))
                if kini:
                    blok.append(kini)
                peta = {}
                for bk in blok:
                    j0, j1 = bk[0][0], bk[-1][0]
                    label = [th[j] for j in range(j0, j1 + 1) if th[j] is not None]
                    if len(set(label)) == 1:                       # tepat satu tahun di dalam blok -> pasti
                        for j, b in bk:
                            peta[j] = pd.Timestamp(label[0], b, 1)
                if len(peta) >= 6:
                    return i, peta
    # Format (a): baris tanggal
    terbaik, peta_terbaik = None, {}
    for i in range(batas):
        peta = {j: t for j, c in enumerate(v.iloc[i].tolist()) if (t := _tanggal(c)) is not None}
        if len(peta) >= 6 and len(peta) > len(peta_terbaik):
            terbaik, peta_terbaik = i, peta
    return terbaik, peta_terbaik


def seri_bulanan(file, pola_label):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        lembar = pd.read_excel(file, header=None, engine="xlrd", sheet_name=None)
    hasil = {}
    for nama, v in lembar.items():
        i, peta = peta_kolom(v)
        if i is None:
            continue
        for r in range(i + 1, len(v)):
            label = " ".join(str(v.iat[r, k]) for k in range(min(4, v.shape[1]))
                             if isinstance(v.iat[r, k], str))
            if re.search(pola_label, label, re.I):
                for j, t in peta.items():
                    x = pd.to_numeric(v.iat[r, j], errors="coerce")
                    if pd.notna(x):
                        hasil[t] = float(x)
                break                                     # baris pertama yang cocok di lembar ini
    return pd.Series(hasil, dtype=float).sort_index()


if __name__ == "__main__":
    import glob
    f = sorted(glob.glob("data/raw/seki/*/TABEL1_1.xls"))[-1]
    for nama, pola in [("M2", r"uang beredar luas|broad money"), ("M1", r"uang beredar sempit|narrow money")]:
        s = seri_bulanan(f, pola)
        bolong = pd.date_range(s.index.min(), s.index.max(), freq="MS").difference(s.index)
        print(f"{nama}: {len(s)} bulan {s.index.min():%Y-%m} s/d {s.index.max():%Y-%m}, bolong {len(bolong)} | "
              f"2003-12 {s.get(pd.Timestamp('2003-12-01'), np.nan):,.0f} | 2018-12 {s.get(pd.Timestamp('2018-12-01'), np.nan):,.0f} | "
              f"terakhir {s.iloc[-1]:,.0f}")
        lompat = s.pct_change().abs()
        print(f"   perubahan bulanan > 10%: {lompat[lompat > 0.10].round(3).to_dict()}")
