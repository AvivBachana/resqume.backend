from dss_adapter import analyze_emergency_text


SAMPLES = [
    "הוא לא מגיב ולא נושם",
    "יש לו כאב חזק בחזה וקוצר נשימה",
    "הפנים עקומות ויד אחת חלשה",
]


def main() -> None:
    for text in SAMPLES:
        result = analyze_emergency_text(text)
        print(f"{result['case_id']} | {result['condition']} | confidence={result['confidence']} | text={text}")


if __name__ == "__main__":
    main()
