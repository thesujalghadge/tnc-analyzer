from typing import List

from pydantic import BaseModel, Field


class SourceChunk(BaseModel):
    chunk_id: int = Field(..., description="Zero-based chunk index in the analyzed document")
    page_number: int
    text: str
    relevance_score: float


class ClauseAnalysis(BaseModel):
    chunk_id: int
    page_number: int
    clause: str
    category: str
    category_confidence: float
    risk: str
    risk_score: float
    confidence: float
    reason: str
    highlighted_terms: List[str]


class RiskOverview(BaseModel):
    high: int
    medium: int
    low: int


class DocumentMetadata(BaseModel):
    source_type: str
    original_name: str | None = None
    source_url: str | None = None
    file_size: int | None = None
    page_count: int
    mime_type: str | None = None
    checksum: str | None = None
    created_at: str | None = None


class AnalyzeResponse(BaseModel):
    document_id: str
    summary: str
    risk_overview: RiskOverview
    clauses: List[ClauseAnalysis]
    formatted_output: str
    metadata: DocumentMetadata | None = None


class AnalyzeUrlRequest(BaseModel):
    url: str


class AskRequest(BaseModel):
    question: str
    document_id: str


class AskResponse(BaseModel):
    answer: str
    grounded: bool
    confidence: float
    citations: List[SourceChunk]
