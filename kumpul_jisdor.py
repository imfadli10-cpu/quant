"""
KURS JISDOR Bank Indonesia (Jakarta Interbank Spot Dollar Rate, USD/IDR) -> kurs referensi RESMI rupiah, ditetapkan ~10:00 WIB
(= SAAT jam bursa IDX; kurs ECB ditetapkan ~20:15 WIB setelah IDX tutup). robots.txt BI: Allow / (yang dilarang hanya /_layouts, /Lists, dst.).
Cara: halaman publik bi.go.id/id/statistik/informasi-kurs/jisdor -> formulir rentang tanggal + tombol 'Unduh' (XLSX), sama seperti pengunjung.
Tanggal di XLSX format AS ('3/26/2024 12:00:00 AM'), kurs format Indonesia ('15.797,00').
Server BI lambat (~20 dtk/permintaan). Dari laptop: WARP HARUS MATI.

  python kumpul_jisdor.py            harian: 60 hari terakhir -> data/raw/harian/jisdor/<tanggal UTC>.parquet
  python kumpul_jisdor.py --histori  per tahun sejak 2013 -> data/raw/histori/jisdor/semua.parquet
  python kumpul_jisdor.py --tes      cek tanpa simpan
"""
import io
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

URL = "https://www.bi.go.id/id/statistik/informasi-kurs/jisdor/default.aspx"
H = {"User-Agent": "quant-data-collector/1.0 (personal research project)"}
P = "ctl00$ctl51$g_8e393016_c37f_48c2_9aa2_ab195a9c1128$ctl00$"
HISTORI, TES = "--histori" in sys.argv, "--tes" in sys.argv
SEKARANG = datetime.now(timezone.utc)


def minta(sesi, metode, **k):
    for coba in range(4):
        try:
            r = sesi.request(metode, URL, headers=H, timeout=180, **k)
            if r.status_code == 200:
                return r
            print(f"   ⚠️ HTTP {r.status_code}")
        except Exception as e:
            print(f"   🔌 {type(e).__name__}")
        time.sleep(15 * (coba + 1))
    return None


def angka(x):
    x = str(x).replace("Rp", "").strip().replace(".", "").replace(",", ".")
    try:
        return float(x)
    except ValueError:
        return float("nan")


def unduh(sesi, dari, sampai):
    r = minta(sesi, "GET")
    if r is None:
        return None
    data = {m.group(1): m.group(2) for m in re.finditer(r'<input type="hidden" name="([^"]+)" id="[^"]*" value="([^"]*)"', r.text)}
    if "__VIEWSTATE" not in data:
        print("   ❌ formulir tidak ditemukan (halaman berubah?)")
        return None
    data.update({P + "TextBoxFrom": dari.strftime("%d/%m/%Y"), P + "TextBoxDateTo": sampai.strftime("%d/%m/%Y"),
                 P + "HiddenFieldDateFrom": dari.isoformat(), P + "HiddenFieldDateTo": sampai.isoformat(),
                 "__EVENTTARGET": P + "ButtonExport", "__EVENTARGUMENT": ""})
    r = minta(sesi, "POST", data=data)
    if r is None or "spreadsheet" not in str(r.headers.get("content-type")):
        print(f"   ❌ bukan XLSX ({None if r is None else r.headers.get('content-type')})")
        return None
    x = pd.read_excel(io.BytesIO(r.content), header=None, dtype=str)
    x = x[pd.to_numeric(x[0], errors="coerce").notna()]          # baris data: kolom 0 = nomor urut
    d = pd.DataFrame({"tanggal": pd.to_datetime(x[1].str.split(" ").str[0], format="%m/%d/%Y", errors="coerce"),
                      "kurs": x[2].map(angka)}).dropna()
    return d


sesi = requests.Session()
if HISTORI:
    rentang = [(date(th, 1, 1), min(date(th, 12, 31), SEKARANG.date())) for th in range(2013, SEKARANG.year + 1)]
else:
    rentang = [(SEKARANG.date() - timedelta(days=60), SEKARANG.date())]
bagian = []
for dari, sampai in rentang:
    d = unduh(sesi, dari, sampai)
    if d is None:
        print(f"❌ gagal {dari}..{sampai}")
        sys.exit(1)
    print(f"   {dari}..{sampai}: {len(d)} hari", flush=True)
    bagian.append(d)
    time.sleep(3)
df = pd.concat(bagian, ignore_index=True).drop_duplicates("tanggal").sort_values("tanggal").reset_index(drop=True)
df["tanggal"] = df["tanggal"].astype("datetime64[ns]")
df["waktu_ambil"] = pd.Timestamp(SEKARANG.replace(tzinfo=None)).as_unit("ns")
lompat = df["kurs"].pct_change().abs()
print(f"✅ JISDOR: {len(df)} hari, {df['tanggal'].min():%Y-%m-%d} s/d {df['tanggal'].max():%Y-%m-%d}, terakhir Rp{df['kurs'].iloc[-1]:,.0f}; "
      f"lompatan harian > 3%: {(lompat > 0.03).sum()}")
if len(df) < (2500 if HISTORI else 20) or not df["kurs"].between(5000, 40000).all():
    print("❌ jumlah hari / nilai kurs tidak wajar -> berhenti")
    sys.exit(1)
if TES:
    print(df.tail(5).to_string())
    sys.exit(0)
f = Path("data/raw/histori/jisdor/semua.parquet") if HISTORI else Path(f"data/raw/harian/jisdor/{SEKARANG.date().isoformat()}.parquet")
f.parent.mkdir(parents=True, exist_ok=True)
df.to_parquet(f, index=False)
print(f"💾 {f}")
