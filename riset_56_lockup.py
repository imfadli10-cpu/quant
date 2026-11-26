"""
RISET #56: BERAKHIRNYA MASA KUNCI (LOCK-UP) 8 BULAN SAHAM IPO IDX -> harga turun? (studi peristiwa, data LATIH saja)
================================================================================================================
DUGAAN (ditulis 26 Nov 2026 SEBELUM harga di sekitar tanggal lock-up dilihat; di-commit sebelum dijalankan)
Field & Hanka (2001, JF): saat lock-up berakhir volume naik ~40% PERMANEN & return abnormal 3 hari -1,5% (lebih besar bila didanai
modal ventura); studi AS 2000-2020: penurunan justru SEBELUM tanggal (diantisipasi); Malaysia: abnormal negatif. Di BEI: POJK
25/POJK.04/2017 -> pihak yang memperoleh saham di bawah harga IPO dalam 6 bulan sebelum pendaftaran DILARANG menjual 8 BULAN sejak
pernyataan pendaftaran EFEKTIF. Mekanisme: pasokan saham baru dari pemegang pra-IPO + pasar ritel IDX yang tipis -> tekanan harga.
Bantahan: tanggal diketahui publik (seharusnya sudah masuk harga), tidak semua IPO punya pemegang saham terkunci, banyak IPO kecil
berderau besar (lotre, ARA/ARB). Perkiraan jujur: arah negatif, |t| < 2 (134 peristiwa, return IPO kecil sangat berderau).

PEMBAGIAN (sama dgn #28): LATIH = IPO pencatatan <= 2023-06-30 (lock-up berakhir ~2022-03 .. 2024-02); UJI = sesudahnya (DIKUNCI).
DATA: raw/ipo/detail.parquet (Closed, ada pencatatan & penawaran_mulai); harga Adj Close Yahoo data/raw/harga_idx/<KODE>; pembanding
  keranjang 30 saham likuid (riset #15). Tanggal EFEKTIF tidak ada di e-IPO -> perkiraan = 1 hari kerja SEBELUM penawaran_mulai
  (OJK menyatakan efektif lalu penawaran dimulai; jarak penawaran->pencatatan median 6 hari). Akhir kunci = efektif + 8 bulan kalender;
  d0 = hari bursa pertama >= tanggal itu (kalender keranjang; harga saham diisi-maju bila tidak ada transaksi).
UJI (3; |t| > 3; t = rata-rata antar peristiwa / (sb/akar n); return abnormal = saham - keranjang, dibatasi +-50%):
  U1 CAR[-5,+5]  (beli tutup d-6, jual tutup d+5)  -> dugaan NEGATIF (Field-Hanka)
  U2 CAR[-20,-1] (antisipasi)                       -> dugaan NEGATIF
  U3 CAR[0,+20]  (pasca)                            -> dugaan NEGATIF
Info: cek mekanisme VOLUME = log(rata-rata volume [0,+20] / rata-rata [-60,-21]) (dugaan positif); median & porsi negatif U1;
  pembanding PLASEBO: tanggal palsu efektif + 6 bulan (bukan tanggal kunci) -> CAR[-5,+5] seharusnya ~0.
Kegunaan kalau lolos: SARINGAN HINDARI (keluarkan saham dari portofolio menjelang akhir lock-up), bukan strategi short.
Uji kode: --tes-tiruan (IPO palsu, -3% di [-5,+5]) & --tes-kosong.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BATAS = pd.Timestamp("2023-06-30")
TES_TIRUAN, TES_KOSONG = "--tes-tiruan" in sys.argv, "--tes-kosong" in sys.argv
POLA = float(__import__("os").environ.get("POLA_56", "0.03"))
JENDELA = {"U1 CAR[-5,+5]": (-6, 5), "U2 CAR[-20,-1]": (-21, -1), "U3 CAR[0,+20]": (-1, 20)}


def t_rata(x):
    x = pd.Series(x).dropna()
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else np.nan


def jadi_tanggal(x):
    t = pd.DatetimeIndex(pd.to_datetime(x))
    return (t.tz_localize(None) if t.tz is not None else t).normalize().astype("datetime64[ns]")


if TES_TIRUAN or TES_KOSONG:
    acak = np.random.default_rng(56)
    hari = pd.bdate_range("2020-06-01", "2026-11-13").astype("datetime64[ns]")
    r_pasar = pd.Series(acak.normal(0.0004, 0.01, len(hari)), index=hari)
    ipo, harga = [], {}
    for i in range(134):
        mulai = pd.Timestamp(acak.choice(hari[(hari >= "2021-02-01") & (hari <= "2023-06-20")]))
        tgl = mulai + pd.offsets.BDay(6)
        kode = f"T{i:03d}"
        hh = hari[hari >= tgl]
        r = acak.normal(-0.04 ** 2 / 2, 0.04, len(hh)) + r_pasar.reindex(hh).values     # log: koreksi sigma^2/2 -> rata-rata aritmetika 0
        r[:3] += 0.15
        vol = np.full(len(hh), 1e6)
        efektif = mulai - pd.offsets.BDay(1)
        akhir = efektif + pd.DateOffset(months=8)
        d0 = int(np.searchsorted(hh, akhir))
        if TES_TIRUAN and d0 + 5 < len(hh):
            r[d0 - 5:d0 + 6] -= POLA / 11
            vol[d0:] *= 1.4
        harga[kode] = pd.DataFrame({"Adj Close": 100 * np.exp(np.cumsum(r)), "Volume": vol}, index=hh)
        ipo.append({"kode_emiten": kode, "pencatatan": tgl, "penawaran_mulai": mulai})
    ipo = pd.DataFrame(ipo)
    baca_harga = harga.get
    print(f"🧪 MODE TES: data PALSU {'dgn pola -3% di [-5,+5] & volume +40%' if TES_TIRUAN else 'tanpa pola'}")
else:
    d = pd.read_parquet("data/raw/ipo/detail.parquet")
    ipo = d[(d["status"] == "Closed") & d["pencatatan"].notna() & d["penawaran_mulai"].notna()].copy()
    ipo["kode_emiten"] = ipo["kode_emiten"].astype(str).str.strip().str.upper()

    def baca_harga(kode):
        f = Path(f"data/raw/harga_idx/{kode}.parquet")
        if not f.exists():
            return None
        h = pd.read_parquet(f, columns=["Adj Close", "Volume"])
        h.index = jadi_tanggal(h.index)
        return h[~h.index.duplicated(keep="last")].sort_index()

    kode = Path("riset_15_ramadan.py").read_text(encoding="utf-8").split("# ===== Label kalender =====")[0]
    ns, simpan = {}, sys.argv
    sys.argv = [sys.argv[0]]
    exec(compile(kode, "riset_15_bagian", "exec"), ns)
    sys.argv = simpan
    r_pasar = ns["ret_keranjang"].dropna()

ipo["pencatatan"] = jadi_tanggal(ipo["pencatatan"])
ipo["penawaran_mulai"] = jadi_tanggal(ipo["penawaran_mulai"])
ipo = ipo[ipo["pencatatan"] <= BATAS]
print(f"🔒 Data uji IPO (pencatatan > {BATAS:%Y-%m-%d}) DIKUNCI. Peristiwa latih: {len(ipo)} IPO.\n")
kal = r_pasar.index
idx_pasar = (1 + r_pasar).cumprod()


def peristiwa(bulan):
    out, tanpa = [], []
    for _, r in ipo.iterrows():
        h = baca_harga(r["kode_emiten"])
        if h is None or h.empty:
            tanpa.append(r["kode_emiten"])
            continue
        efektif = r["penawaran_mulai"] - pd.offsets.BDay(1)
        akhir = efektif + pd.DateOffset(months=bulan)
        i0 = int(np.searchsorted(kal, akhir))
        if i0 - 61 < 0 or i0 + 20 >= len(kal) or kal[i0 - 61] < h.index.min():
            continue
        p = h["Adj Close"].reindex(kal).ffill()
        v = h["Volume"].reindex(kal).fillna(0)
        baris = {"kode": r["kode_emiten"], "d0": kal[i0]}
        for nama, (a, b) in JENDELA.items():
            rs = p.iloc[i0 + b] / p.iloc[i0 + a] - 1
            rp = idx_pasar.iloc[i0 + b] / idx_pasar.iloc[i0 + a] - 1
            baris[nama] = float(np.clip(rs - rp, -0.5, 0.5))
        sebelum, sesudah = v.iloc[i0 - 60:i0 - 20].mean(), v.iloc[i0:i0 + 21].mean()
        baris["vol"] = np.log((sesudah + 1) / (sebelum + 1))
        out.append(baris)
    return pd.DataFrame(out), tanpa


e, tanpa = peristiwa(8)
print(f"Peristiwa dipakai: {len(e)} (tanpa harga: {len(tanpa)}; sisanya terlalu dekat pencatatan/akhir data); d0 {e['d0'].min():%Y-%m-%d} s/d {e['d0'].max():%Y-%m-%d}")
hasil = {}
for nama in JENDELA:
    x = e[nama]
    hasil[nama] = t_rata(x)
    print(f"   {nama:15}: rata-rata {x.mean():+.2%}  t {hasil[nama]:+.2f} | median {x.median():+.2%}, negatif {(x < 0).mean():.0%}")
print(f"   info VOLUME log([0,+20]/[-60,-21]) : {e['vol'].mean():+.3f} (x{np.exp(e['vol'].mean()):.2f})  t {t_rata(e['vol']):+.2f}")
pl, _ = peristiwa(6)
print(f"   info PLASEBO (efektif + 6 bln) CAR[-5,+5]: {pl['U1 CAR[-5,+5]'].mean():+.2%}  t {t_rata(pl['U1 CAR[-5,+5]']):+.2f} | "
      f"volume {pl['vol'].mean():+.3f} t {t_rata(pl['vol']):+.2f}  ({len(pl)} peristiwa)")
lolos = [n for n, t in hasil.items() if abs(t) > 3]
print(f"\n   KEPUTUSAN #56 (|t| > 3): {'✅ ' + ', '.join(lolos) if lolos else '❌ tidak ada yang lolos'}")
