#!/bin/bash

QUERIES_COUNT=250 # spread across 10 buckets
SCHEME=$1

VALID_SCHEMES=("linear_3d" "range_brc_3d" "qdag_src_3d" "tdag_src_3d" "quad_brc_3d")

# Check if the SCHEME is in VALID_SCHEMES
if [[ ! " ${VALID_SCHEMES[@]} " =~ " ${SCHEME} " ]]; then
  echo "Please specify one of the schemes below as an argument:"
  for s in "${VALID_SCHEMES[@]}"; do
    echo "  $s"
  done
  exit 1
fi

python3 -m extensions.util.benchmark.cli \
  --scheme "$SCHEME" \
  --dataset-name nh_64 \
  --dataset-dimension-bits 6 \
  --records-limit 1000000 \
  --queries-count $QUERIES_COUNT