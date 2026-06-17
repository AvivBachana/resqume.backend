from pathlib import Path
from typing import Any, Dict, List

from faster_whisper import WhisperModel


class HebrewWhisperSTT:
    def __init__(
        self,
        model_size: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> None:
        # Load the model once so repeated transcriptions are faster.
        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
        )

    def transcribe_audio(self, audio_path: str | Path) -> Dict[str, Any]:
        audio_path = Path(audio_path)

        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file was not found: {audio_path}")

        segments, info = self.model.transcribe(
            str(audio_path),
            language="he",
            task="transcribe",
            beam_size=5,
            vad_filter=True,
        )

        full_text_parts: List[str] = []
        segment_list: List[Dict[str, Any]] = []

        for segment in segments:
            text = segment.text.strip()

            if text:
                full_text_parts.append(text)

            segment_list.append(
                {
                    "start": float(segment.start),
                    "end": float(segment.end),
                    "text": text,
                }
            )

        return {
            "audio_path": str(audio_path),
            "language": "he",
            "detected_language": getattr(info, "language", None),
            "language_probability": getattr(info, "language_probability", None),
            "duration_seconds": getattr(info, "duration", None),
            "text": " ".join(full_text_parts).strip(),
            "segments": segment_list,
        }