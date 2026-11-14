# Export, editable versions, checks and legends

`scripts/export_figure.py`, `scripts/panels.py`, `scripts/check_figure.py`,
`scripts/check_text.py`, `scripts/editable.py` and `scripts/enlarge.py` print their options
with `--help` and one JSON object with `--json`. Those that write a file write it next to the
input file unless you name the output with `-o`.

## Two questions before you convert

Ask them when the request does not answer them:

1. **Which slot is the figure for?** An in-text figure is sized by column width, single or
   double. A graphical abstract or a cover has its own size rule:
   `references/figure-recipes.md`.
2. **Was it made with an image-generation tool?** Then the publisher's AI policy applies,
   whatever the file format: `references/ai-image-policies.md`. If nobody can say how it was
   made, convert it as asked and put that open question, with the policy, in your hand-over.

A slide has no column and no print resolution: a picture that fills a widescreen slide is 16:9
and at least 1920 px wide. `scripts/check_figure.py --screen` checks a figure for a slide or a
blog without judging it for print. In PowerPoint a widescreen slide is 7.5 inches high,
540 pt: text in a picture that fills it has a size in points of its size in pixels x 540 /
the height of the picture in pixels. `scripts/check_text.py` works that out for a generated
figure on its `TYPE` line. Give the user that number for the smallest text; how small is too
small depends on their room.

## Which file does the user need?

| Need | Do |
|---|---|
| A chart for a journal | Nothing to convert: submit the vector PDF from `scistyle.save`. Ask it for `"eps"`, `"svg"` or `"tiff"` if the journal wants those. |
| A raster illustration as a journal file at print size | `uv run <skill-dir>/scripts/export_figure.py fig.png -f tiff --journal elsevier --column double --dpi 500` |
| More pixels in a PNG, TIFF or PDF, by interpolation and with no journal in mind | `uv run <skill-dir>/scripts/export_figure.py fig.png -f png --dpi 600` |
| Several raster panels as one figure with panel letters | `uv run <skill-dir>/scripts/panels.py a.png b.png c.png --rows 2,1 --journal elsevier --column double -f tiff --dpi 500` |
| Labels editable in PowerPoint or Keynote | `uv run <skill-dir>/scripts/editable.py fig.png --to pptx` |
| Labels editable in Illustrator, Inkscape or Figma; artwork stays one picture | `uv run <skill-dir>/scripts/editable.py fig.png --to svg-text` |
| Shapes editable too: recolour, move, delete | `uv run <skill-dir>/scripts/editable.py fig.png --to svg-vector` |
| To know whether a generated figure carries the texts that were asked for | `uv run <skill-dir>/scripts/check_text.py fig.png --labels labels.txt` |
| More pixels in a generated figure, with real detail and not interpolated | `uv run <skill-dir>/scripts/enlarge.py split fig.png`, a redraw of each tile by the image tool, then `uv run <skill-dir>/scripts/enlarge.py join fig.tiles`: `references/illustration.md`, section 5, step 6. Needs an image tool |

Make content changes first, then convert: a converted file can no longer be edited with the
image tool.

## Print resolution

Printed dpi = pixels / printed width in inches. A 2048 px image is 585 dpi at 89 mm and 292 dpi
at 178 mm. The minimum depends on the journal and on the kind of figure, which you pass to
`scripts/check_figure.py` as `--kind`:

- `line_art`: black lines and text on white, nothing coloured or shaded.
- `photo`: micrographs and photographs without lettering.
- `combination`: everything else, including coloured or shaded illustrations with labels. The
  default.

`scripts/export_figure.py` enlarges an image that is too small and never shrinks one. Its
resolution is 600 dpi unless you pass one, whatever the journal: pass the minimum that
`scripts/check_figure.py` reports. Without a width it brings the longer side to at least 1024,
2048 or 4096 px for 300, 600 or 1000 dpi.

When the result says `"upscaled": true`, tell the user: interpolation adds pixels, not detail,
so the file meets the number and not the quality. The check counts pixels and passes such a
file, so that note has to travel with it. The honest fixes are a larger original or a
narrower print width. For a generated figure `scripts/enlarge.py` makes the larger original
with the image tool itself, 1.6 to 2 times the size for four more generations.

