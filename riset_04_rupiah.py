"""
RISET #4: KURS RUPIAH (USD/IDR) & INDEKS DOLAR (DXY) -> SAHAM IDX
=================================================================

DUGAAN (ditulis 2026-11-20, SEBELUM melihat hubungan kurs-saham apa pun)
------------------------------------------------------------------------
H1: Rupiah MELEMAH bulan ini (USD/IDR naik) -> keranjang saham likuid IDX lebih buruk BULAN DEPAN (tanda NEGATIF).
H2: Dolar MENGUAT global bulan ini (DXY naik) -> keranjang saham likuid IDX lebih buruk bulan depan (tanda NEGATIF).
Alasan logis: (a) arus dana asing keluar dari negara berkembang cenderung berlanjut beberapa minggu-bulan
(dana dikelola bertahap, laporan bulanan, keputusan komite); (b) rupiah lemah menekan laba importir & perusahaan
berutang dolar, tapi baru terlihat di laporan berikutnya. Investor asing memegang porsi besar saham likuid.
Perkiraan jujur: pelajaran riset #1-#3 = pasar IDX cepat menyerap informasi yang jelas. Kurs adalah informasi
paling jelas & paling diawasi. Saya kira t sekitar 1-2, strategi gagal.

DESAIN
------
- Keranjang: tiap akhir bulan, 30 saham dengan median nilai transaksi 60 hari TERBESAR (saringan riset #2:
  harga >= Rp100, >= 80% hari aktif, tanpa lompatan harian > 50%). Bobot sama. Semua informasi saat itu saja.
- Sinyal bulan m: perubahan USD/IDR (Yahoo IDR=X) dan DXY (Yahoo DX-Y.NYB) dari tutup terakhir bulan m-1 ke
  tutup terakhir bulan m. Kurs & DXY ditutup SETELAH IDX tutup, jadi baru dipakai mulai hari bursa pertama m+1.
- Return: beli tutup hari bursa pertama m+1, jual tutup hari bursa pertama m+2 (sama dengan riset #2/#3).
- UJI UTAMA (3): regresi keranjang bulan m+1 pada (H1) kurs bulan m, (H2) DXY bulan m; plus
  (S) strategi: pegang keranjang kalau rupiah TIDAK melemah bulan m, kalau melemah pindah ke KAS (dapat bunga
  BI/12, angka bulan sebelumnya supaya pasti sudah terbit). Dibanding selalu pegang keranjang.
  Biaya: 0,4% x porsi saham keranjang yang diganti + 0,4% penuh tiap keluar-masuk kas.
- UJI TAMBAHAN (2): versi MINGGUAN (minggu Sabtu-Jumat) regresi keranjang minggu w+1 pada kurs & DXY minggu w.
- Total 5 uji. Ambang |t| > 3 (t robust/White sebagai ukuran utama).
- Data uji 2019+ DIKUNCI (--buka-uji). Uji kode: --tes-tiruan (pola tersembunyi -0,5 di bulanan) & --tes-kosong.
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
N_KERANJANG = 30
MIN_HARGA, MIN_HARI_AKTIF, MAX_LOMPAT = 100, 0.8, 0.5


def jadi_tanggal(x):
    """Tanggal polos tanpa zona waktu, presisi ns (tanggal lokal bursa dipertahankan)."""
    t = pd.DatetimeIndex(pd.to_datetime(x))
    if t.tz is not None:
        t = t.tz_localize(None)
    return t.normalize().astype("datetime64[ns]")


def nilai_t(s):
    s = pd.Series(s).dropna()
    return s.mean() / (s.std(ddof=1) / np.sqrt(len(s))) if len(s) > 2 else np.nan


def regresi(y, x, minimal=24):
    """y = a + b*x. Hasil: b, t robust (White), t biasa, jumlah periode."""
    d = pd.concat([y, x], axis=1).dropna()
    n = len(d)
    if n < minimal:
        return np.nan, np.nan, np.nan, n
    yy, xx = d.iloc[:, 0].values, d.iloc[:, 1].values
    xc = xx - xx.mean()
    b = (xc * (yy - yy.mean())).sum() / (xc ** 2).sum()
    e = yy - yy.mean() - b * xc
    se_r = np.sqrt((xc ** 2 * e ** 2).sum()) / (xc ** 2).sum() * np.sqrt(n / (n - 2))
    se_b = np.sqrt((e ** 2).sum() / (n - 2) / (xc ** 2).sum())
    return b, b / se_r, b / se_b, n


def baca_harga_global(nama):
    d = pd.read_parquet(f"data/raw/harga/{nama}.parquet")
    s = pd.Series(d["Close"].values, index=jadi_tanggal(d.index)).dropna()
    return s[~s.index.duplicated(keep="last")].sort_index()


# ===== 1. Data =====
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
    adj, tutup, volume = (x.loc[hari] for x in (adj, tutup, volume))
    # Kurs HARIAN Yahoo IDR=X RUSAK di beberapa titik (lonjakan 1 hari -90%/+900%, nilai nyangkut 9612,45 di 2013)
    # dan BOLONG di 2001-2003 (2003 cuma 106 hari). Dibersihkan + hanya dipakai sejak 2004 (uji mingguan).
    kurs = bersihkan(baca_harga_global("USDIDR"), "USD/IDR Yahoo").loc["2004-01-01":]
    # Kurs BULANAN: akhir bulan versi OECD di FRED (kurs resmi, tanpa lubang, s/d 2023-12) untuk uji utama.
    o = pd.read_parquet("data/raw/makro/CCUSSP02IDM650N.parquet")["nilai"].astype(float)
    kurs_bln = pd.Series(o.values, index=jadi_tanggal(o.index).to_period("M"))
    dxy = baca_harga_global("DOLAR_INDEX")
    bi = pd.read_parquet("data/raw/makro/IRSTCI01IDM156N.parquet")["nilai"].astype(float)
    bi.index = jadi_tanggal(bi.index).to_period("M")
    return adj, tutup, volume, kurs, kurs_bln, dxy, bi


def bersihkan(seri, nama):
    """Buang titik yang menyimpang > 4% dari median 9 hari di sekitarnya; diulang sampai bersih
    (di akhir 2013 nilai rusak 9612 muncul 3 hari berturut-turut, median 5 hari ikut tertipu).
    Median TERPUSAT (lihat 4 hari ke depan): boleh untuk riset historis, JANGAN untuk sinyal live."""
    total = 0
    while True:
        med = seri.rolling(9, center=True, min_periods=5).median()
        rusak = (seri / med - 1).abs() > 0.04
        if not rusak.any():
            break
        total += rusak.sum()
        seri = seri[~rusak]
    print(f"🧹 {nama}: {total} titik rusak dibuang")
    return seri


def buat_data_tiruan(dengan_pola):
    """100 saham palsu + kurs & DXY acak. Pola (kalau ada): semua saham di bulan m+1 mendapat
    dorongan -0,5 x perubahan kurs bulan m (dibagi rata ke hari-hari bulan itu)."""
    acak = np.random.default_rng(5)
    hari = pd.bdate_range("2001-07-02", "2026-11-13").astype("datetime64[ns]")
    bln = hari.to_period("M")
    kolom = [f"S{i:03d}" for i in range(100)]
    kurs = pd.Series(9000 * np.exp(np.cumsum(acak.normal(0, 0.006, len(hari)))), index=hari)
    dxy = pd.Series(90 * np.exp(np.cumsum(acak.normal(0, 0.005, len(hari)))), index=hari)
    harian = pd.DataFrame(acak.normal(0.0003, 0.02, (len(hari), 100)), index=hari, columns=kolom)
    harian = harian.add(acak.normal(0, 0.01, len(hari)), axis=0)          # gerak pasar bersama
    if dengan_pola:
        r_bln = kurs.groupby(bln).last().pct_change()
        jumlah_hari = pd.Series(bln).value_counts()
        dorong = (r_bln.shift(1).reindex(bln).fillna(0).values * -0.5
                  / jumlah_hari.reindex(bln).values)
        harian = harian.add(dorong, axis=0)
    adj = 1000 * np.exp(harian.cumsum())
    volume = pd.DataFrame(1e7, index=hari, columns=kolom)
    bi = pd.Series(6.0, index=pd.period_range("2001-01", "2026-12", freq="M"))
    kurs_bln = kurs.groupby(kurs.index.to_period("M")).last()
    return adj, adj.copy(), volume, kurs, kurs_bln, dxy, bi


if TES_TIRUAN or TES_KOSONG:
    adj, tutup, volume, kurs, kurs_bln, dxy, bi = buat_data_tiruan(TES_TIRUAN)
    print(f"🧪 MODE TES: data PALSU {'dengan pola tersembunyi (-0,5, bulanan)' if TES_TIRUAN else 'tanpa pola'}")
else:
    adj, tutup, volume, kurs, kurs_bln, dxy, bi = muat_data_asli()
hari = adj.index
print(f"📥 {adj.shape[1]} saham, {len(hari):,} hari bursa; kurs {kurs.index.min().date()}, DXY {dxy.index.min().date()}")

# Cek kualitas kurs: lompatan harian > 5% (rupiah jarang bergerak sebesar itu dalam sehari)
for nama, s in [("USD/IDR", kurs), ("DXY", dxy)]:
    r = s.pct_change()
    besar = r[r.abs() > 0.05]
    print(f"🔎 {nama}: {len(besar)} lompatan harian > 5%"
          + (": " + ", ".join(f"{d.date()} {v:+.1%}" for d, v in besar.items()) if len(besar) else ""))

# ===== 2. Saringan & keranjang (informasi saat itu saja) =====
aktif = volume.fillna(0) > 0
median_nilai = (tutup * volume).where(aktif).rolling(60, min_periods=40).median()
porsi_aktif = aktif.rolling(250, min_periods=250).mean()
lompat_maks = adj.pct_change(fill_method=None).abs().rolling(250, min_periods=200).max()


def keranjang_pada(tgl):
    ok = ((tutup.loc[tgl] >= MIN_HARGA) & (porsi_aktif.loc[tgl] >= MIN_HARI_AKTIF)
          & (lompat_maks.loc[tgl] < MAX_LOMPAT) & median_nilai.loc[tgl].notna())
    return median_nilai.loc[tgl][ok].nlargest(N_KERANJANG).index


def sinyal_periode(seri, periode, kalender):
    """Perubahan dari nilai terakhir periode sebelumnya ke nilai terakhir periode ini."""
    akhir = seri.groupby(seri.index.to_period(periode)).last().reindex(kalender)
    return akhir.pct_change(fill_method=None)


# ===== 3. BULANAN =====
bulan_kal = pd.period_range(hari.min().to_period("M"), hari.max().to_period("M"), freq="M")
gb = pd.Series(hari, index=hari).groupby(hari.to_period("M"))
akhir_b, awal_b = gb.max().reindex(bulan_kal), gb.min().reindex(bulan_kal)
harga_awal_b = adj.reindex(awal_b.values).set_axis(bulan_kal)
ret_b = harga_awal_b.shift(-2) / harga_awal_b.shift(-1) - 1
jual_b = awal_b.shift(-2)
kurs_b = kurs_bln.reindex(bulan_kal).pct_change(fill_method=None)     # OECD akhir bulan (data asli)
dxy_b = sinyal_periode(dxy, "M", bulan_kal)
bunga_kas = (bi.reindex(bulan_kal).ffill().shift(1) / 100 / 12)     # bunga BI bulan sebelumnya, per bulan

pilih_b = (awal_b > BATAS_LATIH) & jual_b.notna() if BUKA_DATA_UJI else (jual_b <= BATAS_LATIH)
print(f"🔒 Data uji {'DIBUKA' if BUKA_DATA_UJI else 'DIKUNCI, tidak disentuh'}. "
      f"Menganalisis {'DATA UJI (2019+)' if BUKA_DATA_UJI else 'DATA LATIH (posisi ditutup s/d 2018-12-31)'}.\n")

baris, anggota_lalu = [], {}
for m in bulan_kal[pilih_b.values]:
    if pd.isna(akhir_b[m]) or pd.isna(awal_b[m]):
        continue
    isi = keranjang_pada(akhir_b[m])
    r = ret_b.loc[m, isi].dropna()
    if len(r) < N_KERANJANG * 0.8:
        continue
    lalu = anggota_lalu.get("isi", set())
    ganti = 1 - len(set(r.index) & lalu) / len(r) if lalu else 1.0
    baris.append({"bulan": m, "keranjang": r.mean(), "ganti": ganti, "kurs": kurs_b[m], "dxy": dxy_b[m],
                  "bunga": bunga_kas[m]})
    anggota_lalu["isi"] = set(r.index)
b = pd.DataFrame(baris).set_index("bulan")
print(f"Bulanan: {len(b)} bulan ({b.index[0]} s/d {b.index[-1]}), keranjang {N_KERANJANG} saham, "
      f"ganti anggota rata-rata {b['ganti'].iloc[1:].mean():.0%}/bln")

print("\n0️⃣  Cek kewajaran (bukan prediksi): kurs/DXY bulan m vs keranjang bulan m yang SAMA")
ret_sama = (harga_awal_b.shift(-1) / harga_awal_b - 1)
sama = pd.Series({m: ret_sama.loc[m, list(keranjang_pada(akhir_b[m - 1]))].mean()
                  if pd.notna(akhir_b.get(m - 1, pd.NaT)) else np.nan for m in b.index})
for nama, x in [("kurs", b["kurs"]), ("DXY", b["dxy"])]:
    k, tr, tb, n = regresi(sama, x)
    print(f"   {nama:5} kemiringan {k:+.2f}  t robust = {tr:+5.1f}  ({n} bulan)  (dugaan: jelas negatif)")

print("\n1️⃣  UJI UTAMA bulanan: perubahan bulan m -> keranjang bulan m+1 (dugaan: NEGATIF)")
print(f"   {'sinyal':6}{'bulan':>7}{'kemiringan':>12}{'t robust':>10}{'t biasa':>9}   "
      f"{'keranjang stlh sinyal NAIK':>27}{'stlh TURUN':>12}")
for nama, x in [("H1 kurs", b["kurs"]), ("H2 DXY", b["dxy"])]:
    k, tr, tb, n = regresi(b["keranjang"], x)
    print(f"   {nama:8}{n:>5}{k:>+12.3f}{tr:>+10.1f}{tb:>+9.1f}   "
          f"{b['keranjang'][x > 0].mean():>+27.2%}{b['keranjang'][x <= 0].mean():>+12.2%}")
print("   (kemiringan -0,5 = rupiah melemah 2% -> keranjang rata-rata -1% bulan depan)")

# Strategi (S)
masuk = (b["kurs"] <= 0)
pindah = masuk.astype(int).diff().abs().fillna(1)                 # keluar/masuk kas
biaya_keranjang = b["ganti"] * BIAYA
strat = np.where(masuk, b["keranjang"] - biaya_keranjang, b["bunga"]) - pindah * BIAYA / 2
selalu = b["keranjang"] - biaya_keranjang
s = pd.Series(strat, index=b.index)
lebih = s - selalu
print("\n2️⃣  UJI UTAMA strategi: pegang keranjang kalau rupiah TIDAK melemah bulan lalu, kalau melemah -> kas")
print(f"   Di keranjang {masuk.mean():.0%} bulan, keluar-masuk {pindah.iloc[1:].mean():.0%} bulan")
print(f"   Strategi bersih     : {s.mean():+.2%}/bln (std {s.std():.2%})")
print(f"   Selalu pegang       : {selalu.mean():+.2%}/bln (std {selalu.std():.2%})")
print(f"   Strategi - selalu   : {lebih.mean():+.2%}/bln  t = {nilai_t(lebih):+.1f}  "
      f"(menang {(lebih > 0).mean():.0%} bulan)")
rasio = lambda x: x.mean() / x.std() * np.sqrt(12)
print(f"   Rasio Sharpe kasar (tanpa kurangi bunga): strategi {rasio(s):.2f} vs selalu {rasio(selalu):.2f}")

# ===== 4. MINGGUAN (uji tambahan) =====
mg_kal = pd.period_range(hari.min().to_period("W-FRI"), hari.max().to_period("W-FRI"), freq="W-FRI")
gm = pd.Series(hari, index=hari).groupby(hari.to_period("W-FRI"))
akhir_m, awal_m = gm.max().reindex(mg_kal), gm.min().reindex(mg_kal)
harga_awal_m = adj.reindex(awal_m.values).set_axis(mg_kal)
ret_m = harga_awal_m.shift(-2) / harga_awal_m.shift(-1) - 1
jual_m = awal_m.shift(-2)
kurs_m = sinyal_periode(kurs, "W-FRI", mg_kal)
dxy_m = sinyal_periode(dxy, "W-FRI", mg_kal)
pilih_m = (awal_m > BATAS_LATIH) & jual_m.notna() if BUKA_DATA_UJI else (jual_m <= BATAS_LATIH)
# Anggota keranjang mingguan = keranjang dari akhir bulan sebelumnya (informasi saat itu)
anggota = {m: keranjang_pada(akhir_b[m]) for m in bulan_kal if pd.notna(akhir_b[m])}
mg = []
for w in mg_kal[pilih_m.values]:
    if pd.isna(akhir_m[w]):
        continue
    bl = akhir_m[w].to_period("M") - 1
    if bl not in anggota:
        continue
    r = ret_m.loc[w, list(anggota[bl])].dropna()
    if len(r) >= N_KERANJANG * 0.8:
        mg.append({"minggu": w, "keranjang": r.mean(), "kurs": kurs_m[w], "dxy": dxy_m[w]})
mgd = pd.DataFrame(mg).set_index("minggu")
print(f"\n3️⃣  UJI TAMBAHAN mingguan: perubahan minggu w -> keranjang minggu w+1 ({len(mgd)} minggu)")
for nama, x in [("kurs", mgd["kurs"]), ("DXY", mgd["dxy"])]:
    k, tr, tb, n = regresi(mgd["keranjang"], x, minimal=100)
    print(f"   {nama:5} kemiringan {k:+.3f}  t robust = {tr:+5.1f}  t biasa = {tb:+5.1f}  ({n} minggu)")

# ===== 5. Stabilitas uji utama =====
print("\n4️⃣  Stabilitas uji utama bulanan (t robust per paruh)")
tengah = b.index[len(b) // 2]
for nama, kol in [("H1 kurs", "kurs"), ("H2 DXY", "dxy")]:
    _, ta, _, na = regresi(b["keranjang"].loc[:tengah], b[kol].loc[:tengah])
    _, tb2, _, nb = regresi(b["keranjang"].loc[tengah:].iloc[1:], b[kol].loc[tengah:].iloc[1:])
    print(f"   {nama:8} paruh 1: t = {ta:+5.1f} ({na} bln)   paruh 2: t = {tb2:+5.1f} ({nb} bln)   batas {tengah}")
