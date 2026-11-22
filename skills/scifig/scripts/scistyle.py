# /// script
# requires-python = ">=3.10,<3.15"
# dependencies = ["matplotlib", "numpy"]
#
# [tool.uv]
# # The packages as they were on the day these scripts were tested: a later release cannot change their results.
# exclude-newer = "2026-11-14T00:00:00Z"
# ///
"""Journal-aware matplotlib defaults for publication figures.

    import scistyle

    scistyle.use("nature")
    fig, axes = scistyle.figure("double", aspect=0.4, ncols=2)
    ...
    scistyle.panel_labels(axes)
    scistyle.save(fig, "fig1")

    fig, ax = scistyle.canvas("double", 100)   # a blank page in millimetres, for diagrams

`uv run scistyle.py --list` prints the journal presets and the palettes as JSON.
"""
import argparse
import json
import logging
import string
import sys
from types import SimpleNamespace

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.layout_engine import PlaceHolderLayoutEngine
from PIL import Image  # Pillow comes with matplotlib

if __name__ == "__main__":
    sys.dont_write_bytecode = True  # as a command, leave no __pycache__ next to this file

import journals

# Colour-blind-safe palettes, ordered for use as a colour cycle.
PALETTES = {
    # Okabe & Ito. Blue, orange and bluish green come first because they are at least 10 L* apart,
    # so up to three series also survive greyscale print.
    "okabe_ito": ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#56B4E9", "#CC79A7", "#F0E442", "#000000"],
    # Paul Tol.
    "tol_bright": ["#4477AA", "#EE6677", "#228833", "#CCBB44", "#66CCEE", "#AA3377", "#BBBBBB"],
    "tol_muted": [
        "#CC6677", "#332288", "#DDCC77", "#117733", "#88CCEE", "#882255", "#44AA99", "#999933", "#AA4499",
    ],
}
FORMATS = ("pdf", "png", "tiff", "svg", "eps")
# Fonts for Chinese, Japanese and Korean text. A character the journal font lacks is drawn in the
# first of these that is installed. The first three were checked on macOS, where they embed in a
# PDF as TrueType; PingFang SC and Hiragino Sans GB are left out because viewers flag their PDFs.
CJK_FONTS = ["Heiti SC", "Songti SC", "Arial Unicode MS", "Microsoft YaHei", "SimHei", "Noto Sans CJK SC"]
# Those fonts mostly have no bold face; matplotlib would say so for every bold label in Latin script.
logging.getLogger("matplotlib.font_manager").addFilter(lambda record: "Failed to find font weight" not in record.getMessage())

_journal = "default"  # set by use(); figure(), panel_labels() and save() read it


def use(journal="default", palette="okabe_ito", font_pt=None, fonts=None):
    """Apply a journal preset and a palette to matplotlib's rcParams; return the preset.

    font_pt and fonts replace the preset's type size and typefaces: for a thesis, a grant
    application or a slide, whose figures follow that document and not a journal. fonts names
    installed fonts, the one for Latin text first: ["Times New Roman", "Songti SC"]. Also selects
    the Agg backend: this helper only ever renders to files.
    """
    global _journal
    preset = journals.get(journal)
    if palette not in PALETTES:
        raise ValueError(f"unknown palette {palette!r}; choose from: {', '.join(PALETTES)}")
    installed = {font.name for font in font_manager.fontManager.ttflist}
    missing = [name for name in fonts or () if name not in installed]
    if missing:
        raise ValueError(
            f"font not installed: {', '.join(missing)}; matplotlib.font_manager.get_font_names() lists the ones that are"
        )
    default = journals.get("default")
    font_pt = font_pt or preset["font_pt"] or default["font_pt"]
    _journal = journal
    matplotlib.use("Agg")
    matplotlib.rcParams.update({
        "font.family": [*(fonts or ["sans-serif"]), *(name for name in CJK_FONTS if name in installed)],
        "font.sans-serif": [*(preset["fonts"] or default["fonts"]), "DejaVu Sans"],
        "font.size": font_pt,
        "axes.titlesize": font_pt,
        "axes.labelsize": font_pt,
        "xtick.labelsize": font_pt,
        "ytick.labelsize": font_pt,
        "legend.fontsize": font_pt,
        # Subscripts, superscripts and Greek letters written as "$...$" in the text font, upright,
        # instead of matplotlib's own maths font.
        "mathtext.default": "regular",
        "axes.prop_cycle": matplotlib.cycler(color=PALETTES[palette]),
        "axes.linewidth": 0.6,
        "lines.linewidth": 1.0,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "legend.frameon": False,
        # Embed fonts as text, not outlines, so labels stay editable in vector files.
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        # No hinting: a raster preview then sets its glyphs where the vector file does. It also keeps
        # macOS Helvetica usable, whose own hinting fails below 8 pixels per em (matplotlib 3.11:
        # "FT_Load_Glyph failed with error 0x85"), the size of a log axis's superscripts on screen.
        "text.hinting": "no_hinting",
        # No tight bounding box when saving: the file is exactly the requested width.
        "figure.constrained_layout.use": True,
    })
    return preset


