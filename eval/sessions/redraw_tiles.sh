#!/bin/zsh
# Usage: redraw_tiles.sh TILEDIR
# Has Codex's image tool redraw every tile of a folder that enlarge.py split wrote, all at once, with the
# instruction of references/illustration.md, section 5, step 6. One generation per tile.
set -u
dir=$1
instruction="Redraw this picture exactly as it is, as a sharper copy. It is one part of a larger figure, so nothing may move: keep every element, text, line, icon and colour at exactly the same position and the same size relative to the picture. Shapes and lines that are cut off at an edge stay cut off at the same place. Add nothing, remove nothing, add no margins, re-centre nothing, change no wording. Render crisp text and clean hairlines, each line as fine relative to the text as it is now."
for tile in "$dir"/tile-*.png; do
  n=${${tile:t:r}#tile-}
  ${0:A:h}/run_edit.sh "$dir" "tile-$n.png" "redraw-$n" "$instruction" > "$dir/redraw-$n.run.txt" 2>&1 &
done
wait
for f in "$dir"/redraw-*.run.txt; do echo "${f:t}: $(head -c 150 "$f" | tr '\n' ' ')"; done
