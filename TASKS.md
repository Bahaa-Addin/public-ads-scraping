# TASKS.md - Public Ads Platform Task List

## Status Legend

- `[ ]` not started
- `[-]` in progress
- `[x]` completed
- `[!]` blocked
- `[?]` needs review

## Phase 1: Workflow Foundation

### 1.1 Bootstrap and Environment

**Priority**: Critical  
**Dependencies**: None

- [x] **1.1.1 Canonical bootstrap and env contract**
  - Files: `.env.example`, `LOCAL_BOOTSTRAP.md`, `scripts/bootstrap.sh`
  - Requirements: `FR-1.1`, `FR-1.2`, `FR-1.3`, `NFR-1.1`, `NFR-1.2`
- [x] **1.1.2 Root quality gates and shared config**
  - Files: `package.json`, `.editorconfig`, `.prettierrc.json`, `.eslintrc.cjs`, `scripts/*.sh`
  - Requirements: `FR-5.1`, `NFR-2.1`, `NFR-2.2`, `NFR-3.1`
- [x] **1.1.3 Practical contributor guardrails**
  - Files: `.husky/pre-commit`, `CONTRIBUTING.md`, `docs/COMMIT_MESSAGES.md`, `docs/developer-onboarding/workflows.md`
  - Requirements: `FR-5.2`, `FR-5.4`, `NFR-3.3`

## Phase 2: Planning and State Tracking

### 2.1 Specs, Tasks, and Machine State

**Priority**: Critical  
**Dependencies**: `1.1.1`, `1.1.2`

- [x] **2.1.1 System definition and execution plan**
  - Files: `SPEC.md`, `AGENTS.md`
  - Requirements: `FR-1.3`, `NFR-1.3`, `NFR-3.2`
- [x] **2.1.2 Granular task registry and machine state**
  - Files: `TASKS.md`, `STATE.json`
  - Requirements: `NFR-1.3`, `NFR-3.2`
- [x] **2.1.3 Lightweight orchestrator and worktree bootstrap**
  - Files: `orchestrator/*`, `ORCHESTRATOR_STATE.json`, `.kilocode/setup-script`
  - Requirements: `FR-5.1`, `NFR-3.2`

## Phase 3: Scraping and Processing Runtime

### 3.1 Ingestion and Enrichment

**Priority**: High  
**Dependencies**: `1.1.2`, `2.1.1`

- [ ] **3.1.1 Scraper runtime contracts and source controls**
  - Files: `platform/scrapers/package.json`, `platform/scrapers/scraper.js`, `platform/scrapers/server.js`, `platform/scrapers/limits.js`
  - Requirements: `FR-2.1`, `FR-2.2`, `FR-2.4`
- [ ] **3.1.2 Local/cloud adapter boundary validation**
  - Files: `platform/agent/config.py`, `platform/agent/orchestrator.py`, `platform/agent/adapters/*`, `platform/env.example`
  - Requirements: `FR-1.1`, `FR-1.2`, `FR-1.4`, `FR-2.3`, `FR-3.4`, `NFR-2.3`
- [ ] **3.1.3 Feature extraction and classification verification**
  - Files: `platform/feature_extraction/*`, `platform/tests/test_feature_extraction.py`
  - Requirements: `FR-3.1`, `FR-3.2`, `NFR-4.2`
- [ ] **3.1.4 Reverse prompt generation verification**
  - Files: `platform/reverse_prompt/*`, `platform/tests/test_reverse_prompt.py`
  - Requirements: `FR-3.3`, `FR-3.4`, `NFR-2.3`

## Phase 4: APIs and Dashboard Surfaces

### 4.1 Control Plane and UI

**Priority**: High  
**Dependencies**: `3.1.2`, `3.1.3`, `3.1.4`

- [ ] **4.1.1 Agent API health, queue, and job controls**
  - Files: `platform/agent/api.py`, `platform/main.py`
  - Requirements: `FR-4.1`, `FR-4.4`, `NFR-4.1`
- [ ] **4.1.2 Dashboard backend service contracts**
  - Files: `platform/dashboard/backend/app/*`
  - Requirements: `FR-4.2`, `FR-4.4`, `NFR-4.1`
- [x] **4.1.3 Dashboard frontend quality and build surface**
  - Files: `platform/dashboard/frontend/*`
  - Requirements: `FR-4.3`, `FR-5.1`, `NFR-3.1`
- [ ] **4.1.4 Optional end-to-end validation entrypoints**
  - Files: `platform/tests/e2e/*`, `LOCAL_BOOTSTRAP.md`
  - Requirements: `FR-4.4`, `NFR-4.2`

## Phase 5: Delivery and Operations

### 5.1 Shared Branches, CI, and Validation Playbooks

**Priority**: High  
**Dependencies**: `1.1.2`, `1.1.3`, `4.1.3`

- [x] **5.1.1 Unified GitHub quality workflow**
  - Files: `.github/workflows/python-tests.yml`
  - Requirements: `FR-5.3`, `NFR-2.2`, `NFR-3.3`
- [x] **5.1.2 Deployment branch and release guidance**
  - Files: `docs/developer-onboarding/workflows.md`, `CONTRIBUTING.md`, `README.md`
  - Requirements: `FR-5.4`, `NFR-1.2`
- [x] **5.1.3 Local validation and observability playbooks**
  - Files: `LOCAL_BOOTSTRAP.md`, `platform/LOCAL_VALIDATION.md`, `platform/MANUAL_TESTING.md`
  - Requirements: `FR-4.4`, `NFR-4.1`, `NFR-4.2`
