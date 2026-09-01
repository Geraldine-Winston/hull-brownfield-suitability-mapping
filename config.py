"""Central configuration for file paths and project-wide constants.

Keeps local filesystem paths out of the analysis scripts, per the project's
coding standards (no hardcoded local paths outside this file / a .env).
"""

from pathlib import Path

# Project root = directory containing this file
PROJECT_ROOT = Path(__file__).resolve().parent

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

OUTPUTS_DIR = PROJECT_ROOT / "outputs"
FIGURES_DIR = OUTPUTS_DIR / "figures"

# Target CRS for all analysis (British National Grid)
TARGET_CRS = "EPSG:27700"
