#!/bin/bash
# Shared helpers for the benchmark scripts in scripts/.
#
# Responsibilities:
#   * anchor every script at the repository root (so `python -m ers...` and
#     the ./benchmarks output directory resolve correctly no matter where the
#     script is invoked from);
#   * pick the Python interpreter (the project virtualenv when present,
#     overridable with $PYTHON);
#   * validate the scheme argument against the CLI's registry — the single
#     source of truth — instead of a copy-pasted list per script;
#   * provide run_benchmark(), the one place that shells out to the CLI.
#
# Environment overrides:
#   PYTHON         interpreter to use (default: .venv/bin/python, else python3)
#   QUERIES_COUNT  queries per benchmark run (default: 250, spread over 10
#                  query-size buckets by the harness)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

if [[ -z "${PYTHON:-}" ]]; then
  if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
    PYTHON="$REPO_ROOT/.venv/bin/python"
  else
    PYTHON="python3"
  fi
fi

QUERIES_COUNT="${QUERIES_COUNT:-250}"

# require_scheme <scheme-name>
# Validates the scheme against ers.benchmark.cli's registry; prints the valid
# names and exits when missing or unknown. Sets $SCHEME on success.
require_scheme() {
  SCHEME="${1:-}"
  local valid
  valid="$("$PYTHON" -c 'from ers.benchmark.cli import schemes; print("\n".join(schemes))')"
  if [[ -z "$SCHEME" ]] || ! grep -qx "$SCHEME" <<< "$valid"; then
    echo "Please specify one of the schemes below as an argument:"
    sed 's/^/  /' <<< "$valid"
    exit 1
  fi
}

# run_benchmark <scheme> <dataset> <domain-size-bits> <records-limit>
# Runs one benchmark; the report lands in ./benchmarks/.
run_benchmark() {
  "$PYTHON" -m ers.benchmark.cli \
    --scheme "$1" \
    --dataset "$2" \
    --domain-size "$3" \
    --records-limit "$4" \
    --queries-count "$QUERIES_COUNT"
}
