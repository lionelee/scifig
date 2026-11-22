# /// script
# requires-python = ">=3.10,<3.15"
# dependencies = ["matplotlib", "numpy", "pillow>=10.3"]
#
# [tool.uv]
# # The packages as they were on the day these scripts were tested: a later release cannot change their results.
# exclude-newer = "2026-11-14T00:00:00Z"
# ///
"""Arrange raster panels into one figure at a journal width, with panel letters.

Every row is as wide as the figure: its panels keep their aspect ratio and share one height.
The letters stay text in a PDF. For charts, make the panels in one plotting script instead
(scistyle.figure(ncols=...)), so that they stay vector.
"""
import argparse
import io
import json
import logging
import math
import string
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageCms, ImageOps

if __name__ == "__main__":
    sys.dont_write_bytecode = True  # as a command, leave no __pycache__ next to this file

import journals
import scistyle

BAND = 1.4  # height of the strip that holds a row's letters, in letter sizes


def positive_int(text):
    value = int(text)
    if value <= 0:
        raise argparse.ArgumentTypeError(f"must be a positive integer, got {text}")
    return value


def positive_float(text):
    value = float(text)
    if not (math.isfinite(value) and value > 0):
        raise argparse.ArgumentTypeError(f"must be a positive number, got {text}")
    return value


def gap(text):
    value = float(text)
    if not (math.isfinite(value) and value >= 0):
        raise argparse.ArgumentTypeError(f"must be zero or more, got {text}")
    return value


def counts(text):
    return [positive_int(part) for part in text.split(",")]


def build_parser():
    parser = argparse.ArgumentParser(
        description="Arrange raster panels (PNG, JPEG, WebP, TIFF) into one figure at a journal width, with panel letters.",
        epilog="Every row is as wide as the figure; its panels keep their aspect ratio and share one height. "
        "A panel with too few pixels for its place is enlarged by interpolation, which adds pixels, not detail; "
        "the report names every panel enlarged by more than 1%.",
    )
    parser.add_argument("images", metavar="IMAGE", nargs="+", help="panels, in reading order")
    parser.add_argument("-f", "--format", required=True, choices=("png", "tiff", "pdf"), help="output format")
    parser.add_argument(
        "--rows", type=counts, metavar="N,N,...", help="panels in each row, top to bottom, such as 2,1 (default: one row)"
    )
    parser.add_argument(
        "--journal", default="default", choices=list(journals.JOURNALS), metavar="KEY",
        help=f"journal preset for widths, letters and fonts (default: default): {', '.join(journals.JOURNALS)}",
    )
    width = parser.add_mutually_exclusive_group()
    width.add_argument("--width-mm", type=positive_float, metavar="MM", help="printed width in millimetres")
    width.add_argument("--column", choices=("single", "double"), help="printed width: a column of --journal (default: double)")
    parser.add_argument("--gap-mm", type=gap, default=3.0, metavar="MM", help="space between panels (default: 3)")
    letters = parser.add_mutually_exclusive_group()
    letters.add_argument("--labels", metavar="A,B,...", help="panel letters (default: a, b, c or A, B, C as the journal prints them)")
    letters.add_argument("--no-labels", action="store_true", help="no panel letters")
    parser.add_argument("--dpi", type=positive_int, default=600, metavar="N", help="print resolution (default: 600)")
    parser.add_argument(
        "-o", "--output", metavar="OUTPUT", help="output file (default: the first panel's name plus _panels.<format>, next to it)"
    )
    parser.add_argument("--json", action="store_true", help="print one JSON object instead of the summary")
    return parser


def parse_args():
    parser = build_parser()
    args = parser.parse_args()
    args.rows = args.rows or [len(args.images)]
    if sum(args.rows) != len(args.images):
        parser.error(f"--rows {','.join(map(str, args.rows))} holds {sum(args.rows)} panels, but {len(args.images)} were given")
    if args.labels is not None:
        args.labels = args.labels.split(",")
        if len(args.labels) != len(args.images):
            parser.error(f"--labels names {len(args.labels)} panels, but {len(args.images)} were given")
    return args


def load(path):
    """A panel as 8-bit sRGB, the way viewers show it, with transparency flattened onto white."""
    with Image.open(path) as image:
        ImageOps.exif_transpose(image, in_place=True)
        # An ICC profile describes the panel only while its colour model is RGB.
        icc = image.info.get("icc_profile") if image.mode in ("RGB", "RGBA", "P") else None
        if image.mode.startswith("I;16"):
            # Pillow's own conversion clips 16-bit values above 255 to white.
            image = image.convert("I").point(lambda value: value * (1 / 256)).convert("L")
        rgba = image.convert("RGBA")
        panel = Image.alpha_composite(Image.new("RGBA", rgba.size, "white"), rgba).convert("RGB")
    if icc:
        # Panels can come in different colour spaces, and the figure is in one: sRGB, which a file without a
        # profile means and which the PDF, whose pictures carry none, is shown in.
        try:
            panel = ImageCms.profileToProfile(panel, ImageCms.ImageCmsProfile(io.BytesIO(icc)), ImageCms.createProfile("sRGB"))
        except (OSError, ImageCms.PyCMSError):
            pass  # a profile that cannot be read, or one for another colour model, describes nothing to convert
    return panel


