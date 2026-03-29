# AGENTS.md - Execution Plan

## Operating Mode

This repository uses the **FULL** planning/state model because the target system is multi-service, polyglot, and benefits from parallel workstreams. The runtime portion is intentionally lightweight: it tracks task state, requirement coverage, and worktree/bootstrap conventions without forcing a heavyweight autonomous scheduler onto the repo.

## Phase 1: Workflow Foundation

### 1.1 Canonical Bootstrap and Environment Contract

**Goal**: Make local setup reproducible from the repo root.  
**Primary Files**: `.env.example`, `LOCAL_BOOTSTRAP.md`, `scripts/bootstrap.sh`

**Tasks**:

- standardize the root bootstrap flow around `npm run bootstrap`
- define a canonical env template that is local-first and cloud-optional
- document the shared Python `venv` path and npm install surfaces

**Dependencies**: none

**Acceptance Criteria**:

- contributors can bootstrap from the repo root without guessing subproject commands
- local mode remains the default path
- cloud-only variables are separated clearly from local defaults

### 1.2 Root Quality Gates and Shared Config

**Goal**: Create one repo-native quality entrypoint across Python and Node surfaces.  
**Primary Files**: `package.json`, `.editorconfig`, `.prettierrc.json`, `.eslintrc.cjs`, `scripts/*.sh`

**Tasks**:

- add root commands for lint, typecheck, test, security, build, and verify
- keep Python checks focused on stable deterministic surfaces
- use shared ESLint and Prettier config for repo-level JS and TS files
- block committed secrets and credential files in the repo-level security gate

**Dependencies**: 1.1

**Acceptance Criteria**:

- `npm run verify` exercises the agreed repo-level gates
- the workflow delegates to existing scraper, dashboard, and Python surfaces
- the setup does not require a package-manager migration

### 1.3 Contributor Guardrails

**Goal**: Keep the daily workflow protective but usable.  
**Primary Files**: `.husky/pre-commit`, `CONTRIBUTING.md`, `docs/COMMIT_MESSAGES.md`, `docs/developer-onboarding/workflows.md`

**Tasks**:

- enforce deterministic checks in pre-commit
- document commit-message expectations and the branch promotion path
- make the `develop -> staging -> main` model explicit at the repo level

**Dependencies**: 1.2

**Acceptance Criteria**:

- contributors know which commands to run before opening a PR
- branch expectations match the existing pipeline topology
- hooks remain practical enough for normal development

## Phase 2: Planning and State Tracking

### 2.1 System Definition and Execution Plan

**Goal**: Align the workflow docs to the actual agentic ads domain.  
**Primary Files**: `SPEC.md`, `AGENTS.md`

**Tasks**:

- define users, use cases, requirements, and non-functional targets
- rewrite the execution plan around scraping, enrichment, dashboard, and operations workstreams

**Dependencies**: none

**Acceptance Criteria**:

- no camera-domain language remains
- requirements reflect the current repo architecture
- workflow decisions are traceable to real components

### 2.2 Granular Task Registry and Machine State

**Goal**: Keep the task plan executable by humans and machines.  
**Primary Files**: `TASKS.md`, `STATE.json`

**Tasks**:

- define phase-scoped tasks with dependencies, files, and requirement links
- keep a machine-readable progress model alongside the human task list
- store baseline verification status separately from implementation progress

**Dependencies**: 2.1

**Acceptance Criteria**:

- every active task maps to at least one SPEC requirement
- the state file mirrors the phase and task structure from `TASKS.md`
- verification results can be updated without rewriting the task plan

### 2.3 Lightweight Orchestrator and Worktree Bootstrap

**Goal**: Provide task sync, status, and coverage tooling without over-automating the repo.  
**Primary Files**: `orchestrator/*`, `ORCHESTRATOR_STATE.json`, `.kilocode/setup-script`

**Tasks**:

- parse `SPEC.md` and `STATE.json`
- compute requirement coverage and sync task state
- document how worktrees should inherit the shared env/bootstrap setup

**Dependencies**: 2.2

**Acceptance Criteria**:

- orchestrator commands can sync and report status
- `ORCHESTRATOR_STATE.json` uses deterministic task transitions
- worktree setup keeps local env reuse practical

## Phase 3: Scraping and Processing Runtime

### 3.1 Scraper Runtime Contracts and Source Controls

**Goal**: Keep ingestion behavior explicit and verifiable.  
**Primary Files**: `platform/scrapers/package.json`, `platform/scrapers/scraper.js`, `platform/scrapers/server.js`, `platform/scrapers/limits.js`

**Tasks**:

- validate scraper source coverage and rate-limit controls
- keep the live stream and screenshot path visible in the runtime contract
- ensure the repo-level workflow can lint and test the scraper surface

**Dependencies**: 1.2

