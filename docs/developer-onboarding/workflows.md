# Developer Workflows

## Branch Strategy

This repository already carries deployment assumptions for three shared branches, so the workflow bootstrap keeps that model instead of inventing a new one.

- `develop`: integration branch for day-to-day feature work
- `staging`: pre-production validation branch
- `main`: production-ready branch
- `feature/*`: normal feature branches off `develop`
- `bugfix/*`: regression fixes off `develop`
- `hotfix/*`: production fixes off `main`, then merged back forward

## Daily Workflow

1. Branch from `develop`.
2. Run `npm run bootstrap` if your local environment is not prepared yet.
3. Make a focused change.
4. Run `npm run verify`.
5. If your change touches cross-service behavior, run `npm run test:e2e` after starting the local stack.
6. Open a pull request into `develop`.

## Standard Commands

```bash
npm run bootstrap
npm run verify
npm run orchestrator:status
```

Optional deep validation:

```bash
npm run bootstrap:e2e
npm run test:e2e
npm run orchestrator:coverage
```

## Pull Requests

Every PR should describe:

- what changed
- why the change matters
- how you verified it
- any follow-up work that still remains

Prefer small PRs that stay inside one workstream whenever possible:

- workflow/setup
- agent orchestration
- scraper runtime
- dashboard backend
- dashboard frontend
- cloud/deployment

## Promotion Flow

The intended promotion sequence is:

```text
feature/* or bugfix/* -> develop -> staging -> main
```

Use `hotfix/*` only when `main` needs a direct repair.

## Local-First Rule

The default contributor workflow must stay runnable without cloud credentials. If a change requires `MODE=cloud`, document:

- why local mode is insufficient
- which environment variables are required
- how to validate the same area safely in local mode

## State and Planning Files

The operating model keeps four root files synchronized:

- [SPEC.md](/Users/monterey/Workspace/Projs/Tasmem/agentic-ads-scraping/SPEC.md)
- [AGENTS.md](/Users/monterey/Workspace/Projs/Tasmem/agentic-ads-scraping/AGENTS.md)
- [TASKS.md](/Users/monterey/Workspace/Projs/Tasmem/agentic-ads-scraping/TASKS.md)
- [STATE.json](/Users/monterey/Workspace/Projs/Tasmem/agentic-ads-scraping/STATE.json)

Use the orchestrator commands to inspect sync and coverage after editing them.
