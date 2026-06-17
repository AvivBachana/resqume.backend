from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class AnalyzeTextRequest(BaseModel):
    text: str = Field(..., min_length=1)


class AlternativeCondition(BaseModel):
    condition: str
    confidence: float


class ClarificationCandidate(BaseModel):
    code: str
    name: str
    confidence: float


class ClarificationData(BaseModel):
    question_id: str
    question_text: str
    options: List[str]
    candidate_conditions: List[str]
    candidates: List[ClarificationCandidate]


class AnalyzeResponse(BaseModel):
    input_type: str
    transcript: str
    case_id: str
    condition: str
    urgency: str
    confidence: float
    status: str  # "final" | "needs_clarification"
    needs_clarification: bool
    clarifying_question: Optional[str]
    clarification: Optional[ClarificationData]
    instructions: List[str]
    warnings: List[str]
    matched_symptoms: List[str]
    alternative_conditions: List[AlternativeCondition]
    # Semantic fields for UI rendering
    top_condition_name: str = ""
    top_confidence: float = 0.0
    second_condition_name: Optional[str] = None
    second_confidence: Optional[float] = None
    selected_condition_name: str = ""
    selected_confidence: float = 0.0
    selected_forbidden_action: str = ""
    second_forbidden_action: Optional[str] = None


class ClarifyRequest(BaseModel):
    text: str = Field(..., min_length=1)
    question_id: str
    answer_index: str  # "0" | "1" | "2"


class ErrorResponse(BaseModel):
    error: bool = True
    message: str
