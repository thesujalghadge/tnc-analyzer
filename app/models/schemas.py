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


class RiskOverview(BaseModel):
    high: int
    medium: int
    low: int


class AnalyzeResponse(BaseModel):
    document_id: str
    summary: str
    risk_overview: RiskOverview
    clauses: List[ClauseAnalysis]
    formatted_output: str


class AskRequest(BaseModel):
    question: str
    document_id: str


class AskResponse(BaseModel):
    answer: str
    grounded: bool
    confidence: float
    citations: List[SourceChunk]
