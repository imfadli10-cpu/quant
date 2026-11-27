"""
SHANGHAI FUTURES EXCHANGE (SHFE, + INE minyak mentah) -> harga harian SEMUA kontrak berjangka + STOK GUDANG mingguan & harian
China = konsumen terbesar nikel, timah, tembaga, KARET ALAM -> pelengkap LME (raw/harian/lme) untuk emiten nikel/timah/karet IDX.
Sumber: berkas data publik yang dimuat halaman resmi (alamat dari /images/api.js situs SHFE); www.shfe.com.cn tanpa robots.txt (404).
  kx<YYYYMMDD>.dat                          = 'daily trading bulletin' JSON: per kontrak (PRODUCTID mis. ni_f/sn_f/ru_f/nr_f/cu_f/sc_f,
                                              DELIVERYMONTH, buka/tertinggi/terendah/tutup/SETTLEMENT, volume, open interest). SEJAK 2002
                                              (2002: cu/al/ru saja; nikel & timah sejak 2015). Hari libur = 404.
  weeklydata/<Jumat>weeklystock.dat         = STOK GUDANG mingguan per gudang (JSON, 2014?..2025): SPOTWGHTS (stok memenuhi syarat
                                              serah), WRTWGHTS (sudah jadi warrant/ 'futures'), WHSTOCKS (sisa kapasitas). Baris
                                              WHABBRNAME '合计$$Subtotal' = subtotal wilayah; ROWSTATUS '2' = total produk (bila ada).
  stockdata/weeklystock_<tgl>/ZH/all.html   = stok mingguan FORMAT BARU (akhir 2025+): tabel HTML per produk, header 2 tingkat
                                              (上周库存/本周库存/库存增减 x 小计/期货, 可用库容量). Disimpan sel-per-sel (teks asli).
  stockdata/dailystock_<tgl>/ZH/all.html    = warrant (仓单) HARIAN format baru; dailydata/<tgl>dailystock.dat = format lama (s/d 2025).
SIMPAN
  raw/harian/shfe/<tgl UTC>.parquet            kx 10 hari kalender terakhir (format: tanggal + semua kolom asli, angka -> float)
  raw/harian/shfe_stok/<tgl UTC>.parquet       stok mingguan (3 Jumat terakhir) + warrant harian (5 hari) format HTML baru, sel-per-sel:
                                              laporan (mingguan/harian), tanggal, tabel_ke, baris, kolom, teks
  --histori: raw/histori/shfe/kx_<tahun>.parquet (2002+) & stok_mingguan_<tahun>.parquet (format .dat, semua baris JSON asli)
             upload per tahun, bisa dilanjutkan (tahun yang sudah ada dilewati kecuali tahun berjalan). bisa >5 jam dari server GitHub (lambat ke China) -> 4 permintaan paralel; terpotong = jalankan ulang (workflow manual).
JEBAKAN: angka kosong = '' ; baris 'DELIVERYMONTH' = '小计' (subtotal produk) & PRODUCTID '总计' (total bursa) ikut disimpan -> saring saat riset.
  Harga dalam YUAN/ton TERMASUK PPN 13% China (cek 17 Nov 2026: SHFE/kurs/1,13 = LME 3 bln, nikel 15.971 vs 15.990 USD); jam tutup 15:00 Beijing = 14:00 WIB (SEBELUM IDX tutup!) tapi ada
  sesi MALAM (21:00-01:00 Beijing) -> 'tanggal' = hari dagang SHFE (sesi malam dihitung ke hari berikutnya).
Cara pakai: python kumpul_shfe.py  |  --tes  |  --histori [--tes = 1 bulan, tanpa simpan]
"""
import io
import json
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

DASAR = "https://www.shfe.com.cn/data/tradedata/future"
H = {"User-Agent": "quant-data-collector/1.0 (personal research project)"}
TES, HISTORI = "--tes" in sys.argv, "--histori" in sys.argv
SEKARANG = datetime.now(timezone.utc)
HARI_INI = SEKARANG.date()
REPO = "fadli-sparks/quant-data"
TEKS = {"PRODUCTID", "PRODUCTGROUPID", "PRODUCTNAME", "DELIVERYMONTH", "PRODUCTCLASS", "VARNAME", "REGNAME", "WHABBRNAME", "ROWSTATUS",
        "WRTWEEKRPTTYPE", "WHTYPE", "VARID", "OILID", "OILNAME", "GRDNAME", "REMARK", "WGHTUNIT", "bagian"}


def minta(url):
    for coba in range(4):
        try:
            r = requests.get(url, headers=H, timeout=(20, 90))
            if r.status_code == 200:
                return r
            if r.status_code == 404:
                return None                          # hari libur / laporan tidak ada
            print(f"   ⚠️ HTTP {r.status_code} {url[-60:]}")
        except requests.RequestException as e:
            print(f"   🔌 {type(e).__name__}")
        time.sleep(10 * (coba + 1))
    return None


