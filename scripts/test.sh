#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

log_section "Deterministic Python tests"
run_python_module pytest \
  "$PLATFORM_ROOT/tests/test_feature_extraction.py" \
  "$PLATFORM_ROOT/tests/test_reverse_prompt.py"
log_step "Deterministic Python tests passed"

log_section "Scraper tests"
(cd "$SCRAPERS_DIR" && npx vitest run --passWithNoTests)
log_step "Scraper tests passed"
