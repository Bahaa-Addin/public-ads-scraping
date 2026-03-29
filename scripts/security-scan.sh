#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

log_section "Python dependency integrity"
run_python_module pip check
log_step "pip dependency graph is consistent"

log_section "Tracked secret files"
tracked_secret_files="$(git ls-files '*.env' '*.pem' '*.key' 'service-account*.json' 'credentials.json' | grep -vE '(^|/)(\\.env\\.example|env\\.example)$' || true)"
if [ -n "$tracked_secret_files" ]; then
  fail "Tracked secret-like files detected:\n$tracked_secret_files"
fi
log_step "No tracked secret-like files detected"

log_section "High-signal secret scan"
secret_hits="$(rg -n --hidden \
  --glob '!.git/**' \
  --glob '!**/node_modules/**' \
  --glob '!platform/data/**' \
  --glob '!**/*.md' \
  --glob '!**/env.example' \
  --glob '!**/.env.example' \
  '(BEGIN (RSA|DSA|EC|OPENSSH) PRIVATE KEY|AIza[0-9A-Za-z\\-_]{35}|xox[baprs]-[0-9A-Za-z-]{10,}|ya29\\.[0-9A-Za-z\\-_]+)' \
  "$REPO_ROOT" || true)"
if [ -n "$secret_hits" ]; then
  fail "Potential credential material detected:\n$secret_hits"
fi
log_step "No credential patterns detected"
