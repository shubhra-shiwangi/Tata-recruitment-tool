import streamlit as st
import anthropic
import json
import io

# ── Libraries for reading different file formats ───────────────
try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    from docx import Document
except ImportError:
    Document = None


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


def extract_text_from_file(uploaded_file) -> str:
    """Extract plain text from PDF, DOCX, or TXT file."""
    name = uploaded_file.name.lower()
    raw  = uploaded_file.read()

    # ── PDF ────────────────────────────────────────────────────
    if name.endswith(".pdf"):
        if pdfplumber is None:
            return "ERROR: pdfplumber not installed. Run: pip install pdfplumber"
        try:
            text = ""
            with pdfplumber.open(io.BytesIO(raw)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text.strip() if text.strip() else "Could not extract text from this PDF."
        except Exception as e:
            return f"PDF read error: {e}"

    # ── DOCX ───────────────────────────────────────────────────
    elif name.endswith(".docx"):
        if Document is None:
            return "ERROR: python-docx not installed. Run: pip install python-docx"
        try:
            doc  = Document(io.BytesIO(raw))
            text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
            return text.strip() if text.strip() else "Could not extract text from this DOCX."
        except Exception as e:
            return f"DOCX read error: {e}"

    # ── TXT / plain text ───────────────────────────────────────
    elif name.endswith(".txt"):
        try:
            return raw.decode("utf-8").strip()
        except Exception:
            return raw.decode("latin-1").strip()

    else:
        return f"Unsupported file type: {uploaded_file.name}. Please upload PDF, DOCX, or TXT."


def show_cv_evaluator(api_key: str):

    st.subheader("AI-Powered CV Evaluator & Shortlist")
    st.caption("Upload CV files for each candidate. The AI will score and rank them against your job requirements.")

    # ── Install check ──────────────────────────────────────────
    missing_libs = []
    if pdfplumber is None:
        missing_libs.append("pdfplumber")
    if Document is None:
        missing_libs.append("python-docx")
    if missing_libs:
        st.warning(
            f"Some libraries are missing: `{', '.join(missing_libs)}`. "
            "PDF/DOCX upload may not work. "
            f"Fix: open Anaconda Prompt and run `pip install {' '.join(missing_libs)}`"
        )

    st.markdown("---")

    # ── Step 1: Job requirements ───────────────────────────────
    st.markdown("#### Step 1 — Enter job requirements")

    if st.button("📂 Load demo job description"):
        st.session_state["jd_text"] = DEMO_JD
        st.rerun()

    jd = st.text_area(
        "Paste the job description or list requirements here",
        value=st.session_state.get("jd_text", ""),
        height=180,
        placeholder=(
            "Example:\n"
            "- B.Tech Mechanical or Electrical Engineering\n"
            "- 3+ years in steel plant or heavy manufacturing\n"
            "- SAP PM module experience preferred\n"
            "- ISO 45001 safety certification\n"
            "- Rotating shift flexibility"
        ),
        key="jd_area"
    )

    st.markdown("---")

    # ── Step 2: Number of candidates ──────────────────────────
    st.markdown("#### Step 2 — How many candidates?")

    num = st.number_input(
        "Enter number of candidates",
        min_value=1,
        max_value=10,
        value=st.session_state.get("num_candidates", 2),
        step=1
    )
    st.session_state["num_candidates"] = int(num)

    st.markdown("---")

    # ── Step 3: Upload CVs ─────────────────────────────────────
    st.markdown("#### Step 3 — Upload candidate CVs")
    st.caption("Supported formats: PDF, DOCX, TXT")

    candidates = []

    for i in range(int(num)):
        st.markdown(f"**Candidate {i + 1}**")
        col1, col2 = st.columns([1, 2])

        with col1:
            name = st.text_input(
                "Candidate name",
                key=f"cand_name_{i}",
                placeholder=f"e.g. Candidate {i+1} name"
            )

        with col2:
            uploaded_file = st.file_uploader(
                "Upload CV (PDF / DOCX / TXT)",
                type=["pdf", "docx", "txt"],
                key=f"cand_file_{i}",
                label_visibility="visible"
            )

        if name.strip() and uploaded_file is not None:
            with st.spinner(f"Reading {uploaded_file.name}..."):
                cv_text = extract_text_from_file(uploaded_file)

            if cv_text.startswith("ERROR") or cv_text.startswith("Unsupported"):
                st.error(cv_text)
            else:
                st.success(f"✅ CV read successfully ({len(cv_text)} characters extracted)")
                with st.expander(f"Preview extracted text — {name}"):
                    st.text(cv_text[:800] + ("..." if len(cv_text) > 800 else ""))
                candidates.append({"name": name.strip(), "cv": cv_text})

        elif name.strip() and uploaded_file is None:
            st.info(f"Waiting for CV file for {name}...")

    st.markdown("---")

    # ── Step 4: Evaluate ───────────────────────────────────────
    st.markdown("#### Step 4 — Evaluate and shortlist")

    if st.button("🤖 Evaluate and Shortlist", type="primary", use_container_width=True):

        if not jd.strip():
            st.error("Please enter job requirements in Step 1.")
            return

        if len(candidates) == 0:
            st.error("Please enter at least one candidate name and upload their CV.")
            return

        if len(candidates) < int(num):
            st.warning(
                f"Only {len(candidates)} of {int(num)} candidates have both a name and CV uploaded. "
                "Evaluating the ones that are ready."
            )

        with st.spinner(f"AI is evaluating {len(candidates)} candidate(s)... please wait"):
            results = evaluate_cvs(api_key, jd, candidates)
            st.session_state["last_results"] = results

    # ── Show results ───────────────────────────────────────────
    if st.session_state.get("last_results"):
        display_results(st.session_state["last_results"])


def evaluate_cvs(api_key: str, jd: str, candidates: list) -> list:
    """Send CVs to Claude API and get back scored results."""
    client = anthropic.Anthropic(api_key=api_key)

    candidates_text = "\n\n".join([
        f"--- Candidate {i+1}: {c['name']} ---\n{c['cv']}"
        for i, c in enumerate(candidates)
    ])

    prompt = f"""You are an expert HR recruiter at Tata Steel. Evaluate each candidate's CV against the job requirements below.

JOB REQUIREMENTS:
{jd}

CANDIDATES:
{candidates_text}

Return ONLY a valid JSON array. No explanation, no markdown, no backticks whatsoever.

Each object in the array must have exactly these fields:
- "name": candidate name as string
- "score": integer from 0 to 100 representing % match
- "verdict": exactly one of "Strong match", "Partial match", or "Weak match"
- "matched": list of up to 5 short phrases for requirements clearly met
- "missing": list of up to 4 short phrases for key requirements NOT met
- "partial": list of up to 3 short phrases for partially met requirements
- "summary": one sentence, maximum 20 words, explaining their ranking

Sort results by score from highest to lowest.
Be specific and honest — scores should meaningfully differentiate candidates."""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        raw   = message.content[0].text
        clean = raw.replace("```json", "").replace("```", "").strip()
        data  = json.loads(clean)
        return sorted(data, key=lambda x: x.get("score", 0), reverse=True)

    except json.JSONDecodeError as e:
        st.error(f"Could not parse AI response as JSON: {e}")
        return []
    except Exception as e:
        st.error(f"API error: {e}")
        return []


def display_results(results: list):
    """Display ranked shortlist with scores and breakdowns."""
    st.divider()
    st.subheader("📋 Shortlist — Ranked by Match Score")

    strong  = sum(1 for r in results if r.get("score", 0) >= 70)
    partial = sum(1 for r in results if 40 <= r.get("score", 0) < 70)
    weak    = sum(1 for r in results if r.get("score", 0) < 40)

    m1, m2, m3 = st.columns(3)
    m1.metric("🟢 Strong matches (≥70%)", strong)
    m2.metric("🟡 Partial matches (40–69%)", partial)
    m3.metric("🔴 Weak matches (<40%)", weak)

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
            icon = rank_icons[i] if i < 3 else "✅"
        elif score >= 40:
            icon = "⚠️"
        else:
            icon = "❌"

        with st.container(border=True):
            left, right = st.columns([0.08, 0.92])

            with left:
                st.markdown(f"### {icon}")

            with right:
                st.markdown(f"**#{i+1} — {name}**")
                st.caption(summary)

                bar_col, score_col = st.columns([4, 1])
                with bar_col:
                    st.progress(score / 100)
                with score_col:
                    st.markdown(f"**{score}%**")
                    st.caption(verdict)

                if matched:
                    st.markdown("✅ **Meets:** " + " · ".join(matched))
                if partial_reqs:
                    st.markdown("🔶 **Partial:** " + " · ".join(partial_reqs))
                if missing:
                    st.markdown("❌ **Missing:** " + " · ".join(missing))

    # ── Export shortlist ───────────────────────────────────────
    st.markdown("---")
    export_lines = ["TATA STEEL — CV EVALUATION SHORTLIST\n"]
    for i, r in enumerate(results):
        export_lines.append(
            f"#{i+1} {r.get('name','')} — {r.get('score',0)}% — {r.get('verdict','')}\n"
            f"Summary: {r.get('summary','')}\n"
            f"Meets: {', '.join(r.get('matched',[]))}\n"
            f"Missing: {', '.join(r.get('missing',[]))}\n"
        )
    export_text = "\n".join(export_lines)

    st.download_button(
        label="⬇️ Download shortlist as TXT",
        data=export_text,
        file_name="tata_steel_shortlist.txt",
        mime="text/plain"
    )
