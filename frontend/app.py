import html
import re

import requests
import streamlit as st

API_ANALYZE = "http://127.0.0.1:8000/analyze"
API_ASK = "http://127.0.0.1:8000/ask"

st.set_page_config(page_title="T&C Analyzer", page_icon="📄", layout="wide")

st.markdown(
    """
    <style>
    .block-container {
        max-width: 1100px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }
    .hero-card, .panel-card, .metric-card, .citation-card, .clause-card {
        border: 1px solid rgba(120, 140, 170, 0.18);
        background: linear-gradient(180deg, rgba(18,24,38,0.96), rgba(13,18,30,0.96));
        border-radius: 18px;
        padding: 1rem 1.15rem;
        box-shadow: 0 12px 32px rgba(0,0,0,0.18);
    }
    .hero-title {
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.35rem;
    }
    .hero-subtitle {
        color: #a7b4c8;
        margin-bottom: 0;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        margin: 0;
    }
    .metric-label {
        color: #93a3bc;
        font-size: 0.9rem;
        margin-top: 0.2rem;
    }
    .section-label {
        font-size: 1.15rem;
        font-weight: 700;
        margin-bottom: 0.6rem;
    }
    .badge {
        display: inline-block;
        border-radius: 999px;
        padding: 0.22rem 0.55rem;
        font-size: 0.78rem;
        font-weight: 700;
        margin-right: 0.4rem;
        margin-bottom: 0.35rem;
    }
    .badge-high { background: rgba(220, 38, 38, 0.14); color: #fca5a5; border: 1px solid rgba(248,113,113,0.28); }
    .badge-medium { background: rgba(245, 158, 11, 0.14); color: #fcd34d; border: 1px solid rgba(251,191,36,0.28); }
    .badge-low { background: rgba(16, 185, 129, 0.14); color: #86efac; border: 1px solid rgba(52,211,153,0.28); }
    .badge-neutral { background: rgba(96, 165, 250, 0.12); color: #bfdbfe; border: 1px solid rgba(96,165,250,0.25); }
    mark {
        background: rgba(251, 191, 36, 0.18);
        color: #fde68a;
        padding: 0.05rem 0.18rem;
        border-radius: 0.2rem;
    }
    .muted { color: #90a0b8; font-size: 0.88rem; }
    .answer-box {
        border-left: 4px solid #60a5fa;
        padding-left: 0.95rem;
        margin-top: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _risk_badge(level: str):
    mapping = {
        "HIGH": ("High", "badge-high"),
        "MEDIUM": ("Medium", "badge-medium"),
        "LOW": ("Low", "badge-low"),
    }
    label, css = mapping.get(level, (level.title(), "badge-neutral"))
    return f'<span class="badge {css}">{label}</span>'


def _neutral_badge(text: str):
    return f'<span class="badge badge-neutral">{html.escape(text)}</span>'


def _highlight_clause(text: str, terms):
    rendered = html.escape(text)
    for term in sorted(set(terms or []), key=len, reverse=True):
        pattern = re.compile(re.escape(html.escape(term)), re.IGNORECASE)
        rendered = pattern.sub(lambda match: f"<mark>{match.group(0)}</mark>", rendered)
    return rendered


def _dedupe_clauses(clauses, limit=6):
    def normalize_tokens(text: str):
        cleaned = re.sub(r"[^a-z0-9\s]", " ", text.lower())
        return {token for token in cleaned.split() if len(token) > 2}

    def overlap_ratio(left: str, right: str):
        left_tokens = normalize_tokens(left)
        right_tokens = normalize_tokens(right)
        if not left_tokens or not right_tokens:
            return 0.0
        return len(left_tokens & right_tokens) / min(len(left_tokens), len(right_tokens))

    selected = []

    for clause in sorted(clauses, key=lambda item: (item["risk_score"], item["confidence"]), reverse=True):
        if any(
            overlap_ratio(clause["clause"], existing["clause"]) >= 0.82
            and clause["category"] == existing["category"]
            for existing in selected
        ):
            continue
        selected.append(clause)
        if len(selected) >= limit:
            break

    return selected


def _display_category(category: str):
    mapping = {
        "fees": "Fees & Charges",
        "payment": "Payment Terms",
        "privacy": "Privacy",
        "termination": "Termination",
        "liability": "Liability",
        "penalty": "Penalty",
        "refund": "Refunds",
        "renewal": "Renewal",
        "dispute": "Disputes",
        "general": "General",
        "other": "Other",
    }
    return mapping.get(category, category.replace("_", " ").title())


st.markdown(
    """
    <div class="hero-card">
        <div class="hero-title">AI Terms &amp; Conditions Analyzer</div>
        <p class="hero-subtitle">
            Upload a PDF, surface the riskiest clauses, and chat with cited evidence instead of reading the full document blindly.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# -------------------------------
# SESSION STATE (important)
# -------------------------------
if "document_loaded" not in st.session_state:
    st.session_state.document_loaded = False

if "document_id" not in st.session_state:
    st.session_state.document_id = None

if "analysis_payload" not in st.session_state:
    st.session_state.analysis_payload = None

if "reading_mode" not in st.session_state:
    st.session_state.reading_mode = "Simple"


# -------------------------------
# FILE UPLOAD
# -------------------------------
uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])

