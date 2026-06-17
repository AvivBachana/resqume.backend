import json
from pathlib import Path

from dss_engine import run_dss
from excel_dss_loader import load_dss_knowledge_base

DSS_PATH = Path(__file__).resolve().with_name("dss.xlsx")
OUTPUT_PATH = Path("outputs_dss_test_results.json")


def main() -> None:
    kb = load_dss_knowledge_base(DSS_PATH)
    results = []

    for _, row in kb.test_cases.iterrows():
        case_id = str(row.get("CaseID", "")).strip()
        input_text = str(row.get("InputText", "")).strip()
        expected = str(row.get("ExpectedCondition", "")).strip()

        if not case_id or not input_text:
            continue

        decision = run_dss(input_text, excel_path=DSS_PATH, kb=kb)
        actual = decision.decision_code

        results.append(
            {
                "case_id": case_id,
                "input_text": input_text,
                "expected": expected,
                "actual": actual,
                "passed": actual == expected,
                "confidence": decision.confidence,
                "best_score": decision.best_score,
                "margin": decision.margin,
                "parameters": decision.parameters,
            }
        )

    OUTPUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    passed_count = sum(item["passed"] for item in results)
    total_count = len(results)

    print(f"Passed: {passed_count}/{total_count}")
    for item in results:
        status = "PASS" if item["passed"] else "FAIL"
        print(
            f"{status} | {item['case_id']} | expected={item['expected']} | "
            f"actual={item['actual']} | text={item['input_text']}"
        )


if __name__ == "__main__":
    main()
