"""
RISET #50: MOMENTUM SEKTOR (industry momentum) long-only -> saham IDX bulan depan
================================================================================
DUGAAN (ditulis 2026-11-22 SEBELUM melihat return strategi ini; di-commit sebelum dijalankan)
Moskowitz & Grinblatt (1999 JF, "Do industries explain momentum?"): industri pemenang 6-12 bulan terus menang; komponen industri menjelaskan
sebagian besar momentum saham. Asness, Porter & Stevens (2000); di pasar berkembang momentum sektor/negara juga terdokumentasi. Alasan logis:
informasi tingkat sektor (siklus komoditas, kebijakan, kredit) menyebar lambat ke harga semua emiten sektor itu (Hong-Torous-Valkanov 2007).
Riset #2: momentum saham 12-1 IDX IC t 4 tapi K5 bersih t 1,4 (perputaran & biaya). Momentum SEKTOR berubah lebih lambat -> perputaran
lebih rendah, dan portofolio berisi banyak saham (risiko spesifik terdiversifikasi).
DUGAAN: saham di 3 sektor dengan return 12-1 tertinggi mengungguli semesta bulan depan.

DATA SEKTOR: foto fundamental Yahoo 2026-11-21 (raw/fundamental_idx/info, kolom 'sector', 11 sektor GICS-mirip; 914 dari 919 saham terisi).
  KETERBATASAN (diakui di depan): peta sektor STATIS (Nov 2026) dipakai untuk 2005-2018; klasifikasi emiten jarang berubah tapi ada sedikit
  informasi masa depan (perusahaan yang ganti usaha). Survivorship IDX tetap ada.
SINYAL akhir bulan i: return sektor bulan j = rata-rata ret_pegang[j] saham semesta S2 (`lolos` bulan j) di sektor itu (min 3 saham);
  momentum sektor = jumlah log(1 + return sektor) untuk j = i-12 .. i-2 (11 bulan, lewati bulan terakhir; ret_pegang[j] berakhir
  hari bursa pertama bulan j+2 <= awal bulan i -> sudah terealisasi saat sinyal). Butuh >= 9 dari 11 bulan.
STRATEGI: P = semua saham semesta bulan i di 3 sektor teratas (sektor dgn >= 3 saham semesta), bobot sama; masuk tutup hari bursa pertama
  i+1, tahan 1 bulan. Biaya B (0,4% + 1,2 x tick historis/harga asli) x perputaran P (porsi saham baru).
UJI:
  U1 (PENENTU, satu ukuran): rata-rata (P_bersih - semesta), t antar bulan > 3 -> lolos latih.
  Info: IC peringkat sektor (Spearman sinyal vs return sektor bulan depan), alpha CAPM bersih (rf IRSTCI01IDM156N), perputaran, paruh waktu.
LATIH: bulan sinyal yang tanggal JUAL <= 2018-12-31. UJI 2019+ DIKUNCI (--buka-uji sekali, hanya bila latih lolos).
Daya uji (return palsu, SEBELUM commit): drift sektor AR(1) phi 0,95 sb 0,4% -> IC sektor t +7,7, kotor +0,88%/bln, BERSIH +0,68% t +5,5;
  tanpa pola: IC t -1,0, bersih -0,50% t -4,5 (biaya 0,35% + derau). Perputaran 15-28%/bln, P ~35-40 saham. 113 bulan latih (2006-02..2018-10).
Uji kode: --tes-tiruan (return palsu + sektor punya drift bertahan AR(1) -> momentum sektor nyata) & --tes-kosong (tanpa drift);
  --potong-data (semua file dipotong di 2018-12-31 -> IDENTIK, kecuali biaya beda tipis karena harga_asli; lihat #46).
"""
import contextlib
import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(".").resolve()))
from biaya_idx import tabel_tick_historis

BUKA_DATA_UJI = "--buka-uji" in sys.argv
TES_TIRUAN, TES_KOSONG = "--tes-tiruan" in sys.argv, "--tes-kosong" in sys.argv
POTONG = "--potong-data" in sys.argv
BATAS = pd.Timestamp("2018-12-31")
N_ATAS = 3

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


