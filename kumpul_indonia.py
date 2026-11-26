"""
SUKU BUNGA PASAR UANG RUPIAH dari Bank Indonesia (robots.txt BI: Allow /):
 1) IndONIA (Indonesia Overnight Index Average = suku bunga pinjam-meminjam antarbank SEMALAM, rata-rata tertimbang transaksi nyata)
    + Compounded IndONIA 30/90/180/360 hari + Indeks IndONIA (dasar 2 Jan 2019 = 1). Halaman publik
    https://www.bi.go.id/id/statistik/indikator/Historis-Compounded-IndONIA-Index.aspx -> formulir rentang bulan (mm/yyyy) + tombol 'Lihat',
    sama seperti pengunjung (pola kumpul_jisdor.py). IndONIA sejak 2017-01-03, compounded/indeks sejak 2019-01-02. Satu permintaan ~1 dtk.
    -> raw/harian/indonia/<tanggal UTC>.parquet = SELURUH histori tiap hari (kecil; foto harian = melacak revisi)
       kolom: tanggal, seri (indonia | comp_30 | comp_90 | comp_180 | comp_360 | indeks), nilai (persen; indeks = angka), waktu_ambil
 2) KURVA IMBAL HASIL TRANSAKSI PASAR UANG ('MM Curve', BI DKOM): rata-rata tertimbang & VOLUME transaksi harian pasar sekunder
    REPO 1 bulan dan SRBI 3/6/12 bulan. File resmi .../indonia-jibor/Documents/Data-Publikasi-Kurva-Imbal-Hasil-Transaksi-Pasar-Uang-<tahun>.zip
    (ditautkan halaman publik IndONIA-JIBOR; hanya tahun berjalan tersedia, mulai Jun 2026 -> HANYA KE DEPAN; BI menimpa file).
    -> raw/harian/kurva_pasar_uang/<tanggal UTC>.parquet  kolom: tanggal, pasar (repo | srbi), tenor_bulan, rrt_persen, volume_miliar, status, waktu_ambil
       status = 'libur' (sel LIBUR) | 'tanpa_transaksi' (0 / '-') | 'ada'. Angka dalam file = PECAHAN (0,0625) -> dikali 100.
Cara pakai: python kumpul_indonia.py   |   --tes (tanpa simpan)
"""
import io
import re
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

H = {"User-Agent": "quant-data-collector/1.0 (personal research project)"}
URL = "https://www.bi.go.id/id/statistik/indikator/Historis-Compounded-IndONIA-Index.aspx"
P = "ctl00$PlaceHolderMain$g_f2e9b24b_3422_4563_9e4a_0f108e569fd4$ctl00$"
ZIP = "https://www.bi.go.id/id/fungsi-utama/moneter/indonia-jibor/Documents/Data-Publikasi-Kurva-Imbal-Hasil-Transaksi-Pasar-Uang-{}.zip"
TES = "--tes" in sys.argv
SEKARANG = datetime.now(timezone.utc)
WAKTU = pd.Timestamp(SEKARANG).tz_localize(None).floor("s")
BULAN = {b: i + 1 for i, b in enumerate(["jan", "feb", "mar", "apr", "mei", "jun", "jul", "agu", "sep", "okt", "nov", "des"])}
BULAN.update({"may": 5, "aug": 8, "oct": 10, "dec": 12, "ags": 8, "agt": 8})
gagal = 0


def minta(sesi, metode, url, **k):
    for coba in range(4):
        try:
            r = sesi.request(metode, url, headers=H, timeout=(20, 180), **k)
            if r.status_code == 200:
                return r
            print(f"   ⚠️ HTTP {r.status_code} {url[-70:]}")
            if 400 <= r.status_code < 500 and r.status_code != 429:
                return None
        except requests.RequestException as e:
            print(f"   🔌 {type(e).__name__}")
        time.sleep(10 * (coba + 1))
    return None


def angka_id(x):
    """'5,34796' -> 5.34796 ; '1,452915072' -> 1.452915072 ; '-' -> NaN (titik = ribuan, koma = desimal)."""
    x = str(x).strip().replace("​", "")
    if not re.search(r"\d", x):
        return np.nan
    return float(x.replace(".", "").replace(",", "."))


def tanggal_id(x):
    m = re.match(r"\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", str(x))
    if not m or m.group(2).lower()[:3] not in BULAN:
        return pd.NaT
    return pd.Timestamp(int(m.group(3)), BULAN[m.group(2).lower()[:3]], int(m.group(1)))


# ===== 1) IndONIA
sesi = requests.Session()
r = minta(sesi, "GET", URL)
d_ind = pd.DataFrame()
if r is None:
    print("❌ halaman IndONIA tidak bisa dibuka")
    gagal += 1
