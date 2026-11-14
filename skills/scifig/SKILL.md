---
name: scifig
description: Use when asked to draw, generate, redraw or edit a scientific figure (graphical abstract, mechanism, pathway, workflow, roadmap, framework, model or system architecture, flow diagram, schematic, cover, labelled diagram), plot research data as a journal-style chart, combine panels into one figure, convert a figure to TIFF, PDF, SVG or PPTX or make its labels editable, enlarge a generated figure to a higher resolution, check a figure against journal requirements (dpi, column width, colour-blind safety), or write a figure legend.
---

# scifig

Scientific figures for papers, theses and slides. You do the thinking: the brief, the
plotting code, the checks, the legend. A figure that explains comes from **your host's own
image-generation tool**; this skill calls no image API. The bundled scripts measure, compare
and convert.

## Pick the route

| They want | Route | Read |
|---|---|---|
| A figure that explains: graphical abstract, mechanism, pathway, workflow, roadmap, framework, model or system architecture, labelled diagram, cover. From an idea, an abstract, a sketch, or an image to change | Your host's image tool, from a brief you write | `references/illustration.md` |
| A chart of numbers: CSV, Excel, a pasted table | Plotting code with `scripts/scistyle.py` | `references/charts.md` |
| One of the diagrams that must be code (below) | Drawing code with `scripts/scistyle.py` | `references/diagrams.md` |
| A submission file, a larger file, one multi-panel figure, or editable labels and shapes, from a finished figure | `scripts/export_figure.py`, `scripts/enlarge.py`, `scripts/panels.py`, `scripts/editable.py` | `references/export-and-checks.md` |
| A pre-submission check, or a legend | `scripts/check_figure.py` | `references/export-and-checks.md` |

**Image tool or code.** Boxes, arrows and text are no reason to draw in code. An architecture,
a roadmap or a framework goes to the image tool too, and comes back with a designed finish.
Image tools write dozens of labels correctly, Chinese and formulas included;
`scripts/check_text.py` reads them back. Draw in code only when:

- it is a chart of data: an image model invents bars, axes and values;
- every count must be auditable: PRISMA and CONSORT flow diagrams;
- it is a formal notation: circuit, plasmid map, phylogenetic tree;
- your host has no image tool, the destination does not accept AI-generated images, or the
  user asks for vector artwork.

## Every figure

1. **Destination first.** Journal, thesis, slide or poster decides the width, fonts, resolution
   and file type. For a generated figure it also decides whether the figure may be used at all:
   `references/ai-image-policies.md` (dated; several publishers restrict them).
2. **Journal rules: bundled presets before the web.** Column widths, fonts, minimum dpi and
   accepted formats of ten publishers are bundled; `scripts/scistyle.py --list nature` prints
   one with its verification date, `--list` all. Use them and pass that date on. Look online
   only for rules they lack: an unlisted journal, or a size rule of its own (graphical
   abstract, cover).
3. **Look at what you made.** Open every output image and compare it with the request before
   you call it done.
4. **Hand over facts.** File paths; pixel size and print size; what you checked; what you could
   not check; what you assumed. You cannot vouch for the science: the user must.

## Running the scripts

```text
uv run <skill-dir>/scripts/<name>.py --help
```

`<skill-dir>` is the folder that holds this file. `uv` installs each script's Python packages
on first use, which needs network access and its cache folder: if your sandbox blocks either,
ask for that permission instead of rewriting the script. Without `uv`, tell the user to install
it (https://docs.astral.sh/uv/).