def t_rata(x):
    x = pd.Series(x).dropna()
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else np.nan


def alpha_white(y, x):
    X = np.column_stack([np.ones(len(x)), x])
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    e = y - X @ b
    XtX = np.linalg.inv(X.T @ X)
    V = XtX @ (X.T * e ** 2) @ X @ XtX
    return b[0], b[1], b[0] / np.sqrt(V[0, 0])


kode13 = Path("riset_13_s2_hemat.py").read_text(encoding="utf-8").split("def simulasi(varian):")[0]
g = {"__file__": "riset_13_s2_hemat.py"}
simpan, sys.argv = sys.argv, [sys.argv[0]]
with contextlib.redirect_stdout(io.StringIO()):
    exec(compile(kode13, "riset_13_bagian", "exec"), g)
sys.argv = simpan
gg = g["g"]
akhir_bulan, lolos, ret_pegang = g["akhir_bulan"], g["lolos"], g["ret_pegang"].copy()
tgl_jual = pd.Series(gg["awal_bulan"]).shift(-2).reset_index(drop=True)
tgl_beli = pd.Series(gg["awal_bulan"]).shift(-1).reset_index(drop=True)
if POTONG:
    print(f"   (cek potong: harga terakhir {gg['adj'].index.max():%Y-%m-%d})")
tick = tabel_tick_historis(gg["tutup"], pd.read_parquet("data/raw/aksi_idx/semua.parquet"))
biaya_rt = (0.004 + 1.2 * tick.loc[akhir_bulan]).reset_index(drop=True)
bunga = pd.read_parquet("data/raw/makro/IRSTCI01IDM156N.parquet")["nilai"]
bunga.index = pd.to_datetime(bunga.index).to_period("M")

info = pd.read_parquet("data/raw/fundamental_idx/info/2026-11-21.parquet")
sektor = info.assign(kode=info["kode"].str.replace(".JK", "", regex=False)).set_index("kode")["sector"].dropna()
sektor = sektor.reindex(ret_pegang.columns)
print(f"   peta sektor: {sektor.notna().sum()} dari {len(sektor)} kode harga punya sektor ({sektor.nunique()} sektor)")

if TES_TIRUAN or TES_KOSONG:
    acak = np.random.default_rng(50)
    nama_s = sorted(sektor.dropna().unique())
    T = len(ret_pegang)
    drift = np.zeros((T, len(nama_s)))
    if TES_TIRUAN:                      # drift sektor bertahan (AR(1), phi 0,95, sb inovasi 0,4%) -> momentum sektor nyata
        for s in range(len(nama_s)):
            for t in range(1, T):
                drift[t, s] = 0.95 * drift[t - 1, s] + acak.normal(0, 0.004)
    kol = {s: j for j, s in enumerate(nama_s)}
    d_saham = np.array([[drift[t, kol[sektor[c]]] if pd.notna(sektor[c]) else 0.0 for c in ret_pegang.columns] for t in range(T)])
    pasar = acak.normal(0.01, 0.05, T)[:, None]
    palsu = pasar + d_saham + acak.normal(0, 0.08, ret_pegang.shape)
    ret_pegang = pd.DataFrame(palsu, index=ret_pegang.index, columns=ret_pegang.columns).where(ret_pegang.notna())
    print(f"🧪 MODE TES: return PALSU {'dengan drift sektor AR(1) (momentum sektor)' if TES_TIRUAN else 'tanpa pola sektor'}")

# return sektor per bulan j (bobot sama, saham semesta bulan j)
ret_sektor = {}
for j in range(len(akhir_bulan)):
    ok = lolos.loc[j] & ret_pegang.loc[j].notna() & sektor.notna()
    r = ret_pegang.loc[j][ok].groupby(sektor[ok]).agg(["mean", "size"])
    ret_sektor[j] = r["mean"].where(r["size"] >= 3)
