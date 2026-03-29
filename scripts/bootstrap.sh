#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

WITH_E2E=0
CI_MODE=0

for arg in "$@"; do
  case "$arg" in
    --with-e2e)
      WITH_E2E=1
      ;;
    --ci)
      CI_MODE=1
      ;;
    *)
      fail "Unsupported bootstrap flag: $arg"
      ;;
  esac
done

log_section "Checking prerequisites"
require_cmd python3
require_cmd node
require_cmd npm
log_step "python3, node, and npm are available"

log_section "Installing repo workflow tooling"
install_npm_dependencies "$REPO_ROOT"
log_step "Installed root workflow dependencies"

log_section "Preparing platform runtime"
mkdir -p \
  "$PLATFORM_ROOT/data/db" \
  "$PLATFORM_ROOT/data/assets/raw" \
  "$PLATFORM_ROOT/data/assets/processed" \
  "$PLATFORM_ROOT/data/logs" \
  "$PLATFORM_ROOT/data/metrics" \
  "$PLATFORM_ROOT/data/files/screenshots"
log_step "Ensured local data directories exist"

if [ "$CI_MODE" -eq 1 ] || [ ! -f "$PLATFORM_ROOT/.env" ]; then
  cp "$REPO_ROOT/.env.example" "$PLATFORM_ROOT/.env"
  log_step "Prepared platform/.env from root template"
else
  log_step "Reused existing platform/.env"
fi

if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
  log_step "Created Python virtual environment"
fi

if ! "$PYTHON_BIN" -c 'import sys' >/dev/null 2>&1; then
  rm -rf "$VENV_DIR"
  python3 -m venv "$VENV_DIR"
  log_step "Recreated stale Python virtual environment"
fi

"$PYTHON_BIN" -m pip install --upgrade pip
"$PYTHON_BIN" -m pip install -r "$PLATFORM_ROOT/requirements.txt" -r "$PLATFORM_ROOT/dashboard/backend/requirements.txt"

if [ "$WITH_E2E" -eq 1 ] || [ "$CI_MODE" -eq 1 ]; then
  "$PYTHON_BIN" -m pip install -r "$PLATFORM_ROOT/tests/e2e/requirements-test.txt"
  log_step "Installed optional E2E Python dependencies"
fi

log_step "Installed shared Python dependencies"

log_section "Installing Node.js dependencies"
install_npm_dependencies "$SCRAPERS_DIR"
log_step "Installed scraper dependencies"

install_npm_dependencies "$FRONTEND_DIR"
log_step "Installed dashboard frontend dependencies"

if [ "$WITH_E2E" -eq 1 ] || [ "$CI_MODE" -eq 1 ]; then
  install_npm_dependencies "$PLAYWRIGHT_DIR"
  log_step "Installed Playwright runner dependencies"
fi

log_section "Bootstrap complete"
log_step "Run npm run verify once services are bootstrapped"
