"""
Pencocokan kode saham IDX di judul berita EmitenNews (slug). Dipakai riset berita.
Aturan: token slug = kode (huruf kecil). Kode yang juga KATA UMUM (otomatis: muncul bukan-huruf-besar >= 2x di korpus RSS kita;
+ daftar manual hasil pemeriksaan 21 Nov 2026) hanya dihitung kalau salah satu kata nama perusahaan (2 kata penting pertama dari
longName Yahoo, panjang >= 4, bukan kode itu sendiri) juga ada di slug.
"""
import re

import pandas as pd

OTOMATIS = set(['agar', 'ahap', 'aksi', 'aldo', 'aman', 'andi', 'area', 'arta', 'arti', 'arto', 'assa', 'auto', 'awan', 'ayam', 'baik', 'bali', 'bank', 'beli', 'best', 'bles', 'bola', 'buah', 'budi', 'buka', 'bumi', 'city', 'coin', 'cuan', 'data', 'daya', 'dewi', 'east', 'emas', 'eral', 'fast', 'film', 'gold', 'good', 'goto', 'guna', 'ikan', 'indo', 'inta', 'jawa', 'kayu', 'king', 'kota', 'laba', 'laju', 'land', 'life', 'lion', 'main', 'mang', 'mina', 'naik', 'nasi', 'pada', 'pdes', 'pipa', 'pura', 'rafi', 'raja', 'rans', 'roti', 'satu', 'ship', 'sini', 'suri', 'tama', 'tara', 'uang', 'visi'])   # dari korpus RSS 21 Nov 2026 (bukan-huruf-besar >= 2x)
MANUAL = {"jaya", "agro", "mega", "mari", "cash", "heal", "blue", "food", "bird", "bina", "gula", "ratu", "baja", "bull", "link",
          "real", "kopi", "pola", "coal", "palm", "gems", "trim", "dewa", "reli", "pssi", "iata", "wifi", "boga", "amar", "tugu",
          "star", "gold", "auto", "best", "good", "king", "life", "lion", "land", "city", "fast", "east", "film", "main", "kota"}
BUANG = r"\b(pt|tbk|persero|perusahaan|perseroan|the|indonesia|and|dan|group|grup|tbk\.)\b"


def kata_nama(nama, kode):
    n = re.sub(BUANG, " ", str(nama).lower())
    n = [w for w in re.sub(r"[^a-z ]", " ", n).split() if len(w) >= 4 and w != kode]
    return set(n[:2])


def cocokkan(berita, daftar_kode, nama_perusahaan, kata_umum=()):
    """berita: DataFrame (slug, tanggal). daftar_kode: kode huruf kecil. nama_perusahaan: {kode_kecil: longName}.
    Hasil: DataFrame (tanggal, kode_besar, url) satu baris per (artikel, kode)."""
    ambigu = set(kata_umum) | OTOMATIS | MANUAL
    nama = {k: kata_nama(v, k) for k, v in nama_perusahaan.items()}
    kode = set(daftar_kode)
    baris = []
    for url, slug, tgl in zip(berita["url"], berita["slug"], berita["tanggal"]):
        ts = set(str(slug).split("-"))
        for k in ts & kode:
            if k in ambigu and not (nama.get(k, set()) & ts):
                continue
            baris.append((tgl, k.upper(), url))
    return pd.DataFrame(baris, columns=["tanggal", "kode", "url"])