ret_sektor = pd.DataFrame(ret_sektor).T                  # baris j, kolom sektor
lr = np.log1p(ret_sektor)

baris, pilih_lalu = [], set()
for i, t in enumerate(akhir_bulan):
    if pd.isna(tgl_jual.iloc[i]) or i < 12:
        continue
    if BUKA_DATA_UJI:
        if tgl_beli.iloc[i] < pd.Timestamp("2019-01-01"):
            continue
    elif tgl_jual.iloc[i] > BATAS:
        continue
    jendela = lr.iloc[i - 12:i - 1]                     # j = i-12 .. i-2
    mom = jendela.sum(min_count=9).where(jendela.notna().sum() >= 9)
    ok = lolos.loc[i] & ret_pegang.loc[i].notna() & sektor.notna()
    n_s = sektor[ok].value_counts()
    mom = mom[mom.index.isin(n_s.index[n_s >= 3])].dropna()
    if ok.sum() < 30 or len(mom) < 6:
        pilih_lalu = set()
        continue
    atas = mom.sort_values(ascending=False).index[:N_ATAS]
    r = ret_pegang.loc[i][ok]
    P = set(r.index[sektor[r.index].isin(atas)])
    putar = 1.0 if not pilih_lalu else len(P - pilih_lalu) / len(P)
    biaya = putar * biaya_rt.loc[i, list(P)].fillna(0.012).mean()
    pilih_lalu = P
    rs_depan = r.groupby(sektor[r.index]).mean().reindex(mom.index)
    baris.append({"t": t, "n": ok.sum(), "n_P": len(P), "putar": putar, "biaya": biaya, "sektor_atas": ",".join(atas),
                  "rf": bunga.get(t.to_period("M") + 1, np.nan) / 1200,
                  "P_bersih": r[list(P)].mean() - biaya, "P_kotor": r[list(P)].mean(), "U": r.mean(),
                  "ic": mom.rank().corr(rs_depan.rank())})
h = pd.DataFrame(baris).set_index("t")
h["rf"] = h["rf"].ffill()
print(f"🔒 Data uji (2019+) {'DIBUKA' if BUKA_DATA_UJI else 'DIKUNCI'}.\n")
p = len(h) // 2
selisih = h["P_bersih"] - h["U"]
a, b, ta = alpha_white((h["P_bersih"] - h["rf"]).values, (h["U"] - h["rf"]).values)
print(f"   {len(h)} bulan ({h.index.min():%Y-%m} s/d {h.index.max():%Y-%m}), median {h['n'].median():.0f} saham semesta, "
      f"P median {h['n_P'].median():.0f} saham; putar {h['putar'].iloc[1:].mean():.0%}, biaya {h['biaya'].mean():.2%}/bln")
print(f"   IC peringkat sektor {h['ic'].mean():+.3f} t {t_rata(h['ic']):+.2f} | kotor P - semesta {(h['P_kotor'] - h['U']).mean():+.2%}/bln "
      f"t {t_rata(h['P_kotor'] - h['U']):+.2f} | alpha CAPM bersih {a:+.2%} (beta {b:.2f}) t {ta:+.2f}")
print(f"   U1 P BERSIH - semesta (PENENTU, t > 3): {selisih.mean():+.2%}/bln, t {t_rata(selisih):+.2f} "
      f"(paruh {t_rata(selisih.iloc[:p]):+.1f} / {t_rata(selisih.iloc[p:]):+.1f})")
print("   sektor paling sering terpilih: " + ", ".join(f"{k} {v}" for k, v in
      pd.Series(",".join(h["sektor_atas"]).split(",")).value_counts().head(5).items()))
if BUKA_DATA_UJI:
    print("   per tahun: " + " | ".join(f"{y} {v:+.2%}" for y, v in selisih.groupby(selisih.index.year).mean().items()))
tu = t_rata(selisih)
print(f"\n   KEPUTUSAN #50 (U1 t > 3): {tu:+.2f} -> {'✅ lolos latih' if tu > 3 else '❌ tidak lolos'}")
