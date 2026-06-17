import argparse

from dss_adapter import analyze_emergency_text
from stt_adapter import transcribe_audio


def main() -> None:
    parser = argparse.ArgumentParser(description="Run STT and then DSS.")
    parser.add_argument("--audio", default="sample_audio_01.mp3")
    args = parser.parse_args()

    stt_result = transcribe_audio(args.audio)
    transcript = stt_result["cleaned_text"]
    dss_result = analyze_emergency_text(transcript)

    print("Transcript:")
    print(transcript)
    print("\nDSS result:")
    print(f"{dss_result['case_id']} | {dss_result['condition']} | confidence={dss_result['confidence']}")


if __name__ == "__main__":
    main()
