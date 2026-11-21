"""
RISET #29: PERCEPATAN KREDIT PERBANKAN (SEKI BI) -> SAHAM BANK vs PASAR BULAN DEPAN, data LATIH saja
==================================================================================================

DUGAAN (ditulis 2026-11-21 SEBELUM menghitung hubungan apa pun; di-commit sebelum dijalankan)
-----------------------------------------------------------------------------------------
Kredit = mesin pendapatan bank. Kalau pertumbuhan kredit MENINGKAT, laba bank ke depan naik -> saham bank mengungguli pasar
pada bulan-bulan berikutnya (pasar lambat memperbarui perkiraan laba dari data agregat yang terbit terlambat).
Perkiraan jujur: bank besar menerbitkan laporan bulanan sendiri lebih cepat dari SEKI & analis memantau ketat; saya kira t < 2.

DATA: SEKI Tabel I.4 (posisi kredit rupiah & valas Bank Umum + BPR menurut kelompok bank), miliar Rp.
  TOTAL = jumlah 5 kelompok (Persero, BPD, Swasta Nasional, Asing & Campuran, BPR) = definisi 'Jumlah (1 s.d. 5)' BI
  (dicek terhadap baris 'J U M L A H' di lembar 2016-2024). PERSERO = kelompok 1.
  JEDA TERBIT konservatif 2 bulan (sama dengan riset #27). Percepatan a(m) = g(m) - g(m-3), g = pertumbuhan tahunan.
  Sinyal akhir bulan t = a(t-2). Target = return bulan t+1 (sesudah tutup hari bursa pertama t+1 s/d tutup hari bursa pertama t+2).
  BANK = BBRI BMRI BBNI BBTN BBCA BDMN BNGA BNII PNBN BJBR BJTM BNLI (yang punya harga di bulan itu), bobot sama.
  PERSERO = BBRI BMRI BBNI BBTN. PASAR = keranjang 30 saham paling likuid (riset #4/#15).
UJI (3; dua arah; |t| > 3; t robust White):
  U1 (BANK - PASAR) t+1 pada percepatan kredit TOTAL.
  U2 (PERSERO - PASAR) t+1 pada percepatan kredit bank PERSERO.
  U3 PASAR t+1 pada percepatan kredit TOTAL (kredit = siklus ekonomi).
Data uji 2019+ DIKUNCI. Uji kode: --tes-tiruan (+0,3% per +1 pp percepatan) & --tes-kosong.
"""
import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BATAS_LATIH = pd.Timestamp("2018-12-31")
BUKA_DATA_UJI = "--buka-uji" in sys.argv
TES_TIRUAN, TES_KOSONG = "--tes-tiruan" in sys.argv, "--tes-kosong" in sys.argv
JEDA = 2
BANK = ["BBRI", "BMRI", "BBNI", "BBTN", "BBCA", "BDMN", "BNGA", "BNII", "PNBN", "BJBR", "BJTM", "BNLI"]
PERSERO = ["BBRI", "BMRI", "BBNI", "BBTN"]
KELOMPOK = {"persero": r"bank persero", "bpd": r"bank pemerintah daerah", "swasta": r"bank swasta nasional",
            "asing": r"bank asing", "bpr": r"bank perkreditan rakyat"}

exec(compile(Path("riset_27_likuiditas.py").read_text(encoding="utf-8").split("if TES_TIRUAN or TES_KOSONG:")[0]
             .split("BATAS_LATIH = ")[0], "riset_27_impor", "exec"))
fungsi27 = Path("riset_27_likuiditas.py").read_text(encoding="utf-8")
exec(compile(fungsi27[fungsi27.index("def t_robust"):fungsi27.index("if TES_TIRUAN or TES_KOSONG:")], "riset_27_fungsi", "exec"))


def jadi_tanggal(x):
    t = pd.DatetimeIndex(pd.to_datetime(x))
    return (t.tz_localize(None) if t.tz is not None else t).normalize().astype("datetime64[ns]")


def ret_keranjang_harian(kode_list):
    bag = {}
    for k in kode_list:
        f = Path(f"data/raw/harga_idx/{k}.parquet")
        if f.exists():
            d = pd.read_parquet(f, columns=["Adj Close", "Volume"])
            d.index = jadi_tanggal(d.index)
            d = d[~d.index.duplicated(keep="last")]
            bag[k] = d["Adj Close"].where(d["Volume"].fillna(0) > 0)
    sys.path.insert(0, ".")
    from bersih_idx import bersihkan
    adj = bersihkan(pd.DataFrame(bag).sort_index())
    return adj.pct_change(fill_method=None).mean(axis=1), sorted(bag)


