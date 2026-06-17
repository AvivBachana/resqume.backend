from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional

from rapidfuzz import fuzz

from excel_dss_loader import (
    DSSKnowledgeBase,
    PhraseRule,
    load_dss_knowledge_base,
)

DEFAULT_DSS_PATH = Path(__file__).resolve().with_name("dss.xlsx")

MIN_DECISION_SCORE = 3.0
MIN_DECISION_MARGIN = 1.0

FUZZY_MATCH_THRESHOLD = 82
FUZZY_SHORT_PHRASE_THRESHOLD = 90
PHONETIC_MATCH_THRESHOLD = 88
MIN_FUZZY_PHRASE_LENGTH = 4

MIN_FUZZY_LENGTH_RATIO = 0.60
MIN_PARTIAL_LENGTH_RATIO = 0.80
MIN_MULTIWORD_FIRST_TOKEN_SIMILARITY = 60
NEGATION_TERMS = (
    "אין",
    "אינ",
    "לא",
    "ללא",
    "בלי",
    "אינו",
    "אינה",
    "אינם",
    "אינן",
    "ואין",
    "ואינ",
    "ולא",
    "וללא",
    "ובלי",
)

NEGATION_WINDOW_CHARS = 18


@dataclass(frozen=True)
class PhraseMatch:
    phrase_id: str
    phrase_text: str
    matched_text: str
    match_type: str
    similarity: int
    parameter: str
    value: str
    priority: int
    start: int
    end: int
    clinical_meaning: str
    condition_hint: str


@dataclass(frozen=True)
class DSSDecision:
    input_text: str
    normalized_text: str
    decision_code: str
    decision_name: str
    confidence: str
    best_score: float
    second_score: float
    margin: float
    parameters: Dict[str, str]
    scores: Dict[str, float]
    matched_phrases: List[PhraseMatch]
    instructions: List[str]
    forbidden_action: str

    def to_dict(self) -> dict:
        data = asdict(self)
        data["matched_phrases"] = [asdict(item) for item in self.matched_phrases]
        return data


def normalize_hebrew_text(text: str) -> str:
    text = text or ""

    # Remove Hebrew diacritics.
    text = re.sub(r"[\u0591-\u05C7]", "", text)

    # Normalize final Hebrew letters.
    final_letter_map = str.maketrans({
        "ך": "כ",
        "ם": "מ",
        "ן": "נ",
        "ף": "פ",
        "ץ": "צ",
    })
    text = text.translate(final_letter_map)

    # Remove punctuation.
    text = re.sub(r"[\"'.,!?;:()\[\]{}<>/\\|\-–—]", " ", text)

    # Normalize whitespace.
    text = re.sub(r"\s+", " ", text).strip()

    return text


def hebrew_phonetic_key(text: str) -> str:
    text = normalize_hebrew_text(text)

    phonetic_map = str.maketrans({
        "א": "א",
        "ע": "א",
        "ה": "א",

        "ב": "ב",
        "ו": "ב",
        "פ": "ב",

        "כ": "כ",
        "ק": "כ",
        "ח": "כ",

        "ס": "ס",
        "ש": "ס",
        "צ": "ס",

        "ט": "ט",
        "ת": "ט",

        "ג": "ג",
        "ד": "ד",
        "ז": "ז",
        "י": "י",
        "ל": "ל",
        "מ": "מ",
        "נ": "נ",
        "ר": "ר",
    })

    return text.translate(phonetic_map)


def _strip_hebrew_prefix_vav(token: str) -> str:
    if token.startswith("ו") and len(token) > 1:
        return token[1:]
    return token


def _normalize_negation_token(token: str) -> str:
    token = _strip_hebrew_prefix_vav(token)
    return token


def _phrase_starts_with_negation(phrase: str) -> bool:
    words = phrase.split()

    if not words:
        return False

    first_word = _normalize_negation_token(words[0])
    return first_word in NEGATION_TERMS


