from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import pandas as pd


@dataclass(frozen=True)
class PhraseRule:
    phrase_id: str
    phrase_text: str
    parameter: str
    value: str
    priority: int
    negation_sensitive: bool
    clinical_meaning: str
    condition_hint: str


@dataclass(frozen=True)
class DecisionRule:
    condition_code: str
    condition_name: str
    parameter: str
    expected_value: str
    weight: float


@dataclass(frozen=True)
class Guideline:
    condition_code: str
    condition_name: str
    instructions: List[str]
    forbidden_action: str


@dataclass(frozen=True)
class DSSKnowledgeBase:
    phrases: List[PhraseRule]
    rules: List[DecisionRule]
    guidelines: Dict[str, Guideline]
    test_cases: pd.DataFrame


def _clean_cell(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _as_bool_hebrew(value: object) -> bool:
    normalized = _clean_cell(value).lower()
    return normalized in {"כן", "true", "1", "yes", "y"}


def _as_int(value: object, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _as_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def load_dss_knowledge_base(excel_path: str | Path) -> DSSKnowledgeBase:
    excel_path = Path(excel_path)

    if not excel_path.exists():
        raise FileNotFoundError(f"DSS Excel file was not found: {excel_path}")

    dictionary_df = pd.read_excel(excel_path, sheet_name="03_מילון", engine="openpyxl")
    rules_df = pd.read_excel(excel_path, sheet_name="04_חוקים", engine="openpyxl")
    guidelines_df = pd.read_excel(excel_path, sheet_name="06_הנחיות", engine="openpyxl")
    test_cases_df = pd.read_excel(excel_path, sheet_name="07_בדיקות", engine="openpyxl")

    phrases: List[PhraseRule] = []
    for _, row in dictionary_df.iterrows():
        phrase_text = _clean_cell(row.get("PhraseText"))
        parameter = _clean_cell(row.get("MappedParameter"))
        value = _clean_cell(row.get("MappedValue"))

        if not phrase_text or not parameter or not value:
            continue

        phrases.append(
            PhraseRule(
                phrase_id=_clean_cell(row.get("PhraseID")),
                phrase_text=phrase_text,
                parameter=parameter,
                value=value,
                priority=_as_int(row.get("Priority")),
                negation_sensitive=_as_bool_hebrew(row.get("NegationSensitive")),
                clinical_meaning=_clean_cell(row.get("ClinicalMeaning")),
                condition_hint=_clean_cell(row.get("ConditionHint")),
            )
        )

    rules: List[DecisionRule] = []
    for _, row in rules_df.iterrows():
        condition_code = _clean_cell(row.get("ConditionCode"))
        condition_name = _clean_cell(row.get("ConditionName"))
        parameter = _clean_cell(row.get("Parameter"))
        expected_value = _clean_cell(row.get("ExpectedValue"))

        if not condition_code or not parameter or not expected_value:
            continue

        rules.append(
            DecisionRule(
                condition_code=condition_code,
                condition_name=condition_name,
                parameter=parameter,
                expected_value=expected_value,
                weight=_as_float(row.get("Weight")),
            )
        )

    guidelines: Dict[str, Guideline] = {}
    for _, row in guidelines_df.iterrows():
        condition_code = _clean_cell(row.get("ConditionCode"))

        if not condition_code:
            continue

        instructions = [
            _clean_cell(row.get("Instruction1")),
            _clean_cell(row.get("Instruction2")),
            _clean_cell(row.get("Instruction3")),
        ]

        guidelines[condition_code] = Guideline(
            condition_code=condition_code,
            condition_name=_clean_cell(row.get("ConditionName")),
            instructions=[item for item in instructions if item],
            forbidden_action=_clean_cell(row.get("ForbiddenAction")),
        )

    return DSSKnowledgeBase(
        phrases=phrases,
        rules=rules,
        guidelines=guidelines,
        test_cases=test_cases_df,
    )