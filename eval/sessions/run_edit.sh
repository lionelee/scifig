#!/bin/zsh
# Usage: run_edit.sh WORKDIR SOURCE_IMAGE OUTPUT_NAME INSTRUCTION
# Has Codex edit an image with its built-in image tool, once.
set -u
work=$1; source=$2; out=$3; instruction=$4
start=$(date +%s)
codex exec --skip-git-repo-check -C "$work" -s workspace-write -c 'model_reasoning_effort="low"' -o "$work/$out.last.txt" \
  "Look at the image file $source in the current directory with your view_image tool. Then use your built-in image_gen tool once to edit that image, passing its file in referenced_image_paths, with this instruction, verbatim: $instruction Then copy the edited file from the Codex generated_images folder into the current directory as $out.png and report its pixel size. Do not draw or patch anything with code. If a tool is unavailable or returns an error, quote the error exactly and stop." \
  < /dev/null > "$work/$out.log" 2>&1
echo "codex exit: $? after $(( $(date +%s) - start )) s"
cat "$work/$out.last.txt" 2>/dev/null | head -n 8
