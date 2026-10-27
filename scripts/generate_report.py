"""
generate_report.py
==================
Builds the insights PDF (reports/EstateIQ_Insights_Report.pdf) from the SQL
queries + processed data, and writes reports/summary.json (numbers reused
by the PowerPoint builder).

    python scripts/generate_report.py
"""
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, PageBreak, PageTemplate,
                                CondPageBreak, Paragraph, Preformatted, Spacer, Table, TableStyle)

from src import config as C
from src.database import parse_sql_library, run_query

FIG = C.REPORT_DIR / "figs"
FIG.mkdir(parents=True, exist_ok=True)
NAVY, TEAL, TEAL_D, GOLD, CORAL, MUTED = "#0B1F3A", "#14B8A6", "#0F766E", "#F5B83D", "#F2674B", "#6B7A90"

# ---- fonts: DejaVu (ships with matplotlib) supports the rupee sign and arrows
ttf = Path(font_manager.findfont("DejaVu Sans")).parent
pdfmetrics.registerFont(TTFont("DV", str(ttf / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DV-B", str(ttf / "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont("DV-M", str(ttf / "DejaVuSansMono.ttf")))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DV-B", italic="DV", boldItalic="DV-B")

plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#C9D3E0", "axes.titleweight": "bold", "axes.titlesize": 12,
                     "axes.labelcolor": "#33445C", "xtick.color": "#33445C", "ytick.color": "#33445C"})

LIB = {q["id"]: q for q in parse_sql_library()}


def sql(qid):
    """Run a query from the SQL file by id."""
    return run_query(LIB[qid]["sql"])


# ============================================================ data + numbers
df = pd.read_csv(C.PROCESSED_CSV)
metrics = json.loads(C.METRICS_PATH.read_text())
S = {}  # summary numbers for the deck


