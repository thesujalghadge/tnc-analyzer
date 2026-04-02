import re

import numpy as np

from app.services.embedding import get_embeddings


CATEGORY_RULES = {
    "payment": {
        "keywords": ["payment", "emi", "interest", "repayment", "fee", "charge", "billing", "invoice", "installment"],
        "description": "Payments, fees, billing, subscription charges, interest rates, repayment obligations",
    },
    "liability": {
        "keywords": ["liable", "liability", "responsible", "indemnify", "damages", "obligation"],
        "description": "Legal liability, indemnity, user responsibility, damages, obligations",
    },
    "termination": {
        "keywords": ["terminate", "termination", "cancel", "suspend", "close account", "end service"],
        "description": "Account suspension, termination, cancellation, service shutdown",
    },
    "privacy": {
        "keywords": ["privacy", "personal data", "personal information", "share data", "collect data", "disclose", "cookies"],
        "description": "Privacy, personal data collection, sharing, disclosure, tracking",
    },
    "penalty": {
        "keywords": ["penalty", "fine", "late fee", "default", "penal", "extra charge"],
        "description": "Penalties, late fees, fines, default charges, punitive costs",
    },
    "refund": {
        "keywords": ["refund", "return", "non-refundable", "refund policy", "cancelation fee"],
        "description": "Refunds, returns, reversal of payment, non-refundable terms",
    },
    "renewal": {
        "keywords": ["renew", "auto-renew", "recurring", "subscription", "renewal term"],
        "description": "Automatic renewal, recurring subscriptions, renewal cycles",
    },
    "dispute": {
        "keywords": ["arbitration", "dispute", "governing law", "jurisdiction", "court", "resolve disputes"],
        "description": "Disputes, arbitration, governing law, jurisdiction, legal resolution",
    },
    "general": {
        "keywords": ["purpose", "eligibility", "introduction", "overview", "scope"],
        "description": "General information, purpose, eligibility, introductory clauses",
    },
}


RISK_SIGNALS = {
    "unilateral_change": {
        "weight": 3.0,
        "keywords": ["may change", "can change", "at any time", "without notice", "sole discretion"],
        "reason": "Terms can change without giving the user much control.",
    },
    "deemed_notice": {
        "weight": 3.2,
        "keywords": ["deemed to have notice", "notice board", "published in newspapers", "passbook", "statement of account"],
        "reason": "The lender can treat indirect notice as sufficient, even without directly informing the user.",
    },
    "emi_change": {
        "weight": 2.8,
        "keywords": ["increase the emi", "reduce or increase the emi", "extend the repayment period", "revision in interest rate"],
        "reason": "The lender can change EMIs or repayment duration after rate revisions.",
    },
    "financial_penalty": {
        "weight": 2.5,
        "keywords": ["penalty", "late fee", "fine", "extra charge", "processing fee", "charges"],
        "reason": "The clause can increase what the user has to pay.",
    },
    "broad_liability": {
        "weight": 2.5,
        "keywords": ["liable", "indemnify", "responsible for all", "hold harmless"],
        "reason": "The user may carry broad legal or financial responsibility.",
    },
    "termination_power": {
        "weight": 2.0,
        "keywords": ["terminate", "suspend", "close account", "deny access"],
        "reason": "The provider can stop service or restrict access.",
    },
    "data_sharing": {
        "weight": 2.0,
        "keywords": ["share", "disclose", "third party", "collect", "personal data"],
        "reason": "The clause allows collection or sharing of user data.",
    },
    "forced_dispute_process": {
        "weight": 1.8,
        "keywords": ["arbitration", "exclusive jurisdiction", "waive class action"],
        "reason": "The user may have limited legal options during disputes.",
    },
    "auto_renewal": {
        "weight": 1.5,
        "keywords": ["auto-renew", "recurring", "renew automatically"],
        "reason": "The agreement can continue and charge the user automatically.",
    },
    "refund_restriction": {
        "weight": 1.5,
        "keywords": ["non-refundable", "no refund", "refund not available"],
        "reason": "The user may not get money back after payment.",
    },
}


_CATEGORY_EMBEDDINGS = None


