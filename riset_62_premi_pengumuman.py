"""
RISET #62: PREMI BULAN PENGUMUMAN LABA (Frazzini-Lamont 2007; Barber-De George-Lehavy-Trueman 2013) -> saham IDX, data LATIH
Pra-registrasi: docs/prareg_62_premi_pengumuman.md (di-commit SEBELUM return dilihat).
Diramal mengumumkan di bulan T = punya pengumuman laba di bulan kalender T-12 (jadwal IDX tetap, #58). Banding = saham terliput lain.
U1 IC selisih return (|t| > 3) | U2 beli-saja bersih biaya B - semesta (t > +3). Kerangka #13. Data uji 2019+ DIKUNCI.
Uji kode: --tes-tiruan (+2% bagi diramal) / --tes-kosong / --potong-data (IDENTIK).
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
MIN_N = 5

if POTONG:
    _baca = pd.read_parquet

    def _terpotong(*a, **k):
        d = _baca(*a, **k)
        if isinstance(d.index, pd.DatetimeIndex):
            d = d[d.index <= BATAS]
        for c in ("tanggal", "Date", "waktu_wib"):
            if c in d.columns and pd.api.types.is_datetime64_any_dtype(d[c]):
                x = d[c].dt.tz_localize(None) if d[c].dt.tz is not None else d[c]
                d = d[x <= BATAS]
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
tgl_jual = pd.Series(gg["awal_bulan"]).shift(-2).reset_index(drop=True)
if POTONG:
    print(f"   (cek potong: harga terakhir {gg['adj'].index.max():%Y-%m-%d})")
tick = tabel_tick_historis(gg["tutup"], pd.read_parquet("data/raw/aksi_idx/semua.parquet"))
biaya_rt = (0.004 + 1.2 * tick.loc[akhir_bulan]).reset_index(drop=True)

ev = pd.read_parquet("data/raw/laba_idx/semua.parquet")
ev = ev[ev["eps_aktual"].notna()].copy()
w = pd.to_datetime(ev["waktu_wib"])
ev["tgl"] = (w.dt.tz_localize(None) if w.dt.tz is not None else w).dt.normalize()
ev = ev.drop_duplicates(["kode", "tgl"])
ev["bln"] = ev["tgl"].dt.to_period("M")
per_bln = ev.groupby("bln")["kode"].apply(set).to_dict()          # bulan kalender -> saham yang mengumumkan


def kelompok(i):
    t = pd.Timestamp(akhir_bulan[i])
    T = (t + pd.offsets.MonthBegin(1)).to_period("M")
    lalu = ev[(ev["tgl"] <= t) & (ev["bln"] >= T - 24)]
    terliput = set(lalu["kode"])
    ok = lolos.loc[i] & ret_pegang.loc[i].notna()
    sem = set(ok.index[ok])
    ramal = (per_bln.get(T - 12, set()) & terliput & sem)
    lain = (terliput & sem) - ramal
    return T, sorted(ramal), sorted(lain), sem


if TES_TIRUAN or TES_KOSONG:
    acak = np.random.default_rng(62)
    palsu = pd.DataFrame(acak.normal(0.01, 0.10, ret_pegang.shape), index=ret_pegang.index, columns=ret_pegang.columns)
    if TES_TIRUAN:
        for i in range(len(palsu)):
            _, ramal, _, _ = kelompok(i)
            palsu.loc[i, ramal] += 0.02
    ret_pegang = palsu.where(ret_pegang.notna())
    print(f"🧪 MODE TES: return bulan depan PALSU {'+ 2% bagi diramal-mengumumkan' if TES_TIRUAN else 'tanpa pola'}")

baris, w_lama = [], pd.Series(dtype=float)
for i, t in enumerate(akhir_bulan):
    if pd.isna(tgl_jual.iloc[i]) or tgl_jual.iloc[i] > BATAS:
        continue
    T, ramal, lain, sem = kelompok(i)
    if len(ramal) < MIN_N or len(lain) < MIN_N:
        w_lama = pd.Series(dtype=float)              # bulan tak dipakai: posisi dianggap ditutup (biaya masuk ulang dihitung)
        continue
    rr = ret_pegang.loc[i]
    wb = pd.Series(1 / len(ramal), index=ramal)
    semua = wb.index.union(w_lama.index)
    dw = (wb.reindex(semua, fill_value=0) - w_lama.reindex(semua, fill_value=0)).abs()
    biaya = (dw * biaya_rt.loc[i].reindex(semua).fillna(0.012) / 2).sum()
    tepat = len(set(ramal) & per_bln.get(T, set())) / len(ramal) if T.end_time <= BATAS else np.nan
    baris.append({"t": t, "T": T, "n_ramal": len(ramal), "n_lain": len(lain), "u1": rr[ramal].mean() - rr[lain].mean(),
                  "bersih": rr[ramal].mean() - biaya - rr[list(sem)].mean(), "biaya": biaya, "tepat": tepat})
    w_lama = wb
d = pd.DataFrame(baris).set_index("t")
print("🔒 Data uji (2019+) DIKUNCI.\n")
p = len(d) // 2
musim = d["T"].map(lambda x: "Mar-Apr" if x.month in (3, 4) else "Jul-Agu" if x.month in (7, 8) else "Okt-Nov" if x.month in (10, 11) else "lain")
print(f"   {len(d)} bulan ({d.index.min():%Y-%m} s/d {d.index.max():%Y-%m}); median diramal {d['n_ramal'].median():.0f}, banding {d['n_lain'].median():.0f}; "
      f"ketepatan ramalan {d['tepat'].mean():.0%}")
print(f"   U1 diramal − terliput lain : {d['u1'].mean():+.3%}/bln  t {nilai_t(d['u1']):+.2f}  (paruh {nilai_t(d['u1'].iloc[:p]):+.1f}/{nilai_t(d['u1'].iloc[p:]):+.1f})")
print("      per musim: " + " | ".join(f"{k} {v.mean():+.2%} (n {len(v)}, t {nilai_t(v):+.1f})" for k, v in d['u1'].groupby(musim)))
print(f"   U2 beli diramal, BERSIH − semesta: {d['bersih'].mean():+.3%}/bln  t {nilai_t(d['bersih']):+.2f}  (biaya {d['biaya'].mean():.3%}/bln)")
hasil = {"U1": nilai_t(d["u1"]), "U2": nilai_t(d["bersih"])}
lolos_ = [k for k, v in hasil.items() if (abs(v) > 3 if k == "U1" else v > 3)]
print(f"\n   KEPUTUSAN #62: {'✅ ' + ', '.join(lolos_) if lolos_ else '❌ tidak ada yang lolos'}")
