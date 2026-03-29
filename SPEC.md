# SPEC.md - Product Definition

## Product Overview

**Name**: Public Ads Platform  
**Status**: Active development and workflow hardening  
**Last Updated**: 2026-03-29

Public Ads Platform is a local-first, cloud-optional system for collecting public advertising creatives, extracting structured features, classifying industries, and generating reusable reverse prompts. The repository also includes the operator-facing dashboard, validation tooling, deployment infrastructure, and workflow controls needed to evolve the platform safely.

## Vision

Provide a reproducible pipeline for public creative intelligence that can run on a developer laptop without mandatory cloud services, while still supporting a GCP-backed deployment path for shared environments and scaled workloads.

## Primary Users

| User Type                   | Description                                               | Core Needs                                                           |
| --------------------------- | --------------------------------------------------------- | -------------------------------------------------------------------- |
| Creative research operators | People collecting and reviewing ad creatives              | Reliable ingestion, quick visibility, reproducible outputs           |
| Platform engineers          | Contributors maintaining the pipeline and deployment path | Clear setup, quality gates, branch workflow, local/cloud parity      |
| Analysts and reviewers      | People validating extracted features, prompts, and logs   | Dashboard access, searchable artifacts, manual replay and validation |

## Core Use Cases

### UC-1: Bootstrap a Local Workspace

1. A contributor clones the repository.
2. They run the repo-level bootstrap flow.
3. The shared Python environment, Node surfaces, and local env file are prepared.
4. They verify the deterministic quality gates locally before opening a pull request.

### UC-2: Collect Public Creative Assets

1. An operator triggers one or more public-source scrapers.
2. The scraper service launches Playwright and respects source limits and retry rules.
3. Raw assets and metadata are stored through the configured storage path.
4. Live streaming or screenshots expose scraper progress to the dashboard.

### UC-3: Enrich and Reverse Prompt Assets

1. Feature extraction reads stored assets.
2. Industry signals and creative traits are derived.
3. The reverse prompt service generates prompts from deterministic local rules or cloud LLMs when cloud mode is enabled.
4. Outputs are stored for review and reuse.

### UC-4: Monitor Pipeline State

1. Operators open the dashboard.
2. The dashboard backend exposes jobs, assets, logs, events, screenshots, and metrics.
3. The frontend presents the current pipeline state and any failures requiring action.

### UC-5: Promote a Change Safely

1. A contributor works from `develop` through a short-lived feature or bugfix branch.
2. Pre-commit and GitHub Actions run repo-level quality gates.
3. The branch moves through `develop`, `staging`, and `main` according to release needs.

## System Components

| Component                   | Stack                     | Responsibility                                                         |
| --------------------------- | ------------------------- | ---------------------------------------------------------------------- |
| Agent API and orchestration | Python + FastAPI          | Job lifecycle, adapter binding, queue/storage/LLM orchestration        |
| Scraper runtime             | Node.js + Playwright      | Public-source scraping, rate limits, live stream sessions              |
| Feature extraction          | Python                    | Structured visual and content feature extraction                       |
| Reverse prompt generation   | Python                    | Deterministic template prompts locally, cloud LLM prompts when enabled |
| Dashboard backend           | Python + FastAPI          | UI-facing APIs, metrics, events, screenshots, logs                     |
| Dashboard frontend          | React + TypeScript + Vite | Operational UI for jobs, assets, analytics, logs, and settings         |
| Deployment surface          | Terraform + Docker + CI   | Local containers, cloud deployment, quality automation                 |

## Functional Requirements

### FR-1: Local-First Runtime

| ID     | Requirement                                                                                | Priority |
| ------ | ------------------------------------------------------------------------------------------ | -------- |
| FR-1.1 | Support running the platform locally without mandatory GCP credentials.                    | P0       |
| FR-1.2 | Support a cloud deployment path through the same service boundaries and environment model. | P0       |
| FR-1.3 | Document repo-level setup, verification, and local startup commands.                       | P0       |
| FR-1.4 | Keep storage, queue, LLM, and monitoring behind adapter interfaces.                        | P0       |

### FR-2: Scraping Ingestion