The PDF it writes holds the picture as a lossless raster image, not vector artwork. A journal
that requires vector line art (Nature Portfolio) is not satisfied by any raster file. Both
`export_figure.py` and `check_figure.py` say when the bundled data lists the file format as not
accepted by the journal; pass that on.

## Multi-panel figures

`scripts/panels.py` arranges raster panels at a journal width. `--rows 2,1` puts the first two
panels in the top row and the third below; every row is as wide as the figure, and its panels
keep their aspect ratio and share one height, so nothing is cropped or stretched. The letters
are a, b, c or A, B, C as the journal prints them, in its font and size, in a band above each
row; `--labels` replaces them and `--no-labels` leaves them out. In a PDF the letters stay
text. A panel that carries a colour profile (Display P3, for one) is converted to sRGB, the
colour space of the figure.

Its report gives, for each panel, the resolution that the panel's own pixels reach at its
place, and names every panel enlarged by more than 1%, with the factor. Pass that on as you
would for `export_figure.py`. Every row spans the full width, so a panel alone in a row is
the widest: a panel with too few pixels belongs in a row with others, or needs a larger
original. Two single-column panels fill a double column untouched when the gap is the
difference between the double width and twice the single one (`--gap-mm 4` for Nature
Portfolio).

For charts, do not paste PNG previews together: make all panels in one plotting script
(`references/charts.md`), so that they stay vector and share one type size. If the user asks
for the pasted version anyway, make it and say what it costs: the text becomes pixels, and
each panel keeps its own type size.

## Editable versions

`scripts/editable.py` finds the horizontal text lines by OCR, erases them from the picture, and
puts each one back as real text in the same place.

- `pptx`: one slide, the picture with its text erased, one text box per label.
- `svg-text`: the same picture embedded as an image, labels as SVG text.
- `svg-vector`: the picture traced into coloured paths, labels as SVG text. The trace is an
  approximation: colours shift by a shade and edges are redrawn. It suits flat artwork;
  photographs and shaded renderings trace badly. Few journals list SVG, so it is a file for
  editing, not for submission.

Both SVG modes write `<name>.svg`: to keep both, name one of them with `-o`.

The first run downloads about 100 MB of Python packages (the OCR models are among them) and
takes a few minutes; tell the user before you start it. Later runs take about a second. It
works offline and switches off the telemetry of the OCR runtime (onnxruntime).

Its report lists every label it read, with the font size in pixels. Compare that list with the
original figure, label by label:

- **Skipped text.** Rotated, vertical, curved or very small text stays in the picture, counted
  under `skipped_rotated` or `skipped_low_confidence`. It is not editable.
- **Misread text.** The OCR model knows English and Chinese. It often gets Greek letters,
  subscripts, superscripts, accents and symbols wrong ("γ" read as "v", "H₂O" as "HO", "***" as
  other marks), and it does not cover Japanese, Korean or Cyrillic. A misread label replaces
  the correct pixels with wrong text, so correct each one: in an SVG every label is one `<text>`
  element inside `<g id="labels">`, which you can edit as text; in a PPTX, set the run's text
  with `python-pptx` (`shape.text_frame.paragraphs[0].runs[0].text = "..."` keeps the font,
  size and colour).
- **Fonts.** Every label becomes regular Arial at a size estimated for that label alone, so
  labels of one size can come out slightly different; bold and italic are lost, and text
  touching a line about as dark as itself comes out too large.
- **Backgrounds.** Text on a flat or smoothly shaded area erases cleanly; on stripes or texture
  it leaves a blurred patch.

List what did not convert when you hand the file over. To look at a converted file, render it
to an image: a headless browser screenshot for an SVG; for a PPTX the platform's preview tool
(on macOS, `qlmanage -t -s 1600 -o <folder> figure.pptx`).

Converting changes the file format, not the origin of the picture. A traced or re-typed
AI-generated figure is still an AI-generated figure for every disclosure rule.

## Text of a generated figure

```text
uv run <skill-dir>/scripts/check_text.py fig.png --labels labels.txt
```

`labels.txt` holds the texts the figure should carry, one per line and once for each place a
text stands; a label that the figure sets on several lines is still one line there. For a few
labels, repeat `--label "..."` instead. The script reads the figure with OCR, offline; its
first run downloads the same packages as `scripts/editable.py`.

