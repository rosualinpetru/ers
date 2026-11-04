#!/bin/bash
# Benchmark a scheme on the Cali dataset (2D California road intersections,
# ~21k points) across a range of domain sizes.
#
# Usage:   scripts/cali.sh <scheme>            (see scripts/lib/common.sh for
#          PYTHON / QUERIES_COUNT overrides)
#
# Domain-size guidance: 2^0..2^15 per dimension — beyond that the scale brings
# no difference for this dataset. TDAG-based Hilbert schemes (tdag_src_hilbert,
# interactive_src_hilbert, tdag_src_hilbert_data_dependent) build a structure
# over the full 2^(2d) Hilbert domain and are only practical up to d≈7.
source "$(dirname "$0")/lib/common.sh"
require_scheme "${1:-}"

for d in $(seq 5 10); do
  run_benchmark "$SCHEME" cali "$d" 1000000
done
