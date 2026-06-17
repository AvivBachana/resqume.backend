# Copilot brief for connecting the frontend to this backend

Use this folder as the backend source of truth. Do not restructure it unless there is a clear runtime bug.

## Goal

Connect the frontend to the Python backend through HTTP API calls.

## Do not do

- Do not make the frontend read `dss.xlsx` directly.
- Do not rewrite the DSS logic.
- Do not add data-generation scripts.
- Do not add TTS.
- Do not create nested `src/resqme/...` folders again.
- Do not hardcode medical results in the frontend.

## Correct backend commands

Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run backend:

```bash
uvicorn main:app --reload
```

Test backend logic:

```bash
python test_text_flow.py
python test_dss.py
```

## Frontend integration contract

For typed text, send:

```http
POST http://127.0.0.1:8000/analyze-text
Content-Type: application/json
```

```json
{
  "text": "הוא לא מגיב ולא נושם"
}
```

For audio, send multipart form-data:

```http
POST http://127.0.0.1:8000/analyze-audio
```

with field name:

```text
file
```

## Prompt to give Copilot

```text
You are connecting an existing frontend to a Python FastAPI backend.
Use the backend in this folder as the source of truth.
Do not restructure the backend.
Do not rewrite the DSS engine.
The frontend must call POST /analyze-text for typed text and POST /analyze-audio for audio files.
Bind the JSON response fields to the result screen: case_id, condition, urgency, confidence, instructions, warnings, matched_symptoms, and alternative_conditions.
Keep the backend runtime minimal and do not add data generation, TTS, or extra folders.
```
