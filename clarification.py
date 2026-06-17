"""Clarification question selection based on competing DSS conditions."""
from __future__ import annotations

from typing import Any, Dict, FrozenSet, Optional

CONFIDENCE_THRESHOLD = 0.75
NORMALIZED_GAP_THRESHOLD = 0.15  # gap / best_score

# answer_text_map: "0"=first option, "1"=second option, "2"=not sure
# Hebrew text is appended to the original input and fed back into the DSS.
PAIR_QUESTIONS: Dict[FrozenSet[str], Dict[str, Any]] = {
    frozenset({"G01", "G02"}): {
        "question_id": "q_g01_g02",
        "question_text": "האם האדם מגיב לשיחה ונושם באופן תקין?",
        "options": ["כן, מגיב ונושם", "לא, אינו מגיב ואינו נושם", "לא בטוח/ה"],
        "candidates": ["G01", "G02"],
        "answer_text_map": {
            "0": "האדם מגיב ומדבר נושם יש דופק",
            "1": "אין תגובה אין נשימה אין דופק",
            "2": "",
        },
    },
    frozenset({"G01", "G04"}): {
        "question_id": "q_g01_g04",
        "question_text": "האם האדם מגיב ומנסה לנשום?",
        "options": ["כן, מגיב ומנסה לנשום", "לא, אינו מגיב כלל", "לא בטוח/ה"],
        "candidates": ["G01", "G04"],
        "answer_text_map": {
            "0": "האדם מגיב חסימה בדרכי הנשימה לא מצליח לנשום",
            "1": "אין תגובה אין נשימה אין דופק",
            "2": "",
        },
    },
    frozenset({"G01", "G06"}): {
        "question_id": "q_g01_g06",
        "question_text": "האם יש תנועות פרכוסיות או רעידות בגוף?",
        "options": ["כן, יש פרכוסים", "לא, אין פרכוסים", "לא בטוח/ה"],
        "candidates": ["G01", "G06"],
        "answer_text_map": {
            "0": "יש פרכוסים ותנועות בלתי רצוניות",
            "1": "אין פרכוסים אין תנועות בלתי רצוניות אין נשימה",
            "2": "",
        },
    },
    frozenset({"G02", "G03"}): {
        "question_id": "q_g02_g03",
        "question_text": "האם הכאב בחזה מקרין לזרוע שמאל, לכתף, או ללסת?",
        "options": ["כן, יש הקרנה לזרוע / לסת", "לא, הכאב מקומי בלבד", "לא בטוח/ה"],
        "candidates": ["G02", "G03"],
        "answer_text_map": {
            "0": "כאב מקרין לזרוע שמאל ולסת",
            "1": "אין הקרנת כאב יש חולשה בצד אחד של הגוף",
            "2": "",
        },
    },
    frozenset({"G02", "G04"}): {
        "question_id": "q_g02_g04",
        "question_text": "האם האדם מצליח לנשום, לדבר, או להשתעל?",
        "options": ["כן, יכול לנשום ולדבר", "לא, לא מצליח לנשום כלל", "לא בטוח/ה"],
        "candidates": ["G02", "G04"],
        "answer_text_map": {
            "0": "האדם נושם ומדבר אין חסימה בגרון",
            "1": "חסימה בדרכי הנשימה לא מצליח לנשום",
            "2": "",
        },
    },
    frozenset({"G02", "G06"}): {
        "question_id": "q_g02_g06",
        "question_text": "האם יש כאב בחזה?",
        "options": ["כן, יש כאב בחזה", "לא, אין כאב בחזה", "לא בטוח/ה"],
        "candidates": ["G02", "G06"],
        "answer_text_map": {
            "0": "כאבים חזקים בחזה",
            "1": "אין כאב בחזה יש תנועות בלתי רצוניות",
            "2": "",
        },
    },
    frozenset({"G03", "G05"}): {
        "question_id": "q_g03_g05",
        "question_text": "האם יש דימום חיצוני נראה לעין?",
        "options": ["כן, יש דימום", "לא, אין דימום", "לא בטוח/ה"],
        "candidates": ["G03", "G05"],
        "answer_text_map": {
            "0": "דימום חיצוני כבד לא נעצר",
            "1": "אין דימום יש חולשה בצד אחד קושי בדיבור",
            "2": "",
        },
    },
    frozenset({"G03", "G06"}): {
        "question_id": "q_g03_g06",
        "question_text": "האם יש חולשה או שיתוק בצד אחד של הגוף?",
        "options": ["כן, יש חולשה בצד אחד", "לא, אין חולשה", "לא בטוח/ה"],
        "candidates": ["G03", "G06"],
        "answer_text_map": {
            "0": "חולשה בצד אחד של הגוף קושי בדיבור",
            "1": "אין חולשה יש תנועות בלתי רצוניות פרכוסים",
            "2": "",
        },
    },
    frozenset({"G04", "G06"}): {
        "question_id": "q_g04_g06",
        "question_text": "האם האדם מגיב ומנסה לנשום?",
        "options": ["כן, מנסה לנשום", "לא, אינו מגיב", "לא בטוח/ה"],
        "candidates": ["G04", "G06"],
        "answer_text_map": {
            "0": "האדם מגיב חסימה בגרון לא מצליח לנשום",
            "1": "האדם לא מגיב יש פרכוסים",
            "2": "",
        },
    },
    frozenset({"G05", "G06"}): {
        "question_id": "q_g05_g06",
        "question_text": "האם יש דימום חיצוני?",
        "options": ["כן, יש דימום", "לא, אין דימום", "לא בטוח/ה"],
        "candidates": ["G05", "G06"],
        "answer_text_map": {
            "0": "דימום מסיבי חיצוני לא נעצר",
            "1": "אין דימום יש תנועות בלתי רצוניות",
            "2": "",
        },
    },
}