def _phrase_contains_internal_clinical_negation(phrase: str) -> bool:
    clinical_negative_patterns = (
        "לא ברור",
        "לא ברורות",
        "לא ברורה",
        "לא מובן",
        "לא קוהרנטי",
        "לא רציף",
        "לא תקין",
        "לא סדיר",
        "לא סדירות",
        "לא סימטרי",
        "לא סימטריות",
        "לא שוות",
        "לא שווה",
        "לא זז",
        "לא עולה",
        "לא מתפקד",
        "לא מתפקדת",
        "לא מפסיק",
        "לא נעצר",
        "לא יעיל",
        "לא רצוניות",
    )

    return any(pattern in phrase for pattern in clinical_negative_patterns)


def _is_negated_context(text: str, start_index: int, phrase: str) -> bool:
    # If the phrase itself starts with negation, it is a valid clinical phrase.
    if _phrase_starts_with_negation(phrase):
        return False

    # If negation is part of a known clinical phrase, do not block it.
    if _phrase_contains_internal_clinical_negation(phrase):
        return False

    left_context = text[max(0, start_index - NEGATION_WINDOW_CHARS):start_index].strip()

    if not left_context:
        return False

    tokens = left_context.split()

    if not tokens:
        return False

    last_token = _normalize_negation_token(tokens[-1])

    # Block only direct negation immediately before the phrase.
    if last_token in NEGATION_TERMS:
        return True

    if len(tokens) >= 2:
        previous_token = _normalize_negation_token(tokens[-2])
        current_token = _normalize_negation_token(tokens[-1])

        immediate_negation_patterns = {
            ("אין", "לו"),
            ("אין", "לה"),
            ("אין", "להם"),
            ("אין", "להן"),
            ("לא", "רואים"),
            ("לא", "רואה"),
            ("לא", "מרגישים"),
            ("לא", "מרגיש"),
            ("לא", "מרגישה"),
            ("לא", "שומעים"),
            ("לא", "שומע"),
            ("לא", "שומעת"),
        }

        if (previous_token, current_token) in immediate_negation_patterns:
            return True

    return False


def _get_fuzzy_threshold(phrase: str) -> int:
    if len(phrase) <= MIN_FUZZY_PHRASE_LENGTH:
        return FUZZY_SHORT_PHRASE_THRESHOLD

    return FUZZY_MATCH_THRESHOLD


def _build_word_spans(text: str) -> List[tuple[str, int, int]]:
    return [
        (match.group(0), match.start(), match.end())
        for match in re.finditer(r"\S+", text)
    ]


def _iter_candidate_spans(text: str, phrase: str) -> List[tuple[str, int, int]]:
    word_spans = _build_word_spans(text)
    phrase_word_count = len(phrase.split())

    if phrase_word_count == 0:
        return []

    candidates: List[tuple[str, int, int]] = []
    window_sizes = {
        phrase_word_count - 1,
        phrase_word_count,
        phrase_word_count + 1,
    }

    for window_size in sorted(window_sizes):
        if window_size <= 0:
            continue

        for start_word_index in range(0, len(word_spans) - window_size + 1):
            selected_word_spans = word_spans[start_word_index:start_word_index + window_size]

            candidate_text = " ".join(item[0] for item in selected_word_spans)
            start_char = selected_word_spans[0][1]
            end_char = selected_word_spans[-1][2]

            candidates.append((candidate_text, start_char, end_char))

    return candidates

def _is_safe_fuzzy_candidate(candidate_text: str, phrase: str) -> bool:
    candidate_words = candidate_text.split()
    phrase_words = phrase.split()

    if not candidate_words or not phrase_words:
        return False

    length_ratio = min(len(candidate_text), len(phrase)) / max(len(candidate_text), len(phrase))
    if length_ratio < MIN_FUZZY_LENGTH_RATIO:
        return False

    # A single short word must not activate a multi-word clinical phrase.
    if len(phrase_words) >= 2 and len(candidate_words) == 1:
        return False

    # For multi-word phrases with the same word count, the first content-bearing
    # token must also be reasonably similar. This blocks matches such as
    # "עצירת נשימה" -> "קוצר נשימה" that only share a generic final token.
    if len(phrase_words) >= 2 and len(candidate_words) == len(phrase_words):
        first_candidate = _strip_hebrew_prefix_vav(candidate_words[0])
        first_phrase = _strip_hebrew_prefix_vav(phrase_words[0])

        if fuzz.ratio(first_candidate, first_phrase) < MIN_MULTIWORD_FIRST_TOKEN_SIMILARITY:
            return False

    return True


