"""Export the scored suitability grid as static PNG and standalone HTML maps.

Writes:
    outputs/figures/suitability_map.png        static map for the README/reports
    outputs/figures/band_distribution.png      bar chart of cell counts per band
    outputs/figures/methodology_flowchart.png  pipeline diagram (raw data to bands)
    outputs/suitability_map.html               standalone interactive map (no
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
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Patch

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


def export_methodology_flowchart(out_path: Path) -> None:
    """Save a vertical flowchart of the pipeline stages, from raw shapefiles
    to classified suitability bands. Purely diagrammatic - not derived from
    data - but every stage name/value mirrors the actual code (src/grid.py,
    src/scoring.py, src/suitability_pipeline.py)."""
    # Each row is either a single box (str) or several parallel boxes (list[str]).
    rows: list[str | list[str]] = [
        "Raw shapefiles\n(data/raw/)",
        "Reproject to EPSG:27700\n(British National Grid)",
        "Build 100m x 100m grid\nclipped to Hull boundary\n(5,665 cells)",
        ["Ground stability\n(superficial geology)", "Infill preference\n(distance to buildings)", "Accessibility\n(distance to major roads)"],
        ["Greenspace:\nhard exclusion", "Flood Zone 3:\n x0.2 penalty", "Flood Zone 2:\n x0.5 penalty"],
        "Weighted combination\n(equal thirds) ->\nSuitability Index (0-100)",
        "Classify into bands\nLow / Medium / High / Prime / Excluded",
        "Face-validity check\n(Albion Square, East Bank Urban Village)",
    ]

    box_h = 0.8
    row_gap = 1.4
    n_rows = len(rows)
    fig_h = n_rows * row_gap + 1
    fig, ax = plt.subplots(figsize=(7.5, fig_h))

    def draw_box(cx: float, cy: float, w: float, text: str, color: str = "#f0f0f0") -> None:
        box = FancyBboxPatch(
            (cx - w / 2, cy - box_h / 2), w, box_h,
            boxstyle="round,pad=0.08,rounding_size=0.08",
            linewidth=1.2, edgecolor="#333333", facecolor=color,
        )
        ax.add_patch(box)
        ax.text(cx, cy, text, ha="center", va="center", fontsize=8.5, wrap=True)

    row_colors = ["#f0f0f0"] * 3 + ["#deebf7"] + ["#fee8c8"] + ["#f0f0f0", "#f0f0f0", "#e5f5e0"]
    centers_y = [n_rows - i for i in range(n_rows)]

    for row, cy, color in zip(rows, centers_y, row_colors):
        if isinstance(row, list):
            n = len(row)
            total_w = 6.4
            box_w = total_w / n - 0.2
            xs = [(-total_w / 2 + box_w / 2 + 0.2) + i * (box_w + 0.2) for i in range(n)]
            for x, label in zip(xs, row):
                draw_box(x, cy, box_w, label, color)
        else:
            draw_box(0, cy, 4.4, row, color)

    for cy_from, cy_to in zip(centers_y[:-1], centers_y[1:]):
        arrow = FancyArrowPatch(
            (0, cy_from - box_h / 2), (0, cy_to + box_h / 2),
            arrowstyle="-|>", mutation_scale=14, linewidth=1.2, color="#333333",
        )
        ax.add_patch(arrow)

    ax.set_xlim(-3.6, 3.6)
    ax.set_ylim(0.2, n_rows + 0.8)
    ax.set_title("Suitability scoring pipeline", fontsize=13, fontweight="bold")
    ax.set_axis_off()

    fig.tight_layout()
    fig.savefig(out_path, dpi=250, bbox_inches="tight")
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

    flowchart_path = FIGURES_DIR / "methodology_flowchart.png"
    export_methodology_flowchart(flowchart_path)
    print(f"Saved: {flowchart_path}")

    html_path = OUTPUTS_DIR / "suitability_map.html"
    export_interactive_map(grid.to_crs("EPSG:4326"), context, html_path)
    print(f"Saved: {html_path}")


if __name__ == "__main__":
    main()
