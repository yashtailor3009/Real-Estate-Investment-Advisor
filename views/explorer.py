"""Market Explorer: the 20 EDA questions from the brief, in four tabs."""
import streamlit as st

from src import ui, visuals as V
from src.utils import describe_spread


def render(df):
    ui.hero("Market Explorer", "Twenty guided questions about prices, locations, drivers and amenities - every chart ends with a takeaway.",
            ["Interactive filters in the sidebar", "Hover, zoom, download any chart"])
    if df.empty:
        st.warning("No listings match the current filters.")
        return
    t1, t2, t3, t4 = st.tabs(["💰 Price & Size", "📍 Location", "🔗 Relationships", "🏢 Investment & Amenities"])

    # ------------------------------------------------ Q1-5 price & size
    with t1:
        l, r = st.columns(2)
        with l:
            ui.plot(V.price_distribution(df), "x_price")
            ui.insight("Listings spread almost evenly between ₹10L and ₹500L - there is no single 'typical' price tier, so segment by budget before comparing.", "Q1 Price")
        with r:
            ui.plot(V.price_distribution(df, "Size_in_SqFt", "Size (sq ft)", "How are property sizes distributed?"), "x_size")
            ui.insight("Sizes run from 500 to 5,000 sq ft with similar volume in every band, so supply is not concentrated in compact homes.", "Q2 Size")
        l, r = st.columns(2)
        with l:
            ui.plot(V.ppsf_by_type(df), "x_ppsf_type")
            m = df.groupby("Property_Type", observed=True)["Price_per_SqFt_INR"].mean()
            ui.insight(describe_spread(m, "Average ₹/sq ft") + " Do not pay extra just for a 'Villa' label.", "Q3 Type")
        with r:
            ui.plot(V.size_vs_metric(df, "Price_per_SqFt_INR", "price per sq ft (₹)"), "x_size_ppsf")
            ui.insight("Bigger homes are <b>cheaper per sq ft</b> (r ≈ -0.6): total price does not scale with area, so large units are the better value per square foot.", "Q4 Size vs price")
        l, r = st.columns(2)
        with l:
            ui.plot(V.size_vs_metric(df, "Price_in_Lakhs", "total price (₹ lakhs)"), "x_size_price")
            ui.insight("Total price is unrelated to size here - an unusual market where area is not priced in.", "Q4 Size vs total price")
        with r:
            out = df["PPSF_Outlier"].mean() * 100
            ui.plot(V.ranked_bar(df, "City", "PPSF_Outlier", "mean", "Outlier rate by city (IQR rule)", "Share of listings", 10,
                                 "Top 10 cities by share of price/sq ft outliers", ".2f"), "x_out")
            ui.insight(f"<b>{out:.1f}%</b> of listings are price-per-sq-ft outliers (IQR rule), all on the high side - small units at high totals. Use <b>medians</b>, not averages.", "Q5 Outliers", "warn")

    # --------------------------------------------- Q6-10 location
    with t2:
        l, r = st.columns(2)
        with l:
            ui.plot(V.ranked_bar(df, "State", "Price_per_SqFt_INR", "mean", "Average price per sq ft by state", "₹ per sq ft",
                                 subtitle="Teal = above the overall average"), "x_state")
            m = df.groupby("State", observed=True)["Price_per_SqFt_INR"].mean()
            ui.insight(describe_spread(m, "State-level ₹/sq ft"), "Q6 State")
        with r:
            ui.plot(V.ranked_bar(df, "City", "Price_in_Lakhs", "mean", "Average property price - top 15 cities", "₹ lakhs", 15), "x_city")
            m = df.groupby("City", observed=True)["Price_in_Lakhs"].mean()
            ui.insight(describe_spread(m, "City-level average price") + " City choice matters less than entry price vs the local median.", "Q7 City")
        l, r = st.columns(2)
        with l:
            ui.plot(V.ranked_bar(df, "Locality", "Age_of_Property", "median", "Median building age - 15 oldest localities", "Years", 15, fmt=".0f"), "x_age")
            ui.insight("Older localities will need renovation budgets - factor that into net returns.", "Q8 Age")
        with r:
            ui.plot(V.city_bhk_heatmap(df), "x_bhk")
            ui.insight("Every city carries a balanced 1-5 BHK mix, so configuration is rarely a constraint when shortlisting.", "Q9 BHK")
        ui.plot(V.locality_trend(df), "x_trend")
        ui.insight("Premium localities show no steady upward line by build era - newer is not automatically pricier. Verify each locality individually.", "Q10 Locality trends")
        ui.plot(V.state_type_heatmap(df), "x_heat")
        ui.insight("Use this location heatmap to spot state / type combinations priced above or below the rest.", "Location heatmap")

    # ------------------------------------------- Q11-15 relationships
    with t3:
        ui.plot(V.corr_heatmap(df), "x_corr")
        ui.insight("Only size ↔ price per sq ft is strongly related. Schools, hospitals, age and BHK show ~0 correlation with price, "
                   "so they are livability factors, not price drivers, in this dataset.", "Q11 Correlation")
        l, r = st.columns(2)
        with l:
            ui.plot(V.metric_by_numeric(df, "Nearby_Schools", "Price_per_SqFt_INR", "Nearby schools vs price per sq ft", "Avg ₹/sq ft", "Nearby schools"), "x_sch")
            ui.insight("A flat line: more schools nearby does not command a premium.", "Q12 Schools")
        with r:
            ui.plot(V.metric_by_numeric(df, "Nearby_Hospitals", "Price_per_SqFt_INR", "Nearby hospitals vs price per sq ft", "Avg ₹/sq ft", "Nearby hospitals"), "x_hos")
            ui.insight("Hospitals show the same flat pattern - no price premium for medical access.", "Q13 Hospitals")
        l, r = st.columns(2)
        with l:
            ui.plot(V.category_bars(df, "Furnished_Status", "Price_in_Lakhs", "Average price by furnishing level", "₹ lakhs"), "x_furn")
            m = df.groupby("Furnished_Status", observed=True)["Price_in_Lakhs"].mean()
            ui.insight(describe_spread(m, "Average price") + " A furnished home is effectively a free upgrade.", "Q14 Furnishing")
        with r:
            ui.plot(V.category_bars(df, "Facing", "Price_per_SqFt_INR", "Average price per sq ft by facing", "₹ per sq ft"), "x_face")
            m = df.groupby("Facing", observed=True)["Price_per_SqFt_INR"].mean()
            ui.insight(describe_spread(m, "₹/sq ft") + " No visible 'Vastu premium'.", "Q15 Facing")

    # ------------------------------ Q16-20 investment / amenities
    with t4:
        l, r = st.columns(2)
        with l:
            ui.plot(V.donut(df, "Owner_Type", "Listings by owner type"), "x_own")
            ui.insight("Owner, Builder and Broker listings are split roughly one-third each; the channel does not change quality (Good-Investment rate is ~39% in all three).", "Q16 Owner type")
        with r:
            ui.plot(V.donut(df, "Availability_Status", "Listings by availability status"), "x_avail")
            ui.insight("Half of the stock is under construction - the segment with the highest modelled upside.", "Q17 Availability")
        l, r = st.columns(2)
        with l:
            ui.plot(V.category_bars(df, "Parking_Space", "Price_in_Lakhs", "Average price with vs without parking", "₹ lakhs"), "x_park")
            ui.insight("Parking does not change asking price, yet parking homes score a higher Good-Investment rate (modelled) - cheap upside.", "Q18 Parking")
        with r:
            ui.plot(V.category_bars(df, "Amenity_Count", "Good_Investment", "Good-Investment rate by number of amenities", "% Good Investments", pct=True), "x_amen")
            ui.insight("Price per sq ft is flat across amenity counts, but the modelled Good-Investment rate climbs steadily with every amenity.", "Q19 Amenities")
        l, r = st.columns(2)
        with l:
            ui.plot(V.category_bars(df, "Public_Transport_Accessibility", "Price_per_SqFt_INR", "Price per sq ft by public-transport access", "₹ per sq ft"), "x_tr_p")
        with r:
            ui.plot(V.category_bars(df, "Public_Transport_Accessibility", "Good_Investment", "Good-Investment rate by public-transport access", "% Good Investments", pct=True), "x_tr_g")
        ui.insight("High transit access carries no price premium but the highest modelled investment potential - a bargain signal.", "Q20 Transport")
