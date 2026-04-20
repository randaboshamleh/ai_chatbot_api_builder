# E2E Testing with Playwright

## Overview

This folder contains real end-to-end tests for the running system:
- Frontend UI on `http://127.0.0.1:5173`
- Backend API on `http://127.0.0.1:8000`

Tests create their own users and data so they do not depend on manual setup.

## What is covered

- `auth.spec.ts`: register, login, invalid login, logout
- `user-journey.spec.ts`: full flow (register -> upload document -> navigate -> logout)
- `documents.spec.ts`: upload/list/delete documents
- `chat.spec.ts`: chat page behavior with/without indexed docs
- `analytics.spec.ts`: analytics page rendering
- `channels.spec.ts`: channel forms rendering
- `settings.spec.ts`: view-only account/organization data
- `language.spec.ts`: language toggle + direction persistence

## Prerequisites

```bash
# from project root
python manage.py migrate
python manage.py runserver 127.0.0.1:8000

# in another terminal
cd frontend
npm ci
npx playwright install chromium
```

## Run tests

```bash
cd frontend
npm run test:e2e
```

### Useful commands

```bash
npm run test:e2e:headed
npm run test:e2e:ui
npx playwright test e2e/auth.spec.ts
npm run test:e2e:report
```

## Stability notes

- Tests use `data-testid` selectors for critical UI controls.
- Tests create unique users per run via API.
- Only Chromium project is enabled for reliable CI execution.

## CI

GitHub Actions E2E job now:
1. Starts Django backend
2. Runs Playwright tests against real API
3. Uploads HTML report + test artifacts
