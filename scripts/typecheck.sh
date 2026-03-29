#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

log_section "Python typecheck"
log_warn "Skipping blocking mypy in the default gate; the agent typing backlog remains tracked in TASKS.md."

log_section "Frontend typecheck"
run_npm_script "$FRONTEND_DIR" type-check
log_step "Frontend typecheck passed"

log_section "Orchestrator typecheck"
run_npm_script "$REPO_ROOT/orchestrator" typecheck
log_step "Orchestrator typecheck passed"
