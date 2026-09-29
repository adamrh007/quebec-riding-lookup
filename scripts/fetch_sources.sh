#!/usr/bin/env bash
# Downloads the two third-party inputs that are not stored in this repository.
#   1. 2026 riding boundaries (GeoJSON) from the open project "silatendancesemaintient" (GPL-3.0)
#   2. Canadian postal code centroids from the npm package "canada-postal-codes" (MIT)
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data/raw
cd data/raw

if [ ! -f qc_ridings_2026.geojson ]; then
  git clone --depth 1 https://github.com/essicolo/silatendancesemaintient.git tmp_boundaries
  cp tmp_boundaries/js/data/qc_ridings_2026.geojson .
  rm -rf tmp_boundaries
fi

if [ ! -f postal-codes.bin ]; then
  npm pack canada-postal-codes@0.2.2 --silent
  tar xzf canada-postal-codes-0.2.2.tgz
  cp package/dist/data/postal-codes.bin package/dist/data/cities.json .
  rm -rf package canada-postal-codes-0.2.2.tgz
fi

echo "Sources ready in data/raw/"
