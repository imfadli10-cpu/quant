"""
RISET #54: ARUS ASING di SBN (kepemilikan non-residen, DJPPR) -> saham Indonesia minggu/bulan depan, data LATIH saja
================================================================================================================
DUGAAN (ditulis 26 Nov 2026 SEBELUM hubungan data ini dengan return saham dilihat; di-commit sebelum dijalankan)
Investor asing yang menambah/mengurangi SBN Rupiah = cermin selera risiko global terhadap Indonesia. Studi data harian Indonesia:
arus asing di OBLIGASI MENDAHULUI arus asing di SAHAM (journal.ipb.ac.id abq 74168). Mekanisme: dana pasar berkembang (benchmark obligasi
lokal) bereaksi lebih cepat; dana saham asing menyusul -> tekanan beli/jual saham besar IDX. Bantahan (diakui di depan): literatur pasar
berkembang (EMFT 2020) -> arus berkorelasi dgn return PERIODE YANG SAMA, lemah memprediksi; kepemilikan asing SBN digerakkan faktor
global (IMF 2023) yang juga cepat masuk harga saham. Riset #19 (arus TIC investor AS) NEGATIF. Perkiraan jujur: t < 2.
Ini timing SATU keranjang (breadth rendah) -> daya uji rendah, diakui.

DATA: raw/kepemilikan_sbn/harian.parquet (kumpul_kepemilikan_sbn.py). Nilai = Rp triliun (nominal) -> perubahan ~ ARUS (bukan harga),
  tetapi juga terpengaruh jatuh tempo/penerbitan. Harian sejak 2014; bulanan 2003-2013 (SUN saja s/d 2009, TOTAL SBN 2010+).
JEDA TERBIT: file bulan berjalan terlihat ~3 hari setelah tanggal data (23 Nov 2026 terlihat 26 Nov); histori jeda TIDAK diketahui
  -> konservatif: data harian dipakai 7 hari kalender sesudah tanggalnya; data bulanan dipakai 1 bulan penuh sesudahnya.

SINYAL MINGGUAN (minggu w = Sabtu-Jumat, P = W-FRI): A = kepemilikan non-residen (TOTAL) terakhir dgn tanggal <= Jumat(w) - 7 hari;
  F(w) = [A(Jumat(w) - 7 hr) - A(Jumat(w) - 35 hr)] / TOTAL SBN(Jumat(w) - 35 hr) x 100 (% dari SBN beredar, 4 minggu), dibatasi +-3.
TARGET minggu w+1 (fungsi riset #30/#31, masuk tutup hari bursa pertama w+1): U1 keranjang 30 saham likuid IDX; U2 EIDO.
SINYAL BULANAN U3: porsi asing p(m) = non-residen / total (jenis sama) di observasi TERAKHIR bulan m; dp(m) = p(m) - p(m-1) [pp; hanya
  bila kedua bulan ada & jenis sama]; dipakai akhir bulan m+1 -> target return keranjang 30 bulan m+2 (kalender bulanan riset #4/#27).
UJI (3; |t| robust White > 3; dua arah): U1, U2 (minggu sinyal 2014-02..2018-12, ~250 minggu), U3 (bulan 2003..2018, ~170 bln).
  Info: korelasi minggu YANG SAMA (cek kewajaran: arus asing masuk <-> saham naik, diduga positif), versi swasta saja
  (non-residen − pemerintah & bank sentral asing, 2014+), paruh waktu.
Data uji 2019+ DIKUNCI. Uji kode: --tes-tiruan (return palsu + 0,5%/minggu per +1% arus) & --tes-kosong; --potong-data -> IDENTIK.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BATAS = pd.Timestamp("2018-12-31")
TES_TIRUAN, TES_KOSONG = "--tes-tiruan" in sys.argv, "--tes-kosong" in sys.argv
POTONG = "--potong-data" in sys.argv
P = "W-FRI"
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

src30 = Path("riset_30_tga.py").read_text(encoding="utf-8")
exec(compile(src30[src30.index("def t_robust"):src30.index("def sinyal_tga")], "riset_30_fungsi", "exec"))

# ---- kepemilikan
k = pd.read_parquet("data/raw/kepemilikan_sbn/harian.parquet")
k["tanggal"] = pd.to_datetime(k["tanggal"]).astype("datetime64[ns]")


def seri(kat, jenis):
    x = k[(k["kategori"] == kat) & (k["jenis"] == jenis)].set_index("tanggal")["nilai"].sort_index()
    return x[~x.index.duplicated(keep="last")]


nr, tot, pa = seri("non_residen", "TOTAL"), seri("total", "TOTAL"), seri("non_residen_pemerintah_asing", "TOTAL")
nr_h, tot_h, pa_h = (x[x.index >= "2014-01-01"] for x in (nr, tot, pa))     # era HARIAN


def sinyal_mingguan(a, t):
    jum = pd.period_range("2014-02-07", a.index.max() + pd.Timedelta(days=7), freq=P)
    keluar = {}
    for w in jum:
        f = w.end_time.normalize()
        a1, a0, t0 = a[:f - pd.Timedelta(days=7)], a[:f - pd.Timedelta(days=35)], t[:f - pd.Timedelta(days=35)]
        if len(a0) and len(a1) and len(t0) and (f - pd.Timedelta(days=7) - a1.index[-1]).days <= 7:
            keluar[w] = (a1.iloc[-1] - a0.iloc[-1]) / t0.iloc[-1] * 100
    return pd.Series(keluar).clip(-3, 3)


F = sinyal_mingguan(nr_h, tot_h)
F_swasta = sinyal_mingguan((nr_h - pa_h.reindex(nr_h.index)).dropna(), tot_h)

# bulanan: porsi asing per bulan (observasi terakhir; jenis sama)
bul = []
for jenis in ("SUN", "TOTAL"):
    a, t = seri("non_residen", jenis), seri("total", jenis)
    if jenis == "SUN":
        a, t = a[a.index < "2010-01-01"], t[t.index < "2010-01-01"]
    p = (a / t).dropna()
    p = p.groupby(p.index.to_period("M")).last()
    urut = pd.Series([x.ordinal for x in p.index], index=p.index)
    dp = (p - p.shift(1)).where(urut.diff() == 1) * 100            # hanya bulan berurutan
    bul.append(dp.dropna())
dp = pd.concat(bul).sort_index()
dp = dp[~dp.index.duplicated(keep="last")]

# ---- return
if TES_TIRUAN or TES_KOSONG:
    acak = np.random.default_rng(54)
    mg = pd.period_range("2014-01-03", "2026-11-13", freq=P)
    r_idx = pd.Series(acak.normal(0.002, 0.025, len(mg)), index=mg)
    r_eido = pd.Series(acak.normal(0.002, 0.03, len(mg)), index=mg)
    bl = pd.period_range("2000-01", "2026-10", freq="M")
    r_bln = pd.Series(acak.normal(0.01, 0.06, len(bl)), index=bl)
    if TES_TIRUAN:
        r_idx = r_idx + 0.005 * F.reindex(mg).fillna(0)
        r_eido = r_eido + 0.005 * F.reindex(mg).fillna(0)
        r_bln = r_bln + 0.02 * dp.reindex(bl - 2).fillna(0).values
    print(f"🧪 MODE TES: return PALSU {'dgn pola (+0,5%/mg per +1% arus; +2%/bln per +1 pp porsi)' if TES_TIRUAN else 'tanpa pola'}")
    r_sama = None
else:
    kode = Path("riset_15_ramadan.py").read_text(encoding="utf-8").split("# ===== Label kalender =====")[0]
    ns, simpan = {}, sys.argv
    sys.argv = [sys.argv[0]]
    exec(compile(kode, "riset_15_bagian", "exec"), ns)
    sys.argv = simpan
    rk = ns["ret_keranjang"].dropna()
    r_idx = mingguan_dari_harian(rk)
    r_sama = (1 + rk).groupby(rk.index.to_period(P)).prod() - 1
    import duckdb
    e = duckdb.connect().execute("""SELECT CAST(tanggal AS DATE) t, "Adj Close" a FROM read_parquet('data/bersih/saham_as.parquet')
                                    WHERE kode = 'EIDO' ORDER BY 1""").df()
    se = pd.Series(e["a"].values, index=pd.DatetimeIndex(e["t"]))
    if POTONG:
        se = se[se.index <= BATAS]
    r_eido = mingguan_dari_harian(se.pct_change().dropna())
    r_bln = (1 + rk).groupby(rk.index.to_period("M")).prod() - 1
    # bulan berjalan terakhir tidak lengkap -> buang
    r_bln = r_bln[r_bln.index < rk.index.max().to_period("M")] if not POTONG else r_bln

print("🔒 Data uji 2019+ DIKUNCI.\n")


def pilih_mg(r):
    akhir = pd.Series([(w + 2).end_time.normalize() for w in r.index], index=r.index)
    return r[(akhir <= BATAS).values]


print(f"   sinyal mingguan F: {F.loc[:pd.Period('2018-12-28', freq=P)].notna().sum()} minggu latih, sb {F.loc[:pd.Period('2018-12-28', freq=P)].std():.2f}% "
      f"(dibatasi +-3: {(F.abs() >= 3).sum()} minggu)")
hasil = {}
for nama, r in [("U1 IDX keranjang 30", r_idx), ("U2 EIDO", r_eido)]:
    y = pilih_mg(r)
    b, t, n = t_robust(y, F.reindex(y.index))
    h = len(y) // 2
    t1, t2 = t_robust(y.iloc[:h], F.reindex(y.index[:h]))[1], t_robust(y.iloc[h:], F.reindex(y.index[h:]))[1]
    bs, ts, _ = t_robust(y, F_swasta.reindex(y.index))
    hasil[nama] = t
    print(f"   {nama:20}: +1% arus -> minggu depan {b:+.3%}, t robust {t:+.2f} ({n} mg; paruh {t1:+.1f}/{t2:+.1f}) | swasta saja t {ts:+.2f}")
# U3 bulanan
yb = r_bln[(r_bln.index.end_time.normalize() <= BATAS)]
xb = dp.reindex(yb.index - 2)
xb.index = yb.index
b3, t3, n3 = t_robust(yb, xb)
hasil["U3 bulanan"] = t3
print(f"   U3 bulanan          : +1 pp porsi asing (bln m) -> keranjang bln m+2 {b3:+.3%}, t robust {t3:+.2f} ({n3} bln)")
if r_sama is not None:
    ys = r_sama[r_sama.index.end_time.normalize() <= BATAS]
    a = nr_h
    sama = {}
    for w in ys.index:
        f = w.end_time.normalize()
        a1, a0, t0 = a[:f], a[:f - pd.Timedelta(days=7)], tot_h[:f - pd.Timedelta(days=7)]
        if len(a0) and len(a1) and len(t0):
            sama[w] = (a1.iloc[-1] - a0.iloc[-1]) / t0.iloc[-1] * 100
    sama = pd.Series(sama).clip(-3, 3)
    bs, ts, ns_ = t_robust(ys, sama.reindex(ys.index))
    print(f"   info cek kewajaran: arus minggu w vs keranjang minggu w (sama) {bs:+.3%} per +1%, t {ts:+.2f} ({ns_} mg)")
lolos = [n for n, t in hasil.items() if abs(t) > 3]
print(f"\n   KEPUTUSAN #54 (|t| > 3): {'✅ ' + ', '.join(lolos) if lolos else '❌ tidak ada yang lolos'}")
