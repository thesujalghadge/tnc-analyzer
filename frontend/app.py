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
            radial-gradient(circle at 10% 0%, rgba(13, 148, 136, 0.12), transparent 22%),
            radial-gradient(circle at 90% 12%, rgba(251, 146, 60, 0.10), transparent 18%),
            linear-gradient(180deg, #f8f3ea 0%, #f4efe6 40%, #efe8db 100%);
        color: #162033;
        font-family: 'Manrope', sans-serif;
    }
    .block-container {
        max-width: 100%;
        padding-top: 0.45rem;
        padding-bottom: 4.2rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    header[data-testid="stHeader"] {
        background: transparent;
    }
    [data-testid="stToolbar"] {
        right: 1.2rem;
        top: 1rem;
    }
    [data-testid="stTabs"] button {
        border-radius: 999px !important;
        border: 1px solid rgba(148,163,184,0.14) !important;
        background: rgba(255,251,247,0.78) !important;
        color: #314155 !important;
        padding: 0.8rem 1.15rem !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        box-shadow: 0 8px 18px rgba(15, 23, 42, 0.04);
    }
    [data-testid="stTabs"] button[aria-selected="true"] {
        background: linear-gradient(135deg, rgba(11, 31, 58, 0.96), rgba(26, 48, 83, 0.98)) !important;
        border-color: rgba(11,31,58,0.10) !important;
        color: #f8f3ea !important;
        box-shadow: 0 16px 30px rgba(11, 31, 58, 0.18);
    }
    .stButton > button {
        border-radius: 16px !important;
        border: 1px solid rgba(11,31,58,0.14) !important;
        background: linear-gradient(135deg, #0f2747, #1a3a66) !important;
        color: #f9f4eb !important;
        font-weight: 700 !important;
        padding: 0.8rem 1.25rem !important;
        box-shadow: 0 14px 28px rgba(15, 23, 42, 0.14);
    }
    .stButton > button:hover {
        border-color: rgba(11,31,58,0.24) !important;
        transform: translateY(-2px);
    }
    .stTextInput input {
        border-radius: 16px !important;
        background: rgba(255,252,248,0.95) !important;
        color: #122132 !important;
        border: 1px solid rgba(148,163,184,0.14) !important;
        min-height: 3rem;
    }
    h1, h2, h3, h4, p, div, span, label {
        font-family: 'Manrope', sans-serif !important;
    }
    .hero-card {
        border: 1px solid rgba(255, 255, 255, 0.08);
        background:
            radial-gradient(circle at top right, rgba(45, 212, 191, 0.14), transparent 22%),
            radial-gradient(circle at bottom left, rgba(251, 146, 60, 0.14), transparent 20%),
            linear-gradient(135deg, #081223 0%, #11243f 48%, #183458 100%);
        border-radius: 34px;
        padding: 2.8rem 2.8rem 2.5rem;
        box-shadow: 0 28px 60px rgba(9, 18, 35, 0.22);
        margin-bottom: 1.9rem;
        overflow: hidden;
    }
    .panel-card, .metric-card, .citation-card, .clause-card, .upload-card {
        border: 1px solid rgba(148, 163, 184, 0.11);
        background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(251,248,242,0.98));
        border-radius: 26px;
        padding: 1.25rem 1.3rem;
        box-shadow: 0 14px 30px rgba(15,23,42,0.06);
    }
    .overview-hero {
        border: 1px solid rgba(11, 31, 58, 0.10);
        background:
            radial-gradient(circle at top right, rgba(13,148,136,0.10), transparent 22%),
            radial-gradient(circle at bottom left, rgba(251,146,60,0.10), transparent 18%),
            linear-gradient(135deg, rgba(255,255,255,0.98), rgba(249,245,239,0.98));
        border-radius: 30px;
        padding: 1.7rem 1.8rem;
        box-shadow: 0 18px 34px rgba(15,23,42,0.06);
    }
    .overview-kicker {
        display: inline-block;
        border-radius: 999px;
        padding: 0.32rem 0.7rem;
        font-size: 0.78rem;
        font-weight: 800;
        background: rgba(11,31,58,0.08);
        color: #173250;
        margin-bottom: 0.8rem;
    }
    .overview-title {
        font-size: 2rem;
        line-height: 1.02;
        letter-spacing: -0.03em;
        font-weight: 800;
        color: #102032;
        margin-bottom: 0.55rem;
        max-width: 720px;
    }
    .overview-copy {
        color: #5d6f84;
        line-height: 1.75;
        font-size: 1rem;
        max-width: 840px;
    }
    .summary-point {
        border-top: 1px solid rgba(148,163,184,0.10);
        padding-top: 0.95rem;
        margin-top: 0.95rem;
    }
    .summary-point:first-child {
        border-top: none;
        padding-top: 0;
        margin-top: 0.15rem;
    }
    .summary-point-title {
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #7a8a9f;
        margin-bottom: 0.45rem;
        font-weight: 800;
    }
    .summary-point-copy {
        color: #17283d;
        line-height: 1.8;
        font-size: 1rem;
    }
    .insight-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 1.1rem;
        margin-top: 1.2rem;
    }
    .insight-card {
        border: 1px solid rgba(148,163,184,0.10);
        border-radius: 24px;
        padding: 1.15rem 1.15rem 1rem;
        background: linear-gradient(180deg, rgba(255,255,255,0.92), rgba(249,245,239,0.98));
        box-shadow: 0 10px 22px rgba(15,23,42,0.04);
    }
    .insight-card-title {
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #7a8a9f;
        margin-bottom: 0.4rem;
        font-weight: 800;
    }
    .insight-card-copy {
        color: #18283a;
        line-height: 1.7;
        font-weight: 600;
        margin-bottom: 0.7rem;
    }
    .insight-card-note {
        color: #617287;
        line-height: 1.65;
        font-size: 0.92rem;
    }
    .summary-card {
        border: 1px solid rgba(148, 163, 184, 0.10);
        background:
            linear-gradient(180deg, rgba(255,255,255,0.98), rgba(250,247,241,0.98));
        border-radius: 28px;
        padding: 1.6rem;
        box-shadow: 0 16px 34px rgba(15,23,42,0.05);
    }
    .input-stage {
        border: 1px solid rgba(148, 163, 184, 0.10);
        background:
            radial-gradient(circle at top right, rgba(13,148,136,0.06), transparent 26%),
            linear-gradient(180deg, rgba(255,255,255,0.96), rgba(248,244,237,0.98));
        border-radius: 32px;
        padding: 1.85rem;
        margin-bottom: 1.6rem;
        box-shadow: 0 16px 36px rgba(15,23,42,0.06);
    }
    .hero-title {
        font-size: 4.1rem;
        font-weight: 800;
        margin-bottom: 0.8rem;
        letter-spacing: -0.03em;
        max-width: 760px;
        line-height: 0.96;
        color: #f7f2e9;
    }
    .hero-subtitle {
        color: rgba(236, 242, 250, 0.76);
        margin: 0 0 1.5rem;
        max-width: 660px;
        line-height: 1.75;
        font-size: 1.08rem;
    }
    .hero-kicker {
        display: inline-block;
        border-radius: 999px;
        padding: 0.4rem 0.82rem;
        font-size: 0.78rem;
        font-weight: 700;
        color: #d9fff7;
        background: rgba(255,255,255,0.08);
        border: 1px solid rgba(255,255,255,0.12);
        margin-bottom: 1rem;
    }
    .hero-support {
        display: inline-flex;
        gap: 0.6rem;
        flex-wrap: wrap;
        justify-content: flex-start;
        margin-top: 0.3rem;
    }
    .hero-pill {
        border-radius: 999px;
        padding: 0.42rem 0.9rem;
        font-size: 0.79rem;
        color: rgba(244,248,252,0.88);
        background: rgba(255,255,255,0.08);
        border: 1px solid rgba(255,255,255,0.10);
    }
    .metric-value {
        font-size: 2.45rem;
        font-weight: 700;
        margin: 0;
        color: #132235;
    }
    .metric-label {
        color: #6a7a8f;
        font-size: 0.86rem;
        margin-top: 0.2rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }
    .section-label {
        font-size: 1.4rem;
        font-weight: 800;
        margin-bottom: 0.45rem;
        letter-spacing: -0.02em;
        color: #132235;
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
    .badge-high { background: rgba(220, 38, 38, 0.10); color: #991b1b; border: 1px solid rgba(220,38,38,0.14); }
    .badge-medium { background: rgba(245, 158, 11, 0.12); color: #9a5c00; border: 1px solid rgba(245,158,11,0.16); }
    .badge-low { background: rgba(15, 118, 110, 0.10); color: #0f766e; border: 1px solid rgba(15,118,110,0.14); }
    .badge-neutral { background: rgba(59, 130, 246, 0.08); color: #1d4ed8; border: 1px solid rgba(59,130,246,0.12); }
    mark {
        background: rgba(245, 158, 11, 0.16);
        color: #92400e;
        padding: 0.05rem 0.18rem;
        border-radius: 0.2rem;
    }
    .muted { color: #6f8095; font-size: 0.88rem; }
    .answer-box {
        border: 1px solid rgba(15, 118, 110, 0.12);
        background:
            radial-gradient(circle at top right, rgba(15, 118, 110, 0.05), transparent 26%),
            linear-gradient(180deg, rgba(255,255,255,0.96), rgba(248,244,237,0.98));
        padding: 1.1rem 1.2rem;
        margin-top: 0.35rem;
        border-radius: 22px;
    }
    .section-intro {
        color: #66788d;
        font-size: 1rem;
        margin-top: -0.02rem;
        margin-bottom: 1rem;
        line-height: 1.7;
    }
    .input-mode-note {
        color: #6e8093;
        font-size: 0.88rem;
        margin-top: 0.2rem;
    }
    .mini-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 1.15rem;
        margin-top: 1.15rem;
        margin-bottom: 0.3rem;
    }
    .mini-card {
        border-radius: 24px;
        padding: 1.2rem;
        background: linear-gradient(180deg, rgba(255,255,255,0.82), rgba(248,243,235,0.92));
        border: 1px solid rgba(148,163,184,0.09);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.45);
    }
    .mini-title {
        font-weight: 700;
        margin-bottom: 0.3rem;
        color: #18283a;
    }
    .mini-copy {
        color: #66788d;
        font-size: 0.88rem;
        line-height: 1.5;
    }
    .hero-layout {
        display: grid;
        grid-template-columns: 1.2fr 0.8fr;
        gap: 2rem;
        align-items: stretch;
    }
    .hero-side {
        border-radius: 28px;
        border: 1px solid rgba(255,255,255,0.08);
        background: linear-gradient(180deg, rgba(255,255,255,0.09), rgba(255,255,255,0.04));
        padding: 1.3rem 1.35rem 1.1rem;
        backdrop-filter: blur(14px);
    }
    .hero-side-title {
        font-size: 0.85rem;
        color: rgba(214, 226, 239, 0.72);
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.9rem;
    }
    .hero-side-item {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        padding: 0.9rem 0;
        border-bottom: 1px solid rgba(255,255,255,0.08);
        color: #f5f7fb;
        font-size: 1rem;
    }
    .hero-side-item:last-child {
        border-bottom: none;
    }
    .hero-side-soft {
        color: rgba(202, 215, 230, 0.68);
    }
    .risk-spotlight {
        border-radius: 24px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        border: 1px solid rgba(148,163,184,0.10);
        background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(248,244,237,0.98));
        box-shadow: 0 16px 30px rgba(15,23,42,0.05);
    }
    .risk-spotlight.high {
        box-shadow: inset 0 0 0 1px rgba(220,38,38,0.10);
    }
    .risk-spotlight.medium {
        box-shadow: inset 0 0 0 1px rgba(245,158,11,0.10);
    }
    .summary-shell {
        display: grid;
        grid-template-columns: 1.08fr 0.92fr;
        gap: 1rem;
    }
    .chat-shell {
        border: 1px solid rgba(148,163,184,0.09);
        background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(249,246,241,0.98));
        border-radius: 30px;
        padding: 1.5rem 1.55rem;
        box-shadow: 0 18px 36px rgba(15,23,42,0.05);
    }
    .detail-toggle-shell {
        border: 1px solid rgba(148,163,184,0.10);
        background: linear-gradient(180deg, rgba(255,255,255,0.88), rgba(248,244,237,0.94));
        border-radius: 22px;
        padding: 1rem 1.1rem;
        margin-top: 1.3rem;
    }
    .nav-shell {
        border: 1px solid rgba(148,163,184,0.10);
        background:
            radial-gradient(circle at top left, rgba(13,148,136,0.05), transparent 20%),
            linear-gradient(180deg, rgba(255,255,255,0.70), rgba(255,255,255,0.50));
        border-radius: 32px;
        padding: 1.35rem 1.5rem 1rem;
        margin-top: 1.6rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 18px 42px rgba(15,23,42,0.06);
    }
    [data-testid="stFileUploader"] {
        border: 1px dashed rgba(14, 38, 67, 0.18) !important;
        border-radius: 24px !important;
        background: linear-gradient(180deg, rgba(255,255,255,0.92), rgba(249,245,239,0.96)) !important;
        padding: 0.85rem !important;
    }
    [data-testid="stFileUploader"] section {
        padding: 1.2rem 1rem !important;
    }
    [data-testid="stFileUploaderDropzone"] {
        background: transparent !important;
        border: none !important;
    }
    .workspace-empty {
        border: 1px dashed rgba(14, 38, 67, 0.14);
        border-radius: 30px;
        padding: 2.4rem 2rem;
        background: linear-gradient(180deg, rgba(255,255,255,0.72), rgba(247,242,234,0.76));
        text-align: center;
        color: #5c6d82;
    }
    .workspace-empty-title {
        font-size: 1.4rem;
        font-weight: 800;
        color: #18283a;
        margin-bottom: 0.45rem;
    }
    @media (max-width: 900px) {
        .hero-layout, .summary-shell, .mini-grid, .insight-grid {
            grid-template-columns: 1fr;
        }
        .hero-title {
            font-size: 2.6rem;
        }
        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
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


def _extract_summary_bullets(formatted_output: str):
    summary_block = formatted_output or ""
    if "RISK OVERVIEW:" in summary_block:
        summary_block = summary_block.split("RISK OVERVIEW:", 1)[0]
    summary_block = summary_block.replace("📄 SUMMARY:", "").strip()
    candidates = re.split(r"(?:\n|(?<=\.)\s+)[\*\u2022\-]?\s*", summary_block)
    bullets = []
    for candidate in candidates:
        cleaned = " ".join(candidate.split()).strip(" -*•")
        if len(cleaned) < 25:
            continue
        if cleaned.lower().startswith("summary"):
            continue
        bullets.append(cleaned)
    deduped = []
    seen = set()
    for bullet in bullets:
        key = bullet.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(bullet)
    return deduped[:5]


def _action_prompt_for_clause(clause: dict):
    category = clause.get("category", "general")
    prompts = {
        "payment": "Check whether your EMI, total cost, or repayment timeline can change later.",
        "fees": "Look for charges that may apply later, especially hidden or conditional fees.",
        "penalty": "See when penalties start and how quickly overdue amounts can grow.",
        "privacy": "Verify who can receive your data and whether notice or consent is required.",
        "termination": "Check who can end the agreement and what happens after termination.",
        "liability": "See who carries the loss if something goes wrong.",
        "refund": "Check when money is refundable and when it is not.",
        "renewal": "See whether the agreement can continue or renew automatically.",
        "dispute": "Check where disputes are handled and whether arbitration is mandatory.",
    }
    return prompts.get(category, "Review this clause carefully before agreeing to the document.")


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
                <div class="hero-title">Read the fine print like someone built to catch it.</div>
                <p class="hero-subtitle">
                    Analyze PDFs, links, or printed pages and surface the clauses that actually matter. Start with the risks, dive deeper only when needed, and ask grounded follow-up questions with cited evidence.
                </p>
                <div class="hero-support">
                    <span class="hero-pill">Risk-first analysis</span>
                    <span class="hero-pill">PDFs and links</span>
                    <span class="hero-pill">Printed document photos</span>
                    <span class="hero-pill">Grounded Q&amp;A</span>
                    <span class="hero-pill">Clause evidence</span>
                </div>
            </div>
            <div class="hero-side">
                <div class="hero-side-title">Why this feels useful fast</div>
                <div class="hero-side-item"><span>See money-related red flags first</span><span class="hero-side-soft">Fees, EMIs, penalties</span></div>
                <div class="hero-side-item"><span>Catch hidden change-rights and notice traps</span><span class="hero-side-soft">Revisions, silent updates</span></div>
                <div class="hero-side-item"><span>Ask direct questions instead of reading everything</span><span class="hero-side-soft">Grounded chat</span></div>
                <div class="hero-side-item"><span>Works even with printed forms and paperwork</span><span class="hero-side-soft">Photo input</span></div>
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
        <div class="section-intro">Choose the format the user already has. The product keeps the experience simple: analyze first, understand the risks, then ask direct questions only if you need clarification.</div>
        <div class="mini-grid">
            <div class="mini-card">
                <div class="mini-title">Choose the source</div>
                <div class="mini-copy">Upload a PDF, paste a link, or use photos from a printed contract or bank form.</div>
            </div>
            <div class="mini-card">
                <div class="mini-title">See the critical risks first</div>
                <div class="mini-copy">Get the main money, notice, fee, and clause risks before the user has to inspect the full document.</div>
            </div>
            <div class="mini-card">
                <div class="mini-title">Go deeper only when needed</div>
                <div class="mini-copy">Use chat and clause-level evidence to verify the tricky parts without information overload.</div>
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
    deep_clauses = _dedupe_clauses(payload["clauses"], limit=12)
    summary_text = payload["formatted_output"]
    summary_bullets = _extract_summary_bullets(summary_text)
    clause_explanation_key = "reason"
    st.markdown('<div class="nav-shell">', unsafe_allow_html=True)
    result_tab_overview, result_tab_deep_dive, result_tab_chat = st.tabs(
        ["Overview", "Deep Dive", "Chat"]
    )

    with result_tab_overview:
        metric_cols = st.columns(4, gap="large")
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

        st.markdown("<div style='height:1.25rem;'></div>", unsafe_allow_html=True)
        lead_clause = top_clauses[0] if top_clauses else None
        lead_text = (
            lead_clause[clause_explanation_key]
            if lead_clause
            else "Upload a document to surface the most important risks first."
        )
        lead_note = (
            _action_prompt_for_clause(lead_clause)
            if lead_clause
            else "Once analysis finishes, this space will summarize what deserves attention first."
        )
        st.markdown(
            f"""
            <div class="overview-hero">
                <div class="overview-kicker">At a glance</div>
                <div class="overview-title">{html.escape(lead_text)}</div>
                <div class="overview-copy">{html.escape(lead_note)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        insight_cards = top_clauses[:3]
        if insight_cards:
            insight_html = "".join(
                f"""
                <div class="insight-card">
                    <div class="insight-card-title">{html.escape(_display_category(clause["category"]))}</div>
                    <div class="insight-card-copy">{html.escape(clause[clause_explanation_key])}</div>
                    <div class="insight-card-note">What to check next: {html.escape(_action_prompt_for_clause(clause))}</div>
                </div>
                """
                for clause in insight_cards
            )
            st.markdown(f'<div class="insight-grid">{insight_html}</div>', unsafe_allow_html=True)

        st.markdown("<div style='height:1.4rem;'></div>", unsafe_allow_html=True)
        left_col, right_col = st.columns([1.12, 0.88], gap="large")

        with left_col:
            st.markdown('<div class="section-label">Executive Summary</div>', unsafe_allow_html=True)
            st.markdown('<div class="section-intro">A calmer read of the document: what it covers, what can change later, and what the user should not miss.</div>', unsafe_allow_html=True)
            if summary_bullets:
                summary_html = "".join(
                    f"""
                    <div class="summary-point">
                        <div class="summary-point-title">Key takeaway {index}</div>
                        <div class="summary-point-copy">{html.escape(point)}</div>
                    </div>
                    """
                    for index, point in enumerate(summary_bullets, start=1)
                )
                st.markdown(
                    f'<div class="summary-card">{summary_html}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="summary-card"><pre style="white-space:pre-wrap;font-family:inherit;margin:0;line-height:1.82;">{html.escape(summary_text)}</pre></div>',
                    unsafe_allow_html=True,
                )

        with right_col:
            st.markdown('<div class="section-label">Top Risk Signals</div>', unsafe_allow_html=True)
            st.markdown('<div class="section-intro">The strongest watch-outs, written to be scanned quickly before going into the full clause text.</div>', unsafe_allow_html=True)
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
                        <div style="margin-top:0.6rem;font-weight:600;line-height:1.7;">{html.escape(clause[clause_explanation_key])}</div>
                        <div class="muted" style="margin-top:0.65rem;">What to do: {html.escape(_action_prompt_for_clause(clause))}</div>
                        <div class="muted" style="margin-top:0.45rem;">Page {clause['page_number']} | Confidence {clause['confidence']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with result_tab_deep_dive:
        st.markdown('<div class="section-label">Clause-By-Clause Deep Dive</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-intro">This section is for careful readers who want the actual supporting clauses, trigger phrases, and risk reasoning. It is intentionally separate so the main dashboard stays breathable.</div>', unsafe_allow_html=True)
        clause_columns = st.columns([1, 1], gap="large")
        for index, clause in enumerate(deep_clauses):
            badges = (
                _risk_badge(clause["risk"])
                + _neutral_badge(f"Score {clause['risk_score']}/10")
                + _neutral_badge(f"Confidence {clause['confidence']}")
                + _neutral_badge(_display_category(clause["category"]))
            )
            highlighted = _highlight_clause(clause["clause"][:420], clause.get("highlighted_terms", []))
            terms = ", ".join(clause.get("highlighted_terms", [])[:5]) or "No explicit trigger terms"
            with clause_columns[index % 2]:
                st.markdown(
                    f"""
                    <div class="clause-card" style="margin-bottom:1.15rem;">
                        {badges}
                        <div class="muted" style="margin-top:0.5rem;">Page {clause['page_number']} | Category confidence {clause['category_confidence']}</div>
                        <div style="margin-top:0.9rem; line-height:1.82;">{highlighted}</div>
                        <div class="muted" style="margin-top:1rem;">Why flagged: {html.escape(clause[clause_explanation_key])}</div>
                        <div class="muted" style="margin-top:0.35rem;">Key phrases: {html.escape(terms)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with result_tab_chat:
        st.markdown('<div class="section-label">Chat With Document</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-intro">Ask direct questions in your own words. The app answers using retrieved evidence so the user can verify the result instead of blindly trusting it.</div>', unsafe_allow_html=True)
        st.markdown('<div class="chat-shell">', unsafe_allow_html=True)

        question = st.text_input("Ask something about the document", key="document_question")

        if st.button("Ask", key="document_question_submit"):
            if not question.strip():
                st.warning("Please enter a question")
            else:
                with st.spinner("Thinking..."):
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
                                    <div style="line-height:1.82;">{html.escape(result["answer"])}</div>
                                    <div class="muted" style="margin-top:0.82rem;">{status_label} | Confidence {result['confidence']:.2f}</div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                            st.markdown('<div class="section-label" style="margin-top:1rem;">Citations</div>', unsafe_allow_html=True)
                            st.markdown('<div class="section-intro">These are the exact chunks used to support the answer.</div>', unsafe_allow_html=True)
                            citation_columns = st.columns(2, gap="large")
                            for index, ev in enumerate(result["citations"]):
                                with citation_columns[index % 2]:
                                    st.markdown(
                                        f"""
                                        <div class="citation-card" style="margin-bottom:0.95rem;">
                                            {_neutral_badge(f"Page {ev['page_number']}")}
                                            {_neutral_badge(f"Chunk {ev['chunk_id'] + 1}")}
                                            {_neutral_badge(f"Relevance {ev['relevance_score']:.2f}")}
                                            <div style="margin-top:0.8rem; line-height:1.72;">{html.escape(ev['text'][:320])}</div>
                                        </div>
                                        """,
                                        unsafe_allow_html=True,
                                    )

                    except Exception as e:
                        st.error(f"Connection Error: {e}")

        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
else:
    st.markdown(
        """
        <div class="nav-shell">
            <div class="workspace-empty">
                <div class="workspace-empty-title">Results workspace</div>
                <div class="section-intro" style="margin-bottom:0;">Upload a document to unlock the overview, deep-dive review, and grounded chat experience. The layout expands into separate analysis spaces once a file, link, or printed page is processed.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
