"""
RISET #25: GEMPA BESAR DI INDONESIA -> SAHAM IDX HARI-HARI BERIKUTNYA, data LATIH saja
=================================================================================

DUGAAN (ditulis 2026-11-21 SEBELUM menghitung apa pun; di-commit sebelum dijalankan)
--------------------------------------------------------------------------------
Gempa besar dangkal di wilayah Indonesia = kerusakan nyata + rasa takut. Literatur bencana (mis. Worthington & Valadkhani
2004; Shan & Gong 2012 Wenchuan; Ferreira & Karali 2015) menemukan reaksi negatif jangka pendek lalu sebagian pulih.
  H1 (reaksi): keranjang IDX turun di hari bursa pertama setelah gempa (diagnosis, bukan strategi).
  H2 (pemulihan / reaksi berlebihan): setelah reaksi itu, 5 hari bursa berikutnya keranjang NAIK di atas biasanya
      (investor ritel panik lalu harga kembali) -> strategi beli setelah gempa.
Perkiraan jujur: kebanyakan gempa besar terjadi jauh dari pusat ekonomi (Jakarta/Surabaya); efek kecil. Saya kira t < 2.

PERISTIWA: USGS, magnitudo >= 6,5, kedalaman <= 70 km (dangkal = merusak), episentrum di kotak Indonesia
  (bujur 94..142, lintang -11..6). Dibersihkan dari gempa susulan: peristiwa yang terjadi <= 7 hari setelah peristiwa
  sebelumnya (yang dipakai) dibuang.
WAKTU: waktu gempa UTC -> WIB (+7). d0 = hari bursa pertama yang PENUTUPANNYA (16:00 WIB) sesudah gempa
  (gempa malam/akhir pekan -> hari bursa berikutnya; gempa saat jam bursa -> hari itu juga).
RETURN: keranjang 30 saham paling likuid (riset #4/#15), return harian dikurangi rata-rata return harian 250 hari
  bursa SEBELUM d0 (abnormal).
UJI (3; dua arah; |t| > 3; t = rata-rata abnormal antar-peristiwa / (sb / akar n)):
  U1 reaksi: abnormal hari d0.
  U2 pemulihan (bisa dijalankan): abnormal kumulatif d0+1 .. d0+5 (beli tutup d0, jual tutup d0+5; biaya 0,4% dicatat).
  U3 sama dengan U2 tapi hanya magnitudo >= 7,0 (dugaan: efek lebih besar untuk gempa lebih besar).
Data uji 2019+ DIKUNCI (peristiwa dengan d0+5 <= 2018-12-31). Uji kode: --tes-tiruan (d0 -1%, d0+1..5 +0,2%/hari) & --tes-kosong.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BATAS_LATIH = pd.Timestamp("2018-12-31")
BUKA_DATA_UJI = "--buka-uji" in sys.argv
TES_TIRUAN, TES_KOSONG = "--tes-tiruan" in sys.argv, "--tes-kosong" in sys.argv
KOTAK = (94, 142, -11, 6)
H = 5


def t_rata(x):
    x = pd.Series(x).dropna()
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else np.nan


def peristiwa_gempa():
    bag = [pd.read_parquet(f, columns=["time", "latitude", "longitude", "depth", "mag", "place"])
           for f in sorted(Path("data/raw/histori/gempa").glob("*.parquet"))]
    g = pd.concat(bag, ignore_index=True)
    t = pd.DatetimeIndex(pd.to_datetime(g["time"]))
    g["time"] = t.tz_localize(None) if t.tz is not None else t
    x0, x1, y0, y1 = KOTAK
    g = g[g["longitude"].between(x0, x1) & g["latitude"].between(y0, y1) & (g["mag"] >= 6.5) & (g["depth"] <= 70)]
    g = g.sort_values("time").drop_duplicates("time")
    pakai, terakhir = [], None
    for _, r in g.iterrows():                       # buang gempa susulan (<= 7 hari setelah peristiwa yang dipakai)
        if terakhir is None or r["time"] - terakhir > pd.Timedelta(days=7):
            pakai.append(r)
            terakhir = r["time"]
    return pd.DataFrame(pakai).reset_index(drop=True)


if TES_TIRUAN or TES_KOSONG:
    acak = np.random.default_rng(25)
    hari = pd.bdate_range("2001-01-01", "2026-11-13").astype("datetime64[ns]")
    r_harian = pd.Series(acak.normal(0.0005, 0.012, len(hari)), index=hari)
    waktu = pd.to_datetime(acak.choice(pd.date_range("2002-01-01", "2026-10-01", freq="h"), 120, replace=False)).sort_values()
    ev = pd.DataFrame({"time": waktu, "mag": acak.choice([6.6, 6.8, 7.1, 7.5], 120), "place": "palsu"})
    print(f"🧪 MODE TES: data PALSU {'dengan pola (d0 -1%, d0+1..5 +0,2%/hari)' if TES_TIRUAN else 'tanpa pola'}")
else:
    ev = peristiwa_gempa()
    kode = Path("riset_15_ramadan.py").read_text(encoding="utf-8").split("# ===== Label kalender =====")[0]
    ns, simpan = {}, sys.argv
    sys.argv = [sys.argv[0]]
    exec(compile(kode, "riset_15_bagian", "exec"), ns)
    sys.argv = simpan
    r_harian = ns["ret_keranjang"].dropna()

hari = r_harian.index
tutup_utc = hari + pd.Timedelta(hours=9)                         # 16:00 WIB = 09:00 UTC
posisi = np.searchsorted(tutup_utc.values, ev["time"].values.astype("datetime64[ns]"), side="left")
ev["i0"] = posisi
ev = ev[(ev["i0"] >= 250) & (ev["i0"] + H < len(hari))].copy()
ev["d0"] = hari[ev["i0"].values]
if TES_TIRUAN:
    for i0 in ev["i0"]:
        r_harian.iloc[i0] -= 0.01
        r_harian.iloc[i0 + 1:i0 + 1 + H] += 0.002
target = pd.Series(hari[(ev["i0"] + H).values], index=ev.index)
ev = ev[(target > BATAS_LATIH).values] if BUKA_DATA_UJI else ev[(target <= BATAS_LATIH).values]
print(f"🔒 Data uji {'DIBUKA' if BUKA_DATA_UJI else 'DIKUNCI'}.\n")

baris = []
nilai = r_harian.values
for _, e in ev.iterrows():
    i0 = int(e["i0"])
    normal = nilai[i0 - 250:i0].mean()
    baris.append({"d0": e["d0"], "mag": e["mag"], "tempat": e["place"], "u1": nilai[i0] - normal,
                  "u2": np.prod(1 + nilai[i0 + 1:i0 + 1 + H]) - 1 - H * normal})
h = pd.DataFrame(baris)
print(f"   {len(h)} gempa M>=6,5 dangkal di Indonesia ({h['d0'].min():%Y-%m} s/d {h['d0'].max():%Y-%m}); "
      f"M>=7,0: {(h['mag'] >= 7).sum()}")
print(f"   U1 reaksi hari d0          : {h['u1'].mean():+.3%}  t {t_rata(h['u1']):+.1f}")
print(f"   U2 pemulihan d0+1..d0+5    : {h['u2'].mean():+.3%}  t {t_rata(h['u2']):+.1f} "
      f"(bersih setelah biaya 0,4%: {h['u2'].mean() - 0.004:+.3%})")
b = h[h["mag"] >= 7]
print(f"   U3 pemulihan, hanya M>=7,0 : {b['u2'].mean():+.3%}  t {t_rata(b['u2']):+.1f} ({len(b)} peristiwa)")
print("\n   Diagnosis (bukan uji): 5 gempa terbesar")
for _, r in h.nlargest(5, "mag").iterrows():
    print(f"     {r['d0']:%Y-%m-%d} M{r['mag']:.1f} {str(r['tempat'])[:45]:45} d0 {r['u1']:+.2%} | d0+1..5 {r['u2']:+.2%}")
