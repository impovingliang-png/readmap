#!/usr/bin/env python3
import argparse
import math
import os
import subprocess
import numpy as np
import tifffile as tiff
from urllib.parse import urlencode


WORLDPOP_TOTAL_1KM = "https://worldpop.arcgis.com/arcgis/rest/services/WorldPop_Total_Population_1km/ImageServer"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2020)
    parser.add_argument("--deg", type=float, default=0.5)
    parser.add_argument("--out", default="data/worldpop_grid_0p5deg.csv")
    args = parser.parse_args()

    out_path = args.out
    deg = float(args.deg)
    if deg <= 0 or 360 % deg != 0 or 180 % deg != 0:
        raise ValueError("--deg must evenly divide 360 and 180 (e.g., 1, 0.5, 0.25)")
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
        "time": f"{args.year}-01-01",
    }
    url = f"{WORLDPOP_TOTAL_1KM}/exportImage?{urlencode(params)}"
    tmp = os.path.join(os.path.dirname(out_path), "_worldpop_tmp.tif")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    # Use curl for better DNS behavior in some environments
    res = subprocess.run(["curl", "-L", "-sS", url, "-o", tmp])
    if res.returncode != 0:
        raise RuntimeError("curl failed to download WorldPop exportImage")
    with open(tmp, "rb") as f:
        blob = f.read()
    # Basic sanity check (HTML/JSON error)
    if blob[:1] in (b"{", b"<"):
        raise RuntimeError(f"WorldPop exportImage returned non-TIFF data: {blob[:120]!r}")

    arr = tiff.imread(tmp)
    arr = np.asarray(arr, dtype=np.float32).squeeze()
    # ArcGIS NoData often encoded as extremely large float (~3.4e38)
    arr[arr > 1e30] = 0.0
    arr[arr < 0] = 0.0
    if arr.size != size_x * size_y:
        raise RuntimeError(f"Unexpected TIFF size: {arr.shape} (size={arr.size})")
    arr = arr.reshape((size_y, size_x))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("lat,lon,pop\n")
        for r in range(size_y):
            lat = 90 - (r + 0.5) * deg
            lat_rad = math.radians(lat)
            # approximate area of 1°x1° cell in km²
            area_km2 = 111.32 * 111.32 * max(0.0, math.cos(lat_rad)) * (deg * deg)
            for c in range(size_x):
                lon = -180 + (c + 0.5) * deg
                v = float(arr[r, c])
                if not math.isfinite(v) or v <= 0:
                    continue
                # exportImage likely returns average per 1km cell; scale to total by area
                total = v * area_km2
                if total <= 0:
                    continue
                f.write(f"{lat:.5f},{lon:.5f},{total:.2f}\n")

    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
