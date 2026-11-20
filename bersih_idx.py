"""
Pembersih harga saham IDX dari Yahoo (data/raw/harga_idx).

Masalah yang ditemukan 20 Nov 2026 (scan semua saham): 248 titik di 98 saham menyimpang > 50% dari median 9 hari
di sekitarnya, lalu harga KEMBALI normal. Contoh: ANTM 2008-10-24 = 1757 (median 576, volume 0, nilai basi yang
sama muncul berulang di beberapa tanggal), ELTY 2018-05 = 5000 (median 500), MAPI/TOWR 2018-05-02 turun 80-90% satu
hari. Bursa IDX punya batas ARA/ARB harian (20-35%), jadi lonjakan > 50% yang langsung kembali hampir pasti salah data.

ATURAN: titik dengan |harga / median 9 hari TERPUSAT - 1| > 50% dianggap rusak -> dikosongkan (NaN).
PERINGATAN: median TERPUSAT melihat 4 hari ke depan -> HANYA untuk riset historis, JANGAN untuk sinyal live.
"""
import pandas as pd

AMBANG, JENDELA = 0.5, 9


def tandai_rusak(harga: pd.DataFrame, ambang=AMBANG, jendela=JENDELA) -> pd.DataFrame:
    """True di titik yang menyimpang > ambang dari median terpusat (dihitung per kolom, abaikan NaN)."""
    med = harga.rolling(jendela, center=True, min_periods=5).median()
    return (harga / med - 1).abs() > ambang


def bersihkan(harga: pd.DataFrame, ambang=AMBANG, jendela=JENDELA, ulang=3, batas="2018-12-31") -> pd.DataFrame:
    """Kosongkan titik rusak; diulang beberapa kali karena titik rusak berurutan bisa menutupi satu sama lain.
    Data s/d `batas` (akhir data latih) dibersihkan TERPISAH dari sesudahnya: median terpusat tidak boleh mengintip data uji."""
    if batas is not None:
        b = pd.Timestamp(batas)
        return pd.concat([_bersihkan(harga.loc[harga.index <= b], ambang, jendela, ulang),
                          _bersihkan(harga.loc[harga.index > b], ambang, jendela, ulang)])
    return _bersihkan(harga, ambang, jendela, ulang)


def _bersihkan(harga, ambang, jendela, ulang):
    h = harga.copy()
    for _ in range(ulang):
        rusak = tandai_rusak(h, ambang, jendela)
        if not rusak.values.any():
            break
        h = h.mask(rusak)
    return h


if __name__ == "__main__":
    # Tes dengan data tiruan berformat asli: lonjakan 1 hari harus terhapus, kenaikan bertahap (nyata) harus tetap.
    import numpy as np
    hari = pd.bdate_range("2008-01-01", periods=60).astype("datetime64[ns]")
    a = pd.Series(100.0, index=hari)
    a.iloc[20] = 300.0                       # lonjakan palsu 1 hari
    a.iloc[30:33] = 10.0                     # turun palsu 3 hari berurutan
    b = pd.Series(np.linspace(100, 400, 60), index=hari)   # naik 4x pelan-pelan = nyata
    c = pd.Series(100.0, index=hari)
    c.iloc[40:] = 180.0                      # naik permanen 80% (aksi korporasi/berita) = bukan lonjakan sementara
    h = bersihkan(pd.DataFrame({"A": a, "B": b, "C": c}))
    assert h["A"].isna().sum() == 4 and h["A"].iloc[[20, 30, 31, 32]].isna().all(), h["A"].isna().sum()
    assert h["B"].isna().sum() == 0 and h["C"].isna().sum() == 0
    besar = pd.DataFrame({"A": a}, index=hari)
    besar.index = pd.bdate_range("2018-11-20", periods=60).astype("datetime64[ns]")
    besar.iloc[:] = 100.0
    besar.iloc[33:] = 1000.0      # loncatan permanen tepat setelah batas -> titik 2018 tidak boleh terpengaruh 2019
    assert bersihkan(besar).loc[:"2018-12-31"].notna().all().all()
    print("✅ tes bersih_idx lolos (lonjakan palsu terhapus, gerak permanen/bertahap aman)")