def rapikan(d):
    for c in d.columns:
        if c in TEKS:
            d[c] = d[c].astype(str).str.strip().replace({"None": "", "nan": ""}).astype("string")
        elif c != "tanggal" and not pd.api.types.is_numeric_dtype(d[c]):    # pandas 3: kolom teks murni bertipe 'str', bukan object
            d[c] = pd.to_numeric(d[c].astype(object).replace({"": np.nan, "--": np.nan}), errors="coerce")
    return d


def kx(tgl):
    r = minta(f"{DASAR}/dailydata/kx{tgl:%Y%m%d}.dat")
    if r is None:
        return None
    try:
        j = json.loads(r.text)
    except ValueError:
        return None
    d = pd.DataFrame(j.get("o_curinstrument") or [])
    if d.empty:
        return None
    d.insert(0, "tanggal", pd.Timestamp(tgl))
    return d


def stok_dat(tgl):
    """Stok mingguan format lama (JSON): semua kursor (logam/karet umum, INE minyak, emas, BBM, ...) digabung, kolom 'bagian'."""
    r = minta(f"{DASAR}/weeklydata/{tgl:%Y%m%d}weeklystock.dat")
    if r is None:
        return None
    try:
        j = json.loads(r.text)
    except ValueError:
        return None
    bag = [pd.DataFrame(v).assign(bagian=k) for k, v in j.items() if k.startswith("o_cursor") and isinstance(v, list) and v]
    if not bag:
        return None
    d = pd.concat(bag, ignore_index=True)
    d.insert(0, "tanggal", pd.Timestamp(tgl))
    return d


def stok_html(jenis, tgl):
    r = minta(f"{DASAR}/stockdata/{jenis}_{tgl:%Y%m%d}/ZH/all.html")
    if r is None:
        return []
    r.encoding = "utf-8"
    try:
        tabel = pd.read_html(io.StringIO(r.text), thousands=None)
    except ValueError:
        return []
    out = []
    for ke, t in enumerate(tabel):
        kol = [" | ".join(dict.fromkeys(str(x) for x in (c if isinstance(c, tuple) else (c,)))) for c in t.columns]
        for i in range(t.shape[0]):
            for k in range(t.shape[1]):
                v = t.iat[i, k]
                if pd.isna(v):
                    continue
                out.append({"laporan": "mingguan" if jenis == "weeklystock" else "harian", "tanggal": pd.Timestamp(tgl),
                            "tabel_ke": ke, "baris": i, "kolom": kol[k], "teks": str(v).strip()})
    return out


def hari_kerja(a, b):
    return [x.date() for x in pd.bdate_range(a, b)]


# ===================== HISTORI =====================
if HISTORI:
    if TES:
        bag = [x for x in (kx(t) for t in hari_kerja("2015-11-02", "2015-11-30")) if x is not None]
        d = rapikan(pd.concat(bag, ignore_index=True))
        ni = d[(d["PRODUCTID"] == "ni_f") & (d["DELIVERYMONTH"] != "小计")]
        print(f"🧪 kx Nov 2015: {d['tanggal'].nunique()} hari, {len(d)} baris; nikel {ni['DELIVERYMONTH'].nunique()} kontrak, "
              f"settlement {ni['SETTLEMENTPRICE'].min():.0f}..{ni['SETTLEMENTPRICE'].max():.0f} yuan/t")
        s = stok_dat(date(2015, 11, 6))
        s = rapikan(s) if s is not None else None
        if s is not None:
            n = s[s["VARNAME"].str.contains("NICKEL", na=False)]
            print(f"🧪 stok mingguan 2015-11-06: {len(s)} baris; nikel: {n[['WHABBRNAME', 'SPOTWGHTS', 'WRTWGHTS', 'ROWSTATUS']].tail(4).to_string()}")
        print("🧪 mode tes: tidak disimpan")
        sys.exit()
    from huggingface_hub import HfApi
    api_hf = HfApi(token=os.environ.get("HF_TOKEN") or Path("kunci_hf.txt").read_text().strip())
    sudah = {Path(x).name for x in api_hf.list_repo_files(REPO, repo_type="dataset") if x.startswith("raw/histori/shfe/")}
    folder = Path("data/raw/histori/shfe")
    folder.mkdir(parents=True, exist_ok=True)
    print(f"☁️  {len(sudah)} file histori SHFE sudah di gudang")

    def unggah(f):
        for _ in range(6):
            try:
                api_hf.upload_file(path_or_fileobj=str(f), path_in_repo=f"raw/histori/shfe/{f.name}", repo_id=REPO,
                                   repo_type="dataset", commit_message=f"Upload raw/histori/shfe/{f.name}")
                return
            except Exception as e:
                print(f"   ⚠️  upload {f.name}: {type(e).__name__}, tunggu 2 menit")
                time.sleep(120)
        raise RuntimeError(f"upload {f.name} gagal terus")

    for th in range(2002, HARI_INI.year + 1):
        for nama, fungsi, hari in (("kx", kx, None), ("stok_mingguan", stok_dat, "jumat")):
            f = folder / f"{nama}_{th}.parquet"
            if (f.exists() or f.name in sudah) and th < HARI_INI.year:
                continue
            if nama == "stok_mingguan" and th < 2013:
                continue
            t0, bag, gagal_beruntun = time.time(), [], 0
            tgl_list = hari_kerja(f"{th}-01-01", min(date(th, 12, 31), HARI_INI))
            if hari:
                tgl_list = [t for t in tgl_list if t.weekday() == 4]
            def satu(t):
                x = fungsi(t)
                if x is None and hari:                      # Jumat libur -> coba Kamis
                    x = fungsi(t - timedelta(days=1))
                time.sleep(0.6)
                return x
            # 4 permintaan paralel: dari server GitHub (AS) tiap permintaan ke SHFE lambat (~15-20 mnt/tahun kalau berurutan, 27 Nov 2026)
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=4) as ex:
                bag = [x for x in ex.map(satu, tgl_list) if x is not None]
            if not bag:
                print(f"   {nama} {th}: kosong")
                continue
            d = rapikan(pd.concat(bag, ignore_index=True))
            d.to_parquet(f, index=False)
            unggah(f)
            print(f"   💾☁️  {nama} {th}: {d['tanggal'].nunique()} tanggal, {len(d):,} baris ({time.time() - t0:.0f} dtk)")
    print("✅ histori SHFE selesai")
    sys.exit()

