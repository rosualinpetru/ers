#!/bin/bash
# Benchmark a scheme on the NH dataset (3D elevation samples from the White
# Mountains, 4,096 points on a fixed 2^6 x 2^6 x 2^6 domain).
#
# Usage:   scripts/nh.sh <scheme>
#
# Note: with 3 dimensions at 6 bits, the Hilbert domain is 2^18. Uniform-tree
# Hilbert schemes enumerate that whole domain and become very slow; the
# data-dependent and R-tree schemes are unaffected.
source "$(dirname "$0")/lib/common.sh"
require_scheme "${1:-}"

run_benchmark "$SCHEME" nh_64 6 1000000
