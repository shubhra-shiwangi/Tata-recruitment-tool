import streamlit as st

# ── Page config ────────────────────────────────────────────────
st.set_page_config(
    page_title="Tata Steel | Recruitment Tool",
    page_icon="🏭",
    layout="wide"
)

# ── Anthropic API key ──────────────────────────────────────────
# Paste your key from console.anthropic.com between the quotes
ANTHROPIC_API_KEY = st.secrets["ANTHROPIC_API_KEY"]

# ── Header ─────────────────────────────────────────────────────
st.markdown("## 🏭 Tata Steel — Recruitment & CV Evaluation Tool")
st.markdown("*AI-powered hiring analytics for HR internship project*")
st.divider()

# ── Two tabs ───────────────────────────────────────────────────
tab1, tab2 = st.tabs(["📊 Recruitment Dashboard", "🤖 CV Evaluator & Shortlist"])

with tab1:
    from dashboard import show_dashboard
    show_dashboard()

with tab2:
    from cv_evaluator import show_cv_evaluator
    show_cv_evaluator(ANTHROPIC_API_KEY)