if uploaded_file is not None:

    st.info("Uploading and analyzing document...")

    files = {
        "file": (uploaded_file.name, uploaded_file, "application/pdf")
    }

    try:
        response = requests.post(API_ANALYZE, files=files)

        if response.status_code == 200:
            payload = response.json()
            result = payload["formatted_output"]

            st.success("Analysis Complete ✅")

            # ✅ mark as ready for Q&A
            st.session_state.document_loaded = True
            st.session_state.document_id = payload["document_id"]
            st.session_state.analysis_payload = payload

        else:
            st.error(f"API Error: {response.status_code}")

    except Exception as e:
        st.error(f"Connection Error: {e}")


if st.session_state.analysis_payload:
    payload = st.session_state.analysis_payload
    top_clauses = _dedupe_clauses(payload["clauses"], limit=6)

    mode_col, _ = st.columns([0.45, 0.55])
    with mode_col:
        st.session_state.reading_mode = st.radio(
            "Reading mode",
            ["Standard", "Simple"],
            horizontal=True,
        )

    if st.session_state.reading_mode == "Standard":
        summary_text = payload["formatted_output"]
        clause_explanation_key = "reason"
    else:
        summary_text = payload["simple_summary"]
        clause_explanation_key = "simple_explanation"

    metric_cols = st.columns(4)
    metrics = [
        ("High Risk", payload["risk_overview"]["high"]),
        ("Medium Risk", payload["risk_overview"]["medium"]),
        ("Low Risk", payload["risk_overview"]["low"]),
        ("Clauses Reviewed", len(payload["clauses"])),
    ]
    for col, (label, value) in zip(metric_cols, metrics):
        with col:
            st.markdown(
                f"""
                <div class="metric-card">
                    <p class="metric-value">{value}</p>
                    <div class="metric-label">{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    left_col, right_col = st.columns([1.15, 0.85], gap="large")

    with left_col:
        st.markdown('<div class="section-label">Executive Summary</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="panel-card"><pre style="white-space:pre-wrap;font-family:inherit;margin:0;">{html.escape(summary_text)}</pre></div>',
            unsafe_allow_html=True,
        )

    with right_col:
        st.markdown('<div class="section-label">Top Risk Signals</div>', unsafe_allow_html=True)
        for clause in top_clauses[:3]:
            badges = (
                _risk_badge(clause["risk"])
                + _neutral_badge(f"Score {clause['risk_score']}/10")
                + _neutral_badge(_display_category(clause["category"]))
            )
            st.markdown(
                f"""
                <div class="panel-card" style="margin-bottom:0.8rem;">
                    {badges}
                    <div style="margin-top:0.45rem;font-weight:600;">{html.escape(clause[clause_explanation_key])}</div>
                    <div class="muted" style="margin-top:0.45rem;">Page {clause['page_number']} | Confidence {clause['confidence']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown('<div class="section-label" style="margin-top:1.2rem;">Clause Risk Review</div>', unsafe_allow_html=True)
    for clause in top_clauses:
        badges = (
            _risk_badge(clause["risk"])
            + _neutral_badge(f"Score {clause['risk_score']}/10")
            + _neutral_badge(f"Confidence {clause['confidence']}")
            + _neutral_badge(_display_category(clause["category"]))
        )
        highlighted = _highlight_clause(clause["clause"][:420], clause.get("highlighted_terms", []))
        terms = ", ".join(clause.get("highlighted_terms", [])[:5]) or "No explicit trigger terms"
        st.markdown(
            f"""
            <div class="clause-card" style="margin-bottom:0.85rem;">
                {badges}
                <div class="muted" style="margin-top:0.4rem;">Page {clause['page_number']} | Category confidence {clause['category_confidence']}</div>
                <div style="margin-top:0.85rem; line-height:1.65;">{highlighted}</div>
                <div class="muted" style="margin-top:0.8rem;">Why flagged: {html.escape(clause[clause_explanation_key])}</div>
                <div class="muted" style="margin-top:0.25rem;">Highlighted phrases: {html.escape(terms)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# -------------------------------
# Q&A SECTION
# -------------------------------
st.markdown('<div class="section-label" style="margin-top:1.4rem;">Chat With Document</div>', unsafe_allow_html=True)

if not st.session_state.document_loaded:
    st.warning("⚠️ Please upload and analyze a document first.")
else:
    question = st.text_input("Ask something about the document")

    if st.button("Ask"):
        if not question.strip():
            st.warning("Please enter a question")
        else:
            with st.spinner("Thinking... 🤖"):
                try:
                    response = requests.post(
                        API_ASK,
                        json={
                            "question": question,
                            "document_id": st.session_state.document_id,
                        }
                    )

                    result = response.json()

                    if "detail" in result:
                        st.error(result["detail"])
                    else:
                        status_label = "Grounded" if result["grounded"] else "Low support"
                        st.markdown(
                            f"""
                            <div class="panel-card answer-box">
                                <div class="section-label" style="margin-bottom:0.35rem;">Answer</div>
                                <div style="line-height:1.7;">{html.escape(result["answer"])}</div>
                                <div class="muted" style="margin-top:0.75rem;">{status_label} | Confidence {result['confidence']:.2f}</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        st.markdown('<div class="section-label" style="margin-top:0.9rem;">Citations</div>', unsafe_allow_html=True)

                        for ev in result["citations"]:
                            st.markdown(
                                f"""
                                <div class="citation-card" style="margin-bottom:0.75rem;">
                                    {_neutral_badge(f"Page {ev['page_number']}")}
                                    {_neutral_badge(f"Chunk {ev['chunk_id'] + 1}")}
                                    {_neutral_badge(f"Relevance {ev['relevance_score']:.2f}")}
                                    <div style="margin-top:0.7rem; line-height:1.65;">{html.escape(ev['text'][:320])}</div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                except Exception as e:
                    st.error(f"Connection Error: {e}")
