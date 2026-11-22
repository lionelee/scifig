# Charts from data

A chart is plotting code run on the user's numbers. Never use an image tool for it.

## Steps

1. **Read the data.** Print the columns, their types, the row count and the rows per group.
   Note what one row is (a replicate, a subject, a time point). Use the values as given: no
   invented, imputed, rounded or dropped values. If a row must be excluded, say which and why.
2. **Choose the chart** from the table below, or use the one the user named. If the same
   subject or replicate id appears in every group and the user did not say whether the
   measurements are paired, plot them as independent and put the question in your hand-over.
3. **Write a plotting script** in the user's workspace. Copy `scripts/scistyle.py` and
   `scripts/journals.py` from this skill next to it, so the script reruns without the skill.
4. **Run it** with `PYTHONDONTWRITEBYTECODE=1 uv run <script>.py`, which keeps a `__pycache__`
   folder out of the user's workspace.
5. **Look at the PNG.** Fix clipped labels, overlapping text, a legend covering data. Then run
   `scripts/check_figure.py` on it with the journal and column, and read its `grayscale` and
   `colorblind` lines. The PNG is only a preview of the PDF: its `format` and `effective_dpi`
   lines describe the preview, not the file the user submits. Leave them, and an `OVERALL` that
   only they cause, out of your report.
6. **Deliver** the vector PDF, the PNG preview, the script with its two helper files, a legend
   draft and a note on AI assistance (`references/export-and-checks.md`: "Figure legend" and
   "Disclosure"). The PDF is the submission file: its page is the figure at print size, and its
   text is embedded as text, so it stays editable (`pdfinfo` and `pdffonts` confirm both where
   poppler is installed). Compare the formats with the journal's `accepts` and its note in
   `scistyle.py --list`: when PDF is not listed or another format is preferred, add that
   format to `formats` and say so.

## The style helper

```python
scistyle.use(journal="nature", palette="okabe_ito")  # fonts, sizes, colours; text stays text in PDF and SVG
fig, axes = scistyle.figure(width="double", aspect=0.4, ncols=2)  # "single", "double" or millimetres
scistyle.panel_labels(axes)                            # a, b, c or A, B, C, as the journal prints them
scistyle.save(fig, "fig2", formats=("pdf", "png"))     # also "tiff", "svg", "eps"; returns the paths
```

For a thesis, a grant application or a slide, pass the width in millimetres, and give
`scistyle.use` the type size and the typefaces of that document, the one for Latin text first:
`scistyle.use("default", font_pt=10.5, fonts=["Times New Roman", "Songti SC"])`.

Write subscripts, superscripts and Greek letters as `"IC$_{50}$"`, `"mm$^2$"`, `r"$\mu$m"`:
they come out in the text font. A subscript or superscript is 70% of its label's size, 4.9 pt in a
7 pt label, and so are the exponents on a log axis, which
`ax.xaxis.set_major_formatter("{x:g}")` replaces with plain numbers. Say so in the hand-over
when that is under the journal's minimum.

`uv run <skill-dir>/scripts/scistyle.py --list` prints every journal preset (widths, fonts,
font sizes, dpi, accepted formats) and palette; with journal keys after it, `--list nature cell`,
only those presets. The presets come from a dated data set
(`references/journal-figure-requirements.json`); for a journal that is not listed, look up its
author guide and pass the width in millimetres. Leave the figure size and font sizes to the
helper: a figure made at print size needs no rescaling, so its type stays the size the journal
asked for.

## Example

```python
# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib", "numpy", "pandas"]
# ///
"""Relative expression by group: every replicate, with the mean and s.d."""
from pathlib import Path

import numpy as np
import pandas as pd

import scistyle  # scistyle.py and journals.py sit next to this file

here = Path(__file__).parent  # read and write next to the script, wherever it is run from
scistyle.use("nature")
data = pd.read_csv(here / "expression.csv")
groups = list(data["group"].unique())  # the order of the file, not alphabetical

fig, ax = scistyle.figure("single", aspect=0.7)
for x, name in enumerate(groups):
    values = data.loc[data["group"] == name, "relative_expression"]
    spread = np.linspace(-0.15, 0.15, len(values))  # side by side, so no point hides another
    ax.scatter(x + spread, values, s=10, color="C0", zorder=3)  # one colour: the axis names the groups
    ax.errorbar(x, values.mean(), yerr=values.std(ddof=1), color="black", capsize=3, zorder=2)
    ax.hlines(values.mean(), x - 0.2, x + 0.2, color="black", zorder=2)
ax.set_xticks(range(len(groups)), groups)
ax.set_ylabel("Relative expression")
ax.set_ylim(bottom=0)
print(scistyle.save(fig, here / "expression"))
```

## Which chart

