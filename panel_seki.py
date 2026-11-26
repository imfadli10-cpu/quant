"""
PANEL SEKI -> tabel bulanan/kuartalan panjang (riset #52, langkah 1): SEMUA baris dari tabel SEKI Bank Indonesia (foto terbaru).
Skema SAMA dgn panel lain: seri, kode, judul, frek, bulan (akhir bulan), tersedia, nilai, pit.

ATURAN (ditetapkan 26 Nov 2026 SEBELUM melihat hubungan apa pun dengan return saham):
- Kolom bulan dikenali dgn `seki.peta_kolom` (teruji di riset #27/#29). Tabel tanpa kolom bulan/kuartal yang dikenali = 'terlewat'
  (neraca pembayaran, ULN, APBN, beberapa tabel internasional: header kuartalan/tahunan -> pengurai khusus NANTI).
- Baris data = label teks (4 kolom pertama) + >= 6 angka. Di DALAM satu lembar, kunci = label | urutan kemunculan (pasti).
- ANTAR LEMBAR (periode 'Th 2002-2017', 'Th 2016-2024', 'I.4_1'...): nama baris & susunan tabel BERUBAH antar periode (mis.
  'Simpanan Berjangka' -> 'Deposito', sektor 9 -> 17 KBLI, label grup tanpa/dengan nomor) dan sub-baris ('Industri Pengolahan')
  berulang di bawah tiap kelompok bank -> pencocokan NAMA tidak bisa dipercaya. Disambung HANYA lewat ANGKA: dua baris dari lembar
  berbeda yang punya >= 3 bulan tumpang tindih disambung bila >= 90% bulan tumpang tindih sama (selisih <= 0,5%), angkanya tidak
  konstan, dan pasangan itu SALING tunggal (satu-satunya yang cocok di kedua arah). Lembar belakang menimpa bulan yang sama.
  Baris tanpa pasangan = SEGMEN sendiri (seperti segmen BPS); penyaring memakai pertumbuhan DI DALAM segmen.
- Frekuensi dari ISI: seri dgn <= 4 bulan kalender (Mar/Jun/Sep/Des) = Q.
- KETERSEDIAAN: angka SEKI = versi TERREVISI terbaru (foto kita baru mulai 21 Nov 2026) -> pit=False. Jeda KONSERVATIF dari akhir
  periode: bulanan + 2 bln (moneter/perbankan/pasar/ekspor-impor/kurs/cadev), + 3 utk bab II (pembiayaan, OJK), IV (APBN), VI (ULN);
  kuartalan + 4 bln. Bulan BERJALAN & masa depan dibuang.

CEK (26 Nov 2026, lolos): pertumbuhan M2 Des 2018 6,3% / 2020 12,5% / 2023 3,5% = angka resmi BI; M2 tersambung 2004-2026 (lembar
  'Th 2004-2009' s/d Des 2010 = lembar I.1 persis 12 bulan). Kredit total (I.4 'Jumlah') 2008 +30,8%, 2018 +11,7%, 2020 -2,6%.
  JEBAKAN: baris identitas ('Faktor-faktor yang Mempengaruhi Uang Beredar' = M2) membuat pencocokan angka ambigu -> kelompok kembar
  n x n dipasangkan menurut urutan. Lompatan besar di seri sambungan (49% seri vs 23% seri tunggal) BUKAN dari sambungan (angka di bulan
  tumpang tindih sama) tapi sub-kategori kecil yang bergejolak (BUMD, dana pensiun, koperasi) -> penyaring wajib tahan pencilan.
  Lembar periode TANPA tumpang tindih (mis. 'Th 2001-2003' -> 'Th 2004-2009') TIDAK disambung (= segmen).

  python panel_seki.py ->data/olah/panel_seki.parquet + panel_seki_ringkas.parquet
"""
import glob
import hashlib
import re
import warnings
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from seki import peta_kolom

folder = sorted(d for d in glob.glob("data/raw/seki/*/") if re.search(r"\d{4}-\d{2}-\d{2}", d))
indeks = pd.read_parquet("data/raw/seki/indeks.parquet").sort_values("tanggal_ambil").drop_duplicates("tabel", keep="last")
JUDUL = dict(zip(indeks["tabel"], indeks["judul"]))
file_tabel = {}
for d in folder:                               # foto berikutnya hanya menyimpan tabel yang BERUBAH -> ambil versi terbaru
    for f in glob.glob(d + "TABEL*.xls"):
        file_tabel[Path(f).stem] = f
