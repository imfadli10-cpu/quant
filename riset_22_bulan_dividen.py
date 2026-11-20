"""
RISET #22: "BULAN DIVIDEN" — saham yang DIPERKIRAKAN membagi dividen bulan ini -> return lebih tinggi? (data LATIH saja)
================================================================================================================

DUGAAN (ditulis 2026-11-20 SEBELUM data dividen diunduh/dilihat; di-commit sebelum dijalankan)
-----------------------------------------------------------------------------------------
Hartzmark & Solomon (2013, JFE "The dividend month premium"): saham yang diperkirakan ex-dividen di suatu bulan
(karena 12 bulan lalu ex-dividen di bulan yang sama) memberi return abnormal ~+0,5%/bln di AS. Penjelasan: investor
pemburu dividen membeli menjelang dividen (permintaan yang tidak peduli harga). Di IDX banyak investor ritel & dividen
dibayar sekali-dua kali setahun terkumpul di Apr-Jul -> efek bisa ada. Perkiraan jujur: efek kecil; biaya bisa memakan.

DESAIN (sama dengan riset #12/#13: semesta, waktu beli, return Adj Close = termasuk dividen):
  Sinyal akhir bulan m-1, beli tutup hari bursa pertama bulan m, jual tutup hari bursa pertama bulan m+1.
  KELOMPOK DIVIDEN bulan m = saham di semesta yang punya tanggal EX-dividen di bulan kalender (m-12).
  Info itu sudah publik 11 bulan sebelumnya -> tidak ada look-ahead.
  Bulan dengan kelompok < 5 saham dilewati.
UJI (ditetapkan sekarang):
  U1 selisih return kelompok dividen - semesta (bobot sama), rata-rata per bulan, t biasa & t (bulan sebagai pengamatan).
  U2 (PENENTU, satu ukuran) beli kelompok dividen, potong biaya realistis #13 (0,4% + max(spread CS, tick)) atas perputaran,
     dibanding semesta: t bersih > 3 -> kandidat KOMPONEN model gabungan (bukan strategi sendiri, karena hanya aktif beberapa bulan).
  Diagnosis (bukan uji): per bulan kalender & per paruh waktu; cakupan data dividen Yahoo per tahun.
Data uji 2019+ DIKUNCI. Uji kode: --tes-tiruan (kelompok dividen diberi +2%/bln palsu) & --tes-kosong.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

TES_TIRUAN, TES_KOSONG = "--tes-tiruan" in sys.argv, "--tes-kosong" in sys.argv
sys.path.insert(0, str(Path(".").resolve()))
kode = Path("riset_13_s2_hemat.py").read_text(encoding="utf-8").split("def simulasi(varian):")[0]
g = {"__file__": "riset_13_s2_hemat.py"}
simpan_argv, sys.argv = sys.argv, [sys.argv[0]]
exec(compile(kode, "riset_13_bagian", "exec"), g)
sys.argv = simpan_argv
akhir_bulan, pilih, lolos, ret_pegang, biaya_rt = (g[k] for k in ["akhir_bulan", "pilih", "lolos", "ret_pegang", "biaya_rt"])
MIN_KELOMPOK = 5


def nilai_t(s):
    s = pd.Series(s).dropna()
    return s.mean() / (s.std(ddof=1) / np.sqrt(len(s))) if len(s) > 2 else np.nan


# ===== Kalender ex-dividen: set (kode, tahun, bulan) =====
aksi = pd.read_parquet("data/raw/aksi_idx/semua.parquet")
aksi = aksi[aksi["dividen"] > 0]
ex = set(zip(aksi["kode"], aksi["tanggal"].dt.year, aksi["tanggal"].dt.month))
print("📅 Cakupan data dividen Yahoo (jumlah kode yang ex-dividen per tahun):")
per_th = aksi.groupby(aksi["tanggal"].dt.year)["kode"].nunique()
print("   " + "  ".join(f"{t}:{n}" for t, n in per_th.loc[2003:2018].items()))

if TES_TIRUAN or TES_KOSONG:
    acak = np.random.default_rng(22)
    ret_pegang = pd.DataFrame(acak.normal(0.01, 0.10, ret_pegang.shape), index=ret_pegang.index,
                              columns=ret_pegang.columns).where(ret_pegang.notna())
    print(f"🧪 MODE TES: return PALSU {'(+2%/bln untuk kelompok dividen)' if TES_TIRUAN else 'tanpa pola'}")

hasil, w_lama = [], pd.Series(dtype=float)
for i in np.where(pilih)[0]:
    t = akhir_bulan[i]                          # akhir bulan m-1; bulan pegang m = bulan berikutnya
    m = (t + pd.offsets.MonthBegin(1))
    ok = lolos.loc[i] & ret_pegang.loc[i].notna()
    semesta = list(ok.index[ok])
    if len(semesta) < g["g"]["MIN_SAHAM"]:
        continue
    kel = [k for k in semesta if (k, m.year - 1, m.month) in ex]
    r = ret_pegang.loc[i, semesta].copy()
    if TES_TIRUAN:
        r[kel] += 0.02
    baris = {"t": m, "n_kel": len(kel), "n_semesta": len(semesta)}
    if len(kel) >= MIN_KELOMPOK:
        w = pd.Series(1 / len(kel), index=sorted(kel))
    else:
        w = pd.Series(dtype=float)              # tidak ada posisi bulan ini (uang di semesta = selisih 0, tanpa biaya)
    semua = w.index.union(w_lama.index)
    dw = (w.reindex(semua, fill_value=0) - w_lama.reindex(semua, fill_value=0)).abs()
    biaya = (dw * biaya_rt(i, list(semua)) / 2).sum() if len(semua) else 0.0
    if len(kel) >= MIN_KELOMPOK:
        baris["kotor"] = r[kel].mean() - r.mean()
        baris["bersih"] = baris["kotor"] - biaya
    elif biaya > 0:
        baris["bersih"] = -biaya                # bulan keluar dari kelompok: biaya jual tetap dibayar
    w_lama = w
    hasil.append(baris)
h = pd.DataFrame(hasil).set_index("t")
aktif = h.dropna(subset=["kotor"])
print(f"\n📊 DATA LATIH (data uji TIDAK disentuh): {len(aktif)} bulan aktif dari {len(h)} "
      f"({aktif.index.min():%Y-%m} s/d {aktif.index.max():%Y-%m}), median kelompok {aktif['n_kel'].median():.0f} saham")
print(f"   U1 kelompok dividen - semesta (kotor): {aktif['kotor'].mean():+.2%}/bln  t {nilai_t(aktif['kotor']):+.1f}")
u2 = h["bersih"].dropna()                   # bulan aktif + bulan keluar (biaya jual)
print(f"   U2 BERSIH realistis (penentu)        : {u2.mean():+.2%}/bln  t {nilai_t(u2):+.1f} ({len(u2)} bulan dengan posisi/biaya)")
tengah = aktif.index[len(aktif) // 2]
print(f"   paruh: {nilai_t(aktif.loc[:tengah, 'kotor']):+.1f} / {nilai_t(aktif.loc[tengah:, 'kotor'].iloc[1:]):+.1f}")
print("   per bulan kalender (kotor, rata-rata | jumlah bulan | median saham):")
for bl, s in aktif.groupby(aktif.index.month):
    print(f"     {bl:2d}: {s['kotor'].mean():+.2%} | {len(s):2d} | {s['n_kel'].median():.0f}")
t_u2 = nilai_t(u2)
print(f"\n   KEPUTUSAN (t bersih realistis > 3): {t_u2:+.1f} -> "
      f"{'✅ kandidat KOMPONEN model gabungan' if t_u2 > 3 else '❌ tidak dipakai'}")
