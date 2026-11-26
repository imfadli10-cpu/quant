# Pra-registrasi #56: berakhirnya lock-up 8 bulan saham IPO IDX (studi peristiwa)

Ditulis 26 Nov 2026 SEBELUM harga di sekitar tanggal lock-up dilihat. Detail desain di docstring `riset_56_lockup.py`.
Literatur: Field & Hanka (2001, JF) volume +40% permanen & CAR 3 hari −1,5%; aturan BEI POJK 25/POJK.04/2017 (kunci 8 bulan sejak efektif).

- Peristiwa: 134 IPO latih (pencatatan ≤ 2023-06-30, pembagian sama dgn #28); IPO sesudahnya = data uji DIKUNCI.
- Uji (|t| > 3): U1 CAR[−5,+5], U2 CAR[−20,−1], U3 CAR[0,+20] vs keranjang 30, dibatasi ±50%. Info: volume, plasebo +6 bulan.
- Keputusan: lolos = kandidat SARINGAN HINDARI untuk portofolio; gagal = belum terbukti (daya uji rendah).

## Tes kode (IPO palsu, sb harian 4%)
| Tes | U1 CAR[−5,+5] | volume |
|---|---|---|
| kosong | +1,24% t +1,07 | ×1,00 |
| pola −3% | −1,76% t −1,57 | ×1,40 |
| pola −6% | −4,68% t −4,30 | ×1,40 |

DAYA UJI RENDAH (diakui di depan): hanya efek ≳ 6% (≈ 4x Field-Hanka) yang bisa lolos |t| > 3 dgn 134 peristiwa.
Versi pertama pembuat data palsu punya drift +σ²/2 (kosong +2,1%) → dikoreksi sebelum data asli.
