"""Inspect all shapefiles in data/raw and report their CRS and basic info.

This is the first pipeline step: before any reprojection or analysis, we need
to confirm what coordinate reference system (CRS) each source layer actually
uses (the project brief expects EPSG:27700 / British National Grid, but this
should be verified rather than assumed) and get a quick sense of each layer's
size, geometry type, and attributes.

Run from the project root with the project virtual environment active:

    venv\\Scripts\\python.exe -m src.inspect_data
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import geopandas as gpd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import RAW_DATA_DIR, TARGET_CRS  # noqa: E402


@dataclass
class LayerSummary:
    """Basic facts about one vector layer, gathered without altering the data."""

    filename: str
    crs_name: str | None
    epsg: int | None
    geometry_types: list[str]
    feature_count: int
    columns: list[str]
    bounds: tuple[float, float, float, float]
    matches_target_crs: bool
    error: str | None = field(default=None)


def find_shapefiles(raw_dir: Path) -> list[Path]:
    """Return all .shp files in raw_dir, sorted by filename."""
    return sorted(raw_dir.glob("*.shp"))


def summarise_layer(shp_path: Path, target_crs: str) -> LayerSummary:
    """Load a single shapefile and extract CRS and basic descriptive info."""
    try:
        gdf = gpd.read_file(shp_path)
    except Exception as exc:  # noqa: BLE001 - report any read failure, don't crash the run
        return LayerSummary(
            filename=shp_path.name,
            crs_name=None,
            epsg=None,
            geometry_types=[],
            feature_count=0,
            columns=[],
            bounds=(0.0, 0.0, 0.0, 0.0),
            matches_target_crs=False,
            error=str(exc),
        )

    crs = gdf.crs
    epsg = crs.to_epsg() if crs is not None else None
    matches_target = crs is not None and str(crs).upper() == target_crs.upper() or (
        epsg is not None and f"EPSG:{epsg}" == target_crs.upper()
    )

    return LayerSummary(
        filename=shp_path.name,
        crs_name=crs.name if crs is not None else None,
        epsg=epsg,
        geometry_types=sorted(gdf.geom_type.dropna().unique().tolist()),
        feature_count=len(gdf),
        columns=list(gdf.columns.drop("geometry", errors="ignore")),
        bounds=tuple(gdf.total_bounds) if len(gdf) else (0.0, 0.0, 0.0, 0.0),
        matches_target_crs=matches_target,
    )


def print_report(summaries: list[LayerSummary], target_crs: str) -> None:
    """Print a human-readable report of all layer summaries."""
    print(f"Found {len(summaries)} shapefile(s) in data/raw\n")
    print(f"Target CRS for analysis: {target_crs}\n")
    print("=" * 80)

    for s in summaries:
        print(f"\n{s.filename}")
        print("-" * len(s.filename))
        if s.error:
            print(f"  ERROR reading file: {s.error}")
            continue

        crs_flag = "OK (matches target)" if s.matches_target_crs else "NEEDS REPROJECTION"
        print(f"  CRS:              {s.crs_name}  (EPSG:{s.epsg})  -> {crs_flag}")
        print(f"  Feature count:    {s.feature_count}")
        print(f"  Geometry type(s): {', '.join(s.geometry_types) or 'n/a'}")
        print(f"  Bounds (xmin, ymin, xmax, ymax): {tuple(round(b, 1) for b in s.bounds)}")
        print(f"  Columns ({len(s.columns)}): {', '.join(s.columns)}")

    print("\n" + "=" * 80)
    n_ok = sum(1 for s in summaries if s.matches_target_crs and not s.error)
    n_bad = sum(1 for s in summaries if not s.matches_target_crs and not s.error)
    n_err = sum(1 for s in summaries if s.error)
    print(
        f"\nSummary: {n_ok} layer(s) already in {target_crs}, "
        f"{n_bad} layer(s) will need reprojecting, {n_err} layer(s) failed to load."
    )


def main() -> None:
    shapefiles = find_shapefiles(RAW_DATA_DIR)
    if not shapefiles:
        print(f"No .shp files found in {RAW_DATA_DIR}")
        return

    summaries = [summarise_layer(path, TARGET_CRS) for path in shapefiles]
    print_report(summaries, TARGET_CRS)


if __name__ == "__main__":
    main()
