"""Suitability sub-score calculations: ground stability, infill preference,
and the greenspace/flood exclusion mask.

Each function takes the analysis grid plus one or more source layers
(already in EPSG:27700) and returns the grid with new column(s) added.
Scores are 0-100 unless noted, with higher always meaning more suitable.
"""

from __future__ import annotations

import geopandas as gpd
import pandas as pd

# --- Ground stability --------------------------------------------------------

# Superficial geology ROCK_D class -> stability score (0-100).
# Hull sits on soft alluvial ("warp") deposits over a single, uniform chalk
# bedrock unit, so ground conditions across the city are driven almost
# entirely by the SUPERFICIAL geology, not the bedrock. Scores reflect
# typical bearing capacity / settlement risk for each class:
#   - TILL (glacial diamicton): compact, decent bearing capacity -> high
#   - SAND AND GRAVEL (river terrace deposits): free-draining, moderate-good
#     bearing capacity -> high-moderate
#   - ALLUVIUM (clay, silt and sand): soft, compressible, historically
#     requires piled foundations across Hull -> low
# Where no superficial deposit is mapped, the chalk bedrock exposed there is
# a reasonably competent foundation material -> mid-high fallback score.
SUPERFICIAL_STABILITY_SCORES: dict[str, float] = {
    "DIAMICTON": 85.0,             # TILL
    "SAND AND GRAVEL": 75.0,       # river terrace deposits
    "CLAY, SILT AND SAND": 30.0,   # alluvium
}
BEDROCK_FALLBACK_SCORE = 70.0  # chalk, where no superficial deposit is mapped


def _majority_overlap_attribute(
    grid: gpd.GeoDataFrame, polygons: gpd.GeoDataFrame, attribute: str
) -> pd.Series:
    """For each grid cell, return `attribute` from whichever polygon covers the
    largest share of that cell's area (NaN where nothing overlaps)."""
    overlay = gpd.overlay(
        grid[["cell_id", "geometry"]], polygons[[attribute, "geometry"]], how="intersection"
    )
    if overlay.empty:
        return pd.Series(index=grid["cell_id"], dtype=object)

    overlay["overlap_area"] = overlay.geometry.area
    winning_rows = overlay.loc[overlay.groupby("cell_id")["overlap_area"].idxmax()]
    winners = winning_rows.set_index("cell_id")[attribute]
    return grid["cell_id"].map(winners)


def ground_stability_score(
    grid: gpd.GeoDataFrame,
    superficial_geology: gpd.GeoDataFrame,
    bedrock_geology: gpd.GeoDataFrame,  # noqa: ARG001 - kept for API symmetry / future use
) -> gpd.GeoDataFrame:
    """Add a `ground_stability` column (0-100) from the superficial geology class
    covering most of each cell, falling back to BEDROCK_FALLBACK_SCORE elsewhere."""
    grid = grid.copy()
    rock_class = _majority_overlap_attribute(grid, superficial_geology, "ROCK_D")
    grid["ground_stability"] = rock_class.map(SUPERFICIAL_STABILITY_SCORES)
    grid["ground_stability"] = grid["ground_stability"].fillna(BEDROCK_FALLBACK_SCORE)
    return grid


# --- Infill preference --------------------------------------------------------

# Distance-decay from each cell's centroid to the nearest existing building
# footprint: cells right next to existing development score highest
# (redevelopment / infill, consistent with Hull's regeneration priorities),
# decaying linearly to 0 by INFILL_MAX_DISTANCE_M, beyond which land is
# treated as disconnected greenfield.
INFILL_MAX_DISTANCE_M = 300.0


