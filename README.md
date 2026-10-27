<p align="center">
  <img src="assets/logo.png" alt="EstateIQ logo" width="420"/>
</p>

<h3 align="center">Real Estate Investment Advisor: Predicting Property Profitability & Future Value</h3>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Streamlit-App-FF4B4B?logo=streamlit&logoColor=white" />
  <img src="https://img.shields.io/badge/scikit--learn-ML-F7931E?logo=scikitlearn&logoColor=white" />
  <img src="https://img.shields.io/badge/SQL-SQLite-003B57?logo=sqlite&logoColor=white" />
  <img src="https://img.shields.io/badge/MLflow-Tracking-0194E2?logo=mlflow&logoColor=white" />
</p>

<p align="center">
  <a href="YOUR-STREAMLIT-CLOUD-LINK">🚀 Live Demo</a> ·
  <a href="reports/EstateIQ_Insights_Report.pdf">📄 Insights Report</a> ·
  <a href="reports/EstateIQ_Presentation.pptx">📊 Presentation</a> ·
  <a href="sql/real_estate_analysis.sql">🗄️ SQL Analysis</a>
</p>

---

## 📌 Overview

**EstateIQ** helps property investors answer two questions using 250,000 Indian housing listings:

1. **Classification:** *Is this property a Good Investment?*
2. **Regression:** *What will its price be after 5 years?*

The project covers data cleaning, feature engineering, SQL analytics, machine learning, experiment tracking
with MLflow, and an interactive Streamlit dashboard with a **live SQL playground**.

## ✨ Features

| Page | What it does |
|---|---|
| 🏠 **Overview** | KPIs, key findings and headline charts |
| 📊 **Market Explorer** | 20 guided EDA questions with annotated, interactive charts and business insights |
| 🔮 **Investment Advisor** | Enter a property to get a verdict, confidence gauge, 5-year price, error band and negotiation target |
| 🔎 **Property Finder** | Filter by area, price, BHK and more; rank by projected gain; download CSV |
| 🗄️ **SQL Lab** | Live read-only SQL playground with 33 ready-made queries and auto-charts |
| 🤖 **Model Insights** | Model comparison, ROC curve, confusion matrix, feature importance |
| ℹ️ **About & Method** | Methodology, target definitions and limitations |

## 📸 Screenshots

<!-- Add your screenshots to an assets/screenshots folder and update the paths -->
| Overview | Investment Advisor |
|---|---|
| ![Overview](assets/screenshots/overview.png) | ![Advisor](assets/screenshots/advisor.png) |

| Market Explorer | SQL Lab |
|---|---|
| ![Explorer](assets/screenshots/explorer.png) | ![SQL Lab](assets/screenshots/sql_lab.png) |

## 🗂️ Project Structure

```
real_estate_advisor/
├── app.py                          # Streamlit entry point (navigation, filters, routing)
├── requirements.txt
├── views/                          # One module per dashboard page
│   ├── overview.py   explorer.py   advisor.py
│   ├── finder.py     sql_lab.py    models.py    about.py
├── src/
│   ├── config.py                   # Paths, brand colours, thresholds
│   ├── data_processing.py          # Cleaning, feature engineering, target rules
│   ├── modeling.py                 # Training, model comparison, MLflow, importance
│   ├── database.py                 # SQLite build, safe read-only query runner
│   ├── predict.py                  # Inference + negotiation-price helper
│   ├── visuals.py                  # Plotly chart builders
│   ├── ui.py                       # Theme CSS and UI components
│   └── utils.py                    # Formatters and insight helpers
├── sql/real_estate_analysis.sql    # 33 documented SQL queries
├── scripts/
│   ├── run_pipeline.py             # Clean data → SQLite → train models
│   ├── make_logo.py                # Logo generator
│   ├── generate_report.py          # Insights PDF
│   ├── export_deck_data.py         # Numbers for the deck
│   └── build_deck.js               # PowerPoint builder
├── data/                           # Raw + processed dataset
├── models/                         # Trained pipelines + metrics
├── assets/                         # Logo files
└── reports/                        # PDF report + presentation
```

## ⚙️ Getting Started

