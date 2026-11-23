"""
PANEL FRED -> tabel bulanan panjang (riset #52 langkah 1), memakai ALFRED (vintage) supaya POINT-IN-TIME sejauh mungkin.
Sumber: data/raw/makro/<KODE>.parquet (versi terbaru, 197 seri) + data/raw/alfred/vintage/<KODE>.parquet (187 seri, semua versi).

ATURAN (ditetapkan 23 Nov 2026 SEBELUM melihat hubungan apa pun dengan return saham):
- 'tanggal' FRED = AWAL periode. jeda(obs) = tanggal vintage pertama - tanggal.
- JEDA NORMAL seri = median jeda obs bertanggal >= 2019 (ALFRED mencatat rapi). Contoh: PAYEMS 34 hari, CPIAUCSL ~45, Brent 6.
- Obs "TERCATAT SEJAK TERBIT" bila jeda <= max(2 x normal, normal + 45 hari) -> nilai = RILIS PERTAMA, tersedia = tanggal rilis pertama,
  pit = True. Sebaliknya (artefak: seri Indonesia/IMF sebelum ~2015 punya 'jeda' bertahun-tahun karena ALFRED baru mulai mencatat)
  -> nilai = versi TERBARU (sudah direvisi), tersedia = tanggal + max(2 x normal, DEFAULT[frek]), pit = False.
  RISIKO DIAKUI: keterlambatan terbit yang NYATA (mis. nikel IMF 2018 ~367 hari) di periode artefak tidak bisa dibedakan -> jeda
  konservatif bisa masih terlalu cepat untuk seri IMF komoditas (harga komoditas harian tersedia dari LME/CPO=F di panel lain).
- Seri harian/mingguan (median selisih tanggal <= 8 hari) -> rata-rata bulanan dari raw/makro (data pasar praktis tak direvisi),
  tersedia = akhir bulan + jeda normal (ALFRED >= 2019 bila ada, else 1 hari).
- Seri tanpa file ALFRED -> versi terbaru + jeda konservatif (pit = False).
- 'bulan' = akhir bulan TERAKHIR periode (bulanan: bulan itu; kuartalan: Mar/Jun/Sep/Des; tahunan: Des).

  python panel_fred.py  -> data/olah/panel_fred.parquet (seri, kode, judul, frek, bulan, tersedia, nilai, pit)
                           + data/olah/panel_fred_ringkas.parquet
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd

np.seterr(divide="ignore", invalid="ignore")      # log nilai <= 0 sudah ditangani dgn selisih biasa (np.where)
DEFAULT = {"M": 90, "Q": 180, "A": 450}        # hari sejak AWAL periode (jeda konservatif bila tak tercatat)
kode_makro = Path("ambil_makro.py").read_text(encoding="utf-8").split("folder = Path(")[0]
g = {}
exec(compile(re.sub(r'KUNCI = .*\n', "", kode_makro, count=1), "ambil_makro_seri", "exec"), g)
JUDUL = g["SERI"]
TAMBAHAN = ["GDPC1", "GDP", "PCEPI", "PCE", "PPIFIS", "CES0500000003", "CIVPART", "DGORDER", "UMCSENT", "TCU", "BUSLOANS", "TOTALSL"]
for k in TAMBAHAN:
    JUDUL.setdefault(k, k)


def frek_dari(tgl):
    gap = pd.Series(pd.DatetimeIndex(tgl).sort_values()).diff().dt.days.median()
    if gap <= 8:
        return "D"
    if gap <= 40:
        return "M"
    if gap <= 100:
        return "Q"
    return "A"


def akhir_periode(tgl, f):
    p = pd.PeriodIndex(pd.DatetimeIndex(tgl), freq={"M": "M", "Q": "Q", "A": "Y"}[f])
    return p.to_timestamp(how="end").normalize().astype("datetime64[ns]")


baris, ringkas = [], []
for kode, judul in JUDUL.items():
    fm, fa = Path(f"data/raw/makro/{kode}.parquet"), Path(f"data/raw/alfred/vintage/{kode}.parquet")
    if not fm.exists() and not fa.exists():
        ringkas.append({"kode": kode, "status": "tidak ada file"})
        continue
    makro = pd.read_parquet(fm)["nilai"] if fm.exists() else None
    if makro is not None:
        makro.index = pd.DatetimeIndex(makro.index).astype("datetime64[ns]")
    va = pd.read_parquet(fa) if fa.exists() else None
    tgl_ref = makro.index if makro is not None else va["tanggal"].unique()
    f = frek_dari(tgl_ref)
    jn = np.nan
    if va is not None and len(va):
        pertama = va.sort_values("berlaku_mulai").groupby("tanggal").first()
        jeda = (pertama["berlaku_mulai"] - pertama.index).dt.days
        # JEDA NORMAL dari 24 obs TERBARU (dulu: obs >= 2019 -> seri yang baru dicatat ALFRED belakangan, mis. TIC, dapat jeda
        # bertahun-tahun -> TIC Mar 2015 'tersedia' Apr 2022; diperbaiki 23 Nov 2026)
        baru = jeda.sort_index().iloc[-24:]
        jn = float(baru.median()) if len(baru) >= 6 else np.nan
    if f == "D":
        if makro is None:
            ringkas.append({"kode": kode, "status": "harian tanpa raw/makro"})
            continue
        bul = makro.groupby(makro.index.to_period("M")).mean()
        d = pd.DataFrame({"bulan": bul.index.to_timestamp(how="end").normalize().astype("datetime64[ns]"), "nilai": bul.values})
        d["tersedia"] = d["bulan"] + pd.to_timedelta(0 if np.isnan(jn) else max(jn, 1), unit="D")
        d["pit"] = True
        v = pd.Series(d["nilai"].values)
        for kol, L in (("tumbuh1", 1), ("tumbuh12", 12)):
            lalu = v.shift(L)
            d[kol] = np.where((v > 0) & (lalu > 0), np.log(v / lalu), v - lalu)
        f_out = "D->M"
    else:
        terbaru = makro if makro is not None else va[va["berlaku_sampai"].isna()].set_index("tanggal")["nilai"]
        terbaru = terbaru[~terbaru.index.duplicated(keep="last")]
        jn_pakai = jn if not np.isnan(jn) else DEFAULT[f] / 2
        batas = max(2 * jn_pakai, jn_pakai + 45)
        konservatif = pd.to_timedelta(max(2 * jn_pakai, DEFAULT[f]), unit="D")
        if va is not None and len(va):
            idx = terbaru.index.union(pertama.index)
            d = pd.DataFrame(index=idx)
            d["nilai_terbaru"] = terbaru.reindex(idx)
            d["nilai_pertama"] = pertama["nilai"].reindex(idx)
            d["rilis_pertama"] = pertama["berlaku_mulai"].reindex(idx)
            j = (d["rilis_pertama"] - d.index.to_series()).dt.days
            d["pit"] = (j <= batas) & d["nilai_pertama"].notna()
            d["nilai"] = np.where(d["pit"], d["nilai_pertama"], d["nilai_terbaru"])
            d["tersedia"] = np.where(d["pit"], d["rilis_pertama"], d.index.to_series() + konservatif)
        else:
            d = pd.DataFrame({"nilai": terbaru})
            d["pit"] = False
            d["tersedia"] = d.index.to_series() + konservatif
        d = d.dropna(subset=["nilai"])
        # PERTUMBUHAN REAL-TIME: untuk titik pit, nilai t-L diambil dari VINTAGE YANG SAMA (berlaku pada tanggal rilis t) ->
        # tidak tercampur tahun dasar (mis. PDB AS rilis pertama 2008Q4 = dolar 2000, rilis 2014 = dolar 2009).
        L1, L12 = {"M": (1, 12), "Q": (3, 12), "A": (12, 12)}[f]
        d["tumbuh1"], d["tumbuh12"] = np.nan, np.nan
        if va is not None and len(va):
            per_tgl = {t: grp for t, grp in va.groupby("tanggal")}

            def nilai_di(t, r):
                grp = per_tgl.get(t)
                if grp is None:
                    return np.nan
                ok = (grp["berlaku_mulai"] <= r) & (grp["berlaku_sampai"].isna() | (grp["berlaku_sampai"] >= r))
                return grp.loc[ok, "nilai"].iloc[-1] if ok.any() else np.nan

            for t in d.index[d["pit"].values]:
                r, v = d.at[t, "rilis_pertama"], d.at[t, "nilai"]
                for kol, L in (("tumbuh1", L1), ("tumbuh12", L12)):
                    if f == "A" and kol == "tumbuh1":
                        continue
                    v0 = nilai_di(t - pd.DateOffset(months=L), r)
                    if pd.notna(v0):
                        d.at[t, kol] = np.log(v / v0) if (v > 0 and v0 > 0) else v - v0
        sisa = d["tumbuh12"].isna()                     # titik non-pit / tanpa pasangan vintage -> dari seri TERBARU
        ref = d["nilai_terbaru"] if "nilai_terbaru" in d else d["nilai"]
        for kol, L in (("tumbuh1", L1), ("tumbuh12", L12)):
            lalu = ref.reindex(ref.index - pd.DateOffset(months=L))
            lalu.index = ref.index
            positif = (ref > 0) & (lalu > 0)
            calon = pd.Series(np.where(positif, np.log(ref / lalu), ref - lalu), index=ref.index)
            d.loc[d[kol].isna() & sisa, kol] = calon[d[kol].isna() & sisa]
        d["bulan"] = akhir_periode(d.index, f)
        d = d.reset_index(drop=True)[["bulan", "nilai", "tersedia", "pit", "tumbuh1", "tumbuh12"]]
        f_out = f
    d["tersedia"] = pd.to_datetime(d["tersedia"]).astype("datetime64[ns]")
    d["seri"], d["kode"], d["judul"], d["frek"] = "FRED|" + kode, kode, str(judul), f_out
    baris.append(d)
    ringkas.append({"kode": kode, "status": "ok", "frek": f_out, "awal": d["bulan"].min(), "akhir": d["bulan"].max(), "n": len(d),
                    "jeda_normal": jn, "porsi_pit": d["pit"].mean(),
                    "porsi_pit_2005_2018": d.loc[(d["bulan"] >= "2005-01-01") & (d["bulan"] <= "2018-12-31"), "pit"].mean()})
out = pd.concat(baris, ignore_index=True)[["seri", "kode", "judul", "frek", "bulan", "tersedia", "nilai", "pit", "tumbuh1", "tumbuh12"]]
for k in ["seri", "kode", "judul", "frek"]:
    out[k] = out[k].astype("string")
out["pit"] = out["pit"].astype(bool)
assert (out["tersedia"] >= out["bulan"] - pd.Timedelta(days=400)).all()
mundur = (out["tersedia"] < out["bulan"] - pd.Timedelta(days=31)).sum()
Path("data/olah").mkdir(parents=True, exist_ok=True)
out.to_parquet("data/olah/panel_fred.parquet", index=False)
r = pd.DataFrame(ringkas)
r.to_parquet("data/olah/panel_fred_ringkas.parquet", index=False)
print(f"✅ panel FRED: {out['seri'].nunique()} seri, {len(out):,} baris; status: {r['status'].value_counts().to_dict()}")
print(f"   frek: {r['frek'].value_counts().to_dict()}; porsi titik point-in-time (rilis pertama) 2005-2018: "
      f"{out.loc[(out['bulan'] >= '2005-01-01') & (out['bulan'] <= '2018-12-31'), 'pit'].mean():.0%}; semua: {out['pit'].mean():.0%}")
print(f"   CEK: titik dgn 'tersedia' > 1 bulan SEBELUM akhir periodenya (harus 0 utk seri non-ramalan): {mundur}")
x = r[r["status"] == "ok"].sort_values("porsi_pit_2005_2018")
print("   paling sedikit point-in-time 2005-2018:", ", ".join(f"{k} {v:.0%}" for k, v in zip(x["kode"].head(6), x["porsi_pit_2005_2018"].head(6))))
print("   jeda normal contoh:", {k: v for k, v in zip(r["kode"], r["jeda_normal"]) if k in ("PAYEMS", "CPIAUCSL", "IDNCPIALLMINMEI", "PNICKUSDM", "DCOILBRENTEU", "GDPC1")})