What each line of the report means, and what to do about it, is in
`references/illustration.md`, section 5, step 1; `--crops look/` writes the places to look
at. With `--json`, each label carries `found`, `listed`, `closest`, `second` and `crop`.
`second` says what the reading of its place, cut out and enlarged, did: `found`, `differs`,
`merged` (one letter short in a doubled letter or a run of thin ones), `same` (read twice and not
spelt otherwise) or null; `crop` is the file or null, and `extra_crops` lists the files of
the extra texts. The exit status is 0 whenever the check ran: read the `OVERALL` line.

## Checks before submission

```text
uv run <skill-dir>/scripts/check_figure.py fig.png --journal cell --column single --kind combination --previews checks/
```

It reports six checks as pass, warn or fail: file format, effective dpi at the printed width,
transparency, colour mode, greyscale legibility and colour-blind safety. It reads pixels: for
a PDF or an SVG, also one that only wraps a picture, give it the PNG the file was made from. The two colour checks
say skip when the figure has no two colours strong and widespread enough to compare, as a
figure in faint tints has not: then nothing was judged, the `OVERALL` line says so, and the
previews are the check. A
resolution under a minimum that the publisher states is a fail; under a common value, where
no publisher rule applies, it is a warn. `--min-dpi 300` replaces the preset's minimum with
the one of the guide that does apply: a graphical abstract's, a thesis's, a report's. The
exit status is 0 whenever the checks ran: read the `OVERALL` line. Report each warn and fail
about the file the user will submit, with its detail; do not summarise them away. A `NOTE`
line states a rule of the journal preset, whatever the figure looks like.

- The two colour checks compare the figure's main colours only. They are a screen, not a
  verdict: open the files that `--previews` writes (`grayscale.png`, `deuteranopia.png`,
  `protanopia.png`, `tritanopia.png`) and look whether anything that carries meaning merges.
- `--look` adds two lines that no check judges: `FILLS`, how strong the colours of the light
  areas are (tinted boxes, cards, cell bodies) and how much of the figure is in strong
  colour; and `LINES`, how heavy the long straight lines are (outlines, frames, arrow
  shafts), in pixels to a tenth, with the hairline and the heavy weight for a picture of that
  size. What a generated figure should read, and the edit that mends it, is in
  `references/illustration.md`, section 5, step 3.
- The script does not judge layout. Look yourself: empty margins around or inside a figure
  waste its print size, and a graphical abstract needs the journal's proportions. No script
  here crops: cut the margins with a few lines of Pillow before exporting
  (`uv run --with pillow python crop.py`).
- The script cannot see font sizes. For a generated figure, `scripts/check_text.py` with
  `--width-mm` prints them on its `TYPE` line. For any other figure, measure the height in
  pixels of a capital letter in the smallest label (crop and enlarge the label to count); the font size in points is about that
  height x 100 / the effective dpi, since a capital is roughly 0.72 of the font size. If you ran
  `scripts/editable.py`, its report gives each label's font size in pixels: points = pixels x
  72 / the effective dpi. A Chinese character fills about 0.9 of its font size: points are
  about its height x 80 / the effective dpi. Compare with the journal's minimum from
  `uv run <skill-dir>/scripts/scistyle.py --list`, or for a graphical abstract with the size its
  own guide gives.

## Figure legend

Look at the figure and write the legend from what is in it and what the user told you:

1. A title sentence that states the finding or the subject.
2. One sentence per panel, in panel order, naming what is plotted or drawn.
3. For data: what the points, bars and error bars are, n per group, the test and correction if
   any. For an illustration: what arrows, colours and symbols mean, and abbreviations spelled out.
4. `[placeholder]` for every fact you do not have. Never fill in n, a statistic, a concentration
   or a method from the picture alone.

Give plain text, and a LaTeX `\caption{...}` when the manuscript is LaTeX.

## Disclosure

When an image tool made or changed the figure, give the user what a publisher asks for: the
tool's name and version as your host reports them (say so when it reports no version), what
it was used for, and the brief with every edit instruction.
When you wrote the code that drew a chart or a diagram, the AI tool is you: give your name and
model as your host reports them, say that it wrote the plotting code, and hand over the script,
which is the reproducible method. `references/ai-image-policies.md` says where each publisher
wants it stated.

The publishers' rules on AI-generated images were written about image generators. The bundled
table does not say whether a schematic that a script drew counts as one, and that is the
journal's decision, not yours: report what was done, quote the rule, and name the open
question, so that the user can ask the journal before submitting.
