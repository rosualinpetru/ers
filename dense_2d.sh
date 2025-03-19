#!/bin/bash

QUERIES_COUNT=250 # spread across 10 buckets
SCHEME=$1

VALID_SCHEMES=("linear" "linear_hilbert" \
  "range_brc" "range_brc_hilbert" "range_brc_data_dependent" "range_brc_hilbert_data_dependent" \
  "tdag_src" "tdag_src_hilbert" \
  "quad_brc" "quad_brc_hilbert" "quad_brc_data_dependent" "quad_brc_hilbert_data_dependent" \
  "quad_src" "quad_src_hilbert" "quad_src_data_dependent" "quad_src_hilbert_data_dependent")

# Check if the SCHEME is in VALID_SCHEMES
if [[ ! " ${VALID_SCHEMES[@]} " =~ " ${SCHEME} " ]]; then
  echo "Please specify one of the schemes below as an argument:"
  for s in "${VALID_SCHEMES[@]}"; do
    echo "  $s"
  done
  exit 1
fi

for d in $(seq 4 8); do
  python3 -m ers.benchmark.cli \
    --scheme "$SCHEME" \
    --dataset dense_2d \
    --domain-size $d \
    --records-limit 1000000 \
    --queries-count $QUERIES_COUNT
done