def figure(width="single", aspect=0.75, nrows=1, ncols=1, **subplot_kw):
    """plt.subplots() sized for the current journal.

    width is "single", "double" or millimetres; height is width * aspect.
    """
    preset = journals.get(_journal)
    width_mm = journals.width_mm(_journal, width)
    height_mm = width_mm * aspect
    if preset["max_height_mm"] and height_mm > preset["max_height_mm"]:
        raise ValueError(
            f"figure height {height_mm:.1f} mm exceeds the {preset['max_height_mm']} mm maximum "
            f"of {preset['label']}; use a smaller aspect"
        )
    figsize = (width_mm / journals.MM_PER_INCH, height_mm / journals.MM_PER_INCH)
    return plt.subplots(nrows, ncols, figsize=figsize, **subplot_kw)


def canvas(width, height_mm, grid_mm=None):
    """A blank page for a diagram: (fig, ax) with one axes over the whole figure, in millimetres.

    width is "single", "double" or millimetres. (0, 0) is the bottom-left corner. Nothing is laid
    out automatically, so every box and arrow stays where its coordinates put it. grid_mm draws
    numbered grid lines that far apart: for a scratch render, to read positions off a picture.
    """
    preset = journals.get(_journal)
    width_mm = journals.width_mm(_journal, width)
    if preset["max_height_mm"] and height_mm > preset["max_height_mm"]:
        raise ValueError(
            f"canvas height {height_mm:.1f} mm exceeds the {preset['max_height_mm']} mm maximum of {preset['label']}"
        )
    fig = plt.figure(figsize=(width_mm / journals.MM_PER_INCH, height_mm / journals.MM_PER_INCH))
    # An explicit do-nothing engine: with none at all, matplotlib switches the rc engine back on
    # after the first save.
    fig.set_layout_engine(PlaceHolderLayoutEngine(adjust_compatible=True, colorbar_gridspec=True))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, width_mm)
    ax.set_ylim(0, height_mm)
    ax.set_axis_off()
    if grid_mm:
        marks = dict(color="magenta", fontsize=5, zorder=10)
        for x in np.arange(grid_mm, width_mm, grid_mm):
            ax.axvline(x, color="magenta", linewidth=0.3, zorder=10)
            ax.text(x, 0.5, f"{x:g}", ha="center", va="bottom", **marks)
        for y in np.arange(grid_mm, height_mm, grid_mm):
            ax.axhline(y, color="magenta", linewidth=0.3, zorder=10)
            ax.text(0.5, y, f"{y:g}", ha="left", va="center", **marks)
    return fig, ax


HEADS = {"arrow": "-|>", "bar": "|-|,widthA=0,widthB=0.5", "none": "-"}  # the bar comes out 3 mm long
BAR_GAP_PT = 72 / journals.MM_PER_INCH  # 1 mm: on the frame it points at, a bar would vanish into the frame


def box(ax, x, y, width, height, text, fill="white", align="center"):
    """A frame of a fixed size with its text inside; (x, y) is the bottom-left corner, in millimetres.

    Returns the points to attach lines to (left, right, top, bottom: the middles of the sides), the
    text and the frame. align="left" sets the lines of the text from the left side instead of
    centring them. save() refuses a figure in which a text does not fit its box.
    """
    frame = ax.add_patch(plt.Rectangle((x, y), width, height, facecolor=fill, edgecolor="black", linewidth=0.6))
    if align == "left":
        label = ax.text(x + 1.5, y + height / 2, text, ha="left", va="center")
    else:
        label = ax.text(x + width / 2, y + height / 2, text, ha="center", va="center")
    ax.figure.__dict__.setdefault("_scistyle_boxes", []).append((label, frame))
    middle_x, middle_y = x + width / 2, y + height / 2
    return SimpleNamespace(
        left=(x, middle_y), right=(x + width, middle_y), top=(middle_x, y + height), bottom=(middle_x, y),
        text=label, frame=frame,
    )


