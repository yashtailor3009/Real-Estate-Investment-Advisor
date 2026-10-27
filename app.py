"""
app.py - EstateIQ: Real Estate Investment Advisor (Streamlit entry point)

Run with:  streamlit run app.py

Responsibilities of this file are deliberately small:
  1. page config + theme
  2. make sure data / DB / models exist (build on first run)
  3. cached data loaders
  4. sidebar navigation + global filters
  5. route to the page modules in /views
"""
import streamlit as st

from src import config as C

st.set_page_config(page_title="EstateIQ · Real Estate Investment Advisor", page_icon=str(C.ASSET_DIR / "logo_icon.png"),
                   layout="wide", initial_sidebar_state="expanded")

from src import ui, utils                                    # noqa: E402  (after set_page_config)
from src.predict import load_models                          # noqa: E402
from views import about, advisor, explorer, finder, models, overview, sql_lab  # noqa: E402

PAGES = ["🏠 Overview", "📊 Market Explorer", "🔮 Investment Advisor", "🔎 Property Finder",
         "🗄️ SQL Lab", "🤖 Model Insights", "ℹ️ About & Method"]
FILTERED = {"🏠 Overview", "📊 Market Explorer", "🔎 Property Finder"}


@st.cache_resource(show_spinner="Preparing data, database and models (first run only)...")
def bootstrap():
    """Build any missing artefact once per server process."""
    utils.ensure_artifacts()
    return True


@st.cache_data(show_spinner="Loading 250,000 listings...")
def load_data():
    return utils.read_processed()


@st.cache_resource(show_spinner=False)
def get_models():
    return load_models()


def main():
    ui.inject_css()
    bootstrap()
    df = load_data()
    clf, reg, lookup, metrics = get_models()

    ui.sidebar_brand()
    page = st.sidebar.radio("Navigate", PAGES, label_visibility="collapsed")
    st.sidebar.markdown("---")
    filtered = ui.sidebar_filters(df) if page in FILTERED else df

    if page == PAGES[0]:
        overview.render(filtered)
    elif page == PAGES[1]:
        explorer.render(filtered)
    elif page == PAGES[2]:
        advisor.render(clf, reg, lookup, metrics)
    elif page == PAGES[3]:
        finder.render(filtered)
    elif page == PAGES[4]:
        sql_lab.render()
    elif page == PAGES[5]:
        models.render(metrics)
    else:
        about.render()


if __name__ == "__main__":
    main()
