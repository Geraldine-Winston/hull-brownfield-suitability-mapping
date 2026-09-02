"""Build a regular analysis grid clipped to the Hull administrative boundary.

The project brief calls for "a regular grid or administrative sub-areas as
the unit of analysis". The supplied boundary is a single dissolved polygon
(no ward-level sub-areas), so a regular square grid is used instead. Each
cell is a fixed-size square in EPSG:27700 and is the unit every suitability
sub-score is calculated for.

Run:
    venv\\Scripts\\python.exe -m src.grid
"""

from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
from shapely.geometry import box

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import PROCESSED_DATA_DIR, TARGET_CRS  # noqa: E402

DEFAULT_CELL_SIZE_M = 100.0


def build_grid(boundary: gpd.GeoDataFrame, cell_size: float = DEFAULT_CELL_SIZE_M) -> gpd.GeoDataFrame:
    """Create a square grid covering boundary's extent, keeping cells that intersect it.

    Cells are full `cell_size` x `cell_size` squares, not clipped to the
    boundary edge, so every cell has equal, comparable area for the
    density/coverage calculations used by the sub-scores.
    """
    if boundary.crs is None or str(boundary.crs).upper() != TARGET_CRS.upper():
        boundary = boundary.to_crs(TARGET_CRS)

    xmin, ymin, xmax, ymax = boundary.total_bounds
    boundary_union = boundary.union_all()

    cells = []
    y = ymin
    while y < ymax:
        x = xmin
        while x < xmax:
            cells.append(box(x, y, x + cell_size, y + cell_size))
            x += cell_size
        y += cell_size

    grid = gpd.GeoDataFrame({"geometry": cells}, crs=TARGET_CRS)
    grid = grid[grid.intersects(boundary_union)].reset_index(drop=True)
    grid.insert(0, "cell_id", range(len(grid)))
    return grid


def main() -> None:
    boundary_path = PROCESSED_DATA_DIR / "administrative_boundary_hull_27700.gpkg"
    if not boundary_path.exists():
        raise FileNotFoundError(
            f"{boundary_path} not found - run `python -m src.reproject_boundary` first."
        )

    boundary = gpd.read_file(boundary_path)
    grid = build_grid(boundary)

    out_path = PROCESSED_DATA_DIR / f"analysis_grid_{int(DEFAULT_CELL_SIZE_M)}m.gpkg"
    grid.to_file(out_path, driver="GPKG")

    print(f"Built grid: {len(grid)} cells of {DEFAULT_CELL_SIZE_M:.0f}m x {DEFAULT_CELL_SIZE_M:.0f}m")
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
