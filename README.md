# Hull Brownfield & Regeneration Site Suitability Mapping

A reproducible, transparent decision-support tool for identifying
regeneration-ready land in Hull, UK.

## Problem

Hull City Council's [Council Plan 2024-2028](https://www.hull.gov.uk/) sets out
active regeneration priorities across the city — including the East Bank Urban
Village, Albion Square, the Priority Streets programme, and the wider Hull
Housing Strategy 2023-2030. Identifying which parcels of land are realistically
suitable for redevelopment involves weighing multiple, often competing factors:
ground stability, flood risk, existing development density, and accessibility.

This project builds a **multi-criteria suitability model** that scores areas of
Hull for redevelopment potential and presents the results as an interactive web
map, so the reasoning behind every score is visible and auditable rather than
hidden inside a black-box model.

> **This is a portfolio/demonstration project.** It does not replace statutory
> planning assessment, site surveys, or official council evaluation, and it
> should not be used as the basis for real investment or planning decisions.

## Relationship to other work in this portfolio

This project is deliberately distinct from the author's MSc dissertation, which
modelled surface-water flood vulnerability using machine learning. Here, flood
zone data is used only as an *exclusion/constraint layer* to rule out clearly
unsuitable land — it is not the analytical focus, and no flood vulnerability
modelling methodology from the dissertation is reproduced.

## Methodology

A multi-criteria decision analysis (MCDA), not a machine-learning model:

1. Load and reproject all vector layers to a common CRS (EPSG:27700, British
   National Grid).
2. Define a unit of analysis (a regular grid or administrative sub-areas).
3. Derive suitability sub-scores per unit:
   - **Ground stability** — from BGS bedrock geology classes.
   - **Development density** — distance from existing buildings (infill vs.
     greenfield preference).
   - **Exclusions** — areas intersecting greenspace or Flood Zone 3 are
     excluded outright; Flood Zone 2 is a partial penalty, not a hard
     exclusion.
   - **Accessibility** — distance to the road network.
4. Combine sub-scores into a single weighted Suitability Index (0–100), with
   weights documented and justified explicitly.
5. Classify units into suitability bands (Low / Medium / High / Prime).
6. Sense-check results against known real regeneration sites (e.g. Albion
   Square, East Bank) to confirm they fall into higher suitability bands.

## Data

All source layers live in `data/raw/` and are pre-clipped to Hull. See
`data/raw/dataset_validation_links.xlsx` for source metadata.

| Layer | Purpose |
|---|---|
| `Building_Hull1.shp` | Building footprints — development density |
| `Administrative boundary_Hull.shp` | Hull administrative boundary |
| `GB_GreenspaceSite_Hull.shp` | Protected green space — exclusion layer |
| `625k_V5_BEDROCK_Geology_Polygons_Hull.shp` | Bedrock geology — ground stability proxy |
| `UK_625k_SUPERFICIAL_Geology_Polygons_Hull.shp` | Superficial geology |
| `Flood_Zones_2_3_Rivers__Hull_Clip.shp` | EA flood zones — exclusion/constraint layer only |
| `Roads_Hall1.shp` | Road network — accessibility scoring |
| `Hist Surface Water Flood Record_Hull.shp`, `HydroNode_Hull.shp`, `WatercourseLink_Hull.shp` | Supplementary hydrology context |

Run `src/inspect_data.py` (see below) to confirm each layer's CRS before any
analysis — one source layer (the administrative boundary) is in WGS84 and
needs reprojecting to EPSG:27700 to match the rest.

## Project structure

```
data/
  raw/          source shapefiles (as supplied)
  processed/    cleaned/reprojected/derived layers (generated, gitignored)
notebooks/      exploratory analysis
src/            reproducible pipeline code
app/            interactive Streamlit web app
outputs/        exported maps and figures
config.py       central file paths and constants (no hardcoded paths elsewhere)
```

## How to run

Requires Python 3.11+.

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
```

Inspect the raw data (CRS, feature counts, columns) before running the
pipeline:

```bash
python -m src.inspect_data
```

## Status

🚧 Work in progress. Current stage: data loading and CRS verification.

## Limitations

- This is a demonstration MCDA model with illustrative weights, not a
  validated planning tool.
- Suitability weights reflect the author's judgement, documented for
  transparency, and should be reviewed by a domain expert before any
  real-world use.
- Flood exclusion is based on EA Flood Zones 2/3 only; it is not a substitute
  for a full Flood Risk Assessment.

## License

MIT — see [LICENSE](LICENSE).

## Author

Ayebawanaemi Geraldine Winston — MSc Data Science. Part of a portfolio series;
see also the [surface-water flood vulnerability dissertation
repo](https://github.com/Geraldine-Winston) *(link to be added)*.
