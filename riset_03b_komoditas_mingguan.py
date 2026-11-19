"""
RISET #3b: HARGA & STOK KOMODITAS HARIAN -> SAHAM PRODUSENNYA MINGGU DEPAN
=========================================================================

LATAR: riset #3 (bulanan, rata-rata IMF) negatif: semua arah positif tapi tidak ada yang t > 3.
Sekarang ada harga HARIAN (LME nikel & timah sejak 2008, sawit CPO=F sejak 2010) + stok gudang LME.

DUGAAN (ditulis 2026-11-20, SEBELUM melihat hubungan komoditas-saham apa pun di data harian)
------------------------------------------------------------------------------------------
H1 (harga): komoditas naik minggu ini -> saham produsennya naik MINGGU DEPAN (tanda positif).
    Alasan: reaksi lambat investor ritel; berita komoditas global butuh waktu diterjemahkan ke saham lokal.
    Perkiraan jujur: kalau di bulanan saja lemah, di mingguan mungkin sedikit lebih kuat (reaksi lambat
    biasanya terkonsentrasi di hari/minggu pertama), tapi biaya mingguan jauh lebih berat. Saya kira strategi gagal.
H2 (stok gudang LME): stok TURUN minggu ini = pasokan ketat -> saham produsen naik minggu depan (tanda NEGATIF).
    Alasan: data stok jarang diperhatikan investor ritel Indonesia.
    Perkiraan jujur: sangat lemah, t < 2.

PASANGAN (tetap): nikel (LME) -> INCO, ANTM | timah (LME) -> TINS | sawit (CPO=F) -> AALI, LSIP, SGRO, SIMP, BWPT

WAKTU (supaya tidak mengintip masa depan)
-----------------------------------------
- Minggu = Sabtu s/d Jumat. Sinyal minggu w = perubahan harga terakhir minggu w-1 -> harga terakhir minggu w.
- Harga resmi LME (~18:30-19:30 WIB) & penutupan sawit CME terjadi SETELAH IDX tutup. Stok LME juga dianggap
  baru diketahui setelah IDX tutup. Jadi sinyal minggu w baru bisa dipakai mulai hari bursa pertama minggu w+1.
- Return saham: beli di harga TUTUP hari bursa pertama minggu w+1, jual di tutup hari bursa pertama minggu w+2.
  (Sengaja melewatkan reaksi hari Senin pagi: yang diuji adalah reaksi LAMBAT, bukan sekadar beda jam buka.)
- Saham dipakai hanya bila median nilai transaksi 60 hari >= Rp1 miliar (diukur di akhir minggu w).

UKURAN
------
- Per kelompok: regresi return saham minggu w+1 pada sinyal minggu w. Nilai t memakai galat baku
  "robust" (tahan terhadap volatilitas yang naik-turun) sebagai ukuran UTAMA; t biasa ditampilkan juga.
- Strategi yang bisa dijalankan: tiap minggu beli kelompok yang komoditasnya NAIK minggu lalu (bobot sama,
  kalau tidak ada: kas), dibanding memegang semua kelompok. Biaya 0,4% x porsi yang diganti.
- Cek kewajaran (bukan prediksi): komoditas minggu w vs saham minggu w yang sama harus positif.
- Jumlah uji utama: 3 (harga) + 2 (stok) + 1 (strategi) = 6. Ambang |t| > 3.
- Data uji 2019+ DIKUNCI (--buka-uji). Uji kode: --tes-tiruan & --tes-kosong.
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
MIN_NILAI = 1e9
GRUP = {"nikel": ["INCO", "ANTM"], "timah": ["TINS"], "sawit": ["AALI", "LSIP", "SGRO", "SIMP", "BWPT"]}
PUNYA_STOK = ["nikel", "timah"]
SEMUA_SAHAM = [s for d in GRUP.values() for s in d]
MINGGU = "W-FRI"                                 # periode mingguan Sabtu-Jumat


def jadi_tanggal(x):
    """Tanggal polos tanpa zona waktu, presisi ns (tanggal lokal bursa dipertahankan)."""
    t = pd.DatetimeIndex(pd.to_datetime(x))
    if t.tz is not None:
        t = t.tz_localize(None)
    return t.normalize().astype("datetime64[ns]")


def nilai_t(s):
    s = pd.Series(s).dropna()
    return s.mean() / (s.std(ddof=1) / np.sqrt(len(s))) if len(s) > 2 else np.nan


def regresi(y, x):
    """y = a + b*x. Hasil: b, t robust (White), t biasa, jumlah minggu."""
    d = pd.concat([y, x], axis=1).dropna()
    n = len(d)
    if n < 50:
        return np.nan, np.nan, np.nan, n
    yy, xx = d.iloc[:, 0].values, d.iloc[:, 1].values
    xc = xx - xx.mean()
    b = (xc * (yy - yy.mean())).sum() / (xc ** 2).sum()
    e = yy - yy.mean() - b * xc
    se_robust = np.sqrt((xc ** 2 * e ** 2).sum()) / (xc ** 2).sum() * np.sqrt(n / (n - 2))
    se_biasa = np.sqrt((e ** 2).sum() / (n - 2) / (xc ** 2).sum())
    return b, b / se_robust, b / se_biasa, n


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
    adj, tutup, volume = (x.loc[hari, SEMUA_SAHAM] for x in (adj, tutup, volume))

    lme = pd.read_parquet("data/raw/histori/lme/semua.parquet")
    lme["tanggal"] = jadi_tanggal(lme["tanggal"])
    harga_kom, stok = {}, {}
    for nama in PUNYA_STOK:
        x = lme[lme["logam"] == nama].set_index("tanggal").sort_index()
        harga_kom[nama] = x["harga_tunai"].dropna()
        stok[nama] = x["stok"].dropna()
    s = pd.read_parquet("data/raw/harga/SAWIT.parquet")
    harga_kom["sawit"] = pd.Series(s["Close"].values, index=jadi_tanggal(s.index)).dropna()
    harga_kom["sawit"] = harga_kom["sawit"][~harga_kom["sawit"].index.duplicated(keep="last")]
    return adj, tutup, volume, harga_kom, stok


def buat_data_tiruan(dengan_pola):
    """Data palsu. Pola tersembunyi (kalau ada): return harian saham minggu w+1 mendapat dorongan
    0,2 x return komoditasnya minggu w (dibagi 5 hari). Stok gudang selalu acak (tanpa pola)."""
    acak = np.random.default_rng(11)
    hari = pd.bdate_range("2008-01-01", "2026-11-13").astype("datetime64[ns]")
    minggu = hari.to_period(MINGGU)
    harga_kom, stok = {}, {}
    for nama in GRUP:
        harga_kom[nama] = pd.Series(1000 * np.exp(np.cumsum(acak.normal(0, 0.015, len(hari)))), index=hari)
    for nama in PUNYA_STOK:
        stok[nama] = pd.Series(1e5 * np.exp(np.cumsum(acak.normal(0, 0.01, len(hari)))), index=hari)
    harian = pd.DataFrame(acak.normal(0, 0.02, (len(hari), len(SEMUA_SAHAM))), index=hari, columns=SEMUA_SAHAM)
    if dengan_pola:
        for nama, daftar in GRUP.items():
            k = harga_kom[nama]
            r_mg = k.groupby(k.index.to_period(MINGGU)).last().pct_change()
            dorong = r_mg.shift(1).reindex(minggu).fillna(0).values * 0.2 / 5
            harian[daftar] = harian[daftar].add(dorong, axis=0)
    adj = 1000 * np.exp(harian.cumsum())
    volume = pd.DataFrame(1e7, index=hari, columns=SEMUA_SAHAM)
    return adj, adj.copy(), volume, harga_kom, stok


if TES_TIRUAN or TES_KOSONG:
    adj, tutup, volume, harga_kom, stok = buat_data_tiruan(TES_TIRUAN)
    print(f"🧪 MODE TES: data PALSU {'dengan pola harga tersembunyi (0,2)' if TES_TIRUAN else 'tanpa pola'}")
else:
    adj, tutup, volume, harga_kom, stok = muat_data_asli()


def bersihkan(seri, nama):
    """Buang nilai rusak dari sumber: < 10% atau > 10x median 21 hari di sekitarnya.
    (Ditemukan: stok nikel 2-10 April 2012 tercatat 26-614 ton padahal ~99.000 ton.)"""
    med = seri.rolling(21, center=True, min_periods=5).median()
    rusak = (seri < 0.1 * med) | (seri > 10 * med)
    if rusak.any():
        print(f"🧹 {nama}: {rusak.sum()} nilai rusak dibuang ({', '.join(str(d.date()) for d in seri.index[rusak])})")
    return seri[~rusak]


harga_kom = {k: bersihkan(v, f"harga {k}") for k, v in harga_kom.items()}
stok = {k: bersihkan(v, f"stok {k}") for k, v in stok.items()}
hari = adj.index
print(f"📥 {adj.shape[1]} saham, {len(hari):,} hari bursa IDX; komoditas: "
      + ", ".join(f"{k} {v.index.min().date()}" for k, v in harga_kom.items()))

# ===== 2. Mingguan =====
semua_minggu = pd.period_range(hari.min().to_period(MINGGU), hari.max().to_period(MINGGU), freq=MINGGU)
mg_hari = pd.Series(hari, index=hari).groupby(hari.to_period(MINGGU))
awal = mg_hari.min().reindex(semua_minggu)       # hari bursa pertama tiap minggu (NaT kalau bursa tutup seminggu)
akhir = mg_hari.max().reindex(semua_minggu)


def per_minggu(seri):
    """Nilai terakhir tiap minggu, pada kalender minggu yang lengkap."""
    return seri.groupby(seri.index.to_period(MINGGU)).last().reindex(semua_minggu)


sinyal_harga = pd.DataFrame({k: per_minggu(v).pct_change(fill_method=None) for k, v in harga_kom.items()})
sinyal_stok = pd.DataFrame({k: per_minggu(v).pct_change(fill_method=None) for k, v in stok.items()})

harga_awal = adj.reindex(awal.values).set_axis(semua_minggu)
ret_depan = harga_awal.shift(-2) / harga_awal.shift(-1) - 1     # dipegang minggu w+1 (sinyal minggu w)
ret_sama = harga_awal.shift(-1) / harga_awal - 1                # kira-kira minggu w itu sendiri
tgl_jual = awal.shift(-2)

nilai = (tutup * volume).where(volume > 0)
median_nilai = nilai.rolling(60, min_periods=40).median()
likuid = median_nilai.reindex(akhir.values).set_axis(semua_minggu) >= MIN_NILAI

grup_depan = pd.DataFrame({g: ret_depan[d].where(likuid[d]).mean(axis=1) for g, d in GRUP.items()})
grup_sama = pd.DataFrame({g: ret_sama[d].where(likuid[d]).mean(axis=1) for g, d in GRUP.items()})

if BUKA_DATA_UJI:
    pilih = (awal > BATAS_LATIH) & tgl_jual.notna()
    label = "DATA UJI (2019+)"
else:
    pilih = tgl_jual <= BATAS_LATIH
    label = f"DATA LATIH (posisi ditutup s/d {BATAS_LATIH.date()})"
print(f"🔒 Data uji {'DIBUKA' if BUKA_DATA_UJI else 'DIKUNCI, tidak disentuh'}. Menganalisis {label}.\n")
gd, gs = grup_depan[pilih], grup_sama[pilih]
sh, ss = sinyal_harga[pilih], sinyal_stok[pilih]

# ===== 3. Cek kewajaran =====
print("0️⃣  Cek kewajaran (bukan prediksi): komoditas minggu w vs saham minggu w yang sama")
for g in GRUP:
    b, tr, tb, n = regresi(gs[g], sh[g])
    print(f"   {g:7} kemiringan {b:+.2f}  t robust = {tr:+5.1f}  ({n} minggu)")
print()

# ===== 4. Uji utama =====
print("1️⃣  H1 harga: perubahan harga komoditas minggu w -> return saham minggu w+1")
print(f"   {'kelompok':9}{'minggu':>7}{'kemiringan':>12}{'t robust':>10}{'t biasa':>9}   "
      f"{'saham stlh kom. NAIK':>21}{'stlh TURUN':>12}")
for g in GRUP:
    b, tr, tb, n = regresi(gd[g], sh[g])
    print(f"   {g:9}{n:>7}{b:>+12.3f}{tr:>+10.1f}{tb:>+9.1f}   "
          f"{gd[g][sh[g] > 0].mean():>+21.2%}{gd[g][sh[g] <= 0].mean():>+12.2%}")
print("   (kemiringan 0,1 = komoditas naik 10% -> saham rata-rata +1% minggu depan)\n")

print("2️⃣  H2 stok gudang LME: perubahan stok minggu w -> return saham minggu w+1 (dugaan: NEGATIF)")
for g in PUNYA_STOK:
    b, tr, tb, n = regresi(gd[g], ss[g])
    print(f"   {g:9}{n:>7}{b:>+12.3f}{tr:>+10.1f}{tb:>+9.1f}")
print()

# ===== 5. Strategi =====
baris, w_lalu, wb_lalu = [], None, None
for m in gd.index:
    ada = [g for g in GRUP if pd.notna(gd.loc[m, g]) and pd.notna(sh.loc[m, g])]
    if len(ada) < 2:
        continue
    naik = [g for g in ada if sh.loc[m, g] > 0]
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
    baris.append({"minggu": m, "kotor": r - rb, "strategi": r - ganti * BIAYA,
                  "semua": rb - ganti_b * BIAYA, "ganti": ganti})
    w_lalu, wb_lalu = w, wb
s = pd.DataFrame(baris).set_index("minggu")
lebih = s["strategi"] - s["semua"]
print("3️⃣  Strategi: tiap minggu beli kelompok yang komoditasnya NAIK minggu lalu")
print(f"   Minggu: {len(s)} ({s.index[0].end_time.date()} s/d {s.index[-1].end_time.date()}), "
      f"rata-rata ganti {s['ganti'].iloc[1:].mean():.0%}/minggu")
print(f"   Selisih KOTOR vs pegang semua : {s['kotor'].mean():+.3%}/minggu  t = {nilai_t(s['kotor']):+.1f}")
print(f"   Selisih BERSIH (biaya 0,4%)   : {lebih.mean():+.3%}/minggu  t = {nilai_t(lebih):+.1f}  "
      f"(~{(1 + lebih.mean()) ** 52 - 1:+.1%}/thn, menang {(lebih > 0).mean():.0%} minggu)")

# ===== 6. Stabilitas =====
print("\n4️⃣  Stabilitas H1: t robust per paruh waktu (dibagi dua menurut minggu yang ADA datanya)")
for g in GRUP:
    ada = pd.concat([gd[g], sh[g]], axis=1).dropna().index
    tengah = ada[len(ada) // 2]
    _, ta, _, na = regresi(gd[g].loc[:tengah], sh[g].loc[:tengah])
    _, tb2, _, nb = regresi(gd[g].loc[tengah:].iloc[1:], sh[g].loc[tengah:].iloc[1:])
    print(f"   {g:7} paruh 1: t = {ta:+5.1f} ({na} mg)   paruh 2: t = {tb2:+5.1f} ({nb} mg)   "
          f"batas {tengah.end_time.date()}")
