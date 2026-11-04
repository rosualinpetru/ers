#!/bin/bash
# Benchmark a scheme on the generated dense 3D dataset (every domain cell
# populated, up to the records limit) across a range of domain sizes.
#
# Usage:   scripts/dense_3d.sh <scheme>
source "$(dirname "$0")/lib/common.sh"
require_scheme "${1:-}"

for d in $(seq 4 5); do
  run_benchmark "$SCHEME" dense_3d "$d" 1000000
done
