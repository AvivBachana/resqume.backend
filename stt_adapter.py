from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from text_cleaning_hebrew import clean_hebrew_transcript
from whisper_hebrew import HebrewWhisperSTT

_STT_MODEL: HebrewWhisperSTT | None = None


def _get_stt_model() -> HebrewWhisperSTT:
    global _STT_MODEL
    if _STT_MODEL is None:
        _STT_MODEL = HebrewWhisperSTT(model_size="medium", device="cpu", compute_type="int8")
    return _STT_MODEL


def transcribe_audio(file_path: str | Path) -> Dict[str, Any]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file was not found: {path}")

    result = _get_stt_model().transcribe_audio(path)
    raw_text = str(result.get("text", "")).strip()
    cleaned_text = clean_hebrew_transcript(raw_text)

    return {
        "raw_text": raw_text,
        "cleaned_text": cleaned_text,
        "metadata": result,
    }
