"""
RISET #52: MESIN PENYARING MASSAL "data aneh" -> penampang saham IDX (pra-registrasi: docs/prareg_52_penyaring.md, commit 2558b44)
=================================================================================================================================
Untuk SETIAP seri di data/olah/panel_*.parquet: berita z(t) (perubahan pengamatan baru yang terbit di bulan t, dibagi sb berita masa lalu,
dipotong +-3) x kepekaan saham beta_i(t) -> skor penampang -> IC peringkat thd return bulan depan (kerangka #13, semesta S2).
  Keluarga A: beta = kemiringan return KONTEMPORER (bulan j) thd z(j), j = t-60..t-1 ("peka lalu telat").
  Keluarga B: beta = kemiringan return BULAN SESUDAH berita thd z(j), hanya pasangan yang sudah terealisasi (j <= t-2) ("prediktif").
Koreksi uji ganda Benjamini-Hochberg q = 0,05 atas semua uji (A u B). Latih: tanggal jual <= 2018-12-31. 2019+ DIKUNCI.

  python riset_52_penyaring.py               -> penyaringan data latih -> data/olah/riset52_latih.parquet
  python riset_52_penyaring.py --tes-kosong  -> return PALSU tanpa pola (lolos BH harus ~0)
  python riset_52_penyaring.py --tes-tiruan  -> return PALSU + 21 variabel TERTANAM (3 kekuatan) -> berapa ditemukan / temuan palsu
  python riset_52_penyaring.py --potong-data -> semua file dipotong 2018-12-31 -> harus IDENTIK
  python riset_52_penyaring.py --validasi    -> (SEKALI, setelah latih) buka 2019-2022 HANYA utk variabel lolos BH
"""
import contextlib
import glob
import io
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

TES_TIRUAN, TES_KOSONG = "--tes-tiruan" in sys.argv, "--tes-kosong" in sys.argv
POTONG, VALIDASI = "--potong-data" in sys.argv, "--validasi" in sys.argv
CEPAT = "--cepat" in sys.argv                    # hanya utk mencoba kode: 1 dari 10 variabel
BATAS = pd.Timestamp("2018-12-31")
VAL_AWAL, VAL_AKHIR = pd.Timestamp("2019-01-01"), pd.Timestamp("2022-12-31")
JENDELA, MIN_RET, MIN_BERITA, MIN_SB, MIN_IC, MIN_SAHAM, Q_BH = 60, 36, 12, 12, 40, 30, 0.05

if POTONG:
    _baca = pd.read_parquet

    def _terpotong(*a, **k):
        d = _baca(*a, **k)
        if isinstance(d.index, pd.DatetimeIndex):
            d = d[d.index <= BATAS]
        for c in ("tanggal", "Date", "bulan", "tersedia"):
            if c in d.columns and pd.api.types.is_datetime64_any_dtype(d[c]):
                d = d[d[c] <= BATAS]
        return d
    pd.read_parquet = _terpotong

# ---------------------------------------------------------------- kerangka saham (#13)
kode13 = Path("riset_13_s2_hemat.py").read_text(encoding="utf-8").split("def simulasi(varian):")[0]
g = {"__file__": "riset_13_s2_hemat.py"}
simpan, sys.argv = sys.argv, [sys.argv[0]]
with contextlib.redirect_stdout(io.StringIO()):
    exec(compile(kode13, "riset_13_bagian", "exec"), g)
sys.argv = simpan
akhir_bulan, lolos, ret_pegang = g["akhir_bulan"], g["lolos"], g["ret_pegang"].copy()
awal = pd.Series(g["g"]["awal_bulan"]).reset_index(drop=True)
tgl_beli, tgl_jual = awal.shift(-1), awal.shift(-2)
T, N = ret_pegang.shape
POTONGAN = (pd.DatetimeIndex(akhir_bulan).to_period("M").to_timestamp(how="end").normalize() + pd.Timedelta(days=1)).values
latih = (tgl_jual <= BATAS).values
valid = ((tgl_beli >= VAL_AWAL) & (tgl_jual <= VAL_AKHIR)).values
print(f"   kerangka: {T} bulan sinyal {akhir_bulan[0]:%Y-%m}..{akhir_bulan[-1]:%Y-%m}, {N} saham; latih {latih.sum()} bln; "
      f"semesta median {lolos[latih].sum(1).median():.0f} saham")

