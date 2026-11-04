#!/bin/bash
# Run one dataset script for many schemes in sequence.
#
# Usage:   scripts/run_all.sh <dataset> [scheme ...]
#   <dataset>  one of: cali spitz gowalla nh dense_2d dense_3d
#   [scheme]   schemes to run; defaults to every scheme in the CLI registry.
#
# Examples:
#   scripts/run_all.sh dense_2d                          # all schemes
#   scripts/run_all.sh cali range_brc hilbert_rtree      # a chosen subset
source "$(dirname "$0")/lib/common.sh"

DATASET="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ -z "$DATASET" || ! -f "$SCRIPT_DIR/$DATASET.sh" ]]; then
  echo "Usage: scripts/run_all.sh <dataset> [scheme ...]"
  echo "Datasets:"
  for f in "$SCRIPT_DIR"/*.sh; do
    n="$(basename "$f" .sh)"
    [[ "$n" != "run_all" ]] && echo "  $n"
  done
  exit 1
fi
shift

if [[ $# -gt 0 ]]; then
  SCHEMES=("$@")
else
  # Default to the full registry (single source of truth: the CLI).
  # (while-read instead of mapfile: macOS ships bash 3.2.)
  SCHEMES=()
  while IFS= read -r s; do
    SCHEMES+=("$s")
  done < <("$PYTHON" -c 'from ers.benchmark.cli import schemes; print("\n".join(schemes))')
fi

for scheme in "${SCHEMES[@]}"; do
  "$SCRIPT_DIR/$DATASET.sh" "$scheme"
done
