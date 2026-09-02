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

import folium
import geopandas as gpd
import streamlit as st
from streamlit_folium import st_folium

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import PROCESSED_DATA_DIR, RAW_DATA_DIR  # noqa: E402
from src.scoring import MAJOR_ROAD_KEYWORDS  # noqa: E402
from src.suitability_pipeline import SUITABILITY_BANDS, combine_scores  # noqa: E402

st.set_page_config(page_title="Hull Brownfield Suitability Mapping", layout="wide")

GRID_PATH = PROCESSED_DATA_DIR / "suitability_grid_100m.gpkg"
BOUNDARY_PATH = PROCESSED_DATA_DIR / "administrative_boundary_hull_27700.gpkg"

BAND_ORDER = [label for _, _, label in SUITABILITY_BANDS] + ["Excluded"]
BAND_COLORS = {
    "Excluded": "#8c8c8c",
    "Low": "#d73027",
    "Medium": "#fee08b",
    "High": "#a6d96a",
    "Prime": "#1a9850",
}

# Approximate landmark-level coordinates (not exact site boundaries) for
# known real regeneration sites, shown on the map for face-validity
# orientation only - see the README for the full discussion.
REGENERATION_SITES = {
    "Albion Square": (53.7448, -0.3352),
    "East Bank Urban Village": (53.7515, -0.3255),
}

HULL_CENTRE = (53.76775, -0.335827)


@st.cache_data
def load_grid() -> gpd.GeoDataFrame:
    return gpd.read_file(GRID_PATH)


@st.cache_data
def load_context_layers() -> dict[str, gpd.GeoDataFrame]:
    boundary = gpd.read_file(BOUNDARY_PATH).to_crs("EPSG:4326")
    greenspace = gpd.read_file(RAW_DATA_DIR / "GB_GreenspaceSite_Hull.shp").to_crs("EPSG:4326")
    flood_zones = gpd.read_file(RAW_DATA_DIR / "Flood_Zones_2_3_Rivers__Hull_Clip.shp").to_crs("EPSG:4326")
    roads = gpd.read_file(RAW_DATA_DIR / "Roads_Hall1.shp").to_crs("EPSG:4326")
    is_major = roads["CLASSIFICA"].str.contains("|".join(MAJOR_ROAD_KEYWORDS), na=False)

    return {
        "boundary": boundary,
        "greenspace": greenspace,
        "flood_zone_3": flood_zones.loc[flood_zones["flood_zone"] == "FZ3"],
        "flood_zone_2": flood_zones.loc[flood_zones["flood_zone"] == "FZ2"],
        "major_roads": roads.loc[is_major],
    }


def build_map(
    grid_wgs84: gpd.GeoDataFrame,
    context: dict[str, gpd.GeoDataFrame],
    show_layers: dict[str, bool],
    show_sites: bool,
) -> folium.Map:
    m = folium.Map(location=HULL_CENTRE, zoom_start=12, tiles="CartoDB positron")

    folium.GeoJson(
        context["boundary"],
        name="Hull administrative boundary",
        style_function=lambda _: {"fill": False, "color": "#333333", "weight": 2},
    ).add_to(m)

    if show_layers["flood_zone_3"]:
        folium.GeoJson(
            context["flood_zone_3"],
            name="Flood Zone 3 (heavy penalty)",
            style_function=lambda _: {
                "fillColor": "#3182bd", "color": "#3182bd", "weight": 0, "fillOpacity": 0.25
            },
        ).add_to(m)

    if show_layers["flood_zone_2"]:
        folium.GeoJson(
            context["flood_zone_2"],
            name="Flood Zone 2 (partial penalty)",
            style_function=lambda _: {
                "fillColor": "#9ecae1", "color": "#9ecae1", "weight": 0, "fillOpacity": 0.25
            },
        ).add_to(m)

    if show_layers["greenspace"]:
        folium.GeoJson(
            context["greenspace"],
            name="Greenspace (hard exclusion)",
            style_function=lambda _: {
                "fillColor": "#2ca25f", "color": "#2ca25f", "weight": 0, "fillOpacity": 0.45
            },
        ).add_to(m)

    if show_layers["major_roads"]:
        folium.GeoJson(
            context["major_roads"],
            name="Major roads (accessibility basis)",
            style_function=lambda _: {"color": "#756bb1", "weight": 2},
        ).add_to(m)

    def style_grid_cell(feature: dict) -> dict:
        band = feature["properties"]["suitability_band"]
        return {
            "fillColor": BAND_COLORS.get(band, "#cccccc"),
            "color": "#555555",
            "weight": 0.2,
            "fillOpacity": 0.75,
        }

    tooltip_fields = [
        "cell_id", "suitability_band", "suitability_index",
        "ground_stability", "infill_preference", "accessibility",
        "flood_zone_2", "flood_zone_3",
    ]
    tooltip_aliases = [
        "Cell ID", "Suitability band", "Suitability index",
        "Ground stability", "Infill preference", "Accessibility",
        "In Flood Zone 2", "In Flood Zone 3",
    ]

    folium.GeoJson(
        grid_wgs84,
        name="Suitability grid",
        style_function=style_grid_cell,
        highlight_function=lambda _: {"weight": 2.5, "color": "#000000"},
        tooltip=folium.GeoJsonTooltip(fields=tooltip_fields, aliases=tooltip_aliases, localize=True),
        popup=folium.GeoJsonPopup(fields=tooltip_fields, aliases=tooltip_aliases, localize=True),
    ).add_to(m)

    if show_sites:
        for name, (lat, lon) in REGENERATION_SITES.items():
            folium.Marker(
                location=[lat, lon],
                tooltip=name,
                popup=(
                    f"<b>{name}</b><br>Known real regeneration site "
                    "(approximate landmark coordinate, not exact site boundary)."
                ),
                icon=folium.Icon(color="darkblue", icon="star"),
            ).add_to(m)

    legend_html = "".join(
        f'<div><span style="background:{color};width:12px;height:12px;'
        f'display:inline-block;margin-right:6px;border:1px solid #555;"></span>{band}</div>'
        for band, color in BAND_COLORS.items()
    )
    m.get_root().html.add_child(folium.Element(
        f'<div style="position:fixed;bottom:20px;left:20px;z-index:9999;'
        f'background:white;padding:8px 10px;border:1px solid #999;border-radius:4px;'
        f'font-size:12px;box-shadow:1px 1px 4px rgba(0,0,0,0.3);">'
        f'<b>Suitability band</b>{legend_html}</div>'
    ))

    folium.LayerControl(collapsed=False).add_to(m)
    return m


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
    context = load_context_layers()

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
