#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="$ROOT_DIR/data/ghsl_vrt"

mkdir -p "$OUT_DIR"

echo "Generating GHSL 100m URL list..."
python3 "$ROOT_DIR/scripts/gen_ghsl_url_list.py" --epoch 2020 --res 100 --scheme https > "$OUT_DIR/ghsl_pop_e2020_100m.txt"

echo "Building GHSL 100m VRT..."
gdalbuildvrt -input_file_list "$OUT_DIR/ghsl_pop_e2020_100m.txt" "$OUT_DIR/ghsl_pop_e2020_100m.vrt"

echo "Generating GHSL 1km URL list..."
python3 "$ROOT_DIR/scripts/gen_ghsl_url_list.py" --epoch 2020 --res 1000 --scheme https > "$OUT_DIR/ghsl_pop_e2020_1km.txt"

echo "Building GHSL 1km VRT..."
gdalbuildvrt -input_file_list "$OUT_DIR/ghsl_pop_e2020_1km.txt" "$OUT_DIR/ghsl_pop_e2020_1km.vrt"

echo "Done. VRT files in: $OUT_DIR"
