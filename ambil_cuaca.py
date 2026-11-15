import time
import requests
import pandas as pd
from pathlib import Path
from datetime import date, timedelta

# Nama kota: (lintang, bujur, alasan dipilih)
KOTA = {
    # Indonesia
    "jakarta":    (-6.21, 106.85, "Pusat bursa & ekonomi Indonesia"),
    "surabaya":   (-7.25, 112.75, "Kota industri terbesar ke-2"),
    "medan":      (3.59,  98.67,  "Pusat perkebunan Sumatera"),
    "pekanbaru":  (0.51,  101.45, "Sentra kelapa sawit (Riau)"),
    "makassar":   (-5.15, 119.43, "Pusat ekonomi Indonesia timur"),
    # Pusat keuangan dunia
    "new_york":   (40.71, -74.01, "Wall Street"),
    "london":     (51.51, -0.13,  "Pusat keuangan Eropa"),
    "tokyo":      (35.68, 139.69, "Bursa Jepang"),
    "shanghai":   (31.23, 121.47, "Bursa Tiongkok"),
    "singapura":  (1.35,  103.82, "Pusat keuangan Asia Tenggara"),
    # Sentra komoditas
    "kuala_lumpur": (3.14, 101.69, "Bursa sawit dunia"),
    "des_moines": (41.59, -93.62, "Sabuk jagung & kedelai AS"),
    "chicago":    (41.88, -87.63, "Bursa komoditas pertanian"),
    "houston":    (29.76, -95.37, "Pusat industri minyak AS"),
    "minas_gerais": (-19.92, -43.94, "Sentra kopi Brasil"),
}

VARIABEL = ("temperature_2m_max,temperature_2m_min,precipitation_sum,"
            "sunshine_duration,wind_speed_10m_max")

akhir = (date.today() - timedelta(days=7)).isoformat()
folder = Path("data/raw/cuaca")
folder.mkdir(parents=True, exist_ok=True)

# Simpan katalog kota
katalog = pd.DataFrame(KOTA, index=["lintang", "bujur", "alasan"]).T
katalog.to_csv("data/ref/katalog_cuaca.csv")


def ambil(lat, lon):
    """Ambil data cuaca. Kalau kena batas (429), tunggu lalu coba lagi."""
    url = (f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}"
           f"&start_date=1990-01-01&end_date={akhir}&daily={VARIABEL}&timezone=auto")
    for percobaan in range(1, 4):
        r = requests.get(url, timeout=120)
        if r.status_code == 429:
            print(f"   ⏳ Kena batas, tunggu 70 detik (percobaan {percobaan}/3)...")
            time.sleep(70)
            continue
        r.raise_for_status()
        return r.json()["daily"]
    return None   # tetap gagal setelah 3 kali


for nama, (lat, lon, alasan) in KOTA.items():
    file = folder / f"{nama}.parquet"
    if file.exists():
        print(f"⏭️  {nama}: sudah ada, dilewati")
        continue

    harian = ambil(lat, lon)
    if harian is None:
        print(f"\n🛑 Batas pemakaian Open-Meteo tercapai. Jalankan lagi 1 jam lagi,")
        print("   kota yang sudah berhasil tidak akan diambil ulang.")
        break

    df = pd.DataFrame(harian)
    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time")
    df.to_parquet(file)
    print(f"✅ {nama}: {len(df)} hari  ({alasan})")
    time.sleep(65)   # jeda panjang antar-kota supaya tidak kena batas per menit

print("\nSelesai!")