# ResQme Backend, Simple Runtime Package

This package is intentionally flat and minimal. It contains only the files needed to run the working backend logic and connect it to a frontend.

## File map

```text
main.py                    FastAPI server for the frontend
dss_adapter.py             Converts DSS output to frontend-ready JSON
stt_adapter.py             Runs STT and cleans the transcript
schemas.py                 API request and response models

dss_engine.py              DSS decision engine
excel_dss_loader.py        Loads rules, phrases, tests, and guidelines from dss.xlsx
flutterflow_formatter.py   Optional formatter from the older FlutterFlow flow
whisper_hebrew.py          Hebrew Whisper STT wrapper
text_cleaning_hebrew.py    Hebrew transcript cleaning

dss.xlsx                   Required DSS knowledge base
sample_audio_01.mp3        Sample audio for STT testing

test_dss.py                Tests the DSS using test cases inside dss.xlsx
test_text_flow.py          Tests direct text input through the backend adapter
test_stt.py                Tests STT only
test_stt_to_dss.py         Tests STT then DSS
```

## What matters for integration

The frontend must not read `dss.xlsx` directly.

The frontend should call the API in `main.py`.

Runtime flow:

```text
Frontend text/audio input
↓
main.py
↓
dss_adapter.py or stt_adapter.py
↓
dss_engine.py
↓
excel_dss_loader.py
↓
dss.xlsx
↓
JSON response to frontend
```

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run API

```bash
uvicorn main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

## Test text analysis

```bash
python test_text_flow.py
```

Expected examples:

```text
G01 | דום לב
G02 | התקף לב
G03 | שבץ מוחי
```

## Test DSS from Excel

```bash
python test_dss.py
```

Expected result:

```text
Passed: 15/15
```

## Test STT only

```bash
python test_stt.py --audio sample_audio_01.mp3
```

STT requires `faster-whisper`. The first run may download the Whisper model.

## Test STT then DSS

```bash
python test_stt_to_dss.py --audio sample_audio_01.mp3
```

## API endpoints

### Health

```http
GET /health
```

### Text analysis

```http
POST /analyze-text
```

Body:

```json
{
  "text": "הוא לא מגיב ולא נושם"
}
```

### Audio analysis

```http
POST /analyze-audio
```

Form-data:

```text
file=<audio file>
```

## Response shape

```json
{
  "input_type": "text",
  "transcript": "הוא לא מגיב ולא נושם",
  "case_id": "G01",
  "condition": "דום לב",
  "urgency": "critical",
  "confidence": 0.9,
  "status": "classified",
  "needs_clarification": false,
  "clarifying_question": null,
  "instructions": [],
  "warnings": [],
  "matched_symptoms": [],
  "alternative_conditions": []
}
```

## Important technical note

`dss.xlsx` is required at runtime, but it is not the engine by itself. It is the knowledge base. The actual engine is `dss_engine.py` plus `excel_dss_loader.py`.
