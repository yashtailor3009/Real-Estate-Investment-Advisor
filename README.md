# EstateIQ - Real Estate Investment Advisor

Predicts whether a property is a **Good Investment** (classification) and its **price after 5 years** (regression),
with SQL analytics, a Streamlit dashboard + live SQL playground, MLflow tracking, a PDF report and a deck.

## Quick start
```bash
pip install -r requirements.txt
# put india_housing_prices.csv in data/ (only needed if data/housing_processed.csv is missing)
python scripts/run_pipeline.py      # clean -> SQLite -> train models (MLflow if installed)
streamlit run app.py
mlflow ui                           # optional: experiment dashboard
```
The app rebuilds any missing artefact (processed CSV, DB, models) on first launch.

## Layout
| Path | Purpose |
|---|---|
| `app.py` | Streamlit entry: navigation, filters, routing |
| `views/` | One module per page (overview, explorer, advisor, finder, sql_lab, models, about) |
| `src/config.py` | Paths, palette, thresholds |
| `src/data_processing.py` | Cleaning, features, target rules |
| `src/modeling.py` | Training, comparison, MLflow, importance |
| `src/database.py` | SQLite build, read-only query runner, SQL-file parser |
| `src/predict.py` / `src/visuals.py` / `src/ui.py` | Inference, Plotly charts, UI components |
| `sql/real_estate_analysis.sql` | 33 documented queries |
| `scripts/` | pipeline, logo, PDF report, deck builders |
| `reports/` | Insights PDF, presentation |

## Important
Appreciation, 5-year price and the Good-Investment label are **modelled from domain rules** (the data has no price history).
See the *About & Method* page.
