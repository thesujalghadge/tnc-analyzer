from dataclasses import dataclass
from threading import Lock
from typing import Dict, List, Optional
from uuid import uuid4


@dataclass
class DocumentSession:
    document_id: str
    chunks: List[dict]
    clauses: List[dict]
    vector_index: object


class InMemoryDocumentStore:
    def __init__(self):
        self._documents: Dict[str, DocumentSession] = {}
        self._lock = Lock()

    def create(self, chunks: List[dict], clauses: List[dict], vector_index: object) -> DocumentSession:
        session = DocumentSession(
            document_id=str(uuid4()),
            chunks=chunks,
            clauses=clauses,
            vector_index=vector_index,
        )

        with self._lock:
            self._documents[session.document_id] = session

        return session

    def get(self, document_id: str) -> Optional[DocumentSession]:
        return self._documents.get(document_id)
