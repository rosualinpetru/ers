#!/bin/bash

OUTPUT="cali.out.txt"

QUERIES_COUNT=250 # spread across 10 buckets
SCHEME=$1

VALID_SCHEMES=("linear" "range_brc" "quad_brc" "qdag_src" "tdag_src" "linear_hilbert" "range_brc_hilbert" "tdag_src_hilbert")

# Check if the SCHEME is in VALID_SCHEMES
if [[ ! " ${VALID_SCHEMES[@]} " =~ " ${SCHEME} " ]]; then
  echo "Please specify one of the schemes below as an argument:"
  for s in "${VALID_SCHEMES[@]}"; do
    echo "  $s"
  done
  exit 1
fi

for d in $(seq 6 6); do
  python3 -m extensions.util.benchmark.cli \
    --scheme "$SCHEME" \
    --dataset-name cali \
    --dataset-dimension-bits $d \
    --records-limit 1000000 \
    --queries-count $QUERIES_COUNT
done