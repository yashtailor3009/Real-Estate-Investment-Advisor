"""
visuals.py
==========
All Plotly figure builders. Conventions used everywhere:

* every function takes already-filtered data and returns a go.Figure
* titles state the TAKEAWAY (not just the metric) and axes carry units
* key facts are annotated directly on the chart (median lines, callouts)
* heavy data is aggregated/sampled in pandas first so the browser stays fast
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from . import config as C

P = C.PALETTE
FONT = "Inter, Segoe UI, Roboto, sans-serif"


# ------------------------------------------------------------- base style
def style(fig: go.Figure, title: str, subtitle: str | None = None, height: int = 420,
          legend: bool = False) -> go.Figure:
    """Apply shared chart styling with readable dark labels."""
    text = f"<b>{title}</b>" + (
        f"<br><span style='font-size:12px;color:#374151'>{subtitle}</span>"
        if subtitle else ""
    )

    fig.update_layout(
        title=dict(
            text=text,
            x=0.01,
            xanchor="left",
            font=dict(size=17, color="#111111"),
        ),
        height=height,
        margin=dict(l=10, r=20, t=80 if subtitle else 60, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color="#111827", size=13),
        showlegend=legend,
        colorway=C.COLOR_SEQ,
        legend=dict(font=dict(color="#111111", size=11)),
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
            font_color="#111111",
        ),
    )

    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        linecolor="#9CA3AF",
        tickfont=dict(color="#374151", size=11),
        title_font=dict(color="#111111", size=12),
    )

    fig.update_yaxes(
        gridcolor="#E5E7EB",
        zeroline=False,
        linecolor="#9CA3AF",
        tickfont=dict(color="#374151", size=11),
        title_font=dict(color="#111111", size=12),
    )

    fig.update_annotations(font=dict(color="#111111"))
    return fig



def callout(fig: go.Figure, text: str, x=0.99, y=0.97, color=None) -> None:
    """Add a small boxed note in paper coordinates (top-right by default)."""
    fig.add_annotation(
        x=x, y=y, xref="paper", yref="paper", text=text, showarrow=False, align="left",
        xanchor="right", yanchor="top", bgcolor="#FFF8E6", bordercolor=color or P["gold"],
        borderwidth=1, borderpad=6, font=dict(size=11, color=P["navy"]))


def _hist_bars(series: pd.Series, bins: int):
    """Pre-bin a series -> (centres, counts, width) so the browser gets ~40 bars."""
    counts, edges = np.histogram(series.dropna(), bins=bins)
    return (edges[:-1] + edges[1:]) / 2, counts, edges[1] - edges[0]


# ------------------------------------------------------- price & size
def price_distribution(df: pd.DataFrame, col="Price_in_Lakhs", label="Price (₹ lakhs)",
                       title="How are property prices distributed?") -> go.Figure:
    """Histogram with a median marker and an IQR band."""
    x, y, w = _hist_bars(df[col], 40)
    med, q1, q3 = df[col].median(), df[col].quantile(.25), df[col].quantile(.75)
    fig = go.Figure(go.Bar(x=x, y=y, width=w * 0.92, marker_color=P["teal"],
                           hovertemplate=f"{label}: %{{x:,.0f}}<br>Listings: %{{y:,}}<extra></extra>"))
    fig.add_vrect(x0=q1, x1=q3, fillcolor=P["gold"], opacity=0.15, line_width=0)
    fig.add_vline(x=med, line_dash="dash", line_color=P["coral"], line_width=2)
    fig.add_annotation(x=med, y=max(y), text=f"Median {med:,.0f}", showarrow=True, ax=45, ay=-5,
                       font=dict(color=P["coral"], size=12), arrowcolor=P["coral"])
    style(fig, title, f"Shaded band = middle 50% of listings ({q1:,.0f} - {q3:,.0f})")
    fig.update_xaxes(title=label); fig.update_yaxes(title="Number of listings")
    return fig


def ppsf_by_type(df: pd.DataFrame) -> go.Figure:
    """Box plot of price/sqft by property type with median labels."""
    cap = df["Price_per_SqFt_INR"].quantile(0.99)
    fig = go.Figure()
    for i, (name, g) in enumerate(df.groupby("Property_Type", observed=True)):
        fig.add_trace(go.Box(y=g["Price_per_SqFt_INR"].clip(upper=cap), name=name, boxmean=True,
                             marker_color=C.COLOR_SEQ[i], line_width=1.5))
        fig.add_annotation(x=name, y=g["Price_per_SqFt_INR"].median(), text=f"{g['Price_per_SqFt_INR'].median():,.0f}",
                           showarrow=False, xshift=62, font=dict(size=11, color=P["navy"]))
    style(fig, "Price per sq ft by property type", "Boxes show the middle 50%; dotted line = mean; values capped at the 99th percentile")
    fig.update_yaxes(title="Price per sq ft (₹)")
    return fig


def size_vs_metric(df: pd.DataFrame, metric: str, label: str, n: int = 4000) -> go.Figure:
    """Scatter of size vs price (or price/sqft) with the correlation annotated."""
    s = df.sample(min(n, len(df)), random_state=C.RANDOM_STATE)
    r = df["Size_in_SqFt"].corr(df[metric])
    fig = go.Figure(go.Scattergl(x=s["Size_in_SqFt"], y=s[metric], mode="markers",
                                 marker=dict(size=4, color=P["navy_soft"], opacity=0.35),
                                 hovertemplate="Size %{x:,} sq ft<br>%{y:,.0f}<extra></extra>"))
    verdict = "strong inverse link" if r < -0.4 else "strong positive link" if r > 0.4 else "no meaningful link"
    style(fig, f"Size vs {label}: {verdict}", f"Correlation r = {r:.2f} (sample of {len(s):,} listings)")
    callout(fig, f"<b>r = {r:.2f}</b>")
    fig.update_xaxes(title="Size (sq ft)"); fig.update_yaxes(title=label)
    return fig


# ------------------------------------------------------------- location
def ranked_bar(df: pd.DataFrame, group: str, metric: str, agg: str, title: str, label: str,
               top: int | None = None, subtitle: str | None = None, fmt: str = ",.0f") -> go.Figure:
    """Horizontal ranked bar of an aggregated metric with an 'average' guide line."""
    g = df.groupby(group, observed=True)[metric].agg(agg).sort_values(ascending=False)
    overall = df[metric].agg(agg)
    if top:
        g = g.head(top)
    g = g.sort_values()
    colors = [P["teal"] if v >= overall else P["navy_soft"] for v in g.values]
    fig = go.Figure(go.Bar(x=g.values, y=g.index, orientation="h", marker_color=colors,
                           text=[format(v, fmt) for v in g.values], textposition="outside",
                           hovertemplate="%{y}: %{x:" + fmt + "}<extra></extra>"))
    fig.add_vline(x=overall, line_dash="dash", line_color=P["coral"])
    fig.add_annotation(x=overall, y=1.02, yref="paper", text=f"Overall {format(overall, fmt)}",
                       showarrow=False, font=dict(color=P["coral"], size=11))
    style(fig, title, subtitle, height=max(380, 26 * len(g) + 120))
    fig.update_xaxes(title=label, range=[0, g.max() * 1.18]); fig.update_yaxes(title=None)
    return fig


def city_bhk_heatmap(df: pd.DataFrame, top_cities: int = 12) -> go.Figure:
    """City x BHK share heatmap (percentage of each city's listings)."""
    cities = df["City"].value_counts().head(top_cities).index
    ct = pd.crosstab(df.loc[df["City"].isin(cities), "City"], df["BHK"], normalize="index") * 100
    ct = ct.loc[[c for c in cities if c in ct.index]]
    fig = go.Figure(go.Heatmap(z=ct.values, x=[f"{b} BHK" for b in ct.columns], y=ct.index,
                               colorscale=[[0, "#E7F7F4"], [1, P["teal_dark"]]], zmin=0,
                               text=np.round(ct.values, 1), texttemplate="%{text}%",
                               hovertemplate="%{y} - %{x}: %{z:.1f}%<extra></extra>",
                               colorbar=dict(title="% of city")))
    style(fig, "BHK mix by city", "Each row sums to 100% - a flat colour means a balanced mix", height=440)
    return fig


def locality_trend(df: pd.DataFrame, top: int = 5) -> go.Figure:
    """Price/sqft by construction era for the most expensive localities."""
    loc = df.groupby("Locality", observed=True)["Price_per_SqFt_INR"].mean().nlargest(top).index
    d = df[df["Locality"].isin(loc)].assign(Era=lambda x: (x["Year_Built"] // 5) * 5)
    t = d.groupby(["Locality", "Era"], observed=True)["Price_per_SqFt_INR"].mean().reset_index()
    fig = go.Figure()
    for i, (name, g) in enumerate(t.groupby("Locality", observed=True)):
        fig.add_trace(go.Scatter(x=g["Era"], y=g["Price_per_SqFt_INR"], mode="lines+markers", name=str(name),
                                 line=dict(width=3, color=C.COLOR_SEQ[i % 6]), marker=dict(size=8)))
    style(fig, f"Price trend of the {top} most expensive localities",
          "Average ₹/sq ft by 5-year build era (the dataset has no listing dates, so build era is the time axis)",
          legend=True, height=440)
    fig.update_xaxes(title="Build era (year built, 5-year buckets)", dtick=5)
    fig.update_yaxes(title="Avg price per sq ft (₹)")
    return fig


def state_type_heatmap(df: pd.DataFrame, metric: str = "Price_per_SqFt_INR", label="₹/sq ft") -> go.Figure:
    """Location-wise heatmap: State x Property type."""
    pv = df.pivot_table(index="State", columns="Property_Type", values=metric, aggfunc="mean", observed=True)
    pv = pv.loc[pv.mean(axis=1).sort_values().index]
    fig = go.Figure(go.Heatmap(z=pv.values, x=pv.columns, y=pv.index, colorscale="Tealgrn",
                               text=np.round(pv.values, 0), texttemplate="%{text:,.0f}",
                               hovertemplate="%{y} - %{x}: %{z:,.0f}<extra></extra>",
                               colorbar=dict(title=label)))
    style(fig, f"Average {label} by state and property type", "Darker = higher. Look for rows that stand out.", height=620)
    return fig


# ------------------------------------------------ relationships / drivers
def corr_heatmap(df: pd.DataFrame) -> go.Figure:
    """Correlation matrix of the key numeric features."""
    cols = ["Price_in_Lakhs", "Size_in_SqFt", "Price_per_SqFt_INR", "BHK", "Age_of_Property",
            "Nearby_Schools", "Nearby_Hospitals", "Infra_Score", "Amenity_Count", "Annual_Appreciation"]
    cm = df[cols].corr().round(2)
    fig = go.Figure(go.Heatmap(z=cm.values, x=cols, y=cols, zmin=-1, zmax=1, colorscale="RdBu_r",
                               text=cm.values, texttemplate="%{text}", hovertemplate="%{y} vs %{x}: %{z}<extra></extra>"))
    style(fig, "Which numeric features move together?",
          "Red = positive, blue = negative. Most cells are ~0: listing attributes are largely independent", height=560)
    fig.update_xaxes(tickangle=-40); fig.update_yaxes(autorange="reversed")
    return fig


def metric_by_numeric(df: pd.DataFrame, col: str, metric: str, title: str, ylabel: str, xlabel: str) -> go.Figure:
    """Line/marker chart of an average metric across a small integer feature (schools, hospitals...)."""
    g = df.groupby(col, observed=True)[metric].mean()
    overall = df[metric].mean()
    fig = go.Figure(go.Scatter(x=g.index, y=g.values, mode="lines+markers", line=dict(color=P["teal"], width=3),
                               marker=dict(size=9, color=P["navy_soft"])))
    fig.add_hline(y=overall, line_dash="dash", line_color=P["coral"],
                  annotation_text=f"Overall avg {overall:,.2f}" if overall < 100 else f"Overall avg {overall:,.0f}",
                  annotation_position="top left")
    pad = (g.max() - g.min()) or overall * 0.05
    fig.update_yaxes(range=[min(g.min(), overall) - pad * 2, max(g.max(), overall) + pad * 2])
    style(fig, title, "Dashed line = overall average; a flat line means the feature does not drive this metric")
    fig.update_xaxes(title=xlabel, dtick=1); fig.update_yaxes(title=ylabel)
    return fig


def category_bars(df: pd.DataFrame, col: str, metric: str, title: str, ylabel: str, agg: str = "mean",
                  pct: bool = False, subtitle: str | None = None) -> go.Figure:
    """Vertical bars of an aggregated metric by a categorical column with value labels."""
    g = df.groupby(col, observed=True)[metric].agg(agg)
    vals = g.values * (100 if pct else 1)
    overall = df[metric].agg(agg) * (100 if pct else 1)
    fig = go.Figure(go.Bar(x=[str(i) for i in g.index], y=vals, marker_color=C.COLOR_SEQ[: len(g)] if len(g) <= 6 else P["teal"],
                           text=[f"{v:,.1f}%" if pct else f"{v:,.0f}" for v in vals], textposition="outside"))
    fig.add_hline(y=overall, line_dash="dash", line_color=P["coral"],
                  annotation_text=f"Overall {overall:,.1f}{'%' if pct else ''}", annotation_position="top right")
    style(fig, title, subtitle)
    fig.update_yaxes(title=ylabel, range=[0, max(vals.max(), overall) * 1.2]); fig.update_xaxes(title=None)
    return fig


def donut(df: pd.DataFrame, col: str, title: str, subtitle: str | None = None) -> go.Figure:
    """Share-of-listings donut with total in the centre."""
    c = df[col].value_counts()
    fig = go.Figure(go.Pie(labels=[str(i).replace("_", " ") for i in c.index], values=c.values, hole=0.62,
                           marker=dict(colors=C.COLOR_SEQ), textinfo="label+percent", sort=False))
    fig.add_annotation(text=f"<b>{len(df):,}</b><br>listings", showarrow=False, font=dict(size=15, color=P["navy"]))
    return style(fig, title, subtitle, height=400)


# -------------------------------------------------- investment analysis
def valuation_band_chart(df: pd.DataFrame) -> go.Figure:
    """Good-Investment rate by valuation band vs city median (the key lever)."""
    bins = [0, 0.5, 1.0, 1.5, np.inf]
    labels = ["Deep discount\n(<0.5x)", "Below median\n(0.5-1x)", "Above median\n(1-1.5x)", "Premium\n(>1.5x)"]
    b = pd.cut(df["Value_Ratio"], bins, labels=labels, right=False)
    g = df.groupby(b, observed=True)["Good_Investment"].mean() * 100
    fig = go.Figure(go.Bar(x=[l.replace("\n", "<br>") for l in g.index], y=g.values, text=[f"{v:.0f}%" for v in g.values],
                           textposition="outside", marker_color=[P["teal_dark"], P["teal"], P["gold"], P["coral"]][: len(g)]))
    style(fig, "Buying below the city median multiplies your odds",
          "Share of listings qualifying as a Good Investment, by price vs city median (modelled)")
    callout(fig, "Entry price vs city<br>is the #1 driver", x=0.99, y=0.95)
    fig.update_yaxes(title="% Good Investments", range=[0, 105]); fig.update_xaxes(title=None)
    return fig


def appreciation_hist(df: pd.DataFrame) -> go.Figure:
    """Distribution of modelled annual appreciation with the 'Good' threshold."""
    x, y, w = _hist_bars(df["Annual_Appreciation"] * 100, 40)
    fig = go.Figure(go.Bar(x=x, y=y, width=w * 0.92, marker_color=[P["teal"] if v >= C.GOOD_APPRECIATION_THRESHOLD * 100 else "#BBD0E3" for v in x]))
    fig.add_vline(x=C.GOOD_APPRECIATION_THRESHOLD * 100, line_dash="dash", line_color=P["coral"], line_width=2)
    fig.add_annotation(x=C.GOOD_APPRECIATION_THRESHOLD * 100, y=max(y), text="Good-investment threshold", showarrow=True, ax=70, ay=0,
                       font=dict(color=P["coral"]), arrowcolor=P["coral"])
    style(fig, "Projected annual appreciation", "Teal bars meet the 9% threshold (and the valuation rule)")
    fig.update_xaxes(title="Projected annual appreciation (%)"); fig.update_yaxes(title="Listings")
    return fig


def future_vs_current(df: pd.DataFrame, n: int = 3000) -> go.Figure:
    """Scatter of today's price vs projected 5-year price, coloured by label."""
    s = df.sample(min(n, len(df)), random_state=C.RANDOM_STATE)
    fig = go.Figure()
    for flag, name, col in ((1, "Good investment", P["teal"]), (0, "Other", "#9FB3C8")):
        d = s[s["Good_Investment"] == flag]
        fig.add_trace(go.Scattergl(x=d["Price_in_Lakhs"], y=d["Future_Price_5Y_Lakhs"], mode="markers", name=name,
                                   marker=dict(size=5, color=col, opacity=0.6)))
    mx = s["Price_in_Lakhs"].max()
    fig.add_trace(go.Scatter(x=[0, mx], y=[0, mx], mode="lines", name="No growth", line=dict(dash="dot", color=P["muted"])))
    style(fig, "Today's price vs projected 5-year price", "Points far above the dotted line gain the most", legend=True)
    fig.update_xaxes(title="Price today (₹ lakhs)"); fig.update_yaxes(title="Projected price in 5 years (₹ lakhs)")
    return fig


# ------------------------------------------------------ predictor visuals
def gauge(prob: float) -> go.Figure:
    """Confidence gauge for the Good-Investment probability."""
    color = P["teal"] if prob >= 0.5 else P["coral"]
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=prob * 100, number=dict(suffix="%", font=dict(size=42, color=P["navy"])),
        title=dict(text="Good-investment probability", font=dict(size=14, color=P["muted"])),
        gauge=dict(axis=dict(range=[0, 100]), bar=dict(color=color, thickness=0.3),
                   steps=[dict(range=[0, 40], color="#FBE3DD"), dict(range=[40, 60], color="#FFF1CF"),
                          dict(range=[60, 100], color="#D6F3EE")],
                   threshold=dict(line=dict(color=P["navy"], width=3), value=50))))
    fig.update_layout(height=270, margin=dict(l=20, r=20, t=40, b=10), paper_bgcolor="rgba(0,0,0,0)", font=dict(family=FONT))
    return fig


def projection_chart(price: float, rate: float, city_rate: float | None = None, rmse: float | None = None) -> go.Figure:
    """Year-by-year price path with an uncertainty band around year 5."""
    years = np.arange(0, C.FORECAST_YEARS + 1)
    path = price * (1 + rate) ** years
    fig = go.Figure()
    if rmse:
        band = rmse * (years / C.FORECAST_YEARS)
        fig.add_trace(go.Scatter(x=np.r_[years, years[::-1]], y=np.r_[path + band, (path - band)[::-1]], fill="toself",
                                 fillcolor="rgba(20,184,166,0.15)", line=dict(width=0), hoverinfo="skip", name="Model error band"))
    fig.add_trace(go.Scatter(x=years, y=path, mode="lines+markers+text", name="Projected price",
                             line=dict(color=P["teal"], width=4), marker=dict(size=10),
                             text=[f"{v:,.0f}" for v in path], textposition="top center"))
    fig.add_hline(y=price, line_dash="dot", line_color=P["muted"], annotation_text="Today", annotation_position="bottom right")
    style(fig, "Projected value path", "₹ lakhs by year; shaded band reflects the regression model's typical error", height=360)
    fig.update_xaxes(title="Years from now", dtick=1); fig.update_yaxes(title="Price (₹ lakhs)")
    return fig


# ---------------------------------------------------------- model visuals
def importance_chart(imp: dict, title: str, top: int = 10) -> go.Figure:
    """Horizontal bar of permutation importance (share of total)."""
    s = pd.Series(imp).nlargest(top).sort_values()
    fig = go.Figure(go.Bar(x=s.values * 100, y=[i.replace("_", " ") for i in s.index], orientation="h",
                           marker_color=P["teal"], text=[f"{v * 100:.1f}%" for v in s.values], textposition="outside"))
    style(fig, title, "Share of total predictive importance (permutation method)", height=420)
    fig.update_xaxes(title="Importance (%)", range=[0, s.max() * 100 * 1.2])
    return fig


def confusion_chart(cm: list) -> go.Figure:
    """Annotated confusion matrix."""
    cm = np.array(cm)
    labels = ["Not good", "Good"]
    fig = go.Figure(go.Heatmap(z=cm, x=[f"Pred: {l}" for l in labels], y=[f"Actual: {l}" for l in labels],
                               colorscale=[[0, "#E7F7F4"], [1, P["teal_dark"]]], showscale=False,
                               text=[[f"{v:,}<br>({v / cm.sum() * 100:.1f}%)" for v in r] for r in cm],
                               texttemplate="%{text}", textfont=dict(size=14)))
    style(fig, "Classifier confusion matrix", "Hold-out test set (20% of data)", height=380)
    fig.update_yaxes(autorange="reversed")
    return fig


def roc_chart(roc: dict, auc: float) -> go.Figure:
    """ROC curve with AUC callout."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=roc["fpr"], y=roc["tpr"], mode="lines", line=dict(color=P["teal"], width=4), fill="tozeroy",
                             fillcolor="rgba(20,184,166,0.12)", name="Model"))
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", line=dict(dash="dot", color=P["muted"]), name="Random guess"))
    style(fig, "ROC curve", "Closer to the top-left corner = better separation", legend=True, height=380)
    callout(fig, f"<b>AUC = {auc:.3f}</b>", x=0.97, y=0.2)
    fig.update_xaxes(title="False positive rate"); fig.update_yaxes(title="True positive rate")
    return fig


def actual_vs_pred(scatter: dict, rmse: float, r2: float) -> go.Figure:
    """Regression diagnostics: actual vs predicted 5-year price."""
    fig = go.Figure(go.Scattergl(x=scatter["actual"], y=scatter["pred"], mode="markers",
                                 marker=dict(size=5, color=P["navy_soft"], opacity=0.45)))
    mx = max(scatter["actual"])
    fig.add_trace(go.Scatter(x=[0, mx], y=[0, mx], mode="lines", line=dict(color=P["coral"], dash="dash")))
    style(fig, "Regression: actual vs predicted 5-year price", "Points hugging the dashed line = accurate forecasts (1,500 test listings)")
    callout(fig, f"RMSE = {rmse:.1f} L<br>R² = {r2:.3f}", x=0.35, y=0.97)
    fig.update_xaxes(title="Actual (₹ lakhs)"); fig.update_yaxes(title="Predicted (₹ lakhs)")
    return fig


def model_comparison(results: list, metric: str, title: str, higher_better: bool = True) -> go.Figure:
    """Bar chart comparing candidate models on one metric."""
    d = pd.DataFrame(results)
    best = d[metric].idxmax() if higher_better else d[metric].idxmin()
    colors = [P["teal"] if i == best else "#BBD0E3" for i in d.index]
    fig = go.Figure(go.Bar(x=d["model"], y=d[metric], marker_color=colors, text=[f"{v:.3f}" if v < 10 else f"{v:.1f}" for v in d[metric]],
                           textposition="outside"))
    style(fig, title, "Winner highlighted in teal", height=340)
    fig.update_yaxes(range=[0, d[metric].max() * 1.2], title=metric.upper())
    return fig
