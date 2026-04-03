import sqlite3
import shutil
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import numpy as np

from app.db import database
from app.db.database import init_db
from app.models.schemas import ClauseAnalysis
from app.services import persistence_service
from app.services.persistence_service import build_analysis_payload, fetch_document_bundle, persist_analysis
from app.services.qa_service import answer_question
from app.services.report_service import build_analysis_report_pdf


def fake_get_embeddings(texts):
    vectors = []
    for text in texts:
        lowered = text.lower()
        if "interest" in lowered or "emi" in lowered or "rate" in lowered:
            vectors.append([1.0, 0.0, 0.0])
        elif "privacy" in lowered or "data" in lowered or "share" in lowered:
            vectors.append([0.0, 1.0, 0.0])
        else:
            vectors.append([0.0, 0.0, 1.0])
    return vectors


class FakeIndex:
    def __init__(self, embeddings):
        self.embeddings = np.array(embeddings, dtype="float32")

    def search(self, query_embedding, k):
        query = np.array(query_embedding[0], dtype="float32")
        distances = np.linalg.norm(self.embeddings - query, axis=1)
        ranked_indices = np.argsort(distances)[:k]
        ranked_distances = distances[ranked_indices]
        return np.array([ranked_distances]), np.array([ranked_indices])


class PublicMvpSmokeTests(unittest.TestCase):
    def setUp(self):
        self.test_root = Path("data/test_artifacts")
        self.test_root.mkdir(parents=True, exist_ok=True)
        self.memory_uri = f"file:tnc_test_{uuid4().hex}?mode=memory&cache=shared"
        self.anchor_connection = sqlite3.connect(self.memory_uri, uri=True)
        self.anchor_connection.row_factory = sqlite3.Row
        self.anchor_connection.execute("PRAGMA foreign_keys = ON")

        self.connection_patchers = [
            patch("app.db.database.get_connection", self._shared_get_connection),
            patch("app.services.persistence_service.get_connection", self._shared_get_connection),
        ]
        for patcher in self.connection_patchers:
            patcher.start()

        init_db()

        self.document_id = "doc-interest"
        self.chunks = [
            {
                "chunk_id": 0,
                "page_number": 1,
                "text": "The interest rate is subject to revision from time to time and the bank may increase the EMI.",
            },
            {
                "chunk_id": 1,
                "page_number": 1,
                "text": "Processing fees and pre-closure charges may apply depending on the product.",
            },
        ]
        self.clauses = [
            ClauseAnalysis(
                chunk_id=0,
                page_number=1,
                clause=self.chunks[0]["text"],
                category="payment",
                category_confidence=0.91,
                risk="HIGH",
                risk_score=7.2,
                confidence=0.97,
                reason="The lender can change EMIs or repayment duration after rate revisions.",
                highlighted_terms=["interest rate", "increase the emi"],
            ),
            ClauseAnalysis(
                chunk_id=1,
                page_number=1,
                clause=self.chunks[1]["text"],
                category="fees",
                category_confidence=0.85,
                risk="MEDIUM",
                risk_score=4.6,
                confidence=0.9,
                reason="The clause can increase what the user has to pay.",
                highlighted_terms=["processing fees", "charges"],
            ),
        ]
        persist_analysis(
            document_id=self.document_id,
            source_type="pdf",
            original_name="loan_terms.pdf",
            stored_path="data/uploads/loan_terms.pdf",
            file_size=12345,
            mime_type="application/pdf",
            checksum="abc123",
            page_count=1,
            summary="• The interest rate may change.\n• Fees may apply.",
            formatted_output="📄 SUMMARY:\n• The interest rate may change.\n• Fees may apply.",
            risk_overview={"high": 1, "medium": 1, "low": 0},
            clauses=self.clauses,
            chunks=self.chunks,
        )

    def tearDown(self):
        for patcher in reversed(self.connection_patchers):
            patcher.stop()
        self.anchor_connection.close()
        shutil.rmtree(self.test_root, ignore_errors=True)

    @contextmanager
    def _shared_get_connection(self):
        connection = sqlite3.connect(self.memory_uri, uri=True)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def test_build_analysis_payload_returns_saved_payload(self):
        payload = build_analysis_payload(self.document_id)

        self.assertIsNotNone(payload)
        self.assertEqual(payload["document_id"], self.document_id)
        self.assertEqual(payload["metadata"]["original_name"], "loan_terms.pdf")
        self.assertEqual(len(payload["clauses"]), 2)

    def test_report_builder_returns_pdf_bytes(self):
        bundle = fetch_document_bundle(self.document_id)
        response = build_analysis_report_pdf(bundle)

        self.assertTrue(response.startswith(b"%PDF-1.4"))

    def test_qna_can_run_from_restored_persistence_bundle(self):
        bundle = fetch_document_bundle(self.document_id)
        chunk_texts = [chunk["text"] for chunk in bundle["chunks"]]
        embeddings = fake_get_embeddings(chunk_texts)
        fake_index = FakeIndex(embeddings)

        restored_clauses = build_analysis_payload(self.document_id)["clauses"]

        with patch(
            "app.services.qa_service.get_embeddings",
            side_effect=fake_get_embeddings,
        ), patch("app.services.llm_service.USE_GEMINI", False), patch(
            "app.services.qa_service.generate_answer",
            return_value={"answer": "Yes. The interest rate can change over time.", "grounded": True},
        ):
            response = answer_question(
                "Can the interest rate change?",
                fake_index,
                bundle["chunks"],
                restored_clauses,
            )

        self.assertTrue(response.grounded)
        self.assertGreaterEqual(response.confidence, 0.5)
        self.assertIn("interest rate", response.answer.lower())
        self.assertGreaterEqual(len(response.citations), 1)


if __name__ == "__main__":
    unittest.main()
