import html
import re

import requests
import streamlit as st

API_ANALYZE = "http://127.0.0.1:8000/analyze"
API_ANALYZE_URL = "http://127.0.0.1:8000/analyze-url"
API_ANALYZE_IMAGES = "http://127.0.0.1:8000/analyze-images"
API_ASK = "http://127.0.0.1:8000/ask"

st.set_page_config(page_title="T&C Analyzer", page_icon="📄", layout="wide")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');

    .stApp {
        background:
            radial-gradient(circle at 10% 0%, rgba(34, 197, 94, 0.08), transparent 20%),
            radial-gradient(circle at 90% 0%, rgba(14, 165, 233, 0.10), transparent 24%),
            radial-gradient(circle at 50% 100%, rgba(251, 191, 36, 0.06), transparent 24%),
            linear-gradient(180deg, #06101d 0%, #0a1322 48%, #0c1628 100%);
        color: #edf3fb;
        font-family: 'Manrope', sans-serif;
    }
    .block-container {
        max-width: 1120px;
        padding-top: 1.4rem;
        padding-bottom: 3rem;
    }
    h1, h2, h3, h4, p, div, span, label {
        font-family: 'Manrope', sans-serif !important;
    }
    .hero-card {
        border: 1px solid rgba(125, 149, 181, 0.18);
        background:
            radial-gradient(circle at top right, rgba(14, 165, 233, 0.14), transparent 28%),
            radial-gradient(circle at bottom left, rgba(34, 197, 94, 0.10), transparent 22%),
            linear-gradient(180deg, rgba(14,21,36,0.98), rgba(10,16,29,0.98));
        border-radius: 30px;
        padding: 1.7rem 1.7rem 1.5rem;
        box-shadow: 0 24px 64px rgba(0,0,0,0.28);
        margin-bottom: 1.25rem;
    }
    .panel-card, .metric-card, .citation-card, .clause-card, .upload-card {
        border: 1px solid rgba(120, 140, 170, 0.14);
        background: linear-gradient(180deg, rgba(18,24,38,0.92), rgba(11,17,29,0.96));
        border-radius: 20px;
        padding: 1rem 1.15rem;
        box-shadow: 0 12px 32px rgba(0,0,0,0.18);
    }
    .summary-card {
        border: 1px solid rgba(120, 140, 170, 0.14);
        background:
            linear-gradient(180deg, rgba(20,27,42,0.95), rgba(11,17,29,0.96));
        border-radius: 24px;
        padding: 1.2rem 1.2rem 1.15rem;
        box-shadow: 0 18px 40px rgba(0,0,0,0.20);
    }
    .input-stage {
        border: 1px solid rgba(120, 140, 170, 0.15);
        background:
            linear-gradient(180deg, rgba(15,22,36,0.96), rgba(10,17,30,0.96));
        border-radius: 26px;
        padding: 1.25rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 18px 40px rgba(0,0,0,0.22);
    }
    .hero-title {
        font-size: 2.7rem;
        font-weight: 800;
        margin-bottom: 0.45rem;
        letter-spacing: -0.03em;
        max-width: 700px;
        line-height: 1.05;
    }
    .hero-subtitle {
        color: #b6c6da;
        margin: 0 0 1rem;
        max-width: 680px;
        line-height: 1.65;
        font-size: 1.02rem;
    }
    .hero-kicker {
        display: inline-block;
        border-radius: 999px;
        padding: 0.28rem 0.7rem;
        font-size: 0.78rem;
        font-weight: 700;
        color: #bfe7ff;
        background: rgba(14,165,233,0.12);
        border: 1px solid rgba(56,189,248,0.22);
        margin-bottom: 0.85rem;
    }
    .hero-support {
        display: inline-flex;
        gap: 0.55rem;
        flex-wrap: wrap;
        justify-content: center;
        margin-top: 0.2rem;
    }
    .hero-pill {
        border-radius: 999px;
        padding: 0.32rem 0.72rem;
        font-size: 0.8rem;
        color: #c8d9ee;
        background: rgba(148,163,184,0.08);
        border: 1px solid rgba(148,163,184,0.14);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        margin: 0;
    }
    .metric-label {
        color: #9fb1c8;
        font-size: 0.86rem;
        margin-top: 0.2rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }
    .section-label {
        font-size: 1.2rem;
        font-weight: 800;
        margin-bottom: 0.45rem;
        letter-spacing: -0.02em;
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
        border: 1px solid rgba(96, 165, 250, 0.24);
        background:
            radial-gradient(circle at top right, rgba(96, 165, 250, 0.10), transparent 26%),
            linear-gradient(180deg, rgba(16,23,38,0.98), rgba(10,16,28,0.98));
        padding: 1rem 1.1rem;
        margin-top: 0.35rem;
        border-radius: 22px;
    }
    .section-intro {
        color: #96a9c3;
        font-size: 0.92rem;
        margin-top: -0.02rem;
        margin-bottom: 0.8rem;
        line-height: 1.55;
    }
    .input-mode-note {
        color: #9ab0c8;
        font-size: 0.88rem;
        margin-top: 0.2rem;
    }
    .mini-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.9rem;
        margin-top: 0.85rem;
        margin-bottom: 0.4rem;
    }
    .mini-card {
        border-radius: 20px;
        padding: 0.9rem;
        background: rgba(148,163,184,0.04);
        border: 1px solid rgba(148,163,184,0.08);
    }
    .mini-title {
        font-weight: 700;
        margin-bottom: 0.3rem;
        color: #e8eef8;
    }
    .mini-copy {
        color: #9cb0c8;
        font-size: 0.88rem;
        line-height: 1.5;
    }
    .hero-layout {
        display: grid;
        grid-template-columns: 1.15fr 0.85fr;
        gap: 1.2rem;
        align-items: stretch;
    }
    .hero-side {
        border-radius: 24px;
        border: 1px solid rgba(148,163,184,0.10);
        background: rgba(148,163,184,0.04);
        padding: 1rem;
    }
    .hero-side-title {
        font-size: 0.85rem;
        color: #9fb1c8;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.7rem;
    }
    .hero-side-item {
        display: flex;
        justify-content: space-between;
        padding: 0.62rem 0;
        border-bottom: 1px solid rgba(148,163,184,0.08);
        color: #d7e4f4;
        font-size: 0.95rem;
    }
    .hero-side-item:last-child {
        border-bottom: none;
    }
    .hero-side-soft {
        color: #8fa4bf;
    }
    .risk-spotlight {
        border-radius: 22px;
        padding: 1rem;
        margin-bottom: 0.85rem;
        border: 1px solid rgba(148,163,184,0.10);
        background: linear-gradient(180deg, rgba(17,24,39,0.94), rgba(11,17,29,0.98));
    }
    .risk-spotlight.high {
        box-shadow: inset 0 0 0 1px rgba(248,113,113,0.18);
    }
    .risk-spotlight.medium {
        box-shadow: inset 0 0 0 1px rgba(251,191,36,0.14);
    }
    .summary-shell {
        display: grid;
        grid-template-columns: 1.08fr 0.92fr;
        gap: 1rem;
    }
    .chat-shell {
        border: 1px solid rgba(120, 140, 170, 0.12);
        background: linear-gradient(180deg, rgba(15,22,36,0.94), rgba(11,17,29,0.96));
        border-radius: 24px;
        padding: 1rem 1.1rem;
    }
    @media (max-width: 900px) {
        .hero-layout, .summary-shell, .mini-grid {
            grid-template-columns: 1fr;
        }
        .hero-title {
            font-size: 2.2rem;
        }
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


def _apply_analysis_payload(payload):
    st.session_state.document_loaded = True
    st.session_state.document_id = payload["document_id"]
    st.session_state.analysis_payload = payload


st.markdown(
    """
    <div class="hero-card">
        <div class="hero-layout">
            <div>
                <div class="hero-kicker">Source-grounded document intelligence</div>
                <div class="hero-title">Understand terms and conditions before you agree to them.</div>
                <p class="hero-subtitle">
                    Analyze PDFs, links, or photos of printed documents. Surface the real risks first, then ask follow-up questions with cited evidence.
                </p>
                <div class="hero-support">
                    <span class="hero-pill">PDFs</span>
                    <span class="hero-pill">Links</span>
                    <span class="hero-pill">Printed documents</span>
                    <span class="hero-pill">Risk scoring</span>
                    <span class="hero-pill">Cited answers</span>
                </div>
            </div>
            <div class="hero-side">
                <div class="hero-side-title">What users care about</div>
                <div class="hero-side-item"><span>Can this cost me more later?</span><span class="hero-side-soft">Fees, EMI, penalties</span></div>
                <div class="hero-side-item"><span>Can the company change terms quietly?</span><span class="hero-side-soft">Rate changes, notice</span></div>
                <div class="hero-side-item"><span>Can I ask questions in plain English?</span><span class="hero-side-soft">Grounded chat</span></div>
                <div class="hero-side-item"><span>Can I use printed documents too?</span><span class="hero-side-soft">Photo input</span></div>
            </div>
        </div>
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

# -------------------------------
# FILE UPLOAD
# -------------------------------
st.markdown(
    """
    <div class="input-stage">
        <div class="section-label">Analyze A Document</div>
        <div class="section-intro">Choose the input type that matches what the user actually has. All three options use the same analysis engine and risk scoring.</div>
        <div class="mini-grid">
            <div class="mini-card">
                <div class="mini-title">1. Add the document</div>
                <div class="mini-copy">Upload a PDF, paste a link, or add photos of a printed page.</div>
            </div>
            <div class="mini-card">
                <div class="mini-title">2. Review the risks</div>
                <div class="mini-copy">See the main red flags first, without digging through the full document.</div>
            </div>
            <div class="mini-card">
                <div class="mini-title">3. Ask follow-up questions</div>
                <div class="mini-copy">Use chat to ask direct questions and get evidence-backed answers.</div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

input_tab_pdf, input_tab_link, input_tab_images = st.tabs(["Upload PDF", "Paste Link", "Upload Photos"])

with input_tab_pdf:
    uploaded_file = st.file_uploader("Upload PDF", type=["pdf"], label_visibility="collapsed")
    st.markdown('<div class="input-mode-note">Best for downloaded contracts, policy PDFs, bank documents, and official forms.</div>', unsafe_allow_html=True)

    if uploaded_file is not None:
        st.info("Uploading and analyzing document...")

        files = {
            "file": (uploaded_file.name, uploaded_file, "application/pdf")
        }

        try:
            response = requests.post(API_ANALYZE, files=files)

            if response.status_code == 200:
                payload = response.json()
                st.success("Analysis Complete ✅")
                _apply_analysis_payload(payload)
            else:
                detail = response.json().get("detail", f"API Error: {response.status_code}")
                st.error(detail)

        except Exception as e:
            st.error(f"Connection Error: {e}")

with input_tab_link:
    st.markdown('<div class="input-mode-note">Paste a direct PDF link or a normal webpage link. The app validates the link before analyzing it.</div>', unsafe_allow_html=True)
    doc_url = st.text_input("Paste document link", placeholder="https://example.com/terms.pdf")

    if st.button("Analyze link"):
        if not doc_url.strip():
            st.warning("Please paste a valid link.")
        else:
            with st.spinner("Checking link and analyzing document..."):
                try:
                    response = requests.post(API_ANALYZE_URL, json={"url": doc_url.strip()})
                    if response.status_code == 200:
                        payload = response.json()
                        st.success("Link analysis complete ✅")
                        _apply_analysis_payload(payload)
                    else:
                        detail = response.json().get("detail", f"API Error: {response.status_code}")
                        st.error(detail)
                except Exception as e:
                    st.error(f"Connection Error: {e}")

with input_tab_images:
    st.markdown('<div class="input-mode-note">Upload one or more photos of a printed document. The app extracts text from the images first, then runs the same analyzer.</div>', unsafe_allow_html=True)
    document_images = st.file_uploader(
        "Upload document photos",
        type=["png", "jpg", "jpeg", "webp"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if st.button("Analyze photos"):
        if not document_images:
            st.warning("Please upload at least one document photo.")
        else:
            with st.spinner("Reading document photos and analyzing text..."):
                try:
                    files = [
                        ("files", (image.name, image, image.type or "image/jpeg"))
                        for image in document_images
                    ]
                    response = requests.post(API_ANALYZE_IMAGES, files=files)
                    if response.status_code == 200:
                        payload = response.json()
                        st.success("Photo analysis complete ✅")
                        _apply_analysis_payload(payload)
                    else:
                        detail = response.json().get("detail", f"API Error: {response.status_code}")
                        st.error(detail)
                except Exception as e:
                    st.error(f"Connection Error: {e}")


if st.session_state.analysis_payload:
    payload = st.session_state.analysis_payload
    top_clauses = _dedupe_clauses(payload["clauses"], limit=6)
    summary_text = payload["formatted_output"]
    clause_explanation_key = "reason"

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
        st.markdown('<div class="section-intro">The fast read: what this document is about and where the main risks sit.</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="summary-card"><pre style="white-space:pre-wrap;font-family:inherit;margin:0;line-height:1.7;">{html.escape(summary_text)}</pre></div>',
            unsafe_allow_html=True,
        )

    with right_col:
        st.markdown('<div class="section-label">Top Risk Signals</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-intro">The three clauses most likely to affect the user.</div>', unsafe_allow_html=True)
        for clause in top_clauses[:3]:
            badges = (
                _risk_badge(clause["risk"])
                + _neutral_badge(f"Score {clause['risk_score']}/10")
                + _neutral_badge(_display_category(clause["category"]))
            )
            st.markdown(
                f"""
                <div class="risk-spotlight {'high' if clause['risk']=='HIGH' else 'medium'}">
                    {badges}
                    <div style="margin-top:0.45rem;font-weight:600;">{html.escape(clause[clause_explanation_key])}</div>
                    <div class="muted" style="margin-top:0.45rem;">Page {clause['page_number']} | Confidence {clause['confidence']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with st.expander(f"See detailed clause risk review ({len(top_clauses)} clauses)", expanded=False):
        st.markdown('<div class="section-intro">Open this only when you want to inspect individual clauses in more detail.</div>', unsafe_allow_html=True)
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
st.markdown('<div class="section-intro">Ask direct questions in your own words. The app answers with retrieved document evidence so the user can verify the result.</div>', unsafe_allow_html=True)
st.markdown('<div class="chat-shell">', unsafe_allow_html=True)

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

st.markdown('</div>', unsafe_allow_html=True)
