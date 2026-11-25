"""
PANEL LAIN -> tabel bulanan panjang (riset #52, langkah 1): COT, BIS, kas pemerintah AS (DTS), lelang Treasury AS, Wikipedia, harga pangan.
Skema SAMA dgn panel_alam/panel_pasar: seri, kode, judul, frek, bulan (akhir bulan), tersedia, nilai, pit.

ATURAN (ditetapkan 26 Nov 2026 SEBELUM melihat hubungan apa pun dengan return saham):
- Nilai bulan m hanya memakai pengamatan yang SUDAH TERBIT paling lambat akhir bulan m ('rilis' <= akhir bulan) -> tersedia =
  akhir bulan + 1 hari (sama dgn panel_pasar: angka akhir bulan baru dipakai setelah bursa tutup). Bulan BERJALAN (Nov 2026) dibuang.
- COT (CFTC, legacy/disaggregated/keuangan): posisi hari Selasa, terbit Jumat 15:30 ET (= Sabtu pagi WIB) -> rilis = Selasa + 6 hari
  (cadangan libur). PENUTUPAN PEMERINTAH AS menunda terbitan: laporan 2013-10-01..2013-10-15 -> rilis 2013-11-05; 2018-12-24..2019-03-05
  -> 2019-03-08; 2025-09-30..2025-12-31 -> 2026-01-23 (perkiraan KONSERVATIF; tanggal susulan pasti tidak tercatat). Nilai bulanan =
  laporan TERAKHIR yang sudah terbit. Seri per KODE kontrak CFTC (nama pasar berganti; kode tetap), pasar >= 260 laporan:
  legacy net spekulan (noncomm long-short)/OI, net komersial/OI, OI; disaggregated net managed money/OI; keuangan net leveraged funds/OI
  & net asset manager/OI. pit=False (histori diunduh belakangan; CFTC sesekali merevisi).
- BIS: Indonesia (semua dataset, frek M/Q) + likuiditas global WS_GLI (semua) + suku bunga kebijakan WS_CBPOL bulanan (semua negara)
  + total aset bank sentral WS_CBTA (US, XM, JP, CN, GB). Jeda (BIS terbit lambat): CBPOL/EER/XRU bulanan = 0 (data pasar),
  LONG_CPI 2 bln, CBTA M 2 bln / Q 5 bln, GLI 5 bln, SPP 5 bln, TC/CREDIT_GAP/DSR 7 bln (2026-Q1 baru ada di Nov 2026).
  Kuartal ditandai bulan TERAKHIR kuartal. Seri tahunan & harian dibuang. pit=False (direvisi).
- DTS: saldo TGA. Format berubah: s/d 2021-09-30 'Federal Reserve Account' (close_today_bal); 2021-10-01..2022-04-15
  'Treasury General Account (TGA)' (close_today_bal); sejak 2022-04-18 'TGA Closing Balance' dgn saldo di kolom open_today_bal
  (close kosong!). + Tax and Loan Note Accounts (s/d 2012) -> kas_operasi = TGA + TT&L. Terbit sore hari kerja berikutnya ->
  rilis = tanggal + 1 hari kerja. Nilai = akhir bulan (terakhir terbit) & rata-rata bulan. Juta USD. pit=True (DTS tidak direvisi).
- Lelang Treasury: nominal saja (TIPS & FRN dibuang); tenor dibulatkan ('9-Year 10-Month' -> 10 thn); Bill 4/8/13/17/26/52 mg,
  Note/Bond 2/3/5/7/10/20/30 thn; Cash Management Bill (hari) dibuang. Hasil diumumkan ~13:00 ET (= malam WIB) -> rilis = tanggal + 1.
  Per bulan: rata-rata bid-to-cover & porsi indirect (indirect_bidder_accepted / comp_accepted; proksi minat asing). pit=True.
- Wikipedia (20 artikel id/en): rata-rata pembaca harian per bulan, rilis = tanggal + 1. pit=True.
- Pangan PIHPS BI (sejak 2017-07): rata-rata harga harian per bulan, per jenis harga x wilayah x komoditas; rilis = tanggal + 1.
  Harga <= 0 dibuang. pit=False (histori diunduh belakangan; tidak tahu apakah BI merevisi).

CEK KEWAJARAN (26 Nov 2026, lolos): suku bunga BI Des 2005 12,75 / Des 2008 9,25 / Des 2020 3,75 / Des 2023 6,00; Fed Des 2008 0,125;
  TGA Jul 2020 $1.767 M (pandemi), Apr 2022 $954 M (musim pajak), anjlok Mei 2023 lalu naik Jun 2023 (plafon utang); sambungan format TGA
  2021-09-30 -> 10-01 & 2022-04 mulus; pembaca Wikipedia Bitcoin puncak Des 2017, Stock_market_crash Mar 2020, Recession Jul 2022;
  minyak goreng puncak Apr 2022, beras naik 14,6 rb (Des 2023) -> 15,9 rb (Mar 2024); bid-to-cover 10 thn median 2,54; COT minyak
  tidak punya nilai Jan-Feb 2019 (penutupan pemerintah, BENAR: belum terbit) -> penyaring isi-maju nilai terakhir.
CATATAN untuk penyaring: TGA 2008-2015 kecil & bergejolak (|log| bulanan > 1 sebanyak 30x) -> pakai perubahan dibagi skala (mis. total
  aset Fed) atau peringkat, BUKAN log-growth mentah. 26 harga pangan (cabai, Indonesia timur) melonjak > 65% lalu balik = kemungkinan
  NYATA (cabai sangat musiman), dibiarkan mentah.

  python panel_lain.py  ->data/olah/panel_lain.parquet + data/olah/panel_lain_ringkas.parquet
"""
import glob
import re
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.tseries.offsets import BDay

