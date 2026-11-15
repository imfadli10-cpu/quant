import yfinance as yf

data = yf.download("^JKSE", period="max", interval="1d", progress=False)
print(data.tail())
print("Jumlah baris:", len(data))
data.to_csv("ihsg.csv")
print("Tersimpan ke ihsg.csv")