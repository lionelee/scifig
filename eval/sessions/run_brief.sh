#!/bin/zsh
# Usage: run_brief.sh WORKDIR BRIEF_FILE OUTPUT_NAME
# Has Codex pass a brief to its built-in image tool as it is, and copy the result into WORKDIR.
set -u
work=$1; brief=$2; out=$3
start=$(date +%s)
codex exec --skip-git-repo-check -C "$work" -s workspace-write -c 'model_reasoning_effort="low"' -o "$work/$out.last.txt" \
  "Read the file $brief in the current directory. Call your built-in image_gen tool exactly once, with the full text of that file as the prompt: do not shorten, summarise or rewrite it. Then copy the generated file from the Codex generated_images folder into the current directory as $out.png and report its pixel size. Do not draw anything with code. If the image tool is unavailable or returns an error, quote the error exactly and stop." \
  < /dev/null > "$work/$out.log" 2>&1
echo "codex exit: $? after $(( $(date +%s) - start )) s"
cat "$work/$out.last.txt" 2>/dev/null | head -n 8
echo
grep -E "^tokens used" -A1 "$work/$out.log" | tail -n 1
