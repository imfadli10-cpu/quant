"""
RISET #33: EKSPOR CURAH KERING PELABUHAN KALIMANTAN (IMF PortWatch, sinyal kapal) -> SAHAM BATU BARA IDX vs PASAR
==============================================================================================================

DUGAAN (ditulis 2026-11-21 SEBELUM histori pelabuhan selesai diunduh & SEBELUM dilihat; di-commit sebelum dijalankan)
-------------------------------------------------------------------------------------------------------------------
Batu bara Indonesia diekspor lewat pelabuhan & titik muat di Kalimantan dengan kapal CURAH KERING. Volume muat dari data kapal
(AIS) terlihat ~1 minggu setelah kejadian, jauh sebelum laporan produksi kuartalan emiten & data ekspor BPS (~1 bulan).
  H: pertumbuhan volume ekspor curah kering Kalimantan (dibanding tahun lalu) -> saham batu bara lebih baik dari pasar
     sesudahnya (pasar belum menyerap informasi volume). Dua arah diuji (volume tinggi bisa juga berarti harga sedang jatuh).
Perkiraan jujur: harga batu bara (Newcastle) mendominasi saham batu bara & volume relatif stabil; saya kira t < 2.

DATA: PortWatch `raw/histori/pelabuhan/<tahun>` + harian; pelabuhan Indonesia (ISO3 IDN) di kotak KALIMANTAN (bujur 108..119,
  lintang -4,5..4,5; koordinat dari layanan PortWatch_ports_database); kolom export_dry_bulk (ton) dijumlah per minggu.
  SINYAL minggu w = log(jumlah 4 minggu s/d w-2) - log(jumlah 4 minggu yang sama setahun lalu) (jeda 2 minggu: data PortWatch
  terlambat ~1 minggu; pertumbuhan tahunan menghapus musim).
  TARGET: keranjang batu bara (PTBA, ITMG, ADRO, BUMI, INDY, HRUM; yang punya harga) - keranjang 30 saham paling likuid.
PEMBAGIAN SENDIRI (semua data PortWatch >= 2019; ditetapkan sekarang): LATIH minggu sinyal 2020-01..2022-12 (2019 habis untuk
  pertumbuhan tahunan), UJI 2023+ DIKUNCI (--buka-uji sekali, hanya kalau latih lolos).
UJI (2; |t| > 3; dua arah):
  U1 (BATUBARA - PASAR) minggu w+1 pada sinyal (t robust White).
  U2 (BATUBARA - PASAR) 4 minggu w+1..w+4 TANPA tumpang tindih (tiap minggu ke-4) pada sinyal.
Uji kode: --tes-tiruan & --tes-kosong.
"""
import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd

AWAL_LATIH, AKHIR_LATIH = pd.Timestamp("2020-01-01"), pd.Timestamp("2022-12-31")
BUKA_DATA_UJI = "--buka-uji" in sys.argv
TES_TIRUAN, TES_KOSONG = "--tes-tiruan" in sys.argv, "--tes-kosong" in sys.argv
P = "W-FRI"
BATUBARA = ["PTBA", "ITMG", "ADRO", "BUMI", "INDY", "HRUM"]
KOTAK = (108, 119, -4.5, 4.5)
src30 = Path("riset_30_tga.py").read_text(encoding="utf-8")
exec(compile(src30[src30.index("def t_robust"):src30.index("def sinyal_tga")], "riset_30_fungsi", "exec"))
src29 = Path("riset_29_kredit_bank.py").read_text(encoding="utf-8")
_a = src29.index("def jadi_tanggal")                      # cari penanda SESUDAH fungsi (teks yang sama muncul lebih awal di file #29)
exec(compile(src29[_a:src29.index("\nif TES_TIRUAN or TES_KOSONG:", _a)], "riset_29_fungsi", "exec"))


def sinyal_dari_volume(vol_mingguan):
    roll = vol_mingguan.rolling(4, min_periods=4).sum()
    return np.log(roll.shift(2)) - np.log(roll.shift(2 + 52))


