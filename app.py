import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import streamlit as st
import pandas as pd
import plotly.express as px

from lbidsm.analytics import metrics, features
from lbidsm.simulation import synthetic_cgm
from lbidsm.rules import observations

st.set_page_config(page_title="LBIDSM-DM | Research", layout="wide")
st.title("LBIDSM-DM · Diabetes Intervention Intelligence")
st.caption("Computational research demonstrator · Synthetic/consented data only · NOT for diagnosis, emergency triage, or medication adjustment")
st.warning("This app is not a medical device. It does not predict validated individual risk or recommend treatment. If you have urgent symptoms, seek appropriate medical care rather than relying on this tool.")

with st.sidebar:
    st.header("Data source")
    mode = st.radio("Select source", ["Synthetic demonstration", "Upload CGM CSV"])
    seed = st.number_input("Synthetic random seed", min_value=0, max_value=100000, value=42, disabled=mode != "Synthetic demonstration")
    uploaded = st.file_uploader("CSV: timestamp, glucose_mg_dl", type=["csv"], disabled=mode != "Upload CGM CSV")
    st.caption("Uploaded data are processed in the running app session; avoid uploading identifiable medical data to untrusted deployments.")

try:
    df = synthetic_cgm(seed=int(seed)) if mode == "Synthetic demonstration" else pd.read_csv(uploaded) if uploaded else None
    if df is None:
        st.info("Upload a CGM CSV to begin.")
        st.stop()
    m = metrics(df)
    tabs = st.tabs(["CGM overview", "Dynamic signals", "Clinical context", "Architecture and paper", "Data dictionary"])
    with tabs[0]:
        cols = st.columns(4)
        for col, (k, label) in zip(cols, [
            ("tir_70_180_percent", "TIR 70–180 (%)"),
            ("tbr_70_percent", "TBR <70 (%)"),
            ("cv_percent", "Glucose CV (%)"),
            ("observed_hours", "Usable interval hours"),
        ]):
            col.metric(label, m[k])
        st.plotly_chart(px.line(df, x="timestamp", y="glucose_mg_dl", title="Glucose trajectory (mg/dL)"), use_container_width=True)
        st.dataframe(pd.DataFrame([m]), hide_index=True)
        st.caption("Coverage is based on valid adjacent sample intervals (up to 15 minutes), not a validated CGM wear-time measure.")
    with tabs[1]:
        f = features(df)
        st.plotly_chart(px.line(f, x="timestamp", y=["velocity_mg_dl_min"], title="Glucose velocity (mg/dL/min)"), use_container_width=True)
        st.plotly_chart(px.line(f, x="timestamp", y=["rolling_mean_12", "rolling_sd_12"], title="Rolling signal features (12 readings)"), use_container_width=True)
        st.info("Dynamic features are exploratory; no clinical intervention thresholds have been validated for them.")
    with tabs[2]:
        st.subheader("Descriptive threshold annotations")
        g = st.number_input("Example glucose (mg/dL)", min_value=20.0, max_value=600.0, value=110.0)
        a = st.number_input("Example HbA1c (%)", min_value=3.0, max_value=20.0, value=7.0)
        for item in observations(g, a):
            st.write("• " + item)
        st.info("Predisposition, history, comorbidities, medication exposure and causal treatment effects are specified in the paper but are not estimated by this demonstration.")
    with tabs[3]:
        st.markdown("**Layers:** provenance → predisposition → comorbidity → physiological burden → dynamics → outcome prediction → causal intervention evaluation → clinical governance.")
        st.markdown("Read the research paper: [paper/WHITE_PAPER.md](paper/WHITE_PAPER.md).")
        st.markdown("**Research status:** prediction and causal decision layers are architectural specifications, not trained models.")
    with tabs[4]:
        st.code("timestamp: ISO-8601 timestamp with timezone\nglucose_mg_dl: CGM glucose in mg/dL", language="text")
        st.download_button("Download synthetic CSV", synthetic_cgm().to_csv(index=False), "synthetic_cgm.csv", "text/csv")
except Exception as e:
    st.error(f"Unable to analyze dataset: {e}")
