"""
config.py
=========
Single source of truth for paths, brand colours and modelling constants.
Keeping these in one place means a change (e.g. the "Good Investment"
threshold) is made once and flows through the pipeline, models and UI.
"""
from pathlib import Path

# ----------------------------------------------------------------- paths
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
MODEL_DIR = ROOT / "models"
SQL_DIR = ROOT / "sql"
ASSET_DIR = ROOT / "assets"
REPORT_DIR = ROOT / "reports"

RAW_CSV = DATA_DIR / "india_housing_prices.csv"
PROCESSED_CSV = DATA_DIR / "housing_processed.csv"
DB_PATH = DATA_DIR / "real_estate.db"
SQL_FILE = SQL_DIR / "real_estate_analysis.sql"
LOGO_PNG = ASSET_DIR / "logo.png"

CLASSIFIER_PATH = MODEL_DIR / "classifier.joblib"
REGRESSOR_PATH = MODEL_DIR / "regressor.joblib"
METRICS_PATH = MODEL_DIR / "metrics.json"
LOOKUP_PATH = MODEL_DIR / "lookup.json"

# ----------------------------------------------------------- brand colours
PALETTE = {
    "navy": "#0B1F3A",
    "navy_soft": "#16325C",
    "teal": "#14B8A6",
    "teal_dark": "#0F766E",
    "gold": "#F5B83D",
    "coral": "#F2674B",
    "bg": "#F4F7FB",
    "card": "#FFFFFF",
    "text": "#1B2B44",
    "muted": "#6B7A90",
}
# Ordered colour sequence used by every chart for visual consistency
COLOR_SEQ = ["#14B8A6", "#16325C", "#F5B83D", "#F2674B", "#7C5CFC", "#38BDF8"]

# --------------------------------------------------- domain / modelling rules
CURRENT_YEAR = 2025          # dataset: Year_Built + Age_of_Property == 2025
FORECAST_YEARS = 5           # regression horizon required by the brief
LAKH = 100_000               # 1 lakh = 100,000 INR
RANDOM_STATE = 42

# "Good Investment" rule (see data_processing.add_investment_targets)
GOOD_APPRECIATION_THRESHOLD = 0.090   # projected appreciation >= 9.0 % / year
MAX_VALUE_RATIO = 1.5                 # and not priced >1.5x the city median

# Feature groups used by the ML pipelines
NUMERIC_FEATURES = [
    "BHK", "Size_in_SqFt", "Price_in_Lakhs", "Price_per_SqFt_INR",
    "Age_of_Property", "Floor_No", "Total_Floors", "Floor_Ratio",
    "Nearby_Schools", "Nearby_Hospitals", "Transport_Score",
    "Amenity_Count", "School_Density_Score", "Infra_Score", "Value_Ratio",
    "Parking_Flag", "Security_Flag",
]
CATEGORICAL_FEATURES = [
    "State", "City", "Property_Type", "Furnished_Status", "Facing",
    "Owner_Type", "Availability_Status",
]
CLASSIFICATION_TARGET = "Good_Investment"
REGRESSION_TARGET = "Future_Price_5Y_Lakhs"