def _can_use_partial_ratio(candidate_text: str, phrase: str) -> bool:
    candidate_words = candidate_text.split()
    phrase_words = phrase.split()

    if len(candidate_words) != len(phrase_words):
        return False

    length_ratio = min(len(candidate_text), len(phrase)) / max(len(candidate_text), len(phrase))
    return length_ratio >= MIN_PARTIAL_LENGTH_RATIO

def _deduplicate_matches(matches: List[PhraseMatch]) -> List[PhraseMatch]:
    best_by_key: Dict[tuple[str, str, int, int], PhraseMatch] = {}

    for match in matches:
        key = (match.phrase_id, match.parameter, match.start, match.end)
        current = best_by_key.get(key)

        if current is None:
            best_by_key[key] = match
            continue

        current_rank = (
            current.similarity,
            current.priority,
            len(current.matched_text),
        )

        candidate_rank = (
            match.similarity,
            match.priority,
            len(match.matched_text),
        )

        if candidate_rank > current_rank:
            best_by_key[key] = match

    deduplicated = list(best_by_key.values())
    deduplicated.sort(key=lambda item: (item.start, -item.similarity, -item.priority))
    return deduplicated


def _create_phrase_match(
    phrase: PhraseRule,
    matched_text: str,
    match_type: str,
    similarity: int,
    start: int,
    end: int,
) -> PhraseMatch:
    return PhraseMatch(
        phrase_id=phrase.phrase_id,
        phrase_text=phrase.phrase_text,
        matched_text=matched_text,
        match_type=match_type,
        similarity=similarity,
        parameter=phrase.parameter,
        value=phrase.value,
        priority=phrase.priority,
        start=start,
        end=end,
        clinical_meaning=phrase.clinical_meaning,
        condition_hint=phrase.condition_hint,
    )


def _find_phrase_matches(text: str, phrases: List[PhraseRule]) -> List[PhraseMatch]:
    matches: List[PhraseMatch] = []

    sorted_phrases = sorted(
        phrases,
        key=lambda item: (len(item.phrase_text), item.priority),
        reverse=True,
    )

    for phrase in sorted_phrases:
        normalized_phrase = normalize_hebrew_text(phrase.phrase_text)

        if not normalized_phrase:
            continue

        exact_pattern = re.compile(rf"(?<!\S)(?:ו)?{re.escape(normalized_phrase)}(?!\S)")

        for match in exact_pattern.finditer(text):
            if phrase.negation_sensitive and _is_negated_context(
                text=text,
                start_index=match.start(),
                phrase=normalized_phrase,
            ):
                continue

            matches.append(
                _create_phrase_match(
                    phrase=phrase,
                    matched_text=match.group(0),
                    match_type="exact",
                    similarity=100,
                    start=match.start(),
                    end=match.end(),
                )
            )

        fuzzy_threshold = _get_fuzzy_threshold(normalized_phrase)
        normalized_phrase_phonetic = hebrew_phonetic_key(normalized_phrase)

        for candidate_text, start_char, end_char in _iter_candidate_spans(text, normalized_phrase):
            if candidate_text == normalized_phrase:
                continue

            if phrase.negation_sensitive and _is_negated_context(
                text=text,
                start_index=start_char,
                phrase=normalized_phrase,
            ):
                continue
            if not _is_safe_fuzzy_candidate(candidate_text, normalized_phrase):
                continue

            fuzzy_similarity = int(fuzz.ratio(candidate_text, normalized_phrase))
            token_similarity = int(fuzz.token_sort_ratio(candidate_text, normalized_phrase))

            similarities = [fuzzy_similarity, token_similarity]
            if _can_use_partial_ratio(candidate_text, normalized_phrase):
                similarities.append(int(fuzz.partial_ratio(candidate_text, normalized_phrase)))

            best_fuzzy_similarity = max(similarities)

            if best_fuzzy_similarity >= fuzzy_threshold:
                matches.append(
                    _create_phrase_match(
                        phrase=phrase,
                        matched_text=candidate_text,
                        match_type="fuzzy",
                        similarity=best_fuzzy_similarity,
                        start=start_char,
                        end=end_char,
                    )
                )
                continue

            candidate_phonetic = hebrew_phonetic_key(candidate_text)
            phonetic_similarity = int(fuzz.ratio(candidate_phonetic, normalized_phrase_phonetic))

            if phonetic_similarity >= PHONETIC_MATCH_THRESHOLD:
                matches.append(
                    _create_phrase_match(
                        phrase=phrase,
                        matched_text=candidate_text,
                        match_type="phonetic",
                        similarity=phonetic_similarity,
                        start=start_char,
                        end=end_char,
                    )
                )

    return _deduplicate_matches(matches)


