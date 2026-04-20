# Testing Guide

This project includes:

- Unit tests (`pytest`)
- Integration tests (`pytest` + Django DB)
- Performance tests (`locust`)
- E2E tests (`playwright`)
- Security scanning (`gitleaks` in pre-commit and CI)

## 1) CI/CD Pipeline

Workflow file: `.github/workflows/ci.yml`

Pipeline stages:

1. Secret scanning (GitLeaks)
2. Unit tests
3. Integration tests
4. Performance tests (Locust headless + artifact upload)
5. E2E smoke tests (Playwright, `@smoke`)
6. Build/deploy placeholder
7. Code quality/security checks

## 2) Unit Tests

```bash
python -m pytest apps/tests/test_unit.py -v
python -m pytest apps/tests/test_unit.py --cov=apps --cov=core --cov-report=term
```

## 3) Integration Tests

```bash
python manage.py migrate --settings=ci_settings
python -m pytest apps/tests/test_integration.py -v
```

## 4) Performance Tests

Test definition:

- `tests/performance/locustfile.py`

Run locally:

```bash
python -m locust -f tests/performance/locustfile.py --headless -u 10 -r 2 -t 45s --host http://127.0.0.1:8000 --exit-code-on-error 0
```

Latest measured results:

- `tests/performance/ACTUAL_TEST_RESULTS.md`

## 5) E2E Tests (Playwright)

Test files:

- `frontend/e2e/*.spec.ts`

Install and run:

```bash
cd frontend
npm ci --include=dev
npx playwright install chromium
npm run test:e2e
```

CI smoke profile (required minimal scenario):

```bash
npm run test:e2e -- --grep @smoke
```

## 6) Security Check

Pre-commit config:

- `.pre-commit-config.yaml` (includes `gitleaks`)

Install hooks:

```bash
pre-commit install
pre-commit run --all-files
```
