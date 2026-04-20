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