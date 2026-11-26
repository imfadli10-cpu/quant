"""
Pengurai file KEPEMILIKAN SBN Rupiah yang Dapat Diperdagangkan (DJPPR Kemenkeu) -> format panjang.
Dipakai kumpul_kepemilikan_sbn.py. Format file BERUBAH antar era (dicek 26 Nov 2026 pada 34 lampiran):
  - Excel 2003-2006: bulanan, hanya SUN (satu kolom per tanggal).
  - Excel 2007-2015: lembar tahunan 2007-2013 bulanan (satu kolom per tanggal, label dwibahasa "Indonesia/ English"),
    lembar 2014 & bulan-bulan 2015 harian; sebagian dgn sub-kolom SUN/SBSN/TOTAL.
  - Excel 2016-2024: satu lembar per bulan, tiap tanggal 3 sub-kolom SUN / SBSN / TOTAL.
  - PDF 2025-2026: satu file per bulan, 2-3 halaman; tiap halaman <= 8 tanggal x (SUN, SBSN, TOTAL); halaman ganjil label Indonesia
    di KIRI, halaman berikutnya label Inggris di KANAN. Angka: "1 ,023.15" (spasi nyasar), "(39.51)" = negatif, "-" = 0.
Hanya bagian "A. Dalam Triliun Rupiah" yang diambil (bagian B = persen, bisa dihitung ulang).
Kolom keluaran: tanggal, label (teks asli), kategori (baku), jenis (SUN/SBSN/TOTAL), nilai (Rp triliun), lembar.
"""
import re

import numpy as np
import pandas as pd

# urutan penting: yang lebih spesifik dulu
POLA_KATEGORI = [
    ("non_residen_pemerintah_asing", r"pemerintah\s*&\s*bank\s*sentral|foreign\s*gov|central\s*bank\(s\)"),
    ("non_residen", r"non\s*-?\s*resid|asing|foreign"),
    ("bi_gross", r"bank\s*indonesia\s*\(gross\)"),
    ("bi_net", r"^\s*bank\s*indonesia"),                # 'Bank Indonesia (net, tidak termasuk ... operasi moneter ...)'
    ("bi_operasi_moneter", r"operasi\s*moneter|monetary\s*operation"),
    ("kemenkeu", r"kementerian\s*keuangan|ministry\s*of\s*finance"),
    ("institusi_negara", r"institusi\s*negara|institusi\s*pemerintah|government\s*institution"),
    ("bank_syariah", r"syariah|islamic"),
    ("bank_konvensional", r"konvensional|conventional"),
    ("bank_bumn_rekap", r"bumn|state\s*banks"),
    ("bank_swasta_rekap", r"swasta\s*rekap|private\s*banks"),
    ("bank_non_rekap", r"non\s*rekap|non\s*recap"),
    ("bpd_rekap", r"bpd|regional\s*banks"),
    ("non_bank", r"^\s*non\s*-?\s*bank"),
    ("bank", r"^\s*bank\s*\*?\s*(/|$)|^\s*bank\s*\*\s*$|^\s*banks?\s*$"),
    ("reksadana", r"reksa\s*dana|mutual\s*fund"),
    ("asuransi_dana_pensiun", r"asuransi\s*dan\s*dana\s*pensiun|insurance\s*(company\s*)?and\s*pension"),
    ("asuransi", r"asuransi|insurance"),
    ("dana_pensiun", r"dana\s*pensiun|pension"),
    ("individu", r"individu|individual"),
    ("sekuritas", r"sekuritas|securities\s*company"),
    ("lainnya", r"lain|others"),
    ("total", r"^\s*total|jumlah"),
]


KOREKSI = []      # (file, lembar, tanggal_asli, tanggal_koreksi)


def kategori(label):
    t = str(label).lower().replace("\n", " ")
    for nama, pola in POLA_KATEGORI:
        if re.search(pola, t):
            return nama
    return "lain_tak_dikenal"


def _tanggal(x):
    if isinstance(x, (pd.Timestamp, np.datetime64)) or hasattr(x, "year"):
        try:
            return pd.Timestamp(x).normalize()
        except (ValueError, TypeError):
            return None
    return None


