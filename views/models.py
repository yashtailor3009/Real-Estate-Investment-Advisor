"""Model Insights: metrics, comparison, diagnostics and MLflow notes."""
import pandas as pd
import streamlit as st

from src import ui, visuals as V


def render(metrics):
    clf, reg = metrics["classification"], metrics["regression"]
    ui.hero("Model Insights", "How the classifier and the regressor were built, compared and evaluated.",
            ["Logistic · Random Forest · Gradient Boosting", "MLflow tracked"])
    bc = next(r for r in clf["results"] if r["model"] == clf["best_model"])
    br = next(r for r in reg["results"] if r["model"] == reg["best_model"])

    c = st.columns(5)
    with c[0]: ui.kpi("Classifier", clf["best_model"], "best by ROC-AUC", "#14B8A6")
    with c[1]: ui.kpi("Accuracy", f"{bc['accuracy'] * 100:.1f}%", f"F1 {bc['f1']:.3f}", "#16325C")
    with c[2]: ui.kpi("ROC-AUC", f"{bc['roc_auc']:.3f}", "class separation", "#F5B83D")
    with c[3]: ui.kpi("Regressor RMSE", f"{br['rmse']:.1f} L", f"baseline {reg['baseline_rmse']:.1f} L", "#F2674B")
    with c[4]: ui.kpi("Regressor R²", f"{br['r2']:.3f}", reg["best_model"], "#7C5CFC")
    st.write("")

    ui.insight("Targets are built from the domain rules in <i>About & Method</i>, so these scores show how well the models "
               "<b>learn those rules from property features</b> (with simulated market noise), not how well they predict real-world sale prices. "
               "The regression R² is high mainly because the 5-year price is today's price grown by 2-14% a year; "
               "compare RMSE with the naive baseline to see the real lift.", "How to read these scores", "warn")

    tab1, tab2, tab3 = st.tabs(["🏁 Model comparison", "🔬 Diagnostics", "🧪 MLflow & training"])
    with tab1:
        a, b = st.columns(2)
        with a:
            ui.plot(V.model_comparison(clf["results"], "roc_auc", "Classification: ROC-AUC (higher is better)"), "m_c")
            ui.table(pd.DataFrame(clf["results"]), hide_index=True)
        with b:
            ui.plot(V.model_comparison(reg["results"], "rmse", "Regression: RMSE in ₹ lakhs (lower is better)", False), "m_r")
            ui.table(pd.DataFrame(reg["results"]), hide_index=True)
    with tab2:
        a, b = st.columns(2)
        with a: ui.plot(V.confusion_chart(clf["confusion_matrix"]), "m_cm")
        with b: ui.plot(V.roc_chart(clf["roc_curve"], bc["roc_auc"]), "m_roc")
        a, b = st.columns(2)
        with a: ui.plot(V.actual_vs_pred(reg["scatter"], br["rmse"], br["r2"]), "m_avp")
        with b: ui.plot(V.importance_chart(clf["importance"], "Classifier importance"), "m_imp")
        ui.insight("Valuation vs the city median dominates the classifier, followed by availability status, infrastructure and security - "
                   "consistent with the appreciation rules.", "Reading the drivers")
    with tab3:
        st.markdown(f"""
**Training set:** {metrics['rows']['train']:,} rows · **Test set:** {metrics['rows']['test']:,} rows (stratified 80/20 split)

**Pipeline:** `StandardScaler` on numeric features + `OneHotEncoder` on categoricals → model. Random Forest is fitted on a 60K-row sample for speed.

**MLflow:** {'enabled in this run - experiments are saved in `mlruns/`.' if metrics.get('mlflow_used') else 'was not installed when these models were trained; run `pip install mlflow` and re-run the pipeline to log experiments.'}
""")
        st.code("python scripts/run_pipeline.py   # retrain everything\nmlflow ui                         # open the experiment dashboard at http://127.0.0.1:5000", language="bash")