| ID     | Requirement                                                                                | Priority |
| ------ | ------------------------------------------------------------------------------------------ | -------- |
| FR-2.1 | Support public-source scraping through the Node.js scraper service and Playwright.         | P0       |
| FR-2.2 | Apply source-specific limits, retries, and headless/browser runtime controls.              | P0       |
| FR-2.3 | Persist raw asset files and scrape metadata in local and cloud-compatible storage paths.   | P0       |
| FR-2.4 | Surface live scraper session visibility through WebSocket streaming and saved screenshots. | P1       |

### FR-3: Processing Pipeline

| ID     | Requirement                                                                                               | Priority |
| ------ | --------------------------------------------------------------------------------------------------------- | -------- |
| FR-3.1 | Extract reusable visual and structural features from stored creative assets.                              | P0       |
| FR-3.2 | Classify industry and creative signals from extracted features.                                           | P0       |
| FR-3.3 | Generate reverse prompts locally with deterministic templates and optionally via Vertex AI in cloud mode. | P0       |
| FR-3.4 | Block Vertex AI usage when `MODE=local`.                                                                  | P0       |

### FR-4: Control Plane and Dashboard

| ID     | Requirement                                                                                       | Priority |
| ------ | ------------------------------------------------------------------------------------------------- | -------- |
| FR-4.1 | Expose agent API endpoints for health, readiness, scrape triggers, queue metrics, and job status. | P0       |
| FR-4.2 | Expose dashboard backend endpoints for jobs, assets, metrics, logs, events, and screenshots.      | P0       |
| FR-4.3 | Provide a React dashboard for jobs, assets, pipeline, scrapers, analytics, logs, and settings.    | P1       |
| FR-4.4 | Provide practical local validation and manual test flows spanning the core services.              | P0       |

### FR-5: Workflow and Release Management

| ID     | Requirement                                                                                 | Priority |
| ------ | ------------------------------------------------------------------------------------------- | -------- |
| FR-5.1 | Provide repo-level commands for lint, typecheck, test, security, build, and verify.         | P0       |
| FR-5.2 | Enforce practical pre-commit quality gates for contributors.                                | P1       |
| FR-5.3 | Run GitHub Actions quality gates on pull requests and shared branches.                      | P0       |
| FR-5.4 | Document branch promotion and deployment expectations for `develop`, `staging`, and `main`. | P1       |

## Non-Functional Requirements

### NFR-1: Reproducibility

| ID      | Requirement                                                                  | Target                                                          |
| ------- | ---------------------------------------------------------------------------- | --------------------------------------------------------------- |
| NFR-1.1 | Local verification should default to deterministic, offline-friendly checks. | `npm run verify` completes without cloud credentials            |
| NFR-1.2 | Bootstrap instructions should use real repo paths and commands.              | A new contributor can follow the guide without path translation |
| NFR-1.3 | Machine-readable state should mirror the human task plan.                    | `STATE.json` and `TASKS.md` stay aligned                        |

### NFR-2: Security

| ID      | Requirement                                                      | Target                                                  |
| ------- | ---------------------------------------------------------------- | ------------------------------------------------------- |
| NFR-2.1 | No committed secrets, service-account keys, or private datasets. | Secret scan passes on tracked files                     |
| NFR-2.2 | Security checks should run in local verify and CI.               | `npm run security` is part of verify and GitHub Actions |
| NFR-2.3 | Cloud-only providers must fail fast in local mode.               | Vertex AI remains unavailable in `MODE=local`           |

### NFR-3: Maintainability

| ID      | Requirement                                                                                   | Target                                                          |
| ------- | --------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| NFR-3.1 | The repo workflow must support Python and Node surfaces without forcing a monorepo migration. | Root scripts delegate to existing subprojects                   |
| NFR-3.2 | Planning docs, tasks, and state files must stay synchronized.                                 | Orchestrator coverage reaches 100% against the active task plan |
| NFR-3.3 | Hooks and CI should be protective but practical.                                              | Pre-commit stays inside the deterministic verify surface        |

### NFR-4: Observability

| ID      | Requirement                                                                            | Target                                                            |
| ------- | -------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| NFR-4.1 | Operational services should expose health and metrics endpoints.                       | Agent API, dashboard backend, and scraper can be checked locally  |
| NFR-4.2 | The platform should retain manual and automated validation paths for end-to-end flows. | Local bootstrap includes manual flow and optional E2E entrypoints |

## Out of Scope

- inventing a new package manager strategy for the repo
- replacing the existing Bitbucket deployment pipelines
- introducing cloud-only workflows into the default local development path
- copying source-repo camera virtualization terminology or service contracts
