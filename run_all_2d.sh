#!/bin/bash

datasets=("dense_2d")
schemes=("linear" "linear_hilbert" "quad_brc" "quad_brc_hilbert")

for dataset in "${datasets[@]}"; do
  for scheme in "${schemes[@]}"; do
    ./"$dataset".sh "$scheme"
  done
done
