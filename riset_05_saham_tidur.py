"""
RISET #5: SAHAM "TIDUR" TELAT BEREAKSI (lead-lag saham likuid -> saham kurang diperhatikan)
==========================================================================================

DUGAAN (ditulis 2026-11-20, SEBELUM melihat hubungan apa pun)
------------------------------------------------------------
Saham besar & likuid (diawasi asing, analis, dana besar) bereaksi duluan terhadap berita pasar. Saham lapis
kedua yang kurang diperhatikan menyusul BELAKANGAN. Jadi: keranjang LIKUID naik minggu ini -> keranjang "TIDUR"
naik minggu depan (tanda positif). Literatur: Lo & MacKinlay (1990), Hou (2007) "industry information diffusion".
Kenapa bisa beda dengan riset #1-#4: yang diuji bukan berita jelas, tapi lambatnya perhatian investor pada saham kecil.
Perkiraan jujur:
  - Secara statistik hubungan ini kemungkinan BESAR ada (t > 3), tapi sebagian bisa ILUSI HARGA BASI: saham yang tidak
    bertransaksi mencatat harga kemarin, jadi "reaksinya" baru tercatat saat transaksi berikutnya.
  - Strategi kemungkinan GAGAL setelah biaya (saham tidur juga punya spread lebar yang belum masuk asumsi 0,4%).

KERANJANG (tiap akhir bulan, informasi saat itu saja; saringan riset #2: harga >= Rp100, >= 80% hari aktif,
tanpa lompatan > 50%, median nilai transaksi 60 hari >= Rp1 miliar):
  LIKUID = peringkat nilai transaksi 1-30.   TIDUR = peringkat 31-130 (100 saham berikutnya). Bobot sama.

UJI (4, ditetapkan sekarang; ambang |t| > 3, t robust/White):
  U1 mingguan : return LIKUID minggu w (tutup Jumat ke tutup Jumat) -> return TIDUR minggu w+1
                (beli tutup hari bursa pertama minggu w+1, jual tutup hari bursa pertama minggu w+2). Dugaan positif.
  U2 mingguan : sama, tapi target = TIDUR - LIKUID minggu w+1 ("menyusul" setelah gerak pasar dibuang). Dugaan positif.
  U3 strategi : pegang TIDUR minggu w+1 hanya kalau LIKUID naik minggu w, selain itu kas (tanpa bunga, konservatif)
                vs selalu pegang TIDUR. Biaya: 0,4% x porsi berganti + 0,4% penuh tiap keluar-masuk.
  U4 harian (DIAGNOSIS, tidak bisa dijalankan): LIKUID hari d -> TIDUR hari d+1.
CEK HARGA BASI (diagnosis): ulangi U1 hanya dengan saham TIDUR yang BENAR-BENAR bertransaksi di hari beli DAN hari
  jual. Kalau efek mengecil jauh -> sebagian besar ilusi harga basi. (Memakai info hari jual: hanya untuk diagnosis.)
Data uji 2019+ DIKUNCI (--buka-uji). Uji kode: --tes-tiruan (TIDUR minggu w+1 = 0,3 x LIKUID minggu w) & --tes-kosong.
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
MIN_HARGA, MIN_HARI_AKTIF, MAX_LOMPAT, MIN_NILAI = 100, 0.8, 0.5, 1e9
N_LIKUID, N_TIDUR = 30, 100


def jadi_tanggal(x):
    t = pd.DatetimeIndex(pd.to_datetime(x))
    if t.tz is not None:
        t = t.tz_localize(None)
    return t.normalize().astype("datetime64[ns]")


def nilai_t(s):
    s = pd.Series(s).dropna()
    return s.mean() / (s.std(ddof=1) / np.sqrt(len(s))) if len(s) > 2 else np.nan


def regresi(y, x, minimal=50):
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
    return adj.loc[hari], tutup.loc[hari], volume.loc[hari]


def buat_data_tiruan(dengan_pola):
    """200 saham palsu; S000-S039 sangat likuid, sisanya makin sepi. Faktor pasar harian bersama.
    Pola (kalau ada): saham S040+ (calon TIDUR) mendapat dorongan 0,3 x return faktor pasar minggu
    sebelumnya, dibagi rata ke hari-hari minggu ini. Tanpa pola: semua acak."""
    acak = np.random.default_rng(3)
    hari = pd.bdate_range("2002-01-01", "2026-11-13").astype("datetime64[ns]")
    kolom = [f"S{i:03d}" for i in range(200)]
    pasar = acak.normal(0.0003, 0.012, len(hari))
    harian = pd.DataFrame(acak.normal(0, 0.02, (len(hari), 200)), index=hari, columns=kolom).add(pasar, axis=0)
    if dengan_pola:
        mg = hari.to_period("W-FRI")
        r_mg = pd.Series(pasar, index=hari).groupby(mg).sum()
        jml = pd.Series(mg).value_counts()
        dorong = r_mg.shift(1).reindex(mg).fillna(0).values * 0.3 / jml.reindex(mg).values
        harian.iloc[:, 40:] = harian.iloc[:, 40:].add(dorong, axis=0)
    adj = 1000 * np.exp(harian.cumsum())
    skala = np.geomspace(5e8, 2e5, 200)                 # volume menurun: S000 paling likuid
    volume = pd.DataFrame(np.tile(skala, (len(hari), 1)), index=hari, columns=kolom)
    return adj, adj.copy(), volume


if TES_TIRUAN or TES_KOSONG:
    adj, tutup, volume = buat_data_tiruan(TES_TIRUAN)
    print(f"🧪 MODE TES: data PALSU {'dengan pola tersembunyi (0,3)' if TES_TIRUAN else 'tanpa pola'}")
else:
    adj, tutup, volume = muat_data_asli()
hari = adj.index
print(f"📥 {adj.shape[1]} saham, {len(hari):,} hari bursa, {hari[0].date()} s/d {hari[-1].date()}")

# ===== 2. Keranjang bulanan (informasi saat itu saja) =====
aktif = volume.fillna(0) > 0
median_nilai = (tutup * volume).where(aktif).rolling(60, min_periods=40).median()
porsi_aktif = aktif.rolling(250, min_periods=250).mean()
lompat_maks = adj.pct_change(fill_method=None).abs().rolling(250, min_periods=200).max()
akhir_bln = pd.Series(hari, index=hari).groupby(hari.to_period("M")).max()
keranjang = {}
for bln, tgl in akhir_bln.items():
    ok = ((tutup.loc[tgl] >= MIN_HARGA) & (porsi_aktif.loc[tgl] >= MIN_HARI_AKTIF)
          & (lompat_maks.loc[tgl] < MAX_LOMPAT) & (median_nilai.loc[tgl] >= MIN_NILAI))
    urut = median_nilai.loc[tgl][ok].sort_values(ascending=False).index
    if len(urut) >= N_LIKUID + N_TIDUR * 0.5:
        keranjang[bln] = (list(urut[:N_LIKUID]), list(urut[N_LIKUID:N_LIKUID + N_TIDUR]))


def anggota(tgl):
    """Keranjang dari akhir bulan SEBELUM tanggal ini."""
    return keranjang.get(tgl.to_period("M") - 1)


# ===== 3. Mingguan =====
mg_kal = pd.period_range(hari.min().to_period("W-FRI"), hari.max().to_period("W-FRI"), freq="W-FRI")
gm = pd.Series(hari, index=hari).groupby(hari.to_period("W-FRI"))
awal, akhir = gm.min().reindex(mg_kal), gm.max().reindex(mg_kal)
harga_awal = adj.reindex(awal.values).set_axis(mg_kal)
harga_akhir = adj.reindex(akhir.values).set_axis(mg_kal)
aktif_awal = aktif.reindex(awal.values).set_axis(mg_kal)
ret_depan = harga_awal.shift(-2) / harga_awal.shift(-1) - 1        # dipegang minggu w+1
ret_minggu = harga_akhir / harga_akhir.shift(1) - 1                 # Jumat ke Jumat, minggu w (sinyal)
jual = awal.shift(-2)
pilih = (awal > BATAS_LATIH) & jual.notna() if BUKA_DATA_UJI else (jual <= BATAS_LATIH)
print(f"🔒 Data uji {'DIBUKA' if BUKA_DATA_UJI else 'DIKUNCI, tidak disentuh'}. "
      f"Menganalisis {'DATA UJI (2019+)' if BUKA_DATA_UJI else 'DATA LATIH (posisi ditutup s/d 2018-12-31)'}.\n")

baris, lalu_tidur = [], set()
for w in mg_kal[pilih.values]:
    if pd.isna(akhir[w]) or pd.isna(awal[w]):
        continue
    k = anggota(akhir[w])
    if k is None:
        continue
    lik, tid = k
    sinyal = ret_minggu.loc[w, lik].mean()
    r_lik = ret_depan.loc[w, lik].dropna()
    r_tid = ret_depan.loc[w, tid].dropna()
    # Cek harga basi: saham TIDUR yang benar-benar bertransaksi di hari beli (awal w+1) DAN hari jual (awal w+2)
    beli_ok = aktif_awal.shift(-1).loc[w, tid].fillna(False).astype(bool)
    jual_ok = aktif_awal.shift(-2).loc[w, tid].fillna(False).astype(bool)
    r_tid_nyata = ret_depan.loc[w, tid][beli_ok & jual_ok].dropna()
    if len(r_tid) < N_TIDUR * 0.5 or len(r_lik) < N_LIKUID * 0.8 or pd.isna(sinyal):
        continue
    ganti = 1 - len(set(r_tid.index) & lalu_tidur) / len(r_tid) if lalu_tidur else 1.0
    baris.append({"minggu": w, "sinyal": sinyal, "likuid": r_lik.mean(), "tidur": r_tid.mean(),
                  "tidur_nyata": r_tid_nyata.mean() if len(r_tid_nyata) >= 20 else np.nan,
                  "porsi_nyata": len(r_tid_nyata) / len(r_tid), "ganti": ganti})
    lalu_tidur = set(r_tid.index)
d = pd.DataFrame(baris).set_index("minggu")
print(f"Mingguan: {len(d)} minggu ({d.index[0].end_time.date()} s/d {d.index[-1].end_time.date()})")

print("\n0️⃣  Cek kewajaran: korelasi LIKUID & TIDUR di minggu yang SAMA")
r_sama_tidur = pd.Series({w: ret_minggu.loc[w, anggota(akhir[w])[1]].mean() for w in d.index})
b0, t0, _, n0 = regresi(r_sama_tidur, d["sinyal"])
print(f"   kemiringan {b0:+.2f}, t robust {t0:+.1f} ({n0} minggu)  (dugaan: jelas positif)")

print("\n1️⃣  U1: LIKUID minggu w -> TIDUR minggu w+1 (dugaan positif)")
b, tr, tb, n = regresi(d["tidur"], d["sinyal"])
print(f"   kemiringan {b:+.3f}  t robust {tr:+.1f}  t biasa {tb:+.1f}  ({n} minggu)")
print(f"   TIDUR minggu depan setelah LIKUID naik: {d['tidur'][d['sinyal'] > 0].mean():+.3%}, "
      f"setelah turun: {d['tidur'][d['sinyal'] <= 0].mean():+.3%}")

print("\n2️⃣  U2: LIKUID minggu w -> (TIDUR - LIKUID) minggu w+1 (dugaan positif: 'menyusul')")
b, tr, tb, n = regresi(d["tidur"] - d["likuid"], d["sinyal"])
print(f"   kemiringan {b:+.3f}  t robust {tr:+.1f}  t biasa {tb:+.1f}  ({n} minggu)")

print("\n🔎 CEK HARGA BASI (diagnosis): U1 hanya dengan saham TIDUR yang bertransaksi di hari beli & jual")
b, tr, tb, n = regresi(d["tidur_nyata"], d["sinyal"])
print(f"   kemiringan {b:+.3f}  t robust {tr:+.1f}  ({n} minggu; rata-rata {d['porsi_nyata'].mean():.0%} saham TIDUR lolos)")

# U3 strategi
masuk = d["sinyal"] > 0
pindah = masuk.astype(int).diff().abs().fillna(1)
biaya_isi = d["ganti"] * BIAYA
strat = np.where(masuk, d["tidur"] - biaya_isi, 0.0) - pindah * BIAYA / 2
selalu = d["tidur"] - biaya_isi
s = pd.Series(strat, index=d.index)
lebih = s - selalu
print("\n3️⃣  U3 strategi: pegang TIDUR hanya setelah LIKUID naik, selain itu kas")
print(f"   Di saham {masuk.mean():.0%} minggu, keluar-masuk {pindah.iloc[1:].mean():.0%} minggu, "
      f"ganti isi TIDUR {d['ganti'].iloc[1:].mean():.0%}/minggu")
print(f"   Strategi bersih {s.mean():+.3%}/mg | selalu pegang {selalu.mean():+.3%}/mg | "
      f"selisih {lebih.mean():+.3%}/mg  t = {nilai_t(lebih):+.1f}  (~{(1 + lebih.mean()) ** 52 - 1:+.1%}/thn)")
kotor = np.where(masuk, d["tidur"], 0.0) - d["tidur"]
print(f"   Selisih KOTOR (tanpa biaya): {kotor.mean():+.3%}/mg  t = {nilai_t(kotor):+.1f}")

# ===== 4. U4 harian (diagnosis) =====
ret_h = adj.pct_change(fill_method=None)
bh = []
for tgl in hari[1:]:
    k = anggota(tgl)
    if k is None:
        continue
    bh.append((tgl, ret_h.loc[tgl, k[0]].mean(), ret_h.loc[tgl, k[1]].mean()))
h = pd.DataFrame(bh, columns=["tgl", "likuid", "tidur"]).set_index("tgl")
h["tidur_besok"] = h["tidur"].shift(-1)
h["tgl_besok"] = pd.Series(h.index, index=h.index).shift(-1)
# Hari d hanya dipakai kalau hari d+1 (return yang diprediksi) juga masih di periode yang dianalisis.
# (Versi pertama bocor: hari bursa terakhir 2018 memakai return 2 Januari 2019. Ketahuan oleh cek hapus-data-2019+.)
h = h[h["tgl_besok"] <= BATAS_LATIH] if not BUKA_DATA_UJI else h[h.index > BATAS_LATIH]
b, tr, tb, n = regresi(h["tidur_besok"], h["likuid"], minimal=200)
print(f"\n4️⃣  U4 harian (diagnosis, tidak bisa dijalankan): LIKUID hari d -> TIDUR hari d+1")
print(f"   kemiringan {b:+.3f}  t robust {tr:+.1f}  ({n} hari)")

# ===== 5. Stabilitas U1 =====
tengah = d.index[len(d) // 2]
_, ta, _, na = regresi(d["tidur"].loc[:tengah], d["sinyal"].loc[:tengah])
_, tb2, _, nb = regresi(d["tidur"].loc[tengah:].iloc[1:], d["sinyal"].loc[tengah:].iloc[1:])
print(f"\n5️⃣  Stabilitas U1: paruh 1 t = {ta:+.1f} ({na} mg), paruh 2 t = {tb2:+.1f} ({nb} mg), batas {tengah.end_time.date()}")