BULAN_INI = pd.Timestamp.today().to_period("M")
potong = []          # daftar DataFrame skema panel


def tambah(df, kode, judul, frek, pit, jeda_bulan=0):
    """df: kolom bulan (Period M) & nilai. jeda_bulan > 0: tersedia = akhir (bulan + jeda)."""
    x = df.dropna(subset=["nilai"]).copy()
    x = x[np.isfinite(x["nilai"])]
    x = x[x["bulan"] < BULAN_INI]
    if x.empty:
        return
    x["tersedia"] = (x["bulan"] + jeda_bulan).dt.to_timestamp(how="end").dt.normalize() + pd.Timedelta(days=0 if jeda_bulan else 1)
    x["bulan"] = x["bulan"].dt.to_timestamp(how="end").dt.normalize()
    potong.append(pd.DataFrame({"seri": "LAIN|" + kode, "kode": kode, "judul": judul, "frek": frek,
                                "bulan": x["bulan"].astype("datetime64[ns]").values,
                                "tersedia": x["tersedia"].astype("datetime64[ns]").values,
                                "nilai": x["nilai"].astype(float).values, "pit": pit}))


def bulanan_terakhir(t, rilis, nilai):
    """Nilai terakhir yang sudah terbit tiap bulan (bulan = bulan rilis)."""
    x = pd.DataFrame({"rilis": np.asarray(rilis), "nilai": np.asarray(nilai, dtype=float), "t": np.asarray(t)})
    x = x.dropna().sort_values(["rilis", "t"])
    x["bulan"] = x["rilis"].dt.to_period("M")
    return x.groupby("bulan", as_index=False)["nilai"].last()


def bulanan_rata(rilis, nilai):
    x = pd.DataFrame({"rilis": np.asarray(rilis), "nilai": np.asarray(nilai, dtype=float)}).dropna()
    x["bulan"] = x["rilis"].dt.to_period("M")
    return x.groupby("bulan", as_index=False)["nilai"].mean()


# ---------------------------------------------------------------- COT
TUTUP = [("2013-10-01", "2013-10-15", "2013-11-05"), ("2018-12-24", "2019-03-05", "2019-03-08"),
         ("2025-09-30", "2025-12-31", "2026-01-23")]
