#!/bin/zsh
# Usage: run_e2e.sh WORKDIR REQUEST_FILE
# A fresh Codex session that has only the skill and the user's request. It runs on your own Codex and
# spends its image generations: count them before a round.
set -u
source ${0:A:h:h}/env.sh
work=$1; request=$(cat "$2"); skill=$SCIFIG_SKILL
start=$(date +%s)
codex exec --skip-git-repo-check -C "$work" -s workspace-write --add-dir "$UV_CACHE_DIR" \
  -c 'sandbox_workspace_write.network_access=true' -c 'model_reasoning_effort="medium"' -o "$work/last.txt" \
  "A skill is installed at $skill. Read its SKILL.md first and follow it for the request below; read its other files only as it directs. Work in the current directory. The user is not available: where the skill tells you to ask something, write down the question you would have asked and go on with an assumption you state.

Request from the user:
$request

When you are done, end your reply with a section titled NOTES ON THE SKILL that lists, concretely, every place where the skill's instructions were unclear, wrong, missing or cost you an extra attempt (quote the sentence or name the file and section), and every error message you hit." \
  < /dev/null > "$work/run.log" 2>&1
echo "codex exit: $? after $(( $(date +%s) - start )) s" > "$work/run.txt"
