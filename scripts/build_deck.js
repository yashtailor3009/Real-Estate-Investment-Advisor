/**
 * build_deck.js - EstateIQ presentation (11 slides), built with pptxgenjs.
 * Run after generate_report.py + export_deck_data.py:
 *     node scripts/build_deck.js
 * Numbers come from reports/summary.json and reports/deck_data.json so the
 * deck always matches the PDF and the dashboard.
 */
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa");
const { applyTheme } = require("/mnt/skills/public/pptx/scripts/apply_theme.js");

const ROOT = path.resolve(__dirname, "..");
const S = JSON.parse(fs.readFileSync(path.join(ROOT, "reports/summary.json")));
const D = JSON.parse(fs.readFileSync(path.join(ROOT, "reports/deck_data.json")));
const LOGO_ICON = path.join(ROOT, "assets/logo_icon.png");
const LOGO_LIGHT = path.join(ROOT, "assets/logo_light.png");
const OUT = path.join(ROOT, "reports/EstateIQ_Presentation.pptx");

// ------------------------------------------------------------------ theme
const THEME = {
  name: "EstateIQ", headFontFace: "Trebuchet MS", bodyFontFace: "Calibri",
  colors: { dk1: "1B2B44", lt1: "FFFFFF", dk2: "0B1F3A", lt2: "F4F7FB", accent1: "14B8A6", accent2: "16325C",
            accent3: "F5B83D", accent4: "F2674B", accent5: "7C5CFC", accent6: "0F766E", hlink: "14B8A6", folHlink: "7C5CFC" },
};
const HEX = { navy: "0B1F3A", navy2: "16325C", teal: "14B8A6", tealD: "0F766E", gold: "F5B83D", coral: "F2674B",
              text: "1B2B44", muted: "6B7A90", grid: "E3E9F2", pale: "BBD0E3" };

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";               // 10 x 5.625 in
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "EstateIQ - Real Estate Investment Advisor";
pres.author = "EstateIQ";
const C = pres.SchemeColor;

// ---------------------------------------------------------------- layouts
pres.defineSlideMaster({
  title: "TITLE_DARK", background: { color: HEX.navy },
  objects: [
    { image: { path: LOGO_LIGHT, x: 0.6, y: 0.55, w: 3.1, h: 1.23 } },
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 2.0, w: 8.8, h: 1.4, fontSize: 30, align: "left", bold: true, color: "FFFFFF", valign: "top", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.6, y: 3.65, w: 7.6, h: 0.9, fontSize: 16, align: "left", color: "BFD3EA", valign: "top", margin: 0 }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "CONTENT", background: { color: HEX.navy.replace(HEX.navy, "F4F7FB") },
  objects: [
    { image: { path: LOGO_ICON, x: 0.45, y: 5.12, w: 0.34, h: 0.34 } },
    { text: { text: "EstateIQ · Real Estate Investment Advisor", options: { x: 0.85, y: 5.12, w: 4, h: 0.34, fontSize: 9, color: HEX.muted, valign: "middle", margin: 0 } } },
    { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.28, w: 9, h: 0.9, fontSize: 24, bold: true, color: HEX.navy, valign: "top", align: "left", margin: 0 }, text: "" } },
  ],
  slideNumber: { x: 9.2, y: 5.12, w: 0.4, h: 0.34, fontSize: 9, color: HEX.muted },
});
pres.defineSlideMaster({
  title: "CONTENT_DARK", background: { color: HEX.navy },
  objects: [
    { image: { path: LOGO_ICON, x: 0.45, y: 5.12, w: 0.34, h: 0.34 } },
    { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.28, w: 9, h: 0.9, fontSize: 24, bold: true, color: "FFFFFF", valign: "top", align: "left", margin: 0 }, text: "" } },
  ],
  slideNumber: { x: 9.2, y: 5.12, w: 0.4, h: 0.34, fontSize: 9, color: "BFD3EA" },
});

// ---------------------------------------------------------------- helpers
const shadow = () => ({ type: "outer", color: "1B2B44", blur: 8, offset: 2, angle: 90, opacity: 0.12 });

/** White rounded card behind content. */
function card(slide, x, y, w, h, name) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: C.background1 },
    line: { color: HEX.grid, width: 0.75 }, shadow: shadow(), objectName: name });
}

