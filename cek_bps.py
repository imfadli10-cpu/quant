import sys
import json
import requests
from pathlib import Path

KUNCI = Path("kunci_bps.txt").read_text().strip()
API = "https://webapi.bps.go.id/v1/api/list"
var_id = sys.argv[1] if len(sys.argv) > 1 else "1"

# 1. Tanya: tahun berapa saja yang tersedia untuk variabel ini?
r = requests.get(API, params={"model": "th", "domain": "0000", "var": var_id, "key": KUNCI}, timeout=60)
j = r.json()
print(f"[Daftar tahun] HTTP {r.status_code}, availability: {j.get('data-availability')}")
try:
    daftar_tahun = j["data"][1]
    print(f"   {len(daftar_tahun)} tahun. Contoh item pertama & terakhir:")
    print(f"   {daftar_tahun[0]}")
    print(f"   {daftar_tahun[-1]}")
except (KeyError, IndexError, TypeError):
    print("   Format tak terduga:", json.dumps(j, ensure_ascii=False)[:400])
    sys.exit()

# 2. Ambil data 3 tahun terakhir memakai kode tahun yang benar
kode = [str(t.get("th_id")) for t in daftar_tahun][-3:]
r = requests.get(API, params={"model": "data", "domain": "0000", "var": var_id,
                              "th": ";".join(kode), "key": KUNCI}, timeout=60)
j = r.json()
print(f"\n[Data th={';'.join(kode)}] HTTP {r.status_code}, availability: {j.get('data-availability')}")
print(f"   Jumlah nilai: {len(j.get('datacontent') or {})}")
print(f"   Tahun: {[t['label'] for t in (j.get('tahun') or [])]}")
if not j.get("datacontent"):
    print("   ", json.dumps(j, ensure_ascii=False)[:400])