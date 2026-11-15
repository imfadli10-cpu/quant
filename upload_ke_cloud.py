import os
from pathlib import Path
from huggingface_hub import HfApi

token = os.environ.get("HF_TOKEN") or Path("kunci_hf.txt").read_text().strip()

api = HfApi(token=token)

nama_akun = api.whoami()["name"]
repo = f"{nama_akun}/quant-data"

# Buat gudang data (private = hanya kamu yang bisa lihat)
api.create_repo(repo, repo_type="dataset", private=True, exist_ok=True)

# Upload seluruh isi folder data
api.upload_folder(
    folder_path="data",
    repo_id=repo,
    repo_type="dataset",
    commit_message="Upload data harga, makro, cuaca",
)
print(f"\n✅ Selesai! Lihat di: https://huggingface.co/datasets/{repo}")