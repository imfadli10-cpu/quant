"""
RISET #59: LEAD-LAG DALAM SEKTOR (Hou 2007 RFS) -> return saham PEMIMPIN sektor bulan ini memprediksi saham PENGIKUT bulan depan, data LATIH
==========================================================================================================================
DUGAAN (ditulis 27 Nov 2026 SEBELUM hubungan pemimpin-pengikut dihitung; di-commit sebelum dijalankan)
Informasi tingkat industri masuk lebih dulu ke saham besar & likuid (diliput analis, dipegang institusi), lalu MENYEBAR LAMBAT ke saham kecil
di industri yang sama (Hou 2007: efek lead-lag terutama DALAM industri; Hong-Torous-Valkanov 2007; Cohen-Frazzini 2008 utk rantai pasok).
Di IDX: ritel dominan & liputan analis sempit (~140 saham) -> penyebaran lambat masuk akal. Bedanya dgn #50 (momentum sektor 12-1, gagal):
ini horizon 1 BULAN & arah pemimpin -> pengikut. Bantahan: #2 menemukan return 1 bulan SENDIRI berlanjut (IC t +2,9) -> efek pemimpin bisa
hanya cermin momentum 1 bulan pengikut sendiri (dikontrol di U2); peta sektor statis (Nov 2026). Perkiraan jujur: U1 t 1-3, U2 lebih lemah.

KERANGKA #13: semesta #2 (`lolos`), sinyal akhir bulan i, beli tutup hari bursa pertama bulan berikutnya, tahan 1 bulan (`ret_pegang[i]`),
  biaya B = 0,4% + 1,2 x tick historis/harga asli. Sektor = foto fundamental Yahoo 2026-11-21 (STATIS, diakui).
RETURN BULAN INI r0[i] = harga_akhir[i] / harga_akhir[i-1] - 1 (berakhir di akhir bulan sinyal; BUKAN ret_pegang[i-1] yg melewati tanggal sinyal).
PEMIMPIN sektor (bulan i, sektor dgn >= 6 saham semesta & r0 sah): 3 saham dgn median nilai transaksi 60 hari terbesar di akhir bulan i;
  L_s = rata-rata r0 pemimpin. PENGIKUT = saham semesta lain di sektor itu (yang dinilai).
UJI (U1/U2 |t| > 3; U3 strategi t > +3 [aturan U3 diperbaiki SEBELUM data asli: --tes-kosong 'meloloskan' biaya t -4,3]):
  U1 IC peringkat(L_s, ret_pegang) di antara SEMUA pengikut (gabungan sektor), rata-rata per bulan, t biasa.             Dugaan +.
  U2 Fama-MacBeth: peringkat ret_pegang ~ peringkat L_s + peringkat r0 sendiri (pengikut); t koefisien L_s.               Dugaan +.
  U3 beli-saja: pengikut di sektor dgn L_s TERTINGGI (sepertiga sektor teratas), bobot sama, BERSIH biaya B - semesta.     Dugaan gagal.
Info: koefisien r0 sendiri di U2 (momentum 1 bulan, patokan #2), paruh waktu, jumlah sektor/pengikut.
Data uji 2019+ DIKUNCI. Uji kode: --tes-tiruan (return palsu + 0,3 x L_s utk pengikut) & --tes-kosong; --potong-data -> IDENTIK.
"""
import contextlib
import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(".").resolve()))
from biaya_idx import tabel_tick_historis

TES_TIRUAN, TES_KOSONG = "--tes-tiruan" in sys.argv, "--tes-kosong" in sys.argv
POTONG = "--potong-data" in sys.argv
BATAS = pd.Timestamp("2018-12-31")
MIN_SEKTOR, N_PEMIMPIN = 6, 3

if POTONG:
    _baca = pd.read_parquet

    def _terpotong(*a, **k):
        d = _baca(*a, **k)
        if isinstance(d.index, pd.DatetimeIndex):
            d = d[d.index <= BATAS]
        for c in ("tanggal", "Date"):
            if c in d.columns and pd.api.types.is_datetime64_any_dtype(d[c]):
                d = d[d[c] <= BATAS]
        return d
    pd.read_parquet = _terpotong


def nilai_t(s):
    s = pd.Series(s).dropna()
    return s.mean() / (s.std(ddof=1) / np.sqrt(len(s))) if len(s) > 2 else np.nan


kode13 = Path("riset_13_s2_hemat.py").read_text(encoding="utf-8").split("def simulasi(varian):")[0]
g = {"__file__": "riset_13_s2_hemat.py"}
simpan, sys.argv = sys.argv, [sys.argv[0]]
with contextlib.redirect_stdout(io.StringIO()):
    exec(compile(kode13, "riset_13_bagian", "exec"), g)
sys.argv = simpan
gg = g["g"]
akhir_bulan, lolos, ret_pegang = g["akhir_bulan"], g["lolos"], g["ret_pegang"].copy()
harga_akhir = gg["harga_akhir"]
tgl_jual = pd.Series(gg["awal_bulan"]).shift(-2).reset_index(drop=True)
if POTONG:
    print(f"   (cek potong: harga terakhir {gg['adj'].index.max():%Y-%m-%d})")
tick = tabel_tick_historis(gg["tutup"], pd.read_parquet("data/raw/aksi_idx/semua.parquet"))
biaya_rt = (0.004 + 1.2 * tick.loc[akhir_bulan]).reset_index(drop=True)
likuid = gg["median_nilai"].reindex(pd.DatetimeIndex(akhir_bulan), method="ffill").reset_index(drop=True)
r0 = (harga_akhir / harga_akhir.shift(1) - 1).reset_index(drop=True) if not isinstance(harga_akhir.index, pd.RangeIndex) else harga_akhir / harga_akhir.shift(1) - 1
r0.index = ret_pegang.index

