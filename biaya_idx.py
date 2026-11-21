"""
Biaya transaksi IDX yang benar secara HISTORIS.

1) FRAKSI HARGA (tick) BEI berubah (diverifikasi 21 Nov 2026 dari Bisnis.com, Heygotrade, jurnal Mercu Buana; lihat CLAUDE.md):
   - s/d 5 Jan 2014 : < Rp200: 1 | Rp200-<500: 5 | Rp500-<2.000: 10 | Rp2.000-<5.000: 25 | >= Rp5.000: 50
   - 6 Jan 2014 - 1 Mei 2016: < Rp500: 1 | Rp500-<5.000: 5 | >= Rp5.000: 25
   - sejak 2 Mei 2016 : < Rp200: 1 | Rp200-<500: 2 | Rp500-<2.000: 5 | Rp2.000-<5.000: 10 | >= Rp5.000: 25
   (paper_trading.tick() = aturan 2016, benar untuk masa kini, SALAH untuk 2005-2015.)
2) HARGA ASLI: 'Close' Yahoo sudah disesuaikan split -> tick/harga salah untuk saham yang pernah split. harga_asli() membalik
   penyesuaian memakai raw/aksi_idx (rasio split, tanggal ex): harga asli hari t = Close_t x produk rasio split yang ex SESUDAH t.
"""
import numpy as np
import pandas as pd

AWAL_2014 = pd.Timestamp("2014-01-06")
AWAL_2016 = pd.Timestamp("2016-05-02")


def tick_historis(harga, tanggal):
    """harga & tanggal: array/Series sejajar (atau tanggal tunggal). Hasil: fraksi harga Rupiah (float array)."""
    h = np.asarray(harga, dtype=float)
    t = pd.DatetimeIndex(np.broadcast_to(np.asarray(pd.to_datetime(tanggal), dtype="datetime64[ns]"), h.shape).ravel()).values.reshape(h.shape)
    lama = np.select([h < 200, h < 500, h < 2000, h < 5000], [1, 5, 10, 25], 50)
    tengah = np.select([h < 500, h < 5000], [1, 5], 25)
    baru = np.select([h < 200, h < 500, h < 2000, h < 5000], [1, 2, 5, 10], 25)
    return np.where(t < np.datetime64(AWAL_2014), lama, np.where(t < np.datetime64(AWAL_2016), tengah, baru)).astype(float)


def harga_asli(tutup_adj_split, aksi, kode):
    """tutup_adj_split: Series harga (disesuaikan split) satu saham, indeks tanggal. aksi: DataFrame raw/aksi_idx
    (kode, tanggal, split). Hasil: harga yang benar-benar diperdagangkan saat itu."""
    s = aksi[(aksi["kode"] == kode) & (aksi["split"] > 0)]
    faktor = pd.Series(1.0, index=tutup_adj_split.index)
    for _, r in s.iterrows():
        faktor[faktor.index < r["tanggal"]] *= float(r["split"])     # sebelum ex-date: harga asli = adj x rasio
    return tutup_adj_split * faktor


def tabel_tick_historis(tutup, aksi=None):
    """tutup: DataFrame (tanggal x kode) harga Close Yahoo. Hasil: DataFrame tick/harga_asli (spread minimal, pecahan)."""
    hasil = {}
    for k in tutup.columns:
        h = tutup[k]
        if aksi is not None:
            h = harga_asli(h, aksi, k)
        hasil[k] = pd.Series(tick_historis(h.values, h.index) / h.values, index=h.index)
    return pd.DataFrame(hasil).where(tutup.notna())


if __name__ == "__main__":
    # Tes dengan kasus yang diketahui dari aturan resmi
    kasus = [(300, "2010-06-01", 5), (300, "2015-06-01", 1), (300, "2020-06-01", 2), (1500, "2012-01-02", 10),
             (1500, "2014-01-06", 5), (1500, "2016-05-02", 5), (6000, "2013-12-31", 50), (6000, "2015-01-02", 25),
             (3000, "2016-05-01", 5), (3000, "2016-05-02", 10), (150, "2008-01-01", 1)]
    for h, t, harap in kasus:
        hasil = tick_historis([h], t)[0]
        assert hasil == harap, (h, t, hasil, harap)
    tgl = pd.date_range("2007-07-20", "2007-08-03", freq="B")
    adj = pd.Series(1000.0, index=tgl)                         # Close disesuaikan split 5:1 (ex 27-07-2007)
    aksi = pd.DataFrame({"kode": ["AKRA"], "tanggal": [pd.Timestamp("2007-07-27")], "split": [5.0]})
    asli = harga_asli(adj, aksi, "AKRA")
    assert asli[:"2007-07-26"].eq(5000).all() and asli["2007-07-27":].eq(1000).all()
    print("✅ tes biaya_idx lolos (11 kasus fraksi harga + pembalikan split)")
