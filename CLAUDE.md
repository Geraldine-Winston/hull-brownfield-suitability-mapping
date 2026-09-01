# Project: Hull Brownfield & Regeneration Site Suitability Mapping

## Who this is for
This is a portfolio project by Ayebawanaemi Geraldine Winston, an MSc Data Science
graduate targeting geospatial data scientist roles in the UK. This project must be
built to a professional standard suitable for a public GitHub portfolio and job
applications (GIS consultancies, local government, real estate/insurance analytics).

## Objective
Build a GIS-based multi-criteria suitability model that scores land parcels/areas
across Hull, UK for redevelopment potential (housing, mixed-use regeneration),
and present it as an interactive web map. This directly supports Hull City Council's
active regeneration priorities (East Bank Urban Village, Albion Square, Priority
Streets programme, Hull Housing Strategy 2023-2030).

This project is DELIBERATELY DIFFERENT from the author's dissertation
(surface-water flood vulnerability ML modelling). Flood zone data may be used ONLY
as an exclusion/constraint layer (ruling out clearly unsuitable land), never as the
main analytical focus. Do not reproduce flood vulnerability modelling methodology.

## Data available (in ./data/raw/)
- `Building_Hull1.shp` — building footprints for Hull
- `Administrative boundary_Hull.shp` — Hull administrative/ward boundaries
- `GB_GreenspaceSite_Hull.shp` — green space polygons (protected land, exclusion layer)
- `625k_V5_BEDROCK_Geology_Polygons_Hull.shp` — bedrock geology (ground stability proxy)
- `Flood_Zones_2_3_Rivers__Hull_Clip.shp` — EA flood zones (exclusion/constraint layer ONLY)
- `dataset_validation_links.xlsx` — source metadata for the above

All layers are pre-clipped to Hull. Check `.prj` files for CRS before combining
(likely British National Grid, EPSG:27700) and reproject consistently.

## Suggested additional open data to fetch (if internet available)
- OS Open Roads or OSM roads (accessibility scoring)
- ONS mid-year population estimates or Census 2021 (demand proxy)
- Hull City Council open data portal — vacant/derelict land register if published
- English Indices of Deprivation 2019 (context only, not primary driver here —
  save deprivation-led modelling for a separate future project)

## Methodology (multi-criteria suitability analysis)
1. Load and reproject all layers to a common CRS (EPSG:27700).
2. Create a regular grid or use administrative sub-areas as the unit of analysis.
3. Derive suitability sub-scores per unit:
   - Ground stability (from geology classes — flag known unstable/made-ground types)
   - Distance from existing building density (infill vs. greenfield preference)
   - Exclusion mask: remove areas that intersect greenspace or Flood Zone 3
     (Flood Zone 2 can be a partial penalty, not a hard exclusion)
   - Accessibility (distance to roads/amenities, if road data added)
4. Combine sub-scores into a single weighted Suitability Index (0-100).
   Document weights clearly and justify them — this is a multi-criteria decision
   analysis (MCDA), not a black-box ML model, and should be presented as such.
5. Classify into suitability bands (e.g. Low/Medium/High/Prime).
6. Validate face-validity by checking whether known real regeneration sites
   (e.g. Albion Square, East Bank area — approximate coordinates, cite source)
   fall into higher suitability bands.

## Deliverables
1. `notebooks/` or `src/` — clean, documented, reproducible Python pipeline
   (geopandas, shapely, rasterio if needed)
2. `app/` — an interactive Streamlit (or Folium/Leaflet) web app letting a user
   explore the suitability map, click areas, and see sub-scores
3. `README.md` — professional README: problem statement tied to Hull's real
   regeneration priorities (cite Hull Council Plan 2024-2028), methodology
   summary, how to run, screenshots, limitations
4. `outputs/` — exported suitability map (PNG/HTML), key figures
5. Clear MIT or CC license and requirements.txt / environment.yml

## Tone and framing for README/article
Frame this as: "A reproducible, transparent decision-support tool for identifying
regeneration-ready land in Hull" — emphasise transparency of weights (unlike a
black-box model), and explicitly state this is a portfolio/demonstration project,
not an official planning tool, and does not replace statutory planning assessment.

## Coding standards
- Python 3.11+, use geopandas/shapely for vector ops
- Type hints, docstrings, small functions
- No hardcoded local file paths outside a `config.py` or `.env`
- Include a `.gitignore` excluding large raw data if it exceeds GitHub limits
  (use Git LFS or provide a data-download script instead if files are large)

## Git/GitHub
- Repo name suggestion: `hull-brownfield-suitability-mapping`
- Commit incrementally with clear messages as each stage is built
- Public repo, link it in the README back to the author's dissertation repo
  as part of a portfolio series
