#!/usr/bin/env bash
# Munch verification gate — every linter, type check, and test suite behind one
# entry point. `make verify` and CI both call this; it is the phase gate.
#
# Policy (spec §2: "enforced by tooling, not vibes"):
#   * Anything runnable on this machine MUST pass — any failure exits non-zero.
#   * Tools that cannot exist on this platform (Swift / SwiftLint on Windows)
#     are reported as SKIP loudly, never silently.
#   * Under VERIFY_STRICT=1 (set by CI) a skip IS a failure, so a missing tool
#     can never fake the gate green where it matters.
set -uo pipefail

STRICT="${VERIFY_STRICT:-0}"
TESTS_ONLY=0
[[ "${1:-}" == "--tests-only" ]] && TESTS_ONLY=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESULTS=()
FAILED=0

# run <label> <subdir> <command...> — executes in subdir, records PASS/FAIL.
run() {
  local label="$1" dir="$2"
  shift 2
  printf '\n== %s ==\n' "$label"
  if (cd "$ROOT/$dir" && "$@"); then
    RESULTS+=("PASS  $label")
  else
    RESULTS+=("FAIL  $label")
    FAILED=1
  fi
}

# skip <label> <reason> — loud skip; a failure under VERIFY_STRICT.
skip() {
  printf '\n== %s ==\nSKIPPED: %s\n' "$1" "$2"
  if [[ "$STRICT" == "1" || "$STRICT" == "true" ]]; then
    RESULTS+=("FAIL  $1 (skipped: $2 — skips fail under VERIFY_STRICT)")
    FAILED=1
  else
    RESULTS+=("SKIP  $1 — $2")
  fi
}

# --- Python: recommendation service (backend/reco) ---------------------------
# The interpreter is pinned to 3.12 by backend/reco/.python-version (matching
# CI and the production Dockerfile); `uv run` resolves it and syncs the venv on
# demand, so a fresh clone needs no manual setup step.
if command -v uv >/dev/null 2>&1; then
  PY=(uv run --extra dev --)
  if [[ "$TESTS_ONLY" == "0" ]]; then
    run "python: ruff lint"         backend/reco "${PY[@]}" ruff check .
    run "python: ruff format"       backend/reco "${PY[@]}" ruff format --check .
    run "python: mypy --strict"     backend/reco "${PY[@]}" mypy .
  fi
  run   "python: pytest"            backend/reco "${PY[@]}" pytest
else
  skip "python: reco service" "uv not installed (https://docs.astral.sh/uv/)"
fi

# --- TypeScript: Supabase edge functions (backend/supabase/functions) --------
if command -v deno >/dev/null 2>&1; then
  if [[ "$TESTS_ONLY" == "0" ]]; then
    run "deno: lint"                backend/supabase/functions deno lint
    run "deno: fmt --check"         backend/supabase/functions deno fmt --check
  fi
  run   "deno: test"                backend/supabase/functions deno test
else
  skip "deno: edge functions" "deno not installed"
fi

# --- Swift: pure-logic package (ios/Munch/Packages/MunchKit) ------------------
# MunchKit holds platform-independent logic precisely so it can be tested
# without the iOS SDK. On the Windows dev machine Swift may be absent; the
# macOS/Linux CI job enforces this section.
if command -v swift >/dev/null 2>&1; then
  run "swift: MunchKit tests"       ios/Munch/Packages/MunchKit swift test
else
  skip "swift: MunchKit tests" "Swift toolchain not installed on this machine"
fi

if [[ "$TESTS_ONLY" == "0" ]]; then
  if command -v swiftlint >/dev/null 2>&1; then
    run "swiftlint"                 ios/Munch swiftlint --strict
  else
    skip "swiftlint" "not installed (runs in CI)"
  fi

  if command -v swiftformat >/dev/null 2>&1; then
    run "swiftformat --lint"        ios/Munch swiftformat --lint .
  else
    skip "swiftformat" "not installed (runs in CI)"
  fi
fi

# --- Summary ------------------------------------------------------------------
printf '\n================ verify summary ================\n'
for line in "${RESULTS[@]}"; do printf '%s\n' "$line"; done
printf '================================================\n'

if [[ "$FAILED" == "1" ]]; then
  printf 'verify: FAILED\n'
  exit 1
fi
printf 'verify: OK\n'
