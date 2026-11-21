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
    "CCUSSP02IDM650N":  "Kurs rupiah per USD akhir bulan (OECD, sampai 2023; lebih bersih dari Yahoo IDR=X)",
    # ===== Indonesia (tambahan 20 Nov 2026: seri FRED aktif, bulanan & harian + kuartalan utama) =====
    "NASDAQNQID": "[D] NASDAQ Indonesia Index",
    "NASDAQNQID30": "[D] NASDAQ Indonesia Financials Index",
    "NASDAQNQID30LM": "[D] Nasdaq Indonesia Financials Large Mid Cap Index",
    "NASDAQNQID30LMN": "[D] Nasdaq Indonesia Financials Large Mid Cap Net Total Return Index",
    "NASDAQNQID30LMT": "[D] Nasdaq Indonesia Financials Large Mid Cap Total Return Index",
    "NASDAQNQID30N": "[D] NASDAQ Indonesia Financials Net Total Return Index",
    "NASDAQNQID30T": "[D] NASDAQ Indonesia Financials Total Return Index",
    "NASDAQNQID50": "[D] Nasdaq Indonesia Industrials Index",
    "NASDAQNQID50N": "[D] Nasdaq Indonesia Industrials Net Total Return Index",
    "NASDAQNQID50T": "[D] Nasdaq Indonesia Industrials Total Return Index",
    "NASDAQNQID55": "[D] Nasdaq Indonesia Basic Materials Index",
    "NASDAQNQID55N": "[D] Nasdaq Indonesia Basic Materials Net Total Return Index",
    "NASDAQNQID55T": "[D] Nasdaq Indonesia Basic Materials Total Return Index",
    "NASDAQNQIDLC": "[D] NASDAQ Indonesia Large Cap Index",
    "NASDAQNQIDLCN": "[D] NASDAQ Indonesia Large Cap Net Total Return Index",
    "NASDAQNQIDLCT": "[D] NASDAQ Indonesia Large Cap Total Return Index",
    "NASDAQNQIDLM": "[D] NASDAQ Indonesia Large Mid Cap Index",
    "NASDAQNQIDLMN": "[D] NASDAQ Indonesia Large Mid Cap Net Total Return Index",
    "NASDAQNQIDLMT": "[D] NASDAQ Indonesia Large Mid Cap Total Return Index",
    "NASDAQNQIDMC": "[D] NASDAQ Indonesia Mid Cap Index",
    "NASDAQNQIDMCN": "[D] NASDAQ Indonesia Mid Cap Net Total Return Index",
    "NASDAQNQIDMCT": "[D] NASDAQ Indonesia Mid Cap Total Return Index",
    "NASDAQNQIDN": "[D] NASDAQ Indonesia Net Total Return Index",
    "NASDAQNQIDSC": "[D] NASDAQ Indonesia Small Cap Index",
    "NASDAQNQIDSCN": "[D] NASDAQ Indonesia Small Cap Net Total Return Index",
    "NASDAQNQIDSCT": "[D] NASDAQ Indonesia Small Cap Total Return Index",
    "NASDAQNQIDT": "[D] NASDAQ Indonesia Total Return Index",
    "CCRETT01IDM661N": "[M] Financial Market: Real Effective Exchange Rates: CPI Based for Indonesia",
    "CCUSMA02IDM618N": "[M] Currency Conversions: US Dollar Exchange Rate: Average of Daily Rates: National Currency: USD for Indonesia",
    "EXP5600": "[M] U.S. Exports of Goods by F.A.S. Basis to Indonesia",
    "FORLTAGCYNET42218": "[M] Foreign Net Transactions of U.S. Long-Term Agency Bonds: Indonesia",
    "FORLTAGCYPOS42218": "[M] Foreign Portfolio Holdings of U.S. Long-Term Agency Bonds: Indonesia",
    "FORLTAGCYVALCHG42218": "[M] Valuation Change on Foreign Portfolio Holdings of U.S. Long-Term Agency Bonds: Indonesia",
    "FORLTCORPNET42218": "[M] Foreign Net Transactions of U.S. Long-Term Corporate Bonds: Indonesia",
    "FORLTCORPPOS42218": "[M] Foreign Portfolio Holdings of U.S. Long-Term Corporate Bonds: Indonesia",
    "FORLTCORPVALCHG42218": "[M] Valuation Change on Foreign Portfolio Holdings of U.S. Long-Term Corporate Bonds: Indonesia",
    "FORLTEQTYNET42218": "[M] Foreign Net Transactions of U.S. Equity Securities: Indonesia",
    "FORLTEQTYPOS42218": "[M] Foreign Portfolio Holdings of U.S. Equity Securities: Indonesia",
    "FORLTEQTYVALCHG42218": "[M] Valuation Change on Foreign Portfolio Holdings of U.S. Equity Securities: Indonesia",
    "FORLTTOTALNET42218": "[M] Foreign Net Transactions of All U.S. Long-Term Securities: Indonesia",
    "FORLTTOTALPOS42218": "[M] Foreign Portfolio Holdings of All U.S. Long-Term Securities: Indonesia",
    "FORLTTOTALVALCHG42218": "[M] Valuation Change on Foreign Portfolio Holdings of All U.S. Long-Term Securities: Indonesia",
    "FORLTTREASNET42218": "[M] Foreign Net Transactions of U.S. Long-Term Treasury Securities: Indonesia",
    "FORLTTREASPOS42218": "[M] Foreign Portfolio Holdings of U.S. Long-Term Treasury Securities: Indonesia",
    "FORLTTREASVALCHG42218": "[M] Valuation Change on Foreign Portfolio Holdings of U.S. Long-Term Treasury Securities: Indonesia",
    "FORSTTREASNET42218": "[M] Foreign Net Transactions of U.S. Short-Term Treasury Securities: Indonesia",
    "FORSTTREASPOS42218": "[M] Foreign Portfolio Holdings of U.S. Short-Term Treasury Securities: Indonesia",
    "FORTREASNET42218": "[M] Foreign Net Transactions of U.S. Long-Term and Short-Term Treasury Securities: Indonesia",
    "FORTREASPOS42218": "[M] Foreign Portfolio Holdings of U.S. Long-Term and Short-Term Treasury Securities: Indonesia",
    "IDNCSCICP02STSAM": "[M] Consumer Opinion Surveys: Composite Consumer Confidence for Indonesia",
    "IDNLOLITOAASTSAM": "[M] Leading Indicators OECD: Leading Indicators: Composite Leading Indicator: Amplitude Adjusted for Indonesia",
    "IDNSPASTT01GYM": "[M] Share Prices: All Shares/Broad: Total for Indonesia",
    "IDNXTEXVA01NCMLM": "[M] International Merchandise Trade Statistics: Exports: Commodities for Indonesia",
    "IDNXTIMVA01NCMLM": "[M] International Merchandise Trade Statistics: Imports: Commodities for Indonesia",
    "IDNXTNTVA01NCMLM": "[M] International Merchandise Trade Statistics: Trade Balance: Commodities for Indonesia",
    "IMP5600": "[M] U.S. Imports of Goods by Customs Basis from Indonesia",
    "IR3TIB01IDM156N": "[M] Interest Rates: 3-Month or 90-Day Rates and Yields: Interbank Rates: Total for Indonesia",
    "NBIDBIS": "[M] Broad Effective Exchange Rate for Indonesia",
    "RBIDBIS": "[M] Real Broad Effective Exchange Rate for Indonesia",
    "SPASTT01IDM657N": "[M] Share Prices: All Shares/Broad: Total for Indonesia",
    "SPASTT01IDM661N": "[M] Financial Market: Share Prices for Indonesia",
    "TRESEGIDM052N": "[M] Reserves Excluding Gold for Indonesia",
    "TRESEGIDM194N": "[M] Reserves Excluding Gold for Indonesia",
    "USLTBONDNET42218": "[M] U.S. Net Transactions of Foreign Long-Term Corporate and Government Bonds: Indonesia",
    "USLTBONDPOS42218": "[M] U.S. Portfolio Holdings of Foreign Long-Term Corporate and Government Bonds: Indonesia",
    "USLTBONDVALCHG42218": "[M] Valuation Change on U.S. Portfolio Holdings of Foreign Long-Term Corporate and Government Bonds: Indonesia",
    "USLTEQTYNET42218": "[M] U.S. Net Transactions of Foreign Equity Securities: Indonesia",
    "USLTEQTYPOS42218": "[M] U.S. Portfolio Holdings of Foreign Equity Securities: Indonesia",
    "USLTEQTYVALCHG42218": "[M] Valuation Change on U.S. Portfolio Holdings of Foreign Equity Securities: Indonesia",
    "USLTTOTALNET42218": "[M] U.S. Net Transactions of All Foreign Long-Term Securities: Indonesia",
    "USLTTOTALPOS42218": "[M] U.S. Portfolio Holdings of All Foreign Long-Term Securities: Indonesia",
    "USLTTOTALVALCHG42218": "[M] Valuation Change on U.S. Portfolio Holdings of All Foreign Long-Term Securities: Indonesia",
    "VALEXPIDM052N": "[M] Exports of Goods for Indonesia",
    "VALIMPIDM052N": "[M] Imports of Goods for Indonesia",
    "XTEXVA01IDM657S": "[M] International Merchandise Trade Statistics: Exports: Commodities for Indonesia",
    "XTEXVA01IDM659S": "[M] International Merchandise Trade Statistics: Exports: Commodities for Indonesia",
    "XTEXVA01IDM664S": "[M] International Merchandise Trade Statistics: Exports: Commodities for Indonesia",
    "XTEXVA01IDM667N": "[M] International Merchandise Trade Statistics: Exports: Commodities for Indonesia",
    "XTEXVA01IDM667S": "[M] International Merchandise Trade Statistics: Exports: Commodities for Indonesia",
    "XTIMVA01IDM657S": "[M] International Merchandise Trade Statistics: Imports: Commodities for Indonesia",
    "XTIMVA01IDM659S": "[M] International Merchandise Trade Statistics: Imports: Commodities for Indonesia",
    "XTIMVA01IDM664S": "[M] International Merchandise Trade Statistics: Imports: Commodities for Indonesia",
    "XTIMVA01IDM667N": "[M] International Merchandise Trade Statistics: Imports: Commodities for Indonesia",
    "XTIMVA01IDM667S": "[M] International Merchandise Trade Statistics: Imports: Commodities for Indonesia",
    "XTNTVA01IDM664S": "[M] International Merchandise Trade Statistics: Trade Balance: Commodities for Indonesia",
    "XTNTVA01IDM667N": "[M] International Merchandise Trade Statistics: Trade Balance: Commodities for Indonesia",
    "XTNTVA01IDM667S": "[M] International Merchandise Trade Statistics: Trade Balance: Commodities for Indonesia",
    "CRDQIDAPABIS": "[Q] Total Credit to Private Non-Financial Sector, Adjusted for Breaks, for Indonesia",
    "CRDQIDBPUBIS": "[Q] Credit to Private Non-Financial Sector by Domestic Banks, Unadjusted for Breaks, for Indonesia",
    "IDNGDPRQPSMEI": "[Q] National Accounts: GDP by Expenditure: Constant Prices: Gross Domestic Product: Total for Indonesia",
    "NCPHIRNSAXDCIDQ": "[Q] Real Final Consumption Expenditure, Households for Indonesia",
    "NFIRSAXDCIDQ": "[Q] Real Gross Fixed Capital Formation for Indonesia",
    "NGDPRSAXDCIDQ": "[Q] Real Gross Domestic Product (GDP) for Indonesia",
    "NGDPSAXDCIDQ": "[Q] Nominal Gross Domestic Product (GDP) for Indonesia",
    "NMRSAXDCIDQ": "[Q] Real Imports of Goods and Services for Indonesia",
    "NXRSAXDCIDQ": "[Q] Real Exports of Goods and Services for Indonesia",
    "QIDN628BIS": "[Q] Residential Property Prices for Indonesia",
    "QIDR628BIS": "[Q] Real Residential Property Prices for Indonesia",
    "WUIIDN": "[Q] World Uncertainty Index for Indonesia",
    # ===== Tambahan 21 Nov 2026: likuiditas, resesi, kredit, ketidakpastian =====
    "WRESBAL": "Cadangan perbankan di The Fed (mingguan)",
    "WEI": "Weekly Economic Index (indikator ekonomi AS mingguan)",
    "IORB": "Bunga atas cadangan The Fed",
    "T10Y3M": "Selisih yield 10 thn - 3 bln (sinyal resesi klasik)",
    "T5YIE": "Ekspektasi inflasi 5 tahun",
    "DGS1": "Yield obligasi AS 1 tahun",
    "DGS5": "Yield obligasi AS 5 tahun",
    "DFII5": "Yield riil 5 tahun",
    "BAA10Y": "Selisih obligasi korporasi Baa - Treasury 10 thn (histori panjang)",
    "AAA10Y": "Selisih obligasi korporasi Aaa - Treasury 10 thn",
    "USREC": "Penanda resesi AS (NBER)",
    "SAHMREALTIME": "Indikator resesi Sahm (real-time)",
    "CFNAI": "Indeks aktivitas nasional Chicago Fed",
    "RECPROUSM156N": "Probabilitas resesi AS (smoothed)",
    "GEPUCURRENT": "Indeks ketidakpastian kebijakan ekonomi GLOBAL",
    "WLEMUINDXD": "Ketidakpastian pasar saham (harian, dari berita)",
    "ANFCI": "Indeks kondisi keuangan Chicago (disesuaikan)",
    "KCFSI": "Indeks stres keuangan Kansas City",
    "DTB3": "T-bill 3 bulan (harian)",
    "DEXHKUS": "Kurs HKD per USD",
    "DEXTAUS": "Kurs TWD per USD",
    "DEXNOUS": "Kurs NOK per USD",
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