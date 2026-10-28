"""
ui.py
=====
Reusable Streamlit UI pieces: theme CSS, hero banner, KPI cards, insight
boxes, sidebar filters and wrappers compatible across Streamlit versions.
"""
from __future__ import annotations

import base64

import pandas as pd
import streamlit as st

from . import config as C

P = C.PALETTE


def _html(s: str) -> str:
    """Collapse indented HTML to one line (Markdown treats 4-space indents as code)."""
    return "".join(line.strip() for line in s.splitlines())


def _b64(path) -> str:
    """Base64-encode an image for embedding inside raw HTML."""
    return base64.b64encode(path.read_bytes()).decode("utf-8")


# ------------------------------------------------- version-safe wrappers
def plot(fig, key: str | None = None) -> None:
    """Render a Plotly figure full-width on old and new Streamlit versions."""
    try:
        st.plotly_chart(fig, width="stretch", key=key, config={"displaylogo": False})
    except TypeError:
        st.plotly_chart(fig, use_container_width=True, key=key, config={"displaylogo": False})


def table(df: pd.DataFrame, **kwargs) -> None:
    """Render a DataFrame full-width on old and new Streamlit versions."""
    try:
        st.dataframe(df, width="stretch", **kwargs)
    except TypeError:
        st.dataframe(df, use_container_width=True, **kwargs)


