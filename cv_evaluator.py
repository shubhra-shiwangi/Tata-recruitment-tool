import streamlit as st
import anthropic
import json

DEMO_JD = """Job: Maintenance Engineer — Cold Rolling Mill, Tata Steel Jamshedpur

Requirements:
- B.Tech / B.E. in Mechanical or Electrical Engineering
- Minimum 3 years experience in steel plant or heavy manufacturing
- Knowledge of hydraulic and pneumatic systems
- Preventive maintenance planning experience
- SAP PM module experience preferred
- ISO 45001 / safety certification preferred
- Ability to work rotating shifts
- Team coordination and reporting skills"""

DEMO_CANDIDATES = [
    {
        "name": "Ankit Verma",
        "cv": """B.Tech Mechanical Engineering, NIT Jamshedpur, 2018
5 years at Jindal Steel, Cold Rolling department
Extensive hydraulic and pneumatic systems maintenance
SAP PM module — daily user for 3 years
ISO 45001 certified (2021)
Led a team of 6 maintenance technicians
Comfortable with rotating shifts
Implemented preventive maintenance schedule reducing downtime by 18%"""
    },
    {
        "name": "Priya Nair",
        "cv": """B.E. Electrical Engineering, BITS Pilani, 2020
2 years at Tata Motors, assembly line maintenance
Basic knowledge of pneumatic systems
No SAP experience
Shift work experience: yes
Strong documentation and reporting skills
Currently pursuing ISO certification"""
    },
    {
        "name": "Suresh Kumar",
        "cv": """Diploma in Mechanical Engineering, 2015
8 years at SAIL Bokaro, blast furnace maintenance
Expert in hydraulic systems
No formal SAP training but Excel-based maintenance logs
No ISO certification
Works day shifts only
Managed 4-person team"""
    },
    {
        "name": "Meera Joshi",
        "cv": """B.Tech Mechanical, VNIT Nagpur, 2019
4 years at ArcelorMittal Hazira, hot strip mill maintenance
Hydraulic and pneumatic systems — daily work
SAP PM module trained (2022)
ISO 45001 in progress
Rotating shifts — comfortable
Co-authored plant's preventive maintenance SOPs"""
    },
]


