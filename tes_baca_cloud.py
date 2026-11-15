from pathlib import Path
import pandas as pd

token = Path("kunci_hf.txt").read_text().strip()
GUDANG = "hf://datasets/fadli-sparks/quant-data"

df = pd.read_parquet(f"{GUDANG}/raw/harga/IHSG.parquet",
                     storage_options={"token": token})

print("Data IHSG dibaca langsung dari cloud:")
print(df.tail())
print(f"\nJumlah baris: {len(df)}")