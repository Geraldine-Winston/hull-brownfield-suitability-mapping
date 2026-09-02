"""Interactive Streamlit app for the Hull brownfield suitability map.

Loads the pre-scored analysis grid, lets the user adjust sub-score weights
live (the Suitability Index is recombined on every change, so the effect of
each weight is immediately visible), filter by suitability band, toggle
context layers, and click any grid cell to see its underlying sub-scores.

Run `python -m src.suitability_pipeline` first if
data/processed/suitability_grid_100m.gpkg doesn't exist yet, then:

    venv\\Scripts\\python.exe -m streamlit run app/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import streamlit as st
from streamlit_folium import st_folium

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import PROCESSED_DATA_DIR  # noqa: E402
from src.mapping import build_map, load_context_layers  # noqa: E402
from src.suitability_pipeline import SUITABILITY_BANDS, combine_scores  # noqa: E402

st.set_page_config(page_title="Hull Brownfield Suitability Mapping", layout="wide")

GRID_PATH = PROCESSED_DATA_DIR / "suitability_grid_100m.gpkg"
BOUNDARY_PATH = PROCESSED_DATA_DIR / "administrative_boundary_hull_27700.gpkg"

BAND_ORDER = [label for _, _, label in SUITABILITY_BANDS] + ["Excluded"]


@st.cache_data
def load_grid() -> gpd.GeoDataFrame:
    return gpd.read_file(GRID_PATH)


@st.cache_data
def cached_context_layers() -> dict[str, gpd.GeoDataFrame]:
    return load_context_layers(BOUNDARY_PATH)


def main() -> None:
    st.title("Hull Brownfield & Regeneration Site Suitability Mapping")
    st.caption(
        "A reproducible, transparent decision-support tool for identifying regeneration-ready "
        "land in Hull, UK. Portfolio/demonstration project - not an official planning tool and "
        "does not replace statutory planning assessment."
    )

    if not GRID_PATH.exists():
        st.error(f"{GRID_PATH} not found. Run `python -m src.suitability_pipeline` first.")
        return

    grid = load_grid()
    context = cached_context_layers()

    st.sidebar.header("Sub-score weights")
    st.sidebar.caption(
        "Move the sliders to see how the Suitability Index changes - "
        "this is a transparent MCDA model, not a black box. Values are "
        "normalised to sum to 1 automatically."
    )
    w_ground = st.sidebar.slider("Ground stability", 0.0, 1.0, 1 / 3, 0.05)
    w_infill = st.sidebar.slider("Infill preference", 0.0, 1.0, 1 / 3, 0.05)
    w_access = st.sidebar.slider("Accessibility", 0.0, 1.0, 1 / 3, 0.05)

    raw_weights = {
        "ground_stability": w_ground,
        "infill_preference": w_infill,
        "accessibility": w_access,
    }
    total_weight = sum(raw_weights.values()) or 1.0
    weights = {key: value / total_weight for key, value in raw_weights.items()}
    st.sidebar.write({key: round(value, 2) for key, value in weights.items()})

    scored = combine_scores(grid, weights=weights)

    st.sidebar.header("Filter")
    selected_bands = st.sidebar.multiselect("Suitability bands shown", BAND_ORDER, default=BAND_ORDER)

    st.sidebar.header("Map layers")
    show_layers = {
        "flood_zone_3": st.sidebar.checkbox("Flood Zone 3", value=False),
        "flood_zone_2": st.sidebar.checkbox("Flood Zone 2", value=False),
        "greenspace": st.sidebar.checkbox("Greenspace (excluded)", value=False),
        "major_roads": st.sidebar.checkbox("Major roads (accessibility basis)", value=False),
    }
    show_sites = st.sidebar.checkbox("Known regeneration sites", value=True)

    filtered = scored.loc[scored["suitability_band"].isin(selected_bands)]

    col_map, col_stats = st.columns([3, 1])

    with col_stats:
        st.metric("Cells shown", f"{len(filtered):,}")
        scoreable = scored.loc[scored["suitability_band"] != "Excluded", "suitability_index"]
        st.metric("Mean index (non-excluded)", f"{scoreable.mean():.1f}")
        st.subheader("Band counts")
        st.bar_chart(scored["suitability_band"].value_counts().reindex(BAND_ORDER))

    with col_map:
        grid_wgs84 = filtered.to_crs("EPSG:4326")
        fmap = build_map(grid_wgs84, context, show_layers, show_sites)
        st_folium(fmap, width=None, height=650, returned_objects=[])
        st.caption("Click a cell to see its full sub-score breakdown in a popup.")

    st.subheader("Top-scoring cells")
    top_cells = (
        scored.loc[scored["suitability_band"] != "Excluded"]
        .sort_values("suitability_index", ascending=False)
        .head(15)
    )
    st.dataframe(
        top_cells[[
            "cell_id", "suitability_index", "suitability_band",
            "ground_stability", "infill_preference", "accessibility",
        ]].reset_index(drop=True),
        width="stretch",
    )

    with st.expander("Methodology and limitations"):
        st.markdown(
            """
This is a multi-criteria decision analysis (MCDA), not a black-box ML model
- every weight above is visible and adjustable. See the project
[README](https://github.com/Geraldine-Winston/hull-brownfield-suitability-mapping)
for the full methodology, data sources, and documented limitations,
including why Flood Zone 3 is treated as a heavy score penalty rather than
a hard exclusion (a literal hard exclusion covers ~79% of Hull and flagged
both regeneration sites shown on this map as "Excluded").
            """
        )


if __name__ == "__main__":
    main()
