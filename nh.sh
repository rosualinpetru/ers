#!/bin/bash

QUERIES_COUNT=250 # spread across 10 buckets
SCHEME=$1

VALID_SCHEMES=("linear" "range_brc" "quad_brc" "quad_src" "tdag_src" "linear_hilbert" "range_brc_hilbert" "tdag_src_hilbert")

# Check if the SCHEME is in VALID_SCHEMES
if [[ ! " ${VALID_SCHEMES[@]} " =~ " ${SCHEME} " ]]; then
  echo "Please specify one of the schemes below as an argument:"
  for s in "${VALID_SCHEMES[@]}"; do
    echo "  $s"
  done
  exit 1
fi

python3 -m ers.benchmark.cli \
  --scheme "$SCHEME" \
  --dataset nh_64 \
  --domain-size 6 \
  --records-limit 1000000 \
  --queries-count $QUERIES_COUNT