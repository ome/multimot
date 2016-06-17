#!/bin/bash

set -eu

IN="/multimot/filesets/vinculin/20140110Dataset/TV 30 sec PAD input 20140110"
OUT="/multimot/filesets/vinculin/20140110Dataset/TV 30 sec PAD output 20140110"
IN_PLATES=( "cell_movies" "cell_movies_filtered" "cell_movies_ratio" )
OUT_PLATES=( "0001" "DynOverlay" "Overlay" "mosaic" "patch_label" "roi_label" )

for s in A B; do
    mkdir -p screen${s}/plates
done
mkdir -p screens

for i in 0 1 2; do
    p=${IN_PLATES[i]}
    python make_screen.py "${IN}" -s PAD_input -l ${i} \
        -p ${p} -o screens/${p}.screen
    echo vinculin/screens/${p}.screen > screenA/plates/${p}
done

for p in ${OUT_PLATES[@]}; do
    python make_screen.py "${OUT}" -s PAD_output -t ${p} \
        -p ${p} -o screens/${p}.screen
    echo vinculin/screens/${p}.screen > screenB/plates/${p}
done