# ---------------------------------------------------------------- berita z(t) per seri
PANEL = {"bps": ("panel_bps", "nilai"), "bpss": ("panel_bps_sambung", "tumbuh1"), "fred": ("panel_fred", "tumbuh1"),
         "alam": ("panel_alam", "nilai"), "pasar": ("panel_pasar", "nilai"), "lain": ("panel_lain", "nilai"),
         "seki": ("panel_seki", "nilai")}


def berita(bulan, tersedia, nilai, sudah_delta):
    """-> array T: perubahan pengamatan terbaru yang BARU terbit di bulan t (0 = tak ada berita, NaN = belum ada data)."""
    o = np.argsort(bulan, kind="stable")
    bulan, tersedia, nilai = bulan[o], tersedia[o], nilai[o]
    if sudah_delta:
        d = nilai
    elif np.all(nilai > 0):
        d = np.concatenate([[np.nan], np.diff(np.log(nilai))])
    else:
        d = np.concatenate([[np.nan], np.diff(nilai)])
    urut = np.argsort(tersedia, kind="stable")
    terbaru = np.maximum.accumulate(urut)                          # posisi (urut bulan) pengamatan terbaru yg sudah terbit
    k = np.searchsorted(tersedia[urut], POTONGAN, side="right")
    pos = np.where(k > 0, terbaru[np.maximum(k - 1, 0)], -1)
    dx = np.full(T, np.nan)
    ada = pos >= 0
    dx[ada] = 0.0
    baru = ada & (pos > np.concatenate([[-1], pos[:-1]]))
    dx[baru] = np.nan_to_num(d[pos[baru]], nan=0.0)
    # z: dibagi sb berita (Δx != 0) MASA LALU, min MIN_SB berita, dipotong +-3
    z = np.full(T, np.nan)
    lalu = []
    for t in range(T):
        if np.isnan(dx[t]):
            continue
        if len(lalu) >= MIN_SB:
            sb = np.std(lalu, ddof=1)
            z[t] = np.clip(dx[t] / sb, -3, 3) if sb > 0 else np.nan
        if dx[t] != 0:
            lalu.append(dx[t])
    return z


t0 = time.time()
Z, info = [], []
for nama, (f, kol) in PANEL.items():
    p = pd.read_parquet(f"data/olah/{f}.parquet", columns=["seri", "judul", "frek", "bulan", "tersedia", kol]
                        + (["pit"] if f not in ("panel_bps", "panel_bps_sambung") else []))
    p = p.dropna(subset=[kol, "tersedia", "bulan"])
    p = p[~p["frek"].astype(str).str.startswith("Y")]
    jml = p[(p["bulan"] >= "2000-01-01") & (p["bulan"] <= BATAS)].groupby("seri").size()
    calon = jml[jml >= MIN_IC].index
    if CEPAT:
        calon = calon[::10]
    p = p[p["seri"].isin(calon)]
    n0 = len(Z)
    for s, x in p.groupby("seri", sort=False):
        z = berita(x["bulan"].values.astype("datetime64[ns]"), x["tersedia"].values.astype("datetime64[ns]"),
                   x[kol].values.astype(float), kol == "tumbuh1")
        if np.sum(latih & ~np.isnan(z) & (np.nan_to_num(z) != 0)) < MIN_IC:
            continue
        Z.append(z)
        info.append({"seri": s, "panel": nama, "judul": str(x["judul"].iloc[0])[:150], "frek": str(x["frek"].iloc[0]),
                     "pit": bool(x["pit"].mean() > 0.5) if "pit" in x else False})
    print(f"   {nama}: {len(calon):,} seri cukup panjang -> {len(Z) - n0:,} punya >= {MIN_IC} bulan berita di latih ({time.time() - t0:.0f} dtk)")
