"""
Cadangkan / pulihkan folder private/ (riset & catatan SENSITIF) ke/dari gudang Hugging Face PRIVATE.

Folder private/ diabaikan git (.gitignore) -> tidak pernah masuk GitHub yang PUBLIK.
Isinya: skrip & catatan untuk sinyal yang terbukti menguntungkan (detail strategi, parameter, hasil).

Cara pakai:
  python simpan_private.py          -> upload private/ ke HF  private/   (hanya menambah/menimpa, tidak menghapus)
  python simpan_private.py --ambil  -> unduh HF private/ ke folder private/ (mis. di laptop baru)
"""
import os
import sys
from pathlib import Path

from huggingface_hub import HfApi, snapshot_download

REPO = "fadli-sparks/quant-data"
token = os.environ.get("HF_TOKEN") or Path("kunci_hf.txt").read_text().strip()
folder = Path("private")

if "--ambil" in sys.argv:
    snapshot_download(REPO, repo_type="dataset", local_dir=".", allow_patterns=["private/*", "private/**"], token=token)
    print(f"⬇️  private/ dipulihkan dari gudang ({sum(1 for _ in folder.rglob('*') if _.is_file())} file)")
    sys.exit()

if not folder.exists() or not any(folder.rglob("*")):
    print("ℹ️  folder private/ kosong, tidak ada yang dicadangkan")
    sys.exit()
HfApi(token=token).upload_folder(folder_path=str(folder), path_in_repo="private", repo_id=REPO, repo_type="dataset",
                                 commit_message="Cadangan private/")
print(f"☁️  private/ dicadangkan ke gudang HF private ({sum(1 for _ in folder.rglob('*') if _.is_file())} file)")
