# Local Bootstrap Guide

**Last Updated**: 2026-03-29  
**Operating Mode**: FULL workflow setup with a lightweight orchestrator

This guide is the repo-level bootstrap path for the Agentic Ads Platform. It standardizes the contributor workflow around the existing Python and npm entrypoints already present in the repository instead of forcing a new monorepo toolchain.

## Prerequisites

- Python 3.11 or newer
- Node.js 20 or newer
- npm 10 or newer
- Docker Compose, if you want to run the containerized stack
- Terraform 1.5+, if you are validating the cloud deployment path

Verify the baseline toolchain:

```bash
python3 --version
node --version
npm --version
```

## Canonical Bootstrap

From the repository root:

```bash
npm run bootstrap
```

That command will:

- install the repo-level workflow tooling
- create `platform/venv` if it does not exist
- install the shared Python dependencies used by the agent, feature extraction flow, and dashboard backend
- install scraper and dashboard frontend npm dependencies
- create `platform/.env` from the root [`.env.example`](/Users/monterey/Workspace/Projs/Tasmem/agentic-ads-scraping/.env.example) if it is missing

If you also want the optional Playwright and pytest-bdd E2E surface:

```bash
npm run bootstrap:e2e
```

## Baseline Verification

Run the repo-level quality gates after bootstrapping:

```bash
npm run verify
```

The default verify surface is intentionally deterministic and local-first:

- `npm run lint`
- `npm run typecheck`
- `npm run test`
- `npm run security`
- `npm run build`

Optional E2E coverage stays out of the default pre-commit path:

```bash
npm run test:e2e
```

## Local Service Startup

The workflow standardizes the agent API on port `8081` because that matches the dashboard env templates, Docker wiring, and `platform/scripts/start-local.sh`. Some older platform docs still reference port `8080`; treat those as legacy notes.

### Terminal 1: Agent API

```bash
cd /Users/monterey/Workspace/Projs/Tasmem/agentic-ads-scraping/platform
source venv/bin/activate
MODE=local API_PORT=8081 uvicorn agent.api:app --host 0.0.0.0 --port 8081 --reload
```

### Terminal 2: Dashboard Backend

```bash
cd /Users/monterey/Workspace/Projs/Tasmem/agentic-ads-scraping/platform/dashboard/backend
MODE=local \
DATA_DIR=../../data \
AGENT_API_URL=http://localhost:8081 \
SCRAPER_API_URL=http://localhost:3001 \
../../venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Terminal 3: Scraper Service

```bash
cd /Users/monterey/Workspace/Projs/Tasmem/agentic-ads-scraping/platform/scrapers
npm run server
```

### Terminal 4: Dashboard Frontend

```bash
cd /Users/monterey/Workspace/Projs/Tasmem/agentic-ads-scraping/platform/dashboard/frontend
npm run dev
```

### Expected Endpoints

- Agent API: `http://localhost:8081/health`
- Dashboard backend: `http://localhost:8000/api/v1/health`
- Scraper server: `http://localhost:3001/health`
- Dashboard frontend: `http://localhost:3000` or `http://localhost:5173`, depending on the Vite config you are using locally

## Manual Validation Flow

Use this path when you want a realistic end-to-end local check without enabling the heavier E2E suite:

```bash
curl http://localhost:8081/health
curl http://localhost:8000/api/v1/health
curl http://localhost:3001/health
```

Trigger a scrape through the agent API:

```bash
curl -X POST http://localhost:8081/scrape \
  -H "Content-Type: application/json" \
  -d '{"source":"meta_ad_library","max_items":5}'
```

Then confirm the dashboard surfaces load:

- open the pipeline view
- confirm jobs appear through the dashboard backend
- confirm scraper sessions or screenshots are visible when streaming is enabled

## Optional BDD and Playwright Validation

After the four services are running:

```bash
cd /Users/monterey/Workspace/Projs/Tasmem/agentic-ads-scraping
bash ./platform/tests/e2e/run_e2e_tests.sh
```

Use this for integration-level validation, not for every commit.

## Orchestrator Commands

The lightweight orchestrator reads [SPEC.md](/Users/monterey/Workspace/Projs/Tasmem/agentic-ads-scraping/SPEC.md), [TASKS.md](/Users/monterey/Workspace/Projs/Tasmem/agentic-ads-scraping/TASKS.md), [STATE.json](/Users/monterey/Workspace/Projs/Tasmem/agentic-ads-scraping/STATE.json), and [ORCHESTRATOR_STATE.json](/Users/monterey/Workspace/Projs/Tasmem/agentic-ads-scraping/ORCHESTRATOR_STATE.json):

```bash
npm run orchestrator:sync
npm run orchestrator:status
npm run orchestrator:coverage
```

## Cloud Validation Notes

The repo stays local-first by default. Only set `MODE=cloud` after you have:

- configured `GCP_PROJECT_ID`
- populated storage, Pub/Sub, and Vertex AI variables
- exported `GOOGLE_APPLICATION_CREDENTIALS`
- validated the Terraform and Cloud Run surfaces intentionally

Do not use cloud-only variables in normal local verification.
