import argparse
import json
from datetime import datetime
from pathlib import Path

from text_cleaning_hebrew import clean_hebrew_transcript
from whisper_hebrew import HebrewWhisperSTT


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Hebrew STT only.")
    parser.add_argument("--audio", default="sample_audio_01.mp3")
    parser.add_argument("--model-size", default="small")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--compute-type", default="int8")
    args = parser.parse_args()

    stt = HebrewWhisperSTT(
        model_size=args.model_size,
        device=args.device,
        compute_type=args.compute_type,
    )
    raw_result = stt.transcribe_audio(args.audio)
    cleaned_text = clean_hebrew_transcript(raw_result["text"])

    final_result = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "audio_path": raw_result["audio_path"],
        "raw_text": raw_result["text"],
        "cleaned_text": cleaned_text,
        "segments": raw_result["segments"],
    }

    Path("outputs_stt_result.json").write_text(
        json.dumps(final_result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("Raw transcript:")
    print(raw_result["text"])
    print("\nCleaned transcript:")
    print(cleaned_text)


if __name__ == "__main__":
    main()