COT = {"cot_legacy": [("spek", "noncomm_positions_long_all", "noncomm_positions_short_all", "net spekulan (noncomm)/OI"),
                      ("komersial", "comm_positions_long_all", "comm_positions_short_all", "net komersial/OI"),
                      ("oi", None, None, "open interest")],
       "cot_disaggregated": [("mm", "m_money_positions_long_all", "m_money_positions_short_all", "net managed money/OI")],
       "cot_keuangan": [("lev", "lev_money_positions_long", "lev_money_positions_short", "net leveraged funds/OI"),
                        ("am", "asset_mgr_positions_long", "asset_mgr_positions_short", "net asset manager/OI")]}
n_cot = 0
for berkas, ukuran in COT.items():
    c = pd.read_parquet(f"data/raw/histori/cot/{berkas}.parquet")
    c["t"] = pd.to_datetime(c["report_date_as_yyyy_mm_dd"]).astype("datetime64[ns]")
    c["rilis"] = c["t"] + pd.Timedelta(days=6)
    for a, b, r in TUTUP:
        m = c["t"].between(a, b)
        c.loc[m, "rilis"] = c.loc[m, "rilis"].clip(lower=pd.Timestamp(r))
    c["kodec"] = c["cftc_contract_market_code"].astype(str).str.strip()
    for k in ["open_interest_all"] + [u for _, l_, s_, _ in ukuran for u in (l_, s_) if u]:
        c[k] = pd.to_numeric(c[k], errors="coerce")
    c = c.sort_values("t").drop_duplicates(["kodec", "t"], keep="last")
    jumlah = c.groupby("kodec")["t"].size()
    for kc in jumlah[jumlah >= 260].index:
        x = c[c["kodec"] == kc]
        nama = str(x["market_and_exchange_names"].iloc[-1]).strip()
        oi = x["open_interest_all"].where(x["open_interest_all"] > 0)
        for nm, l_, s_, jd in ukuran:
            v = oi if l_ is None else (x[l_] - x[s_]) / oi
            if l_ is not None:
                v = v.where(v.abs() <= 1)          # net/OI > 1 MUSTAHIL (salah data sumber: kedelai 1986-09, minyak kedelai 1988-01)
            tambah(bulanan_terakhir(x["t"], x["rilis"], v), f"cot_{berkas[4:]}_{nm}_{kc}", f"COT {nama}: {jd}", "M", False)
            n_cot += 1
print(f"   COT: {n_cot} seri")

# ---------------------------------------------------------------- BIS
ATTR = {"decimals", "unit_mult", "obs_status", "obs_conf", "obs_pre_break", "time_format", "availability",
        "compilation", "source_ref", "supp_info_breaks", "title", "title_tsv", "comment", "time_period", "obs_value", "freq"}
JEDA_BIS = {("WS_CBPOL", "M"): 0, ("WS_EER", "M"): 0, ("WS_XRU", "M"): 0, ("WS_LONG_CPI", "M"): 2, ("WS_CBTA", "M"): 2,
            ("WS_CBTA", "Q"): 5, ("WS_GLI", "Q"): 5, ("WS_SPP", "Q"): 5, ("WS_TC", "Q"): 7, ("WS_CREDIT_GAP", "Q"): 7,
            ("WS_DSR", "Q"): 7}


def periode(s, f):
    s = s.astype(str)
    if f == "M":
        return pd.PeriodIndex(s.str[:7], freq="M")
    q = s.str.extract(r"^(\d{4})-Q([1-4])$")
    return pd.PeriodIndex.from_fields(year=q[0].astype(int), month=q[1].astype(int) * 3, freq="M")


