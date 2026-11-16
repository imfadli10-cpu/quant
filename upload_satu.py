import os
import sys
from pathlib import Path
from huggingface_hub import HfApi

REPO = "fadli-sparks/quant-data"
token = os.environ.get("HF_TOKEN") or Path("kunci_hf.txt").read_text().strip()
api = HfApi(token=token)

# Cara pakai: python upload_satu.py data/raw/xxx/file.parquet  (atau sebuah folder)
for jalur in sys.argv[1:]:
    p = Path(jalur)
    tujuan = p.relative_to("data").as_posix()   # data/raw/x → raw/x di gudang
    if p.is_dir():
        api.upload_folder(folder_path=str(p), path_in_repo=tujuan, repo_id=REPO,
                          repo_type="dataset", commit_message=f"Upload {tujuan}")
    else:
        api.upload_file(path_or_fileobj=str(p), path_in_repo=tujuan, repo_id=REPO,
                        repo_type="dataset", commit_message=f"Upload {tujuan}")
    print(f"☁️  {jalur} → {tujuan}")