```bash
# 1. Clone
git clone https://github.com/YOUR-USERNAME/YOUR-REPO.git
cd YOUR-REPO

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add the dataset (only needed if data/housing_processed.csv is missing)
#    Place india_housing_prices.csv inside the data/ folder

# 4. Build data, SQLite database and models (MLflow logs if installed)
python scripts/run_pipeline.py

# 5. Launch the app
streamlit run app.py

# Optional: view experiment tracking
mlflow ui
```

> The app also rebuilds any missing artefact automatically on first launch.

## 🔬 Methodology

1. **Preprocessing:** duplicate and missing-value handling, text cleaning, IQR outlier flags, scaling and one-hot encoding inside the model pipeline.
2. **Feature engineering:** price per sq ft in ₹, `Amenity_Count`, `Transport_Score`, `School_Density_Score`, `Infra_Score`, `Floor_Ratio`, `Value_Ratio` (price per sq ft ÷ city median), age and price bands.
3. **SQL analysis:** 33 queries covering data quality, the 20 EDA questions, and window-function/CTE investment deep-dives.
4. **Modelling:** Logistic/Ridge Regression, Random Forest and Gradient Boosting compared for each task on a stratified 80/20 split.
5. **Deployment:** Streamlit app with filters, predictions, confidence scores and feature importance.

### ⚠️ How the targets are defined
The dataset has **no price history and no investment label**, so both are derived from transparent domain rules:

| Component | Effect on annual appreciation |
|---|---|
| Base rate | 4.5% |
| Infrastructure (schools, hospitals, transit) | up to +3.0% |
| Amenities / security / parking | up to +1.2% / +0.8% / +0.6% |
| Under construction | +1.0% |
| Newer building | up to +1.0% |
| Price vs city median (cheaper is better) | −2.0% to +2.0% |
| Simulated market noise | N(0, 0.8%) |

- **5-year price** = price × (1 + appreciation)⁵
- **Good Investment** = appreciation ≥ 9% **and** price per sq ft ≤ 1.5× the city median (≈39% of listings)

## 📈 Results

| Task | Best model | Result |
|---|---|---|
| Classification | Gradient Boosting | **87.6% accuracy**, ROC-AUC **0.953**, F1 0.844 |
| Regression (5-year price) | Gradient Boosting | **RMSE 16.1 lakhs**, R² **0.994** (naive baseline RMSE 34.9) |

> These scores show how well the models learn the rule-based targets (plus noise), not accuracy on real sale prices.

## 🔍 Key Insights

- **Entry price vs the city median is the biggest lever:** deep-discount listings qualify as Good Investments 81% of the time versus 28% just above the median (modelled).
- **Prices are flat across location and features:** state, city, property type, furnishing, facing and transit differ by under 5% in price per sq ft.
- **Size drives price per sq ft:** correlation of −0.61, while total price is unrelated to size.
- **Data-quality issue:** about 46.5% of rows list a floor above the building's height.
- **Under-construction, well-connected, amenity-rich homes** score highest in the investment model.

## ⚠️ Limitations

- Appreciation and 5-year prices are scenario-based, not real forecasts. Replace the rule engine with historical transaction data for production use.
- The descriptive data shows almost no link between price and location or amenities.
- The dataset has no crime-rate field, so that analysis from the brief was not possible.
- This is decision support, not financial advice.

## 🛠️ Tech Stack

Python · Pandas · NumPy · scikit-learn · Plotly · Streamlit · SQLite · MLflow · Matplotlib · ReportLab · PptxGenJS

## 🚀 Deployment (Streamlit Community Cloud)

1. Push the repo to GitHub (see the large-file note below).
2. Go to [share.streamlit.io](https://share.streamlit.io), choose the repo and set the main file to `app.py`.
3. Deploy. The app builds the database and models on first run.

> **Large files:** the processed CSV is ~64 MB, under GitHub's 100 MB limit. Add `data/real_estate.db` and `mlruns/` to `.gitignore`, since they are rebuilt automatically.

## 🗺️ Roadmap

- [ ] Replace rule-based targets with real historical prices
- [ ] Add rental yield and EMI calculators to the advisor
- [ ] Validate floor numbers at data entry
- [ ] Scheduled monthly model retraining

## 📄 License

Released under the [MIT License](LICENSE).

## 👤 Author

**Yash Tailor** · [LinkedIn]([https://linkedin.com/in/YOUR-PROFILE](https://www.linkedin.com/in/yash-tailor-054373342/)) 

⭐ If you found this project useful, please star the repository!
