"""
RISET #15: EFEK RAMADAN & LIBUR LEBARAN di saham IDX
====================================================

DUGAAN (ditulis 2026-11-20, SEBELUM melihat return apa pun di sekitar Ramadan/Lebaran)
------------------------------------------------------------------------------------
H1 Ramadan: return saham selama Ramadan LEBIH TINGGI dari hari biasa (Białkowski-Etebari-Wisniewski 2012, 14 negara
   mayoritas Muslim: suasana hati/optimisme investor membaik).
H2 Menjelang libur Lebaran: 2 hari bursa terakhir sebelum libur Lebaran LEBIH TINGGI (efek menjelang libur, Ariel 1990;
   libur Lebaran = libur terpanjang bursa Indonesia).
Perkiraan jujur: hanya ~18 Ramadan & ~18 Lebaran di data latih -> daya uji rendah. Efek kalender yang terkenal sering
sudah hilang. Saya kira t < 2. Semua uji DUA ARAH, |t| > 3.

INSTRUMEN (bisa dibeli): keranjang 30 saham paling likuid (riset #4: saringan riset #2, 30 nilai transaksi terbesar
  tiap akhir bulan, bobot sama, anggota dari akhir bulan SEBELUMNYA). Return harian = rata-rata return harian anggota.
TANGGAL: Ramadan = 1 Ramadan s/d sehari sebelum 1 Syawal (kalender Umm al-Qura, pustaka hijridate; bisa beda 1 hari dari
  penetapan Indonesia). Libur Lebaran = jeda TERPANJANG antar hari bursa di sekitar 1 Syawal (+/-10 hari) di data.
  (Jadwal libur bursa diumumkan berbulan-bulan sebelumnya, jadi mengetahuinya bukan mengintip masa depan.)
UJI (3):
  U1 (H1) rata-rata return harian keranjang: hari Ramadan - hari bukan Ramadan (t Welch).
  U2 (H2) rata-rata return harian: 2 hari sebelum libur Lebaran - hari biasa (t Welch).
  U3 (bisa dijalankan): tiap tahun, "return abnormal Ramadan" = return keranjang selama Ramadan - (rata-rata return harian
     tahun itu di luar Ramadan x jumlah hari Ramadan), dikurangi biaya 0,4% (keluar-masuk sekali). t antar tahun.
Data uji 2019+ DIKUNCI (--buka-uji). Uji kode: --tes-tiruan (+0,15%/hari selama Ramadan) & --tes-kosong.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from hijridate import Gregorian, Hijri

BATAS_LATIH = pd.Timestamp("2018-12-31")
BUKA_DATA_UJI = "--buka-uji" in sys.argv
TES_TIRUAN = "--tes-tiruan" in sys.argv
TES_KOSONG = "--tes-kosong" in sys.argv
BIAYA = 0.004
N_KERANJANG = 30
MIN_HARGA, MIN_HARI_AKTIF, MAX_LOMPAT = 100, 0.8, 0.5


def jadi_tanggal(x):
    t = pd.DatetimeIndex(pd.to_datetime(x))
    if t.tz is not None:
        t = t.tz_localize(None)
    return t.normalize().astype("datetime64[ns]")


def t_welch(a, b):
    a, b = pd.Series(a).dropna(), pd.Series(b).dropna()
    return (a.mean() - b.mean()) / np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))


def nilai_t(s):
    s = pd.Series(s).dropna()
    return s.mean() / (s.std(ddof=1) / np.sqrt(len(s)))


def jadwal_ramadan(tahun_awal, tahun_akhir):
    """[(1 Ramadan, 1 Syawal)] dalam rentang tahun Masehi."""
    hasil = []
    h0 = Gregorian(tahun_awal, 1, 1).to_hijri().year
    h1 = Gregorian(tahun_akhir, 12, 31).to_hijri().year
    for th in range(h0, h1 + 1):
        r = pd.Timestamp(str(Hijri(th, 9, 1).to_gregorian()))
        s = pd.Timestamp(str(Hijri(th, 10, 1).to_gregorian()))
        hasil.append((r, s))
    return hasil


def muat_data_asli():
    adj, tutup, volume = {}, {}, {}
    for f in sorted(Path("data/raw/harga_idx").glob("*.parquet")):
        d = pd.read_parquet(f, columns=["Adj Close", "Close", "Volume"])
        d.index = jadi_tanggal(d.index)
        d = d[~d.index.duplicated(keep="last")]
        adj[f.stem], tutup[f.stem], volume[f.stem] = d["Adj Close"], d["Close"], d["Volume"]
    adj, tutup, volume = (pd.DataFrame(x).sort_index() for x in (adj, tutup, volume))
    aktif = volume.fillna(0) > 0
    hari = aktif.index[(aktif.sum(axis=1) >= 10) & (aktif.index.day_of_week < 5)]
    return adj.loc[hari], tutup.loc[hari], volume.loc[hari]


def buat_data_tiruan(dengan_pola):
    """100 saham palsu; hari libur Lebaran palsu (5 hari kerja setelah 1 Syawal dihapus dari kalender bursa).
    Pola (kalau ada): semua saham +0,15% per hari selama Ramadan."""
    acak = np.random.default_rng(15)
    hari = pd.bdate_range("2001-01-01", "2026-11-13").astype("datetime64[ns]")
    for r, s in jadwal_ramadan(2001, 2026):
        hari = hari[~((hari >= s - pd.Timedelta(days=1)) & (hari <= s + pd.Timedelta(days=6)))]
    kolom = [f"S{i:03d}" for i in range(100)]
    harian = pd.DataFrame(acak.normal(0.0003, 0.02, (len(hari), 100)), index=hari, columns=kolom)
    harian = harian.add(acak.normal(0, 0.01, len(hari)), axis=0)
    if dengan_pola:
        di_ramadan = np.zeros(len(hari), dtype=bool)
        for r, s in jadwal_ramadan(2001, 2026):
            di_ramadan |= (hari >= r) & (hari < s)
        harian.loc[di_ramadan] += 0.0015
    adj = 1000 * np.exp(harian.cumsum())
    return adj, adj.copy(), pd.DataFrame(1e7, index=hari, columns=kolom)


if TES_TIRUAN or TES_KOSONG:
    adj, tutup, volume = buat_data_tiruan(TES_TIRUAN)
    print(f"🧪 MODE TES: data PALSU {'dengan pola Ramadan +0,15%/hari' if TES_TIRUAN else 'tanpa pola'}")
else:
    adj, tutup, volume = muat_data_asli()
hari = adj.index
print(f"📥 {adj.shape[1]} saham, {len(hari):,} hari bursa, {hari[0].date()} s/d {hari[-1].date()}")

# ===== Keranjang 30 saham paling likuid (anggota dari akhir bulan sebelumnya) =====
aktif = volume.fillna(0) > 0
median_nilai = (tutup * volume).where(aktif).rolling(60, min_periods=40).median()
porsi_aktif = aktif.rolling(250, min_periods=250).mean()
ret_h = adj.pct_change(fill_method=None)
lompat = ret_h.abs().rolling(250, min_periods=200).max()
akhir_bulan = pd.Series(hari, index=hari).groupby(hari.to_period("M")).max()
anggota = {}
for bln, tgl in akhir_bulan.items():
    ok = ((tutup.loc[tgl] >= MIN_HARGA) & (porsi_aktif.loc[tgl] >= MIN_HARI_AKTIF) & (lompat.loc[tgl] < MAX_LOMPAT)
          & median_nilai.loc[tgl].notna())
    pilih = median_nilai.loc[tgl][ok].nlargest(N_KERANJANG).index
    if len(pilih) >= N_KERANJANG * 0.8:
        anggota[bln + 1] = list(pilih)
ret_keranjang = pd.Series({d: ret_h.loc[d, anggota[d.to_period("M")]].mean()
                           for d in hari[1:] if d.to_period("M") in anggota}).dropna()

# ===== Label kalender =====
jadwal = jadwal_ramadan(hari[0].year, hari[-1].year)
label = pd.DataFrame(index=ret_keranjang.index)
label["ramadan"] = False
label["pra_lebaran"] = False
tahun_ramadan = {}
for r, s in jadwal:
    di = (label.index >= r) & (label.index < s)
    label.loc[di, "ramadan"] = True
    tahun_ramadan[s.year] = (r, s)
    sekitar = hari[(hari >= s - pd.Timedelta(days=12)) & (hari <= s + pd.Timedelta(days=12))]
    if len(sekitar) < 2:
        continue
    jeda = pd.Series(sekitar[1:] - sekitar[:-1], index=sekitar[:-1])
    sebelum_libur = jeda.idxmax()                                  # hari bursa terakhir sebelum jeda terpanjang
    i = hari.get_loc(sebelum_libur)
    for d in hari[max(0, i - 1):i + 1]:                            # 2 hari bursa terakhir sebelum libur
        if d in label.index:
            label.loc[d, "pra_lebaran"] = True

if BUKA_DATA_UJI:
    pakai = label.index > BATAS_LATIH
else:
    pakai = label.index <= BATAS_LATIH
r = ret_keranjang[pakai]
lb = label[pakai]
print(f"🔒 Data uji {'DIBUKA' if BUKA_DATA_UJI else 'DIKUNCI, tidak disentuh'}. "
      f"{'DATA UJI (2019+)' if BUKA_DATA_UJI else 'DATA LATIH'}: {len(r):,} hari ({r.index[0].date()} s/d {r.index[-1].date()})\n")

biasa = r[~lb["ramadan"] & ~lb["pra_lebaran"]]
ram, pra = r[lb["ramadan"]], r[lb["pra_lebaran"]]
print(f"1️⃣  U1 Ramadan    : {ram.mean():+.3%}/hari ({len(ram)} hari) vs bukan Ramadan {r[~lb['ramadan']].mean():+.3%}/hari "
      f"-> selisih t = {t_welch(ram, r[~lb['ramadan']]):+.1f}")
print(f"2️⃣  U2 pra-Lebaran: {pra.mean():+.3%}/hari ({len(pra)} hari) vs hari biasa {biasa.mean():+.3%}/hari "
      f"-> selisih t = {t_welch(pra, biasa):+.1f}")

abn = {}
for th, (rr, s) in tahun_ramadan.items():
    th_hari = r[r.index.year == th]
    in_r = th_hari[(th_hari.index >= rr) & (th_hari.index < s)]
    luar = th_hari[~((th_hari.index >= rr) & (th_hari.index < s))]
    if len(in_r) < 10 or len(luar) < 100:
        continue
    abn[th] = (np.prod(1 + in_r) - 1) - luar.mean() * len(in_r) - BIAYA
abn = pd.Series(abn)
print(f"3️⃣  U3 abnormal Ramadan per tahun (bersih biaya 0,4%): rata-rata {abn.mean():+.2%}, t = {nilai_t(abn):+.1f}, "
      f"positif {(abn > 0).mean():.0%} dari {len(abn)} tahun")
print("   per tahun: " + " ".join(f"{t}:{v:+.1%}" for t, v in abn.items()))
