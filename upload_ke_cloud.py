import os
import time
from pathlib import Path
from huggingface_hub import HfApi

token = os.environ.get("HF_TOKEN") or Path("kunci_hf.txt").read_text().strip()

api = HfApi(token=token)

nama_akun = api.whoami()["name"]
repo = f"{nama_akun}/quant-data"

# Buat gudang data (private = hanya kamu yang bisa lihat)
api.create_repo(repo, repo_type="dataset", private=True, exist_ok=True)

# Upload seluruh isi folder data. Coba ulang kalau gagal: beberapa workflow (harian, histori, berita) bisa upload
# bersamaan -> Hugging Face kadang menolak sementara (429 / konflik commit). Gagal di sini = data hari itu tidak tersimpan.
for percobaan in range(6):
    try:
        api.upload_folder(
            folder_path="data",
            repo_id=repo,
            repo_type="dataset",
            commit_message="Upload data harga, makro, cuaca",
        )
        break
    except Exception as e:
        if percobaan == 5:
            raise
        tunggu = 120 * (percobaan + 1)
        print(f"⚠️  upload gagal ({type(e).__name__}: {str(e)[:150]}), coba lagi {tunggu} detik lagi...")
        time.sleep(tunggu)
print(f"\n✅ Selesai! Lihat di: https://huggingface.co/datasets/{repo}")