def init_state():
    """Initialise all session state keys safely."""
    defaults = {
        "demo_loaded": False,
        "num_candidates": 2,
        "results": None,
        "jd": "",
        "candidate_names": ["", ""],
        "candidate_cvs": ["", ""],
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def load_demo():
    """Write demo data straight into session state."""
    st.session_state.demo_loaded = True
    st.session_state.num_candidates = 4
    st.session_state.jd = DEMO_JD
    st.session_state.results = None
    st.session_state.candidate_names = [c["name"] for c in DEMO_CANDIDATES]
    st.session_state.candidate_cvs  = [c["cv"]   for c in DEMO_CANDIDATES]


def show_cv_evaluator(api_key: str):

    st.subheader("AI-Powered CV Evaluator & Shortlist")
    st.caption(
        "Paste the job requirements and up to 5 candidate CVs. "
        "The AI will score each CV against the requirements and rank the shortlist."
    )

    init_state()

    # ── Demo button ────────────────────────────────────────────
    if st.button("📂 Load demo data (Maintenance Engineer role)"):
        load_demo()
        st.rerun()

    # ── Job description ────────────────────────────────────────
    st.markdown("#### Step 1 — Enter job requirements")
    st.session_state.jd = st.text_area(
        "Job description / requirements",
        value=st.session_state.jd,
        height=180,
        placeholder=(
            "Example:\n"
            "- B.Tech Mechanical or Electrical Engineering\n"
            "- 3+ years in steel plant or heavy manufacturing\n"
            "- SAP PM module experience preferred\n"
            "- ISO 45001 safety certification"
        )
    )

    # ── Number of candidates ───────────────────────────────────
    st.markdown("#### Step 2 — Add candidate CVs")

    new_num = st.slider(
        "How many candidates?",
        min_value=1,
        max_value=5,
        value=st.session_state.num_candidates
    )

    # Resize lists if slider changed
    if new_num != st.session_state.num_candidates:
        st.session_state.num_candidates = new_num
        # Pad or trim the lists
        while len(st.session_state.candidate_names) < new_num:
            st.session_state.candidate_names.append("")
        while len(st.session_state.candidate_cvs) < new_num:
            st.session_state.candidate_cvs.append("")
        st.session_state.candidate_names = st.session_state.candidate_names[:new_num]
        st.session_state.candidate_cvs   = st.session_state.candidate_cvs[:new_num]

    # ── CV input boxes ─────────────────────────────────────────
    candidates = []

    for i in range(st.session_state.num_candidates):
        st.markdown(f"**Candidate {i + 1}**")
        c1, c2 = st.columns([1, 3])

        with c1:
            name = st.text_input(
                "Name",
                value=st.session_state.candidate_names[i],
                key=f"name_input_{i}",
                placeholder="e.g. Rahul Sharma"
            )
            st.session_state.candidate_names[i] = name

        with c2:
            cv_text = st.text_area(
                "Paste CV text",
                value=st.session_state.candidate_cvs[i],
                key=f"cv_input_{i}",
                height=130,
                placeholder="Paste candidate's CV or resume text here..."
            )
            st.session_state.candidate_cvs[i] = cv_text

        if name.strip() and cv_text.strip():
            candidates.append({"name": name.strip(), "cv": cv_text.strip()})

    # ── Evaluate button ────────────────────────────────────────
    st.markdown("#### Step 3 — Evaluate")
    run_btn = st.button(
        "🤖 Evaluate and Shortlist",
        type="primary",
        use_container_width=True
    )

    if run_btn:
        if not st.session_state.jd.strip():
            st.error("Please enter the job requirements first.")
            return
        if len(candidates) == 0:
            st.error("Please add at least one candidate name and CV.")
            return

        with st.spinner(f"AI is evaluating {len(candidates)} candidate(s)... please wait"):
            results = evaluate_cvs(api_key, st.session_state.jd, candidates)
            st.session_state.results = results

    # ── Show results ───────────────────────────────────────────
    if st.session_state.results:
        display_results(st.session_state.results)


def evaluate_cvs(api_key: str, jd: str, candidates: list) -> list:
    client = anthropic.Anthropic(api_key=api_key)

    candidates_text = "\n\n".join([
        f"--- Candidate {i+1}: {c['name']} ---\n{c['cv']}"
        for i, c in enumerate(candidates)
    ])

    prompt = f"""You are an expert HR recruiter at Tata Steel. Evaluate each candidate CV against the job requirements below.

JOB REQUIREMENTS:
{jd}

CANDIDATES:
{candidates_text}

Return ONLY a valid JSON array — no explanation, no markdown, no backticks.

Each object in the array must have:
- "name": candidate name (string)
- "score": overall match percentage as integer 0-100
- "verdict": one of "Strong match", "Partial match", "Weak match"
- "matched": list of up to 5 requirements clearly met (short phrases)
- "missing": list of up to 4 key requirements NOT met (short phrases)
- "partial": list of up to 3 partially met requirements (short phrases)
- "summary": one sentence (max 20 words) on why they rank where they do

Sort by score descending. Be honest — scores must meaningfully differentiate candidates."""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = message.content[0].text
        clean = raw.replace("```json", "").replace("```", "").strip()
        results = json.loads(clean)
        return sorted(results, key=lambda x: x.get("score", 0), reverse=True)
    except Exception as e:
        st.error(f"API error: {e}")
        return []


def display_results(results: list):
    st.divider()
    st.subheader("Shortlist — Ranked by Match Score")

    strong  = sum(1 for r in results if r.get("score", 0) >= 70)
    partial = sum(1 for r in results if 40 <= r.get("score", 0) < 70)
    weak    = sum(1 for r in results if r.get("score", 0) < 40)

    m1, m2, m3 = st.columns(3)
    m1.metric("Strong matches (≥70%)", strong)
    m2.metric("Partial matches (40–69%)", partial)
    m3.metric("Weak matches (<40%)", weak)

    st.markdown("---")

    rank_icons = ["🥇", "🥈", "🥉"]

    for i, r in enumerate(results):
        score        = r.get("score", 0)
        name         = r.get("name", f"Candidate {i+1}")
        verdict      = r.get("verdict", "")
        summary      = r.get("summary", "")
        matched      = r.get("matched", [])
        missing      = r.get("missing", [])
        partial_reqs = r.get("partial", [])

        if score >= 70:
            rank_icon = rank_icons[i] if i < 3 else "✅"
        elif score >= 40:
            rank_icon = "⚠️"
        else:
            rank_icon = "❌"

        with st.container(border=True):
            col_rank, col_info = st.columns([0.08, 0.92])

            with col_rank:
                st.markdown(f"### {rank_icon}")

            with col_info:
                st.markdown(f"**#{i+1} — {name}**")
                st.caption(summary)

                sc1, sc2 = st.columns([4, 1])
                with sc1:
                    st.progress(score / 100)
                with sc2:
                    st.markdown(f"**{score}%** — {verdict}")

                if matched:
                    st.markdown("✅ **Meets:** " + " · ".join(matched))
                if partial_reqs:
                    st.markdown("🔶 **Partial:** " + " · ".join(partial_reqs))
                if missing:
                    st.markdown("❌ **Missing:** " + " · ".join(missing))
