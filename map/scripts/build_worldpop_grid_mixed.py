#!/usr/bin/env python3
import argparse
import math
import os
import subprocess
import json
from urllib.parse import urlencode

import numpy as np
import tifffile as tiff

WORLDPOP_TOTAL_1KM = "https://worldpop.arcgis.com/arcgis/rest/services/WorldPop_Total_Population_1km/ImageServer"
NE_COUNTRIES = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson"

TARGET_NAMES = {
    # Asia
    "taiwan",
    "japan",
    "south korea",
    "korea, south",
    "korea",
    "israel",
    "armenia",
    "lebanon",
    "kuwait",
    "qatar",
    "timor-leste",
    "east timor",
    "singapore",
    "bahrain",
    # Europe
    "belgium",
    "albania",
    "north macedonia",
    "macedonia",
    "slovenia",
    "moldova",
    "moldova, republic of",
    "kosovo",
    "cyprus",
    # Africa
    "rwanda",
    "burundi",
    "equatorial guinea",
    "djibouti",
    "lesotho",
    "eswatini",
    "swaziland",
    "gambia",
    "guinea-bissau",
    # Americas
    "haiti",
    "jamaica",
    "el salvador",
    "trinidad and tobago",
}


def norm_name(s: str) -> str:
    return "".join(ch.lower() if ch.isalnum() or ch.isspace() or ch in "-," else " " for ch in s).strip()


def download(url: str, out_path: str, allow_text: bool = False):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    res = subprocess.run(["curl", "-L", "-sS", url, "-o", out_path])
    if res.returncode != 0:
        raise RuntimeError(f"curl failed: {url}")
    if not allow_text:
        with open(out_path, "rb") as f:
            head = f.read(1)
        if head in (b"{", b"<"):
            raise RuntimeError(f"download returned non-binary content: {url}")


def export_worldpop_tiff(year: int, deg: float, out_path: str):
    size_x = int(round(360 / deg))
    size_y = int(round(180 / deg))
    params = {
        "f": "image",
        "bbox": "-180,-90,180,90",
        "bboxSR": 4326,
        "imageSR": 4326,
        "size": f"{size_x},{size_y}",
        "format": "tiff",
        "pixelType": "F32",
        "renderingRule": '{"rasterFunction":"None"}',
        "time": f"{year}-01-01",
    }
    url = f"{WORLDPOP_TOTAL_1KM}/exportImage?{urlencode(params)}"
    download(url, out_path)


def ring_bbox(ring):
    minx = 180.0
    miny = 90.0
    maxx = -180.0
    maxy = -90.0
    for x, y in ring:
        if x < minx:
            minx = x
        if y < miny:
            miny = y
        if x > maxx:
            maxx = x
        if y > maxy:
            maxy = y
    return (minx, miny, maxx, maxy)


def point_in_ring(pt, ring):
    x, y = pt
    inside = False
    for i in range(len(ring)):
        j = (i - 1) % len(ring)
        xi, yi = ring[i]
        xj, yj = ring[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi):
            inside = not inside
    return inside


def build_country_index(geojson_path):
    with open(geojson_path, "r", encoding="utf-8") as f:
        geo = json.load(f)
    bins = {}
    bin_size = 10.0

    def add_poly(ring):
        if not ring or len(ring) < 3:
            return
        bbox = ring_bbox(ring)
        minx, miny, maxx, maxy = bbox
        x0 = int(math.floor((minx + 180) / bin_size))
        x1 = int(math.floor((maxx + 180) / bin_size))
        y0 = int(math.floor((miny + 90) / bin_size))
        y1 = int(math.floor((maxy + 90) / bin_size))
        for yi in range(y0, y1 + 1):
            for xi in range(x0, x1 + 1):
                key = (yi, xi)
                if key not in bins:
                    bins[key] = []
                bins[key].append({"ring": ring, "bbox": bbox})

    for ftr in geo.get("features", []):
        props = ftr.get("properties", {})
        names = set()
        for key in ("NAME", "NAME_LONG", "ADMIN", "SOVEREIGNT"):
            v = props.get(key)
            if isinstance(v, str) and v.strip():
                names.add(norm_name(v))
        if not any(n in TARGET_NAMES for n in names):
            continue
        geom = ftr.get("geometry")
        if not geom:
            continue
        if geom["type"] == "Polygon":
            outer = geom["coordinates"][0]
            add_poly(outer)
        elif geom["type"] == "MultiPolygon":
            for poly in geom["coordinates"]:
                outer = poly[0] if poly else None
                add_poly(outer)

    return {"bins": bins, "bin_size": bin_size}