else:
    data = {m.group(1): m.group(2) for m in re.finditer(r'<input type="hidden" name="([^"]+)" id="[^"]*" value="([^"]*)"', r.text)}
    data.update({P + "dtBulanFrom": "01/2017", P + "dtBulanTo": f"{SEKARANG.month:02d}/{SEKARANG.year}", P + "ButtonFilter": "Lihat",
                 "__EVENTTARGET": "", "__EVENTARGUMENT": ""})
    r2 = minta(sesi, "POST", URL, data=data)
    baris = []
    if r2 is not None:
        for tb in BeautifulSoup(r2.text, "lxml").find_all("table"):
            rows = [[c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])] for tr in tb.find_all("tr")]
            if not rows or not rows[0] or "Tanggal Publikasi" not in rows[0][0]:
                continue
            kepala = " ".join(rows[0])
            nama = ["indonia"] if "Compounded" not in kepala else ["comp_30", "comp_90", "comp_180", "comp_360", "indeks"]
            for row in rows[1:]:
                t = tanggal_id(row[0]) if row else pd.NaT
                if pd.isna(t) or len(row) != len(nama) + 1:
                    continue
                for n, v in zip(nama, row[1:]):
                    baris.append({"tanggal": t, "seri": n, "nilai": angka_id(v)})
    d_ind = pd.DataFrame(baris)
    if d_ind.empty or "indonia" not in set(d_ind["seri"]):
        print("❌ tabel IndONIA tidak terbaca")
        gagal += 1
        d_ind = pd.DataFrame()
    else:
        d_ind = d_ind.drop_duplicates(["tanggal", "seri"], keep="first").sort_values(["seri", "tanggal"]).reset_index(drop=True)
        d_ind["tanggal"] = d_ind["tanggal"].astype("datetime64[ns]")
        d_ind["seri"] = d_ind["seri"].astype("string")
        d_ind["waktu_ambil"] = WAKTU
        ind = d_ind[d_ind["seri"] == "indonia"].set_index("tanggal")["nilai"]
        lompat = ind.diff().abs()
        print(f"✅ IndONIA: {len(ind)} hari {ind.index.min():%Y-%m-%d} s/d {ind.index.max():%Y-%m-%d}, terakhir {ind.iloc[-1]:.4f}% | "
              f"seri {d_ind['seri'].nunique()} | perubahan harian > 0,5 pp: {(lompat > 0.5).sum()} hari | kosong {ind.isna().sum()}")
        if ind.dropna().between(0, 25).mean() < 0.999:
            print("❌ nilai IndONIA di luar 0-25% -> curigai format angka")
            gagal += 1

# ===== 2) Kurva pasar uang (tahun berjalan; awal Januari juga tahun lalu kalau masih ada)
kurva = []
for th in sorted({SEKARANG.year, (SEKARANG - pd.Timedelta(days=20)).year}):
    rz = minta(sesi, "GET", ZIP.format(th), allow_redirects=False)
    if rz is None or not rz.content[:2] == b"PK":
        print(f"   (kurva {th}: tidak tersedia)")
        continue
    z = zipfile.ZipFile(io.BytesIO(rz.content))
    for nama in z.namelist():
        if not nama.lower().endswith((".xlsx", ".xls")):
            continue
        x = pd.read_excel(io.BytesIO(z.read(nama)), header=None)
        # 3 baris kepala: pasar (isi ke kanan), tenor, (RRT % | Volume)
        pasar = x.iloc[0].ffill()
        tenor = x.iloc[1].ffill()
        for j in range(2, x.shape[1]):
            if not str(x.iat[2, j]).strip().upper().startswith("RRT"):
                continue
            ps = "repo" if "repo" in str(pasar[j]).lower() else ("srbi" if "srbi" in str(pasar[j]).lower() else str(pasar[j]).strip().lower())
            tb = int(re.search(r"\d+", str(tenor[j])).group())
            for i in range(3, x.shape[0]):
                t = pd.to_datetime(x.iat[i, 0], errors="coerce")
                if pd.isna(t):
                    continue
                v, vol = x.iat[i, j], x.iat[i, j + 1]
                if str(v).strip().upper() == "LIBUR":
                    status, v, vol = "libur", np.nan, np.nan
                else:
                    v = pd.to_numeric(v, errors="coerce")
                    vol = pd.to_numeric(vol, errors="coerce")
                    status = "ada" if (pd.notna(v) and v > 0 and pd.notna(vol) and vol > 0) else "tanpa_transaksi"
                    if status != "ada":
                        v, vol = np.nan, (0.0 if pd.notna(vol) else np.nan)
                kurva.append({"tanggal": t.normalize(), "pasar": ps, "tenor_bulan": tb, "rrt_persen": v * 100 if pd.notna(v) else np.nan,
                              "volume_miliar": vol, "status": status, "file": nama})
d_kur = pd.DataFrame(kurva)
if d_kur.empty:
    print("❌ kurva pasar uang tidak terbaca")
    gagal += 1
else:
    d_kur = d_kur.drop_duplicates(["tanggal", "pasar", "tenor_bulan"], keep="last").sort_values(["pasar", "tenor_bulan", "tanggal"])
    d_kur["tanggal"] = d_kur["tanggal"].astype("datetime64[ns]")
    for c in ("pasar", "status", "file"):
        d_kur[c] = d_kur[c].astype("string")
    d_kur["waktu_ambil"] = WAKTU
    ok = d_kur[d_kur["status"] == "ada"]
    print(f"✅ kurva pasar uang: {d_kur['tanggal'].nunique()} hari {d_kur['tanggal'].min():%Y-%m-%d} s/d {d_kur['tanggal'].max():%Y-%m-%d}; "
          + " | ".join(f"{p} {t}bln {len(g)} hari ada, median {g['rrt_persen'].median():.2f}%" for (p, t), g in ok.groupby(["pasar", "tenor_bulan"])))
    if len(ok) and not ok["rrt_persen"].between(0, 25).all():
        print("❌ imbal hasil kurva di luar 0-25%")
        gagal += 1

if TES:
    print("🧪 mode tes: tidak disimpan")
    sys.exit(1 if gagal else 0)
tgl = SEKARANG.date().isoformat()
for df, nama in [(d_ind, "indonia"), (d_kur, "kurva_pasar_uang")]:
    if len(df):
        f = Path(f"data/raw/harian/{nama}/{tgl}.parquet")
        f.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(f, index=False)
        print(f"💾 {f}")
sys.exit(1 if gagal else 0)
