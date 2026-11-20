"""
RISET #12b: MEMBUKA DATA UJI (2019+) - HANYA untuk kandidat S2 "dekat puncak 52 minggu"
=====================================================================================

Rencana & kriteria ditetapkan di CLAUDE.md (commit a7e92f7, 20 Nov 2026) SEBELUM data uji dibuka:
  - Strategi PERSIS seperti di data latih (riset_12): semesta riset #2, S2 = harga / tertinggi 250 hari,
    beli 20% teratas tiap akhir bulan, beli tutup hari bursa pertama bulan berikutnya, tahan 1 bulan, biaya 0,4%
    x porsi diganti, dibanding semesta (tanpa biaya).
  - LOLOS kalau rata-rata bersih > 0 DAN t > 2. Versi 50 saham paling likuid & biaya 0,8% = informasi saja.
  - Dibuka SEKALI. Kalau gagal, S2 dibuang sebagai strategi tunggal (tidak boleh dicoba variasi lain di data ini).
Skrip ini sengaja HANYA menghitung S2 di data uji (sinyal lain & gabungan TIDAK dihitung -> data uji mereka tetap
belum tersentuh). Kode diambil langsung dari riset_12_gabung_sinyal.py supaya definisinya identik.
"""
import sys
from pathlib import Path

sys.argv = [sys.argv[0], "--buka-uji"]          # paksa mode data uji untuk kode riset_12
kode = Path("riset_12_gabung_sinyal.py").read_text(encoding="utf-8")
persiapan = kode.split("baris, korelasi, lalu = [], [], {}")[0]                    # data, saringan, sinyal (tanpa loop utama)
fungsi_s2 = "nilai_bln = " + kode.split("nilai_bln = ")[1].split("for nama, kw in")[0]   # definisi strategi_s2 yang sama
exec(compile(persiapan + "\n" + fungsi_s2, "riset_12_bagian", "exec"))

print("\n" + "=" * 78)
print("🔓 DATA UJI DIBUKA - HANYA S2 (dekat puncak 52 minggu)")
print("=" * 78)
hasil = {}
for nama, kw in [("UTAMA (kriteria)", {}), ("50 saham paling likuid (info)", {"likuid_teratas": 50}),
                 ("biaya 0,8% (info)", {"biaya": 0.008})]:
    h = strategi_s2(**kw)
    hasil[nama] = h
    t_bersih = nilai_t(h["bersih"])
    print(f"   {nama:32} {len(h)} bln ({h.index[0]:%Y-%m} s/d {h.index[-1]:%Y-%m}) | bersih {h['bersih'].mean():+.2%}/bln "
          f"t {t_bersih:+.1f} | ~{(1 + h['bersih'].mean()) ** 12 - 1:+.1%}/thn | menang {(h['bersih'] > 0).mean():.0%} | "
          f"IC t {nilai_t(h['ic']):+.1f}")
u = hasil["UTAMA (kriteria)"]["bersih"]
lolos_uji = u.mean() > 0 and nilai_t(u) > 2
print(f"\n   KEPUTUSAN (kriteria ditetapkan sebelumnya: rata-rata > 0 DAN t > 2): "
      f"{'✅ LOLOS' if lolos_uji else '❌ GAGAL'}")
print("\n   Per tahun (versi UTAMA, bersih vs semesta):")
th = u.groupby(u.index.year).agg(["mean", "count"])
print("   " + "  ".join(f"{t}: {r['mean']:+.2%} ({int(r['count'])} bln)" for t, r in th.iterrows()))
