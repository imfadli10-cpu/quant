"""
RISET #12: MENGGABUNGKAN SINYAL LEMAH (langkah 4 ala Renaissance) - saham IDX, bulanan
====================================================================================

DUGAAN (ditulis 2026-11-20, SEBELUM menghitung sinyal baru apa pun di data IDX)
------------------------------------------------------------------------------
Momentum 12-1 (riset #2) adalah sinyal nyata (IC t=5,0) tapi strategi beli-saja belum lolos (bersih t=2,7).
Kalau beberapa sinyal lemah yang TIDAK terlalu mirip digabung, kesalahannya saling meredam -> sinyal gabungan
lebih stabil daripada masing-masing. Dugaan: gabungan punya IC lebih tinggi dan strategi beli-saja lebih baik
dari momentum saja. Perkiraan jujur: perbaikan kecil; mungkin mendekati t=3 tapi belum tentu lewat.

4 SINYAL (dipilih dari LITERATUR, bukan dari hasil riset kita; arah ditetapkan sekarang):
  S1 momentum 12-1           (Jegadeesh-Titman 1993)          naik = bagus  [sudah diuji di riset #2]
  S2 dekat harga tertinggi 52 minggu: harga / tertinggi 250 hari (George-Hwang 2004)   dekat puncak = bagus
  S3 volatilitas rendah: simpangan baku return harian 120 hari (Ang dkk. 2006; Blitz-van Vliet 2007)  rendah = bagus
  S4 "saham lotre" MAX: return harian tertinggi dalam 21 hari terakhir (Bali-Cakici-Whitelaw 2011)  tinggi = BURUK
  SENGAJA TIDAK DIPAKAI: kelanjutan 1 bulan (riset #2 menemukannya di data latih -> memakainya = curang).
GABUNGAN: tiap bulan, tiap sinyal diubah jadi z-skor antar-saham (dibatasi +/-3), arah disamakan (besar = bagus),
  lalu DIRATA-RATA dengan bobot SAMA. Tidak ada bobot yang dicari dari data.

DESAIN (sama dengan riset #2 supaya bisa dibandingkan): semesta & saringan riset #2, sinyal akhir bulan, beli tutup
  hari bursa pertama bulan berikutnya, tahan 1 bulan, 5 kelompok, bobot sama, biaya 0,4% x porsi diganti.
UJI (6; ambang |t| > 3):
  U1-U4: IC masing-masing sinyal S1..S4 (S1 = ulangan riset #2, sebagai patokan)
  U5: IC sinyal GABUNGAN
  U6: strategi beli-saja kelompok TERATAS sinyal gabungan, BERSIH, dibanding semesta tanpa biaya   <- uji penentu
DIAGNOSIS: korelasi antar sinyal, stabilitas per paruh, perbandingan U6 dengan momentum saja.
Data uji 2019+ DIKUNCI (--buka-uji). Uji kode: --tes-tiruan (pola di S3: saham tenang naik) & --tes-kosong.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BATAS_LATIH = pd.Timestamp("2018-12-31")
BUKA_DATA_UJI = "--buka-uji" in sys.argv
TES_TIRUAN = "--tes-tiruan" in sys.argv
TES_KOSONG = "--tes-kosong" in sys.argv
BIAYA = 0.004
MIN_HARGA, MIN_NILAI, MIN_HARI_AKTIF, MAX_LOMPAT, MIN_SAHAM = 100, 1e9, 0.8, 0.5, 30
NAMA = {"S1": "momentum 12-1", "S2": "dekat puncak 52 mg", "S3": "volatilitas rendah", "S4": "bukan saham lotre"}


def jadi_tanggal(x):
    t = pd.DatetimeIndex(pd.to_datetime(x))
    if t.tz is not None:
        t = t.tz_localize(None)
    return t.normalize().astype("datetime64[ns]")


def nilai_t(s):
    s = pd.Series(s).dropna()
    return s.mean() / (s.std(ddof=1) / np.sqrt(len(s))) if len(s) > 2 else np.nan


# ===== 1. Data harian =====
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
    """150 saham palsu, volatilitas tiap saham berbeda & berubah pelan. Pola (kalau ada): saham dengan volatilitas
    rendah mendapat return lebih tinggi (dorongan harian sebanding dengan -volatilitasnya). Tanpa pola: acak."""
    acak = np.random.default_rng(12)
    hari = pd.bdate_range("2001-01-01", "2026-11-13").astype("datetime64[ns]")
    n = 150
    vol = np.exp(np.log(0.02) + np.cumsum(acak.normal(0, 0.01, (len(hari), n)), axis=0) * 0.3)
    vol = np.clip(vol, 0.005, 0.08)
    harian = acak.normal(0, 1, (len(hari), n)) * vol
    if dengan_pola:
        harian += (0.02 - vol) * 0.05            # saham tenang (vol kecil) naik sedikit lebih cepat
    kolom = [f"S{i:03d}" for i in range(n)]
    adj = pd.DataFrame(1000 * np.exp(np.cumsum(harian, axis=0)), index=hari, columns=kolom)
    volume = pd.DataFrame(1e7, index=hari, columns=kolom)
    return adj, adj.copy(), volume


if TES_TIRUAN or TES_KOSONG:
    adj, tutup, volume = buat_data_tiruan(TES_TIRUAN)
    print(f"🧪 MODE TES: data PALSU {'dengan pola (volatilitas rendah = bagus)' if TES_TIRUAN else 'tanpa pola'}")
else:
    adj, tutup, volume = muat_data_asli()
hari = adj.index
print(f"📥 {adj.shape[1]} saham, {len(hari):,} hari bursa")

# ===== 2. Bahan harian (semua hanya memakai data sampai hari itu) =====
aktif = volume.fillna(0) > 0
ret_h = adj.pct_change(fill_method=None)
median_nilai = (tutup * volume).where(aktif).rolling(60, min_periods=40).median()
porsi_aktif = aktif.rolling(250, min_periods=250).mean()
lompat_maks = ret_h.abs().rolling(250, min_periods=200).max()
puncak_250 = adj.rolling(250, min_periods=200).max()
vol_120 = ret_h.rolling(120, min_periods=100).std()
max_21 = ret_h.rolling(21, min_periods=15).max()

# ===== 3. Bulanan =====
bulan = pd.Series(hari, index=hari).groupby(hari.to_period("M"))
akhir_bulan = pd.DatetimeIndex(bulan.max().values)
awal_bulan = pd.DatetimeIndex(bulan.min().values)
harga_akhir = adj.loc[akhir_bulan].reset_index(drop=True)
harga_awal = adj.loc[awal_bulan].reset_index(drop=True)
ret_pegang = harga_awal.shift(-2) / harga_awal.shift(-1) - 1
tgl_jual = pd.Series(awal_bulan).shift(-2)


def di_akhir(df):
    return df.loc[akhir_bulan].reset_index(drop=True)


lolos = ((di_akhir(tutup) >= MIN_HARGA) & (di_akhir(median_nilai) >= MIN_NILAI)
         & (di_akhir(porsi_aktif) >= MIN_HARI_AKTIF) & (di_akhir(lompat_maks) < MAX_LOMPAT))
sinyal = {"S1": harga_akhir.shift(1) / harga_akhir.shift(12) - 1,         # arah: besar = bagus
          "S2": di_akhir(adj) / di_akhir(puncak_250),                      # besar = bagus
          "S3": -di_akhir(vol_120),                                        # dibalik: vol rendah = besar
          "S4": -di_akhir(max_21)}                                         # dibalik: bukan lotre = besar

if BUKA_DATA_UJI:
    pilih = (pd.Series(akhir_bulan) > BATAS_LATIH) & tgl_jual.notna()
else:
    pilih = tgl_jual <= BATAS_LATIH
print(f"🔒 Data uji {'DIBUKA' if BUKA_DATA_UJI else 'DIKUNCI, tidak disentuh'}. "
      f"Menganalisis {'DATA UJI (2019+)' if BUKA_DATA_UJI else 'DATA LATIH (posisi ditutup s/d 2018-12-31)'}.\n")


def z(s):
    return ((s - s.mean()) / s.std()).clip(-3, 3)


baris, korelasi, lalu = [], [], {}
for i in np.where(pilih)[0]:
    ok = lolos.loc[i] & ret_pegang.loc[i].notna()
    for k in sinyal:
        ok &= sinyal[k].loc[i].notna()
    if ok.sum() < MIN_SAHAM:
        continue
    r = ret_pegang.loc[i][ok]
    zs = pd.DataFrame({k: z(sinyal[k].loc[i][ok]) for k in sinyal})
    zs["G"] = zs[list(sinyal)].mean(axis=1)
    korelasi.append(zs[list(sinyal)].corr())
    b = {"tanggal": akhir_bulan[i], "n": int(ok.sum()), "semesta": r.mean()}
    for k in list(sinyal) + ["G"]:
        b[f"ic_{k}"] = zs[k].rank().corr(r.rank())
        atas = set(zs[k].index[pd.qcut(zs[k].rank(method="first"), 5, labels=False) == 4])
        ganti = 1 - len(atas & lalu.get(k, set())) / len(atas) if lalu.get(k) else 1.0
        b[f"atas_{k}"] = r[list(atas)].mean()
        b[f"bersih_{k}"] = r[list(atas)].mean() - ganti * BIAYA - r.mean()
        b[f"ganti_{k}"] = ganti
        lalu[k] = atas
    baris.append(b)
d = pd.DataFrame(baris).set_index("tanggal")
print(f"Bulan: {len(d)} ({d.index[0]:%Y-%m} s/d {d.index[-1]:%Y-%m}), semesta median {d['n'].median():.0f} saham "
      f"(min {d['n'].min()})")

print("\n🔗 Korelasi rata-rata antar sinyal (makin kecil = makin saling melengkapi):")
print((sum(korelasi) / len(korelasi)).round(2).to_string())

print("\n1️⃣  IC tiap sinyal & gabungan (korelasi peringkat dengan return bulan depan)")
print(f"   {'uji':4}{'sinyal':22}{'IC':>8}{'t':>7}   {'beli kelompok teratas, BERSIH vs semesta':>42}{'t':>7}{'ganti':>7}")
for uji, k in [("U1", "S1"), ("U2", "S2"), ("U3", "S3"), ("U4", "S4"), ("U5", "G")]:
    nama = NAMA.get(k, "GABUNGAN (rata-rata)")
    print(f"   {uji:4}{nama:22}{d[f'ic_{k}'].mean():>+8.3f}{nilai_t(d[f'ic_{k}']):>+7.1f}   "
          f"{d[f'bersih_{k}'].mean():>+40.2%}/bln{nilai_t(d[f'bersih_{k}']):>+7.1f}{d[f'ganti_{k}'].iloc[1:].mean():>7.0%}")
g = d["bersih_G"]
print(f"\n2️⃣  U6 (uji penentu): beli 20% teratas sinyal GABUNGAN, bersih biaya, vs semesta:")
print(f"   {g.mean():+.2%}/bln, t = {nilai_t(g):+.1f}, ~{(1 + g.mean()) ** 12 - 1:+.1%}/thn, menang {(g > 0).mean():.0%} bulan")
selisih = d["bersih_G"] - d["bersih_S1"]
print(f"   Dibanding momentum saja: {selisih.mean():+.2%}/bln (t {nilai_t(selisih):+.1f})")

print("\n3️⃣  Stabilitas (paruh waktu)")
tengah = d.index[len(d) // 2]
for k in ["S1", "G"]:
    a, b2 = d.loc[:tengah], d.loc[tengah:].iloc[1:]
    print(f"   {NAMA.get(k, 'GABUNGAN'):22} IC: {nilai_t(a[f'ic_{k}']):+.1f} / {nilai_t(b2[f'ic_{k}']):+.1f}   "
          f"bersih: {nilai_t(a[f'bersih_{k}']):+.1f} / {nilai_t(b2[f'bersih_{k}']):+.1f}   (batas {tengah:%Y-%m})")

# ===== 4. DIAGNOSIS TAMBAHAN untuk S2 (DITAMBAHKAN SETELAH MELIHAT HASIL, 2026-11-20) =====
# S2 (dekat puncak 52 minggu) memberi strategi bersih t=3,9 padahal yang ditetapkan sebagai uji penentu adalah U6.
# Cek ketahanan berikut BUKAN uji baru; tujuannya mencari tanda ilusi (saham kecil, pencilan, biaya, waktu).
print("\n4️⃣  DIAGNOSIS TAMBAHAN S2 (ditambahkan SETELAH melihat hasil)")
nilai_bln = di_akhir(median_nilai)


def strategi_s2(likuid_teratas=None, potong=None, biaya=BIAYA):
    hasil, lalu_s2 = [], set()
    for i in np.where(pilih)[0]:
        ok = lolos.loc[i] & ret_pegang.loc[i].notna() & sinyal["S2"].loc[i].notna()
        for k in sinyal:
            ok &= sinyal[k].loc[i].notna()
        if likuid_teratas:
            ok &= nilai_bln.loc[i].where(ok).rank(ascending=False) <= likuid_teratas
        if ok.sum() < MIN_SAHAM:
            continue
        r = ret_pegang.loc[i][ok]
        if potong:
            r = r.clip(-potong, potong)
        s = sinyal["S2"].loc[i][ok]
        atas = set(s.index[pd.qcut(s.rank(method="first"), 5, labels=False) == 4])
        ganti = 1 - len(atas & lalu_s2) / len(atas) if lalu_s2 else 1.0
        hasil.append((akhir_bulan[i], r[list(atas)].mean() - ganti * biaya - r.mean(), s.rank().corr(r.rank())))
        lalu_s2 = atas
    return pd.DataFrame(hasil, columns=["tanggal", "bersih", "ic"]).set_index("tanggal")


for nama, kw in [("seperti di atas", {}), ("50 saham paling likuid", {"likuid_teratas": 50}),
                 ("return dipotong +/-30%", {"potong": 0.30}), ("biaya 0,8% (2x lipat)", {"biaya": 0.008})]:
    h = strategi_s2(**kw)
    t2 = h.index[len(h) // 2]
    print(f"   {nama:24} bersih {h['bersih'].mean():+.2%}/bln t {nilai_t(h['bersih']):+.1f} | IC t {nilai_t(h['ic']):+.1f} | "
          f"paruh: bersih t {nilai_t(h['bersih'].loc[:t2]):+.1f} / {nilai_t(h['bersih'].loc[t2:].iloc[1:]):+.1f}")
