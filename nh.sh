#!/bin/bash

OUTPUT="nh.out.txt"

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

python3 -m extensions.experiments.benchmark \
  --scheme "$SCHEME" \
  --queries-count $QUERIES_COUNT \
  --dataset nh_64 \
  --dataset-dimension-size 6 >>$OUTPUT