def layout(sizes, rows, width_px, gap_px, band_px):
    """Return ([(x, y, width, height)] in pixels for each panel, total height).

    A row's height is the one at which its panels, at their own aspect ratios, fill the width.
    """
    boxes, y, first = [], 0, 0
    for count in rows:
        aspects = [width / height for width, height in sizes[first : first + count]]
        height = (width_px - gap_px * (count - 1)) / sum(aspects)
        y += band_px
        x = 0.0
        for aspect in aspects:
            left, right = round(x), round(x + aspect * height)
            boxes.append((left, y, right - left, round(height)))
            x += aspect * height + gap_px
        y += round(height) + gap_px
        first += count
    return boxes, y - gap_px


def compose(args):
    sources = [Path(image) for image in args.images]
    output = Path(args.output) if args.output else sources[0].with_name(f"{sources[0].stem}_panels.{args.format}")
    if any(output.exists() and source.exists() and output.samefile(source) for source in sources):
        raise ValueError("refusing to overwrite a panel; choose another path with -o")
    preset = journals.get(args.journal)
    width_mm = journals.width_mm(args.journal, args.width_mm or args.column or "double")
    width_px = journals.pixels_for(width_mm, args.dpi)
    dpi = width_px / (width_mm / journals.MM_PER_INCH)  # the tag that makes the file print at exactly width_mm
    letter_pt = preset["panel_pt"] or 8
    if args.no_labels:
        letters = [None] * len(sources)
    else:
        alphabet = string.ascii_uppercase if preset["panel_case"] == "upper" else string.ascii_lowercase
        letters = args.labels or list(alphabet[: len(sources)])
    band_px = 0 if args.no_labels else round(BAND * letter_pt / 72 * dpi)
    images = [load(source) for source in sources]
    boxes, height_px = layout(
        [image.size for image in images], args.rows, width_px, round(args.gap_mm / journals.MM_PER_INCH * dpi), band_px
    )
    height_mm = height_px / dpi * journals.MM_PER_INCH
    if preset["max_height_mm"] and height_mm > preset["max_height_mm"]:
        raise ValueError(
            f"the figure would be {height_mm:.0f} mm tall; {preset['label']} allows {preset['max_height_mm']:g} mm: "
            "put more panels in a row or choose a narrower width"
        )

    scistyle.use(args.journal)  # the journal's font for the letters; renders off screen
    # A hair more than the pixel count, so that rounding down gives exactly width_px x height_px.
    figure = plt.figure(figsize=((width_px + 0.01) / dpi, (height_px + 0.01) / dpi), dpi=dpi, layout="none")
    for image, (x, y, width, height), letter in zip(images, boxes, letters):
        pixels = np.asarray(image.resize((width, height), Image.Resampling.LANCZOS))
        figure.figimage(pixels, xo=x, yo=height_px - y - height)
        if letter:
            top = y - band_px + 0.1 * band_px
            figure.text(x / width_px, 1 - top / height_px, letter, ha="left", va="top", fontsize=letter_pt, fontweight="bold")
    if args.format == "pdf":
        logging.getLogger("fontTools").setLevel(logging.ERROR)  # harmless warnings while a font is embedded
        figure.savefig(output, format="pdf", dpi=dpi)
    else:
        figure.canvas.draw()
        picture = Image.fromarray(np.asarray(figure.canvas.buffer_rgba())).convert("RGB")  # no alpha channel
        extra = {"compression": "tiff_lzw"} if args.format == "tiff" else {}
        picture.save(output, args.format.upper(), dpi=(dpi, dpi), **extra)
    plt.close(figure)

    panels = [
        {
            "file": str(source),
            "label": letter,
            "box_px": list(box),
            "effective_dpi": round(image.width * dpi / box[2]),
            "scale": round(box[2] / image.width, 3),
            "upscaled": box[2] > 1.01 * image.width,  # a pixel or two of rounding is not an enlargement
        }
        for source, image, box, letter in zip(sources, images, boxes, letters)
    ]
    notes = []
    enlarged = [f"{Path(panel['file']).name} ({panel['scale']:.2f}x)" for panel in panels if panel["upscaled"]]
    if enlarged:
        notes.append(
            f"Enlarged by interpolation, which adds pixels, not detail: {', '.join(enlarged)}. Supply larger originals if you can."
        )
    problem = journals.format_problem(args.journal, args.format)
    if problem:
        notes.append(problem)
    return {
        "output": str(output),
        "format": args.format,
        "pixels": [width_px, height_px],
        "dpi": round(dpi, 1),
        "size_mm": [round(width_mm, 1), round(height_mm, 1)],
        "panels": panels,
        "notes": notes,
    }


def summary(report):
    width, height = report["pixels"]
    width_mm, height_mm = report["size_mm"]
    lines = [
        f"wrote {report['output']}",
        f"{report['format']}, {width} x {height} px at {report['dpi']} dpi = {width_mm} x {height_mm} mm in print",
    ]
    for panel in report["panels"]:
        _, _, box_width, box_height = panel["box_px"]
        lines.append(
            f"panel {panel['label'] or '-'}  {Path(panel['file']).name}  {box_width} x {box_height} px, "
            f"{panel['effective_dpi']} dpi from its own pixels" + (f" (enlarged {panel['scale']:.2f}x)" if panel["upscaled"] else "")
        )
    return "\n".join(lines + [f"note: {note}" for note in report["notes"]])


def main():
    # A Windows pipe takes the ANSI code page, which cannot print a file name or a label in Chinese: print UTF-8.
    if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    try:
        report = compose(args)
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        sys.exit(f"panels: {exc}")
    print(json.dumps(report, indent=2) if args.json else summary(report))


if __name__ == "__main__":
    main()
