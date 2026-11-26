"""
RISET #58: PENGUMUMAN LABA YANG TELAT (dibanding kebiasaan emiten sendiri) -> saham IDX 20 hari sesudahnya, data LATIH saja
======================================================================================================================
DUGAAN (ditulis 27 Nov 2026 SEBELUM hubungan keterlambatan-return dihitung; di-commit sebelum dijalankan)
Manajer cenderung MENUNDA kabar buruk (Givoly-Palmon 1982 JAR; Begley-Fischer 1998; deHaan-Shevlin-Thornock 2015 JAE: pengumuman yang
DIGESER lebih lambat dari tahun lalu = kabar lebih buruk & return pasca-pengumuman lebih rendah; investor kurang memperhatikan perubahan
jadwal). Di IDX ada tenggat laporan (OJK/BEI), tetapi waktu di dalam tenggat bebas. Dugaan: pengumuman yang >= 14 hari lebih lambat dari
pengumuman yang sama tahun lalu -> abnormal 20 hari sesudahnya LEBIH RENDAH. Bantahan: tanggal Yahoo kadang 'jam tempelan' (hari tetap
benar), cakupan hanya ~40-60 saham besar yang diliput analis, efek AS kecil (~-1% per kuartal). Perkiraan jujur: arah negatif, |t| < 2.

DATA: raw/laba_idx/semua.parquet (Yahoo earnings dates; pakai baris eps_aktual terisi = pengumuman yang SUDAH terjadi); harga & semesta
  seperti #34 (harga >= Rp100, median nilai transaksi 60 hari >= Rp1 M saat masuk; masuk tutup hari bursa ke-2 setelah tanggal, tahan
  20 hari, abnormal = saham - keranjang 30 likuid).
KETERLAMBATAN: pasangan = pengumuman saham yang sama dengan tanggal terdekat ke (tanggal - 365 hari), dalam +-45 hari;
  telat = tanggal - pasangan - 365 (hari). TELAT = telat >= +14; tanpa pasangan = tidak dipakai. Diketahui SAAT pengumuman (tidak bocor).
UJI (2; |t| > 3; per KUARTAL kalender lalu t antar kuartal, karena peristiwa berkelompok waktu):
  U1 rata-rata abnormal TELAT - TIDAK TELAT per kuartal (kuartal dgn >= 3 peristiwa telat & >= 10 total).            Dugaan: negatif.
  U2 kemiringan abnormal ~ telat (hari, dibatasi +-60) per kuartal (Fama-MacBeth; kuartal >= 15 peristiwa).          Dugaan: negatif.
Info: kejutan laba (EPS) rata-rata kelompok telat vs tidak (mekanisme: telat = kabar buruk?), pengumuman DIPERCEPAT (<= -14), paruh.
Kegunaan kalau lolos: saringan HINDARI / fitur model penampang. Data uji 2019+ DIKUNCI. Uji kode: --tes-tiruan (telat -> -2%/20 hari) & --tes-kosong.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BATAS_LATIH = pd.Timestamp("2018-12-31")
TES_TIRUAN, TES_KOSONG = "--tes-tiruan" in sys.argv, "--tes-kosong" in sys.argv
TAHAN, AMBANG = 20, 14
if "--potong-data" in sys.argv:                 # cek kebocoran: semua data > 2018 dibuang SEBELUM dibaca
    _baca = pd.read_parquet

    def _terpotong(*a, **k):
        d = _baca(*a, **k)
        if isinstance(d.index, pd.DatetimeIndex):
            d = d[d.index <= BATAS_LATIH]
        for c in ("tanggal", "Date", "waktu_wib"):
            if c in d.columns and pd.api.types.is_datetime64_any_dtype(d[c]):
                d = d[(d[c].dt.tz_localize(None) if d[c].dt.tz is not None else d[c]) <= BATAS_LATIH]
        return d
    pd.read_parquet = _terpotong


def t_rata(x):
    x = pd.Series(x).dropna()
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else np.nan


if TES_TIRUAN or TES_KOSONG:
    acak = np.random.default_rng(58)
    hari = pd.bdate_range("2005-01-03", "2026-11-13").astype("datetime64[ns]")
    kode = [f"S{i:03d}" for i in range(60)]
    r = acak.normal(0.0003, 0.02, (len(hari), len(kode)))
    ev = []
    for k in kode:
        for tgl in pd.date_range("2005-03-31", "2026-06-30", freq="QE"):
            ev.append({"kode": k, "waktu_wib": tgl + pd.Timedelta(days=int(acak.integers(25, 75))), "eps_aktual": 1.0, "eps_perkiraan": 1.0})
    ev = pd.DataFrame(ev)
    adj = pd.DataFrame(1000 * np.exp(np.cumsum(r, axis=0)), index=hari, columns=kode)
    tutup = adj.copy()
    median_nilai = pd.DataFrame(5e9, index=hari, columns=kode)
    r_pasar = pd.Series(0.0, index=hari)
    print(f"🧪 MODE TES: data PALSU {'dgn pola (telat >= 14 hr -> -2% selama 20 hari)' if TES_TIRUAN else 'tanpa pola'}")
else:
    sys.argv_simpan = sys.argv
    sys.argv = [sys.argv[0]]
    g = {}
    kode12 = Path("riset_12_gabung_sinyal.py").read_text(encoding="utf-8").split("baris, korelasi, lalu = [], [], {}")[0]
    exec(compile(kode12, "riset_12_bagian", "exec"), g)
    kode15 = Path("riset_15_ramadan.py").read_text(encoding="utf-8").split("# ===== Label kalender =====")[0]
    ns = {}
    exec(compile(kode15, "riset_15_bagian", "exec"), ns)
    sys.argv = sys.argv_simpan
    adj, tutup, median_nilai, hari = g["adj"], g["tutup"], g["median_nilai"], g["hari"]
    r_pasar = ns["ret_keranjang"].reindex(hari).fillna(0)
    ev = pd.read_parquet("data/raw/laba_idx/semua.parquet")

ev = ev[ev["eps_aktual"].notna()].copy()
ev["tanggal"] = pd.to_datetime(ev["waktu_wib"]).dt.tz_localize(None).dt.normalize() if getattr(pd.to_datetime(ev["waktu_wib"]).dt, "tz", None) \
    else pd.to_datetime(ev["waktu_wib"]).dt.normalize()
ev = ev.drop_duplicates(["kode", "tanggal"]).sort_values(["kode", "tanggal"])
ev["kejutan"] = (ev["eps_aktual"] - ev["eps_perkiraan"]) / ev["eps_perkiraan"].abs()

# keterlambatan vs pengumuman setahun sebelumnya (saham yang sama)
telat = []
for k, b in ev.groupby("kode"):
    tg = b["tanggal"].values
    for t in tg:
        sasaran = t - np.timedelta64(365, "D")
        lalu = tg[tg < t - np.timedelta64(200, "D")]
        if len(lalu) == 0:
            telat.append(np.nan)
            continue
        p = lalu[np.argmin(np.abs(lalu - sasaran))]
        sel = (t - p).astype("timedelta64[D]").astype(int) - 365
        telat.append(sel if abs(sel) <= 45 else np.nan)
ev["telat"] = telat

if TES_TIRUAN:
    kol = {k: j for j, k in enumerate(adj.columns)}
    r = np.log(adj).diff().fillna(0).values.copy()
    for _, e in ev[ev["telat"] >= AMBANG].iterrows():
        i = np.searchsorted(hari.values, np.datetime64(e["tanggal"]), side="right") + 1
        r[i + 1:i + 1 + TAHAN, kol[e["kode"]]] -= 0.02 / TAHAN
    adj = pd.DataFrame(1000 * np.exp(np.cumsum(r, axis=0)), index=hari, columns=adj.columns)

nilai = adj.values
pasar_kum = np.concatenate([[1.0], np.cumprod(1 + r_pasar.values)])
kolom = {k: j for j, k in enumerate(adj.columns)}
baris = []
for _, e in ev[ev["telat"].notna()].iterrows():
    j = kolom.get(str(e["kode"]))
    if j is None:
        continue
    i1 = np.searchsorted(hari.values, np.datetime64(e["tanggal"]), side="right")
    masuk, keluar = i1 + 1, i1 + 1 + TAHAN
    if keluar >= len(hari) or not (tutup.iat[masuk, j] >= 100 and median_nilai.iat[masuk, j] >= 1e9):
        continue
    a0, a1 = nilai[masuk, j], nilai[keluar, j]
    if not (np.isfinite(a0) and np.isfinite(a1)):
        continue
    baris.append({"kode": e["kode"], "tanggal": e["tanggal"], "kuartal": e["tanggal"].to_period("Q"), "keluar": hari[keluar],
                  "telat": e["telat"], "kejutan": e["kejutan"], "abnormal": a1 / a0 - 1 - (pasar_kum[keluar + 1] / pasar_kum[masuk + 1] - 1)})
h = pd.DataFrame(baris)
h = h[h["keluar"] <= BATAS_LATIH]
print("🔒 Data uji 2019+ DIKUNCI.\n")
h["T"] = h["telat"] >= AMBANG
per_q = []
for q, b in h.groupby("kuartal"):
    baris_q = {"kuartal": q, "n": len(b), "n_telat": int(b["T"].sum())}
    if b["T"].sum() >= 3 and len(b) >= 10:
        baris_q["selisih"] = b.loc[b["T"], "abnormal"].mean() - b.loc[~b["T"], "abnormal"].mean()
    if len(b) >= 15:
        x = b["telat"].clip(-60, 60)
        baris_q["miring"] = np.polyfit(x, b["abnormal"], 1)[0] * 10 if x.std() > 0 else np.nan     # per 10 hari
    per_q.append(baris_q)
q = pd.DataFrame(per_q).set_index("kuartal")
print(f"   {len(h):,} peristiwa berpasangan ({h['tanggal'].min():%Y-%m} s/d {h['tanggal'].max():%Y-%m}), TELAT {h['T'].sum()} "
      f"({h['T'].mean():.0%}); median telat {h['telat'].median():+.0f} hari; {q['selisih'].notna().sum()} kuartal U1, {q['miring'].notna().sum()} kuartal U2")
s = q["selisih"].dropna()
print(f"   U1 TELAT - tidak telat (abnormal 20 hari): {s.mean():+.2%} per kuartal, t {t_rata(s):+.2f} (paruh {t_rata(s.iloc[:len(s) // 2]):+.1f}/{t_rata(s.iloc[len(s) // 2:]):+.1f})")
m = q["miring"].dropna()
print(f"   U2 kemiringan abnormal per +10 hari telat : {m.mean():+.3%}, t {t_rata(m):+.2f}")
print(f"   info: abnormal TELAT {h.loc[h['T'], 'abnormal'].mean():+.2%} vs lainnya {h.loc[~h['T'], 'abnormal'].mean():+.2%}; "
      f"DIPERCEPAT (<= -14) {h.loc[h['telat'] <= -AMBANG, 'abnormal'].mean():+.2%} ({(h['telat'] <= -AMBANG).sum()} peristiwa)")
kj = h["kejutan"].replace([np.inf, -np.inf], np.nan)
print(f"   info mekanisme: median kejutan EPS TELAT {kj[h['T']].median():+.1%} vs lainnya {kj[~h['T']].median():+.1%}; "
      f"porsi kejutan negatif {(kj[h['T']] < 0).mean():.0%} vs {(kj[~h['T']] < 0).mean():.0%}")
hasil = {"U1": t_rata(s), "U2": t_rata(m)}
lolos = [k for k, v in hasil.items() if abs(v) > 3]
print(f"\n   KEPUTUSAN #58 (|t| > 3): {'✅ ' + ', '.join(lolos) if lolos else '❌ tidak ada yang lolos'}")
