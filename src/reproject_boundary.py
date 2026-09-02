"""Reproject the Hull administrative boundary from WGS84 to EPSG:27700.

src/inspect_data.py identified Administrative boundary_Hull.shp as the one
source layer not already in British National Grid (it's in WGS84 / EPSG:4326).
This script reprojects it to the project's target CRS and writes the result
to data/processed/ as a GeoPackage, leaving the original raw file untouched.

Run from the project root with the project virtual environment active:

    venv\\Scripts\\python.exe -m src.reproject_boundary
"""

from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import PROCESSED_DATA_DIR, RAW_DATA_DIR, TARGET_CRS  # noqa: E402

SOURCE_FILE = RAW_DATA_DIR / "Administrative boundary_Hull.shp"
OUTPUT_FILE = PROCESSED_DATA_DIR / "administrative_boundary_hull_27700.gpkg"


def reproject_boundary(source_path: Path, target_crs: str) -> gpd.GeoDataFrame:
    """Load the boundary layer and reproject it to target_crs."""
    gdf = gpd.read_file(source_path)
    original_crs = gdf.crs
    reprojected = gdf.to_crs(target_crs)
    print(f"Loaded {source_path.name}: {len(gdf)} feature(s), CRS {original_crs}")
    print(f"Reprojected to {target_crs}")
    return reprojected


def main() -> None:
    if not SOURCE_FILE.exists():
        raise FileNotFoundError(f"Source boundary shapefile not found: {SOURCE_FILE}")

    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    reprojected = reproject_boundary(SOURCE_FILE, TARGET_CRS)
    reprojected.to_file(OUTPUT_FILE, driver="GPKG")

    bounds = reprojected.total_bounds
    print(f"\nSaved: {OUTPUT_FILE}")
    print(f"New CRS: {reprojected.crs}  (EPSG:{reprojected.crs.to_epsg()})")
    print(f"New bounds (xmin, ymin, xmax, ymax): {tuple(round(b, 1) for b in bounds)}")


if __name__ == "__main__":
    main()