**Acceptance Criteria**:

- scraper commands remain runnable via npm
- source-specific throttling stays explicit
- session visibility remains part of the public contract

### 3.2 Local/Cloud Adapter Boundary Validation

**Goal**: Preserve mode separation and dependency inversion.  
**Primary Files**: `platform/agent/config.py`, `platform/agent/orchestrator.py`, `platform/agent/adapters/*`, `platform/env.example`

**Tasks**:

- keep local and cloud adapters behind interfaces
- document and validate the env boundary for each mode
- validate that raw assets and scrape metadata can persist through local and cloud-compatible storage paths
- preserve the cloud-only Vertex AI restriction

**Dependencies**: 1.1

**Acceptance Criteria**:

- local mode runs without GCP credentials
- cloud mode still maps cleanly onto the same business interfaces
- local and cloud storage paths stay interchangeable for raw assets and scrape metadata
- Vertex AI fails fast when local mode is active

### 3.3 Feature Extraction and Reverse Prompt Verification

**Goal**: Protect the enrichment stages with deterministic checks.  
**Primary Files**: `platform/feature_extraction/*`, `platform/reverse_prompt/*`, `platform/tests/test_feature_extraction.py`, `platform/tests/test_reverse_prompt.py`

**Tasks**:

- keep feature extraction tests in the repo-level deterministic suite
- keep reverse prompt validation deterministic in local mode
- ensure cloud-specific prompt paths are optional rather than default

**Dependencies**: 1.2, 3.2

**Acceptance Criteria**:

- deterministic tests cover the core enrichment stages
- local reverse prompt generation stays reproducible
- cloud-only prompt generation remains optional

## Phase 4: APIs and Dashboard Surfaces

### 4.1 Agent API Health, Queue, and Job Controls

**Goal**: Make the orchestration surface easy to validate locally.  
**Primary Files**: `platform/agent/api.py`, `platform/main.py`

**Tasks**:

- keep health, readiness, scrape trigger, and queue endpoints stable
- align the repo bootstrap docs with the actual agent startup path
- document the standard local agent port

**Dependencies**: 1.1, 3.2

**Acceptance Criteria**:

- agent health checks are runnable from the bootstrap guide
- the standard local port is documented consistently
- job-trigger flows remain testable without cloud dependencies

### 4.2 Dashboard Backend and Frontend Quality Surfaces

**Goal**: Keep the monitoring UI maintainable and shippable.  
**Primary Files**: `platform/dashboard/backend/app/*`, `platform/dashboard/frontend/*`

**Tasks**:

- expose dashboard backend endpoints for jobs, assets, metrics, logs, and screenshots
- lint, typecheck, and build the frontend from the repo root
- document the backend/frontend startup sequence in the bootstrap guide

**Dependencies**: 1.2, 4.1

**Acceptance Criteria**:

- the dashboard backend participates in local validation
- the frontend is part of repo-level lint/typecheck/build coverage
- startup instructions match the actual subproject paths

### 4.3 Optional E2E Validation Entry Points

**Goal**: Keep broader validation available without slowing every commit.  
**Primary Files**: `platform/tests/e2e/*`, `LOCAL_BOOTSTRAP.md`

**Tasks**:

- expose the BDD and Playwright entrypoints clearly
- keep them outside the default pre-commit path
- define when contributors should use them

**Dependencies**: 4.2

**Acceptance Criteria**:

- optional E2E commands are documented and runnable
- contributors understand the difference between deterministic verify and full E2E validation

## Phase 5: Delivery and Operations

### 5.1 Unified GitHub Quality Workflow

**Goal**: Replace narrow smoke coverage with a repo-level quality workflow.  
**Primary Files**: `.github/workflows/python-tests.yml`

**Tasks**:

- prepare Python and Node surfaces in CI
- run the same repo-level gates used locally
- cover pull requests and the shared `develop`, `staging`, and `main` branches

**Dependencies**: 1.2

**Acceptance Criteria**:

- CI and local verify use the same command surface
- PRs receive more than a Python-only smoke test
- branch triggers align with the existing promotion model

### 5.2 Local Validation and Release Playbooks

**Goal**: Keep operational knowledge close to the codebase.  
**Primary Files**: `LOCAL_BOOTSTRAP.md`, `platform/LOCAL_VALIDATION.md`, `platform/MANUAL_TESTING.md`, `docs/developer-onboarding/workflows.md`

**Tasks**:

- connect repo-level bootstrap docs to the more detailed platform validation guides
- keep release guidance aligned with local-first development
- make manual checks and follow-up investigation paths explicit

**Dependencies**: 1.1, 1.3, 5.1

**Acceptance Criteria**:

- contributors can find the correct validation doc quickly
- the repo-level workflow explains when to use the deeper platform guides
- release promotion stays aligned with the branch model
