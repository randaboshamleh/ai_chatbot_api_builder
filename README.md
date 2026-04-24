# AI Chatbot API Builder - Assistify

نظام شات بوت ذكي متعدد المستأجرين مع RAG (Retrieval-Augmented Generation) باستخدام Django و Ollama.

[![CI/CD Pipeline](https://github.com/randaboshamleh/ai_chatbot_api_builder/actions/workflows/ci.yml/badge.svg)](https://github.com/randaboshamleh/ai_chatbot_api_builder/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/tests-75%2B%20passing-brightgreen)](./TESTING.md)
[![Coverage](https://img.shields.io/badge/coverage-80%25-green)](./htmlcov/index.html)
[![Python](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-4.2-green)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/license-MIT-blue)](./LICENSE)

## 👥 Group Members
- Rand Aboshamleh

##  How to Run Tests

### Prerequisites
- Python 3.11
- pip

### Setup
```bash
git clone https://github.com/randaboshamleh/ai_chatbot_api_builder
cd ai_chatbot_api_builder
pip install -r requirements.txt
```

### Run Unit Tests
```bash
pytest apps/tests/test_unit.py -v
```

### Run Integration Tests
```bash
python manage.py migrate --settings=ci_settings
pytest apps/tests/test_integration.py -v
```

### Run Performance Tests
```bash
locust -f tests/performance/locustfile.py
```

## CI/CD Status
![CI Pipeline](https://github.com/randaboshamleh/ai_chatbot_api_builder/actions/workflows/ci.yml/badge.svg)


##  Performance Test Results
**Tool:** Locust | **Users:** 10 | **RPS:** 4.65

| Endpoint | Avg Response Time | Median | Failures |
|---|---|---|---|
| POST Chat Query (RAG) | 115 ms | 6 ms | 0% |
| GET Analytics | 29 ms | 16 ms | 0% |
| GET List Documents | 117 ms | 5 ms | 0% |
| POST Upload Document | 7 ms | 6 ms | 0% |
| **Overall** | **91 ms** | **6 ms** | **0%** |

### Interpretation
-  Zero failures across all endpoints
-  Median response time is excellent (6ms)
-  Max response time reached 5953ms (likely RAG processing overhead)
-  System handles 10 concurrent users with 5 RPS


![Locust](docs/Screenshot%202026-04-20%20193639.png)
![GitHub Actions](docs/Screenshot%202026-04-20%20193733.png)
![Playwright](docs/Screenshot%202026-04-20%20193757.png)
![Playwright](docs/Screenshot%202026-04-20%20193821.png)
![Playwright](docs/Screenshot%202026-04-20%20193839.png)
## Stability Runbook (Prevent 502 Recurrence)

1. Start with health-aware orchestration:
```bash
docker compose up -d
```

2. Verify all core services are healthy before using frontend:
```bash
docker compose ps
```
You should see `api`, `nginx`, `postgres`, and `redis` in `Up`/`healthy` state.

3. Frontend development should target API directly on port `8000` via proxy config:
- `frontend/.env`
  - `VITE_API_BASE_URL=/api/v1`
  - `VITE_API_PROXY_TARGET=http://localhost:8000`

4. Quick smoke test for backend login path:
```bash
curl -X POST http://localhost/api/v1/auth/login/ -H "Content-Type: application/json" -d '{"username":"dummy","password":"dummy"}'
```
Expected: `401` for invalid credentials (this confirms no `502`).

5. If a service is unhealthy, restart only that service (not full rebuild):
```bash
docker compose up -d --force-recreate nginx
```

6. Rebuild images only when dependencies or Dockerfile changed.

## Indexing Performance Tuning

You can tune indexing speed without code changes by setting these environment variables in `.env`:

```env
DOCUMENT_CHUNK_SIZE=1400
DOCUMENT_CHUNK_OVERLAP=100
DOCUMENT_BULK_CREATE_BATCH_SIZE=1000
OLLAMA_EMBED_BATCH_SIZE=24
OLLAMA_EMBED_MAX_WORKERS=1
OLLAMA_EMBED_MAX_CHARS=2400
```

Recommended starting point:
- Keep `DOCUMENT_CHUNK_SIZE` between `1200-1800`
- Keep `DOCUMENT_CHUNK_OVERLAP` between `80-150`
- Increase `OLLAMA_EMBED_BATCH_SIZE` gradually if your machine has enough RAM/CPU

After updating `.env`, restart services:

```bash
docker compose up -d --force-recreate api worker
```

## Query Reliability Tuning

If answers are slow, mixed-language, or pulled from the wrong file, tune these values in `.env`:

```env
RAG_RETRIEVAL_K=6
RAG_ENABLE_KEYWORD_SEARCH=True
RAG_MAX_DETAIL_CHUNKS=3
RAG_ANSWER_MAX_TOKENS=160
RAG_MAX_RESPONSE_SECONDS=75
RAG_SINGLE_DOCUMENT_BIAS=True
RAG_DOCUMENT_CONFIDENCE_MARGIN=0.06
RAG_MIN_ARABIC_ANSWER_RATIO=0.72
TELEGRAM_PROCESSING_MODE=celery
```

Then recreate API + worker to apply:

```bash
docker compose up -d --force-recreate api worker
```