if TES_TIRUAN or TES_KOSONG:
    acak = np.random.default_rng(29)
    bln = pd.period_range("1998-01", "2026-09", freq="M")
    tumbuh = 0.012 + np.cumsum(acak.normal(0, 0.004, len(bln))) * 0.15
    total = pd.Series(1000 * np.exp(np.cumsum(tumbuh)), index=bln.to_timestamp())
    persero = pd.Series(400 * np.exp(np.cumsum(tumbuh + acak.normal(0, 0.004, len(bln)))), index=bln.to_timestamp())
    sig_bln = pd.period_range("2002-05", "2026-09", freq="M")
    y_bank = pd.Series(acak.normal(0, 0.04, len(sig_bln)), index=sig_bln)
    y_pers = pd.Series(acak.normal(0, 0.05, len(sig_bln)), index=sig_bln)
    y_pasar = pd.Series(acak.normal(0.01, 0.06, len(sig_bln)), index=sig_bln)
    if TES_TIRUAN:
        y_bank = y_bank + 0.3 * percepatan(total.copy()).shift(JEDA).reindex(sig_bln).fillna(0)
        y_pers = y_pers + 0.3 * percepatan(persero.copy()).shift(JEDA).reindex(sig_bln).fillna(0)
    print(f"🧪 MODE TES: data PALSU {'dengan pola (+0,3% per +1 pp)' if TES_TIRUAN else 'tanpa pola'}")
else:
    sys.path.insert(0, ".")
    from seki import seri_bulanan
    f = sorted(glob.glob("data/raw/seki/*/TABEL1_4.xls"))[-1]
    seri = {k: seri_bulanan(f, p) for k, p in KELOMPOK.items()}
    tabel = pd.DataFrame(seri)
    total = tabel.sum(axis=1, min_count=5)
    persero = tabel["persero"]
    cek = seri_bulanan(f, r"j\s*u\s*m\s*l\s*a\s*h")
    beda = (total.reindex(cek.index) / cek - 1).abs().dropna()
    print(f"📊 kredit: {total.notna().sum()} bulan ({total.dropna().index.min():%Y-%m} s/d {total.dropna().index.max():%Y-%m}); "
          f"cek vs baris JUMLAH BI: {len(beda)} bulan, beda maks {beda.max():.4%}")
    print(f"   pertumbuhan tahunan kredit Des: " + ", ".join(
        f"{t.year}: {v:+.1f}%" for t, v in (total[total.index.month == 12].pct_change() * 100).loc["2005":"2018"].items()))
    kode = Path("riset_15_ramadan.py").read_text(encoding="utf-8").split("# ===== Label kalender =====")[0]
    ns, simpan = {}, sys.argv
    sys.argv = [sys.argv[0]]
    exec(compile(kode, "riset_15_bagian", "exec"), ns)
    sys.argv = simpan
    r_pasar = ns["ret_keranjang"].dropna()
    r_bank, ada_bank = ret_keranjang_harian(BANK)
    r_pers, ada_pers = ret_keranjang_harian(PERSERO)
    print(f"   saham bank dengan harga: {', '.join(ada_bank)}")
    y_pasar = return_bulan_depan(r_pasar)
    y_bank = return_bulan_depan(r_bank.reindex(r_pasar.index).fillna(0)) - y_pasar
    y_pers = return_bulan_depan(r_pers.reindex(r_pasar.index).fillna(0)) - y_pasar

a_total = percepatan(total.copy()).shift(JEDA)
a_pers = percepatan(persero.copy()).shift(JEDA)
akhir_target = pd.Series([(p + 2).start_time for p in y_pasar.index], index=y_pasar.index)
pilih = (akhir_target > BATAS_LATIH + pd.Timedelta(days=1)) if BUKA_DATA_UJI else (akhir_target <= BATAS_LATIH)
pilih = pilih.values
print(f"🔒 Data uji {'DIBUKA' if BUKA_DATA_UJI else 'DIKUNCI'}.\n")
for nama, y, a in [("U1 BANK-PASAR   <- kredit total  ", y_bank, a_total), ("U2 PERSERO-PASAR <- kredit persero", y_pers, a_pers),
                   ("U3 PASAR        <- kredit total  ", y_pasar, a_total)]:
    yy = y[pilih[:len(y)]] if len(y) == len(pilih) else y.reindex(y_pasar.index)[pilih]
    b, t, n = t_robust(yy, a.reindex(yy.index))
    print(f"   {nama}: +1 pp percepatan -> {b * 0.01:+.2%} bulan depan, t robust {t:+.1f} ({n} bulan)")
