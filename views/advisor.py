"""Investment Advisor: property form -> classification + 5-year price + explanations."""
import streamlit as st

from src import ui, visuals as V
from src.predict import predict_property, find_good_price
from src.utils import fmt_money


def _form(lookup):
    """Render the input form; return (submitted, inputs)."""
    opts = lookup["options"]
    # State/City live OUTSIDE the form so the city list refreshes instantly when the state changes
    ui.section("1 · Location")
    c = st.columns(2)
    states = sorted(lookup["state_cities"])
    state = c[0].selectbox("State", states, index=states.index("Maharashtra"))
    city = c[1].selectbox("City", lookup["state_cities"][state])
    with st.form("advisor_form"):
        ptype = st.selectbox("Property type", opts["Property_Type"])
        ui.section("2 · Property")
        c = st.columns(4)
        bhk = c[0].selectbox("BHK", [1, 2, 3, 4, 5], index=2)
        size = c[1].number_input("Size (sq ft)", 500, 5000, 1500, step=50)
        price = c[2].number_input("Asking price (₹ lakhs)", 10.0, 500.0, 150.0, step=5.0)
        age = c[3].number_input("Age (years)", 2, 35, 8)
        c = st.columns(4)
        total_floors = c[0].number_input("Total floors", 1, 30, 12)
        floor = c[1].number_input("Floor no.", 0, 30, 4)
        furn = c[2].selectbox("Furnishing", opts["Furnished_Status"])
        face = c[3].selectbox("Facing", opts["Facing"])
        ui.section("3 · Neighbourhood & features")
        c = st.columns(4)
        schools = c[0].slider("Nearby schools", 1, 10, 6)
        hospitals = c[1].slider("Nearby hospitals", 1, 10, 6)
        transit = c[2].selectbox("Public transport", ["High", "Medium", "Low"])
        avail = c[3].selectbox("Availability", opts["Availability_Status"])
        c = st.columns(3)
        parking = c[0].radio("Parking", ["Yes", "No"], horizontal=True)
        security = c[1].radio("Security", ["Yes", "No"], horizontal=True)
        owner = c[2].selectbox("Owner type", opts["Owner_Type"])
        amen = st.multiselect("Amenities", lookup["amenities"], default=["Gym", "Pool"])
        go_btn = st.form_submit_button("🔮 Analyse this property")
    inputs = dict(State=state, City=city, Property_Type=ptype, BHK=bhk, Size_in_SqFt=size, Price_in_Lakhs=float(price),
                  Age_of_Property=age, Floor_No=floor, Total_Floors=total_floors, Nearby_Schools=schools,
                  Nearby_Hospitals=hospitals, Public_Transport_Accessibility=transit, Parking_Space=parking,
                  Security=security, Amenities=", ".join(amen) if amen else "Gym", Furnished_Status=furn,
                  Facing=face, Owner_Type=owner, Availability_Status=avail)
    return go_btn, inputs


def render(clf, reg, lookup, metrics):
    ui.hero("Investment Advisor", "Describe a property and get an instant verdict, a 5-year price forecast and the reasons behind it.",
            ["Classification", "Regression", "Confidence scores"])
    submitted, inputs = _form(lookup)
    if submitted:
        st.session_state["advisor_result"] = (inputs, predict_property(clf, reg, lookup, inputs),
                                              find_good_price(clf, lookup, inputs))
    if "advisor_result" not in st.session_state:
        ui.insight("Fill in the form and press <b>Analyse this property</b>.", "Get started")
        return

    inputs, res, target_price = st.session_state["advisor_result"]
    best = next(r for r in metrics["regression"]["results"] if r["model"] == metrics["regression"]["best_model"])
    rmse = best["rmse"]

    st.write("")
    l, r = st.columns([1.4, 1])
    with l:
        kind, head = ("good", "✅ Good Investment") if res["is_good"] else ("bad", "⚠️ Not a Good Investment")
        st.markdown(f"<div class='verdict {kind}'><h2>{head}</h2><p>Model confidence <b>{res['confidence'] * 100:.0f}%</b> · "
                    f"{inputs['BHK']} BHK {inputs['Property_Type']} in {inputs['City']}, {inputs['State']}</p></div>", unsafe_allow_html=True)
        st.write("")
        c = st.columns(3)
        with c[0]: ui.kpi("Price in 5 years", fmt_money(res["future_price"]), f"± {fmt_money(rmse)} typical error", "#14B8A6")
        with c[1]: ui.kpi("Projected gain", fmt_money(res["gain"]), f"{res['cagr'] * 100:.1f}% per year", "#F5B83D")
        with c[2]: ui.kpi("Price vs city median", f"{res['value_ratio']:.2f}x", f"₹{res['ppsf']:,.0f} vs ₹{res['city_median_ppsf']:,.0f} /sq ft", "#F2674B")
    with r:
        ui.plot(V.gauge(res["prob_good"]), "ad_gauge")

    l, r = st.columns([1.3, 1])
    with l:
        ui.plot(V.projection_chart(inputs["Price_in_Lakhs"], res["cagr"], rmse=rmse), "ad_proj")
    with r:
        ui.section("Why this verdict?")
        tips = []
        if res["value_ratio"] <= 1:
            tips.append(("good", f"Priced <b>{(1 - res['value_ratio']) * 100:.0f}% below</b> the {inputs['City']} median ₹/sq ft - the strongest positive factor."))
        elif res["value_ratio"] > 1.5:
            tips.append(("warn", f"Priced <b>{res['value_ratio']:.1f}x</b> the city median - over-priced; this alone rules out a 'Good' label."))
        else:
            tips.append(("", f"Priced {res['value_ratio']:.2f}x the city median - a modest premium."))
        if res["infra_score"] >= 70:
            tips.append(("good", f"Strong infrastructure score (<b>{res['infra_score']:.0f}/100</b>)."))
        elif res["infra_score"] < 50:
            tips.append(("warn", f"Weak infrastructure score (<b>{res['infra_score']:.0f}/100</b>) limits growth."))
        if inputs["Availability_Status"] == "Under_Construction":
            tips.append(("good", "Under construction: extra upside on completion."))
        if inputs["Parking_Space"] == "No" or inputs["Security"] == "No":
            tips.append(("warn", "Missing parking or security reduces projected appreciation."))
        for k, t in tips:
            ui.insight(t, "Factor", k)
        if not res["is_good"] and target_price:
            ui.insight(f"Negotiate to about <b>{fmt_money(target_price)}</b> (from {fmt_money(inputs['Price_in_Lakhs'])}) and the model flips to <b>Good Investment</b>.",
                       "Negotiation target", "good")

    ui.section("What drives the model overall?", "Global feature importance of the two trained models")
    a, b = st.columns(2)
    with a: ui.plot(V.importance_chart(metrics["classification"]["importance"], "Classifier: what decides 'Good Investment'"), "ad_imp_c")
    with b: ui.plot(V.importance_chart(metrics["regression"]["importance"], "Regressor: what decides the 5-year price"), "ad_imp_r")
    st.caption("Estimates come from models trained on rule-derived targets; treat them as decision support, not financial advice.")
