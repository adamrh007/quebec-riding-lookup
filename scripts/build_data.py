"""Builds the lookup data used by the site.

Steps
  1. Assign every Quebec postal code to a 2026 riding (point-in-polygon on its centroid).
  2. Fix coordinate outliers: a code far from the rest of its postal area (FSA),
     in a riding that is rare in that FSA, gets the FSA's usual riding instead.
  3. Compress the result per FSA (first 3 characters) and compute each FSA's
     split between ridings.
  4. Join the Qc125 projections and ratings for all 127 ridings.

Inputs : data/raw/* (see fetch_sources.sh), data/ridings.csv,
         data/projections_qc125.csv, data/regions.json
Outputs: build/ridings.json, build/postal.json
Requires: pip install shapely
"""
import collections, csv, json, math, statistics, struct
from pathlib import Path
from shapely.geometry import Point, shape
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parent.parent
RAW, OUT = ROOT / "data" / "raw", ROOT / "build"
OUT.mkdir(exist_ok=True)
PARTIES = ["PQ", "PLQ", "CAQ", "PCQ", "QS"]
QC_PROVINCE_INDEX = 10          # index of "QC" in the package's provinces.json
MAX_SNAP_DEG = 0.03             # codes just outside a polygon (coastline) snap to the nearest riding
OUTLIER_KM, OUTLIER_SPREAD, RARE_SHARE = 8, 4, 0.03


def norm(name):
    return name.replace("'", "’")


# ---- ridings and projections ------------------------------------------------
ridings = list(csv.DictReader(open(ROOT / "data" / "ridings.csv", encoding="utf-8")))
index = {r["name"]: i for i, r in enumerate(ridings)}
proj_file = ROOT / "data" / "projections_qc125.csv"
proj = {r["id"]: {p: int(r[p]) for p in PARTIES if r[p]} for r in csv.DictReader(open(proj_file, encoding="utf-8"))}

# ---- 1. point-in-polygon ----------------------------------------------------
geo = json.load(open(RAW / "qc_ridings_2026.geojson", encoding="utf-8"))
polys = [shape(f["geometry"]) for f in geo["features"]]
poly_riding = [index[norm(f["properties"]["riding_name"])] for f in geo["features"]]
tree = STRtree(polys)

raw = open(RAW / "postal-codes.bin", "rb").read()
code_riding, xy = {}, {}
for off in range(0, len(raw), 18):
    code, prov, _tz, _city, lat, lon = struct.unpack_from("<6sBbHff", raw, off)
    if prov != QC_PROVINCE_INDEX:
        continue
    code, pt, hit = code.decode(), Point(lon, lat), None
    for j in tree.query(pt):
        if polys[j].contains(pt):
            hit = int(j)
            break
    if hit is None:
        j = int(tree.nearest(pt))
        if polys[j].distance(pt) < MAX_SNAP_DEG:
            hit = j
    if hit is not None:
        code_riding[code] = poly_riding[hit]
        xy[code] = (lat, lon)

# ---- 2. outlier correction --------------------------------------------------
by_fsa = collections.defaultdict(list)
for c in code_riding:
    by_fsa[c[:3]].append(c)
fixed = 0
for fsa, codes in by_fsa.items():
    mlat = statistics.median(xy[c][0] for c in codes)
    mlon = statistics.median(xy[c][1] for c in codes)
    km = {c: math.hypot((xy[c][0] - mlat) * 111, (xy[c][1] - mlon) * 111 * math.cos(math.radians(mlat))) for c in codes}
    spread = statistics.median(km.values())
    count = collections.Counter(code_riding[c] for c in codes)
    usual = count.most_common(1)[0][0]
    for c in codes:
        if code_riding[c] != usual and count[code_riding[c]] / len(codes) < RARE_SHARE and km[c] > max(OUTLIER_KM, OUTLIER_SPREAD * spread):
            code_riding[c] = usual
            fixed += 1

# ---- 3. compact per-FSA table ----------------------------------------------
# pc[fsa] = [usual riding, "LDU+riding(3 digits)" exceptions, unused, "LDU" list of codes in the usual riding]
pc, fsa_share = {}, {}
for fsa, codes in by_fsa.items():
    count = collections.Counter(code_riding[c] for c in codes)
    usual = count.most_common(1)[0][0]
    exc = "".join(f"{c[3:]}{code_riding[c]:03d}" for c in sorted(codes) if code_riding[c] != usual)
    known = "".join(c[3:] for c in sorted(codes) if code_riding[c] == usual)
    pc[fsa] = [usual, exc, [], known]
    fsa_share[fsa] = [[i, round(n / len(codes) * 100)] for i, n in count.most_common() if n / len(codes) >= 0.05]

# ---- 4. riding records ------------------------------------------------------
LAB_EN = {"solide": "safe", "probable": "likely", "enclin": "leaning"}
def label_en(lab):
    w = lab.split()
    return f"toss-up {w[1]}" if w[0] == "Pivot" else f"{w[0]} {LAB_EN.get(w[1], w[1])}"

out = []
for i, r in enumerate(ridings):
    shares = dict(sorted(proj[r["id"]].items(), key=lambda kv: -kv[1]))
    top = list(shares.values())
    out.append(dict(
        name=r["name"], region=r["region"], label=r["qc125_rating"], label_en=label_en(r["qc125_rating"]),
        shares=shares, gap=top[0] - top[1],
        fsa=sorted([[f, p] for f, lst in fsa_share.items() for j, p in lst if j == i], key=lambda x: (-x[1], x[0])),
        url=f"https://qc125.com/{r['id']}f.htm"))

regions = json.load(open(ROOT / "data" / "regions.json", encoding="utf-8"))
json.dump(dict(regions=regions, ridings=out), open(OUT / "ridings.json", "w", encoding="utf-8"), ensure_ascii=False)
json.dump(dict(fsa=fsa_share, pc=pc), open(OUT / "postal.json", "w"), separators=(",", ":"))
print(f"{len(code_riding)} postal codes matched, {fixed} outliers corrected, {len(pc)} FSAs, {len(out)} ridings")