if TES_TIRUAN or TES_KOSONG:
    acak = np.random.default_rng(33)
    mg = pd.period_range("2019-01-04", "2026-11-13", freq=P)
    lv = np.zeros(len(mg))
    for i in range(1, len(mg)):
        lv[i] = 0.9 * lv[i - 1] + acak.normal(0, 0.08)
    vol = pd.Series(1e6 * np.exp(lv + 0.1 * np.sin(np.arange(len(mg)) * 2 * np.pi / 52)), index=mg)
    sinyal = sinyal_dari_volume(vol)
    y1 = pd.Series(acak.normal(0, 0.03, len(mg)), index=mg)
    if TES_TIRUAN:
        y1 = y1 + 0.05 * sinyal.fillna(0)                       # +0,5% per +0,1 log pertumbuhan
    print(f"🧪 MODE TES: data PALSU {'dengan pola (+0,5% per +0,1)' if TES_TIRUAN else 'tanpa pola'}")
else:
    ref = pd.read_parquet("data/ref/pelabuhan_portwatch.parquet")
    x0, x1, yy0, yy1 = KOTAK
    kal = ref[(ref["ISO3"] == "IDN") & ref["lon"].between(x0, x1) & ref["lat"].between(yy0, yy1)]["portid"]
    bag = [pd.read_parquet(f, columns=["date", "portid", "export_dry_bulk"]) for f in
           sorted(glob.glob("data/raw/histori/pelabuhan/*.parquet")) + sorted(glob.glob("data/raw/harian/pelabuhan/*.parquet"))]
    pel = pd.concat(bag).drop_duplicates(["date", "portid"], keep="last")
    pel = pel[pel["portid"].isin(set(kal))]
    harian = pel.groupby("date")["export_dry_bulk"].sum()
    harian.index = pd.DatetimeIndex(harian.index)
    vol = harian.groupby(harian.index.to_period(P)).sum()
    vol = vol[vol.index.end_time.normalize() <= harian.index.max()]            # buang minggu belum lengkap
    sinyal = sinyal_dari_volume(vol)
    print(f"🚢 {len(kal)} pelabuhan Kalimantan; ekspor curah kering mingguan {vol.index.min()} s/d {vol.index.max()} "
          f"(median {vol.median() / 1e6:.2f} juta ton/minggu)")
    kode = Path("riset_15_ramadan.py").read_text(encoding="utf-8").split("# ===== Label kalender =====")[0]
    ns, simpan = {}, sys.argv
    sys.argv = [sys.argv[0]]
    exec(compile(kode, "riset_15_bagian", "exec"), ns)
    sys.argv = simpan
    r_pasar = ns["ret_keranjang"].dropna()
    r_bb, ada = ret_keranjang_harian(BATUBARA)
    print(f"   saham batu bara dengan harga: {', '.join(ada)}")
    y1 = mingguan_dari_harian((r_bb.reindex(r_pasar.index).fillna(0) - r_pasar))

akhir = pd.Series([(w + 2).end_time.normalize() for w in y1.index], index=y1.index)
awal = pd.Series([w.start_time for w in y1.index], index=y1.index)
if BUKA_DATA_UJI:
    pilih = (awal > AKHIR_LATIH).values
else:
    pilih = ((awal >= AWAL_LATIH) & (akhir <= AKHIR_LATIH)).values
print(f"🔒 Data uji (2023+) {'DIBUKA' if BUKA_DATA_UJI else 'DIKUNCI'}.\n")
y = y1[pilih]
b, t, n = t_robust(y, sinyal.reindex(y.index))
print(f"   U1 BATUBARA-PASAR minggu depan: +0,1 log pertumbuhan volume -> {b * 0.1:+.3%}, t robust {t:+.1f} ({n} minggu)")
akhir4 = pd.Series([(w + 5).end_time.normalize() for w in y1.index], index=y1.index)   # jendela 4 minggu selesai di w+5
pilih4 = (awal > AKHIR_LATIH).values if BUKA_DATA_UJI else ((awal >= AWAL_LATIH) & (akhir4 <= AKHIR_LATIH)).values
y4 = sum(y1.shift(-k) for k in range(4))[pilih4].dropna().iloc[::4]   # (ditemukan cek hapus-2023+: dulu bocor ke 2023)
b, t, n = t_robust(y4, sinyal.reindex(y4.index))
print(f"   U2 BATUBARA-PASAR 4 minggu (tanpa tumpang tindih): +0,1 -> {b * 0.1:+.3%}, t robust {t:+.1f} ({n} titik)")
