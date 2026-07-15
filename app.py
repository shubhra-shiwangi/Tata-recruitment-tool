import streamlit as st

st.set_page_config(
    page_title="Tata Steel | Recruitment Tool",
    page_icon="🏭",
    layout="wide"
)

ANTHROPIC_API_KEY = st.secrets["ANTHROPIC_API_KEY"]

st.markdown("## 🏭 Tata Steel — Recruitment & CV Evaluation Tool")
st.markdown("*AI-powered hiring analytics for HR internship project*")
st.divider()

tab1, tab2 = st.tabs(["📊 Recruitment Dashboard", "🤖 CV Evaluator & Shortlist"])

with tab1:
    from dashboard import show_dashboard
    show_dashboard()

with tab2:
    from cv_evaluator import show_cv_evaluator
    show_cv_evaluator(ANTHROPIC_API_KEY)
