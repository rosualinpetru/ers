#!/bin/bash
# Benchmark a scheme on the Gowalla dataset (2D check-ins, ~6.4M points).
# This is by far the largest dataset — runs take a long time; consider running
# it overnight or on a server.
#
# Usage:   scripts/gowalla.sh <scheme>
#
# Domain-size guidance: up to 2^42 per dimension is meaningful, but index
# construction cost grows quickly; start small. Keep TDAG-based Hilbert
# schemes at d≲7 (2^(2d) Hilbert domain).
source "$(dirname "$0")/lib/common.sh"
require_scheme "${1:-}"

for d in $(seq 5 10); do
  run_benchmark "$SCHEME" gowalla "$d" 1000000
done
