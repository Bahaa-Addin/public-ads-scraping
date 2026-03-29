#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

log_section "Python bytecode build check"
run_python_module compileall \
  "$PLATFORM_ROOT/agent" \
  "$PLATFORM_ROOT/dashboard/backend/app" \
  "$PLATFORM_ROOT/feature_extraction" \
  "$PLATFORM_ROOT/reverse_prompt" \
  "$PLATFORM_ROOT/firestore"
log_step "Python modules compile cleanly"

log_section "Frontend build"
run_npm_script "$FRONTEND_DIR" build
log_step "Dashboard frontend build passed"

log_section "Orchestrator build"
run_npm_script "$REPO_ROOT/orchestrator" build
log_step "Orchestrator build passed"
