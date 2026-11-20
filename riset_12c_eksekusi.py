"""
RISET #12c: UJI EKSEKUSI REALISTIS untuk strategi S2 (dekat puncak 52 minggu)
============================================================================

Strategi TIDAK diubah (persis riset_12/12b). Yang diukur = gesekan dunia nyata yang belum dihitung:
  1. SPREAD: perkiraan Corwin-Schultz (2012) dari High/Low harian 21 hari sebelum beli, dibanding batas bawah
     1 tick / harga (aturan fraksi harga IDX sekarang: <200: 1, <500: 2, <2000: 5, <5000: 10, >=5000: 25).
     Biaya per saham yang diganti = 0,4% (komisi+pajak) + max(spread CS, tick/harga).
     Catatan: harga Yahoo sudah disesuaikan split -> harga lama terlihat lebih kecil -> tick/harga terlalu BESAR
     (konservatif = biaya dilebih-lebihkan, bukan dikurangi).
  2. TERKUNCI ARA/ARB: hari beli dengan return >= +19% DAN tutup = harga tertinggi = kemungkinan terkunci ARA (tidak ada
     penjual -> tidak bisa dibeli). Saham ini DIKELUARKAN dari portofolio bulan itu. Hari jual dengan return <= -6,9%
     DAN tutup = terendah = kemungkinan terkunci ARB (tidak bisa dijual); frekuensinya dilaporkan.
  3. KAPASITAS: ambil maksimal 5% dari median nilai transaksi harian tiap saham. Ukuran portofolio maksimal (bobot sama)
     = jumlah saham x persentil-10 kapasitas per saham (90% saham masih muat).
Ditetapkan 20 Nov 2026 sebelum dijalankan. Dijalankan untuk data latih DAN uji (data uji S2 sudah dibuka di #12b).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

kode_riset = Path("riset_12_gabung_sinyal.py").read_text(encoding="utf-8")
persiapan = kode_riset.split("baris, korelasi, lalu = [], [], {}")[0]
KOMISI = 0.004
PARTISIPASI = 0.05


def tick(harga):
    return np.select([harga < 200, harga < 500, harga < 2000, harga < 5000], [1, 2, 5, 10], 25)


def corwin_schultz(tinggi, rendah):
    """Perkiraan spread harian dari High/Low dua hari berturut-turut (nilai negatif -> 0)."""
    k = 3 - 2 * np.sqrt(2)
    hl = np.log(tinggi / rendah) ** 2
    beta = hl + hl.shift(1)
    gamma = np.log(np.maximum(tinggi, tinggi.shift(1)) / np.minimum(rendah, rendah.shift(1))) ** 2
    alpha = (np.sqrt(2 * beta) - np.sqrt(beta)) / k - np.sqrt(gamma / k)
    s = 2 * (np.exp(alpha) - 1) / (1 + np.exp(alpha))
    return s.clip(lower=0)


def jalankan(buka_uji):
    g = {}
    sys.argv = [sys.argv[0]] + (["--buka-uji"] if buka_uji else [])
    exec(compile(persiapan, "riset_12_bagian", "exec"), g)
    adj, tutup, hari = g["adj"], g["tutup"], g["hari"]
    # High/Low harian (tambahan, tidak ada di riset_12)
    tinggi, rendah = {}, {}
    for f in sorted(Path("data/raw/harga_idx").glob("*.parquet")):
        d = pd.read_parquet(f, columns=["High", "Low"])
        d.index = g["jadi_tanggal"](d.index)
        d = d[~d.index.duplicated(keep="last")]
        tinggi[f.stem], rendah[f.stem] = d["High"], d["Low"]
    tinggi = pd.DataFrame(tinggi).reindex(index=hari, columns=adj.columns)
    rendah = pd.DataFrame(rendah).reindex(index=hari, columns=adj.columns)
    sah = (tinggi > 0) & (rendah > 0) & (tinggi >= rendah) & g["aktif"]
    cs = corwin_schultz(tinggi.where(sah), rendah.where(sah)).rolling(21, min_periods=10).mean()
    ret_h = g["ret_h"]
    kunci_ara = (ret_h >= 0.19) & (tutup >= tinggi * 0.999)
    kunci_arb = (ret_h <= -0.069) & (tutup <= rendah * 1.001)
    nilai = g["median_nilai"]

    akhir_bulan, awal_bulan = g["akhir_bulan"], g["awal_bulan"]
    pilih, lolos, sinyal, ret_pegang = g["pilih"], g["lolos"], g["sinyal"], g["ret_pegang"]
    baris, lalu = [], set()
    for i in np.where(pilih)[0]:
        ok = lolos.loc[i] & ret_pegang.loc[i].notna()
        for k in sinyal:
            ok &= sinyal[k].loc[i].notna()
        if ok.sum() < g["MIN_SAHAM"]:
            continue
        r = ret_pegang.loc[i][ok]
        s = sinyal["S2"].loc[i][ok]
        atas = list(s.index[pd.qcut(s.rank(method="first"), 5, labels=False) == 4])
        tgl_akhir, tgl_beli, tgl_jual = akhir_bulan[i], awal_bulan[i + 1], awal_bulan[i + 2]
        terkunci = [k for k in atas if kunci_ara.at[tgl_beli, k]]
        bisa = [k for k in atas if k not in terkunci]
        tak_jual = sum(bool(kunci_arb.at[tgl_jual, k]) for k in bisa)
        spread = cs.loc[tgl_akhir, bisa]
        tk = pd.Series(tick(tutup.loc[tgl_akhir, bisa].values) / tutup.loc[tgl_akhir, bisa].values, index=bisa)
        biaya_nama = KOMISI + np.maximum(spread.fillna(tk), tk)
        baru = [k for k in bisa if k not in lalu]
        porsi_baru = len(baru) / len(bisa) if lalu else 1.0
        biaya = biaya_nama[baru].mean() * porsi_baru if baru else 0.0
        kap = (nilai.loc[tgl_akhir, bisa] * PARTISIPASI)
        baris.append({"tanggal": tgl_akhir, "n": len(atas), "terkunci_ara": len(terkunci) / len(atas),
                      "tak_bisa_jual": tak_jual / len(bisa), "spread_cs": spread.median(), "tick": tk.median(),
                      "biaya_bln": biaya, "biaya_lama": porsi_baru * KOMISI,
                      "kotor_lama": r[atas].mean() - r.mean(), "kotor_bisa": r[bisa].mean() - r.mean(),
                      "kapasitas": len(bisa) * kap.quantile(0.10), "nilai_median": nilai.loc[tgl_akhir, bisa].median()})
        lalu = set(bisa)
    return pd.DataFrame(baris).set_index("tanggal")


def nilai_t(s):
    s = pd.Series(s).dropna()
    return s.mean() / (s.std(ddof=1) / np.sqrt(len(s)))


for label, uji in [("DATA LATIH 2005-2018", False), ("DATA UJI 2019-2026", True)]:
    d = jalankan(uji)
    lama = d["kotor_lama"] - d["biaya_lama"]
    realistis = d["kotor_bisa"] - d["biaya_bln"]
    print(f"\n{'=' * 80}\n📊 {label}: {len(d)} bulan, {d['n'].median():.0f} saham per bulan")
    print(f"   Perkiraan spread Corwin-Schultz (median saham pilihan): {d['spread_cs'].median():.2%} | "
          f"1 tick / harga: {d['tick'].median():.2%}")
    print(f"   Saham pilihan kemungkinan TERKUNCI ARA saat beli: {d['terkunci_ara'].mean():.1%} | "
          f"terkunci ARB saat jual: {d['tak_bisa_jual'].mean():.1%}")
    print(f"   Biaya per bulan: asumsi lama {d['biaya_lama'].mean():.2%} -> realistis {d['biaya_bln'].mean():.2%}")
    print(f"   Bersih ASUMSI LAMA (0,4%)            : {lama.mean():+.2%}/bln  t {nilai_t(lama):+.1f}")
    print(f"   Bersih REALISTIS (spread + tanpa ARA): {realistis.mean():+.2%}/bln  t {nilai_t(realistis):+.1f}  "
          f"(~{(1 + realistis.mean()) ** 12 - 1:+.1%}/thn, menang {(realistis > 0).mean():.0%})")
    print(f"   Kapasitas (5% nilai transaksi harian, 90% saham muat): median Rp {d['kapasitas'].median() / 1e9:.1f} miliar "
          f"per transaksi (min Rp {d['kapasitas'].min() / 1e6:.0f} juta); median nilai transaksi harian saham pilihan "
          f"Rp {d['nilai_median'].median() / 1e9:.1f} miliar")
