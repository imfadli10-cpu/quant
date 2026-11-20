"""
RISET #7: LONJAKAN PERHATIAN WIKIPEDIA -> VOLATILITAS MINGGU DEPAN (kripto & saham AS), data LATIH saja
==================================================================================================

DUGAAN (ditulis 2026-11-20 SEBELUM hubungan apa pun dilihat; di-commit sebelum dijalankan)
--------------------------------------------------------------------------------------
Perhatian publik mendadak naik (banyak orang membaca artikel Bitcoin/Ethereum/"Stock market crash") = investor baru &
kurang berpengalaman masuk -> perdagangan lebih ramai & emosional -> volatilitas minggu berikutnya LEBIH TINGGI,
melebihi yang sudah bisa ditebak dari volatilitas minggu ini (volatilitas itu "lengket"). Literatur: Urquhart 2018
(Google Trends memprediksi volatilitas Bitcoin), Da-Engelberg-Gao 2011 (perhatian -> tekanan harga).
Perkiraan jujur: sebagian besar efek sudah tertangkap volatilitas minggu ini; sisa efek kecil.

KEGUNAAN kalau lolos: BUKAN strategi beli/jual, tapi ramalan RISIKO (ukuran posisi / kapan mengurangi eksposur).

DEFINISI (minggu Sabtu-Jumat, pakai hari kalender untuk kripto, hari bursa untuk SPY):
  Lonjakan minggu w = log(rata-rata pembaca harian minggu w) - log(median pembaca harian 8 minggu SEBELUM w).
  Volatilitas RV = akar(jumlah kuadrat return log harian) dalam minggu itu; dipakai log(RV).
  Regresi: log RV(w+1) = a + b * log RV(w) + c * lonjakan(w).  Yang diuji: c > 0.
UJI (3, ditetapkan sekarang; |t| > 3; t = yang TERKECIL antara t White & t Newey-West 4 lag):
  U1 BTC-USD (Coinbase) <- artikel Bitcoin (en + id dijumlah)
  U2 ETH-USD (Coinbase) <- artikel Ethereum (en)
  U3 SPY (ETF S&P 500)   <- artikel en "Stock_market_crash" + "Recession" dijumlah
Latih: minggu target w+1 berakhir <= 2018-12-31. Data uji 2019+ DIKUNCI. Uji kode: --tes-tiruan (c = 0,3) & --tes-kosong.
"""
import sys

import numpy as np
import pandas as pd

BATAS_LATIH = pd.Timestamp("2018-12-31")
BUKA_DATA_UJI = "--buka-uji" in sys.argv
TES_KUAT = "--tes-tiruan-kuat" in sys.argv          # cek kebenaran kode: pola c = 1,0 harus jelas ditemukan
TES_TIRUAN, TES_KOSONG = "--tes-tiruan" in sys.argv or TES_KUAT, "--tes-kosong" in sys.argv
C_TIRUAN = 1.0 if TES_KUAT else 0.3
P = "W-FRI"


def ols_t(y, X, lag=4):
    """Koefisien + t White + t Newey-West(lag) untuk regresi y pada X (konstanta ditambahkan)."""
    X = np.column_stack([np.ones(len(y)), X])
    XtX_inv = np.linalg.inv(X.T @ X)
    b = XtX_inv @ X.T @ y
    e = y - X @ b
    u = X * e[:, None]
    S = u.T @ u
    se_white = np.sqrt(np.diag(XtX_inv @ S @ XtX_inv))
    for L in range(1, lag + 1):
        G = u[L:].T @ u[:-L]
        S = S + (1 - L / (lag + 1)) * (G + G.T)
    se_nw = np.sqrt(np.diag(XtX_inv @ S @ XtX_inv))
    return b, b / se_white, b / se_nw


def lonjakan_mingguan(pembaca_harian):
    """pembaca_harian: Series per tanggal. Hasil: Series per minggu (Period)."""
    rata = pembaca_harian.groupby(pembaca_harian.index.to_period(P)).mean()
    dasar = pembaca_harian.groupby(pembaca_harian.index.to_period(P)).median()
    acuan = dasar.shift(1).rolling(8, min_periods=8).median()       # median 8 minggu SEBELUMNYA
    return np.log(rata) - np.log(acuan)


def log_rv_mingguan(harga_harian):
    r = np.log(harga_harian).diff().dropna()
    kel = r.groupby(r.index.to_period(P))
    rv = np.sqrt((r ** 2).groupby(r.index.to_period(P)).sum())
    return np.log(rv[kel.size() >= 3])                              # minggu dengan >= 3 return harian


