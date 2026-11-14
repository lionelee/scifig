#!/bin/zsh
# Usage: measure.sh TOOL [--each]   (TOOL: content_stats | stroke_fine | element_stats | type_size | bold | detail)
# One measure over the groups of groups.sh, with the scripts of this repository's skill.
here=${0:A:h}
source $here/groups.sh
ORT_DISABLE_TELEMETRY=1 uv run --quiet $here/$1.py $SCIFIG_SKILL/scripts ${@:2} $groups
