"""
RISET #2: MOMENTUM SAHAM IDX
============================

DUGAAN (ditulis 2026-11-19, SEBELUM melihat hasil apa pun)
---------------------------------------------------------
H1. Momentum menengah: saham yang naik paling banyak selama 12 bulan terakhir (bulan terakhir
    dilewati, disebut "12-1") cenderung tetap lebih baik bulan depan.
    Alasan logis: investor bereaksi terlalu lambat (underreaction) terhadap berita, dan informasi
    menyebar pelan di pasar yang didominasi investor ritel dan analis yang sedikit.
    Kenapa bulan terakhir dilewati: return 1 bulan terakhir biasanya justru BERBALIK (lihat H2),
    jadi kalau dicampur sinyalnya kotor.
    Perkiraan jujur: di Asia momentum terkenal LEMAH (Jepang hampir nol). Saya menduga t < 3.
H2. Pembalikan jangka pendek: saham yang paling jatuh bulan lalu cenderung naik bulan ini
    (pembeli/penjual panik dibayar oleh penyedia likuiditas). Di saham kurang likuid efek ini
    biasanya kuat, TAPI sebagian besar ilusi pantulan bid-ask dan habis dimakan biaya.

Hanya 4 varian yang diuji (ditetapkan sekarang, tidak ditambah setelah melihat hasil):
    12-1, 6-1, 3-1 (momentum)   dan   1-0 (pembalikan 1 bulan, berharap tanda NEGATIF)

DESAIN UJI
----------
- Akhir tiap bulan: hitung sinyal hanya dari data yang SUDAH ada saat itu.
- Semesta (disaring dengan informasi saat itu saja):
    harga >= Rp100, median nilai transaksi 60 hari >= Rp1 miliar,
    >= 80% hari ada transaksi dalam 250 hari, tidak ada lompatan harian > 50% (curiga data salah).
- Beli di harga TUTUP hari bursa PERTAMA bulan berikutnya (jeda 1 hari supaya tidak
  menipu diri dengan pantulan bid-ask), tahan 1 bulan, bobot sama.
- Bagi semesta jadi 5 kelompok (kuintil) menurut sinyal.
- Ukuran utama:
    a) IC = korelasi peringkat (Spearman) sinyal vs return bulan depan, dirata-rata per bulan.
    b) "Long-only": kelompok terbaik dikurangi rata-rata semesta, SETELAH biaya 0,4% x perputaran.
       (IDX praktis tidak bisa short, jadi selisih atas-bawah hanya untuk diagnosis.)
- Ambang lolos: t > 3. Data uji 2019+ DIKUNCI (buka sekali di akhir dengan --buka-uji).

PERINGATAN DATA
---------------
Daftar saham = saham yang MASIH tercatat sekarang. Saham yang sudah delisting (sering yang hancur)
tidak ada. Efeknya: kelompok "pecundang" tampak lebih bagus dari kenyataan, dan semesta secara
umum tampak lebih untung. Hasil long-only harus dibaca dengan curiga.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BATAS_LATIH = pd.Timestamp("2018-12-31")
BUKA_DATA_UJI = "--buka-uji" in sys.argv
BIAYA = 0.004                       # beli + jual di IDX
MIN_HARGA = 100
MIN_NILAI = 1e9                     # Rp 1 miliar per hari (median 60 hari)
MIN_HARI_AKTIF = 0.8
MAX_LOMPAT = 0.5
MIN_SAHAM = 30                      # bulan dengan semesta lebih kecil dari ini dilewati
VARIAN = {"12-1": (12, 1), "6-1": (6, 1), "3-1": (3, 1), "1-0 (pembalikan)": (1, 0)}


def jadi_tanggal(x):
    """Tanggal polos tanpa zona waktu, presisi ns (menghindari jebakan ms vs ns)."""
    t = pd.DatetimeIndex(pd.to_datetime(x))
    if t.tz is not None:
        t = t.tz_localize(None)
    return t.normalize().astype("datetime64[ns]")


def nilai_t(s):
    s = pd.Series(s).dropna()
    return s.mean() / (s.std(ddof=1) / np.sqrt(len(s))) if len(s) > 2 else np.nan


TES_TIRUAN = "--tes-tiruan" in sys.argv     # data palsu DENGAN momentum tersembunyi: harus ditemukan
TES_KOSONG = "--tes-kosong" in sys.argv     # data palsu TANPA pola: hasil harus ~nol (cek bocoran masa depan)


def buat_data_tiruan(dengan_pola):
    """150 saham palsu, hari kerja 2000-2026. Tiap saham punya 'arah' tersembunyi yang berubah pelan
    tiap bulan (AR 0,9). Kalau dengan_pola=False, arahnya nol: harga murni acak."""
    acak = np.random.default_rng(42)
    tgl = pd.bdate_range("2000-07-03", "2026-11-13").astype("datetime64[ns]")
    n_saham = 150
    bln = tgl.to_period("M")
    kode_bln = pd.factorize(bln)[0]
    arah = np.zeros((kode_bln.max() + 1, n_saham))
    for m in range(1, len(arah)):
        arah[m] = 0.9 * arah[m - 1] + acak.normal(0, 0.012, n_saham)     # arah bulanan, sd ~2,8%
    harian = acak.normal(0, 0.02, (len(tgl), n_saham))
    if dengan_pola:
        harian += arah[kode_bln] / 21
    kolom = [f"S{i:03d}" for i in range(n_saham)]
    a = pd.DataFrame(1000 * np.exp(np.cumsum(harian, axis=0)), index=tgl, columns=kolom)
    v = pd.DataFrame(1e7, index=tgl, columns=kolom)
    return a, a.copy(), v


# ===== 1. Muat data harian semua saham =====
if TES_TIRUAN or TES_KOSONG:
    adj, tutup, volume = buat_data_tiruan(dengan_pola=TES_TIRUAN)
    print(f"🧪 MODE TES: data PALSU {'dengan pola momentum tersembunyi' if TES_TIRUAN else 'tanpa pola'}")
else:
    adj, tutup, volume = {}, {}, {}
    for f in sorted(Path("data/raw/harga_idx").glob("*.parquet")):
        d = pd.read_parquet(f, columns=["Adj Close", "Close", "Volume"])
        d.index = jadi_tanggal(d.index)
        d = d[~d.index.duplicated(keep="last")]
        adj[f.stem], tutup[f.stem], volume[f.stem] = d["Adj Close"], d["Close"], d["Volume"]
    adj, tutup, volume = (pd.DataFrame(x).sort_index() for x in (adj, tutup, volume))
    if __import__("os").environ.get("BERSIHKAN_IDX", "1") == "1":   # titik rusak Yahoo (bersih_idx.py)
        from bersih_idx import bersihkan
        adj2 = bersihkan(adj)
        rusak = adj2.isna() & adj.notna()
        print(f"🧹 {int(rusak.values.sum())} titik rusak dikosongkan (BERSIHKAN_IDX=0 untuk versi lama)")
        adj, tutup = adj2, tutup.mask(rusak)

# Hari bursa = hari kerja dengan minimal 10 saham bertransaksi (buang baris libur buatan yfinance)
aktif = volume.fillna(0) > 0
hari_bursa = aktif.index[(aktif.sum(axis=1) >= 10) & (aktif.index.day_of_week < 5)]
adj, tutup, volume, aktif = (x.loc[hari_bursa] for x in (adj, tutup, volume, aktif))
print(f"📥 {adj.shape[1]} saham, {len(hari_bursa):,} hari bursa, "
      f"{hari_bursa[0].date()} s/d {hari_bursa[-1].date()}")

# ===== 2. Bahan penyaring semesta (semua hanya memakai data masa lalu) =====
nilai_trx = (tutup * volume).where(aktif)
median_nilai = nilai_trx.rolling(60, min_periods=40).median()
porsi_aktif = aktif.rolling(250, min_periods=250).mean()
ret_harian = adj.pct_change(fill_method=None)
lompat_maks = ret_harian.abs().rolling(250, min_periods=200).max()

# ===== 3. Kalender bulanan =====
bulan = pd.Series(hari_bursa, index=hari_bursa).groupby(hari_bursa.to_period("M"))
akhir_bulan = pd.DatetimeIndex(bulan.max().values)          # tanggal sinyal
awal_bulan = pd.DatetimeIndex(bulan.min().values)           # tanggal beli/jual
harga_akhir = adj.loc[akhir_bulan].reset_index(drop=True)   # baris i = akhir bulan ke-i
harga_awal = adj.loc[awal_bulan].reset_index(drop=True)

# Return pegang: tutup hari pertama bulan i+1 -> tutup hari pertama bulan i+2
ret_pegang = harga_awal.shift(-2) / harga_awal.shift(-1) - 1
tgl_jual = pd.Series(awal_bulan).shift(-2)

lolos = ((tutup.loc[akhir_bulan] >= MIN_HARGA) & (median_nilai.loc[akhir_bulan] >= MIN_NILAI)
         & (porsi_aktif.loc[akhir_bulan] >= MIN_HARI_AKTIF)
         & (lompat_maks.loc[akhir_bulan] < MAX_LOMPAT)).reset_index(drop=True)

if BUKA_DATA_UJI:
    pilih_bulan = (pd.Series(akhir_bulan) > BATAS_LATIH) & tgl_jual.notna()
    label = "DATA UJI (2019+)"
else:
    pilih_bulan = tgl_jual <= BATAS_LATIH
    label = f"DATA LATIH (s/d {BATAS_LATIH.date()})"
print(f"🔒 Data uji {'DIBUKA' if BUKA_DATA_UJI else 'DIKUNCI, tidak disentuh'}. Menganalisis {label}.\n")


# ===== 4. Uji tiap varian =====
nilai_akhir = median_nilai.loc[akhir_bulan].reset_index(drop=True)


def uji(nama, lihat, lewati, likuid_teratas=None, potong=None):
    """likuid_teratas: hanya N saham dengan nilai transaksi terbesar (diukur saat itu).
    potong: batasi return bulanan di +/- angka ini (meredam data salah / kejadian ekstrem)."""
    sinyal = harga_akhir.shift(lewati) / harga_akhir.shift(lihat) - 1
    baris = []
    sebelumnya = set()
    sebelumnya_semesta = set()
    for i in np.where(pilih_bulan)[0]:
        ok = lolos.loc[i] & sinyal.loc[i].notna() & ret_pegang.loc[i].notna()
        if likuid_teratas:
            ok = ok & (nilai_akhir.loc[i].where(ok).rank(ascending=False) <= likuid_teratas)
        if ok.sum() < MIN_SAHAM:
            continue
        s, r = sinyal.loc[i][ok], ret_pegang.loc[i][ok]
        if potong:
            r = r.clip(-potong, potong)
        kelompok = pd.qcut(s.rank(method="first"), 5, labels=False) + 1
        rata = r.groupby(kelompok).mean()
        teratas = set(s.index[kelompok == 5])
        terbawah = set(s.index[kelompok == 1])
        semesta = set(s.index)
        # Untuk pembalikan, "kelompok terbaik" = yang paling JATUH bulan lalu (kelompok 1)
        pilihan = terbawah if lewati == 0 else teratas
        ganti = 1 - len(pilihan & sebelumnya) / len(pilihan) if sebelumnya else 1.0
        ganti_s = 1 - len(semesta & sebelumnya_semesta) / len(semesta) if sebelumnya_semesta else 1.0
        ret_pilihan = r[list(pilihan)].mean()
        baris.append({"tanggal": akhir_bulan[i], "n": int(ok.sum()), "ic": s.rank().corr(r.rank()),
                      **{f"K{k}": rata.get(k, np.nan) for k in range(1, 6)},
                      "pilihan": ret_pilihan, "semesta": r.mean(),
                      "lebih_kotor": ret_pilihan - r.mean(),
                      "lebih_bersih": (ret_pilihan - ganti * BIAYA) - (r.mean() - ganti_s * BIAYA),
                      "ganti": ganti})
        sebelumnya, sebelumnya_semesta = pilihan, semesta
    return pd.DataFrame(baris).set_index("tanggal")


hasil = {nama: uji(nama, *p) for nama, p in VARIAN.items()}

c = next(iter(hasil.values()))
print(f"Bulan dianalisis: {len(c)} ({c.index[0]:%Y-%m} s/d {c.index[-1]:%Y-%m}), "
      f"semesta {c['n'].min()}–{c['n'].max()} saham (median {c['n'].median():.0f})\n")

print("1️⃣  Kemampuan memprediksi (IC = korelasi peringkat sinyal vs return bulan depan)")
print(f"   {'varian':18}{'IC rata':>9}{'t':>7}   {'K1 (bawah)':>11}{'K2':>8}{'K3':>8}{'K4':>8}{'K5 (atas)':>10}"
      f"{'K5-K1':>9}{'t':>7}")
for nama, h in hasil.items():
    sel = h["K5"] - h["K1"]
    print(f"   {nama:18}{h['ic'].mean():>+9.3f}{nilai_t(h['ic']):>+7.1f}   "
          + "".join(f"{h[f'K{k}'].mean():>{11 if k == 1 else (10 if k == 5 else 8)}.2%}" for k in range(1, 6))
          + f"{sel.mean():>+9.2%}{nilai_t(sel):>+7.1f}")
print("   (return rata-rata per BULAN, bobot sama. K5-K1 butuh short = tidak bisa di IDX, hanya diagnosis)")

print("\n2️⃣  Strategi yang BISA dijalankan: beli kelompok terbaik saja, dibanding beli semua semesta")
print(f"   {'varian':18}{'kelompok':>9}{'ganti/bln':>10}{'lebih kotor':>12}{'lebih bersih':>13}{'t bersih':>9}"
      f"{'per tahun':>10}{'% bln menang':>13}")
for nama, h in hasil.items():
    k = "K1" if VARIAN[nama][1] == 0 else "K5"
    b = h["lebih_bersih"]
    print(f"   {nama:18}{k:>9}{h['ganti'].iloc[1:].mean():>10.0%}{h['lebih_kotor'].mean():>+12.2%}"
          f"{b.mean():>+13.2%}{nilai_t(b):>+9.1f}{(1 + b.mean()) ** 12 - 1:>+10.1%}{(b > 0).mean():>13.0%}")
print(f"   (biaya {BIAYA:.1%} x porsi saham yang diganti tiap bulan, juga dibebankan ke semesta)")

print("\n3️⃣  Stabilitas: IC per paruh waktu (sinyal sungguhan harus konsisten)")
for nama, h in hasil.items():
    tengah = h.index[len(h) // 2]
    a, b = h.loc[:tengah, "ic"], h.loc[tengah:, "ic"].iloc[1:]
    print(f"   {nama:18} {a.index[0]:%Y}-{a.index[-1]:%Y}: IC {a.mean():+.3f} (t {nilai_t(a):+.1f})   "
          f"{b.index[0]:%Y}-{b.index[-1]:%Y}: IC {b.mean():+.3f} (t {nilai_t(b):+.1f})")

print("\n4️⃣  Uji ketahanan varian 12-1 (bukan varian baru, cek apakah hasilnya ilusi)")
cek = {"semua (seperti di atas)": hasil["12-1"],
       "50 saham paling likuid": uji("12-1", 12, 1, likuid_teratas=50),
       "return dipotong ±30%/bln": uji("12-1", 12, 1, potong=0.30)}
print(f"   {'versi':26}{'IC':>8}{'t':>7}{'K5-K1':>9}{'t':>7}{'K5 lebih bersih':>17}{'t':>7}")
for nama, h in cek.items():
    sel = h["K5"] - h["K1"]
    print(f"   {nama:26}{h['ic'].mean():>+8.3f}{nilai_t(h['ic']):>+7.1f}{sel.mean():>+9.2%}{nilai_t(sel):>+7.1f}"
          f"{h['lebih_bersih'].mean():>+17.2%}{nilai_t(h['lebih_bersih']):>+7.1f}")

print("\nℹ️  Ingat: daftar saham hanya yang masih tercatat sekarang (survivorship bias).")
