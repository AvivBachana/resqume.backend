import re


def clean_hebrew_transcript(text: str) -> str:
    # Normalize whitespace.
    text = re.sub(r"\s+", " ", text).strip()

    # Remove punctuation that is not useful for downstream processing.
    text = re.sub(r"[\"'.,!?;:()\[\]{}]", "", text)

    # Normalize whitespace again after punctuation removal.
    text = re.sub(r"\s+", " ", text).strip()

    return text