# ===================== HARIAN =====================
bag = [x for x in (kx(t) for t in hari_kerja(HARI_INI - timedelta(days=10), HARI_INI)) if x is not None]
if not bag:
    print("❌ tidak ada data kx SHFE 10 hari terakhir")
    sys.exit(1)
d = rapikan(pd.concat(bag, ignore_index=True))
sah = d[d["DELIVERYMONTH"] != "小计"].groupby("tanggal")["SETTLEMENTPRICE"].apply(lambda x: x.notna().any())
if (~sah).any():                                      # hari dagang yang BELUM selesai (settlement kosong) dibuang
    print(f"   hari belum selesai dibuang: {[f'{x:%Y-%m-%d}' for x in sah.index[~sah]]}")
    d = d[d["tanggal"].isin(sah.index[sah])]
d["waktu_ambil"] = pd.Timestamp(SEKARANG).tz_localize(None).floor("s")
utama = d[d["DELIVERYMONTH"] != "小计"].sort_values("OPENINTEREST").groupby(["tanggal", "PRODUCTID"]).tail(1)
akhir = utama[utama["tanggal"] == utama["tanggal"].max()].set_index("PRODUCTID")
print(f"✅ kx: {d['tanggal'].nunique()} hari ({d['tanggal'].min():%Y-%m-%d}..{d['tanggal'].max():%Y-%m-%d}), {len(d)} baris, "
      f"{d['PRODUCTID'].nunique()} produk")
print("   kontrak utama (OI terbesar) terakhir: " + " | ".join(f"{p} {akhir.loc[p, 'SETTLEMENTPRICE']:,.0f}" for p in ("ni_f", "sn_f", "ru_f", "nr_f", "cu_f")
                                                         if p in akhir.index))
stok = []
for t in hari_kerja(HARI_INI - timedelta(days=21), HARI_INI):
    if t.weekday() == 4:
        stok += stok_html("weeklystock", t)
    if t >= HARI_INI - timedelta(days=7):
        stok += stok_html("dailystock", t)
    time.sleep(0.6)
s = pd.DataFrame(stok)
if len(s):
    for k in ("laporan", "kolom", "teks"):
        s[k] = s[k].astype("string")
    s["waktu_ambil"] = pd.Timestamp(SEKARANG).tz_localize(None).floor("s")
    print(f"✅ stok: " + " | ".join(f"{k} {v} tanggal" for k, v in s.groupby("laporan")["tanggal"].nunique().items()) + f"; {len(s):,} sel")
    m = s[(s["laporan"] == "mingguan") & (s["teks"].isin(["镍", "锡", "天然橡胶"]))]
    print(f"   produk tabel mingguan contoh ditemukan: {sorted(m['teks'].unique())}")
else:
    print("⚠️ stok SHFE kosong (format berubah?)")
if TES:
    print(akhir[["DELIVERYMONTH", "SETTLEMENTPRICE", "VOLUME", "OPENINTEREST"]].head(30).to_string())
    print("🧪 mode tes: tidak disimpan")
    sys.exit()
for folder, x in ((Path("data/raw/harian/shfe"), d), (Path("data/raw/harian/shfe_stok"), s)):
    if len(x):
        folder.mkdir(parents=True, exist_ok=True)
        x.to_parquet(folder / f"{HARI_INI.isoformat()}.parquet", index=False)
        print(f"💾 {folder}/{HARI_INI.isoformat()}.parquet")
