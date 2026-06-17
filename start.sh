#!/bin/bash
cd "$(dirname "$0")"
KMP_DUPLICATE_LIB_OK=TRUE python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
