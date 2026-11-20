"""
RISET #13: S2 YANG LEBIH HEMAT BIAYA (dirancang & dinilai HANYA di data latih 2005-2018)
=====================================================================================

LATAR: S2 lolos data uji (#12b) tapi biaya nyata ~0,62%/bln (#12c, spread Corwin-Schultz) menurunkan t ke ~2,5.
Biaya datang dari PERPUTARAN: ~49% saham diganti tiap bulan.
DUGAAN (ditulis 2026-11-20, sebelum menghitung varian apa pun): mengurangi perputaran menurunkan biaya lebih banyak
daripada keuntungan yang hilang, karena sinyal S2 bergerak pelan (saham dekat puncak cenderung tetap dekat puncak).

VARIAN (hanya 2, ditetapkan sekarang):
  V0 patokan: beli 20% teratas tiap bulan (= S2 asli).
  V1 PENYANGGA: saham MASUK kalau di 20% teratas; yang sudah dipegang baru DIJUAL kalau keluar dari 40% teratas
     (atau keluar dari semesta). Bobot sama.
  V2 TAHAN 3 BULAN: tiap bulan 1/3 modal membeli 20% teratas bulan itu dan ditahan 3 bulan (3 kelompok bertumpuk).
DATA UJI 2019+ TIDAK BOLEH dipakai: data uji S2 sudah terpakai di #12b; menilai varian di sana = curang.
UKURAN UTAMA: selisih BERSIH REALISTIS vs semesta (biaya per saham = 0,4% + max(spread CS, tick/harga), dibayar
  separuh saat beli & separuh saat jual sesuai perubahan bobot).
KEPUTUSAN (ditetapkan sekarang): varian dengan t bersih realistis tertinggi menjadi PAPER TRADING KEDUA hanya kalau
  rata-rata bersihnya >= V0 DAN t-nya > V0. Kalau tidak ada, S2 asli tetap satu-satunya.
CEK KODE: V0 di simulator ini harus mendekati hasil #12c (latih: bersih realistis +0,87%/bln, t 2,5).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.argv = [sys.argv[0]]                     # mode data latih
g = {}
kode = Path("riset_12_gabung_sinyal.py").read_text(encoding="utf-8").split("baris, korelasi, lalu = [], [], {}")[0]
exec(compile(kode, "riset_12_bagian", "exec"), g)
from paper_trading import corwin_schultz, tick   # rumus yang sama dengan #12c & paper trading

KOMISI = 0.004
adj, tutup, hari, aktif = g["adj"], g["tutup"], g["hari"], g["aktif"]
tinggi, rendah = {}, {}
for f in sorted(Path("data/raw/harga_idx").glob("*.parquet")):
    d = pd.read_parquet(f, columns=["High", "Low"])
    d.index = g["jadi_tanggal"](d.index)
    d = d[~d.index.duplicated(keep="last")]
    tinggi[f.stem], rendah[f.stem] = d["High"], d["Low"]
tinggi = pd.DataFrame(tinggi).reindex(index=hari, columns=adj.columns)
rendah = pd.DataFrame(rendah).reindex(index=hari, columns=adj.columns)
sah = (tinggi > 0) & (rendah > 0) & (tinggi >= rendah) & aktif
cs = corwin_schultz(tinggi.where(sah), rendah.where(sah)).rolling(21, min_periods=10).mean()

akhir_bulan, pilih, lolos, sinyal, ret_pegang = g["akhir_bulan"], g["pilih"], g["lolos"], g["sinyal"], g["ret_pegang"]


def biaya_rt(i, nama):
    """Biaya bolak-balik per saham pada akhir bulan i."""
    t = akhir_bulan[i]
    harga = tutup.loc[t, nama]
    tk = pd.Series(tick(harga.values) / harga.values, index=nama)
    return (KOMISI + np.maximum(cs.loc[t, nama].fillna(tk), tk)).fillna(KOMISI + 0.01)


def simulasi(varian):
    baris, w_lama, kelompok = [], pd.Series(dtype=float), []
    for i in np.where(pilih)[0]:
        ok = lolos.loc[i] & ret_pegang.loc[i].notna()
        for k in sinyal:
            ok &= sinyal[k].loc[i].notna()
        if ok.sum() < g["MIN_SAHAM"]:
            continue
        s = sinyal["S2"].loc[i][ok]
        pct = s.rank(pct=True)
        atas = set(s.index[pd.qcut(s.rank(method="first"), 5, labels=False) == 4])
        if varian == "V0":
            pegang = atas
            w = pd.Series(1 / len(pegang), index=sorted(pegang))
        elif varian == "V1":
            tetap = {k for k in w_lama.index if k in pct.index and pct[k] > 0.60}
            pegang = atas | tetap
            w = pd.Series(1 / len(pegang), index=sorted(pegang))
        else:  # V2: 3 kelompok bertumpuk, masing-masing 1/3 modal
            kelompok = (kelompok + [sorted(atas)])[-3:]
            w = pd.concat([pd.Series(1 / len(kel) / len(kelompok), index=kel) for kel in kelompok])
            w = w.groupby(level=0).sum()
        r = ret_pegang.loc[i]
        r_w = r.reindex(w.index)
        ada = r_w.notna()
        w_ef = w[ada] / w[ada].sum()                    # saham tanpa harga bulan depan dibuang (sama dengan riset)
        semua = w.index.union(w_lama.index)
        dw = (w.reindex(semua, fill_value=0) - w_lama.reindex(semua, fill_value=0)).abs()
        biaya = (dw * biaya_rt(i, list(semua)) / 2).sum()
        bench = r[ok].mean()
        baris.append({"tanggal": akhir_bulan[i], "kotor": (w_ef * r_w[ada]).sum() - bench, "biaya": biaya,
                      "putar": dw.sum() / 2, "n": len(w)})
        w_lama = w
    d = pd.DataFrame(baris).set_index("tanggal")
    d["bersih"] = d["kotor"] - d["biaya"]
    return d


def nilai_t(s):
    s = pd.Series(s).dropna()
    return s.mean() / (s.std(ddof=1) / np.sqrt(len(s)))


print("\n📊 DATA LATIH 2005-2018 (data uji TIDAK disentuh)")
print(f"   {'varian':28}{'saham':>7}{'putar/bln':>11}{'biaya/bln':>11}{'kotor':>9}{'BERSIH':>9}{'t':>7}{'paruh1 t':>10}{'paruh2 t':>10}")
hasil = {}
for v, nama in [("V0", "V0 patokan (S2 asli)"), ("V1", "V1 penyangga 20%->40%"), ("V2", "V2 tahan 3 bulan")]:
    d = simulasi(v)
    hasil[v] = d
    t2 = d.index[len(d) // 2]
    print(f"   {nama:28}{d['n'].median():>7.0f}{d['putar'].iloc[1:].mean():>11.0%}{d['biaya'].iloc[1:].mean():>11.2%}"
          f"{d['kotor'].mean():>+9.2%}{d['bersih'].mean():>+9.2%}{nilai_t(d['bersih']):>+7.1f}"
          f"{nilai_t(d['bersih'].loc[:t2]):>+10.1f}{nilai_t(d['bersih'].loc[t2:].iloc[1:]):>+10.1f}")
v0 = hasil["V0"]["bersih"]
calon = max(["V1", "V2"], key=lambda v: nilai_t(hasil[v]["bersih"]))
b = hasil[calon]["bersih"]
lolos_kep = b.mean() >= v0.mean() and nilai_t(b) > nilai_t(v0)
print(f"\n   KEPUTUSAN (aturan ditetapkan di depan): calon terbaik {calon} -> "
      f"{'✅ jadi PAPER TRADING KEDUA' if lolos_kep else '❌ tidak lebih baik dari S2 asli'}")
print(f"   Cek kode: V0 di sini {v0.mean():+.2%}/bln t {nilai_t(v0):+.1f} (riset #12c: +0,87%/bln t +2,5)")