BULAN_INI = pd.Timestamp.today().to_period("M")
TOL, PORSI, MIN_TUMPANG = 0.005, 0.9, 3


def jeda(tabel, frek):
    if frek == "Q":
        return 4
    bab = re.match(r"TABEL(\d+)_", tabel).group(1)
    return 3 if bab in ("2", "4", "6") else 2


def rapikan(s):
    return re.sub(r"\s+", " ", s).strip()


def baris_lembar(v):
    i, peta = peta_kolom(v)
    if i is None or len(peta) < 6:
        return None
    hasil, hit, bagian = [], Counter(), []
    kol_label = range(min(4, v.shape[1], min(peta)))     # HANYA kolom sebelum kolom data pertama (dulu '-' di kolom data ikut label)
    for r in range(i + 1, len(v)):
        label = rapikan(" ".join(str(v.iat[r, k]) for k in kol_label if isinstance(v.iat[r, k], str)))
        if not label or len(label) > 200:
            continue
        nilai = {}
        for j, t in peta.items():
            c = v.iat[r, j]
            x = pd.to_numeric(str(c).replace(",", "") if isinstance(c, str) else c, errors="coerce")
            if pd.notna(x) and np.isfinite(x):
                nilai[t] = float(x)
        if len(nilai) >= 6:
            hit[label] += 1
            hasil.append((label, hit[label], nilai, " > ".join(bagian[-2:])))
        elif len(label) <= 80:
            bagian.append(label)                       # judul bagian (baris tanpa angka) -> konteks keterangan saja, BUKAN kunci
    return hasil


def pasangan(A, B):
    """A, B: list (label, ke, nilai) dari dua lembar. -> list (ia, ib) yang SALING tunggal cocok lewat angka."""
    bln = sorted(set().union(*[set(x[2]) for x in A]) & set().union(*[set(x[2]) for x in B]))
    if len(bln) < MIN_TUMPANG:
        return []
    ma = np.array([[x[2].get(t, np.nan) for t in bln] for x in A])
    mb = np.array([[x[2].get(t, np.nan) for t in bln] for x in B])
    with np.errstate(invalid="ignore", divide="ignore"):
        ada = ~np.isnan(ma)[:, None, :] & ~np.isnan(mb)[None, :, :]
        sama = np.abs(ma[:, None, :] - mb[None, :, :]) <= TOL * np.maximum(np.abs(mb[None, :, :]), 1e-9)
        sama |= (ma[:, None, :] == mb[None, :, :])
        n = ada.sum(2)
        cocok = (n >= MIN_TUMPANG) & ((sama & ada).sum(2) >= PORSI * np.maximum(n, 1))
    konstan_a = np.nanstd(ma, axis=1) == 0
    konstan_b = np.nanstd(mb, axis=1) == 0
    cocok[konstan_a, :] = False
    cocok[:, konstan_b] = False
    hasil, sudah = [], set()
    for ia in range(len(A)):
        ib = np.flatnonzero(cocok[ia])
        if len(ib) == 1 and cocok[:, ib[0]].sum() == 1:
            hasil.append((ia, int(ib[0])))
        elif len(ib) > 1 and ia not in sudah:
            # baris KEMBAR (identitas akuntansi, mis. 'Faktor-faktor yang Mempengaruhi Uang Beredar' = M2): kalau kelompoknya
            # saling cocok SEMUA (n x n), pasangkan menurut urutan di lembar; selain itu dilewati (ambigu).
            ia_grup = np.flatnonzero(cocok[:, ib].all(1))
            if len(ia_grup) == len(ib) and cocok[np.ix_(ia_grup, np.arange(cocok.shape[1]))].sum() == len(ib) ** 2:
                hasil.extend(zip(ia_grup.tolist(), ib.tolist()))
                sudah.update(ia_grup.tolist())
    return hasil


