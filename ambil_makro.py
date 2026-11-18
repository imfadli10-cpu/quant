import os
import time
import requests
import pandas as pd
from pathlib import Path


KUNCI = os.environ.get("FRED_API_KEY") or Path("kunci_fred.txt").read_text().strip()

# Kode FRED : keterangan
SERI = {
    # ===== Suku bunga AS =====
    "DFF":          "Suku bunga The Fed (harian)",
    "DGS3MO":       "Yield obligasi AS 3 bulan",
    "DGS2":         "Yield obligasi AS 2 tahun",
    "DGS10":        "Yield obligasi AS 10 tahun",
    "DGS30":        "Yield obligasi AS 30 tahun",
    "T10Y2Y":       "Selisih yield 10th - 2th (sinyal resesi)",
    "T10YIE":       "Ekspektasi inflasi 10 tahun (breakeven)",
    "DFII10":       "Yield riil 10 tahun (setelah inflasi)",
    "SOFR":         "Suku bunga antarbank AS (SOFR)",
    "MORTGAGE30US": "Bunga KPR AS 30 tahun",
    # ===== Inflasi, uang beredar, likuiditas The Fed =====
    "CPIAUCSL":     "Inflasi AS (CPI)",
    "CPILFESL":     "Inflasi inti AS (tanpa pangan & energi)",
    "PCEPILFE":     "Inflasi inti PCE (acuan The Fed)",
    "M2SL":         "Uang beredar M2 AS",
    "WALCL":        "Total aset neraca The Fed",
    "RRPONTSYD":    "Reverse repo The Fed (likuiditas berlebih)",
    "WTREGEN":      "Saldo kas pemerintah AS di The Fed",
    # ===== Tenaga kerja & aktivitas ekonomi AS =====
    "UNRATE":       "Tingkat pengangguran AS",
    "PAYEMS":       "Jumlah pekerja non-pertanian AS",
    "ICSA":         "Klaim pengangguran baru (mingguan)",
    "CCSA":         "Klaim pengangguran lanjutan (mingguan)",
    "JTSJOL":       "Lowongan kerja AS",
    "INDPRO":       "Produksi industri AS",
    "RSAFS":        "Penjualan ritel AS",
    "HOUST":        "Rumah baru dibangun AS",
    "PERMIT":       "Izin bangun rumah AS",
    "DGORDER":      "Pesanan barang tahan lama AS",
    "TOTALSA":      "Penjualan kendaraan AS",
    "UMCSENT":      "Sentimen konsumen Michigan",
    # ===== Risiko, stres & ketidakpastian =====
    "VIXCLS":       "VIX - indeks ketakutan pasar",
    "BAMLH0A0HYM2": "Selisih bunga obligasi sampah (risiko kredit)",
    "BAMLC0A0CM":   "Selisih bunga obligasi perusahaan layak investasi",
    "STLFSI4":      "Indeks stres keuangan St. Louis (mingguan)",
    "NFCI":         "Indeks kondisi keuangan Chicago (mingguan)",
    "USEPUINDXD":   "Indeks ketidakpastian kebijakan ekonomi AS (harian)",
    "DRCCLACBS":    "Tunggakan kartu kredit AS",
    # ===== Kurs mata uang (harian) =====
    "DTWEXBGS":     "Indeks kekuatan dolar AS",
    "DEXJPUS":      "Yen Jepang per USD",
    "DEXUSEU":      "USD per Euro",
    "DEXUSUK":      "USD per Poundsterling",
    "DEXCHUS":      "Yuan Tiongkok per USD",
    "DEXSZUS":      "Franc Swiss per USD",
    "DEXKOUS":      "Won Korea per USD",
    "DEXINUS":      "Rupee India per USD",
    "DEXSIUS":      "Dolar Singapura per USD",
    "DEXMAUS":      "Ringgit Malaysia per USD",
    "DEXTHUS":      "Baht Thailand per USD",
    "DEXBZUS":      "Real Brasil per USD",
    "DEXCAUS":      "Dolar Kanada per USD",
    "DEXUSAL":      "USD per Dolar Australia",
    "DEXMXUS":      "Peso Meksiko per USD",
    # ===== Yield obligasi 10 tahun negara lain (bulanan) =====
    "IRLTLT01DEM156N": "Yield obligasi Jerman 10 tahun",
    "IRLTLT01JPM156N": "Yield obligasi Jepang 10 tahun",
    "IRLTLT01GBM156N": "Yield obligasi Inggris 10 tahun",
    "IRLTLT01KRM156N": "Yield obligasi Korea 10 tahun",
    "IRLTLT01AUM156N": "Yield obligasi Australia 10 tahun",
    # ===== Energi =====
    "DCOILWTICO":   "Harga minyak WTI (harian)",
    "DCOILBRENTEU": "Harga minyak Brent (harian)",
    "DHHNGSP":      "Harga gas alam Henry Hub (harian)",
    "GASREGW":      "Harga bensin eceran AS (mingguan)",
    # ===== Komoditas dunia (bulanan, data IMF) =====
    "PNICKUSDM":    "Harga nikel",
    "PTINUSDM":     "Harga timah",
    "PPOILUSDM":    "Harga minyak sawit",
    "PCOALAUUSDM":  "Harga batu bara Australia",
    "PRUBBUSDM":    "Harga karet",
    "PCOPPUSDM":    "Harga tembaga",
    "PALUMUSDM":    "Harga aluminium",
    "PIORECRUSDM":  "Harga bijih besi",
    "PCOFFOTMUSDM": "Harga kopi",
    "PCOCOUSDM":    "Harga kakao",
    "PWHEAMTUSDM":  "Harga gandum",
    "PMAIZMTUSDM":  "Harga jagung",
    "PSOYBUSDM":    "Harga kedelai",
    # ===== Indonesia =====
    "IDNCPIALLMINMEI":  "Inflasi Indonesia (CPI)",
    "IRSTCI01IDM156N":  "Suku bunga jangka pendek Indonesia",
}

folder = Path("data/raw/makro")
folder.mkdir(parents=True, exist_ok=True)
Path("data/ref").mkdir(parents=True, exist_ok=True)


def ambil(kode):
    """Ambil satu seri dari FRED API, coba ulang sampai 3 kali kalau gagal."""
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {"series_id": kode, "api_key": KUNCI, "file_type": "json"}
    for percobaan in range(1, 4):
        try:
            r = requests.get(url, params=params, timeout=60)
            r.raise_for_status()
            return r.json()["observations"]
        except Exception as e:
            print(f"   ⏳ {kode} gagal (percobaan {percobaan}/3): {type(e).__name__}")
            time.sleep(5)
    return None


for kode, ket in SERI.items():
    data = ambil(kode)
    if data is None:
        print(f"❌ {kode}: tetap gagal setelah 3 kali")
        continue

    df = pd.DataFrame(data)[["date", "value"]]
    df["date"] = pd.to_datetime(df["date"])
    df["nilai"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.set_index("date")[["nilai"]].dropna()

    df.to_parquet(folder / f"{kode}.parquet")
    print(f"✅ {kode}: {len(df)} data, {df.index[0].date()} s/d {df.index[-1].date()}  ({ket})")
    time.sleep(1)

pd.Series(SERI, name="keterangan").to_csv("data/ref/katalog_makro.csv")
print("\nSelesai!")