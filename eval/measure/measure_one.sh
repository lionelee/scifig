#!/bin/zsh
# Usage: measure_one.sh NAME=PATH[,PATH...] ...   richness, colour, type and lines of figures
here=${0:A:h}
source ${here:h}/env.sh
S=$SCIFIG_SKILL/scripts
ORT_DISABLE_TELEMETRY=1 uv run --quiet $here/bold.py $S --each $@ 2>/dev/null | grep -v "^group\|^[a-z]"
ORT_DISABLE_TELEMETRY=1 uv run --quiet $here/type_size.py $S $@ 2>/dev/null | cut -c1-175
for group in $@; do for p in ${(s:,:)${group#*=}}; do echo "$(uv run --quiet $S/check_figure.py $p --look --screen 2>&1 | grep -E 'FILLS' | sed -E 's/.*median chroma ([0-9]+).*covers ([0-9]+)%.*/fills chroma \1, strong colour \2%/')  $(uv run --quiet $S/check_figure.py $p --look --screen 2>&1 | grep -E 'LINES' | sed -E 's/.*coloured ones are ([0-9.]+) px.*dark ones ([0-9.]+) px.*/lines \1 \/ \2 px/')  $p"; done; done
