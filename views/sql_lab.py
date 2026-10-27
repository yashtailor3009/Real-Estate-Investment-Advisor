"""SQL Lab: a live, read-only SQL playground over the property database."""
import sqlite3
import time

import pandas as pd
import streamlit as st

from src import config as C, ui
from src.database import parse_sql_library, run_query

DEFAULT_SQL = ("SELECT City, ROUND(AVG(Price_in_Lakhs),1) AS avg_price_lakhs,\n"
               "       ROUND(100.0*AVG(Good_Investment),1) AS good_pct\n"
               "FROM properties\nGROUP BY City\nORDER BY good_pct DESC\nLIMIT 10;")


@st.cache_data(show_spinner=False)
def _library():
    return parse_sql_library()


@st.cache_data(show_spinner=False)
def _schema():
    """Column names/types straight from SQLite (trusted internal call)."""
    con = sqlite3.connect(f"file:{C.DB_PATH}?mode=ro", uri=True)
    rows = con.execute("PRAGMA table_info(properties)").fetchall()
    con.close()
    return pd.DataFrame(rows, columns=["cid", "column", "type", "notnull", "default", "pk"])[["column", "type"]]


def _load_choice():
    """on_change callback: copy the chosen library query into the editor."""
    lib = {f"{q['id']} · {q['title']}": q for q in _library()}
    choice = st.session_state.get("lib_choice")
    if choice in lib:
        st.session_state["sql_text"] = lib[choice]["sql"]
        st.session_state["sql_insight"] = lib[choice].get("insight", "")


def render():
    ui.hero("SQL Lab", "A live SQL playground on the 250,000-row dataset. Run the 33 analysis queries or write your own.",
            ["SQLite", "Read-only & safe", "Auto-charts"])
    st.session_state.setdefault("sql_text", DEFAULT_SQL)
    lib = _library()
    left, right = st.columns([2.2, 1])
    with right:
        ui.section("Query library")
        st.selectbox("Load a prepared query", [""] + [f"{q['id']} · {q['title']}" for q in lib],
                     key="lib_choice", on_change=_load_choice)
        with st.expander("📋 Table schema: properties"):
            ui.table(_schema(), hide_index=True, height=360)
        with st.expander("💡 SQL tips"):
            st.markdown("- Table name: `properties`\n- Use `ROUND()`, `AVG()`, `COUNT()`, `GROUP BY`\n"
                        "- Window functions work: `RANK() OVER (...)`\n- Only `SELECT` / `WITH` queries are allowed\n"
                        "- Results are capped at 5,000 rows")
    with left:
        ui.section("Editor")
        sql = st.text_area("SQL query", key="sql_text", height=240, label_visibility="collapsed")
        run = st.button("▶ Run query")
        if st.session_state.get("sql_insight"):
            ui.insight(st.session_state["sql_insight"], "What this shows")

    if run:
        try:
            t0 = time.time()
            df = run_query(sql)
            st.session_state["sql_result"] = (df, time.time() - t0, None)
        except Exception as exc:
            st.session_state["sql_result"] = (None, 0, str(exc))

    if "sql_result" not in st.session_state:
        return
    df, secs, err = st.session_state["sql_result"]
    if err:
        st.error(f"Query failed: {err}")
        return
    c = st.columns(3)
    with c[0]: ui.kpi("Rows returned", f"{len(df):,}", "", "#14B8A6")
    with c[1]: ui.kpi("Columns", str(df.shape[1]), "", "#16325C")
    with c[2]: ui.kpi("Run time", f"{secs:.2f}s", "", "#F5B83D")
    st.write("")
    t1, t2 = st.tabs(["📄 Results", "📈 Chart it"])
    with t1:
        ui.table(df, hide_index=True, height=380)
        st.download_button("⬇️ Download CSV", df.to_csv(index=False).encode(), "query_result.csv", "text/csv")
    with t2:
        num = df.select_dtypes("number").columns.tolist()
        if df.empty or not num:
            st.info("Run a query that returns at least one numeric column to chart it.")
        else:
            cx, cy, ct = st.columns(3)
            xcol = cx.selectbox("X axis", df.columns, index=0)
            ycol = cy.selectbox("Y axis", num, index=min(len(num) - 1, 1 if df.columns[0] in num else 0))
            kind = ct.selectbox("Chart type", ["Bar", "Line"])
            plot_df = df[[xcol, ycol]].set_index(xcol)
            (st.bar_chart if kind == "Bar" else st.line_chart)(plot_df)
