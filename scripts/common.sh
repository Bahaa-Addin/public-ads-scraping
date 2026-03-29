#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLATFORM_ROOT="$REPO_ROOT/platform"
VENV_DIR="${PLATFORM_VENV_DIR:-$PLATFORM_ROOT/venv}"
PYTHON_BIN="${PLATFORM_PYTHON_BIN:-$VENV_DIR/bin/python}"
PIP_BIN="${PLATFORM_PIP_BIN:-$VENV_DIR/bin/pip}"
SCRAPERS_DIR="$PLATFORM_ROOT/scrapers"
FRONTEND_DIR="$PLATFORM_ROOT/dashboard/frontend"
PLAYWRIGHT_DIR="$PLATFORM_ROOT/tests/e2e/playwright"

log_section() {
  printf '\n==> %s\n' "$1"
}

log_step() {
  printf '  [ok] %s\n' "$1"
}

log_warn() {
  printf '  [warn] %s\n' "$1"
}

fail() {
  printf '  [error] %s\n' "$1" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

ensure_python_venv() {
  [ -x "$PYTHON_BIN" ] || fail "Python virtual environment not found at $VENV_DIR. Run npm run bootstrap first."
}

run_python_module() {
  ensure_python_venv
  "$PYTHON_BIN" -m "$@"
}

run_npm_script() {
  local dir="$1"
  local script="$2"
  shift 2
  (cd "$dir" && npm run "$script" -- "$@")
}
