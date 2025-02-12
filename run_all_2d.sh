#!/bin/bash

datasets=("dense_2d" "spitz" "cali" "gowalla")
VALID_SCHEMES=("linear" "range_brc" "tdag_src" "quad_brc" "quad_src" "linear_hilbert" "range_brc_hilbert" "tdag_src_hilbert" "quad_brc_hilbert" "quad_src_hilbert")

for dataset in "${datasets[@]}"; do
  for config in "${configurations[@]}"; do
    ./"$dataset".sh "$config"
  done
done
