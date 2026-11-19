"""
RISET #3: HARGA KOMODITAS -> SAHAM PRODUSENNYA BULAN DEPAN
==========================================================

DUGAAN (ditulis 2026-11-19, SEBELUM melihat hubungan komoditas-saham apa pun)
----------------------------------------------------------------------------
Kalau harga komoditas (nikel, timah, batu bara, sawit, minyak) naik bulan ini, saham perusahaan
penghasilnya di IDX cenderung ikut naik BULAN DEPAN (tanda positif).
Alasan logis: investor bereaksi lambat. Kenaikan harga komoditas baru terlihat di laporan laba
1-3 bulan kemudian; investor ritel & analis yang sedikit tidak langsung menghitung dampaknya.
Literatur pendukung: perubahan harga minyak memprediksi return saham bulan depan
("Striking Oil", Driesprong-Jacobsen-Maat 2008); industri hulu "mendahului" pasar (Hong-Torous-Valkanov 2007).
Perkiraan jujur: efeknya lemah dan mungkin sudah hilang karena pasar makin efisien; saya kira t sekitar 1-2.

PASANGAN (ditetapkan sekarang, tidak diubah setelah melihat hasil). Hanya saham dengan histori sebelum 2012:
    nikel     (IMF PNICKUSDM)   : INCO, ANTM
    timah     (IMF PTINUSDM)    : TINS
    batu bara (IMF PCOALAUUSDM) : PTBA, ITMG, ADRO, BUMI, INDY, HRUM
    sawit     (IMF PPOILUSDM)   : AALI, LSIP, SGRO, SIMP, BWPT
    minyak    (FRED Brent)      : MEDC, ENRG

DESAIN UJI
----------
- Sinyal bulan m = perubahan RATA-RATA harga komoditas bulan m dibanding bulan m-1.
  Semua harga harian penyusunnya sudah publik paling lambat akhir bulan m (di bursa LME/ICE/dll.).
  CATATAN: FRED/IMF menerbitkan angka ini terlambat 1-2 bulan (tidak teratur), jadi untuk
  dijalankan sungguhan nanti dibutuhkan sumber harga HARIAN. Uji ini mengukur apakah informasinya berguna.
- Return saham: beli di harga tutup hari bursa PERTAMA bulan m+1, jual di hari bursa pertama bulan m+2
  (sama dengan riset #2). Saham hanya dipakai bila median nilai transaksi 60 hari >= Rp1 miliar
  pada akhir bulan m (informasi saat itu).
- Per komoditas: portofolio bobot sama dari sahamnya. Regresi return bulan m+1 pada sinyal bulan m.
  Juga versi "dikurangi IHSG" (membuang gerak pasar umum) sebagai cek ketahanan.
- Strategi yang bisa dijalankan: tiap bulan beli kelompok komoditas yang harganya NAIK bulan lalu
  (bobot sama; kalau tidak ada, pegang kas), dibanding memegang semua kelompok. Biaya 0,4% x porsi diganti.
- Cek kewajaran (BUKAN prediksi): korelasi komoditas bulan m dengan saham bulan m yang SAMA harus
  jelas positif. Kalau tidak, berarti pasangan saham-komoditas salah pilih.
- Jumlah uji utama: 5 kemiringan regresi + 1 strategi = 6. Ambang |t| > 3.
- Data uji 2019+ DIKUNCI (buka sekali di akhir dengan --buka-uji).
- Uji kode: --tes-tiruan (data palsu dengan pola tersembunyi, harus ditemukan) dan
  --tes-kosong (data palsu tanpa pola, harus ~nol).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BATAS_LATIH = pd.Period("2018-12", "M")
BUKA_DATA_UJI = "--buka-uji" in sys.argv
TES_TIRUAN = "--tes-tiruan" in sys.argv
TES_KOSONG = "--tes-kosong" in sys.argv
BIAYA = 0.004
MIN_NILAI = 1e9
GRUP = {
    "nikel":     ("PNICKUSDM",    ["INCO", "ANTM"]),
    "timah":     ("PTINUSDM",     ["TINS"]),
    "batu bara": ("PCOALAUUSDM",  ["PTBA", "ITMG", "ADRO", "BUMI", "INDY", "HRUM"]),
    "sawit":     ("PPOILUSDM",    ["AALI", "LSIP", "SGRO", "SIMP", "BWPT"]),
    "minyak":    ("DCOILBRENTEU", ["MEDC", "ENRG"]),
}
SEMUA_SAHAM = [s for _, (_, daftar) in GRUP.items() for s in daftar]


def jadi_tanggal(x):
    """Tanggal polos tanpa zona waktu, presisi ns."""
    t = pd.DatetimeIndex(pd.to_datetime(x))
    if t.tz is not None:
        t = t.tz_localize(None)
    return t.normalize().astype("datetime64[ns]")


def nilai_t(s):
    s = pd.Series(s).dropna()
    return s.mean() / (s.std(ddof=1) / np.sqrt(len(s))) if len(s) > 2 else np.nan


def regresi(y, x):
    """Kemiringan, nilai t, dan jumlah bulan dari regresi y = a + b*x."""
    d = pd.concat([y, x], axis=1).dropna()
    if len(d) < 24:
        return np.nan, np.nan, len(d)
    r = d.iloc[:, 0].corr(d.iloc[:, 1])
    b = r * d.iloc[:, 0].std() / d.iloc[:, 1].std()
    return b, r * np.sqrt(len(d) - 2) / np.sqrt(1 - r ** 2), len(d)


# ===== 1. Data =====
def muat_data_asli():
    adj, tutup, volume = {}, {}, {}
    for f in sorted(Path("data/raw/harga_idx").glob("*.parquet")):
        d = pd.read_parquet(f, columns=["Adj Close", "Close", "Volume"])
        d.index = jadi_tanggal(d.index)
        d = d[~d.index.duplicated(keep="last")]
        adj[f.stem], tutup[f.stem], volume[f.stem] = d["Adj Close"], d["Close"], d["Volume"]
    adj, tutup, volume = (pd.DataFrame(x).sort_index() for x in (adj, tutup, volume))
    # Hari bursa = hari kerja dengan minimal 10 saham bertransaksi (sama dengan riset #2)
    aktif = volume.fillna(0) > 0
    hari = aktif.index[(aktif.sum(axis=1) >= 10) & (aktif.index.day_of_week < 5)]
    adj, tutup, volume = (x.loc[hari, SEMUA_SAHAM] for x in (adj, tutup, volume))

    m = pd.read_parquet("data/raw/harga/IHSG.parquet")
    ihsg = pd.Series(m["Close"].values, index=jadi_tanggal(m.index))
    ihsg = ihsg[~ihsg.index.duplicated(keep="last")].reindex(hari).ffill()

    kom = {}
    for nama, (kode, _) in GRUP.items():
        k = pd.read_parquet(f"data/raw/makro/{kode}.parquet")["nilai"].astype(float)
        k.index = jadi_tanggal(k.index)
        kom[nama] = k.groupby(k.index.to_period("M")).mean()   # rata-rata bulanan
    return adj, tutup, volume, ihsg, pd.DataFrame(kom)


def buat_data_tiruan(dengan_pola):
    """Saham & komoditas palsu. Pola tersembunyi: return saham bulan m+1 = 0,3 x perubahan
    komoditasnya bulan m + acak. Tanpa pola: semuanya acak murni."""
    acak = np.random.default_rng(7)
    hari = pd.bdate_range("2000-07-03", "2026-11-13").astype("datetime64[ns]")
    bln = hari.to_period("M")
    daftar_bln = bln.unique()
    kom_ret = pd.DataFrame(acak.normal(0, 0.06, (len(daftar_bln), len(GRUP))), index=daftar_bln, columns=list(GRUP))
    kom = 100 * np.exp(kom_ret.cumsum())
    kom_ret = kom.pct_change()
    harian = pd.DataFrame(acak.normal(0, 0.02, (len(hari), len(SEMUA_SAHAM))), index=hari, columns=SEMUA_SAHAM)
    if dengan_pola:
        for nama, (_, daftar) in GRUP.items():
            dorong = kom_ret[nama].shift(1).reindex(bln).fillna(0).values * 0.3 / 21   # efek bulan m -> m+1
            harian[daftar] = harian[daftar].add(dorong, axis=0)
    adj = 1000 * np.exp(harian.cumsum())
    volume = pd.DataFrame(1e7, index=hari, columns=SEMUA_SAHAM)
    ihsg = pd.Series(1000 * np.exp(np.cumsum(acak.normal(0, 0.01, len(hari)))), index=hari)
    return adj, adj.copy(), volume, ihsg, kom


if TES_TIRUAN or TES_KOSONG:
    adj, tutup, volume, ihsg, kom = buat_data_tiruan(TES_TIRUAN)
    print(f"🧪 MODE TES: data PALSU {'dengan pola tersembunyi (koefisien 0,3)' if TES_TIRUAN else 'tanpa pola'}")
else:
    adj, tutup, volume, ihsg, kom = muat_data_asli()
hari = adj.index
print(f"📥 {adj.shape[1]} saham, {len(hari):,} hari bursa, {hari[0].date()} s/d {hari[-1].date()}; "
      f"komoditas bulanan {kom.index.min()} s/d {kom.index.max()}")

# ===== 2. Bulanan =====
kom_ret = kom.pct_change(fill_method=None)            # perubahan rata-rata bulan m vs m-1
bulan = pd.Series(hari, index=hari).groupby(hari.to_period("M"))
akhir = bulan.max()                                   # index: Period bulan
awal = bulan.min()
harga_awal = adj.loc[awal.values].set_axis(awal.index)
ihsg_awal = ihsg.loc[awal.values].set_axis(awal.index)

ret_depan = harga_awal.shift(-2) / harga_awal.shift(-1) - 1   # dipegang bulan m+1 (sinyal bulan m)
ret_sama = harga_awal.shift(-1) / harga_awal - 1              # kira-kira bulan m itu sendiri
ihsg_depan = ihsg_awal.shift(-2) / ihsg_awal.shift(-1) - 1
ihsg_sama = ihsg_awal.shift(-1) / ihsg_awal - 1
bulan_jual = pd.Series(awal.index, index=awal.index).shift(-2)   # bulan saat posisi ditutup

nilai = (tutup * volume).where(volume > 0)
median_nilai = nilai.rolling(60, min_periods=40).median().loc[akhir.values].set_axis(akhir.index)
likuid = median_nilai >= MIN_NILAI

grup_depan = pd.DataFrame({g: ret_depan[d].where(likuid[d]).mean(axis=1) for g, (_, d) in GRUP.items()})
grup_sama = pd.DataFrame({g: ret_sama[d].where(likuid[d]).mean(axis=1) for g, (_, d) in GRUP.items()})
kom_ret = kom_ret.reindex(grup_depan.index)

if BUKA_DATA_UJI:
    pilih = (bulan_jual > BATAS_LATIH) & (pd.Series(awal.index, index=awal.index) > BATAS_LATIH) & bulan_jual.notna()
    label = "DATA UJI (2019+)"
else:
    pilih = bulan_jual <= BATAS_LATIH
    label = f"DATA LATIH (posisi ditutup s/d {BATAS_LATIH})"
print(f"🔒 Data uji {'DIBUKA' if BUKA_DATA_UJI else 'DIKUNCI, tidak disentuh'}. Menganalisis {label}.\n")
gd, gs, kr = grup_depan[pilih], grup_sama[pilih], kom_ret[pilih]
idp, ids = ihsg_depan[pilih], ihsg_sama[pilih]

# ===== 3. Cek kewajaran: bulan yang SAMA =====
print("0️⃣  Cek kewajaran (bukan prediksi): komoditas bulan m vs saham bulan m yang sama")
for g in GRUP:
    b, t, n = regresi(gs[g], kr[g])
    print(f"   {g:10} kemiringan {b:+.2f}  t = {t:+5.1f}  ({n} bulan)")
print("   (harus jelas positif: kalau tidak, pasangan saham-komoditas salah pilih)\n")

# ===== 4. Uji utama: bulan m -> bulan m+1 =====
print("1️⃣  Prediksi: perubahan komoditas bulan m -> return saham bulan m+1")
print(f"   {'kelompok':10}{'bulan':>7}{'kemiringan':>12}{'t':>7}   {'dikurangi IHSG':>15}{'t':>7}   "
      f"{'saham setelah kom. NAIK':>24}{'setelah TURUN':>15}")
for g in GRUP:
    b, t, n = regresi(gd[g], kr[g])
    b2, t2, _ = regresi(gd[g] - idp, kr[g])
    naik = gd[g][kr[g] > 0].mean()
    turun = gd[g][kr[g] <= 0].mean()
    print(f"   {g:10}{n:>7}{b:>+12.3f}{t:>+7.1f}   {b2:>+15.3f}{t2:>+7.1f}   {naik:>+24.2%}{turun:>+15.2%}")
print("   (kemiringan 0,1 = komoditas naik 10% -> saham rata-rata +1% bulan depan)\n")

# ===== 5. Strategi yang bisa dijalankan =====
baris, w_lalu, wb_lalu = [], None, None
for m in gd.index:
    ada = [g for g in GRUP if pd.notna(gd.loc[m, g]) and pd.notna(kr.loc[m, g])]
    if len(ada) < 2:
        continue
    naik = [g for g in ada if kr.loc[m, g] > 0]
    w = pd.Series(0.0, index=list(GRUP) + ["kas"])
    if naik:
        w[naik] = 1 / len(naik)
    else:
        w["kas"] = 1.0
    wb = pd.Series(0.0, index=w.index)
    wb[ada] = 1 / len(ada)
    ganti = 0.5 * (w - w_lalu).abs().sum() if w_lalu is not None else 1.0
    ganti_b = 0.5 * (wb - wb_lalu).abs().sum() if wb_lalu is not None else 1.0
    r = gd.loc[m, naik].mean() if naik else 0.0
    rb = gd.loc[m, ada].mean()
    baris.append({"bulan": m, "strategi": r - ganti * BIAYA, "semua": rb - ganti_b * BIAYA,
                  "ihsg": idp.loc[m], "ganti": ganti, "kas": not naik})
    w_lalu, wb_lalu = w, wb
s = pd.DataFrame(baris).set_index("bulan")
lebih = s["strategi"] - s["semua"]
print("2️⃣  Strategi: beli kelompok yang komoditasnya NAIK bulan lalu (setelah biaya 0,4%)")
print(f"   Bulan: {len(s)} ({s.index[0]} s/d {s.index[-1]}), rata-rata ganti {s['ganti'].iloc[1:].mean():.0%}/bln, "
      f"pegang kas {s['kas'].mean():.0%} bulan")
print(f"   Strategi bersih          : {s['strategi'].mean():+.2%}/bln")
print(f"   Pegang semua kelompok    : {s['semua'].mean():+.2%}/bln")
print(f"   IHSG (tanpa biaya)       : {s['ihsg'].mean():+.2%}/bln")
print(f"   Strategi - semua kelompok: {lebih.mean():+.2%}/bln  t = {nilai_t(lebih):+.1f}  "
      f"(~{(1 + lebih.mean()) ** 12 - 1:+.1%}/thn, menang {(lebih > 0).mean():.0%} bulan)")

# ===== 6. Stabilitas =====
print("\n3️⃣  Stabilitas: nilai t kemiringan per paruh waktu")
tengah = gd.index[len(gd) // 2]
for g in GRUP:
    _, ta, na = regresi(gd[g].loc[:tengah], kr[g].loc[:tengah])
    _, tb, nb = regresi(gd[g].loc[tengah:].iloc[1:], kr[g].loc[tengah:].iloc[1:])
    print(f"   {g:10} paruh 1: t = {ta:+5.1f} ({na} bln)   paruh 2: t = {tb:+5.1f} ({nb} bln)")
print(f"   (batas paruh: {tengah})")
