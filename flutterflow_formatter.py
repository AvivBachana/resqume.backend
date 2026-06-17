from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4


CRITICAL_KEYWORDS = (
    "דום לב",
    "החייאה",
    "לא נושם",
    "חנק",
    "שבץ",
    "דימום",
    "איבוד הכרה",
    "פרכוס",
)

EMERGENCY_CALL_KEYWORDS = (
    "מד״א",
    "מדא",
    "101",
    "חירום",
    "התקשרו",
    "התקשר",
    "אמבולנס",
)

ASSESSMENT_KEYWORDS = (
    "בדקו",
    "בדקי",
    "בדוק",
    "האם",
    "נשימה",
    "תגובה",
    "הכרה",
)

FIRST_AID_KEYWORDS = (
    "התחילו",
    "התחל",
    "לחצו",
    "עיסויי",
    "לחץ",
    "הרימו",
    "השכיבו",
    "עצור",
    "עצרו",
)

DEFAULT_CLARIFYING_QUESTIONS = [
    {
        "question_id": "Q_CONSCIOUSNESS",
        "text": "האם האדם מגיב כשקוראים לו או נוגעים בו?",
        "options": ["כן", "לא", "לא בטוחה"],
        "parameter": "consciousness_status",
    },
    {
        "question_id": "Q_BREATHING",
        "text": "האם האדם נושם כרגיל?",
        "options": ["כן", "לא", "לא בטוחה"],
        "parameter": "breathing_status",
    },
    {
        "question_id": "Q_BLEEDING",
        "text": "האם יש דימום משמעותי או בלתי נשלט?",
        "options": ["כן", "לא", "לא בטוחה"],
        "parameter": "bleeding_status",
    },
]


