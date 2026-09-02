"""End-to-end suitability index pipeline.

Builds the analysis grid, computes each sub-score, combines them into a
single weighted Suitability Index (0-100), classifies the result into
bands, and writes the scored grid to data/processed/.

Run:
    venv\\Scripts\\python.exe -m src.suitability_pipeline
"""

from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import PROCESSED_DATA_DIR, RAW_DATA_DIR  # noqa: E402
from src.grid import DEFAULT_CELL_SIZE_M, build_grid  # noqa: E402
from src.scoring import (  # noqa: E402
    FLOOD_ZONE_2_PENALTY_FACTOR,
    FLOOD_ZONE_3_PENALTY_FACTOR,
    exclusion_mask,
    ground_stability_score,
    infill_preference_score,
)

# Provisional weights for the two sub-scores built so far. Ground stability
# and infill preference are weighted equally for now; once the accessibility
# (road-distance) sub-score is added these will be rebalanced and the
# reasoning documented here and in the README.
WEIGHTS = {
    "ground_stability": 0.5,
    "infill_preference": 0.5,
}

# (lower bound inclusive, upper bound exclusive, label)
SUITABILITY_BANDS = [
    (0, 25, "Low"),
    (25, 50, "Medium"),
    (50, 75, "High"),
    (75, 100.0001, "Prime"),
]


def load_layers() -> dict[str, gpd.GeoDataFrame]:
    boundary_path = PROCESSED_DATA_DIR / "administrative_boundary_hull_27700.gpkg"
    if not boundary_path.exists():
        raise FileNotFoundError(
            f"{boundary_path} not found - run `python -m src.reproject_boundary` first."
        )

    return {
        "boundary": gpd.read_file(boundary_path),
        "buildings": gpd.read_file(RAW_DATA_DIR / "Building_Hull1.shp"),
        "superficial_geology": gpd.read_file(RAW_DATA_DIR / "UK_625k_SUPERFICIAL_Geology_Polygons_Hull.shp"),
        "bedrock_geology": gpd.read_file(RAW_DATA_DIR / "625k_V5_BEDROCK_Geology_Polygons_Hull.shp"),
        "greenspace": gpd.read_file(RAW_DATA_DIR / "GB_GreenspaceSite_Hull.shp"),
        "flood_zones": gpd.read_file(RAW_DATA_DIR / "Flood_Zones_2_3_Rivers__Hull_Clip.shp"),
    }


def classify_band(score: float) -> str:
    for lower, upper, label in SUITABILITY_BANDS:
        if lower <= score < upper:
            return label
    return "Low"


def combine_scores(grid: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Weight and sum the sub-scores, apply the flood penalties and greenspace
    hard exclusion, and classify each cell into a suitability band.

    Flood Zone 3 and Flood Zone 2 are both penalties, not hard exclusions
    (see src/scoring.py); where a cell is flagged for both, only the
    stronger FZ3 penalty is applied, not both multiplied together.
    """
    grid = grid.copy()
    weighted = sum(grid[column] * weight for column, weight in WEIGHTS.items())
    grid["suitability_index"] = weighted

    fz3 = grid["flood_zone_3"]
    fz2_only = grid["flood_zone_2"] & ~fz3
    grid.loc[fz3, "suitability_index"] *= FLOOD_ZONE_3_PENALTY_FACTOR
    grid.loc[fz2_only, "suitability_index"] *= FLOOD_ZONE_2_PENALTY_FACTOR

    grid.loc[grid["excluded"], "suitability_index"] = 0.0

    grid["suitability_band"] = grid["suitability_index"].apply(classify_band)
    grid.loc[grid["excluded"], "suitability_band"] = "Excluded"
    return grid


def main() -> None:
    layers = load_layers()

    grid = build_grid(layers["boundary"])
    grid = ground_stability_score(grid, layers["superficial_geology"], layers["bedrock_geology"])
    grid = infill_preference_score(grid, layers["buildings"])
    grid = exclusion_mask(grid, layers["greenspace"], layers["flood_zones"])
    grid = combine_scores(grid)

    out_path = PROCESSED_DATA_DIR / f"suitability_grid_{int(DEFAULT_CELL_SIZE_M)}m.gpkg"
    grid.to_file(out_path, driver="GPKG")

    print(f"Scored {len(grid)} grid cells ({DEFAULT_CELL_SIZE_M:.0f}m cells)\n")
    print("Suitability band counts:")
    print(grid["suitability_band"].value_counts())
    print(f"\nMean ground_stability:  {grid['ground_stability'].mean():.1f}")
    print(f"Mean infill_preference: {grid['infill_preference'].mean():.1f}")
    print(f"Cells excluded (greenspace): {grid['excluded'].sum()} ({grid['excluded'].mean():.1%})")
    print(f"Cells in Flood Zone 3:       {grid['flood_zone_3'].sum()} ({grid['flood_zone_3'].mean():.1%})")
    print(f"Cells in Flood Zone 2 only:  {(grid['flood_zone_2'] & ~grid['flood_zone_3']).sum()}")
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
