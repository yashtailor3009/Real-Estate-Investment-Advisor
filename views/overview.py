"""Overview page: hero, headline KPIs, key findings and four anchor charts."""
import streamlit as st

from src import ui, visuals as V
from src.utils import fmt_money, fmt_int


def render(df):
    ui.hero("Real Estate Investment Advisor",
            "Data-backed answers to two questions: is this a good investment, and what will it be worth in 5 years?",
            ["250K listings", "20 states · 42 cities", "ML + SQL + Streamlit"])
    if df.empty:
        st.warning("No listings match the current filters. Widen the filters in the sidebar.")
        return

    # ---- KPI row
    c = st.columns(5)
    with c[0]: ui.kpi("Listings analysed", fmt_int(len(df)), "after current filters", "#14B8A6")
    with c[1]: ui.kpi("Average price", fmt_money(df["Price_in_Lakhs"].mean()), f"median {fmt_money(df['Price_in_Lakhs'].median())}", "#16325C")
    with c[2]: ui.kpi("Median ₹ / sq ft", f"₹{df['Price_per_SqFt_INR'].median():,.0f}", "robust to outliers", "#F5B83D")
    with c[3]: ui.kpi("Good investments", f"{df['Good_Investment'].mean() * 100:.1f}%", "modelled label", "#F2674B")
    with c[4]: ui.kpi("Avg 5-year gain", fmt_money(df["Projected_Gain_Lakhs"].mean()), f"{df['Annual_Appreciation'].mean() * 100:.1f}% a year (modelled)", "#7C5CFC")
    st.write("")

    # ---- Key findings (computed from the filtered data)
    ready = df.groupby("Availability_Status", observed=True)["Good_Investment"].mean()
    below = df[df["Value_Ratio"] < 1]["Good_Investment"].mean()
    above = df[df["Value_Ratio"] >= 1]["Good_Investment"].mean()
    a, b, d = st.columns(3)
    with a:
        ui.insight(f"Listings priced <b>below their city median</b> qualify as Good Investments <b>{below * 100:.0f}%</b> of the time vs "
                   f"<b>{above * 100:.0f}%</b> above it.", "Buy below the median", "good")
    with b:
        gap = (ready.get("Under_Construction", 0) - ready.get("Ready_to_Move", 0)) * 100
        ui.insight(f"Under-construction homes beat ready-to-move on Good-Investment rate by <b>{gap:.0f} points</b> (modelled upside on completion).",
                   "Timing matters")
    with d:
        ui.insight("Raw prices barely differ by state, city, furnishing or facing. <b>Entry price vs the local median</b> and "
                   "<b>infrastructure</b> are what separate winners.", "Where the signal is", "warn")

    ui.insight("<b>Good Investment</b>, <b>Annual Appreciation</b> and <b>5-year price</b> are <i>modelled</i> from transparent domain rules "
               "(the raw file has no price history). Descriptive charts (price, size, location) are observed data; investment metrics are scenario-based. "
               "See <i>About & Method</i>.", "Read this first", "warn")

    # ---- Anchor charts
    l, r = st.columns(2)
    with l: ui.plot(V.price_distribution(df), "ov_price")
    with r: ui.plot(V.valuation_band_chart(df), "ov_val")
    l, r = st.columns(2)
    with l: ui.plot(V.appreciation_hist(df), "ov_app")
    with r: ui.plot(V.future_vs_current(df), "ov_future")
