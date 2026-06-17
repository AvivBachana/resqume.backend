from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from clarification import get_clarification_question, should_ask_clarification
from dss_engine import run_dss
from excel_dss_loader import DSSKnowledgeBase, load_dss_knowledge_base

PROJECT_ROOT = Path(__file__).resolve().parent
DSS_PATH = PROJECT_ROOT / "dss.xlsx"

CONFIDENCE_TO_NUMERIC = {
    "high": 0.90,
    "medium": 0.60,
    "low": 0.35,
    "uncertain": 0.0,
}


@lru_cache(maxsize=1)
def _get_kb() -> DSSKnowledgeBase:
    return load_dss_knowledge_base(DSS_PATH)


def _confidence_to_numeric(confidence: str) -> float:
    return CONFIDENCE_TO_NUMERIC.get(str(confidence).lower(), 0.0)


def _urgency_from_decision(decision_code: str, confidence_value: float) -> str:
    if decision_code == "UNCERTAIN" or confidence_value <= 0.0:
        return "unknown"
    if confidence_value >= 0.75:
        return "critical"
    return "urgent"


def _unique_non_empty(items: List[str]) -> List[str]:
    seen: set[str] = set()
    result: List[str] = []
    for item in items:
        cleaned = str(item).strip()
        if cleaned and cleaned not in seen:
            result.append(cleaned)
            seen.add(cleaned)
    return result


def _alternative_conditions(scores: Dict[str, float], selected_code: str) -> List[Dict[str, Any]]:
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    alternatives: List[Dict[str, Any]] = []
    for condition_code, score in ranked:
        if condition_code == selected_code:
            continue
        alternatives.append({"condition": condition_code, "confidence": max(0.0, min(float(score) / 10.0, 1.0))})
        if len(alternatives) >= 3:
            break
    return alternatives


def _build_condition_names(kb: DSSKnowledgeBase) -> Dict[str, str]:
    names: Dict[str, str] = {}
    for r in kb.rules:
        names[r.condition_code] = r.condition_name
    for code, g in kb.guidelines.items():
        names[code] = g.condition_name
    return names


def analyze_emergency_text(text: str, force_final: bool = False) -> Dict[str, Any]:
    cleaned_text = str(text or "").strip()
    if not cleaned_text:
        raise ValueError("Text input is empty.")

    kb = _get_kb()
    decision = run_dss(cleaned_text, kb=kb)
    confidence_value = _confidence_to_numeric(decision.confidence)

    # Ranked scores for candidate analysis.
    ranked_scores = sorted(decision.scores.items(), key=lambda x: x[1], reverse=True)
    max_score = max(decision.scores.values(), default=1.0) or 1.0

    # Top condition — normalized confidence (top always scores 100% relative to itself).
    top_confidence_normalized = round(min(decision.best_score / max_score, 1.0), 2)

    # Second condition.
    second_entry = ranked_scores[1] if len(ranked_scores) > 1 else None
    second_code: Optional[str] = second_entry[0] if second_entry else None
    second_score: float = second_entry[1] if second_entry else 0.0
    second_confidence_normalized: Optional[float] = (
        round(min(second_score / max_score, 1.0), 2) if second_code else None
    )

    condition_names = _build_condition_names(kb)
    second_condition_name: Optional[str] = condition_names.get(second_code, second_code) if second_code else None

    second_guideline = kb.guidelines.get(second_code) if second_code else None
    second_forbidden_action: Optional[str] = (
        second_guideline.forbidden_action if second_guideline and second_guideline.forbidden_action else None
    )

    # Clarification decision.
    ask = (not force_final) and should_ask_clarification(
        confidence_value=confidence_value,
        margin=decision.margin,
        best_score=decision.best_score,
    )

    clarification_data = None
    if ask and decision.decision_code != "UNCERTAIN":
        raw_question = get_clarification_question(
            decision.decision_code, second_code or decision.decision_code
        )
        if raw_question:
            top_two = sorted(decision.scores.items(), key=lambda x: x[1], reverse=True)[:2]
            candidates = [
                {
                    "code": code,
                    "name": condition_names.get(code, code),
                    "confidence": round(min(score / max_score, 1.0), 2),
                }
                for code, score in top_two
                if score > 0
            ]
            clarification_data = {
                "question_id": raw_question["question_id"],
                "question_text": raw_question["question_text"],
                "options": raw_question["options"],
                "candidate_conditions": raw_question["candidates"],
                "candidates": candidates,
            }

    status = "needs_clarification" if clarification_data else "final"
    matched_symptoms = _unique_non_empty([m.clinical_meaning for m in decision.matched_phrases[:10]])
    warnings = _unique_non_empty([decision.forbidden_action])

    return {
        "input_type": "text",
        "transcript": decision.input_text,
        "case_id": decision.decision_code,
        "condition": decision.decision_name,
        "urgency": _urgency_from_decision(decision.decision_code, confidence_value),
        "confidence": confidence_value,
        "status": status,
        "needs_clarification": clarification_data is not None,
        "clarifying_question": clarification_data["question_text"] if clarification_data else None,
        "clarification": clarification_data,
        "instructions": decision.instructions,
        "warnings": warnings,
        "matched_symptoms": matched_symptoms,
        "alternative_conditions": _alternative_conditions(decision.scores, selected_code=decision.decision_code),
        # Semantic fields for UI rendering.
        "top_condition_name": decision.decision_name,
        "top_confidence": top_confidence_normalized,
        "second_condition_name": second_condition_name,
        "second_confidence": second_confidence_normalized,
        "selected_condition_name": decision.decision_name,
        "selected_confidence": confidence_value,
        "selected_forbidden_action": decision.forbidden_action,
        "second_forbidden_action": second_forbidden_action,
    }
