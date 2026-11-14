# Where the evaluation scripts find things. Sourced by them; set any of these in the environment to override.
: ${SCIFIG_REPO:=${${(%):-%x}:A:h:h}}                       # this repository
: ${SCIFIG_SKILL:=$SCIFIG_REPO/skills/scifig}                # the skill the Codex sessions are given
: ${SCIFIG_GEN:=$SCIFIG_REPO/eval/runs}                      # the runs: one folder per session, its figures and labels.txt
: ${SCIDRAW_SAMPLES:=$SCIFIG_REPO/eval/samples}              # SciDraw's published samples, compared with
# eval/runs and eval/samples hold local data and are not committed: make them folders, or links to where the data is.
: ${UV_CACHE_DIR:=$HOME/.cache/uv}                           # uv's cache, which a session must be allowed to write
export SCIFIG_REPO SCIFIG_SKILL SCIFIG_GEN SCIDRAW_SAMPLES UV_CACHE_DIR
