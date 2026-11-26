"""
RISET #52b: GABUNGAN banyak sinyal lemah "data aneh" (pra-registrasi docs/prareg_52b_gabungan.md, commit b37d712)
=================================================================================================================
Konstruksi #52 (riset_52_penyaring.py) dipakai APA ADANYA: berita z_v(t), beta keluarga A, semesta & return kerangka #13.
Skor gabungan G = rata berbobot peringkat (beta x z), bobot w_v(t) = rata IC masa lalu (hanya return yang SUDAH terealisasi, tau <= t-2,
min 24 bulan IC). SATU uji: IC G vs return bulan depan, latih (jual <= 2018-12-31), LOLOS bila t > 3.

  python riset_52b_gabungan.py [--tes-kosong | --tes-tiruan | --potong-data | --cepat | --validasi]
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

kode52 = Path("riset_52_penyaring.py").read_text(encoding="utf-8").split("pilih_periode = valid if VALIDASI else latih")[0]
exec(compile(kode52, "riset_52_bagian", "exec"))                   # -> Z, info, E, RC, L, latih, valid, fungsi, g (kerangka)

MIN_W = 24
SUSUT = 0.0 if "--tanpa-susut" in sys.argv else 4.0       # AMANDEMEN (lihat prareg 52b bagian 'Amandemen'): w = rata IC x max(0, 1 - 4/t^2)
EVAL_AWAL = pd.Timestamp("2005-01-01")
boleh = (tgl_jual <= (VAL_AKHIR if VALIDASI else BATAS)).values      # IC yang BOLEH dihitung (return tak melewati periode)
evaluasi = (valid if VALIDASI else (latih & (pd.Series(akhir_bulan) >= EVAL_AWAL).values))


def peringkat(sk, x):
    m = L & ~np.isnan(sk) & ((~np.isnan(x)) & (np.nan_to_num(x) != 0))[:, None]
    r = pd.DataFrame(np.where(m, sk, np.nan)).rank(axis=1, pct=True).to_numpy(copy=True)
    return r - 0.5


akum = {k: [np.zeros((T, N)), np.zeros((T, N))] for k in ("semua", "pit")}
jml_w = np.zeros(T)
for v in range(V):
    x = Z[:, v]
    bet = beta_bergulir(x, RC, 1)
    ic = ic_bulanan(bet, x, boleh)
    # w(t) = rata IC(tau) utk tau <= t-2
    ada = ~np.isnan(ic)
    i0 = np.nan_to_num(ic)
    cs, cn = np.concatenate([[0], np.cumsum(i0)]), np.concatenate([[0], np.cumsum(ada)])
    c2 = np.concatenate([[0], np.cumsum(i0 ** 2)])
    hi = np.clip(np.arange(T) - 1, 0, T)                           # tau < t-1  <=>  tau <= t-2
    n = cn[hi]
    with np.errstate(invalid="ignore", divide="ignore"):
        rata_ic = cs[hi] / np.maximum(n, 1)
        sb = np.sqrt(np.maximum(c2[hi] / np.maximum(n, 1) - rata_ic ** 2, 0) * n / np.maximum(n - 1, 1))
        t_lalu = rata_ic / (sb / np.sqrt(np.maximum(n, 1)))
    susut = np.clip(1 - SUSUT / np.where(np.isfinite(t_lalu), t_lalu, 0) ** 2, 0, 1) if SUSUT else 1.0   # James-Stein
    w = np.where(n >= MIN_W, rata_ic * susut, 0.0)
    w = np.nan_to_num(w)
    if not np.any(w != 0):
        continue
    rk = peringkat(bet * x[:, None], x)
    pakai = ~np.isnan(rk)
    for k in ("semua", "pit") if info.at[v, "pit"] else ("semua",):
        akum[k][0] += np.where(pakai, w[:, None] * rk, 0)
        akum[k][1] += np.where(pakai, np.abs(w)[:, None], 0)
    jml_w += (w != 0) & ((~np.isnan(x)) & (np.nan_to_num(x) != 0))
    if v % 500 == 499:
        print(f"   ... {v + 1:,}/{V:,} variabel")


def ic_skor(G, pilih):
    ic = ic_bulanan(G, np.ones(T), pilih)
    return ic, ringkas(ic) if np.sum(~np.isnan(ic)) >= 12 else (0, np.nan, np.nan)


print(f"\n🔒 Data uji 2019+ {'DIBUKA SEBAGIAN (validasi 2019-2022)' if VALIDASI else 'DIKUNCI'}.")
print(f"   variabel ber-bobot per bulan evaluasi: median {np.median(jml_w[evaluasi]):.0f} (maks {jml_w[evaluasi].max():.0f})")
S2 = g["sinyal"]["S2"].values
for k, (num, den) in akum.items():
    G = np.where(den > 0, num / np.maximum(den, 1e-12), np.nan)
    ic, (n, m, t) = ic_skor(G, evaluasi)
    idx = np.flatnonzero(~np.isnan(ic))
    h = len(idx) // 2
    t1 = ringkas(np.where(np.isin(np.arange(T), idx[:h]), ic, np.nan))[2] if h >= MIN_IC else np.nan
    t2 = ringkas(np.where(np.isin(np.arange(T), idx[h:]), ic, np.nan))[2] if len(idx) - h >= MIN_IC else np.nan
    # korelasi dgn S2 & IC setelah S2 dikendalikan (residual peringkat)
    kor, res = [], np.full((T, N), np.nan)
    for t_ in idx:
        mm = L[t_] & ~np.isnan(G[t_]) & ~np.isnan(S2[t_])
        if mm.sum() < MIN_SAHAM:
            continue
        a = pd.Series(G[t_][mm]).rank().values
        b = pd.Series(S2[t_][mm]).rank().values
        kor.append(np.corrcoef(a, b)[0, 1])
        bb = np.polyfit(b, a, 1)
        res[t_, np.flatnonzero(mm)] = a - np.polyval(bb, b)
    _, (_, mr, tr) = ic_skor(res, evaluasi)
    # 5 kelompok (kotor)
    k5 = []
    for t_ in idx:
        mm = L[t_] & ~np.isnan(G[t_]) & ~np.isnan(E[t_])
        if mm.sum() < MIN_SAHAM:
            continue
        q = pd.qcut(pd.Series(G[t_][mm]).rank(method="first"), 5, labels=False).values
        k5.append(E[t_][mm][q == 4].mean() - E[t_][mm][q == 0].mean())
    k5 = np.array(k5)
    tk5 = k5.mean() / (k5.std(ddof=1) / np.sqrt(len(k5))) if len(k5) > 2 else np.nan
    putus = ("✅ LOLOS VALIDASI" if (m > 0 and t > 2) else "❌ GAGAL VALIDASI") if VALIDASI else \
        ("✅ LOLOS (t > 3)" if t > 3 else "❌ TIDAK LOLOS (t <= 3)")
    print(f"   [{k}] {n} bulan: IC G {m:+.4f} t {t:+.2f} (paruh {t1:+.2f} / {t2:+.2f}) -> {putus if k == 'semua' else '(info)'}")
    print(f"          kor peringkat G vs S2 {np.nanmean(kor):+.2f}; IC G setelah S2 dikendalikan {mr:+.4f} t {tr:+.2f}; "
          f"K5-K1 kotor {k5.mean():+.2%}/bln t {tk5:+.2f}")