def _angka(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return np.nan
    if isinstance(x, (int, float, np.number)) and not isinstance(x, bool):
        return float(x)
    t = str(x).strip().replace(" ", "")
    if t in ("-", "–", ""):
        return 0.0 if t else np.nan
    neg = t.startswith("(") and t.endswith(")")
    t = t.strip("()").replace(",", "")
    try:
        v = float(t)
    except ValueError:
        return np.nan
    return -v if neg else v


def urai_excel(jalur, jenis_bawaan="TOTAL"):
    keluar = []
    for lembar, d in pd.read_excel(jalur, sheet_name=None, header=None).items():
        d = d.dropna(how="all", axis=1)
        d.columns = range(d.shape[1])
        if d.empty:
            continue
        # baris header = baris pertama dgn >= 1 sel tanggal (selain kolom label)
        hdr = None
        for r in range(min(15, len(d))):
            if sum(_tanggal(v) is not None for v in d.iloc[r, 1:]) >= 1:
                hdr = r
                break
        if hdr is None:
            continue
        kol_tgl = {c: _tanggal(d.iat[hdr, c]) for c in range(1, d.shape[1]) if _tanggal(d.iat[hdr, c]) is not None}
        # salah ketik tahun di sumber (mis. lembar Des 2022 berisi 30-12-2023): tanggal harus NAIK antar kolom;
        # tanggal yang merusak urutan diganti tahunnya mengikuti kolom tetangga (dicatat di KOREKSI)
        kk = sorted(kol_tgl)
        for n, c in enumerate(kk):
            sebelum = kol_tgl[kk[n - 1]] if n > 0 else None
            sesudah = kol_tgl[kk[n + 1]] if n + 1 < len(kk) else None
            t0 = kol_tgl[c]
            rusak = ((sebelum is not None and (t0 <= sebelum or (t0 - sebelum).days > 200)) or
                     (sesudah is not None and (t0 >= sesudah or (sesudah - t0).days > 200)))
            if rusak:
                for acuan in (sebelum, sesudah):
                    if acuan is None:
                        continue
                    try:
                        calon = t0.replace(year=acuan.year)
                    except ValueError:
                        continue
                    if ((sebelum is None or sebelum < calon <= sebelum + pd.Timedelta(days=200)) and
                            (sesudah is None or calon < sesudah <= calon + pd.Timedelta(days=200))):
                        KOREKSI.append((str(jalur), lembar, t0.date(), calon.date()))
                        kol_tgl[c] = calon
                        break
        # sub-kolom SUN/SBSN/TOTAL (baris sesudah header)
        sub = {}
        bawah = d.iloc[hdr + 1] if hdr + 1 < len(d) else None
        if bawah is not None and any(str(v).strip().upper() in ("SUN", "SBSN", "TOTAL") for v in bawah):
            tgl_kini = None
            for c in range(1, d.shape[1]):
                if c in kol_tgl:
                    tgl_kini = kol_tgl[c]
                j = str(bawah.iloc[c]).strip().upper()
                if tgl_kini is not None and j in ("SUN", "SBSN", "TOTAL"):
                    sub[c] = (tgl_kini, j)
            mulai = hdr + 2
        else:
            judul = " ".join(str(v) for v in d.iloc[:hdr, 0].dropna())
            jenis = "SUN" if re.search(r"\(SUN\)|Surat Utang Negara", judul) and "SBN" not in judul.replace("SUN", "") else jenis_bawaan
            sub = {c: (t, jenis) for c, t in kol_tgl.items()}
            mulai = hdr + 1
        label_lalu = None
        for r in range(mulai, len(d)):
            lab = d.iat[r, 0]
            teks = "" if pd.isna(lab) else str(lab).strip()
            if re.match(r"^\s*B\s*\.", teks) or re.search(r"dalam\s*persen|in\s*percent", teks, re.I):
                break                                              # bagian B (persen) -> berhenti
            nilai = {c: _angka(d.iat[r, c]) for c in sub}
            if not teks or all(np.isnan(v) for v in nilai.values()):
                continue
            label_lalu = teks
            for c, (t, j) in sub.items():
                if not np.isnan(nilai[c]):
                    keluar.append((t, teks, j, nilai[c], lembar))
            if kategori(teks) == "total":
                break                                              # akhir bagian A (bagian B = persen)
    h = pd.DataFrame(keluar, columns=["tanggal", "label", "jenis", "nilai", "lembar"])
    h["kategori"] = h["label"].map(kategori)
    return h


URUTAN_PDF = ["bank", "bank_konvensional", "bank_syariah", "institusi_negara", "bi_net", "bi_gross", "bi_operasi_moneter",
              "non_bank", "reksadana", "asuransi_dana_pensiun", "non_residen", "non_residen_pemerintah_asing", "individu",
              "lainnya", "total"]
TGL = r"\d{1,2}-[A-Za-z]{3}-\d{2}"
BARIS_BARU = chr(10)


def angka_pdf(sel):
    """'1 ,023.15' / '1.209,49' / '(39.51)' / '-' -> float. Format desimal dikenali per sel."""
    t = str(sel).replace(" ", "").strip()
    if t in ("-", "–"):
        return 0.0
    neg = t.startswith("(") and t.endswith(")")
    t = t.strip("()")
    if re.search(r",\d{1,2}$", t):            # format Indonesia: 1.209,49
        t = t.replace(".", "").replace(",", ".")
    else:                                       # format Inggris: 1,209.49
        t = t.replace(",", "")
    v = float(t)
    return -v if neg else v


def cek_identitas(v, toleransi=0.05):
    """v: dict kategori -> array nilai (per kolom). Kembalikan selisih maksimum identitas (Rp triliun)."""
    s = [v["bank"] - v["bank_konvensional"] - v["bank_syariah"],
         v["non_bank"] - v["reksadana"] - v["asuransi_dana_pensiun"] - v["non_residen"] - v["individu"] - v["lainnya"],
         v["total"] - v["bank"] - v["institusi_negara"] - v["non_bank"],
         v["bi_net"] - (v["bi_gross"] - v["bi_operasi_moneter"])]
    return max(float(np.max(np.abs(x))) for x in s)


def urai_pdf(jalur):
    """Tabel pertama tiap halaman = bagian A (triliun). Sel yang memuat beberapa baris (dipisah '\n') dipecah; urutan baris
    dicocokkan dgn URUTAN_PDF lalu DIVERIFIKASI lewat identitas hitung (gagal -> ValueError, bukan tebakan)."""
    import pdfplumber
    keluar = []
    with pdfplumber.open(jalur) as pdf:
        for pg in pdf.pages:
            tabel = pg.extract_tables()
            if not tabel:
                continue
            t = tabel[0]
            hdr, sub = t[0], t[1]
            kol_tgl, tgl_kini = {}, None
            for c, x in enumerate(hdr):
                m = re.search(TGL, x or "")
                if m:
                    tgl_kini = pd.Timestamp(pd.to_datetime(m.group(0), format="%d-%b-%y"))
                j = (sub[c] or "").strip().upper()
                if tgl_kini is not None and j in ("SUN", "SBSN", "TOTAL"):
                    kol_tgl[c] = (tgl_kini, j)
            if not kol_tgl:
                continue
            kolom = sorted(kol_tgl)
            # baca PER KOLOM dari atas ke bawah (pemecahan sel antar baris tabel tidak konsisten antar kolom; 2025-01..06)
            per_kolom = []
            for c in kolom:
                isi = [y for r in t[2:] for y in str(r[c] or "").split(BARIS_BARU) if y.strip()]
                if len(isi) != len(URUTAN_PDF):
                    raise ValueError(f"{jalur}: hal {pg.page_number} kolom {c}: {len(isi)} nilai, harus {len(URUTAN_PDF)}")
                per_kolom.append([angka_pdf(y) for y in isi])
            vektor = list(np.array(per_kolom).T)
            v = dict(zip(URUTAN_PDF, vektor))
            sel = cek_identitas(v)
            if sel > 0.05:
                raise ValueError(f"{jalur}: hal {pg.page_number} identitas meleset {sel:.3f} triliun")
            for kat, arr in v.items():
                for c, x in zip(kolom, arr):
                    keluar.append((kol_tgl[c][0], kat, kol_tgl[c][1], x, f"hal{pg.page_number}"))
    h = pd.DataFrame(keluar, columns=["tanggal", "label", "jenis", "nilai", "lembar"])
    h["kategori"] = h["label"]
    return h


def urai(jalur):
    with open(jalur, "rb") as f:
        kepala = f.read(4)
    return urai_pdf(jalur) if kepala.startswith(b"%PDF") else urai_excel(jalur)