n_bis, dup_bis = 0, 0
for f in sorted(glob.glob("data/raw/bis/*.parquet")):
    ds = Path(f).stem
    b = pd.read_parquet(f)
    neg = "ref_area" if "ref_area" in b.columns else "borrowers_cty"
    dims = [k for k in b.columns if f"{k}_label" in b.columns and k not in ATTR]
    pilih = b[neg] == "ID"
    if ds == "WS_GLI":
        pilih |= True
    if ds == "WS_CBPOL":
        pilih |= b["freq"] == "M"
    if ds == "WS_CBTA":
        pilih |= b[neg].isin(["US", "XM", "JP", "CN", "GB"])
    b = b[pilih & b["freq"].isin(["M", "Q"])].copy()
    b["obs_value"] = pd.to_numeric(b["obs_value"], errors="coerce")
    for fr, g in b.groupby("freq"):
        if (ds, fr) not in JEDA_BIS:
            print(f"   ⚠️ BIS {ds} frek {fr} tanpa aturan jeda -> dilewati ({len(g):,} baris)")
            continue
        g = g.copy()
        g["bulan"] = periode(g["time_period"], fr)
        g["kunci"] = g[dims].astype(str).agg("_".join, axis=1)        # 'collection' = dimensi (XRU: rata-rata vs akhir periode)
        for kunci, h in g.groupby("kunci"):
            d = h.duplicated("bulan", keep="last")
            dup_bis += d.sum()
            h = h[~d]
            lab = " | ".join(str(h[f"{k}_label"].iloc[0]) for k in dims if str(h[f"{k}_label"].iloc[0]) not in ("", "nan"))
            tambah(h[["bulan"]].assign(nilai=h["obs_value"].values), f"bis_{ds[3:]}_{fr}_{kunci}", f"BIS {ds}: {lab}", fr, False,
                   jeda_bulan=JEDA_BIS[(ds, fr)])
            n_bis += 1
print(f"   BIS: {n_bis} seri (duplikat dibuang {dup_bis})")

# ---------------------------------------------------------------- DTS (TGA)
t = pd.read_parquet("data/raw/dts/operating_cash_balance.parquet")
t["t"] = pd.to_datetime(t["record_date"]).astype("datetime64[ns]")
a1 = t[(t["account_type"] == "Federal Reserve Account")].set_index("t")["close_today_bal"]
a2 = t[(t["account_type"] == "Treasury General Account (TGA)")].set_index("t")["close_today_bal"]
a3 = t[(t["account_type"] == "Treasury General Account (TGA) Closing Balance")].set_index("t")["open_today_bal"]
tga = pd.concat([a1, a2, a3]).astype(float)
tga = tga[~tga.index.duplicated(keep="last")].sort_index()
ttl = t[t["account_type"] == "Tax and Loan Note Accounts (Table V)"].set_index("t")["close_today_bal"].astype(float)
ttl = ttl[~ttl.index.duplicated(keep="last")]
kas = tga.add(ttl.reindex(tga.index).fillna(0))
for nm, s, jd in [("tga", tga, "saldo TGA di The Fed"), ("kas_operasi", kas, "kas operasi (TGA + TT&L)")]:
    rilis = pd.Series(s.index + BDay(1), index=s.index)
    tambah(bulanan_terakhir(s.index.to_series(), rilis, s), f"dts_{nm}_akhir", f"DTS: {jd}, akhir bulan (juta USD)", "M", True)
    tambah(bulanan_rata(rilis, s), f"dts_{nm}_rata", f"DTS: {jd}, rata-rata bulan (juta USD)", "M", True)
print(f"   DTS: TGA {tga.index.min().date()}..{tga.index.max().date()} ({len(tga):,} hari); "
      f"celah > 7 hari: {(tga.index.to_series().diff() > pd.Timedelta(days=7)).sum()}")

# ---------------------------------------------------------------- Lelang Treasury
l = pd.read_parquet("data/raw/lelang_as/semua.parquet")
l = l[(l["inflation_index_security"].astype(str) != "Yes") & (l["floating_rate"].astype(str) != "Yes")].copy()


def tenor(s):
    m = re.match(r"^(\d+)-Year(?: (\d+)-Month)?$", s)
    if m:
        return f"{int(round(int(m[1]) + int(m[2] or 0) / 12))}y"
    m = re.match(r"^(\d+)-Week$", s)
    return f"{int(m[1])}w" if m else None


l["tenor"] = l["security_term"].astype(str).str.strip().map(tenor)
l = l[l["tenor"].isin(["4w", "8w", "13w", "17w", "26w", "52w", "2y", "3y", "5y", "7y", "10y", "20y", "30y"])]
l["rilis"] = pd.to_datetime(l["auction_date"]).astype("datetime64[ns]") + pd.Timedelta(days=1)
for k in ["bid_to_cover_ratio", "indirect_bidder_accepted", "comp_accepted"]:
    l[k] = pd.to_numeric(l[k], errors="coerce")