Z = np.array(Z).T                                                  # T x V
info = pd.DataFrame(info)
V = Z.shape[1]

# ---------------------------------------------------------------- return (asli / palsu)
R = ret_pegang.values.astype(float)
L = lolos.values.astype(bool)
if TES_TIRUAN or TES_KOSONG:
    acak = np.random.default_rng(52)
    palsu = acak.normal(0.0, 0.10, (T, N)) + acak.normal(0.01, 0.06, T)[:, None]
    tanam = []
    if TES_TIRUAN:
        kandidat = np.flatnonzero((~np.isnan(Z)).sum(0) >= 200)
        tanam = acak.choice(kandidat, 21, replace=False)
        if "--satu" in sys.argv:                     # tes terkendali: SATU variabel (harga jagung), gamma 0,015
            tanam = np.flatnonzero(info["seri"].str.contains("yahoo_jagung_akhir").values)[:1].repeat(3)[2:]
        B_TANAM = {}
        if "--z-acak" in sys.argv:                   # berita variabel tertanam diganti acak N(0,1) TANPA autokorelasi (di bulan berita
            for v in tanam:                          # yang sama) -> mengisolasi jalur reaksi TERTUNDA (gamma)
                ada = ~np.isnan(Z[:, v]) & (np.nan_to_num(Z[:, v]) != 0)
                Z[ada, v] = np.clip(acak.normal(0, 1, ada.sum()), -3, 3)
        for k, v in enumerate(tanam):
            gam = 0.015 if "--satu" in sys.argv else [0.005, 0.010, 0.015][k % 3]
            if "--lemah" in sys.argv:                # daya uji gabungan #52b: semua efek 3x lebih lemah
                gam /= 3
            if "--tanpa-gamma" in sys.argv:          # kontrol: HANYA reaksi kontemporer (tanpa reaksi tertunda)
                gam = 0.0
            b = acak.normal(0, 1, N)
            B_TANAM[v] = b
            zz = np.nan_to_num(Z[:, v])
            palsu += b[None, :] * (gam * zz[:, None] + 0.03 * np.concatenate([zz[1:], [0]])[:, None])
            info.loc[v, "gamma_tanam"] = gam
    R = np.where(np.isnan(R), np.nan, palsu)
    print(f"🧪 MODE TES: return PALSU {'+ 21 variabel tertanam (gamma 0,005/0,010/0,015)' if TES_TIRUAN else 'tanpa pola'}")
rata = np.array([np.nanmean(R[t][L[t]]) if (L[t] & ~np.isnan(R[t])).any() else np.nan for t in range(T)])
E = R - rata[:, None]                                              # return dikurangi rata semesta (bulan pegang t)
RC = np.vstack([np.full((1, N), np.nan), E[:-1]])                  # return kontemporer bulan j = E[j-1]


def beta_bergulir(x, Y, geser):
    """kemiringan Y thd x atas jendela baris [t-geser-JENDELA+1 .. t-geser]."""
    M = ~np.isnan(Y) & ~np.isnan(x)[:, None]
    xf = np.where(M, x[:, None], 0.0)
    yf = np.where(M, Y, 0.0)
    nol = np.zeros((1, N))

    def jum(a):
        c = np.vstack([nol, np.cumsum(a, 0)])                    # c[k] = jumlah baris < k
        hi = np.clip(np.arange(T) - geser + 1, 0, T)
        lo = np.clip(hi - JENDELA, 0, T)
        return c[hi] - c[lo]
    n, sx, sy, sxx, sxy = jum(M.astype(float)), jum(xf), jum(yf), jum(xf * xf), jum(xf * yf)
    xb = np.where(np.isnan(x), 0, (np.nan_to_num(x) != 0).astype(float))
    cb = np.concatenate([[0], np.cumsum(xb)])
    hi = np.clip(np.arange(T) - geser + 1, 0, T)
    nb = cb[hi] - cb[np.clip(hi - JENDELA, 0, T)]
    pen = n * sxx - sx * sx
    with np.errstate(invalid="ignore", divide="ignore"):
        b = (n * sxy - sx * sy) / pen
    b[(n < MIN_RET) | (pen <= 1e-12) | (nb < MIN_BERITA)[:, None]] = np.nan
    return b


