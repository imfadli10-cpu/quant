"""
RISET #30: KAS PEMERINTAH AS DI THE FED (TGA) NAIK = LIKUIDITAS DOLAR DISEDOT -> SAHAM INDONESIA & AS MINGGU DEPAN
===============================================================================================================

DUGAAN (ditulis 2026-11-21 SEBELUM menghitung hubungan apa pun; di-commit sebelum dijalankan)
-----------------------------------------------------------------------------------------
Saat Kemenkeu AS menumpuk kas di rekeningnya di The Fed (TGA naik: penerimaan pajak / penerbitan utang > belanja),
cadangan perbankan berkurang = likuiditas dolar tersedot -> aset berisiko (terutama pasar berkembang) melemah.
TGA turun = likuiditas disuntik -> aset berisiko menguat. Dugaan: hubungan NEGATIF antara kenaikan TGA minggu w dan
return minggu w+1. Narasi ini populer sejak 2020-2022; di data 2005-2018 TGA jauh lebih kecil -> perkiraan jujur t < 2.

DATA: DTS `operating_cash_balance`, account_type 'Federal Reserve Account' (saldo penutupan, juta USD), 2005-10..2018.
WAKTU: DTS hari d terbit sore hari bursa berikutnya (~16:00 New York). Sinyal minggu w (Sabtu-Jumat) = perubahan saldo
  KAMIS(w) - KAMIS(w-1): angka Kamis terbit Jumat sore NY = Sabtu pagi WIB -> diketahui sebelum pasar buka Senin.
  Sinyal dibagi simpangan baku perubahan mingguan 52 minggu SEBELUMNYA (z, hanya masa lalu).
TARGET (minggu w+1): sesudah tutup hari bursa pertama w+1 s/d tutup hari bursa pertama w+2 (fungsi riset #20).
  IDX = keranjang 30 saham paling likuid (riset #4/#15); EIDO & SPY = Adj Close (bersih/saham_as).
UJI (3; dua arah; |t| > 3; t robust White):
  U1 IDX keranjang 30 <- z kenaikan TGA.   U2 EIDO <- z.   U3 SPY <- z.
Data uji 2019+ DIKUNCI. Uji kode: --tes-tiruan (-0,3% per +1 z) & --tes-kosong.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BATAS_LATIH = pd.Timestamp("2018-12-31")
BUKA_DATA_UJI = "--buka-uji" in sys.argv
TES_TIRUAN, TES_KOSONG = "--tes-tiruan" in sys.argv, "--tes-kosong" in sys.argv
P = "W-FRI"


def t_robust(y, x):
    d = pd.concat([y, x], axis=1).dropna()
    yy, xx = d.iloc[:, 0].values, d.iloc[:, 1].values
    xc = xx - xx.mean()
    b = (xc * (yy - yy.mean())).sum() / (xc ** 2).sum()
    e = yy - yy.mean() - b * xc
    return b, b / (np.sqrt((xc ** 2 * e ** 2).sum()) / (xc ** 2).sum()), len(d)


def mingguan_dari_harian(r_harian):
    """Return minggu w+1 per minggu sinyal w: sesudah tutup hari bursa pertama w+1 s/d tutup hari bursa pertama w+2."""
    hari = r_harian.index
    mg = hari.to_period(P)
    awal = pd.Series(hari, index=hari).groupby(mg).min()
    hasil = {}
    for w in awal.index:
        if w + 1 not in awal.index or w + 2 not in awal.index:
            continue
        r = r_harian[(r_harian.index > awal[w + 1]) & (r_harian.index <= awal[w + 2])]
        if len(r):
            hasil[w] = np.prod(1 + r) - 1
    return pd.Series(hasil)


def sinyal_tga(saldo_harian):
    """Perubahan saldo Kamis->Kamis per minggu (Sabtu-Jumat), dibagi sb 52 minggu SEBELUMNYA."""
    s = saldo_harian.sort_index()
    kamis = s[s.index.day_of_week <= 3]                       # hari kerja Senin-Kamis; ambil hari terakhir <= Kamis tiap minggu
    per_minggu = kamis.groupby(kamis.index.to_period(P)).last()
    d = per_minggu.diff()
    sb = d.shift(1).rolling(52, min_periods=26).std()
    return d / sb


if TES_TIRUAN or TES_KOSONG:
    acak = np.random.default_rng(30)
    hari = pd.bdate_range("2005-10-03", "2026-11-13").astype("datetime64[ns]")
    saldo = pd.Series(np.cumsum(acak.normal(0, 5000, len(hari))) + 100000, index=hari)
    z = sinyal_tga(saldo)
    mg = pd.period_range(hari[0], hari[-1], freq=P)
    dasar = {k: pd.Series(acak.normal(0.002, 0.03, len(mg)), index=mg) for k in ["idx", "eido", "spy"]}
    if TES_TIRUAN:
        for k in dasar:
            dasar[k] = dasar[k] - 0.003 * z.reindex(mg).fillna(0)
    r_idx, r_eido, r_spy = dasar["idx"], dasar["eido"], dasar["spy"]
    print(f"🧪 MODE TES: data PALSU {'dengan pola (-0,3% per +1 z)' if TES_TIRUAN else 'tanpa pola'}")
else:
    d = pd.read_parquet("data/raw/dts/operating_cash_balance.parquet")
    d = d[d["account_type"].astype(str) == "Federal Reserve Account"]
    saldo = pd.Series(d["close_today_bal"].values, index=pd.DatetimeIndex(d["record_date"])).dropna()
    saldo = saldo[~saldo.index.duplicated(keep="last")]
    z = sinyal_tga(saldo)
    print(f"🏦 TGA (Federal Reserve Account): {len(saldo)} hari, {saldo.index.min():%Y-%m} s/d {saldo.index.max():%Y-%m}; "
          f"median 2006 {saldo.loc['2006'].median():,.0f} | 2018 {saldo.loc['2018'].median():,.0f} juta USD")
    kode = Path("riset_15_ramadan.py").read_text(encoding="utf-8").split("# ===== Label kalender =====")[0]
    ns, simpan = {}, sys.argv
    sys.argv = [sys.argv[0]]
    exec(compile(kode, "riset_15_bagian", "exec"), ns)
    sys.argv = simpan
    r_idx = mingguan_dari_harian(ns["ret_keranjang"].dropna())
    import duckdb
    con = duckdb.connect()
    def as_harian(k):
        e = con.execute(f"""SELECT CAST(tanggal AS DATE) t, "Adj Close" a FROM read_parquet('data/bersih/saham_as.parquet')
                            WHERE kode = '{k}' ORDER BY 1""").df()
        return pd.Series(e["a"].values, index=pd.DatetimeIndex(e["t"])).pct_change().dropna()
    r_eido, r_spy = mingguan_dari_harian(as_harian("EIDO")), mingguan_dari_harian(as_harian("SPY"))

print(f"🔒 Data uji {'DIBUKA' if BUKA_DATA_UJI else 'DIKUNCI'}.\n")
for nama, r in [("U1 IDX keranjang 30", r_idx), ("U2 EIDO", r_eido), ("U3 SPY", r_spy)]:
    akhir = pd.Series([(w + 2).end_time.normalize() for w in r.index], index=r.index)   # paling lambat minggu w+2
    pilih = (akhir > BATAS_LATIH + pd.Timedelta(days=14)) if BUKA_DATA_UJI else (akhir <= BATAS_LATIH)
    y = r[pilih.values]
    b, t, n = t_robust(y, z.reindex(y.index))
    print(f"   {nama:20}: +1 z kenaikan TGA -> minggu depan {b:+.3%}, t robust {t:+.1f} ({n} minggu)")
