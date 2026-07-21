import streamlit as st
import io
import re

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    from docx import Document
except ImportError:
    Document = None


# ── Text extraction ────────────────────────────────────────────
def extract_text_from_file(uploaded_file) -> str:
    name = uploaded_file.name.lower()
    raw  = uploaded_file.read()

    if name.endswith(".pdf"):
        if pdfplumber is None:
            return "ERROR: pdfplumber not installed."
        try:
            text = ""
            with pdfplumber.open(io.BytesIO(raw)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text.strip() if text.strip() else "Could not extract text from PDF."
        except Exception as e:
            return f"PDF read error: {e}"

    elif name.endswith(".docx"):
        if Document is None:
            return "ERROR: python-docx not installed."
        try:
            doc  = Document(io.BytesIO(raw))
            text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
            return text.strip() if text.strip() else "Could not extract text from DOCX."
        except Exception as e:
            return f"DOCX read error: {e}"

    elif name.endswith(".txt"):
        try:
            return raw.decode("utf-8").strip()
        except Exception:
            return raw.decode("latin-1").strip()

    else:
        return f"Unsupported file type: {name}. Please upload PDF, DOCX, or TXT."


# ── Keyword-based scoring engine ───────────────────────────────
def parse_requirements(jd_text: str) -> list:
    """Extract individual requirements from the job description."""
    requirements = []
    for line in jd_text.strip().split('\n'):
        line = line.strip()
        # Remove bullet characters and dashes
        line = re.sub(r'^[-•*·]\s*', '', line).strip()
        if len(line) > 5:
            requirements.append(line)
    return requirements


def extract_keywords(requirement: str) -> list:
    """Extract searchable keywords from a single requirement."""
    # Remove common filler words
    stopwords = {
        'a', 'an', 'the', 'and', 'or', 'of', 'in', 'with',
        'for', 'to', 'is', 'be', 'are', 'at', 'on', 'as',
        'preferred', 'required', 'experience', 'knowledge',
        'ability', 'skills', 'minimum', 'least', 'good', 'strong'
    }
    words = re.findall(r'[a-zA-Z0-9+#./-]+', requirement.lower())
    keywords = [w for w in words if w not in stopwords and len(w) > 2]
    return keywords


def score_cv(cv_text: str, requirements: list) -> dict:
    """
    Score a CV against a list of requirements using keyword matching.
    Returns score (0-100), matched list, partial list, missing list.
    """
    cv_lower = cv_text.lower()
    matched  = []
    partial  = []
    missing  = []

    for req in requirements:
        keywords = extract_keywords(req)
        if not keywords:
            continue

        # Count how many keywords from this requirement appear in the CV
        hits = sum(1 for kw in keywords if kw in cv_lower)
        ratio = hits / len(keywords) if keywords else 0

        if ratio >= 0.6:
            matched.append(req[:60] + ('...' if len(req) > 60 else ''))
        elif ratio >= 0.25:
            partial.append(req[:60] + ('...' if len(req) > 60 else ''))
        else:
            missing.append(req[:60] + ('...' if len(req) > 60 else ''))

    total = len(requirements)
    if total == 0:
        return {"score": 0, "matched": [], "partial": [], "missing": []}

    # Score = full matches + half credit for partial
    raw_score = (len(matched) + 0.5 * len(partial)) / total * 100
    score = round(min(raw_score, 100))

    if score >= 70:
        verdict = "Strong match"
    elif score >= 40:
        verdict = "Partial match"
    else:
        verdict = "Weak match"

    return {
        "score":   score,
        "verdict": verdict,
        "matched": matched,
        "partial": partial,
        "missing": missing,
    }


# ── Main UI ────────────────────────────────────────────────────
def show_cv_evaluator(api_key: str = None):

    st.subheader("AI-Powered CV Evaluator & Shortlist")
    st.caption(
        "Upload candidate CVs and enter job requirements. "
        "The system will score and rank each candidate automatically."
    )

    

    st.markdown("---")

    # ── Step 1: Job requirements ───────────────────────────────
    st.markdown("#### Step 1 — Enter job requirements")
    st.caption("Write each requirement on a new line starting with a dash ( - )")

    

    jd = st.text_area(
        "Job description / requirements",
        value="",
        height=180,
        placeholder=(
            "- B.Tech Mechanical or Electrical Engineering\n"
            "- 3+ years in steel plant or manufacturing\n"
            "- SAP PM module experience\n"
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
                placeholder="e.g. Rahul Sharma"
            )

        with col2:
            uploaded_file = st.file_uploader(
                "Upload CV (PDF / DOCX / TXT)",
                type=["pdf", "docx", "txt"],
                key=f"cand_file_{i}"
            )

        if name.strip() and uploaded_file is not None:
            with st.spinner(f"Reading {uploaded_file.name}..."):
                cv_text = extract_text_from_file(uploaded_file)

            if cv_text.startswith("ERROR") or cv_text.startswith("Unsupported"):
                st.error(cv_text)
            else:
                st.success(f"✅ CV read — {len(cv_text)} characters extracted")
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
            st.stop()

        requirements = parse_requirements(jd)
        if len(requirements) == 0:
            st.error("Could not read any requirements. Make sure each is on its own line.")
            st.stop()

        if len(candidates) == 0:
            st.error("Please enter at least one candidate name and upload their CV.")
            st.stop()

        if len(candidates) < int(num):
            st.warning(
                f"Only {len(candidates)} of {int(num)} candidates ready. "
                "Evaluating those with both name and CV uploaded."
            )

        # Score all candidates
        results = []
        for c in candidates:
            scored = score_cv(c["cv"], requirements)
            scored["name"] = c["name"]
            # Auto-generate summary
            scored["summary"] = (
                f"Meets {len(scored['matched'])} of {len(requirements)} requirements "
                f"with {len(scored['partial'])} partial matches."
            )
            results.append(scored)

        # Sort by score descending
        results = sorted(results, key=lambda x: x["score"], reverse=True)
        st.session_state["last_results"] = results

    # ── Show results ───────────────────────────────────────────
    if st.session_state.get("last_results"):
        display_results(st.session_state["last_results"])


# ── Results display ────────────────────────────────────────────
def display_results(results: list):
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
            c1, c2 = st.columns([0.08, 0.92])

            with c1:
                st.markdown(f"### {icon}")

            with c2:
                st.markdown(f"**#{i+1} — {name}**")
                st.caption(summary)

                p1, p2 = st.columns([4, 1])
                with p1:
                    st.progress(score / 100)
                with p2:
                    st.markdown(f"**{score}%**")
                    st.caption(verdict)

                if matched:
                    st.markdown("✅ **Meets:** " + " · ".join(matched))
                if partial_reqs:
                    st.markdown("🔶 **Partial:** " + " · ".join(partial_reqs))
                if missing:
                    st.markdown("❌ **Missing:** " + " · ".join(missing))

    # ── Download shortlist ─────────────────────────────────────
    st.markdown("---")
    lines = ["TATA STEEL — CV EVALUATION SHORTLIST\n",
             "Scored using keyword-based matching engine\n",
             "=" * 50 + "\n"]

    for i, r in enumerate(results):
        lines.append(
            f"#{i+1}  {r.get('name','')}  —  {r.get('score',0)}%  —  {r.get('verdict','')}\n"
            f"Summary: {r.get('summary','')}\n"
            f"Meets:   {', '.join(r.get('matched',[]))}\n"
            f"Partial: {', '.join(r.get('partial',[]))}\n"
            f"Missing: {', '.join(r.get('missing',[]))}\n"
            + "-" * 40 + "\n"
        )

    st.download_button(
        label="⬇️ Download shortlist as TXT",
        data="\n".join(lines),
        file_name="tata_steel_shortlist.txt",
        mime="text/plain",
        use_container_width=True
    )