def ic_bulanan(bet, x, pilih):
    """IC peringkat per bulan: tanda(z) x Spearman(beta, E) di semesta; NaN bila < MIN_SAHAM."""
    rows = np.flatnonzero(pilih & ~np.isnan(x) & (np.nan_to_num(x) != 0))
    out = np.full(T, np.nan)
    if len(rows) == 0:
        return out
    B, Y = bet[rows], E[rows]
    M = ~np.isnan(B) & ~np.isnan(Y) & L[rows]
    ok = M.sum(1) >= MIN_SAHAM
    if not ok.any():
        return out
    rb = pd.DataFrame(np.where(M, B, np.nan)).rank(axis=1).to_numpy(copy=True)
    ry = pd.DataFrame(np.where(M, Y, np.nan)).rank(axis=1).to_numpy(copy=True)
    rb -= np.nanmean(rb, 1, keepdims=True)
    ry -= np.nanmean(ry, 1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        c = np.nansum(rb * ry, 1) / np.sqrt(np.nansum(rb ** 2, 1) * np.nansum(ry ** 2, 1))
    c = np.where(ok, c, np.nan) * np.sign(x[rows])
    out[rows] = c
    return out


def ringkas(ic):
    ic = ic[~np.isnan(ic)]
    if len(ic) < MIN_IC:
        return len(ic), np.nan, np.nan
    return len(ic), ic.mean(), ic.mean() / (ic.std(ddof=1) / np.sqrt(len(ic)))


pilih_periode = valid if VALIDASI else latih
if VALIDASI:
    lama = pd.read_parquet("data/olah/riset52_latih.parquet")
    lulus = lama[lama["lolos_bh"]]
    print(f"🔓 VALIDASI 2019-2022 dibuka HANYA utk {len(lulus)} uji yang lolos BH di latih")
    if lulus.empty:
        sys.exit("   tidak ada variabel lolos BH -> tidak ada yang dibuka.")
baris, IC_simpan = [], {}
t0 = time.time()
for v in range(V):
    x = Z[:, v]
    for kel, (Y, geser) in {"A": (RC, 1), "B": (E, 2)}.items():
        if VALIDASI and not ((lulus["seri"] == info.at[v, "seri"]) & (lulus["keluarga"] == kel)).any():
            continue
        bet = beta_bergulir(x, Y, geser)
        ic = ic_bulanan(bet, x, pilih_periode)
        n, m, t = ringkas(ic)
        if np.isnan(t):
            continue
        idx = np.flatnonzero(~np.isnan(ic))
        h = len(idx) // 2
        _, _, t1 = ringkas(np.where(np.isin(np.arange(T), idx[:h]), ic, np.nan)) if h >= MIN_IC else (0, 0, np.nan)
        _, _, t2 = ringkas(np.where(np.isin(np.arange(T), idx[h:]), ic, np.nan)) if len(idx) - h >= MIN_IC else (0, 0, np.nan)
        baris.append({**info.loc[v].to_dict(), "keluarga": kel, "n_ic": n, "ic": m, "t": t, "t_paruh1": t1, "t_paruh2": t2})
        if VALIDASI:
            IC_simpan[(info.at[v, "seri"], kel)] = (ic, bet, x)
    if v % 500 == 499:
        print(f"   ... {v + 1:,}/{V:,} variabel ({time.time() - t0:.0f} dtk)")
h = pd.DataFrame(baris)
from scipy.stats import norm  # noqa: E402

h["p"] = 2 * norm.sf(h["t"].abs())
m = len(h)
urut = h["p"].rank(method="first")
ambang = h["p"] <= Q_BH * urut / m
kmax = urut[ambang].max() if ambang.any() else 0
h["lolos_bh"] = urut <= kmax
print(f"\n🔒 Data uji 2019+ {'DIBUKA SEBAGIAN (validasi 2019-2022, variabel lolos saja)' if VALIDASI else 'DIKUNCI'}.")
print(f"   {V:,} variabel, {m:,} uji (A+B); |t| > 2: {(h['t'].abs() > 2).sum():,} (acak ~{0.0455 * m:,.0f}); "
      f"|t| > 3: {(h['t'].abs() > 3).sum():,} (acak ~{0.0027 * m:,.1f}); |t| > 4: {(h['t'].abs() > 4).sum():,} (acak ~{6.3e-5 * m:,.2f})")
print(f"   LOLOS BH (q = {Q_BH}): {h['lolos_bh'].sum():,} uji; ambang p {h.loc[h['lolos_bh'], 'p'].max() if kmax else float('nan'):.2e}")
print(f"   sebaran t: rata {h['t'].mean():+.2f}, sb {h['t'].std():.2f} (acak murni ~1,0; sb > 1 = ketergantungan antar variabel/saham)")
print(f"   per panel & keluarga (jumlah uji / |t|>3 / lolos BH):")
print(h.groupby(["panel", "keluarga"]).agg(uji=("t", "size"), t3=("t", lambda s: (s.abs() > 3).sum()),
                                           bh=("lolos_bh", "sum")).to_string())
kol = ["panel", "keluarga", "seri", "judul", "frek", "pit", "n_ic", "ic", "t", "t_paruh1", "t_paruh2", "lolos_bh"]
print("\n   20 |t| terbesar:")
print(h.reindex(h["t"].abs().sort_values(ascending=False).index)[kol].head(20).to_string(max_colwidth=70))
if TES_TIRUAN:
    tn = h[h["gamma_tanam"].notna()] if "gamma_tanam" in h else h.iloc[0:0]
    print("\n🧪 HASIL TES TIRUAN (keluarga A seharusnya menemukan; B tidak wajib):")
    print(tn.groupby(["gamma_tanam", "keluarga"]).agg(n=("t", "size"), t_median=("t", "median"),
                                                      ditemukan=("lolos_bh", "sum")).to_string())
    print(tn[["seri", "keluarga", "gamma_tanam", "n_ic", "ic", "t", "lolos_bh"]].sort_values(["gamma_tanam", "keluarga"]).to_string())
    palsu_lolos = h[h["lolos_bh"] & h.get("gamma_tanam", pd.Series(np.nan, index=h.index)).isna()]
    print(f"   temuan PALSU (lolos BH tapi tidak ditanam): {len(palsu_lolos)}")
    # DIAGNOSIS: ketepatan beta A thd kepekaan sebenarnya, |z| rata di bulan IC, & korelasi temuan palsu dgn variabel tertanam
    vi = {s: i for i, s in enumerate(info["seri"])}
    for v in tanam:
        x = Z[:, v]
        bet = beta_bergulir(x, RC, 1)
        bul = np.flatnonzero(latih & ~np.isnan(x) & (np.nan_to_num(x) != 0))
        kor = [np.corrcoef(bet[t][L[t] & ~np.isnan(bet[t])], B_TANAM[v][L[t] & ~np.isnan(bet[t])])[0, 1]
               for t in bul if (L[t] & ~np.isnan(bet[t])).sum() >= MIN_SAHAM]
        print(f"   tanam {info.at[v, 'seri'][:45]:45s} gamma {info.at[v, 'gamma_tanam']}: bulan berita latih {len(bul)}, "
              f"bulan beta sah {len(kor)}, kor(beta, b) median {np.nanmedian(kor) if kor else np.nan:.2f}, "
              f"|z| rata {np.nanmean(np.abs(x[bul])):.2f}")
    for v in tanam[:3]:                               # IC ORAKEL: kepekaan SEBENARNYA (b) menggantikan beta taksiran
        x = Z[:, v]
        orakel = np.where(~np.isnan(beta_bergulir(x, RC, 1)), B_TANAM[v][None, :], np.nan)
        n_o, m_o, t_o = ringkas(ic_bulanan(orakel, x, latih))
        n_h, m_h, t_h = ringkas(ic_bulanan(beta_bergulir(x, RC, 1), x, latih))
        print(f"   ORAKEL {info.at[v, 'seri'][:40]}: IC b-sebenarnya {m_o:+.4f} (t {t_o:+.2f}) vs beta-taksiran {m_h:+.4f} (t {t_h:+.2f})")
    zt = np.nan_to_num(Z[:, tanam])
    for s in palsu_lolos["seri"].unique()[:15]:
        zv = np.nan_to_num(Z[:, vi[s]])
        k = [abs(np.corrcoef(zv, zt[:, j])[0, 1]) for j in range(zt.shape[1])]
        print(f"   palsu {s[:55]:55s} max |kor z| dgn tanam {np.nanmax(k):.2f}")
    kmax_all = []
    for s in palsu_lolos["seri"].unique():
        zv = np.nan_to_num(Z[:, vi[s]])
        kmax_all.append(np.nanmax([abs(np.corrcoef(zv, zt[:, j])[0, 1]) for j in range(zt.shape[1])]))
    kmax_all = np.array(kmax_all)
    print(f"   temuan palsu dgn max |kor z| >= 0,5 thd variabel tertanam: {(kmax_all >= 0.5).sum()} dari {len(kmax_all)}; "
          f">= 0,3: {(kmax_all >= 0.3).sum()}")
elif TES_KOSONG:
    print(f"\n🧪 TES KOSONG: lolos BH {h['lolos_bh'].sum()} (harus ~0)")
elif VALIDASI:
    print("\n   VALIDASI per uji (2019-2022):")
    print(h[kol].to_string(max_colwidth=70))
    # skor gabungan: rata peringkat skor (arah = tanda IC latih)
    arah = lulus.set_index(["seri", "keluarga"])["ic"].pipe(np.sign)
    skor = np.zeros((T, N))
    cacah = np.zeros((T, N))
    for (s, kel), (ic, bet, x) in IC_simpan.items():
        sk = bet * np.nan_to_num(x)[:, None] * arah[(s, kel)]
        rk = pd.DataFrame(np.where(L & (np.nan_to_num(x) != 0)[:, None], sk, np.nan)).rank(axis=1, pct=True).values
        skor += np.nan_to_num(rk)
        cacah += ~np.isnan(rk)
    gab = np.where(cacah > 0, skor / np.maximum(cacah, 1), np.nan)
    icg = ic_bulanan(gab, np.ones(T), valid)
    n, mg, tg = ringkas(icg) if np.sum(~np.isnan(icg)) >= MIN_IC else (np.sum(~np.isnan(icg)), np.nanmean(icg),
                                                                        np.nanmean(icg) / (np.nanstd(icg, ddof=1) / np.sqrt(np.sum(~np.isnan(icg)))))
    print(f"\n   GABUNGAN 2019-2022: {n} bulan, IC {mg:+.4f}, t {tg:+.2f} -> {'✅ LOLOS VALIDASI' if (mg > 0 and tg > 2) else '❌ GAGAL VALIDASI'}")
else:
    if POTONG:
        h.to_parquet("data/olah/riset52_latih_potong.parquet", index=False)
    else:
        h.to_parquet("data/olah/riset52_latih.parquet", index=False)
    print("   disimpan -> data/olah/riset52_latih" + ("_potong" if POTONG else "") + ".parquet")
