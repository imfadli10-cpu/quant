"""
RISET #26: EFEK KALENDER IDX — HARI SEBELUM LIBUR BURSA & PERGANTIAN BULAN, data LATIH saja
========================================================================================

DUGAAN (ditulis 2026-11-21 SEBELUM menghitung apa pun; di-commit sebelum dijalankan)
--------------------------------------------------------------------------------
  H1 PRA-LIBUR (Ariel 1990; Kim-Park 1994): hari bursa tepat sebelum libur (hari kerja Senin-Jumat tanpa perdagangan)
     memberi return jauh di atas hari biasa. Alasan: suasana hati menjelang libur + penjual pendek menutup posisi.
     Riset #15 U2 (khusus Lebaran) searah: +0,42%/hari vs +0,09%, t 1,7. Di sini SEMUA libur -> lebih banyak peristiwa.
  H2 PERGANTIAN BULAN (Ariel 1987; McConnell-Xu 2008): return terkumpul di hari bursa terakhir bulan + 3 hari bursa
     pertama bulan berikutnya (arus dana gaji/dana pensiun/reksa dana). Di Indonesia gaji umumnya dibayar akhir bulan.
Perkiraan jujur: efek kalender banyak melemah setelah dipublikasikan; IDX kurang diteliti, mungkin masih ada sisa.

DATA: keranjang 30 saham paling likuid (riset #4/#15), return harian tutup-ke-tutup, 2002-05..2018-12.
  Hari libur = hari kerja (Senin-Jumat) tanpa perdagangan di antara dua hari bursa. Jadwal libur bursa diumumkan
  jauh hari -> diketahui sebelumnya (bukan look-ahead).
UJI (4; dua arah; |t| > 3; t Welch hari peristiwa vs hari lain):
  U1 return hari PRA-LIBUR vs hari lain.
  U2 return jendela PERGANTIAN BULAN (hari bursa terakhir bulan + 3 hari bursa pertama) vs hari lain (per hari).
  U3 STRATEGI pra-libur: beli tutup 1 hari sebelum hari pra-libur, jual tutup hari pra-libur (pegang 1 hari),
     biaya realistis 0,4% + 0,1% spread saham likuid = 0,5% bolak-balik: rata-rata bersih per peristiwa, t.
  U4 STRATEGI pergantian bulan: beli tutup H-2 (hari sebelum hari bursa terakhir), jual tutup hari bursa ke-3,
     pegang 4 hari, biaya 0,5%: bersih per bulan vs pegang keranjang 4 hari biasa (selisih), t.
Data uji 2019+ DIKUNCI. Uji kode: --tes-tiruan (pra-libur +0,3%, pergantian bulan +0,15%/hari) & --tes-kosong.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BATAS_LATIH = pd.Timestamp("2018-12-31")
BUKA_DATA_UJI = "--buka-uji" in sys.argv
TES_TIRUAN, TES_KOSONG = "--tes-tiruan" in sys.argv, "--tes-kosong" in sys.argv
BIAYA = 0.005


def t_welch(a, b):
    a, b = pd.Series(a).dropna(), pd.Series(b).dropna()
    return (a.mean() - b.mean()) / np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))


def t_rata(x):
    x = pd.Series(x).dropna()
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))


if TES_TIRUAN or TES_KOSONG:
    acak = np.random.default_rng(26)
    semua_hari = pd.bdate_range("2002-01-01", "2026-11-13")
    libur = pd.DatetimeIndex(acak.choice(semua_hari, 300, replace=False))
    hari = semua_hari.difference(libur).astype("datetime64[ns]")
    r = pd.Series(acak.normal(0.0005, 0.012, len(hari)), index=hari)
    print(f"🧪 MODE TES: data PALSU {'dengan pola' if TES_TIRUAN else 'tanpa pola'}")
else:
    kode = Path("riset_15_ramadan.py").read_text(encoding="utf-8").split("# ===== Label kalender =====")[0]
    ns, simpan = {}, sys.argv
    sys.argv = [sys.argv[0]]
    exec(compile(kode, "riset_15_bagian", "exec"), ns)
    sys.argv = simpan
    r = ns["ret_keranjang"].dropna()
    hari = r.index

# Label: pra-libur = ada hari kerja (Sen-Jum) tanpa perdagangan sebelum hari bursa berikutnya
berikut = pd.Series(hari[1:].append(pd.DatetimeIndex([pd.NaT])), index=hari)
hari_kerja_antara = [len(pd.bdate_range(a + pd.Timedelta(days=1), b - pd.Timedelta(days=1))) if pd.notna(b) else 0
                     for a, b in zip(hari, berikut)]
pra_libur = pd.Series(np.array(hari_kerja_antara) > 0, index=hari)
pra_libur.iloc[-1] = False
bln = hari.to_period("M")
urut_awal = pd.Series(hari, index=hari).groupby(bln).cumcount()                         # 0 = hari bursa pertama bulan
urut_akhir = pd.Series(hari, index=hari).groupby(bln).cumcount(ascending=False)         # 0 = hari bursa terakhir
gb = pd.Series((urut_akhir == 0).values | (urut_awal <= 2).values, index=hari)          # jendela pergantian bulan

if TES_TIRUAN:
    r = r + 0.003 * pra_libur + 0.0015 * gb

# Latih: hari bursa BERIKUTNYA juga harus <= batas (label pra-libur bergantung padanya; ditemukan cek hapus-2019+)
pilih = (hari > BATAS_LATIH) if BUKA_DATA_UJI else ((hari <= BATAS_LATIH) & (berikut.values <= BATAS_LATIH))
pilih = pd.Series(pilih, index=hari)
pilih.iloc[-1] = False                                   # hari terakhir tidak punya label pra-libur yang pasti
print(f"🔒 Data uji {'DIBUKA' if BUKA_DATA_UJI else 'DIKUNCI'}.\n")
rr, pl, g = r[pilih], pra_libur[pilih], gb[pilih]
print(f"   {len(rr)} hari bursa ({rr.index.min():%Y-%m} s/d {rr.index.max():%Y-%m}); pra-libur {pl.sum()} hari; "
      f"jendela pergantian bulan {g.sum()} hari")
print(f"   U1 PRA-LIBUR        : {rr[pl].mean():+.3%}/hari vs lain {rr[~pl].mean():+.3%} -> t {t_welch(rr[pl], rr[~pl]):+.1f}")
print(f"   U2 PERGANTIAN BULAN : {rr[g].mean():+.3%}/hari vs lain {rr[~g].mean():+.3%} -> t {t_welch(rr[g], rr[~g]):+.1f}")
# U3: pegang 1 hari (hari pra-libur), bersih
u3 = rr[pl] - BIAYA
print(f"   U3 strategi pra-libur (pegang 1 hari, biaya {BIAYA:.1%}): bersih {u3.mean():+.3%}/peristiwa t {t_rata(u3):+.1f} "
      f"(~{u3.mean() * pl.sum() / (len(rr) / 250):+.1%}/thn)")
# U4: per bulan, return kumulatif 4 hari jendela (hari terakhir + 3 pertama berikutnya) - 4 x rata-rata hari lain - biaya
rata_lain = rr[~g].mean()
jendela = []
idx = list(rr.index)
for i, t in enumerate(idx):
    if urut_akhir[t] == 0 and i + 3 < len(idx) and all(pilih[idx[i + k]] for k in range(4)):
        kum = np.prod(1 + rr.iloc[i:i + 4].values) - 1
        jendela.append(kum - 4 * rata_lain - BIAYA)
u4 = pd.Series(jendela)
print(f"   U4 strategi pergantian bulan (4 hari, biaya {BIAYA:.1%}): selisih bersih {u4.mean():+.3%}/bulan t {t_rata(u4):+.1f} "
      f"({len(u4)} bulan)")
tengah = rr.index[len(rr) // 2]
print(f"   paruh (U1): {t_welch(rr[:tengah][pl[:tengah]], rr[:tengah][~pl[:tengah]]):+.1f} / "
      f"{t_welch(rr[tengah:][pl[tengah:]], rr[tengah:][~pl[tengah:]]):+.1f} | "
      f"(U2): {t_welch(rr[:tengah][g[:tengah]], rr[:tengah][~g[:tengah]]):+.1f} / {t_welch(rr[tengah:][g[tengah:]], rr[tengah:][~g[tengah:]]):+.1f}")