| The question | Chart | Notes |
|---|---|---|
| Do groups differ? Few values per group | Dot plot: every value, plus a mean or median line; beeswarm when points would overlap | Bars hide the data when n is small. `seaborn.swarmplot` |
| Do groups differ? Many values | Box, violin or raincloud, with the points; ridgeline for many groups | |
| A count or a total per category | Bar chart; with error bars when a bar is a mean | Bars start at zero. |
| Means with their uncertainty | Error bar plot | Say what the bars are. |
| Did each subject change? | Paired dot plot with connecting lines | |
| Each subject's change, ranked | Waterfall plot | One bar per subject, sorted by value. |
| How does it change over time? | Line graph or time series, with an error band; growth curve with a fitted model; stacked area for a composition over time | Dates go on a date axis. |
| Response to a dose or a concentration | Dose-response curve on a log x axis with a four-parameter fit; enzyme kinetics with a Michaelis-Menten fit; standard curve with the fit that reads the unknowns | `scipy.optimize.curve_fit`. Every replicate as an open symbol at its own concentration. Report the model, each parameter with its interval, and which IC50 it is: the curve's midpoint or the 50% crossing. |
| Are two variables related? | Scatter, with a regression line and its interval; bubble chart when a third variable sets the size; hexbin for thousands of points | |
| How are values distributed? | Histogram, density, ECDF, ogive (cumulative frequency), Q-Q; stem-and-leaf for a small sample | `scipy.stats.probplot` for Q-Q. |
| Several measures per item | Radar chart | Readable for three or four items at most. |
| What is it made of? | Stacked bar or stacked area | |
| Many variables by many samples | Heatmap, with a dendrogram if clustered; correlation matrix; calendar heatmap for one value per day | A sequential colour map; a diverging one only for signed data. `scipy.cluster.hierarchy` |
| Differential expression | Volcano (log2 fold change against -log10 p), MA plot; enrichment plot for gene sets | Draw the thresholds; label only the top genes. |
| Survival | Kaplan-Meier step curves, censor ticks, numbers at risk | `lifelines`, with `"pandas<3"` in the dependencies; see below. |
| Meta-analysis | Forest plot, funnel plot | |
| Classifier quality | ROC, precision-recall, calibration curve, confusion matrix | `scikit-learn` |
| Do two methods agree? | Bland-Altman | |
| Genome-wide association | Manhattan, Q-Q | |
| Set overlaps | Venn for two or three sets, UpSet for more | `matplotlib-venn`; `upsetplot` with pinned versions, see below. |
| Flows between stages | Sankey | `matplotlib.sankey` draws one node with its inflows and outflows; a multi-stage flow needs another library. |

Libraries, each rendered on 2026-11-11 with matplotlib 3.11, pandas 3.1 and numpy 2.5:

- `scipy`, `scikit-learn`, `matplotlib-venn` and the seaborn functions that take `ax=` work with
  the style helper as they are.
- A function that makes or lays out its own figure clashes with the helper's automatic layout:
  seaborn's `clustermap` raises "Colorbar layout of new layout engine not compatible", and its
  `jointplot`, `pairplot`, `catplot` and `lmplot`, like `upsetplot`, warn. Make and save such a
  figure with that layout switched off, and set its print size yourself:

  ```python
  with plt.rc_context({"figure.constrained_layout.use": False}):
      grid = sns.clustermap(table, cmap="vlag", center=0)
      grid.figure.set_size_inches(88 / 25.4, 88 / 25.4)  # width and height in millimetres
      scistyle.save(grid.figure, here / "clustered")
  ```
- `lifelines` needs `"pandas<3"` in the script's dependencies. Without it uv installs an old
  lifelines release next to pandas 3, a pair the library no longer supports and in which its
  numbers-at-risk table fails. With it, `fit.plot_survival_function(ax=ax, show_censors=True)`
  draws a curve and `add_at_risk_counts(*fits, ax=ax, rows_to_show=["At risk"])` adds the rows.
- `upsetplot` fails unless the script's dependencies also list `"pandas<3"` and `"numpy<2.4"`.

A library that fails for you with newer versions is not a reason to change the data or the
chart type: pin an older version in the script's dependencies, or draw the chart with plain
matplotlib.

Several panels: `scistyle.figure("double", ncols=2)`, then `scistyle.panel_labels(axes)`. One
panel of a larger figure, made on its own: give it the width it will have there and its letter,
`scistyle.panel_labels(ax, labels=["b"])`, and say in the hand-over that the panels still have
to be joined, best in one script.

## What the reader must be told

- **Error bars.** Say what they are (s.d., s.e.m., 95% interval) and the n behind each, in the
  legend draft.
- **Statistics.** Add p-values or significance marks only when the user asked for them or told
  you the design: independent or paired, biological or technical replicates. Then name the test
  and the correction in the legend.
- **Axes.** Units in the axis label. Bars start at zero. Name a log axis in the legend draft.
- **Language.** Text in the figure is in the language of the publication, whatever language
  the request was in. When you translate the user's wording, list each translation in the
  hand-over. Chinese, Japanese and Korean text needs no font setting: the helper falls back to
  an installed font for those characters.
- **Colour.** Use colour where it tells series apart, from the palette that `scistyle.use` set;
  groups already named on an axis share one colour. When colour alone separates more than
  three series, add a second cue (marker shape, line style, direct labels): the greyscale check
  will ask for it.
- **AI assistance.** Some publishers ask authors to report AI-written plotting code in Methods:
  `references/ai-image-policies.md` has each publisher's rule, and "Disclosure" in
  `references/export-and-checks.md` says what to hand over. The script you deliver is the
  reproducible method they ask for.