# ------------------------------------------------------------------- CSS
def inject_css() -> None:
    """Apply global theme and improve contrast for headings, labels and charts."""
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif;
    }}
    .stApp {{
        background: {P['bg']};
    }}
    .block-container {{
        padding-top: 1.4rem;
        padding-bottom: 3rem;
        max-width: 1280px;
    }}
    #MainMenu, footer {{
        visibility: hidden;
    }}

    /* Main content: dark readable text on the light background */
    [data-testid="stAppViewContainer"] .main,
    [data-testid="stAppViewContainer"] .main p,
    [data-testid="stAppViewContainer"] .main li,
    [data-testid="stAppViewContainer"] .main label,
    [data-testid="stAppViewContainer"] .main [data-testid="stMarkdownContainer"],
    [data-testid="stAppViewContainer"] .main [data-testid="stMarkdownContainer"] p,
    [data-testid="stAppViewContainer"] .main [data-testid="stMarkdownContainer"] li {{
        color: #111827 !important;
    }}

    [data-testid="stAppViewContainer"] .main h1,
    [data-testid="stAppViewContainer"] .main h2,
    [data-testid="stAppViewContainer"] .main h3,
    [data-testid="stAppViewContainer"] .main h4,
    [data-testid="stAppViewContainer"] .main h5 {{
        color: #111111 !important;
    }}

    /* Form labels and field descriptions */
    [data-testid="stWidgetLabel"] p,
    [data-testid="stWidgetLabel"] label,
    [data-testid="stCaptionContainer"] p,
    [data-testid="stHelp"] {{
        color: #374151 !important;
    }}

    /* Tabs */
    .stTabs [data-baseweb="tab"] {{
        color: #374151 !important;
        font-weight: 600;
    }}
    .stTabs [aria-selected="true"] {{
        color: #111111 !important;
    }}

    /* Keep sidebar text light against the dark sidebar */
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {P['navy']} 0%, #123A5E 100%);
    }}
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {{
        color: #E6EEF8 !important;
    }}
    [data-testid="stSidebar"] [role="radiogroup"] label {{
        background: rgba(255,255,255,0.06);
        border-radius: 12px;
        padding: 9px 14px;
        margin-bottom: 6px;
        transition: all .15s;
        border: 1px solid transparent;
    }}
    [data-testid="stSidebar"] [role="radiogroup"] label:hover {{
        background: rgba(20,184,166,0.25);
        border-color: {P['teal']};
    }}

    /* Hero banner */
    .hero {{
        background: linear-gradient(120deg, {P['navy']} 0%, {P['navy_soft']} 55%, {P['teal_dark']} 100%);
        border-radius: 22px;
        padding: 28px 34px;
        color: white;
        display: flex;
        align-items: center;
        gap: 26px;
        box-shadow: 0 12px 30px rgba(11,31,58,.25);
        margin-bottom: 22px;
    }}
    .hero img {{
        height: 92px;
        border-radius: 20px;
    }}
    .hero h1 {{
        margin: 0;
        font-size: 2rem;
        font-weight: 800;
        color: white !important;
        line-height: 1.15;
    }}
    .hero p {{
        margin: 6px 0 0;
        color: #CFE3F5 !important;
        font-size: 1.02rem;
    }}
    .hero .pill {{
        display: inline-block;
        background: rgba(245,184,61,.18);
        color: {P['gold']} !important;
        border: 1px solid rgba(245,184,61,.5);
        border-radius: 999px;
        padding: 3px 12px;
        font-size: .78rem;
        font-weight: 600;
        margin-right: 8px;
        margin-top: 10px;
    }}

    /* KPI cards */
    .kpi {{
        background: white;
        border-radius: 18px;
        padding: 18px 20px;
        border: 1px solid #E3E9F2;
        box-shadow: 0 4px 14px rgba(20,40,80,.06);
        position: relative;
        overflow: hidden;
        height: 100%;
    }}
    .kpi:before {{
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 6px;
        background: var(--accent);
    }}
    .kpi .label {{
        color: {P['muted']} !important;
        font-size: .78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: .05em;
    }}
    .kpi .value {{
        color: {P['navy']} !important;
        font-size: 1.85rem;
        font-weight: 800;
        margin-top: 2px;
    }}
    .kpi .sub {{
        color: {P['muted']} !important;
        font-size: .8rem;
        margin-top: 2px;
    }}

    /* Insight / information boxes */
    .insight {{
        background: #FFFBEF;
        border: 1px solid #F6E3B0;
        border-left: 6px solid {P['gold']};
        border-radius: 14px;
        padding: 12px 16px;
        margin: 4px 0 18px;
        color: {P['text']} !important;
        font-size: .93rem;
    }}
    .insight b.t {{
        color: {P['navy']} !important;
    }}
    .insight.warn {{
        background: #FFF3F0;
        border-color: #F7CFC6;
        border-left-color: {P['coral']};
    }}
    .insight.good {{
        background: #EDFAF7;
        border-color: #BFEBE4;
        border-left-color: {P['teal']};
    }}

    .verdict {{
        border-radius: 20px;
        padding: 22px 26px;
        color: white;
        box-shadow: 0 10px 26px rgba(0,0,0,.15);
    }}
    .verdict.good {{
        background: linear-gradient(120deg, {P['teal_dark']}, {P['teal']});
    }}
    .verdict.bad {{
        background: linear-gradient(120deg, #B3412B, {P['coral']});
    }}
    .verdict h2 {{
        margin: 0;
        color: white !important;
        font-size: 1.7rem;
        font-weight: 800;
    }}
    .verdict p {{
        margin: 6px 0 0;
        color: white !important;
        opacity: .95;
    }}

    .section-title {{
        font-size: 1.25rem;
        font-weight: 700;
        color: {P['navy']} !important;
        margin: 8px 0 4px;
    }}
    .chip {{
        display: inline-block;
        background: #E8F6F4;
        color: {P['teal_dark']} !important;
        border-radius: 999px;
        padding: 2px 11px;
        font-size: .78rem;
        font-weight: 600;
        margin-right: 6px;
    }}

    /* Widgets */
    .stButton > button, .stFormSubmitButton > button {{
        background: linear-gradient(120deg, {P['teal_dark']}, {P['teal']});
        color: white !important;
        border: 0;
        border-radius: 12px;
        padding: .6rem 1.4rem;
        font-weight: 700;
        box-shadow: 0 6px 16px rgba(20,184,166,.35);
    }}
    .stButton > button:hover, .stFormSubmitButton > button:hover {{
        filter: brightness(1.06);
        color: white !important;
    }}
    </style>
    """, unsafe_allow_html=True)


# ----------------------------------------------------------- components
def hero(title: str, subtitle: str, chips: list[str] | None = None) -> None:
    """Render the gradient hero banner with the brand mark."""
    chip_html = "".join(f"<span class='pill'>{c}</span>" for c in (chips or []))
    st.markdown(
        _html(f"""
        <div class='hero'>
            <img src='data:image/png;base64,{_b64(C.ASSET_DIR / "logo_icon.png")}'/>
            <div><h1>{title}</h1><p>{subtitle}</p>{chip_html}</div>
        </div>
        """),
        unsafe_allow_html=True,
    )


def kpi(label: str, value: str, sub: str = "", accent: str = P["teal"]) -> None:
    """Render a single KPI card."""
    st.markdown(
        _html(f"""
        <div class='kpi' style='--accent:{accent}'>
            <div class='label'>{label}</div>
            <div class='value'>{value}</div>
            <div class='sub'>{sub}</div>
        </div>
        """),
        unsafe_allow_html=True,
    )


def insight(text: str, title: str = "Business insight", kind: str = "") -> None:
    """Render a takeaway box: default yellow, green ('good') or red ('warn')."""
    icon = {"good": "✅", "warn": "⚠️"}.get(kind, "💡")
    st.markdown(
        f"<div class='insight {kind}'>{icon} <b class='t'>{title}:</b> {text}</div>",
        unsafe_allow_html=True,
    )


def section(title: str, caption: str | None = None) -> None:
    """Render a section heading and optional caption."""
    st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)
    if caption:
        st.caption(caption)


def sidebar_brand() -> None:
    """Render the logo at the top of the sidebar."""
    st.sidebar.markdown(
        _html(f"""
        <div style='text-align:center;margin:-6px 0 14px'>
            <img src='data:image/png;base64,{_b64(C.ASSET_DIR / "logo_light.png")}'
                 style='width:100%;max-width:250px'/>
        </div>
        """),
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------- global filters
def sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Render sidebar filters and return the filtered DataFrame."""
    st.sidebar.markdown("### 🎛️ Filters")

    states = st.sidebar.multiselect("State", sorted(df["State"].unique()), key="f_state")
    pool = df[df["State"].isin(states)] if states else df

    cities = st.sidebar.multiselect("City", sorted(pool["City"].unique()), key="f_city")
    types = st.sidebar.multiselect("Property type", sorted(df["Property_Type"].unique()), key="f_type")
    bhk = st.sidebar.multiselect("BHK", [1, 2, 3, 4, 5], key="f_bhk")
    price = st.sidebar.slider("Price (₹ lakhs)", 10, 500, (10, 500), key="f_price")

    out = df[df["Price_in_Lakhs"].between(*price)]
    if states:
        out = out[out["State"].isin(states)]
    if cities:
        out = out[out["City"].isin(cities)]
    if types:
        out = out[out["Property_Type"].isin(types)]
    if bhk:
        out = out[out["BHK"].isin(bhk)]

    st.sidebar.caption(f"**{len(out):,}** of {len(df):,} listings match")
    return out