info = pd.read_parquet("data/raw/fundamental_idx/info/2026-11-21.parquet")
sektor = info.assign(kode=info["kode"].str.replace(".JK", "", regex=False)).set_index("kode")["sector"].dropna()
sektor = sektor.reindex(ret_pegang.columns)


def pemimpin_pengikut(i):
    ok = lolos.loc[i] & ret_pegang.loc[i].notna() & r0.loc[i].notna() & sektor.notna() & likuid.loc[i].notna()
    kode = ok.index[ok]
    L, ikut = {}, []
    for s, b in pd.Series(sektor[kode].values, index=kode).groupby(sektor[kode].values):
        if len(b) < MIN_SEKTOR:
            continue
        pimp = likuid.loc[i, b.index].sort_values(ascending=False).index[:N_PEMIMPIN]
        L[s] = r0.loc[i, pimp].mean()
        ikut += [k for k in b.index if k not in pimp]
    return ok, L, ikut


if TES_TIRUAN or TES_KOSONG:
    acak = np.random.default_rng(59)
    palsu = pd.DataFrame(acak.normal(0.01, 0.10, ret_pegang.shape), index=ret_pegang.index, columns=ret_pegang.columns)
    if TES_TIRUAN:
        for i in range(len(palsu)):
            _, L, ikut = pemimpin_pengikut(i)
            for k in ikut:
                palsu.loc[i, k] += 0.3 * L[sektor[k]]
    ret_pegang = palsu.where(ret_pegang.notna())
    print(f"🧪 MODE TES: return bulan depan PALSU {'+ 0,3 x L_s utk pengikut' if TES_TIRUAN else 'tanpa pola'}")

baris, w_lama = [], pd.Series(dtype=float)
for i, t in enumerate(akhir_bulan):
    if i == 0 or pd.isna(tgl_jual.iloc[i]) or tgl_jual.iloc[i] > BATAS:
        continue
    ok, L, ikut = pemimpin_pengikut(i)
    if len(L) < 3 or len(ikut) < 20:
        continue
    rr = ret_pegang.loc[i]
    x = pd.Series([L[sektor[k]] for k in ikut], index=ikut)
    y, own = rr[ikut], r0.loc[i, ikut]
    ic = x.rank().corr(y.rank())
    X = np.column_stack([np.ones(len(ikut)), x.rank(pct=True) - 0.5, own.rank(pct=True) - 0.5])
    b = np.linalg.lstsq(X, (y.rank(pct=True) - 0.5).values, rcond=None)[0]
    s_atas = pd.Series(L).sort_values(ascending=False).index[:max(1, len(L) // 3)]
    pilih = sorted(k for k in ikut if sektor[k] in set(s_atas))
    w = pd.Series(1 / len(pilih), index=pilih)
    semua = w.index.union(w_lama.index)
    dw = (w.reindex(semua, fill_value=0) - w_lama.reindex(semua, fill_value=0)).abs()
    biaya = (dw * biaya_rt.loc[i].reindex(semua).fillna(0.012) / 2).sum()
    semesta = rr[ok].mean()
    baris.append({"t": t, "n_sektor": len(L), "n_ikut": len(ikut), "ic": ic, "bL": b[1], "bown": b[2],
                  "bersih": rr[pilih].mean() - biaya - semesta, "kotor": rr[pilih].mean() - semesta, "biaya": biaya, "n_pilih": len(pilih)})
    w_lama = w
d = pd.DataFrame(baris).set_index("t")
print("🔒 Data uji (2019+) DIKUNCI.\n")
p = len(d) // 2
print(f"   {len(d)} bulan ({d.index.min():%Y-%m} s/d {d.index.max():%Y-%m}); median {d['n_sektor'].median():.0f} sektor, "
      f"{d['n_ikut'].median():.0f} pengikut, beli {d['n_pilih'].median():.0f} saham")
print(f"   U1 IC(L_s, r bulan depan) pengikut : {d['ic'].mean():+.4f}  t {nilai_t(d['ic']):+.2f}  (paruh {nilai_t(d['ic'].iloc[:p]):+.1f}/{nilai_t(d['ic'].iloc[p:]):+.1f})")
print(f"   U2 Fama-MacBeth koef L_s          : {d['bL'].mean():+.4f}  t {nilai_t(d['bL']):+.2f}  | info koef r0 sendiri {d['bown'].mean():+.4f} t {nilai_t(d['bown']):+.2f}")
print(f"   U3 beli pengikut sektor teratas    : BERSIH {d['bersih'].mean():+.3%}/bln  t {nilai_t(d['bersih']):+.2f}  "
      f"(kotor {d['kotor'].mean():+.3%}, biaya {d['biaya'].mean():.3%})")
hasil = {"U1": nilai_t(d["ic"]), "U2": nilai_t(d["bL"]), "U3": nilai_t(d["bersih"])}
lolos_ = [k for k, v in hasil.items() if (abs(v) > 3 if k != "U3" else v > 3)]     # U3 strategi: hanya t > +3 (ditemukan --tes-kosong)
print(f"\n   KEPUTUSAN #59 (|t| > 3): {'✅ ' + ', '.join(lolos_) if lolos_ else '❌ tidak ada yang lolos'}")