def uji(nama, lonj, lrv, rentang=None):
    d = pd.DataFrame({"lonj": lonj, "rv": lrv})
    d["rv_depan"] = d["rv"].shift(-1)
    d = d[d.index.to_series().map(lambda w: (w + 1) in lrv.index)].dropna()   # minggu w+1 benar-benar ada
    akhir_target = pd.Series([(w + 1).end_time.normalize() for w in d.index], index=d.index)
    pilih = (d.index.to_series().map(lambda w: w.end_time.normalize()) > BATAS_LATIH) if BUKA_DATA_UJI \
        else (akhir_target <= BATAS_LATIH)
    d = d[pilih.values]
    b, tw, tnw = ols_t(d["rv_depan"].values, d[["rv", "lonj"]].values)
    t_min = min(abs(tw[2]), abs(tnw[2])) * np.sign(b[2])
    print(f"   {nama:34} {len(d):4} mg ({d.index[0]} s/d {d.index[-1]}) | lengket b {b[1]:+.2f} | "
          f"c lonjakan {b[2]:+.3f} (t White {tw[2]:+.1f}, NW {tnw[2]:+.1f}) -> t {t_min:+.1f}")
    return t_min


if TES_TIRUAN or TES_KOSONG:
    acak = np.random.default_rng(7)
    hari = pd.date_range("2015-07-01", "2026-11-13", freq="D")
    hasil_seri = {}
    for nama in ["BTC", "ETH", "SPY"]:
        mg = pd.period_range(hari[0], hari[-1], freq=P)
        lon = pd.Series(acak.normal(0, 0.3, len(mg)), index=mg)
        lv = np.zeros(len(mg))
        for i in range(1, len(mg)):
            lv[i] = 0.5 * lv[i - 1] + (C_TIRUAN * lon.iloc[i - 1] if TES_TIRUAN else 0) + acak.normal(0, 0.3)
        # harga harian palsu dengan volatilitas mingguan exp(lv) dan pembaca harian palsu sesuai lonjakan
        sig = pd.Series(np.exp(lv - 3.5), index=mg).reindex(hari.to_period(P)).values / np.sqrt(7)
        harga = pd.Series(100 * np.exp(np.cumsum(acak.normal(0, 1, len(hari)) * sig)), index=hari)
        hasil_seri[nama] = (lon, log_rv_mingguan(harga))
    print(f"🧪 MODE TES: data PALSU {f'dengan pola (c = {C_TIRUAN})' if TES_TIRUAN else 'tanpa pola'}")
    pasangan = [(f"U{i + 1} {n} (palsu)", *hasil_seri[n]) for i, n in enumerate(["BTC", "ETH", "SPY"])]
else:
    w = pd.read_parquet("data/raw/histori/wikipedia/semua.parquet")
    w["tanggal"] = pd.to_datetime(w["tanggal"])
    def baca(*kunci):
        bag = [w[(w["wiki"] == wk) & (w["artikel"] == a)].set_index("tanggal")["pembaca"] for wk, a in kunci]
        return pd.concat(bag, axis=1).sum(axis=1, min_count=len(bag)).dropna().sort_index()
    c = pd.read_parquet("data/raw/histori/crypto_harian/semua.parquet")
    c["waktu"] = pd.DatetimeIndex(pd.to_datetime(c["waktu"]))
    if c["waktu"].dt.tz is not None:
        c["waktu"] = c["waktu"].dt.tz_localize(None)
    def koin(k):
        s = c[c["kode"] == k].set_index("waktu")["close"].sort_index()
        return s[~s.index.duplicated(keep="last")]
    import duckdb
    e = duckdb.connect().execute("""SELECT CAST(tanggal AS DATE) t, "Adj Close" a FROM read_parquet('data/bersih/saham_as.parquet')
                                    WHERE kode = 'SPY' ORDER BY 1""").df()
    spy = pd.Series(e["a"].values, index=pd.DatetimeIndex(e["t"]))
    pasangan = [
        ("U1 BTC <- Bitcoin (en+id)", lonjakan_mingguan(baca(("en.wikipedia", "Bitcoin"), ("id.wikipedia", "Bitcoin"))),
         log_rv_mingguan(koin("BTC-USD"))),
        ("U2 ETH <- Ethereum (en)", lonjakan_mingguan(baca(("en.wikipedia", "Ethereum"))), log_rv_mingguan(koin("ETH-USD"))),
        ("U3 SPY <- Stock_market_crash+Recession", lonjakan_mingguan(baca(("en.wikipedia", "Stock_market_crash"),
                                                                         ("en.wikipedia", "Recession"))),
         log_rv_mingguan(spy)),
    ]

print(f"🔒 Data uji {'DIBUKA' if BUKA_DATA_UJI else 'DIKUNCI'}.\n")
hasil = {nama: uji(nama, lon, lrv) for nama, lon, lrv in pasangan}
lolos = [n for n, t in hasil.items() if t > 3]
print(f"\n   KEPUTUSAN (t > 3): {', '.join(lolos) if lolos else 'tidak ada yang lolos'}")
