#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

log_section "Repo formatting"
(cd "$REPO_ROOT" && npx prettier --check \
  AGENTS.md \
  SPEC.md \
  TASKS.md \
  LOCAL_BOOTSTRAP.md \
  README.md \
  CONTRIBUTING.md \
  docs/**/*.md \
  .github/workflows/*.yml \
  .*.json \
  .*.cjs)
log_step "Repo formatting checks passed"

log_section "Scraper lint"
run_npm_script "$SCRAPERS_DIR" lint
log_step "Scraper lint passed"

log_section "Frontend lint"
run_npm_script "$FRONTEND_DIR" lint
log_step "Frontend lint passed"

log_section "Orchestrator lint"
(cd "$REPO_ROOT" && npx eslint orchestrator/*.ts --max-warnings=0)
log_step "Orchestrator lint passed"