def connect(ax, *points, head="arrow"):
    """A line through the given points, in millimetres, ending in a head.

    head is "arrow" (leads to, activates), "bar" (inhibits) or "none". Give three points for an
    elbow: the start, the corner, the end. A bar stands 1 mm before the end point, so it stays
    visible in front of the box it points at.
    """
    if head not in HEADS:
        raise ValueError(f"unknown head {head!r}; choose from: {', '.join(HEADS)}")
    xs, ys = zip(*points[:-1])
    ax.plot(xs, ys, color="black", linewidth=0.6, solid_capstyle="projecting", solid_joinstyle="miter")
    ax.annotate(
        "", xy=points[-1], xytext=points[-2],
        arrowprops=dict(
            arrowstyle=HEADS[head], color="black", linewidth=0.6, mutation_scale=8,
            shrinkA=0, shrinkB=BAR_GAP_PT if head == "bar" else 0,
        ),
    )


def _check_boxes(fig):
    """Raise ValueError if the text of a box() does not lie inside its frame."""
    boxes = fig.__dict__.get("_scistyle_boxes", [])
    if not boxes:
        return
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    for label, frame in boxes:
        text, limit = label.get_window_extent(renderer), frame.get_window_extent(renderer)
        if not (limit.x0 <= text.x0 and text.x1 <= limit.x1 and limit.y0 <= text.y0 and text.y1 <= limit.y1):
            raise ValueError(
                f"text does not fit its box: {label.get_text()!r}; widen the box, break the line or shorten the text"
            )


def panel_labels(axes, labels=None):
    """Write a bold panel letter just outside the top-left corner of each axes."""
    preset = journals.get(_journal)
    if labels is None:
        labels = string.ascii_uppercase if preset["panel_case"] == "upper" else string.ascii_lowercase
    for ax, label in zip(np.ravel(axes), labels):
        ax.annotate(
            label, xy=(0, 1), xycoords="axes fraction", xytext=(-3, 3), textcoords="offset points",
            ha="right", va="bottom", fontsize=preset["panel_pt"] or 8, fontweight="bold",
        )


def save(fig, stem, formats=("pdf", "png"), dpi=None):
    """Save fig as <stem>.<format> for each format and return the paths written.

    Raster dpi defaults to what the current journal asks for combination figures. Raises
    ValueError, before writing anything, if the text of a box() does not fit its frame.
    """
    unknown = [fmt for fmt in formats if fmt not in FORMATS]
    if unknown:
        raise ValueError(f"unknown format {unknown[0]!r}; choose from: {', '.join(FORMATS)}")
    if dpi is None:
        dpi = journals.required_dpi(_journal, "combination")[0] or 600
    _check_boxes(fig)
    # While embedding a font, fontTools warns about harmless quirks of some system fonts.
    logging.getLogger("fontTools").setLevel(logging.ERROR)
    paths = []
    for fmt in formats:
        path = f"{stem}.{fmt}"
        fig.savefig(path, format=fmt, dpi=dpi)
        if fmt == "tiff":
            # matplotlib writes RGBA; publishers ask for RGB, so flatten the page onto white.
            with Image.open(path) as page:
                rgba = page.convert("RGBA")
            flat = Image.alpha_composite(Image.new("RGBA", rgba.size, "white"), rgba).convert("RGB")
            flat.save(path, "TIFF", dpi=(dpi, dpi), compression="tiff_lzw")
        paths.append(path)
    return paths


def main():
    parser = argparse.ArgumentParser(description="List the journal presets and colour palettes scistyle knows.")
    parser.add_argument(
        "--list", nargs="*", metavar="JOURNAL", required=True,
        help="print the presets as one JSON object: all of them, or only the journals named",
    )
    names = parser.parse_args().list or list(journals.JOURNALS)
    unknown = [name for name in names if name not in journals.JOURNALS]
    if unknown:
        parser.error(f"unknown journal: {', '.join(unknown)} (choose from: {', '.join(journals.JOURNALS)})")
    presets = {name: journals.JOURNALS[name] for name in names}
    print(json.dumps({"verified": journals.VERIFIED, "journals": presets, "palettes": PALETTES}, indent=2))


if __name__ == "__main__":
    main()
