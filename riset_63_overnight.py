"""
RISET #63: "TARIK-MENARIK" OVERNIGHT vs SIANG (Lou-Polk-Skouras 2019 JFE) -> saham IDX bulan depan, data LATIH
Pra-registrasi: docs/prareg_63_overnight.md (di-commit SEBELUM hubungan sinyal-return dihitung).
ON12 = jumlah log return overnight (Open disesuaikan dividen / Adj kemarin) 12 bulan s/d akhir bulan m (>= 150 hari sah).
U1 IC(ON12, r) | U2 Fama-MacBeth ON12 + S1 + S2 | U3 beli 20% teratas bersih biaya B - semesta (t > +3). Kerangka #13.
Uji kode: --tes-tiruan (+2% x z(ON12)) / --tes-kosong / --potong-data (IDENTIK). Data uji 2019+ DIKUNCI.
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
MIN_HARI, BATAS_LOMPAT = 150, 0.35

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


def jadi_tanggal(x):
    t = pd.DatetimeIndex(pd.to_datetime(x))
    return (t.tz_localize(None) if t.tz is not None else t).normalize().astype("datetime64[ns]")


kode13 = Path("riset_13_s2_hemat.py").read_text(encoding="utf-8").split("def simulasi(varian):")[0]
g = {"__file__": "riset_13_s2_hemat.py"}
simpan, sys.argv = sys.argv, [sys.argv[0]]
with contextlib.redirect_stdout(io.StringIO()):
    exec(compile(kode13, "riset_13_bagian", "exec"), g)
sys.argv = simpan
gg = g["g"]
akhir_bulan, lolos, ret_pegang, sinyal = g["akhir_bulan"], g["lolos"], g["ret_pegang"].copy(), g["sinyal"]
adj, tutup = gg["adj"], gg["tutup"]
tgl_jual = pd.Series(gg["awal_bulan"]).shift(-2).reset_index(drop=True)
if POTONG:
    print(f"   (cek potong: harga terakhir {adj.index.max():%Y-%m-%d})")
tick = tabel_tick_historis(tutup, pd.read_parquet("data/raw/aksi_idx/semua.parquet"))
biaya_rt = (0.004 + 1.2 * tick.loc[akhir_bulan]).reset_index(drop=True)

# ---- harga buka (Open) & volume, diselaraskan dgn adj yang sudah dibersihkan
buka, vol = {}, {}
for f in sorted(Path("data/raw/harga_idx").glob("*.parquet")):
    d = pd.read_parquet(f, columns=["Open", "Volume"])
    d.index = jadi_tanggal(d.index)
    d = d[~d.index.duplicated(keep="last")]
    buka[f.stem], vol[f.stem] = d["Open"], d["Volume"]
buka = pd.DataFrame(buka).reindex(index=adj.index, columns=adj.columns)
vol = pd.DataFrame(vol).reindex(index=adj.index, columns=adj.columns)
faktor = adj / tutup                                           # faktor penyesuaian dividen (& split) per hari
buka_adj = (buka * faktor).where((vol.fillna(0) > 0) & (buka > 0))
ov = buka_adj / adj.shift(1) - 1
siang = adj / buka_adj - 1
ov = ov.where(ov.abs() <= BATAS_LOMPAT)
siang = siang.where(ov.notna() & (siang.abs() <= BATAS_LOMPAT))
nol = float((ov == 0).sum().sum() / ov.notna().sum().sum())
lov, lsi = np.log1p(ov), np.log1p(siang)
ak = pd.DatetimeIndex(akhir_bulan)
kum_ov, kum_si, kum_n = (x.fillna(0).cumsum().reindex(ak, method="ffill").reset_index(drop=True) for x in (lov, lsi, lov.notna().astype(float)))
n12 = kum_n - kum_n.shift(12)
ON12 = (kum_ov - kum_ov.shift(12)).where(n12 >= MIN_HARI)
SI12 = (kum_si - kum_si.shift(12)).where(n12 >= MIN_HARI)
ON12.index = SI12.index = ret_pegang.index
S1, S2 = sinyal["S1"], sinyal["S2"]

if TES_TIRUAN or TES_KOSONG:
    acak = np.random.default_rng(63)
    palsu = pd.DataFrame(acak.normal(0.01, 0.10, ret_pegang.shape), index=ret_pegang.index, columns=ret_pegang.columns)
    if TES_TIRUAN:
        for i in range(len(palsu)):
            x = ON12.loc[i][lolos.loc[i]].dropna()
            if len(x) > 10:
                palsu.loc[i, x.index] += 0.02 * (x - x.mean()) / x.std()
    ret_pegang = palsu.where(ret_pegang.notna())
    print(f"🧪 MODE TES: return bulan depan PALSU {'+ 2% x z(ON12)' if TES_TIRUAN else 'tanpa pola'}")

baris, w_lama = [], pd.Series(dtype=float)
for i, t in enumerate(akhir_bulan):
    if pd.isna(tgl_jual.iloc[i]) or tgl_jual.iloc[i] > BATAS:
        continue
    ok = lolos.loc[i] & ret_pegang.loc[i].notna() & ON12.loc[i].notna() & S1.loc[i].notna() & S2.loc[i].notna()
    if ok.sum() < gg["MIN_SAHAM"]:
        continue
    on, rr, s1, s2, si = ON12.loc[i][ok], ret_pegang.loc[i][ok], S1.loc[i][ok], S2.loc[i][ok], SI12.loc[i][ok]
    rk = lambda x: x.rank(pct=True) - 0.5
    X = np.column_stack([np.ones(len(on)), rk(on), rk(s1), rk(s2)])
    b = np.linalg.lstsq(X, rk(rr).values, rcond=None)[0]
    pilih = sorted(on.index[on.rank(pct=True) > 0.8])
    w = pd.Series(1 / len(pilih), index=pilih)
    semua = w.index.union(w_lama.index)
    dw = (w.reindex(semua, fill_value=0) - w_lama.reindex(semua, fill_value=0)).abs()
    biaya = (dw * biaya_rt.loc[i].reindex(semua).fillna(0.012) / 2).sum()
    baris.append({"t": t, "n": int(ok.sum()), "ic": on.rank().corr(rr.rank()), "b_on": b[1], "ic_si": si.rank().corr(rr.rank()),
                  "kor_s1": on.rank().corr(s1.rank()), "bersih": rr[pilih].mean() - biaya - rr.mean(), "biaya": biaya})
    w_lama = w
d = pd.DataFrame(baris).set_index("t")
print("🔒 Data uji (2019+) DIKUNCI.\n")
p = len(d) // 2
print(f"   {len(d)} bulan ({d.index.min():%Y-%m} s/d {d.index.max():%Y-%m}), semesta median {d['n'].median():.0f}; "
      f"porsi hari aktif dgn overnight tepat 0: {nol:.0%}; korelasi peringkat ON12–S1 {d['kor_s1'].mean():+.2f}")
print(f"   U1 IC(ON12, r)               : {d['ic'].mean():+.4f}  t {nilai_t(d['ic']):+.2f}  (paruh {nilai_t(d['ic'].iloc[:p]):+.1f}/{nilai_t(d['ic'].iloc[p:]):+.1f})")
print(f"   U2 Fama-MacBeth ON12 | S1,S2 : {d['b_on'].mean():+.4f}  t {nilai_t(d['b_on']):+.2f}")
print(f"   U3 20% teratas BERSIH − sem. : {d['bersih'].mean():+.3%}/bln  t {nilai_t(d['bersih']):+.2f}  (biaya {d['biaya'].mean():.3%})")
print(f"   info IC(siang 12 bln, r)     : {d['ic_si'].mean():+.4f}  t {nilai_t(d['ic_si']):+.2f}")
hasil = {"U1": nilai_t(d["ic"]), "U2": nilai_t(d["b_on"]), "U3": nilai_t(d["bersih"])}
lolos_ = [k for k, v in hasil.items() if (abs(v) > 3 if k != "U3" else v > 3)]
print(f"\n   KEPUTUSAN #63: {'✅ ' + ', '.join(lolos_) if lolos_ else '❌ tidak ada yang lolos'}")
