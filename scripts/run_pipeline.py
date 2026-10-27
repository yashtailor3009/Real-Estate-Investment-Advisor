"""
run_pipeline.py
===============
One command to rebuild everything:

    python scripts/run_pipeline.py

1. cleans the raw CSV and engineers features/targets  -> data/housing_processed.csv
2. loads the data into SQLite                          -> data/real_estate.db
3. trains + compares models (MLflow if installed)      -> models/*.joblib, metrics.json
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config as C                       # noqa: E402
from src import data_processing as dp             # noqa: E402
from src.database import build_database           # noqa: E402
from src.modeling import train_all                # noqa: E402

if __name__ == "__main__":
    print("1/3 Processing data ...")
    df = dp.build_processed_dataset()
    print(f"    {len(df):,} rows x {df.shape[1]} columns")
    print("2/3 Building SQLite database ...")
    build_database(df)
    print("3/3 Training models ...")
    m = train_all(df)
    print("Done. Best classifier:", m["classification"]["best_model"],
          "| best regressor:", m["regression"]["best_model"])
