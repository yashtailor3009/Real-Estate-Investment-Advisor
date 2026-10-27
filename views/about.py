"""About & Method: methodology, target definitions, data dictionary and limitations."""
import streamlit as st

from src import config as C, ui


def render():
    ui.hero("About & Method", "How the data was cleaned, how the investment targets were defined, and what to keep in mind.",
            ["Transparent rules", "Reproducible"])
    st.markdown(f"""
### 1 · Data preparation
- **250,000 listings**, 20 states, 42 cities, 500 localities; no missing values or duplicate rows were found (the code still handles both).
- `Price_per_SqFt` in the source is in *lakhs per sq ft*; we add `Price_per_SqFt_INR` (₹ per sq ft) for readability.
- **Data-quality flag:** ~46.5% of rows list a `Floor_No` above `Total_Floors`. Rows are kept and flagged; `Floor_Ratio` is clipped to 1.
- **Outliers:** IQR flags (not removal) - ~7.9% of price/sq ft values are high outliers; size has none.

### 2 · Engineered features
`Amenity_Count`, `Transport_Score`, `School_Density_Score`, `Infra_Score` (0-100), `Floor_Ratio`, `Value_Ratio` (price/sq ft ÷ city median),
`Parking_Flag`, `Security_Flag`, `Age_Band`, `Price_Band`.

### 3 · How the targets are defined (important)
The raw file has **no price history and no investment label**, so the brief's targets are derived from transparent domain rules:

| Component | Effect on annual appreciation |
|---|---|
| Base rate | 4.5% |
| Infrastructure (schools, hospitals, transit) | up to +3.0% |
| Amenities / security / parking | up to +1.2% / +0.8% / +0.6% |
| Under construction | +1.0% |
| Newer building | up to +1.0% |
| Price vs city median (cheaper = better) | -2.0% to +2.0% |
| Market noise | N(0, 0.8%) |

- **5-year price** = today's price × (1 + appreciation)⁵
- **Good Investment** = appreciation ≥ **{C.GOOD_APPRECIATION_THRESHOLD * 100:.0f}%** *and* price/sq ft ≤ **{C.MAX_VALUE_RATIO}×** the city median

### 4 · Limitations
- Investment metrics are **scenario-based**. Replace the rule engine with real historical prices to turn this into a true forecast.
- The descriptive data shows almost no relationship between price and location, amenities or neighbourhood - typical of synthetic data.
- The brief mentions crime rate; the dataset has no crime field, so that analysis is not possible.
- Not financial advice.

### 5 · Run it yourself
```bash
pip install -r requirements.txt
python scripts/run_pipeline.py     # clean data, build SQLite DB, train + track models
streamlit run app.py
```
""")
