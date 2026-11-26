"""
RISET #57: 'FROG-IN-THE-PAN' (Da, Gurun & Warachka 2014, RFS) -> momentum IDX dari kenaikan KECIL TERUS-MENERUS lebih awet, data LATIH saja
================================================================================================================================
DUGAAN (ditulis 27 Nov 2026 SEBELUM ukuran kontinuitas dihitung pada data IDX; di-commit sebelum dijalankan)
Investor kurang memperhatikan informasi yang datang SEDIKIT DEMI SEDIKIT (perhatian terbatas; katak dalam panci yang dipanaskan pelan)
dibanding lompatan besar yang mencolok. Akibatnya momentum yang terbentuk dari banyak gerak kecil searah ('kontinu') berlanjut lebih kuat;
momentum dari beberapa lompatan besar ('diskret') cepat habis. DGW 2014 (AS 1927-2007): momentum kontinu ~5,9%/6 bln vs diskret ~-2,1%;
replikasi internasional (mis. Pan dkk. Pacific-Basin) umumnya searah. IDX: S1 momentum 12-1 IC t 4,0 (#2, data bersih), lotre/ARA umum
-> pasar ritel yang gemar lompatan; dugaan arah SAMA. Bantahan: biaya IDX & long-only (#36-#50: alpha kotor ~ biaya). Perkiraan jujur:
IC kontinuitas di antara saham pemenang searah (t 1-3), strategi beli-saja bersih t < 2.

UKURAN (akhir bulan m, jendela pembentukan SAMA dgn S1: hari bursa sesudah akhir bulan m-12 s/d akhir bulan m-1):
  PRET = S1 (harga akhir m-1 / akhir m-12 - 1);  ID = tanda(PRET) x (%hari return < 0 - %hari return > 0)   [hari return 0 tidak dihitung]
  ID kecil (negatif) = kontinu; ID besar = diskret. Butuh >= 150 hari return sah.
SEMESTA, kalender, biaya: kerangka #13 (semesta #2, sinyal akhir bulan, beli tutup hari bursa pertama m+1, tahan 1 bulan; biaya B = 0,4% +
  1,2 x tick historis/harga asli per bolak-balik x perubahan bobot / 2).
UJI (2; |t| > 3):
  U1 IC di antara PEMENANG (S1 40% teratas semesta): korelasi peringkat(-ID, return bulan depan), rata-rata per bulan, t biasa. Dugaan +.
  U2 (penentu strategi) FIP = pemenang dgn ID <= median pemenang (~20% semesta, bobot sama); BERSIH biaya B - semesta (tanpa biaya), t biasa.
Info: momentum biasa 20% teratas bersih - semesta (patokan #2); FIP - momentum biasa; paruh waktu; IC -ID di seluruh semesta.
Data uji 2019+ DIKUNCI. Uji kode: --tes-tiruan (return bulan depan palsu + 2% x z(-ID) bagi pemenang) & --tes-kosong; --potong-data -> IDENTIK.
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
MIN_HARI = 150

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
akhir_bulan, lolos, ret_pegang, sinyal = g["akhir_bulan"], g["lolos"], g["ret_pegang"].copy(), g["sinyal"]
awal_bulan = pd.DatetimeIndex(gg["awal_bulan"])
adj = gg["adj"]
tgl_jual = pd.Series(awal_bulan).shift(-2).reset_index(drop=True)
if POTONG:
    print(f"   (cek potong: harga terakhir {adj.index.max():%Y-%m-%d})")
tick = tabel_tick_historis(gg["tutup"], pd.read_parquet("data/raw/aksi_idx/semua.parquet"))
biaya_rt = (0.004 + 1.2 * tick.loc[akhir_bulan]).reset_index(drop=True)
S1 = sinyal["S1"]

# ---- ID: hitung kumulatif hari naik/turun/sah, ambil di akhir bulan
r = adj.pct_change(fill_method=None)
naik, turun, sah = (r > 0).astype(float).cumsum(), (r < 0).astype(float).cumsum(), r.notna().astype(float).cumsum()
ak = pd.DatetimeIndex(akhir_bulan)
N, T, V = (x.reindex(ak, method="ffill").reset_index(drop=True) for x in (naik, turun, sah))
dn, dt, dv = N.shift(1) - N.shift(12), T.shift(1) - T.shift(12), V.shift(1) - V.shift(12)   # jendela akhir m-12 .. akhir m-1
ID = (np.sign(S1) * (dt - dn) / dv).where(dv >= MIN_HARI)

if TES_TIRUAN or TES_KOSONG:
    acak = np.random.default_rng(57)
    palsu = pd.DataFrame(acak.normal(0.01, 0.10, ret_pegang.shape), index=ret_pegang.index, columns=ret_pegang.columns)
    if TES_TIRUAN:
        for i in range(len(palsu)):
            ok = lolos.loc[i] & S1.loc[i].notna() & ID.loc[i].notna()
            if ok.sum() < 20:
                continue
            s1, idv = S1.loc[i][ok], ID.loc[i][ok]
            menang = s1.rank(pct=True) > 0.6
            z = -(idv - idv[menang].mean()) / idv[menang].std()
            palsu.loc[i, z.index[menang]] += 0.02 * z[menang]
    ret_pegang = palsu.where(ret_pegang.notna())
    print(f"🧪 MODE TES: return bulan depan PALSU {'+ 2% x z(-ID) bagi pemenang' if TES_TIRUAN else 'tanpa pola'}")

baris, w_lama = [], {"F": pd.Series(dtype=float), "M": pd.Series(dtype=float)}
for i, t in enumerate(akhir_bulan):
    if pd.isna(tgl_jual.iloc[i]) or tgl_jual.iloc[i] > BATAS:
        continue
    ok = lolos.loc[i] & ret_pegang.loc[i].notna() & S1.loc[i].notna() & ID.loc[i].notna()
    if ok.sum() < gg["MIN_SAHAM"]:
        continue
    s1, idv, rr = S1.loc[i][ok], ID.loc[i][ok], ret_pegang.loc[i][ok]
    pr = s1.rank(pct=True)
    menang = pr.index[pr > 0.6]
    fip = sorted(idv[menang][idv[menang] <= idv[menang].median()].index)
    mom = sorted(pr.index[pr > 0.8])
    br = biaya_rt.loc[i]
    h = {"t": t, "n": int(ok.sum()), "U": rr.mean(),
         "ic_menang": (-idv[menang]).rank().corr(rr[menang].rank()), "ic_semua": (-idv).rank().corr(rr.rank())}
    for k, pilih in [("F", fip), ("M", mom)]:
        w = pd.Series(1 / len(pilih), index=pilih)
        semua = w.index.union(w_lama[k].index)
        dw = (w.reindex(semua, fill_value=0) - w_lama[k].reindex(semua, fill_value=0)).abs()
        h[f"{k}_kotor"] = rr.reindex(pilih).mean()
        h[f"{k}_biaya"] = (dw * br.reindex(semua).fillna(0.012) / 2).sum()
        h[f"{k}_bersih"] = h[f"{k}_kotor"] - h[f"{k}_biaya"] - h["U"]
        h[f"{k}_n"] = len(pilih)
        w_lama[k] = w
    baris.append(h)
d = pd.DataFrame(baris).set_index("t")
print("🔒 Data uji (2019+) DIKUNCI.\n")
p = len(d) // 2
print(f"   {len(d)} bulan ({d.index.min():%Y-%m} s/d {d.index.max():%Y-%m}), semesta median {d['n'].median():.0f}, FIP {d['F_n'].median():.0f} saham, "
      f"momentum {d['M_n'].median():.0f}")
print(f"   U1 IC(-ID, r) di antara pemenang : {d['ic_menang'].mean():+.4f}  t {nilai_t(d['ic_menang']):+.2f}  "
      f"(paruh {nilai_t(d['ic_menang'].iloc[:p]):+.1f}/{nilai_t(d['ic_menang'].iloc[p:]):+.1f})")
print(f"   U2 FIP bersih - semesta          : {d['F_bersih'].mean():+.3%}/bln  t {nilai_t(d['F_bersih']):+.2f}  "
      f"(kotor {d['F_kotor'].mean() - d['U'].mean():+.3%}, biaya {d['F_biaya'].mean():.3%}; paruh {nilai_t(d['F_bersih'].iloc[:p]):+.1f}/{nilai_t(d['F_bersih'].iloc[p:]):+.1f})")
print(f"   info momentum biasa bersih - sem.: {d['M_bersih'].mean():+.3%}/bln  t {nilai_t(d['M_bersih']):+.2f}  (biaya {d['M_biaya'].mean():.3%})")
print(f"   info FIP - momentum biasa        : {(d['F_bersih'] - d['M_bersih']).mean():+.3%}/bln  t {nilai_t(d['F_bersih'] - d['M_bersih']):+.2f}")
print(f"   info IC(-ID, r) seluruh semesta  : {d['ic_semua'].mean():+.4f}  t {nilai_t(d['ic_semua']):+.2f}")
hasil = {"U1": nilai_t(d["ic_menang"]), "U2": nilai_t(d["F_bersih"])}
lolos_ = [k for k, v in hasil.items() if abs(v) > 3]
print(f"\n   KEPUTUSAN #57 (|t| > 3): {'✅ ' + ', '.join(lolos_) if lolos_ else '❌ tidak ada yang lolos'}")