l["porsi_indirect"] = l["indirect_bidder_accepted"] / l["comp_accepted"].where(l["comp_accepted"] > 0)
for tn, g in l.groupby("tenor"):
    tambah(bulanan_rata(g["rilis"], g["bid_to_cover_ratio"]), f"lelang_btc_{tn}", f"Lelang Treasury {tn}: bid-to-cover rata bulan", "M", True)
    tambah(bulanan_rata(g["rilis"], g["porsi_indirect"]), f"lelang_indirect_{tn}", f"Lelang Treasury {tn}: porsi indirect bidder", "M", True)
print(f"   lelang: {len(l):,} lelang nominal, tenor {sorted(l['tenor'].unique())}")

# ---------------------------------------------------------------- Wikipedia
w = pd.read_parquet("data/raw/histori/wikipedia/semua.parquet")
w["rilis"] = pd.to_datetime(w["tanggal"]).astype("datetime64[ns]") + pd.Timedelta(days=1)
for (wk, ar), g in w.groupby(["wiki", "artikel"]):
    kode = f"wiki_{wk.split('.')[0]}_{ar}"
    tambah(bulanan_rata(g["rilis"], pd.to_numeric(g["pembaca"], errors="coerce")), kode, f"Wikipedia {wk} {ar}: rata pembaca/hari",
           "M", True)
print(f"   Wikipedia: {w.groupby(['wiki', 'artikel']).ngroups} seri")

# ---------------------------------------------------------------- Pangan
p = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob("data/raw/histori/pangan/*.parquet"))], ignore_index=True)
p["rilis"] = pd.to_datetime(p["tanggal"]).astype("datetime64[ns]") + pd.Timedelta(days=1)
p["harga"] = pd.to_numeric(p["harga"], errors="coerce")
p = p[p["harga"] > 0]
p = p.drop_duplicates(["tanggal", "jenis_harga", "wilayah", "komoditas"], keep="last")
p["bulan"] = p["rilis"].dt.to_period("M")
pg = p.groupby(["jenis_harga", "wilayah", "komoditas", "bulan"], as_index=False)["harga"].mean()
n_pg = 0
for (jh, wl, km), g in pg.groupby(["jenis_harga", "wilayah", "komoditas"]):
    kode = "pangan_" + re.sub(r"[^a-z0-9]+", "_", f"{jh}_{wl}_{km}".lower()).strip("_")
    tambah(g[["bulan"]].assign(nilai=g["harga"].values), kode, f"Pangan PIHPS {jh} | {wl} | {km} (Rp)", "M", False)
    n_pg += 1
print(f"   pangan: {n_pg} seri")

# ---------------------------------------------------------------- simpan
out = pd.concat(potong, ignore_index=True)
for k in ["seri", "kode", "judul", "frek"]:
    out[k] = out[k].astype("string")
dup = out.duplicated(["seri", "bulan"]).sum()
assert dup == 0, f"duplikat seri-bulan {dup}"
assert (out["tersedia"] > out["bulan"]).all(), "ada data tersedia sebelum/di akhir bulannya sendiri"
Path("data/olah").mkdir(parents=True, exist_ok=True)
out.to_parquet("data/olah/panel_lain.parquet", index=False)
r = out.groupby("seri").agg(judul=("judul", "first"), frek=("frek", "first"), awal=("bulan", "min"), akhir=("bulan", "max"),
                            n=("nilai", "size"), n_latih=("bulan", lambda s: ((s >= "2005-01-01") & (s <= "2018-12-31")).sum()))
r.to_parquet("data/olah/panel_lain_ringkas.parquet")
grup = out.drop_duplicates("seri")["kode"].str.split("_").str[0].value_counts().to_dict()
print(f"✅ panel lain: {len(out):,} baris, {out['seri'].nunique():,} seri {grup}; "
      f"cukup latih (M >= 120 / Q >= 40): {((r['frek'] == 'M') & (r['n_latih'] >= 120)).sum() + ((r['frek'] == 'Q') & (r['n_latih'] >= 40)).sum():,}")
