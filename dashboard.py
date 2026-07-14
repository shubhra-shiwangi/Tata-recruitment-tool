import streamlit as st
import plotly.graph_objects as go
import pandas as pd

def show_dashboard():

    # ── Metric cards ───────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Active Vacancies",   "34",   "12 IRP · 22 External")
    col2.metric("CVs in Pipeline",    "218",  "+28 this week")
    col3.metric("Avg. Cycle Time",    "41 days", "-3 vs last month")
    col4.metric("Offer Acceptance",   "87%",  "+4% vs last quarter")

    st.divider()

    # ── Cycle time by recruitment type ─────────────────────────
    st.subheader("Cycle Time by Recruitment Type")
    st.caption("Target: IRP OPR = 30 days | IRP NOPR = 35 days | External NOPR = 40 days")

    cycle_data = {
        "Type":        ["IRP OPR", "IRP NOPR", "External NOPR"],
        "Actual (days)": [28,        44,          52],
        "Target (days)": [30,        35,          40],
    }
    df_cycle = pd.DataFrame(cycle_data)

    # Color bars: green if on track, red if over
    colors = []
    for actual, target in zip(df_cycle["Actual (days)"], df_cycle["Target (days)"]):
        colors.append("#1D9E75" if actual <= target else "#E24B4A")

    fig_cycle = go.Figure()
    fig_cycle.add_trace(go.Bar(
        name="Actual",
        x=df_cycle["Type"],
        y=df_cycle["Actual (days)"],
        marker_color=colors,
        text=df_cycle["Actual (days)"].astype(str) + "d",
        textposition="outside"
    ))
    fig_cycle.add_trace(go.Scatter(
        name="Target",
        x=df_cycle["Type"],
        y=df_cycle["Target (days)"],
        mode="markers+lines",
        marker=dict(symbol="line-ew", size=16, color="#888", line=dict(width=2, color="#888")),
        line=dict(dash="dot", color="#888")
    ))
    fig_cycle.update_layout(
        height=320,
        margin=dict(t=20, b=20, l=0, r=0),
        legend=dict(orientation="h", y=1.1),
        yaxis_title="Days",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig_cycle, use_container_width=True)

    st.divider()

    # ── Pipeline funnel and vacancy table side by side ─────────
    left, right = st.columns([1, 1.5])

    with left:
        st.subheader("Pipeline Funnel")
        funnel_data = dict(
            stages=["Applied","Screened","Shortlisted","Interviewed","Offered","Joined"],
            values=[218,       157,        82,           47,           26,       18]
        )
        fig_funnel = go.Figure(go.Funnel(
            y=funnel_data["stages"],
            x=funnel_data["values"],
            textinfo="value+percent initial",
            marker=dict(color=["#9FE1CB","#5DCAA5","#1D9E75","#EF9F27","#D85A30","#993C1D"])
        ))
        fig_funnel.update_layout(
            height=340,
            margin=dict(t=10, b=10, l=0, r=0),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_funnel, use_container_width=True)

    with right:
        st.subheader("Active Requisitions — Bottleneck Flags")

        vacancies = [
            {"Role": "Blast Furnace Operator", "Type": "IRP OPR",      "BU": "Iron Making",   "Days Open": 22, "Stage": "Shortlisting",     "Status": "✅ On Track"},
            {"Role": "Maintenance Engineer",   "Type": "External NOPR","BU": "Cold Rolling",  "Days Open": 58, "Stage": "Awaiting approval","Status": "🔴 Delayed"},
            {"Role": "Safety Officer",         "Type": "IRP NOPR",     "BU": "Corporate HSE", "Days Open": 47, "Stage": "Interviews",        "Status": "🔴 Delayed"},
            {"Role": "HR Generalist",          "Type": "External NOPR","BU": "HR Corporate",  "Days Open": 31, "Stage": "Screening",         "Status": "✅ On Track"},
            {"Role": "Shift Supervisor",       "Type": "IRP OPR",      "BU": "Hot Strip Mill","Days Open": 18, "Stage": "Shortlisting",      "Status": "✅ On Track"},
            {"Role": "Accounts Executive",     "Type": "External NOPR","BU": "Finance",       "Days Open": 63, "Stage": "Offer Stage",       "Status": "🔴 Delayed"},
        ]
        df_vac = pd.DataFrame(vacancies)

        # Highlight delayed rows in red
        def highlight_delayed(row):
            if "Delayed" in row["Status"]:
                return ["background-color: #fff0f0"] * len(row)
            return [""] * len(row)

        st.dataframe(
            df_vac.style.apply(highlight_delayed, axis=1),
            use_container_width=True,
            hide_index=True,
            height=320
        )

    st.divider()

    # ── DEI drive summary ──────────────────────────────────────
    st.subheader("DEI Diversity Drive — FY26 Progress")
    d1, d2, d3 = st.columns(3)

    with d1:
        st.markdown("**Women**")
        st.progress(0.64)
        st.caption("18 of 28 target placements")

    with d2:
        st.markdown("**TG (Transgender)**")
        st.progress(0.40)
        st.caption("4 of 10 target placements")

    with d3:
        st.markdown("**PWD (Persons with Disability)**")
        st.progress(0.55)
        st.caption("11 of 20 target placements")