potong, laporan, dipakai = [], [], set()
for tabel, f in sorted(file_tabel.items()):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            lembar = pd.read_excel(f, header=None, engine="xlrd", sheet_name=None)
        except Exception as e:                       # noqa: BLE001
            laporan.append((tabel, "GAGAL BACA", str(e)[:60]))
            continue
        segs = [(nama, b) for nama, v in lembar.items() if (b := baris_lembar(v))]
    if not segs:
        laporan.append((tabel, "terlewat", f"{len(lembar)} lembar tanpa kolom bulan"))
        continue
    # union-find atas (lembar, baris)
    induk = {(s, r): (s, r) for s, (_, b) in enumerate(segs) for r in range(len(b))}

    def akar(x):
        while induk[x] != x:
            induk[x] = induk[induk[x]]
            x = induk[x]
        return x

    n_link = 0
    for sa in range(len(segs)):
        for sb in range(sa + 1, len(segs)):
            for ia, ib in pasangan(segs[sa][1], segs[sb][1]):
                ra, rb = akar((sa, ia)), akar((sb, ib))
                if ra != rb:
                    induk[ra] = rb if rb > ra else ra
                    n_link += 1
    grup = {}
    for k in induk:
        grup.setdefault(akar(k), []).append(k)
    for anggota in grup.values():
        anggota.sort()                                   # urutan lembar: belakang menimpa
        nilai = {}
        for s, r in anggota:
            nilai.update(segs[s][1][r][2])
        s_akhir, r_akhir = anggota[-1]
        nama, b = segs[s_akhir]
        label, ke, _, bagian = b[r_akhir]
        sr = pd.Series(nilai).sort_index()
        bln = pd.PeriodIndex(sr.index, freq="M")
        ok = bln < BULAN_INI
        if ok.sum() < 6:
            continue
        frek = "Q" if len(set(bln[ok].month)) <= 4 and set(bln[ok].month) <= {3, 6, 9, 12} else "M"
        slug = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")[:50]
        lslug = re.sub(r"[^a-z0-9]+", "", nama.lower())[:12]
        kode = f"seki_{tabel[5:]}_{lslug}_{slug}_{ke}"
        if kode in dipakai:
            kode += "_" + hashlib.md5(f"{nama}|{label}|{ke}".encode()).hexdigest()[:6]
        dipakai.add(kode)
        jd = jeda(tabel, frek)
        potong.append(pd.DataFrame({
            "seri": "SEKI|" + kode, "kode": kode,
            "judul": f"SEKI {JUDUL.get(tabel, tabel)[:70]} | lembar {nama} | " + (f"{bagian} > " if bagian else "") + label + (f" (#{ke})" if ke > 1 else "")
                     + (f" [disambung {len(anggota)} lembar]" if len(anggota) > 1 else ""),
            "frek": frek,
            "bulan": bln[ok].to_timestamp(how="end").normalize().astype("datetime64[ns]"),
            "tersedia": (bln[ok] + jd).to_timestamp(how="end").normalize().astype("datetime64[ns]"),
            "nilai": sr.values[ok], "pit": False, "n_lembar": len(anggota)}))
    laporan.append((tabel, "ok", f"{len(segs)}/{len(lembar)} lembar, {sum(len(b) for _, b in segs)} baris -> {len(grup)} seri "
                                 f"({n_link} sambungan lewat angka)"))

out = pd.concat(potong, ignore_index=True)
for k in ["seri", "kode", "judul", "frek"]:
    out[k] = out[k].astype("string")
assert out.duplicated(["seri", "bulan"]).sum() == 0
Path("data/olah").mkdir(parents=True, exist_ok=True)
out.drop(columns="n_lembar").to_parquet("data/olah/panel_seki.parquet", index=False)
r = out.groupby("seri").agg(judul=("judul", "first"), frek=("frek", "first"), n_lembar=("n_lembar", "first"), awal=("bulan", "min"),
                            akhir=("bulan", "max"), n=("nilai", "size"),
                            n_latih=("bulan", lambda s: ((s >= "2005-01-01") & (s <= "2018-12-31")).sum()))
r.to_parquet("data/olah/panel_seki_ringkas.parquet")
lp = pd.DataFrame(laporan, columns=["tabel", "status", "keterangan"])
if __name__ == "__main__":
    print(lp["status"].value_counts().to_dict(), "| terlewat:", lp.loc[lp["status"] != "ok", "tabel"].tolist())
    print(lp[lp["status"] == "ok"].to_string(max_colwidth=100))
    print(f"✅ panel SEKI: {len(out):,} baris, {out['seri'].nunique():,} seri (frek {r['frek'].value_counts().to_dict()}; "
          f"disambung > 1 lembar: {(r['n_lembar'] > 1).sum():,}); cukup latih (M >= 120 / Q >= 40 di 2005-2018): "
          f"{(((r['frek'] == 'M') & (r['n_latih'] >= 120)) | ((r['frek'] == 'Q') & (r['n_latih'] >= 40))).sum():,}")
