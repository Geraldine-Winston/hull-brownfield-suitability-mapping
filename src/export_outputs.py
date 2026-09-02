"""Export the scored suitability grid as static PNG and standalone HTML maps.

Writes:
    outputs/figures/suitability_map.png       static map for the README/reports
    outputs/figures/band_distribution.png     bar chart of cell counts per band
    outputs/suitability_map.html              standalone interactive map (no
                                               Streamlit server needed to view it)

Run `python -m src.suitability_pipeline` first if
data/processed/suitability_grid_100m.gpkg doesn't exist yet, then:

    venv\\Scripts\\python.exe -m src.export_outputs
"""

from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import FIGURES_DIR, OUTPUTS_DIR, PROCESSED_DATA_DIR  # noqa: E402
from src.mapping import BAND_COLORS, build_map, load_context_layers  # noqa: E402
from src.suitability_pipeline import SUITABILITY_BANDS  # noqa: E402

GRID_PATH = PROCESSED_DATA_DIR / "suitability_grid_100m.gpkg"
BOUNDARY_PATH = PROCESSED_DATA_DIR / "administrative_boundary_hull_27700.gpkg"
BAND_ORDER = [label for _, _, label in SUITABILITY_BANDS] + ["Excluded"]


def export_static_map(grid: gpd.GeoDataFrame, boundary: gpd.GeoDataFrame, out_path: Path) -> None:
    """Save a static PNG choropleth of the suitability grid, coloured by band."""
    fig, ax = plt.subplots(figsize=(10, 9))

    for band, color in BAND_COLORS.items():
        subset = grid.loc[grid["suitability_band"] == band]
        if not subset.empty:
            subset.plot(ax=ax, color=color, edgecolor="none")

    boundary.boundary.plot(ax=ax, color="#333333", linewidth=1)

    ax.set_title("Hull Brownfield & Regeneration Site Suitability Map", fontsize=14, fontweight="bold")
    ax.set_axis_off()
    legend_handles = [Patch(facecolor=color, edgecolor="#555555", label=band) for band, color in BAND_COLORS.items()]
    ax.legend(handles=legend_handles, title="Suitability band", loc="lower right", frameon=True)
    ax.annotate(
        "Portfolio/demonstration project - not an official planning tool.\n"
        "EPSG:27700. Equal-weighted ground stability, infill preference and accessibility;\n"
        "Flood Zone 3/2 penalties applied, greenspace hard-excluded.",
        xy=(0.01, 0.01), xycoords="axes fraction", fontsize=7, color="#555555",
    )

    fig.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def export_band_distribution(grid: gpd.GeoDataFrame, out_path: Path) -> None:
    """Save a bar chart of grid cell counts per suitability band."""
    counts = grid["suitability_band"].value_counts().reindex(BAND_ORDER).fillna(0)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar(counts.index, counts.values, color=[BAND_COLORS[b] for b in counts.index], edgecolor="#555555")
    ax.set_title("Suitability band distribution (100m grid cells)", fontsize=12, fontweight="bold")
    ax.set_ylabel("Number of cells")
    for i, value in enumerate(counts.values):
        ax.text(i, value, f"{int(value):,}", ha="center", va="bottom", fontsize=9)

    fig.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def export_interactive_map(grid_wgs84: gpd.GeoDataFrame, context: dict[str, gpd.GeoDataFrame], out_path: Path) -> None:
    """Save the standalone interactive Folium map as self-contained HTML."""
    show_layers = {"flood_zone_3": False, "flood_zone_2": False, "greenspace": False, "major_roads": False}
    fmap = build_map(grid_wgs84, context, show_layers, show_sites=True)
    fmap.save(str(out_path))


def main() -> None:
    if not GRID_PATH.exists():
        raise FileNotFoundError(f"{GRID_PATH} not found - run `python -m src.suitability_pipeline` first.")

    grid = gpd.read_file(GRID_PATH)
    boundary = gpd.read_file(BOUNDARY_PATH)
    context = load_context_layers(BOUNDARY_PATH)

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    png_path = FIGURES_DIR / "suitability_map.png"
    export_static_map(grid, boundary, png_path)
    print(f"Saved: {png_path}")

    band_chart_path = FIGURES_DIR / "band_distribution.png"
    export_band_distribution(grid, band_chart_path)
    print(f"Saved: {band_chart_path}")

    html_path = OUTPUTS_DIR / "suitability_map.html"
    export_interactive_map(grid.to_crs("EPSG:4326"), context, html_path)
    print(f"Saved: {html_path}")


if __name__ == "__main__":
    main()