def save(fig, name):
    """Save a figure at print resolution and return its path."""
    p = FIG / f"{name}.png"
    fig.savefig(p, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return p


def hist_fig(series, color, xlabel, title, name, fmt="{:,.0f}"):
    """Histogram with median line + IQR band annotated."""
    fig, ax = plt.subplots(figsize=(6.6, 3.1))
    ax.hist(series, bins=40, color=color, edgecolor="white", linewidth=.5)
    q1, med, q3 = series.quantile([.25, .5, .75])
    ax.axvspan(q1, q3, color=GOLD, alpha=.18, label="Middle 50%")
    ax.axvline(med, color=CORAL, ls="--", lw=2)
    ax.annotate(f"Median {fmt.format(med)}", (med, ax.get_ylim()[1] * .93), xytext=(12, 0), textcoords="offset points",
                color=CORAL, fontweight="bold", fontsize=9)
    ax.set_xlabel(xlabel); ax.set_ylabel("Listings"); ax.set_title(title, loc="left")
    ax.legend(frameon=False, loc="lower right", fontsize=8)
    return save(fig, name)


def figs():
    """Create every chart used in the PDF; return dict of paths."""
    F = {}
    F["price"] = hist_fig(df["Price_in_Lakhs"], TEAL, "Price (₹ lakhs)", "Prices spread evenly from ₹10L to ₹500L", "price")
    F["size"] = hist_fig(df["Size_in_SqFt"], "#16325C", "Size (sq ft)", "Sizes spread evenly from 500 to 5,000 sq ft", "size")

    # price/sqft by type (zero-based bars so a lack of difference is visible)
    t = sql("Q06")
    fig, ax = plt.subplots(figsize=(6.6, 3.0))
    ax.bar(t["Property_Type"], t["avg_ppsf_inr"], color=[TEAL, "#16325C", GOLD], width=.55)
    for i, v in enumerate(t["avg_ppsf_inr"]):
        ax.text(i, v + 250, f"₹{v:,.0f}", ha="center", fontweight="bold", fontsize=10)
    ax.set_ylim(0, t["avg_ppsf_inr"].max() * 1.25); ax.set_ylabel("Avg ₹ per sq ft")
    ax.set_title("Property type barely moves price per sq ft", loc="left")
    spread = (t["avg_ppsf_inr"].max() - t["avg_ppsf_inr"].min()) / t["avg_ppsf_inr"].mean() * 100
    ax.annotate(f"Gap between highest and lowest: {spread:.1f}%", (.98, .92), xycoords="axes fraction", ha="right",
                bbox=dict(boxstyle="round", fc="#FFF8E6", ec=GOLD), fontsize=9)
    F["type"] = save(fig, "type"); S["type_spread_pct"] = round(spread, 2)

    # size vs ppsf: binned means over a 2D density
    fig, ax = plt.subplots(figsize=(6.6, 3.2))
    smp = df.sample(30000, random_state=1)
    ax.hexbin(smp["Size_in_SqFt"], smp["Price_per_SqFt_INR"].clip(upper=df["Price_per_SqFt_INR"].quantile(.99)),
              gridsize=40, cmap="GnBu", mincnt=1)
    b = df.groupby(pd.cut(df["Size_in_SqFt"], 12), observed=True).agg(x=("Size_in_SqFt", "mean"), y=("Price_per_SqFt_INR", "mean"))
    ax.plot(b["x"], b["y"], color=CORAL, lw=3, marker="o", label="Average")
    r = df["Size_in_SqFt"].corr(df["Price_per_SqFt_INR"]); S["corr_size_ppsf"] = round(r, 3)
    ax.annotate(f"r = {r:.2f}\nBigger homes cost\nless per sq ft", (.97, .93), xycoords="axes fraction", ha="right", va="top",
                bbox=dict(boxstyle="round", fc="#FFF8E6", ec=GOLD), fontsize=9)
    ax.set_xlabel("Size (sq ft)"); ax.set_ylabel("₹ per sq ft"); ax.set_title("Size vs price per sq ft: a strong inverse link", loc="left")
    ax.legend(frameon=False, loc="lower left"); F["size_ppsf"] = save(fig, "size_ppsf")

    # states
    s = sql("Q09").sort_values("avg_ppsf_inr")
    fig, ax = plt.subplots(figsize=(6.6, 4.4))
    avg = df["Price_per_SqFt_INR"].mean()
    ax.barh(s["State"], s["avg_ppsf_inr"], color=[TEAL if v >= avg else "#16325C" for v in s["avg_ppsf_inr"]])
    ax.axvline(avg, color=CORAL, ls="--"); ax.text(avg, len(s) - .3, f" Overall ₹{avg:,.0f}", color=CORAL, fontsize=9, va="bottom")
    ax.set_xlim(0, s["avg_ppsf_inr"].max() * 1.12); ax.set_xlabel("Avg ₹ per sq ft")
    ax.set_title("State averages sit in a narrow band", loc="left"); ax.tick_params(axis="y", labelsize=8)
    F["state"] = save(fig, "state")
    S["state_hi"] = (s.iloc[-1]["State"], float(s.iloc[-1]["avg_ppsf_inr"])); S["state_lo"] = (s.iloc[0]["State"], float(s.iloc[0]["avg_ppsf_inr"]))

    # top-5 locality trend
    t = sql("Q13"); fig, ax = plt.subplots(figsize=(6.6, 3.1))
    for i, (n, g) in enumerate(t.groupby("Locality")):
        ax.plot(g["build_era"], g["avg_ppsf_inr"], marker="o", lw=2.4, label=n, color=[TEAL, "#16325C", GOLD, CORAL, "#7C5CFC"][i])
    ax.set_xlabel("Build era (5-year buckets)"); ax.set_ylabel("Avg ₹ per sq ft")
    ax.set_title("Top-5 priciest localities: no steady trend by build era", loc="left"); ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper center", bbox_to_anchor=(.5, -.2))
    F["trend"] = save(fig, "trend")

    # correlation bars
    c = sql("Q14").iloc[::-1]; fig, ax = plt.subplots(figsize=(6.6, 2.8))
    ax.barh(c["feature"], c["corr_with_ppsf"], color=[CORAL if v < 0 else TEAL for v in c["corr_with_ppsf"]])
    for i, v in enumerate(c["corr_with_ppsf"]):
        ax.text(v + (.015 if v >= 0 else -.015), i, f"{v:+.3f}", va="center", ha="left" if v >= 0 else "right", fontsize=9)
    ax.set_xlim(-.75, .35); ax.axvline(0, color="#888", lw=.8); ax.set_xlabel("Correlation with price per sq ft")
    ax.set_title("Only size relates to price per sq ft", loc="left"); F["corr"] = save(fig, "corr")

    # schools & hospitals flat lines
    fig, axs = plt.subplots(1, 2, figsize=(6.6, 2.9), sharey=True)
    for ax, q, col, lab in ((axs[0], "Q15", "Nearby_Schools", "Nearby schools"), (axs[1], "Q16", "Nearby_Hospitals", "Nearby hospitals")):
        d = sql(q); ax.plot(d[col], d["avg_ppsf_inr"], marker="o", color=TEAL, lw=2.4)
        ax.axhline(df["Price_per_SqFt_INR"].mean(), color=CORAL, ls="--", lw=1.2)
        ax.set_xlabel(lab); ax.set_ylim(11500, 14500); ax.set_xticks(range(1, 11))
    axs[0].set_ylabel("Avg ₹ per sq ft"); fig.suptitle("Schools and hospitals do not move price per sq ft", x=.01, ha="left", fontweight="bold", fontsize=12)
    F["flat"] = save(fig, "flat")

    # modelled drivers: availability, parking, transport (good-investment rate)
    fig, axs = plt.subplots(1, 3, figsize=(6.8, 2.8), sharey=True)
    for ax, q, col, ttl in ((axs[0], "Q20", "Availability_Status", "Availability"), (axs[1], "Q21", "Parking_Space", "Parking"),
                            (axs[2], "Q24", "transport_access", "Transit access")):
        d = sql(q); ax.bar([str(v).replace("_", "\n") for v in d[col]], d["good_investment_pct"], color=[TEAL, "#16325C", GOLD][:len(d)])
        for i, v in enumerate(d["good_investment_pct"]): ax.text(i, v + 1, f"{v:.0f}%", ha="center", fontsize=9, fontweight="bold")
        ax.set_title(ttl, fontsize=10, loc="left"); ax.set_ylim(0, 60)
    axs[0].set_ylabel("% Good Investment (modelled)"); F["drivers"] = save(fig, "drivers")

    # amenities
    a = sql("Q22"); fig, ax = plt.subplots(figsize=(6.6, 2.9)); ax2 = ax.twinx()
    ax.bar(a["Amenity_Count"], a["good_investment_pct"], color=TEAL, width=.55, label="Good-Investment rate (modelled)")
    ax2.plot(a["Amenity_Count"], a["avg_ppsf_inr"], color=CORAL, marker="o", lw=2.4, label="Avg ₹/sq ft")
    ax2.set_ylim(0, 16000); ax2.spines["right"].set_visible(True); ax.set_ylim(0, 60)
    for x, v in zip(a["Amenity_Count"], a["good_investment_pct"]): ax.text(x, v + 1, f"{v:.0f}%", ha="center", fontsize=9, fontweight="bold")
    ax.set_xlabel("Number of amenities"); ax.set_ylabel("% Good Investment"); ax2.set_ylabel("Avg ₹ per sq ft")
    ax.set_title("Amenities add investment quality, not asking price", loc="left")
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels(); ax.legend(h1 + h2, l1 + l2, frameon=False, fontsize=8, loc="upper left")
    F["amen"] = save(fig, "amen")

    # valuation bands
    v = sql("Q26"); fig, ax = plt.subplots(figsize=(6.6, 3.0))
    lab = [x.split(". ")[1].replace(" (", "\n(") for x in v["valuation_band"]]
    ax.bar(lab, v["good_investment_pct"], color=[TEAL_D, TEAL, GOLD, CORAL], width=.6)
    for i, x in enumerate(v["good_investment_pct"]): ax.text(i, x + 2, f"{x:.0f}%", ha="center", fontweight="bold")
    ax.set_ylim(0, 100); ax.set_ylabel("% Good Investment (modelled)"); ax.tick_params(axis="x", labelsize=8)
    ax.set_title("Buying below the city median multiplies the odds", loc="left"); F["val"] = save(fig, "val")
    S["val_bands"] = v[["valuation_band", "good_investment_pct"]].values.tolist()

    # model panel
    cm = np.array(metrics["classification"]["confusion_matrix"]); imp = pd.Series(metrics["classification"]["importance"]).nlargest(8).iloc[::-1]
    fig, axs = plt.subplots(1, 2, figsize=(6.8, 3.0), gridspec_kw={"width_ratios": [1, 1.25]})
    axs[0].imshow(cm, cmap="GnBu"); axs[0].set_xticks([0, 1], ["Pred: No", "Pred: Good"], fontsize=8); axs[0].set_yticks([0, 1], ["Actual: No", "Actual: Good"], fontsize=8)
    for i in range(2):
        for j in range(2): axs[0].text(j, i, f"{cm[i, j]:,}\n{cm[i, j] / cm.sum() * 100:.1f}%", ha="center", va="center", fontsize=9, fontweight="bold",
                                       color="white" if cm[i, j] > cm.max() / 2 else NAVY)
    axs[0].set_title("Confusion matrix (test set)", fontsize=10, loc="left")
    axs[1].barh([i.replace("_", " ") for i in imp.index], imp.values * 100, color=TEAL)
    for i, x in enumerate(imp.values): axs[1].text(x * 100 + .8, i, f"{x * 100:.1f}%", va="center", fontsize=8)
    axs[1].set_title("What drives 'Good Investment'", fontsize=10, loc="left"); axs[1].tick_params(axis="y", labelsize=8); axs[1].set_xlim(0, imp.max() * 100 * 1.2)
    fig.tight_layout(); F["models"] = save(fig, "models")
    return F


# ================================================================== PDF
base = ParagraphStyle("b", fontName="DV", fontSize=9, leading=13.2, textColor=colors.HexColor("#1B2B44"), alignment=TA_LEFT)
H1 = ParagraphStyle("h1", parent=base, fontName="DV-B", fontSize=16, leading=20, textColor=colors.HexColor(NAVY), spaceBefore=4, spaceAfter=4)
H2 = ParagraphStyle("h2", parent=base, fontName="DV-B", fontSize=11, leading=14, textColor=colors.HexColor(TEAL_D), spaceBefore=8, spaceAfter=2)
CAP = ParagraphStyle("cap", parent=base, fontSize=7.5, textColor=colors.HexColor(MUTED), leading=10)
SMALL = ParagraphStyle("s", parent=base, fontSize=8, leading=11)
INS = ParagraphStyle("ins", parent=base, fontSize=8.6, leading=12.2)


def insight(text, kind="gold"):
    """Boxed takeaway with a coloured left rule."""
    col = {"gold": GOLD, "good": TEAL, "warn": CORAL}[kind]; bg = {"gold": "#FFFBEF", "good": "#EDFAF7", "warn": "#FFF3F0"}[kind]
    t = Table([[Paragraph(text, INS)]], colWidths=[17 * cm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(bg)), ("LINEBEFORE", (0, 0), (0, -1), 3.5, colors.HexColor(col)),
                           ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                           ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    return t


def img(path, w=14.8):
    """Image scaled to a given width in cm, preserving aspect."""
    from PIL import Image as PI
    iw, ih = PI.open(path).size
    return Image(str(path), width=w * cm, height=w * cm * ih / iw)


def table(rows, widths, header=True, font=8):
    """Clean data table with zebra rows."""
    t = Table(rows, colWidths=[w * cm for w in widths], repeatRows=1 if header else 0)
    st = [("FONT", (0, 0), (-1, -1), "DV", font), ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1B2B44")),
          ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F6FB")]),
          ("LINEBELOW", (0, 0), (-1, -1), .25, colors.HexColor("#DCE4EE")), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header:
        st += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(NAVY)), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONT", (0, 0), (-1, 0), "DV-B", font)]
    t.setStyle(TableStyle(st)); return t


def on_page(canvas, doc):
    """Header band + footer on every page after the cover."""
    if doc.page == 1:
        return
    canvas.saveState()
    canvas.setFillColor(colors.HexColor(NAVY)); canvas.rect(0, A4[1] - 1.1 * cm, A4[0], 1.1 * cm, fill=1, stroke=0)
    canvas.drawImage(str(C.ASSET_DIR / "logo_icon.png"), 1.6 * cm, A4[1] - 1.0 * cm, .8 * cm, .8 * cm, mask="auto")
    canvas.setFillColor(colors.white); canvas.setFont("DV-B", 9); canvas.drawString(2.6 * cm, A4[1] - .72 * cm, "EstateIQ · Real Estate Investment Advisor")
    canvas.setFont("DV", 8); canvas.drawRightString(A4[0] - 1.6 * cm, A4[1] - .72 * cm, "Insights Report")
    canvas.setFillColor(colors.HexColor(MUTED)); canvas.setFont("DV", 8); canvas.drawCentredString(A4[0] / 2, 1 * cm, f"Page {doc.page}")
    canvas.restoreState()


def build(F):
    """Assemble the story and write the PDF."""
    out = C.REPORT_DIR / "EstateIQ_Insights_Report.pdf"
    doc = BaseDocTemplate(str(out), pagesize=A4, leftMargin=1.9 * cm, rightMargin=1.9 * cm, topMargin=1.9 * cm, bottomMargin=1.6 * cm,
                          title="EstateIQ - Real Estate Investment Insights", author="EstateIQ")
    doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height - .2 * cm, id="f")], onPage=on_page)])
    sp = lambda h=6: Spacer(1, h)
    good = df["Good_Investment"].mean() * 100
    cl = metrics["classification"]; rg = metrics["regression"]
    bc = next(r for r in cl["results"] if r["model"] == cl["best_model"]); br = next(r for r in rg["results"] if r["model"] == rg["best_model"])
    q2 = sql("Q02"); q3 = sql("Q03"); val = sql("Q26"); av = sql("Q20"); amen = sql("Q22"); tr = sql("Q24")
    S.update(dict(rows=len(df), avg_price=float(df.Price_in_Lakhs.mean()), median_ppsf=float(df.Price_per_SqFt_INR.median()), good_pct=float(good),
                  avg_gain=float(df.Projected_Gain_Lakhs.mean()), avg_rate=float(df.Annual_Appreciation.mean() * 100),
                  floor_bad_pct=float(q2.pct_of_rows[0]), ppsf_out_pct=float(q3.pct[0]), acc=bc["accuracy"], auc=bc["roc_auc"], f1=bc["f1"],
                  rmse=br["rmse"], r2=br["r2"], base_rmse=rg["baseline_rmse"], clf_best=cl["best_model"], reg_best=rg["best_model"],
                  avail=av[["Availability_Status", "good_investment_pct"]].values.tolist(), amen=amen[["Amenity_Count", "good_investment_pct"]].values.tolist(),
                  transit=tr[["transport_access", "good_investment_pct"]].values.tolist(),
                  importance=dict(list(cl["importance"].items())[:6]), clf_results=cl["results"], reg_results=rg["results"]))
    st = []
    # ---------------- cover
    st += [Spacer(1, 2.2 * cm), Image(str(C.ASSET_DIR / "logo.png"), width=11 * cm, height=11 * cm * 748 / 1883), Spacer(1, 1.4 * cm),
           Paragraph("Real Estate Investment<br/>Insights Report", ParagraphStyle("t", parent=base, fontName="DV-B", fontSize=30, leading=36, textColor=colors.HexColor(NAVY))),
           sp(10), Paragraph("Predicting property profitability and future value across 250,000 Indian listings, with SQL analytics, "
                             "machine learning and an interactive Streamlit advisor.", ParagraphStyle("st", parent=base, fontSize=12, leading=17, textColor=colors.HexColor(MUTED))),
           Spacer(1, 1.2 * cm)]
    kp = [[Paragraph(f"<font size=20 color='{TEAL_D}'><b>{n}</b></font><br/><font size=8 color='{MUTED}'>{l}</font>", base)
           for n, l in ((f"{len(df):,}", "listings analysed"), ("33", "SQL queries"), (f"{bc['accuracy'] * 100:.0f}%", "classifier accuracy"), (f"{good:.0f}%", "flagged Good Investment"))]]
    t = Table(kp, colWidths=[4.25 * cm] * 4); t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), .5, colors.HexColor("#D5DCE6")), ("INNERGRID", (0, 0), (-1, -1), .5, colors.HexColor("#D5DCE6")),
                                                                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F4F7FB")), ("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 10)]))
    st += [t, Spacer(1, 6 * cm), Paragraph(f"Prepared {date.today():%d %B %Y} · Python · SQLite · scikit-learn · Streamlit", CAP), PageBreak()]

    # ---------------- executive summary
    st += [Paragraph("1. Executive summary", H1),
           Paragraph("This report answers two investor questions: <b>Is this property a good investment?</b> and <b>What will it be worth in five years?</b> "
                     "It combines 33 SQL queries on the full dataset with two machine-learning models.", base), sp(8),
           Paragraph("Five findings that matter", H2),
           Paragraph(f"<b>1. Entry price versus the city median is the biggest lever.</b> Properties priced below their city's median ₹/sq ft qualify as Good Investments "
                     f"far more often ({val.good_investment_pct[0]:.0f}% for deep discounts, {val.good_investment_pct[1]:.0f}% below median) than premium-priced ones ({val.good_investment_pct[3]:.0f}%).", base), sp(3),
           Paragraph(f"<b>2. Descriptive price data is remarkably flat.</b> State, city, property type, furnishing, facing, schools and hospitals all move average price by "
                     f"under 5% (state 2.5%, city 4.8%, the rest under 1%). Location alone will not tell an investor where to buy.", base), sp(3),
           Paragraph(f"<b>3. Size is priced per rupee, not per square foot.</b> Total price is unrelated to size (r = -0.00) so bigger homes are far cheaper per sq ft (r = {S['corr_size_ppsf']:.2f}).", base), sp(3),
           Paragraph(f"<b>4. Under-construction, well-connected, amenity-rich homes score highest.</b> Under-construction listings qualify {av.good_investment_pct[1]:.0f}% of the time versus "
                     f"{av.good_investment_pct[0]:.0f}% for ready-to-move; five amenities lift the rate from {amen.good_investment_pct[0]:.0f}% to {amen.good_investment_pct[4]:.0f}%.", base), sp(3),
           Paragraph(f"<b>5. The models learn the investment rules well.</b> The classifier reaches {bc['accuracy'] * 100:.1f}% accuracy (ROC-AUC {bc['roc_auc']:.3f}); the 5-year price "
                     f"regressor has RMSE {br['rmse']:.1f} lakhs (R² {br['r2']:.3f}), beating a constant-growth baseline of {rg['baseline_rmse']:.1f}.", base), sp(8),
           insight("<b>Read this first.</b> The raw file contains no price history and no investment label. <i>Annual appreciation</i>, <i>5-year price</i> and <i>Good Investment</i> are "
                   "<b>modelled</b> from transparent domain rules (Section 2). Findings tagged <b>(modelled)</b> reflect those rules; everything else is observed in the data.", "warn"), sp(8),
           Paragraph("Recommendations", H2),
           Paragraph("• Screen on <b>price vs city median</b> first, then infrastructure score, transit access and amenities.<br/>"
                     "• Prefer <b>larger units</b> for value per sq ft and <b>under-construction</b> stock for modelled upside.<br/>"
                     "• Use <b>medians</b>, not averages, when quoting prices: price/sq ft has a long right tail.<br/>"
                     "• Fix data capture: about 46% of rows list a floor above the building's height.<br/>"
                     "• Replace the rule engine with real transaction history to turn modelled upside into a true forecast.", base), PageBreak()]

    # ---------------- data & method
    st += [Paragraph("2. Data and methodology", H1),
           Paragraph("The dataset covers 250,000 listings across 20 states, 42 cities and 500 localities. The pipeline (<font name='DV-M'>scripts/run_pipeline.py</font>) cleans the data, "
                     "engineers features, loads SQLite and trains the models.", base), sp(6), Paragraph("Data-quality results (SQL Q01-Q03)", H2),
           table([["Check", "Result"], ["Rows / unique IDs", "250,000 / 250,000"], ["Missing values (price, size, city)", "0"], ["Duplicate rows", "0"],
                  ["Floor_No above Total_Floors", f"{int(q2.inconsistent_rows[0]):,} rows ({q2.pct_of_rows[0]}%) - flagged, floor ratio clipped"],
                  ["Price/sq ft outliers (IQR rule)", f"{int(q3.outliers[0]):,} rows ({q3.pct[0]}%) - flagged, kept"], ["Size outliers", "0"]], [6.5, 10.5]),
           sp(8), Paragraph("Engineered features", H2),
           Paragraph("Price per sq ft in rupees, Amenity_Count, Transport_Score, School_Density_Score, Infra_Score (0-100), Floor_Ratio, Value_Ratio (price/sq ft ÷ city median), "
                     "parking/security flags, age and price bands. Numeric features are standardised and categoricals one-hot encoded inside the model pipeline.", base), sp(8),
           Paragraph("How the investment targets are defined", H2),
           table([["Component", "Effect on annual appreciation"], ["Base rate", "4.5%"], ["Infrastructure (schools, hospitals, transit)", "up to +3.0%"],
                  ["Amenities / security / parking", "up to +1.2% / +0.8% / +0.6%"], ["Under construction / newer building", "+1.0% / up to +1.0%"],
                  ["Price vs city median (cheaper is better)", "-2.0% to +2.0%"], ["Simulated market noise", "N(0, 0.8%)"]], [9, 8]),
           sp(5), Paragraph(f"<b>5-year price</b> = price × (1 + appreciation)<super>5</super>. <b>Good Investment</b> = appreciation ≥ {C.GOOD_APPRECIATION_THRESHOLD * 100:.0f}% <i>and</i> "
                            f"price/sq ft ≤ {C.MAX_VALUE_RATIO}× the city median. {good:.1f}% of listings qualify.", base), PageBreak()]

    # ---------------- EDA sections
    def block(path, caption, text, kind="gold"):
        return KeepTogether([img(path), Paragraph(caption, CAP), sp(2), insight(text, kind), sp(9)])

    st += [Paragraph("3. Price and size analysis", H1), Paragraph("SQL queries Q04-Q08 · EDA questions 1-5", CAP), sp(4),
           block(F["price"], "Q1 · Distribution of property prices", f"Prices run evenly from ₹10L to ₹500L (median ₹{df.Price_in_Lakhs.median():.0f}L, mean ₹{df.Price_in_Lakhs.mean():.0f}L). There is no single typical tier, so segment by budget before comparing properties."),
           block(F["type"], "Q3 · Price per sq ft by property type (SQL Q06)", f"Villas, apartments and independent houses price within {S['type_spread_pct']:.1f}% of each other per sq ft. Do not pay a premium for the label alone."),
           block(F["size_ppsf"], "Q4 · Size versus price per sq ft", f"Correlation r = {S['corr_size_ppsf']:.2f}. Total price is unrelated to size (r = -0.00), so larger homes are materially cheaper per sq ft: the best value per square foot sits in big units."),
           CondPageBreak(11 * cm),
           block(F["size"], "Q2 · Distribution of property sizes", "Every 500 sq ft band holds a similar share of listings, so supply is not skewed toward compact homes."),
           insight(f"<b>Q5 · Outliers.</b> {q3.pct[0]}% of listings ({int(q3.outliers[0]):,}) are price-per-sq-ft outliers, all on the high side (small footprint, high total price). Size has no outliers. "
                   "Use medians for pricing decisions.", "warn"), CondPageBreak(11 * cm)]

    st += [Paragraph("4. Location analysis", H1), Paragraph("SQL queries Q09-Q13 · EDA questions 6-10", CAP), sp(4),
           block(F["state"], "Q6 · Average price per sq ft by state (SQL Q09)", f"The highest state ({S['state_hi'][0]}, ₹{S['state_hi'][1]:,.0f}) and the lowest ({S['state_lo'][0]}, ₹{S['state_lo'][1]:,.0f}) are only "
                  f"{(S['state_hi'][1] - S['state_lo'][1]) / df.Price_per_SqFt_INR.mean() * 100:.1f}% apart. Location alone does not explain price in this data."),
           block(F["trend"], "Q10 · Price trend of the five most expensive localities (SQL Q13)", "Premium localities show no steady rise by build era; newer is not automatically pricier. Evaluate each locality individually.")]
    c10 = sql("Q10").head(5)
    st += [KeepTogether([Paragraph("Q7 · Top five cities by average price (SQL Q10)", H2),
           table([["City", "State", "Listings", "Avg price (L)", "Avg Rs/sq ft"]] + [[r.City, r.State, f"{r.properties:,}", f"{r.avg_price_lakhs}", f"{r.avg_ppsf_inr:,.0f}"] for r in c10.itertuples()], [3.6, 3.6, 3, 3.4, 3.4])]),
           sp(4), insight("City averages differ by only a few lakhs (about 3% from top to bottom of the full list); entry price against the local median matters more than the city.", "gold"), CondPageBreak(11 * cm)]

    st += [Paragraph("5. Feature relationships", H1), Paragraph("SQL queries Q14-Q18 · EDA questions 11-15", CAP), sp(4),
           block(F["corr"], "Q11 · Correlation with price per sq ft (SQL Q14)", "Size is the only feature meaningfully related to price per sq ft. Age, BHK, schools, hospitals and infrastructure score all sit at ~0."),
           block(F["flat"], "Q12-13 · Nearby schools and hospitals versus price per sq ft (SQL Q15, Q16)", "Both lines are flat around the overall average (dashed): schools and hospitals are livability factors, not price drivers, in this dataset.")]
    f17 = sql("Q17"); f18 = sql("Q18")
    st += [KeepTogether([Paragraph("Q14-15 · Furnishing and facing (SQL Q17, Q18)", H2),
           table([["Furnishing", "Avg price (L)", "Avg Rs/sq ft"]] + [[r.Furnished_Status, f"{r.avg_price_lakhs}", f"{r.avg_ppsf_inr:,.0f}"] for r in f17.itertuples()], [6, 5.5, 5.5]), sp(4),
           table([["Facing", "Avg Rs/sq ft", "% vs overall"]] + [[r.Facing, f"{r.avg_ppsf_inr:,.0f}", f"{r.pct_vs_overall:+.2f}%"] for r in f18.itertuples()], [6, 5.5, 5.5]), sp(4)]),
           insight("Furnishing changes asking price by under 0.3% and facing direction by under 1%. A fully furnished home is effectively a free upgrade, and there is no visible Vastu premium.", "gold"), CondPageBreak(11 * cm)]

    st += [Paragraph("6. Investment, amenities and ownership", H1), Paragraph("SQL queries Q19-Q24 · EDA questions 16-20", CAP), sp(4)]
    q19 = sql("Q19")
    st += [Paragraph("Q16 · Properties by owner type (SQL Q19)", H2),
           table([["Owner type", "Listings", "Share", "Good-Investment rate"]] + [[r.Owner_Type, f"{r.properties:,}", f"{r.pct_share}%", f"{r.good_investment_pct}%"] for r in q19.itertuples()], [4.5, 4, 4, 4.5]),
           sp(3), Paragraph("Q17 · Availability status: 50% Ready-to-Move, 50% Under-Construction (SQL Q20).", base), sp(6),
           block(F["drivers"], "Q17-20 · Good-Investment rate by availability, parking and transit access (modelled; SQL Q20, Q21, Q24)",
                 f"Under-construction homes qualify {av.good_investment_pct[1]:.0f}% of the time (vs {av.good_investment_pct[0]:.0f}%); parking adds about 11 points; high transit access reaches {tr.good_investment_pct[0]:.0f}% (vs {tr.good_investment_pct[2]:.0f}% for low). "
                 "None of these change the asking price, so they are cheap sources of upside. (modelled)", "good"),
           block(F["amen"], "Q19 · Amenity count versus price and investment quality (SQL Q22)",
                 f"Price per sq ft is flat across amenity counts, but the modelled Good-Investment rate rises from {amen.good_investment_pct[0]:.0f}% with one amenity to {amen.good_investment_pct[4]:.0f}% with five. (modelled)", "good"), CondPageBreak(11 * cm)]

    st += [Paragraph("7. Investment deep-dive", H1), Paragraph("SQL queries Q25-Q33 · window functions, CTEs, ranking", CAP), sp(4),
           block(F["val"], "Good-Investment rate by valuation band (SQL Q26)",
                 f"Deep discounts qualify {val.good_investment_pct[0]:.0f}% of the time; premium-priced homes (above 1.5× the city median) never do, by definition of the rule. Negotiating the entry price is the single strongest lever. (modelled)", "good")]
    q27 = sql("Q27").head(6)
    st += [KeepTogether([Paragraph("Top best-buy shortlist (SQL Q27 - first six rows; growth is capped at 14%)", H2),
           table([["ID", "City", "Type", "BHK", "Price (L)", "5-yr (L)", "Growth", "vs median"]] +
                 [[r.ID, r.City, r.Property_Type[:11], r.BHK, f"{r.Price_in_Lakhs:.0f}", f"{r.Future_Price_5Y_Lakhs:.0f}", f"{r.appreciation_pct:.1f}%", f"{r.Value_Ratio:.2f}x"] for r in q27.itertuples()],
                 [1.9, 2.8, 2.7, 1.2, 2, 2, 2, 2.4], font=7.5)]), sp(6), KeepTogether([Paragraph("SQL spotlight: valuation bands", H2),
           Preformatted(LIB["Q26"]["sql"].replace("\n  ", "\n "), ParagraphStyle("c", fontName="DV-M", fontSize=6.8, leading=8.8, backColor=colors.HexColor("#F2F6FB"), borderPadding=6, textColor=colors.HexColor(NAVY)))]),
           sp(8), insight("Percentage returns fall as price rises (cheaper bands sit below their city median) while rupee gains rise: the cheapest band projects ~10.1% a year, the 400L+ band ~7.4%.", "gold"), CondPageBreak(11 * cm)]

    st += [PageBreak(), Paragraph("8. Machine-learning results", H1), sp(2),
           Paragraph(f"Three models were compared for each task on a stratified 80/20 split; experiments are tracked with MLflow when installed. "
                     f"<b>{cl['best_model']}</b> won classification and <b>{rg['best_model']}</b> won regression.", base), sp(6),
           table([["Classifier", "Accuracy", "Precision", "Recall", "F1", "ROC-AUC"]] + [[r["model"], f"{r['accuracy']:.3f}", f"{r['precision']:.3f}", f"{r['recall']:.3f}", f"{r['f1']:.3f}", f"{r['roc_auc']:.3f}"] for r in cl["results"]], [5, 2.4, 2.4, 2.4, 2.4, 2.4]), sp(6),
           table([["Regressor", "RMSE (L)", "MAE (L)", "R²"]] + [[r["model"], f"{r['rmse']:.2f}", f"{r['mae']:.2f}", f"{r['r2']:.4f}"] for r in rg["results"]] +
                 [["Naive baseline (constant growth)", f"{rg['baseline_rmse']:.2f}", "-", "-"]], [7, 3.3, 3.3, 3.3]), sp(8),
           block(F["models"], "Classifier diagnostics and drivers",
                 f"The classifier correctly labels {(cm_acc := bc['accuracy']) * 100:.1f}% of unseen listings. Valuation versus the city median accounts for about {list(cl['importance'].values())[0] * 100:.0f}% of its predictive power, followed by availability status, price per sq ft and infrastructure.", "gold"),
           insight(f"<b>Interpretation.</b> Targets are rule-derived plus simulated noise, so the scores show how well the models learn the investment logic from property features, not accuracy on real sale prices. "
                   f"The regressor's RMSE of {br['rmse']:.1f}L is a {(1 - br['rmse'] / rg['baseline_rmse']) * 100:.0f}% improvement over a constant-growth baseline.", "warn"), CondPageBreak(11 * cm)]

    st += [Paragraph("9. Recommendations and limitations", H1),
           Paragraph("For investors", H2),
           Paragraph("1. <b>Negotiate to below the city median.</b> The Streamlit advisor shows the price at which a property turns into a Good Investment.<br/>"
                     "2. <b>Favour infrastructure and transit</b> over a prestige location: they cost no premium in this data.<br/>"
                     "3. <b>Prefer larger units</b> for lower cost per sq ft.<br/>4. <b>Look at under-construction stock</b> for the highest modelled upside, and weigh the delivery risk.", base),
           Paragraph("For real-estate platforms", H2),
           Paragraph("Show 'vs city median' beside every listing, surface the Good-Investment flag and confidence score, and fix floor-number validation at data entry.", base),
           Paragraph("Limitations", H2),
           Paragraph("• No price history: appreciation and 5-year price are scenario-based.<br/>• Descriptive data shows almost no link between price and location or amenities, typical of synthetic data.<br/>"
                     "• No crime-rate field, so the crime analysis in the brief could not be done.<br/>• Not financial advice.", base),
           Paragraph("Deliverables", H2),
           table([["Item", "File"], ["SQL analysis (33 queries)", "sql/real_estate_analysis.sql"], ["Streamlit app + SQL playground", "app.py, views/, src/"], ["Cleaned dataset", "data/housing_processed.csv"],
                  ["Training pipeline + MLflow", "scripts/run_pipeline.py, src/modeling.py"], ["Logo", "assets/logo.png / .svg"], ["Presentation", "EstateIQ_Presentation.pptx"]], [8, 9])]
    doc.build(st)
    return out


if __name__ == "__main__":
    figures = figs()
    pdf = build(figures)
    (C.REPORT_DIR / "summary.json").write_text(json.dumps(S, indent=2, default=str))
    print("PDF:", pdf)
