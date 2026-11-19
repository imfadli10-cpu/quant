import sys
import requests
from pathlib import Path

KUNCI = Path("kunci_bps.txt").read_text().strip()
kata = " ".join(sys.argv[1:]) or "inflasi"

r = requests.get("https://webapi.bps.go.id/v1/api/list",
                 params={"model": "var", "domain": "0000", "keyword": kata, "key": KUNCI},
                 timeout=60)
print(f"Status: HTTP {r.status_code}")
hasil = r.json()

try:
    halaman, daftar = hasil["data"][0], hasil["data"][1]
    print(f"🔎 '{kata}': {halaman.get('total', len(daftar))} data ditemukan (ditampilkan {len(daftar)})\n")
    for v in daftar:
        print(f"  [{v['var_id']}] {v['title']}  ({v.get('unit', '-')})")
except (KeyError, IndexError, TypeError):
    print("⚠️ Format jawaban tidak terduga. Ini 500 karakter pertamanya:")
    print(str(hasil)[:500])