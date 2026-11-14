# Diagrams drawn in code

A figure that explains normally comes from the image tool (`references/illustration.md`), boxes
and arrows included. Draw it in code when one of these holds:

- **Every count must be auditable.** Study and participant flow diagrams (PRISMA, CONSORT): the
  numbers are results, and a reviewer adds them up.
- **It is a formal notation.** Circuit diagrams, plasmid maps, phylogenetic trees, Punnett
  squares, Venn diagrams.
- **The image tool is not an option.** The host has none, the destination does not accept
  AI-generated images, or the user asks for vector artwork.
- **A generated picture needs real text.** See "Real text over a picture" below.

A code-drawn diagram is a vector PDF with editable text, at the size and in the font of its
destination. It is plainer than a generated figure: rectangles, lines and type. Where the user
could have had either, say so in the hand-over.

## Steps

1. **Collect the content.** Every box text, count and link comes from the user. For a standard
   template, take the box order and wording from its official source when you have web access
   (PRISMA: https://www.prisma-statement.org/prisma-2020-flow-diagram, CONSORT:
   https://www.consort-spirit.org/); otherwise say that the wording is from memory. Leave out
   template items the user gave no value for, and list them in your hand-over.
2. **Check the numbers before drawing.** Counts that should add up must add up (identified
   minus removed equals screened, and so on). Report a mismatch to the user; do not repair it.
3. **Language.** Text in the figure is in the language of the publication. When you translate
   the user's wording, list each translation in the hand-over.
4. **Write a script** in the user's workspace, next to copies of `scripts/scistyle.py` and
   `scripts/journals.py`, and run it with `PYTHONDONTWRITEBYTECODE=1 uv run <script>.py`.
5. **Look at the PNG** and compare every string and number with the request. If the diagram
   uses colours other than black, white and grey, run `scripts/check_figure.py` on the PNG and
   read its two colour lines.
6. **Deliver** the PDF, the PNG preview, the script with its two helper files, a legend draft
   and a note on AI assistance (`references/export-and-checks.md`: "Figure legend" and
   "Disclosure"). For a journal, compare the formats with its `accepts` and its note in
   `uv run <skill-dir>/scripts/scistyle.py --list`: when PDF is not listed or another format is
   preferred, add that format to `formats` and say so.

## Example

```python
# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib", "numpy"]
# ///
"""Study selection flow. Every count is the user's, and they are checked before drawing."""
from pathlib import Path

import scistyle  # scistyle.py and journals.py sit next to this file

n = {"found": 1300, "duplicates": 314, "screened": 986, "excluded": 720, "assessed": 266, "ineligible": 210, "included": 56}
assert n["found"] - n["duplicates"] == n["screened"]  # counts that should add up, do
assert n["screened"] - n["excluded"] == n["assessed"]
assert n["assessed"] - n["ineligible"] == n["included"]

scistyle.use("elsevier")
fig, ax = scistyle.canvas("single", 74)  # a blank page in millimetres: 90 x 74 mm
steps = [  # what happens at each step, and what leaves the flow there
    (f"Records identified\n(n = {n['found']:,})", f"Duplicates removed\n(n = {n['duplicates']:,})"),
    (f"Records screened\n(n = {n['screened']:,})", f"Records excluded\n(n = {n['excluded']:,})"),
    (f"Reports assessed\n(n = {n['assessed']:,})", f"Reports excluded\n(n = {n['ineligible']:,})"),
    (f"Studies included\n(n = {n['included']:,})", None),
]
width, height, gap = 38, 11, 9  # every box has one size, so the columns line up
previous = None
for row, (text, removed) in enumerate(steps):
    y = 74 - 2 - height - row * (height + gap)  # from the top of the page downwards
    step = scistyle.box(ax, 2, y, width, height, text)
    if removed:
        scistyle.connect(ax, step.right, scistyle.box(ax, 50, y, width, height, removed).left)
    if previous:
        scistyle.connect(ax, previous.bottom, step.top)
    previous = step
print(scistyle.save(fig, Path(__file__).parent / "flow"))  # refuses to save if a text overflows its box
```

## The helpers

- **`scistyle.canvas(width, height_mm)`** is a page in millimetres, measured from its
  bottom-left corner, with nothing laid out automatically. The width is "single", "double" or
  millimetres. `scistyle.py --list` also shows the widths between one and two columns that a
  journal names (`other_mm`); a diagram that looks sparse across two columns often fits one.
- **`scistyle.box(ax, x, y, width, height, text)`** draws a frame of that size with the text
  centred in it, and returns the points to attach lines to: `.left`, `.right`, `.top`,
  `.bottom`. Give the boxes of a row or a column one size. `align="left"` sets a list inside a
  box from the left; `fill="0.9"` shades it light grey (any matplotlib colour). `scistyle.save`
  raises an error while the text of a box is larger than its box: widen the box, break the
  line, or shorten the text. Nothing checks text you place with `ax.text`, or the page edge.
- **`scistyle.connect(ax, start, end)`** draws a line that ends in an arrow head. More points
  make corners: `connect(ax, a.bottom, (x, y), b.top)` is an elbow. `head="bar"` ends in a flat
  bar (inhibits), which stands 1 mm before the end point so that it shows in front of a box;
  `head="none"` is a plain line, for branches that join.
- **Layouts.** A flow with exits is the example. A roadmap has one row per stage, the stage
  name in a shaded box in the left margin, parallel work side by side, and connectors that
  branch and join through elbows. A framework has variables as boxes and hypotheses as
  connectors with a label (`ax.text`) beside them.

## Size and type

- **A journal:** `scistyle.use(<journal>)` and a column width, as for charts.
- **A thesis, a grant application, any document a journal does not typeset:** make the canvas
  as wide as the page's text area, in millimetres, and set the type a little under the body
  text, in the document's typefaces:
  `scistyle.use("default", font_pt=10.5, fonts=["Times New Roman", "Songti SC"])`. `fonts`
  names installed fonts, the one for Latin text first; on macOS 宋体 is "Songti SC" and 黑体
  "Heiti SC", and `matplotlib.font_manager.get_font_names()` lists what a system has. Word
  takes the PNG, which `scistyle.save` writes at 600 dpi unless you pass `dpi=`; LaTeX takes
  the PDF.
- **A slide:** PowerPoint's widescreen page is 338.7 x 190.5 mm; size the canvas as the part of
  it the figure will fill, and use the type size of the slide's own text.
- **Chinese, Japanese and Korean text** needs nothing extra: a character the journal font
  lacks is drawn in the first font of `scistyle.CJK_FONTS` that is installed (Heiti SC on
  macOS). Empty squares in the PNG mean none of those fonts is installed.
- **Subscripts, superscripts and Greek letters** are written `"IC$_{50}$"`, `"mm$^2$"`,
  `r"$\mu$m"` and come out in the text font. A subscript or superscript is 70% of the type
  size, 4.9 pt at 7 pt: say so in the hand-over when that is under the journal's minimum.

## Real text over a picture

To label a picture with exact text, the picture should carry no text and no leader lines.

1. Make the canvas as wide and high as the picture will be shown, and put the picture on it:
   `ax.imshow(pixels, extent=(0, width_mm, 0, height_mm), aspect="auto")`.
2. For a scratch render, pass `grid_mm=10` to `scistyle.canvas`: numbered grid lines let you
   read the position of each structure off the picture. Leave it out of the final render.
3. Add each label with its own line:
   `ax.annotate(text, xy=structure, xytext=label_position, arrowprops=dict(arrowstyle="-"))`.
4. Look at the result and check each line against the structure it ends on.

The same serves for one text that an image tool will not write right
(`references/illustration.md`, section 5, step 4): the rest of the picture keeps its text,
and the one line is set with `ax.text` at its place, in the weight and size of its
neighbours. `scripts/check_text.py` gives the size of the type in pixels.

## Formal notations

Each of these was rendered on 2026-11-11 with matplotlib 3.11:

| Diagram | Library | How |
|---|---|---|
| Circuit diagram | `schemdraw` | It makes its own figure, so leave `scistyle.use` out of that script: `drawing.config(font="Arial", fontsize=7)`, then `drawing.save("circuit.pdf")`. |
| Plasmid map | `dna_features_viewer` | `CircularGraphicRecord(sequence_length, features).plot()` |
| Phylogenetic tree, cladogram | `biopython` | `Bio.Phylo.draw(tree, axes=ax, do_show=False)` |
| Venn diagram | `matplotlib-venn` | `venn2` or `venn3` with `ax=ax` |

Grids and curves need no library. A Punnett square is a loop of `scistyle.box` calls. A bell
curve or an action potential is a line chart: `references/charts.md`.
