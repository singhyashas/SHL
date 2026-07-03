# Conversational SHL Assessment Recommender

FastAPI service for a stateless conversational recommender over the SHL
Individual Test Solutions catalog.

## Features

- `GET /health` readiness endpoint
- `POST /chat` endpoint with the exact assignment response schema
- catalog-only recommendations with names, URLs, and test type codes
- clarification for vague requests
- refinement from full stateless conversation history
- grounded comparison of named SHL assessments
- refusals for off-topic requests, prompt injection, legal/compliance advice,
  general hiring advice, and non-SHL product comparisons
- local replay harness with Recall@10 reporting

## Project Structure

```text
app/
  main.py          FastAPI routes
  schemas.py       request/response models
  agent.py         conversation behavior
  retriever.py     BM25-style ranking
  comparator.py    catalog-grounded comparisons
  guardrails.py    refusal logic
  catalog.py       catalog loader
data/
  catalog.json       normalized catalog
  catalog_meta.json  catalog build summary
evaluation/
  replay.py          trace replay runner
  metrics.py         Recall@K helpers
scripts/
  build_catalog.py   raw-to-normalized catalog build
tests/
```

## Setup

```bash
pip install -r requirements.txt
```

Rebuild the normalized catalog if the raw pasted file changes:

```bash
python scripts/build_catalog.py
```

Run the API locally:

```bash
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/health
```

## API

Health:

```http
GET /health
```

Response:

```json
{"status": "ok"}
```

Chat:

```http
POST /chat
```

Request:

```json
{
  "messages": [
    {
      "role": "user",
      "content": "Hiring a Java developer who works with stakeholders"
    }
  ]
}
```

Response:

```json
{
  "reply": "Here are 10 SHL catalog assessments that fit the request.",
  "recommendations": [
    {
      "name": "Java 8 (New)",
      "url": "https://www.shl.com/products/product-catalog/view/java-8-new/",
      "test_type": "K"
    }
  ],
  "end_of_conversation": true
}
```

`recommendations` is empty when the agent is clarifying, comparing, or refusing.

## Evaluation

Run all tests:

```bash
python -m pytest
```

Replay local labeled traces:

```bash
python -m evaluation.replay
```

The replay output includes hard checks, per-trace Recall@10, and mean Recall@10.

## Deployment

The app can be deployed on Render, Railway, Fly, or similar Python web hosts.

Generic start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Render configuration is included in `render.yaml`. `Procfile` is included for
platforms that use Heroku-style process declarations.
