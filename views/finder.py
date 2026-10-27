"""Property Finder: filter listings by area, price, BHK and rank by investment potential."""
import streamlit as st

from src import ui, visuals as V
from src.utils import fmt_money


def render(df):
    ui.hero("Property Finder", "Shortlist listings that match your budget and rank them by projected 5-year gain.",
            ["Filter by area, price, BHK", "Download your shortlist"])
    with st.expander("🔎 Refine your search (sidebar filters apply too)", expanded=True):
        c = st.columns(4)
        size = c[0].slider("Size (sq ft)", 500, 5000, (500, 5000), step=100)
        avail = c[1].multiselect("Availability", sorted(df["Availability_Status"].unique()))
        transit = c[2].multiselect("Public transport", ["High", "Medium", "Low"])
        min_infra = c[3].slider("Min infrastructure score", 0, 100, 0)
        c = st.columns(4)
        only_good = c[0].toggle("Only 'Good Investment'", value=True)
        parking = c[1].toggle("Parking required", value=False)
        sec = c[2].toggle("Security required", value=False)
        sort_by = c[3].selectbox("Rank by", ["Projected_Gain_Lakhs", "Annual_Appreciation", "Value_Ratio", "Price_in_Lakhs"])

    d = df[df["Size_in_SqFt"].between(*size) & (df["Infra_Score"] >= min_infra)]
    if avail: d = d[d["Availability_Status"].isin(avail)]
    if transit: d = d[d["Public_Transport_Accessibility"].isin(transit)]
    if only_good: d = d[d["Good_Investment"] == 1]
    if parking: d = d[d["Parking_Flag"] == 1]
    if sec: d = d[d["Security_Flag"] == 1]

    if d.empty:
        st.warning("No properties match. Relax a filter (try turning off 'Only Good Investment').")
        return

    asc = sort_by in ("Value_Ratio", "Price_in_Lakhs")
    d = d.sort_values(sort_by, ascending=asc)
    c = st.columns(4)
    with c[0]: ui.kpi("Matches", f"{len(d):,}", "listings found", "#14B8A6")
    with c[1]: ui.kpi("Avg price", fmt_money(d["Price_in_Lakhs"].mean()), "today", "#16325C")
    with c[2]: ui.kpi("Avg 5-yr price", fmt_money(d["Future_Price_5Y_Lakhs"].mean()), "projected", "#F5B83D")
    with c[3]: ui.kpi("Avg growth", f"{d['Annual_Appreciation'].mean() * 100:.1f}% / yr", "modelled", "#F2674B")
    st.write("")

    cols = ["ID", "State", "City", "Locality", "Property_Type", "BHK", "Size_in_SqFt", "Price_in_Lakhs", "Future_Price_5Y_Lakhs",
            "Annual_Appreciation", "Projected_Gain_Lakhs", "Value_Ratio", "Infra_Score", "Availability_Status", "Good_Investment"]
    show = d[cols].head(300).copy()
    show["Annual_Appreciation"] = (show["Annual_Appreciation"] * 100).round(2)
    show["Good_Investment"] = show["Good_Investment"].map({1: "✅ Good", 0: "—"})
    ui.section("Top matches", f"Showing the first {len(show)} of {len(d):,}. Click a column header to re-sort.")
    ui.table(show, hide_index=True, column_config={
        "Price_in_Lakhs": st.column_config.NumberColumn("Price (L)", format="%.1f"),
        "Future_Price_5Y_Lakhs": st.column_config.NumberColumn("5-yr price (L)", format="%.1f"),
        "Annual_Appreciation": st.column_config.ProgressColumn("Growth % / yr", min_value=2, max_value=14, format="%.2f"),
        "Projected_Gain_Lakhs": st.column_config.NumberColumn("Gain (L)", format="%.1f"),
        "Infra_Score": st.column_config.ProgressColumn("Infra score", min_value=0, max_value=100, format="%.0f"),
        "Value_Ratio": st.column_config.NumberColumn("vs city median", format="%.2fx"),
    }, height=420)
    st.download_button("⬇️ Download shortlist (CSV)", d[cols].head(5000).to_csv(index=False).encode(), "shortlist.csv", "text/csv")

    l, r = st.columns(2)
    with l:
        ui.plot(V.ranked_bar(d, "City", "Projected_Gain_Lakhs", "mean", "Cities with the highest average 5-year gain (your shortlist)", "₹ lakhs", 12), "fd_city")
    with r:
        ui.plot(V.future_vs_current(d), "fd_fut")
    ui.insight("Rank by <b>Projected gain</b> to maximise rupees earned, or by <b>Value ratio</b> (lowest first) to find the biggest discounts to the city median.", "How to use")
