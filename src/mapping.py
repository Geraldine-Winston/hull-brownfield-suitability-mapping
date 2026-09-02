"""Shared Folium map-building logic for the Streamlit app and the static
HTML/PNG export script, so both stay visually consistent from one source.
"""

from __future__ import annotations

import sys
from pathlib import Path

import folium
import geopandas as gpd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import RAW_DATA_DIR  # noqa: E402
from src.scoring import MAJOR_ROAD_KEYWORDS  # noqa: E402

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


def load_context_layers(boundary_path: Path) -> dict[str, gpd.GeoDataFrame]:
    """Load the boundary and the raw context layers (greenspace, flood
    zones, major roads), all reprojected to WGS84 for Folium."""
    boundary = gpd.read_file(boundary_path).to_crs("EPSG:4326")
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
    """Build the interactive suitability Folium map: grid coloured by band,
    optional context layers, regeneration-site markers, and a legend."""
    m = folium.Map(location=HULL_CENTRE, zoom_start=12, tiles="OpenStreetMap")

    folium.GeoJson(
        context["boundary"],
        name="Hull administrative boundary",
        style_function=lambda _: {"fill": False, "color": "#333333", "weight": 2},
    ).add_to(m)

    if show_layers.get("flood_zone_3"):
        folium.GeoJson(
            context["flood_zone_3"],
            name="Flood Zone 3 (heavy penalty)",
            style_function=lambda _: {
                "fillColor": "#3182bd", "color": "#3182bd", "weight": 0, "fillOpacity": 0.25
            },
        ).add_to(m)

    if show_layers.get("flood_zone_2"):
        folium.GeoJson(
            context["flood_zone_2"],
            name="Flood Zone 2 (partial penalty)",
            style_function=lambda _: {
                "fillColor": "#9ecae1", "color": "#9ecae1", "weight": 0, "fillOpacity": 0.25
            },
        ).add_to(m)

    if show_layers.get("greenspace"):
        folium.GeoJson(
            context["greenspace"],
            name="Greenspace (hard exclusion)",
            style_function=lambda _: {
                "fillColor": "#2ca25f", "color": "#2ca25f", "weight": 0, "fillOpacity": 0.45
            },
        ).add_to(m)

    if show_layers.get("major_roads"):
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