def infill_preference_score(grid: gpd.GeoDataFrame, buildings: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add an `infill_preference` column (0-100): higher for cells closer to
    existing building footprints, linearly decaying to 0 by INFILL_MAX_DISTANCE_M."""
    grid = grid.copy()
    centroids = gpd.GeoDataFrame(
        {"cell_id": grid["cell_id"]}, geometry=grid.geometry.centroid, crs=grid.crs
    )
    nearest = gpd.sjoin_nearest(centroids, buildings[["geometry"]], distance_col="dist_to_building")
    nearest = nearest.drop_duplicates(subset="cell_id").set_index("cell_id")["dist_to_building"]

    distance = grid["cell_id"].map(nearest).fillna(INFILL_MAX_DISTANCE_M)
    score = 100.0 * (1.0 - distance / INFILL_MAX_DISTANCE_M)
    grid["infill_preference"] = score.clip(lower=0.0, upper=100.0)
    return grid


# --- Exclusion mask ------------------------------------------------------------

# A cell is hard-excluded if greenspace covers at least this share of its
# area (guards against a cell being excluded just because it clips the edge
# of a polygon).
#
# Flood Zone 3 is deliberately NOT a hard exclusion here, even though it
# covers ~79% of Hull's administrative area (the city is largely below
# high-tide level and depends on tidal defences). A literal hard exclusion
# was tried and rejected: it flagged both cited real regeneration sites
# (Albion Square, East Bank Urban Village) as "Excluded", which contradicts
# how development actually proceeds in Hull under the NPPF Sequential/
# Exception Test. Instead FZ3 applies a heavy score penalty - substantially
# stronger than Flood Zone 2 - so flood-exposed land is still marked clearly
# less suitable without erasing most of the city from the map. Greenspace
# remains a hard exclusion since it is genuinely protected/undevelopable
# land, not a risk gradient.
EXCLUSION_OVERLAP_THRESHOLD = 0.5
FLOOD_ZONE_2_PENALTY_FACTOR = 0.5   # multiplies the combined score for flagged cells
FLOOD_ZONE_3_PENALTY_FACTOR = 0.2   # stronger penalty; applied instead of the FZ2 factor


def _overlap_fraction(grid: gpd.GeoDataFrame, polygons: gpd.GeoDataFrame) -> pd.Series:
    """Fraction (0-1) of each grid cell's area covered by `polygons`."""
    empty = pd.Series(0.0, index=grid["cell_id"])
    if polygons.empty:
        return empty

    dissolved = gpd.GeoDataFrame(geometry=[polygons.union_all()], crs=grid.crs)
    overlay = gpd.overlay(grid[["cell_id", "geometry"]], dissolved, how="intersection")
    if overlay.empty:
        return empty

    overlay["area"] = overlay.geometry.area
    cell_area = float(grid.geometry.area.iloc[0])  # uniform, unclipped grid cells
    overlap = overlay.groupby("cell_id")["area"].sum() / cell_area
    return grid["cell_id"].map(overlap).fillna(0.0)


def exclusion_mask(
    grid: gpd.GeoDataFrame,
    greenspace: gpd.GeoDataFrame,
    flood_zones: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """Add `excluded` (bool, hard exclusion - greenspace only), `flood_zone_2`
    and `flood_zone_3` (bool, penalty flags) columns, plus the overlap
    fractions behind them. See the module-level note above on why Flood Zone
    3 is a penalty rather than a hard exclusion."""
    grid = grid.copy()

    greenspace_frac = _overlap_fraction(grid, greenspace)
    fz3_frac = _overlap_fraction(grid, flood_zones.loc[flood_zones["flood_zone"] == "FZ3"])
    fz2_frac = _overlap_fraction(grid, flood_zones.loc[flood_zones["flood_zone"] == "FZ2"])

    grid["greenspace_overlap_frac"] = greenspace_frac.round(3).values
    grid["flood_zone_3_overlap_frac"] = fz3_frac.round(3).values
    grid["excluded"] = (greenspace_frac >= EXCLUSION_OVERLAP_THRESHOLD).values
    grid["flood_zone_2"] = (fz2_frac > 0.0).values
    grid["flood_zone_3"] = (fz3_frac > 0.0).values

    return grid