SINGLE_QUESTIONS: Dict[str, Dict[str, Any]] = {
    "G01": {
        "question_id": "q_g01",
        "question_text": "האם האדם נושם ומגיב?",
        "options": ["כן, נושם ומגיב", "לא, אינו נושם ואינו מגיב", "לא בטוח/ה"],
        "candidates": ["G01"],
        "answer_text_map": {"0": "האדם נושם ומגיב יש דופק", "1": "אין נשימה אין תגובה אין דופק", "2": ""},
    },
    "G02": {
        "question_id": "q_g02",
        "question_text": "האם הכאב בחזה מקרין לזרוע שמאל, לכתף, או ללסת?",
        "options": ["כן, יש הקרנה", "לא, הכאב מקומי", "לא בטוח/ה"],
        "candidates": ["G02"],
        "answer_text_map": {"0": "כאב מקרין לזרוע שמאל ולסת", "1": "", "2": ""},
    },
    "G03": {
        "question_id": "q_g03",
        "question_text": "האם יש חולשה בצד אחד של הגוף, קושי בדיבור, או עיוות פנים?",
        "options": ["כן, יש סימנים אלו", "לא, אין סימנים אלו", "לא בטוח/ה"],
        "candidates": ["G03"],
        "answer_text_map": {"0": "חולשה בצד אחד קושי בדיבור עיוות פנים", "1": "", "2": ""},
    },
    "G04": {
        "question_id": "q_g04",
        "question_text": "האם האדם מצליח לנשום, להשתעל, או לדבר?",
        "options": ["כן, מצליח לנשום", "לא, לא מצליח לנשום", "לא בטוח/ה"],
        "candidates": ["G04"],
        "answer_text_map": {"0": "האדם נושם חלקית חסימה חלקית", "1": "חסימה מלאה בדרכי הנשימה אין נשימה", "2": ""},
    },
    "G05": {
        "question_id": "q_g05",
        "question_text": "האם הדימום אינו נעצר לאחר לחיצה ישירה?",
        "options": ["כן, הדימום לא נעצר", "לא, הדימום האט", "לא בטוח/ה"],
        "candidates": ["G05"],
        "answer_text_map": {"0": "דימום מסיבי לא נעצר לאחר לחיצה", "1": "", "2": ""},
    },
    "G06": {
        "question_id": "q_g06",
        "question_text": "האם היו פרכוסים או תנועות בלתי רצוניות?",
        "options": ["כן, היו פרכוסים", "לא, לא היו פרכוסים", "לא בטוח/ה"],
        "candidates": ["G06"],
        "answer_text_map": {"0": "פרכוסים ותנועות בלתי רצוניות", "1": "", "2": ""},
    },
}


def should_ask_clarification(confidence_value: float, margin: float, best_score: float) -> bool:
    if confidence_value >= CONFIDENCE_THRESHOLD:
        return False
    return True


def get_clarification_question(top_code: str, second_code: str) -> Optional[Dict[str, Any]]:
    pair_key = frozenset({top_code, second_code})
    if pair_key in PAIR_QUESTIONS:
        return PAIR_QUESTIONS[pair_key]
    return SINGLE_QUESTIONS.get(top_code)


def get_question_by_id(question_id: str) -> Optional[Dict[str, Any]]:
    for q in PAIR_QUESTIONS.values():
        if q["question_id"] == question_id:
            return q
    for q in SINGLE_QUESTIONS.values():
        if q["question_id"] == question_id:
            return q
    return None


def augment_text_with_answer(original_text: str, question_id: str, answer_index: str) -> str:
    question = get_question_by_id(question_id)
    if not question:
        return original_text
    additional = question["answer_text_map"].get(str(answer_index), "")
    if not additional:
        return original_text
    return f"{original_text} {additional}".strip()