def in_target_country(lat, lon, idx):
    bin_size = idx["bin_size"]
    xi = int(math.floor((lon + 180) / bin_size))
    yi = int(math.floor((lat + 90) / bin_size))
    polys = idx["bins"].get((yi, xi), [])
    if not polys:
        return False
    for p in polys:
        minx, miny, maxx, maxy = p["bbox"]
        if lon < minx or lon > maxx or lat < miny or lat > maxy:
            continue
        if point_in_ring((lon, lat), p["ring"]):
            return True
    return False


def area_km2_for_cell(lat_deg, deg):
    lat_rad = math.radians(lat_deg)
    return 111.32 * 111.32 * max(0.0, math.cos(lat_rad)) * (deg * deg)


def read_worldpop_array(path, size_x, size_y):
    arr = tiff.imread(path)
    arr = np.asarray(arr, dtype=np.float32).squeeze()
    arr[arr > 1e30] = 0.0
    arr[arr < 0] = 0.0
    if arr.size != size_x * size_y:
        raise RuntimeError(f"Unexpected TIFF size: {arr.shape} (size={arr.size})")
    return arr.reshape((size_y, size_x))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2020)
    parser.add_argument("--out", default="data/worldpop_grid_mixed.csv")
    args = parser.parse_args()

    out_path = args.out
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    tmp_dir = os.path.join(os.path.dirname(out_path), "_tmp_worldpop")
    os.makedirs(tmp_dir, exist_ok=True)

    geojson_path = os.path.join(tmp_dir, "ne_countries.geojson")
    if not os.path.exists(geojson_path):
        download(NE_COUNTRIES, geojson_path, allow_text=True)

    idx = build_country_index(geojson_path)

    tiff_05 = os.path.join(tmp_dir, "worldpop_0p5deg.tif")
    tiff_025 = os.path.join(tmp_dir, "worldpop_0p25deg.tif")
    export_worldpop_tiff(args.year, 0.5, tiff_05)
    export_worldpop_tiff(args.year, 0.25, tiff_025)

    arr_05 = read_worldpop_array(tiff_05, 720, 360)
    arr_025 = read_worldpop_array(tiff_025, 1440, 720)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("lat,lon,pop,deg\n")

        # 0.25° cells for target countries
        deg = 0.25
        for r in range(720):
            lat = 90 - (r + 0.5) * deg
            area_km2 = area_km2_for_cell(lat, deg)
            for c in range(1440):
                lon = -180 + (c + 0.5) * deg
                if not in_target_country(lat, lon, idx):
                    continue
                v = float(arr_025[r, c])
                if not math.isfinite(v) or v <= 0:
                    continue
                total = v * area_km2
                if total <= 0:
                    continue
                f.write(f"{lat:.5f},{lon:.5f},{total:.2f},{deg}\n")

        # 0.5° cells everywhere else
        deg = 0.5
        for r in range(360):
            lat = 90 - (r + 0.5) * deg
            area_km2 = area_km2_for_cell(lat, deg)
            for c in range(720):
                lon = -180 + (c + 0.5) * deg
                if in_target_country(lat, lon, idx):
                    continue
                v = float(arr_05[r, c])
                if not math.isfinite(v) or v <= 0:
                    continue
                total = v * area_km2
                if total <= 0:
                    continue
                f.write(f"{lat:.5f},{lon:.5f},{total:.2f},{deg}\n")

    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
