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
    accessibility_score,
    exclusion_mask,
    ground_stability_score,
    infill_preference_score,
)

# All three sub-scores are weighted equally (1/3 each). This is a deliberate
# simplification for a demonstration project rather than a claim that all
# three genuinely matter the same amount - a defensible weighting exercise
# (e.g. AHP with input from planners/surveyors) would be a natural next step
# beyond this project's scope. Equal weights keep the index transparent and
# easy to reason about without asserting false precision.
WEIGHTS = {
    "ground_stability": 1 / 3,
    "infill_preference": 1 / 3,
    "accessibility": 1 / 3,
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
        "roads": gpd.read_file(RAW_DATA_DIR / "Roads_Hall1.shp"),
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


def combine_scores(grid: gpd.GeoDataFrame, weights: dict[str, float] | None = None) -> gpd.GeoDataFrame:
    """Weight and sum the sub-scores, apply the flood penalties and greenspace
    hard exclusion, and classify each cell into a suitability band.

    Flood Zone 3 and Flood Zone 2 are both penalties, not hard exclusions
    (see src/scoring.py); where a cell is flagged for both, only the
    stronger FZ3 penalty is applied, not both multiplied together.

    `weights` overrides the module-level WEIGHTS (e.g. from the Streamlit
    app's interactive sliders) - keys must match sub-score column names in
    `grid`. Values need not sum to 1; the caller is expected to normalise.
    """
    weights = weights if weights is not None else WEIGHTS
    grid = grid.copy()
    weighted = sum(grid[column] * weight for column, weight in weights.items())
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
    grid = accessibility_score(grid, layers["roads"])
    grid = exclusion_mask(grid, layers["greenspace"], layers["flood_zones"])
    grid = combine_scores(grid)

    out_path = PROCESSED_DATA_DIR / f"suitability_grid_{int(DEFAULT_CELL_SIZE_M)}m.gpkg"
    grid.to_file(out_path, driver="GPKG")

    print(f"Scored {len(grid)} grid cells ({DEFAULT_CELL_SIZE_M:.0f}m cells)\n")
    print("Suitability band counts:")
    print(grid["suitability_band"].value_counts())
    print(f"\nMean ground_stability:  {grid['ground_stability'].mean():.1f}")
    print(f"Mean infill_preference: {grid['infill_preference'].mean():.1f}")
    print(f"Mean accessibility:     {grid['accessibility'].mean():.1f}")
    print(f"Cells excluded (greenspace): {grid['excluded'].sum()} ({grid['excluded'].mean():.1%})")
    print(f"Cells in Flood Zone 3:       {grid['flood_zone_3'].sum()} ({grid['flood_zone_3'].mean():.1%})")
    print(f"Cells in Flood Zone 2 only:  {(grid['flood_zone_2'] & ~grid['flood_zone_3']).sum()}")
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
