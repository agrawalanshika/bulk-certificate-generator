# Bulk Certificate Generator

FastAPI backend that accepts a bulk list of recipients and generates certificates (PDF) from a predefined template, with job/status tracking.

> Work in progress — built phase by phase. Full documentation arrives in Phase 10.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # Windows: copy .env.example .env
```

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

- Health: http://localhost:8000/health
- Swagger: http://localhost:8000/docs

## Tests

```bash
pytest -v
```