def _select_parameter_values(matches: List[PhraseMatch]) -> Dict[str, str]:
    selected: Dict[str, PhraseMatch] = {}

    for match in matches:
        current = selected.get(match.parameter)

        if current is None:
            selected[match.parameter] = match
            continue

        current_rank = (
            current.priority,
            current.similarity,
            len(current.phrase_text),
            -current.start,
        )

        candidate_rank = (
            match.priority,
            match.similarity,
            len(match.phrase_text),
            -match.start,
        )

        if candidate_rank > current_rank:
            selected[match.parameter] = match

    return {parameter: match.value for parameter, match in selected.items()}


def _score_conditions(kb: DSSKnowledgeBase, parameters: Dict[str, str]) -> Dict[str, float]:
    scores: Dict[str, float] = {}

    for rule in kb.rules:
        scores.setdefault(rule.condition_code, 0.0)

        if parameters.get(rule.parameter) == rule.expected_value:
            scores[rule.condition_code] += rule.weight

    return scores


def _get_condition_names(kb: DSSKnowledgeBase) -> Dict[str, str]:
    names: Dict[str, str] = {}

    for rule in kb.rules:
        names[rule.condition_code] = rule.condition_name

    for code, guideline in kb.guidelines.items():
        names[code] = guideline.condition_name

    return names


def _classify_confidence(best_score: float, margin: float) -> str:
    if best_score < MIN_DECISION_SCORE:
        return "uncertain"

    if margin < MIN_DECISION_MARGIN:
        return "low"

    if best_score >= 7 and margin >= 2:
        return "high"

    return "medium"


def _select_decision(
    kb: DSSKnowledgeBase,
    scores: Dict[str, float],
) -> tuple[str, str, float, float, float, str]:
    names = _get_condition_names(kb)
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)

    if not ranked:
        return "UNCERTAIN", "לא ודאי", 0.0, 0.0, 0.0, "uncertain"

    best_code, best_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0
    margin = best_score - second_score
    confidence = _classify_confidence(best_score, margin)

    if confidence == "uncertain":
        return "UNCERTAIN", "לא ודאי", best_score, second_score, margin, confidence

    return best_code, names.get(best_code, best_code), best_score, second_score, margin, confidence


def run_dss(
    text: str,
    excel_path: str | Path = DEFAULT_DSS_PATH,
    kb: Optional[DSSKnowledgeBase] = None,
) -> DSSDecision:
    kb = kb or load_dss_knowledge_base(excel_path)

    normalized_text = normalize_hebrew_text(text)
    matches = _find_phrase_matches(normalized_text, kb.phrases)
    parameters = _select_parameter_values(matches)
    scores = _score_conditions(kb, parameters)

    decision_code, decision_name, best_score, second_score, margin, confidence = _select_decision(
        kb=kb,
        scores=scores,
    )

    guideline = kb.guidelines.get(decision_code)

    if guideline:
        instructions = guideline.instructions
        forbidden_action = guideline.forbidden_action
    else:
        instructions = [
            "לא התקבלה הכרעה מספקת. יש לאסוף מידע נוסף או לפנות למד״א 101 במקרה חירום."
        ]
        forbidden_action = "אין להציג הנחיה רפואית ספציפית כאשר הסיווג אינו ודאי."

    return DSSDecision(
        input_text=text,
        normalized_text=normalized_text,
        decision_code=decision_code,
        decision_name=decision_name,
        confidence=confidence,
        best_score=best_score,
        second_score=second_score,
        margin=margin,
        parameters=parameters,
        scores=scores,
        matched_phrases=matches,
        instructions=instructions,
        forbidden_action=forbidden_action,
    )