def _safe_get(obj: Any, field_name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(field_name, default)

    return getattr(obj, field_name, default)


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _generate_event_id() -> str:
    return f"EVT_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"


def _is_uncertain(decision: Any) -> bool:
    decision_code = _safe_get(decision, "decision_code", "")
    confidence = _safe_get(decision, "confidence", "")
    best_score = float(_safe_get(decision, "best_score", 0.0) or 0.0)

    return (
        decision_code == "UNCERTAIN"
        or confidence == "uncertain"
        or best_score <= 0
    )


def _build_status(decision: Any) -> str:
    confidence = _safe_get(decision, "confidence", "")

    if _is_uncertain(decision):
        return "needs_clarification"

    if confidence == "low":
        return "needs_clarification"

    return "classified"


def _build_target_screen(status: str) -> str:
    if status == "classified":
        return "Result_Summary_05"

    if status == "needs_clarification":
        return "Clarifying_Question_04"

    return "Safety_Fallback_07"


def _build_display_mode(status: str, urgency_level: str) -> str:
    if status != "classified":
        return "warning"

    if urgency_level == "critical":
        return "critical"

    if urgency_level == "high":
        return "urgent"

    return "standard"


def _infer_urgency_level(decision: Any) -> str:
    if _is_uncertain(decision):
        return "unknown"

    decision_name = str(_safe_get(decision, "decision_name", "") or "")
    decision_code = str(_safe_get(decision, "decision_code", "") or "")
    instructions = _safe_get(decision, "instructions", []) or []

    text_blob = " ".join([decision_name, decision_code, *instructions])

    if any(keyword in text_blob for keyword in ("דום לב", "החייאה", "לא נושם", "חנק")):
        return "critical"

    if any(keyword in text_blob for keyword in CRITICAL_KEYWORDS):
        return "high"

    if any(keyword in text_blob for keyword in EMERGENCY_CALL_KEYWORDS):
        return "high"

    return "medium"


def _requires_emergency_call(decision: Any, urgency_level: str) -> bool:
    if urgency_level in {"critical", "high"}:
        return True

    instructions = _safe_get(decision, "instructions", []) or []
    forbidden_action = str(_safe_get(decision, "forbidden_action", "") or "")

    text_blob = " ".join([*instructions, forbidden_action])

    return any(keyword in text_blob for keyword in EMERGENCY_CALL_KEYWORDS)


def _infer_instruction_type(instruction_text: str) -> str:
    text = instruction_text or ""

    if any(keyword in text for keyword in EMERGENCY_CALL_KEYWORDS):
        return "emergency_call"

    if any(keyword in text for keyword in ASSESSMENT_KEYWORDS):
        return "assessment"

    if any(keyword in text for keyword in FIRST_AID_KEYWORDS):
        return "first_aid_action"

    return "general_instruction"


def _build_instruction_objects(instructions: List[str]) -> List[Dict[str, Any]]:
    result = []

    for index, instruction in enumerate(instructions, start=1):
        clean_instruction = str(instruction).strip()

        if not clean_instruction:
            continue

        result.append(
            {
                "step_number": index,
                "text": clean_instruction,
                "type": _infer_instruction_type(clean_instruction),
                "is_safe_action": True,
            }
        )

    return result


def _build_ranked_conditions(decision: Any) -> List[Dict[str, Any]]:
    scores = _safe_get(decision, "scores", {}) or {}
    decision_code = _safe_get(decision, "decision_code", "")
    decision_name = _safe_get(decision, "decision_name", "")

    ranked = sorted(scores.items(), key=lambda item: float(item[1] or 0.0), reverse=True)

    result = []
    for condition_code, score in ranked:
        condition_name = decision_name if condition_code == decision_code else condition_code

        result.append(
            {
                "condition_code": condition_code,
                "condition_name": condition_name,
                "score": float(score or 0.0),
                "is_primary": condition_code == decision_code,
            }
        )

    return result


def _build_detected_symptoms(decision: Any) -> List[Dict[str, Any]]:
    matched_phrases = _safe_get(decision, "matched_phrases", []) or []
    result = []

    for match in matched_phrases:
        phrase_text = _safe_get(match, "phrase_text", "")
        clinical_meaning = _safe_get(match, "clinical_meaning", "")
        parameter = _safe_get(match, "parameter", "")
        value = _safe_get(match, "value", "")
        priority = _safe_get(match, "priority", 0)

        result.append(
            {
                "phrase": phrase_text,
                "clinical_meaning": clinical_meaning,
                "parameter": parameter,
                "value": value,
                "priority": int(priority or 0),
            }
        )

    return result


def _build_main_title(status: str, decision: Any) -> str:
    if status == "classified":
        decision_name = str(_safe_get(decision, "decision_name", "") or "").strip()
        return f"חשד ל{decision_name}" if decision_name else "זוהה מצב חירום"

    if status == "needs_clarification":
        return "נדרש מידע נוסף"

    return "לא ניתן לסווג את האירוע"


def _build_subtitle(status: str, urgency_level: str) -> str:
    if status == "classified" and urgency_level == "critical":
        return "נדרשת פעולה מיידית"

    if status == "classified" and urgency_level == "high":
        return "יש לפעול במהירות ולשקול פנייה למד״א"

    if status == "classified":
        return "המערכת זיהתה מצב אפשרי והכינה הנחיות"

    if status == "needs_clarification":
        return "עני על שאלה קצרה כדי לשפר את הסיווג"

    return "במקרה של סכנה מיידית יש להתקשר למד״א 101"


def _build_fallback_message(status: str) -> Optional[str]:
    if status == "classified":
        return None

    return "המערכת לא הצליחה להגיע לסיווג ודאי. במקרה של סכנת חיים, חוסר הכרה, קושי נשימה, דימום משמעותי או החמרה מהירה, התקשרו מיד למד״א 101."


def format_dss_for_flutterflow(
    decision: Any,
    *,
    raw_text: Optional[str] = None,
    cleaned_text: Optional[str] = None,
    source: str = "text",
    event_id: Optional[str] = None,
    timestamp: Optional[str] = None,
    include_debug: bool = True,
) -> Dict[str, Any]:
    status = _build_status(decision)
    urgency_level = _infer_urgency_level(decision)
    target_screen = _build_target_screen(status)
    requires_emergency_call = _requires_emergency_call(decision, urgency_level)

    instructions = _safe_get(decision, "instructions", []) or []
    instruction_objects = _build_instruction_objects(instructions)

    flutterflow_response: Dict[str, Any] = {
        "event_id": event_id or _generate_event_id(),
        "timestamp": timestamp or _now_iso(),
        "status": status,
        "target_screen": target_screen,
        "display_mode": _build_display_mode(status, urgency_level),
        "source": source,
        "input": {
            "raw_text": raw_text,
            "cleaned_text": cleaned_text,
            "normalized_text": _safe_get(decision, "normalized_text", ""),
        },
        "classification": {
            "primary_condition_code": None if status != "classified" else _safe_get(decision, "decision_code", ""),
            "primary_condition_name": None if status != "classified" else _safe_get(decision, "decision_name", ""),
            "confidence": _safe_get(decision, "confidence", "uncertain"),
            "best_score": float(_safe_get(decision, "best_score", 0.0) or 0.0),
            "second_score": float(_safe_get(decision, "second_score", 0.0) or 0.0),
            "margin": float(_safe_get(decision, "margin", 0.0) or 0.0),
            "urgency_level": urgency_level,
        },
        "ui": {
            "main_title": _build_main_title(status, decision),
            "subtitle": _build_subtitle(status, urgency_level),
            "show_emergency_call_button": requires_emergency_call,
            "show_clarifying_questions": status == "needs_clarification",
            "show_safety_message": status != "classified",
        },
        "instructions": instruction_objects,
        "safety": {
            "requires_emergency_call": requires_emergency_call,
            "forbidden_action": _safe_get(decision, "forbidden_action", ""),
            "fallback_message": _build_fallback_message(status),
        },
        "clarifying_questions": DEFAULT_CLARIFYING_QUESTIONS if status == "needs_clarification" else [],
        "detected_symptoms": _build_detected_symptoms(decision),
        "ranked_conditions": _build_ranked_conditions(decision),
    }

    if include_debug:
        flutterflow_response["debug"] = {
            "parameters": _safe_get(decision, "parameters", {}) or {},
            "scores": _safe_get(decision, "scores", {}) or {},
            "matched_phrases_count": len(_safe_get(decision, "matched_phrases", []) or []),
            "original_decision": decision.to_dict() if hasattr(decision, "to_dict") else decision,
        }

    return flutterflow_response