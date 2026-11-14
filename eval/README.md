# eval: measuring and regression tools for the skill

> The version number was reset to 0.1.0 on 2026-11-14 for the first public release. The 0.4.x–0.5.x numbers below are those of the internal iterations before it; 0.5.2 is what became 0.1.0.

These are the scripts used during development to validate the skill. They are not published with the npm package (`package.json` lists only `bin`, `lib` and `skills` in `files`). Sample figures, generated figures and session logs are not in the repository either; the scripts find them through the variables in `env.sh`:

| Variable | Default | What it is |
|---|---|---|
| `SCIFIG_SKILL` | this repository's `skills/scifig` | the skill the Codex sessions are given |
| `SCIFIG_GEN` | `eval/runs` | the output of end-to-end runs, one folder per session (figures, `labels.txt`, `run.log`) |
| `SCIDRAW_SAMPLES` | `eval/samples` | SciDraw's public sample figures, used only for comparison |
| `UV_CACHE_DIR` | `~/.cache/uv` | the uv cache, which a session must be allowed to write |

`eval/runs` and `eval/samples` hold local data and are not committed. If your data lives elsewhere, make them symbolic links, for example `ln -s ~/data/scifig-runs eval/runs`.

## sessions: real generations (they spend image quota)

All of these run `codex exec` on your machine, with your own Codex account and its image generations, so count the generations before you start.

- `run_e2e.sh WORKDIR REQUEST_FILE`: a fresh session that has only the skill and the request, and works from the brief to the delivered file. At the end it lists every place where the skill was unclear or wrong, or cost an extra generation (`NOTES ON THE SKILL`).
- `run_fix.sh WORKDIR REQUEST_FILE`: gives a fresh session a finished but unverified figure (`figure.png`, `brief.txt`, `labels.txt`), to see whether it verifies and corrects it as the skill says.
- `run_brief.sh WORKDIR BRIEF_FILE OUTPUT_NAME`: passes a brief to the image tool as it is, for one generation.
- `run_edit.sh WORKDIR SOURCE_IMAGE OUTPUT_NAME INSTRUCTION`: one edit with the image tool.
- `redraw_tiles.sh TILEDIR`: redraws every tile that `enlarge.py split` wrote, one generation per tile.

## text: regression of the text check

- `regress_text.sh OUT_DIR [SCRIPTS_DIR]`: runs `check_text.py` on every end-to-end figure under `SCIFIG_GEN` that has a `labels.txt`, and stores one JSON report per figure. The scripts default to this repository's; run it with a copy of an older version to make a baseline. About a minute and a half for 100 figures.
- `compare_runs.py BASELINE_DIR NEW_DIR`: compares two runs label by label, and lists the labels whose verdict changed, with the totals. Run it after every change to `check_text.py`: the 0.5.1 baseline has 5 `DIFFERS` in 98 figures ("Questoin", "ratiio" twice, 间题, "Takeaway:"), all real typos, and none of them may be lost.
- `stress_cards.py OUT_DIR [SCRIPTS_DIR]`: draws correct labels in cards (5 typefaces, 4 sizes, PNG and JPEG) and reports every `DIFFERS`, all of them false. 0.5.1 had 3 of 1,040; 0.5.2 has none.
- `stress_edges.py OUT_DIR [SCRIPTS_DIR]`: the same with a card border 3 px or 6 px left of the label, or none. 0.5.1 had 31 false verdicts in 1,260; 0.5.2 has 6, all a letter that OCR put in inside a word. Inside a word the rules go by the first reading, because that is how an extra letter written by the image tool shows.
- `vary.py FIGURE TEXT`: reads the same text in many crops and at several enlargements, to show how OCR's reading varies. The doubled-letter rule was measured with it.

## measure: the look, against SciDraw's samples

The scripts directory argument is always `$SCIFIG_SKILL/scripts` (`measure.sh` passes it), and groups are written `NAME=PATH[,PATH...]`; a path that is a folder stands for every PNG in it.

- `colour_stats.py`: the lightness and chroma (CIELAB) of the fills, and the share in strong colour.
- `content_stats.py`: the lines and characters of text that OCR reads.
- `type_size.py`: the type size, as a share of the figure's height and in points on a slide the figure fills.
- `stroke_fine.py`: line weight, measured as `check_figure.py --look` measures it, to 0.1 px.
- `element_stats.py`: the number and area of icon-sized pictorial shapes.
- `bold.py`: how solid the pictures are, and the area in visible colour.
- `detail.py`: detail: how many parts the drawing is made of, the share of lines with a gloss in parentheses, and the total outline length.
- `groups.sh`: the groups of the 2026-11-13 comparison (`sd-*` are SciDraw's samples, `our-*` our figures). Change its paths for a new round.
- `measure.sh TOOL [--each]`: runs one measurement over every group of `groups.sh`.
- `measure_one.sh NAME=PATH ...`: measures how much a few figures carry, their colour, type size and line weight, in one go.
- `density.py`: compares the samples and our figures in bands of text lines; it reads `type.out`, `colour.out`, `bold.out` and `stroke-each.out` as written by `measure.sh`.
- `crops.py OUT HEIGHT LABEL=PATH:x0,y0,x1,y1 ...`: cuts the same relative region out of several figures and sets them side by side, to compare detail.

Do not judge the look by eye alone: the over-saturated fills went unnoticed when looking at the figures one by one, and were found by measuring. Validate a measurement before you trust it, too: line weights counted in whole pixels were read wrong at first.