/** Big-number stat tile. */
function stat(slide, x, y, w, value, label, accent, name, fs = 26) {
  card(slide, x, y, w, 1.05, name + " card");
  slide.addShape(pres.shapes.RECTANGLE, { x: x + 0.01, y: y + 0.18, w: 0.07, h: 0.69, fill: { color: accent }, line: { color: accent, width: 0 }, objectName: name + " accent" });
  slide.addText(value, { x: x + 0.22, y: y + 0.1, w: w - 0.3, h: 0.55, fontSize: fs, bold: true, color: C.text2, fontFace: "Trebuchet MS", margin: 0, valign: "middle", isTextBox: true, objectName: name + " value" });
  slide.addText(label, { x: x + 0.22, y: y + 0.62, w: w - 0.3, h: 0.35, fontSize: 11, color: HEX.muted, margin: 0, valign: "top", isTextBox: true, objectName: name + " label" });
}

/** Insight call-out strip at the bottom of a slide. */
function insight(slide, text, y = 4.45, color = HEX.gold) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.5, y, w: 9, h: 0.55, rectRadius: 0.08, fill: { color: "FFFBEF" }, line: { color, width: 1 }, objectName: "Insight box" });
  slide.addText([{ text: "Insight  ", options: { bold: true, color: HEX.navy } }, { text, options: { color: HEX.text } }],
    { x: 0.65, y, w: 8.7, h: 0.55, fontSize: 12.5, valign: "middle", margin: 0, isTextBox: true, objectName: "Insight text" });
}

/** Render a react-icon to a PNG data URI. */
async function icon(Comp, color = "#FFFFFF", size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color, size: String(size) }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

/** Common chart styling (hex only; theme font via +mn-lt). */
function chartBase(extra) {
  return Object.assign({
    catAxisLabelColor: HEX.text, valAxisLabelColor: HEX.muted, catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt",
    catAxisLabelFontSize: 11, valAxisLabelFontSize: 10, valGridLine: { color: HEX.grid, size: 0.5 }, catGridLine: { style: "none" },
    showLegend: false, dataLabelFontFace: "+mn-lt", dataLabelFontSize: 11, dataLabelColor: HEX.text, titleFontFace: "+mn-lt",
  }, extra);
}

function chartTitle(slide, text, x, y, w) {
  slide.addText(text, { x, y, w, h: 0.35, fontSize: 14, bold: true, color: C.text2, margin: 0, isTextBox: true, objectName: "Chart title" });
}

