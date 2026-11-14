#!/bin/zsh
# Usage: regress_text.sh OUT_DIR [SCRIPTS_DIR]
# The text check on every figure of the end-to-end runs that has a labels.txt beside it, with the file
# selection of the earlier runs: one JSON report per figure in OUT_DIR. SCRIPTS_DIR defaults to this
# repository's; give a copy of an older version to make a baseline, then compare the two with
# compare_runs.py. Runs three figures at a time; about a minute and a half for a hundred figures.
set -euo pipefail
source ${0:A:h:h}/env.sh
out=$1; scripts=${2:-$SCIFIG_SKILL/scripts}
[[ -f $scripts/check_text.py ]] || { echo "no check_text.py in $scripts" >&2; exit 2; }
mkdir -p $out
cd $SCIFIG_GEN
for d in e2e*(/N); do
  [[ -f $d/labels.txt ]] || continue
  for p in $d/*.png(N); do
    case $p in *150mm*|*300dpi*|*enlarged*|*large*|*preview*|*inspection*|*contact*|*1200*|*word*|*master*|*report*) continue;; esac
    printf '%s\t%s\n' $p $d/labels.txt
  done
done | xargs -P 3 -L 1 bash -c '
  name=$(printf "%s" "$0" | tr "/" "_")
  ORT_DISABLE_TELEMETRY=1 PYTHONDONTWRITEBYTECODE=1 uv run --quiet "'$scripts'/check_text.py" "$0" --labels "$1" --json > "'$out'/$name.json" 2> "'$out'/$name.err" || echo "FAILED $0"
'
echo "figures: $(ls $out/*.json | wc -l | tr -d ' ')"
