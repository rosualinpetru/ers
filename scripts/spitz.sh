#!/bin/bash
# Benchmark a scheme on the Spitz dataset (2D phone-location points of
# politician Malte Spitz, ~29k points) across a range of domain sizes.
#
# Usage:   scripts/spitz.sh <scheme>
#
# Domain-size guidance: 2^0..2^16 per dimension — beyond that the scale brings
# no difference. Keep TDAG-based Hilbert schemes at d≲7 (2^(2d) Hilbert domain).
source "$(dirname "$0")/lib/common.sh"
require_scheme "${1:-}"

for d in $(seq 5 10); do
  run_benchmark "$SCHEME" spitz "$d" 1000000
done
