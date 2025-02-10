#!/bin/bash

datasets=("dense_2d" "spitz" "cali" "gowalla")
configurations=("linear" "linear_hilbert" "range_brc" "quad_brc" "quad_src" "range_brc_hilbert" "tdag_src" "tdag_src_hilbert")

for dataset in "${datasets[@]}"; do
  for config in "${configurations[@]}"; do
    ./"$dataset".sh "$config"
  done
done