// ------------------------------------------------------------------ build
(async () => {
  const ic = {
    chart: await icon(fa.FaChartBar), db: await icon(fa.FaDatabase), robot: await icon(fa.FaRobot), search: await icon(fa.FaSearch),
    home: await icon(fa.FaHome), file: await icon(fa.FaFilePdf), code: await icon(fa.FaCode), flask: await icon(fa.FaFlask),
    broom: await icon(fa.FaBroom), cogs: await icon(fa.FaCogs), rocket: await icon(fa.FaRocket), calc: await icon(fa.FaCalculator),
  };
  const section = (t) => pres.addSection({ title: t });

  // 1 ── Title
  section("Opening");
  let s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Opening" });
  s.addText("Is it a good investment, and what will it be worth in 5 years?", { placeholder: "title" });
  s.addText("Real estate analytics on 250,000 Indian listings: SQL insights, machine learning and an interactive Streamlit advisor.", { placeholder: "body" });
  s.addNotes("Welcome. This project answers two investor questions with data: a classification (good investment or not) and a regression (price in five years).");

  // 2 ── Approach
  section("Approach");
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Approach" });
  s.addText("One pipeline, four deliverables", { placeholder: "title" });
  const steps = [["broom", "Clean & engineer", "Duplicates, missing values, outliers, 10+ new features"], ["db", "Analyse in SQL", "33 documented queries on a 250K-row SQLite database"],
                 ["robot", "Model", "Classifier + 5-year price regressor, tracked with MLflow"], ["rocket", "Deliver", "Streamlit advisor, SQL lab, PDF report, this deck"]];
  steps.forEach(([k, t, d], i) => {
    const x = 0.5 + i * 2.28;
    card(s, x, 1.45, 2.08, 3.0, `Step ${i + 1} card`);
    s.addShape(pres.shapes.OVAL, { x: x + 0.74, y: 1.7, w: 0.6, h: 0.6, fill: { color: C.accent1 }, line: { color: C.accent1, width: 0 }, objectName: `Step ${i + 1} badge` });
    s.addImage({ data: ic[k], x: x + 0.89, y: 1.85, w: 0.3, h: 0.3, altText: t });
    s.addText(t, { x: x + 0.15, y: 2.5, w: 1.78, h: 0.4, fontSize: 15, bold: true, color: C.text2, align: "center", margin: 0, isTextBox: true, objectName: `Step ${i + 1} title` });
    s.addText(d, { x: x + 0.15, y: 2.95, w: 1.78, h: 1.3, fontSize: 12, color: HEX.muted, align: "center", valign: "top", margin: 0, isTextBox: true, objectName: `Step ${i + 1} text` });
  });
  s.addText("Raw CSV  →  cleaned data  →  SQLite + models  →  Streamlit + reports", { x: 0.5, y: 4.62, w: 9, h: 0.3, fontSize: 12, italic: true, color: HEX.muted, align: "center", margin: 0, isTextBox: true, objectName: "Flow caption" });

  // 3 ── Data
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Approach" });
  s.addText("The data is clean, but one field is badly broken", { placeholder: "title" });
  stat(s, 0.5, 1.4, 2.1, "250,000", "listings, no duplicates or nulls", C.accent1, "Rows");
  stat(s, 2.75, 1.4, 2.1, "20/42/500", "states · cities · localities", C.accent2, "Geography", 20);
  stat(s, 5.0, 1.4, 2.1, `${S.floor_bad_pct}%`, "rows with floor above building height", C.accent4, "Floors");
  stat(s, 7.25, 1.4, 2.25, `${S.ppsf_out_pct}%`, "price/sq ft outliers (IQR rule)", C.accent3, "Outliers");
  card(s, 0.5, 2.65, 9, 1.6, "Targets card");
  s.addText([{ text: "The brief's targets are not in the file, so they are modelled", options: { bold: true, color: HEX.navy, breakLine: true } },
             { text: "Annual appreciation = 4.5% base + infrastructure + amenities + security/parking + construction status + building age + price vs city median + simulated noise.", options: { breakLine: true } },
             { text: "5-year price = price × (1 + appreciation)^5.   Good Investment = appreciation ≥ 9% and price/sq ft ≤ 1.5× the city median.", options: {} }],
    { x: 0.75, y: 2.75, w: 8.5, h: 1.4, fontSize: 13, color: HEX.text, valign: "middle", paraSpaceAfter: 6, margin: 0, isTextBox: true, objectName: "Targets text" });
  insight(s, `${S.good_pct.toFixed(0)}% of listings qualify as a Good Investment. Descriptive charts are observed data; investment metrics are scenario-based.`, 4.45, HEX.coral);
  s.addNotes("Be upfront: the dataset has no price history, so appreciation and the label come from transparent rules plus noise.");

  // 4 ── Flat prices
  section("Insights");
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Insights" });
  s.addText("Where you buy barely changes what you pay per sq ft", { placeholder: "title" });
  const gk = Object.keys(D.gaps).filter((k) => k !== "Size band").sort((a, b) => D.gaps[a] - D.gaps[b]);
  card(s, 0.5, 1.3, 5.6, 3.05, "Chart card");
  chartTitle(s, "Gap between highest and lowest group average (% of overall)", 0.7, 1.38, 5.3);
  s.addChart(pres.charts.BAR, [{ name: "Gap %", labels: gk, values: gk.map((k) => D.gaps[k]) }],
    chartBase({ x: 0.6, y: 1.75, w: 5.4, h: 2.55, barDir: "bar", chartColors: [HEX.teal], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: '0.0"%"', valAxisHidden: true, valGridLine: { style: "none" }, valAxisMaxVal: 6 }));
  card(s, 6.3, 1.3, 3.2, 3.05, "Contrast card");
  s.addText("By contrast", { x: 6.5, y: 1.42, w: 2.8, h: 0.3, fontSize: 12, color: HEX.muted, margin: 0, isTextBox: true, objectName: "Contrast label" });
  s.addText(`${Math.round(D.gaps["Size band"])}%`, { x: 6.5, y: 1.75, w: 2.8, h: 0.9, fontSize: 44, bold: true, color: C.accent4, fontFace: "Trebuchet MS", margin: 0, isTextBox: true, objectName: "Size gap value" });
  s.addText("gap in price per sq ft between the smallest and largest size bands", { x: 6.5, y: 2.7, w: 2.8, h: 0.8, fontSize: 13, color: HEX.text, valign: "top", margin: 0, isTextBox: true, objectName: "Size gap text" });
  insight(s, "State, city, type, furnishing, facing and transit all sit within 5% of each other. Size is the only real price driver per sq ft.");
  s.addNotes("Each bar is the max-min of group average price per square foot divided by the overall mean. Seven of eight factors are essentially flat.");

  // 5 ── Size
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Insights" });
  s.addText("Bigger homes are far cheaper per sq ft", { placeholder: "title" });
  card(s, 0.5, 1.3, 6.1, 3.05, "Chart card");
  chartTitle(s, "Average ₹ per sq ft by size band (sq ft)", 0.7, 1.38, 5.8);
  s.addChart(pres.charts.BAR, [{ name: "₹/sq ft", labels: D.size_band.labels, values: D.size_band.values }],
    chartBase({ x: 0.6, y: 1.75, w: 5.9, h: 2.55, barDir: "col", chartColors: [HEX.navy2], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "#,##0", dataLabelFontSize: 9, catAxisLabelFontSize: 9, valAxisHidden: true, valGridLine: { style: "none" } }));
  stat(s, 6.8, 1.3, 2.7, `r = ${S.corr_size_ppsf.toFixed(2)}`, "size vs price per sq ft", C.accent4, "Corr ppsf");
  stat(s, 6.8, 2.5, 2.7, `r = ${D.price_size_corr.toFixed(2)}`, "size vs total price", C.accent2, "Corr price");
  s.addText("Total price ignores area, so large units are the best value per sq ft.", { x: 6.8, y: 3.7, w: 2.7, h: 0.65, fontSize: 12, color: HEX.text, valign: "top", margin: 0, isTextBox: true, objectName: "Size note" });
  insight(s, "Screen for larger units first: the same budget buys far more space in the 4,000-5,000 sq ft bands.");

  // 6 ── Valuation lever
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Insights" });
  s.addText("Entry price versus the city median is the biggest lever", { placeholder: "title" });
  const vb = S.val_bands;
  card(s, 0.5, 1.3, 6.1, 3.05, "Chart card");
  chartTitle(s, "% of listings that are Good Investments (modelled)", 0.7, 1.38, 5.8);
  s.addChart(pres.charts.BAR, [{ name: "Good %", labels: ["Deep discount (<0.5x)", "Below median (0.5-1x)", "Above median (1-1.5x)", "Premium (>1.5x)"], values: vb.map((v) => v[1]) }],
    chartBase({ x: 0.6, y: 1.75, w: 5.9, h: 2.55, barDir: "col", chartColors: [HEX.tealD, HEX.teal, HEX.gold, HEX.coral], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: '0"%"', valAxisHidden: true, valGridLine: { style: "none" }, valAxisMaxVal: 100, catAxisLabelFontSize: 10 }));
  card(s, 6.8, 1.3, 2.7, 3.05, "Model drivers card");
  s.addText("Top model drivers", { x: 7.0, y: 1.42, w: 2.3, h: 0.3, fontSize: 13, bold: true, color: C.text2, margin: 0, isTextBox: true, objectName: "Drivers title" });
  const imp = Object.entries(S.importance).slice(0, 5);
  imp.forEach(([k, v], i) => {
    s.addText(k.replace(/_/g, " "), { x: 7.0, y: 1.85 + i * 0.48, w: 1.5, h: 0.4, fontSize: 11, color: HEX.text, margin: 0, valign: "middle", isTextBox: true, objectName: `Driver ${i + 1} name` });
    s.addText(`${(v * 100).toFixed(0)}%`, { x: 8.55, y: 1.85 + i * 0.48, w: 0.8, h: 0.4, fontSize: 13, bold: true, color: C.accent6, align: "right", margin: 0, valign: "middle", isTextBox: true, objectName: `Driver ${i + 1} value` });
  });
  insight(s, "Negotiating to below the city median lifts the odds from 28% to 55% or more. The advisor shows the exact target price.");

  // 7 ── Amenities & transit
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Insights" });
  s.addText("Amenities, transit and timing add upside without adding price", { placeholder: "title" });
  card(s, 0.5, 1.3, 4.4, 3.05, "Amenity chart card");
  chartTitle(s, "Good-Investment rate by amenity count", 0.7, 1.38, 4.0);
  s.addChart(pres.charts.BAR, [{ name: "Good %", labels: S.amen.map((a) => String(a[0])), values: S.amen.map((a) => a[1]) }],
    chartBase({ x: 0.6, y: 1.75, w: 4.2, h: 2.55, barDir: "col", chartColors: [HEX.teal], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: '0"%"', valAxisHidden: true, valGridLine: { style: "none" }, valAxisMaxVal: 60 }));
  card(s, 5.1, 1.3, 4.4, 3.05, "Transit chart card");
  chartTitle(s, "By transit access and availability", 5.3, 1.38, 4.0);
  const tl = S.transit.map((t) => `Transit: ${t[0]}`).concat(S.avail.map((a) => a[0].replace(/_/g, " ")));
  const tv = S.transit.map((t) => t[1]).concat(S.avail.map((a) => a[1]));
  s.addChart(pres.charts.BAR, [{ name: "Good %", labels: tl, values: tv }],
    chartBase({ x: 5.2, y: 1.75, w: 4.2, h: 2.55, barDir: "bar", chartColors: [HEX.navy2], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: '0"%"', valAxisHidden: true, valGridLine: { style: "none" }, valAxisMaxVal: 65, catAxisLabelFontSize: 10 }));
  insight(s, "Price per sq ft is flat across all of these, so they are cheap sources of modelled upside. All rates are modelled.", 4.45, HEX.teal);

  // 8 ── Models
  section("Models");
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Models" });
  s.addText("Both models learn the investment logic well", { placeholder: "title" });
  stat(s, 0.5, 1.3, 2.1, `${(S.acc * 100).toFixed(1)}%`, "classifier accuracy", C.accent1, "Accuracy");
  stat(s, 2.75, 1.3, 2.1, S.auc.toFixed(3), "ROC-AUC", C.accent2, "AUC");
  stat(s, 5.0, 1.3, 2.1, `${S.rmse.toFixed(1)} L`, `RMSE vs ${S.base_rmse.toFixed(1)} L baseline`, C.accent3, "RMSE");
  stat(s, 7.25, 1.3, 2.25, S.r2.toFixed(3), "regression R²", C.accent5, "R2");
  card(s, 0.5, 2.5, 9, 1.85, "Table card");
  const hdr = (t) => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: HEX.navy }, align: "center" } });
  const rows = [[{ text: "Model", options: { bold: true, color: "FFFFFF", fill: { color: HEX.navy } } }, hdr("Accuracy"), hdr("ROC-AUC"), hdr("Regressor"), hdr("RMSE (L)"), hdr("R²")]];
  S.clf_results.forEach((c, i) => {
    const r = S.reg_results.find((x) => x.model.includes(c.model.split(" ")[0])) || S.reg_results[i];
    const best = c.model === S.clf_best;
    const o = { align: "center", bold: best, color: best ? HEX.tealD : HEX.text };
    rows.push([{ text: c.model, options: { bold: best, color: best ? HEX.tealD : HEX.text } }, { text: c.accuracy.toFixed(3), options: o }, { text: c.roc_auc.toFixed(3), options: o },
               { text: r.model, options: o }, { text: r.rmse.toFixed(2), options: o }, { text: r.r2.toFixed(4), options: o }]);
  });
  s.addTable(rows, { x: 0.7, y: 2.65, w: 8.6, colW: [1.9, 1.2, 1.2, 1.9, 1.2, 1.2], fontSize: 12, color: HEX.text, border: { type: "solid", color: HEX.grid, pt: 0.5 }, rowH: 0.36, valign: "middle", fill: { color: "FFFFFF" } });
  insight(s, "Scores show how well models learn the rule-based targets (plus noise), not accuracy on real sale prices. Gradient Boosting wins both tasks.", 4.45, HEX.coral);
  s.addNotes("The regression beats a constant-growth baseline by more than half on RMSE. Be clear that targets are rule-derived.");

  // 9 ── App & SQL
  section("Delivery");
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Delivery" });
  s.addText("A dashboard investors can actually use", { placeholder: "title" });
  const feats = [["search", "Investment Advisor", "Enter a property: verdict, confidence gauge, 5-year price, negotiation target"],
                 ["chart", "Market Explorer", "20 guided questions with annotated, interactive charts and takeaways"],
                 ["home", "Property Finder", "Filter by area, price, BHK; rank by projected gain; download CSV"],
                 ["code", "SQL Lab", "Live read-only SQL playground with 33 ready queries and auto-charts"],
                 ["flask", "Model Insights", "Model comparison, ROC, confusion matrix, feature importance, MLflow"],
                 ["file", "Reports", "Insights PDF, SQL file, cleaned dataset and this presentation"]];
  feats.forEach(([k, t, d], i) => {
    const x = 0.5 + (i % 3) * 3.07, y = 1.35 + Math.floor(i / 3) * 1.58;
    card(s, x, y, 2.9, 1.42, `Feature ${i + 1} card`);
    s.addShape(pres.shapes.OVAL, { x: x + 0.18, y: y + 0.2, w: 0.5, h: 0.5, fill: { color: i % 2 ? C.accent2 : C.accent1 }, line: { color: C.accent1, width: 0 }, objectName: `Feature ${i + 1} badge` });
    s.addImage({ data: ic[k], x: x + 0.3, y: y + 0.32, w: 0.26, h: 0.26, altText: t });
    s.addText(t, { x: x + 0.8, y: y + 0.2, w: 2.0, h: 0.5, fontSize: 14, bold: true, color: C.text2, valign: "middle", margin: 0, isTextBox: true, objectName: `Feature ${i + 1} title` });
    s.addText(d, { x: x + 0.18, y: y + 0.76, w: 2.6, h: 0.6, fontSize: 11, color: HEX.muted, valign: "top", margin: 0, isTextBox: true, objectName: `Feature ${i + 1} text` });
  });
  s.addText("Run:  streamlit run app.py", { x: 0.5, y: 4.62, w: 9, h: 0.3, fontSize: 12, italic: true, color: HEX.muted, align: "center", margin: 0, isTextBox: true, objectName: "Run hint" });

  // 10 ── Recommendations
  section("Close");
  s = pres.addSlide({ masterName: "CONTENT_DARK", sectionTitle: "Close" });
  s.addText("What an investor should do", { placeholder: "title" });
  const recs = [["1", "Buy below the city median", "Use the advisor's negotiation target; discounts raise Good-Investment odds from 28% to 55-81%."],
                ["2", "Favour fundamentals over prestige", "Infrastructure, transit and amenities carry no price premium here."],
                ["3", "Choose larger units", "Cost per sq ft falls steeply with size while total price stays flat."],
                ["4", "Weigh under-construction stock", "Highest modelled upside, with delivery risk to consider."]];
  recs.forEach(([n, t, d], i) => {
    const y = 1.3 + i * 0.9;
    s.addShape(pres.shapes.OVAL, { x: 0.55, y: y + 0.08, w: 0.55, h: 0.55, fill: { color: C.accent1 }, line: { color: C.accent1, width: 0 }, objectName: `Rec ${n} badge` });
    s.addText(n, { x: 0.55, y: y + 0.08, w: 0.55, h: 0.55, fontSize: 18, bold: true, color: "FFFFFF", align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: `Rec ${n} number` });
    s.addText([{ text: t, options: { bold: true, fontSize: 16, color: "FFFFFF", breakLine: true } }, { text: d, options: { fontSize: 12.5, color: "BFD3EA" } }],
      { x: 1.3, y, w: 8.2, h: 0.75, valign: "middle", margin: 0, isTextBox: true, objectName: `Rec ${n} text` });
  });

  // 11 ── Limitations & next steps
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Close" });
  s.addText("Limitations and next steps", { placeholder: "title" });
  card(s, 0.5, 1.3, 4.4, 3.65, "Limits card");
  s.addText([{ text: "Limitations", options: { bold: true, fontSize: 16, color: HEX.coral, breakLine: true } },
             { text: "No price history: appreciation and 5-year price are scenario-based", options: { bullet: true, breakLine: true } },
             { text: "Descriptive data shows almost no link between price and location or amenities", options: { bullet: true, breakLine: true } },
             { text: "No crime-rate field, so that analysis was not possible", options: { bullet: true, breakLine: true } },
             { text: "Not financial advice", options: { bullet: true } }],
    { x: 0.75, y: 1.45, w: 3.95, h: 3.35, fontSize: 13, color: HEX.text, valign: "top", paraSpaceAfter: 8, margin: 0, isTextBox: true, objectName: "Limits text" });
  card(s, 5.1, 1.3, 4.4, 3.65, "Next card");
  s.addText([{ text: "Next steps", options: { bold: true, fontSize: 16, color: HEX.tealD, breakLine: true } },
             { text: "Replace the rule engine with real transaction history", options: { bullet: true, breakLine: true } },
             { text: "Add rental yield and loan EMI to the advisor", options: { bullet: true, breakLine: true } },
             { text: "Validate floor numbers at data entry", options: { bullet: true, breakLine: true } },
             { text: "Deploy on Streamlit Cloud and schedule monthly retraining", options: { bullet: true } }],
    { x: 5.35, y: 1.45, w: 3.95, h: 3.35, fontSize: 13, color: HEX.text, valign: "top", paraSpaceAfter: 8, margin: 0, isTextBox: true, objectName: "Next text" });

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("deck written:", OUT);
})();