def _phrase_present(text: str, phrase: str):
    if " " in phrase or "-" in phrase:
        return phrase in text

    pattern = rf"\b{re.escape(phrase)}s?\b"
    return re.search(pattern, text) is not None


def _matched_terms(text: str, terms):
    return [term for term in terms if _phrase_present(text, term)]


def _cosine_similarity(vector_a, vector_b):
    denominator = np.linalg.norm(vector_a) * np.linalg.norm(vector_b)
    if denominator == 0:
        return 0.0
    return float(np.dot(vector_a, vector_b) / denominator)


def _get_category_embeddings():
    global _CATEGORY_EMBEDDINGS

    if _CATEGORY_EMBEDDINGS is None:
        descriptions = [rule["description"] for rule in CATEGORY_RULES.values()]
        embeddings = get_embeddings(descriptions)
        _CATEGORY_EMBEDDINGS = {
            category: np.array(embedding, dtype="float32")
            for category, embedding in zip(CATEGORY_RULES.keys(), embeddings)
        }

    return _CATEGORY_EMBEDDINGS


def classify_clause(clause: str):
    clause_lower = clause.lower()
    keyword_scores = {}

    for category, rule in CATEGORY_RULES.items():
        matched = _matched_terms(clause_lower, rule["keywords"])
        keyword_scores[category] = len(matched)

    clause_embedding = np.array(get_embeddings([clause])[0], dtype="float32")
    category_embeddings = _get_category_embeddings()

    combined_scores = {}
    for category, rule in CATEGORY_RULES.items():
        semantic_score = _cosine_similarity(clause_embedding, category_embeddings[category])
        keyword_score = min(keyword_scores[category] / 3.0, 1.0)
        combined_scores[category] = (keyword_score * 0.65) + (semantic_score * 0.35)

    best_category = max(combined_scores, key=combined_scores.get)
    confidence = round(min(max(combined_scores[best_category], 0.0), 1.0), 2)

    if confidence < 0.35:
        return "other", confidence

    return best_category, confidence


def score_risk(clause: str, category: str):
    clause_lower = clause.lower()
    matched_signals = []
    highlighted_terms = []
    score = 1.0

    for signal_name, signal in RISK_SIGNALS.items():
        matched_keywords = _matched_terms(clause_lower, signal["keywords"])
        if matched_keywords:
            score += signal["weight"]
            matched_signals.append({
                "name": signal_name,
                "weight": signal["weight"],
                "reason": signal["reason"],
                "keywords": matched_keywords,
            })
            highlighted_terms.extend(matched_keywords)

    category_bias = {
        "liability": 1.2,
        "penalty": 1.2,
        "termination": 1.0,
        "privacy": 0.8,
        "dispute": 0.8,
        "renewal": 0.7,
        "refund": 0.6,
        "payment": 0.5,
    }
    score += category_bias.get(category, 0.0)

    score = round(min(score, 10.0), 1)

    if score >= 7.0:
        risk_level = "HIGH"
    elif score >= 4.0:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    if matched_signals:
        strongest_signal = max(matched_signals, key=lambda signal: signal["weight"])
        reason = strongest_signal["reason"]
    elif category == "general":
        reason = "This clause looks informational and has limited direct user risk."
    elif category == "other":
        reason = "The clause could not be classified confidently, so risk is estimated conservatively."
    elif category == "payment":
        reason = "This clause affects pricing, repayment, or fee-related terms for the user."
    else:
        reason = f"This clause is mainly about {category} terms and may affect the user."

    signal_strength = min(len(matched_signals) * 0.2, 0.5)
    confidence = round(min(0.45 + signal_strength + (score / 20.0), 0.99), 2)

    return risk_level, score, confidence, reason, sorted(set(highlighted_terms))


def analyze_clauses(chunks):
    results = []

    for chunk in chunks:
        if not chunk.strip():
            continue

        category, category_confidence = classify_clause(chunk)
        risk_level, risk_score, risk_confidence, reason, highlighted_terms = score_risk(chunk, category)

        results.append({
            "clause": chunk,
            "category": category,
            "category_confidence": category_confidence,
            "risk": risk_level,
            "risk_score": risk_score,
            "confidence": max(category_confidence, risk_confidence),
            "reason": reason,
            "highlighted_terms": highlighted_terms,
        })

    return results
