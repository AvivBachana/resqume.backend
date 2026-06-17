from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from clarification import augment_text_with_answer
from dss_adapter import analyze_emergency_text
from schemas import AnalyzeResponse, AnalyzeTextRequest, ClarifyRequest
from stt_adapter import transcribe_audio
import logging

app = FastAPI(title="ResQme Backend API", version="0.1.0")

# Simple request/response logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("resqme_backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "service": "ResQme Backend API"}


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze-text", response_model=AnalyzeResponse)
def analyze_text(request: AnalyzeTextRequest) -> AnalyzeResponse:
    logger.info("Incoming POST /analyze-text request: %s", request.text)
    try:
        result = analyze_emergency_text(request.text)
        logger.info("Outgoing /analyze-text response: %s", result)
        return AnalyzeResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Text analysis failed: {exc}") from exc


@app.post("/clarify", response_model=AnalyzeResponse)
def clarify(request: ClarifyRequest) -> AnalyzeResponse:
    logger.info("Incoming POST /clarify question_id=%s answer=%s", request.question_id, request.answer_index)
    try:
        augmented = augment_text_with_answer(request.text, request.question_id, request.answer_index)
        result = analyze_emergency_text(augmented, force_final=True)
        logger.info("Outgoing /clarify response: %s", result)
        return AnalyzeResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Clarification failed: {exc}") from exc


@app.post("/analyze-audio", response_model=AnalyzeResponse)
async def analyze_audio(file: UploadFile = File(...)) -> AnalyzeResponse:
    suffix = Path(file.filename or "audio.wav").suffix or ".wav"
    temp_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(await file.read())

        logger.info("Incoming POST /analyze-audio file: %s", file.filename)
        stt_result = transcribe_audio(temp_path)
        transcript = stt_result["cleaned_text"]

        if not transcript:
            raise ValueError("STT returned an empty transcript.")

        result = analyze_emergency_text(transcript)
        result["input_type"] = "audio"
        result["transcript"] = transcript
        logger.info("Outgoing /analyze-audio response: %s", result)
        return AnalyzeResponse(**result)

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Audio analysis failed: {exc}") from exc
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)
