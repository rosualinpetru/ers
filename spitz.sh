#!/bin/bash

QUERIES_COUNT=250 # spread across 10 buckets
SCHEME=$1

VALID_SCHEMES=("linear" "range_brc" "tdag_src" "quad_brc" "quad_src" "linear_hilbert" "range_brc_hilbert" "tdag_src_hilbert" "quad_brc_hilbert" "quad_src_hilbert")

# Check if the SCHEME is in VALID_SCHEMES
if [[ ! " ${VALID_SCHEMES[@]} " =~ " ${SCHEME} " ]]; then
  echo "Please specify one of the schemes below as an argument:"
  for s in "${VALID_SCHEMES[@]}"; do
    echo "  $s"
  done
  exit 1
fi

for d in $(seq 5 10); do
  python3 -m ers.benchmark.cli \
    --scheme "$SCHEME" \
    --dataset spitz \
    --domain-size $d \
    --records-limit 1000000 \
    --queries-count $QUERIES_COUNT
done