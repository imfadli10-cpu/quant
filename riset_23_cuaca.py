"""
RISET #23: CUACA KOTA BURSA -> RETURN SAHAM HARI ITU (efek "suasana hati"), data LATIH saja
=========================================================================================

DUGAAN (ditulis 2026-11-20 SEBELUM hubungan apa pun dilihat; di-commit sebelum dijalankan)
--------------------------------------------------------------------------------------
Hirshleifer & Shumway (2003, JF "Good Day Sunshine"): hari cerah di kota bursa -> suasana hati investor lebih baik ->
return saham lebih tinggi hari itu (26 bursa, 1982-1997). Di Jakarta, mayoritas pialang & investor aktif ada di kota yang
sama dengan bursa; hujan lebat juga membuat macet/banjir (aktivitas & suasana hati turun).
Perkiraan jujur: penelitian lanjutan menemukan efek melemah/hilang di data baru; dugaan saya t < 2.

DATA: Open-Meteo (reanalisis ERA5, bukan stasiun) harian: sunshine_duration (detik/hari), precipitation_sum (mm).
  IDX: keranjang 30 saham paling likuid (riset #4/#15), return tutup kemarin -> tutup hari ini, bobot sama.
  SPY: return Adj Close harian (sejak 1993), cuaca New York.
  "Cerah abnormal" = sinar matahari dikurangi rata-rata bulan kalender yang sama (rata-rata dihitung HANYA dari data latih),
  dibagi simpangan baku -> z.
UJI (3; dua arah; |t| > 3; t robust White):
  U1 IDX keranjang 30 <- z sinar matahari Jakarta (2002-2018)
  U2 IDX keranjang 30: hari hujan LEBAT Jakarta (>= 20 mm) vs hari lain (t Welch)
  U3 SPY <- z sinar matahari New York (1993-2018), replikasi literatur
Ini uji DIAGNOSIS suasana hati (cuaca seharian baru diketahui sore). Kalau ada yang lolos, versi yang bisa dijalankan
(prakiraan pagi, beli buka -> jual tutup) dirancang sebagai riset terpisah.
Data uji 2019+ DIKUNCI. Uji kode: --tes-tiruan (0,05%/hari per +1 z) & --tes-kosong.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BATAS_LATIH = pd.Timestamp("2018-12-31")
BUKA_DATA_UJI = "--buka-uji" in sys.argv
TES_TIRUAN, TES_KOSONG = "--tes-tiruan" in sys.argv, "--tes-kosong" in sys.argv


def t_robust(y, x):
    d = pd.concat([y, x], axis=1).dropna()
    yy, xx = d.iloc[:, 0].values, d.iloc[:, 1].values
    xc = xx - xx.mean()
    b = (xc * (yy - yy.mean())).sum() / (xc ** 2).sum()
    e = yy - yy.mean() - b * xc
    return b, b / (np.sqrt((xc ** 2 * e ** 2).sum()) / (xc ** 2).sum()), len(d)


def t_welch(a, b):
    a, b = pd.Series(a).dropna(), pd.Series(b).dropna()
    return (a.mean() - b.mean()) / np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))


def baca_cuaca(kota):
    c = pd.read_parquet(f"data/raw/cuaca/{kota}.parquet")
    c.index = pd.DatetimeIndex(pd.to_datetime(c.index)).normalize().astype("datetime64[ns]")
    return c


def z_musiman(s):
    """Kurangi rata-rata & bagi simpangan baku per bulan kalender; statistik dari data LATIH saja."""
    latih = s[s.index <= BATAS_LATIH]
    rata = latih.groupby(latih.index.month).mean()
    sb = latih.groupby(latih.index.month).std()
    return (s - rata.reindex(s.index.month).values) / sb.reindex(s.index.month).values


def periode(s):
    return s[s.index > BATAS_LATIH] if BUKA_DATA_UJI else s[s.index <= BATAS_LATIH]


if TES_TIRUAN or TES_KOSONG:
    acak = np.random.default_rng(23)
    hari = pd.bdate_range("1993-01-04", "2026-11-13").astype("datetime64[ns]")
    sinar_jkt = pd.Series(acak.normal(0, 1, len(hari)), index=hari)
    sinar_ny = pd.Series(acak.normal(0, 1, len(hari)), index=hari)
    hujan = pd.Series(acak.exponential(6, len(hari)), index=hari)
    r_idx = pd.Series(acak.normal(0.0005, 0.012, len(hari)), index=hari)
    r_spy = pd.Series(acak.normal(0.0004, 0.011, len(hari)), index=hari)
    if TES_TIRUAN:
        r_idx += 0.0005 * sinar_jkt - 0.002 * (hujan >= 20)
        r_spy += 0.0005 * sinar_ny
    r_idx = r_idx[r_idx.index >= "2002-05-01"]
    print(f"🧪 MODE TES: data PALSU {'dengan pola (+0,05%/z sinar; hujan lebat -0,2%)' if TES_TIRUAN else 'tanpa pola'}")
else:
    jkt, ny = baca_cuaca("jakarta"), baca_cuaca("new_york")
    sinar_jkt, sinar_ny = z_musiman(jkt["sunshine_duration"]), z_musiman(ny["sunshine_duration"])
    hujan = jkt["precipitation_sum"]
    kode = Path("riset_15_ramadan.py").read_text(encoding="utf-8").split("# ===== Label kalender =====")[0]
    ns, simpan = {}, sys.argv
    sys.argv = [sys.argv[0]]
    exec(compile(kode, "riset_15_bagian", "exec"), ns)
    sys.argv = simpan
    r_idx = ns["ret_keranjang"]
    import duckdb
    e = duckdb.connect().execute("""SELECT CAST(tanggal AS DATE) t, "Adj Close" a FROM read_parquet('data/bersih/saham_as.parquet')
                                    WHERE kode = 'SPY' ORDER BY 1""").df()
    r_spy = pd.Series(e["a"].values, index=pd.DatetimeIndex(e["t"]).astype("datetime64[ns]")).pct_change().dropna()

print(f"🔒 Data uji {'DIBUKA' if BUKA_DATA_UJI else 'DIKUNCI'}.\n")
r = periode(r_idx)
b, t, n = t_robust(r, sinar_jkt.reindex(r.index))
print(f"   U1 IDX keranjang 30 <- sinar Jakarta : {b:+.4%} per +1 z, t robust {t:+.1f} ({n} hari, "
      f"{r.index.min():%Y-%m} s/d {r.index.max():%Y-%m})")
lebat = hujan.reindex(r.index) >= 20
print(f"   U2 hujan lebat Jakarta (>= 20 mm): {r[lebat].mean():+.3%}/hari ({lebat.sum()} hari) vs lain {r[~lebat].mean():+.3%} "
      f"-> selisih t {t_welch(r[lebat], r[~lebat]):+.1f}")
rs = periode(r_spy)
b, t, n = t_robust(rs, sinar_ny.reindex(rs.index))
print(f"   U3 SPY <- sinar New York           : {b:+.4%} per +1 z, t robust {t:+.1f} ({n} hari, "
      f"{rs.index.min():%Y-%m} s/d {rs.index.max():%Y-%m})")
# Diagnosis (bukan uji): hari paling cerah vs paling mendung (kuintil)
q = pd.qcut(sinar_jkt.reindex(r.index), 5, labels=False)
print("   diagnosis IDX per kuintil sinar (1 = paling mendung): " +
      "  ".join(f"{k + 1}: {r[q == k].mean():+.3%}" for k in range(5)))
