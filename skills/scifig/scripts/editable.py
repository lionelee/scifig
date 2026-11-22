# /// script
# requires-python = ">=3.11,<3.13"
# dependencies = [
#   "rapidocr-onnxruntime==1.4.4",
#   "opencv-python-headless>=5.0,<6",
#   "numpy>=2,<3",
#   "pillow>=13,<14",
#   "python-pptx>=1.0.2,<2",
#   "vtracer>=0.6.15,<0.7",
# ]
#
# [tool.uv]
# # rapidocr-onnxruntime asks for the GUI build of OpenCV; the headless build is the same cv2.
# override-dependencies = ["opencv-python ; sys_platform == 'never'"]
# # The packages as they were on the day these scripts were tested: a later release cannot change their results.
# exclude-newer = "2026-11-14T00:00:00Z"
# ///
"""Turn a raster figure into an editable PPTX or SVG.

The text labels are read with OCR, erased from the picture and put back as real text
(Arial) in the same place, so they can be edited. Run it with uv, which installs the
dependencies listed above on first use:

    uv run editable.py figure.png --to pptx

OCR, tracing and inpainting all run offline on the CPU; nothing is written except OUTPUT.
OCR makes mistakes: proofread the labels of the result against the original figure.
"""
import argparse
import base64
import contextlib
import io
import json
import logging
import math
import os
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

import cv2
import numpy as np
from PIL import Image

MODES = ("pptx", "svg-text", "svg-vector")
ROTATED, UNSURE = 1, 2  # why an OCR item is left in the picture
MAX_TILT = 10  # degrees; text tilted further than this is left in the picture
RING = 3  # px; width of the band just outside a box that is sampled as its surround
FLAT_TOLERANCE = 3  # grey levels; a surround this close to its median counts as one flat colour
SLIDE_WIDTH_IN = 13.333
TRACE_2X_LIMIT = 4_000_000  # pixels; larger pictures are traced at their own size

# Arial glyph extents, as fractions of the font size. TOP is how far a character reaches above the
# baseline (characters not listed reach capital height). DEPTH is how far it reaches below the
# baseline (characters not listed sit on it; negative values float above it).
CAP_HEIGHT = 0.72
TOP = {
    **dict.fromkeys("acegmnopqrsuvwxyz:;αεμπ", 0.53), **dict.fromkeys("+<>±×÷", 0.59),
    "=": 0.50, **dict.fromkeys("~→←", 0.43), "-": 0.30, ".": 0.10, ",": 0.10, "_": -0.14,
}
DEPTH = {
    **dict.fromkeys("gjpqy()[]{}|@βμ", 0.21), ",": 0.14, ";": 0.14, "_": 0.20, "Q": 0.06,
    **dict.fromkeys("+<>×÷", -0.12), "=": -0.20, "~": -0.27, "→": -0.08, "←": -0.08, "-": -0.21,
    "*": -0.42, "^": -0.34, **dict.fromkeys("\"'°", -0.46),
}
CJK_TOP, CJK_DEPTH = 0.83, 0.09  # ideographs in common sans-serif fonts
ASCENT, LINE_HEIGHT = 0.905, 1.15  # Arial: top of a text line to its baseline, and to the next line
SIDE_BEARING = 0.045  # typical gap between where a text starts and its first stroke


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="editable.py",
        description="Turn a raster figure into an editable file: text labels are read with OCR, "
        "erased from the picture and re-created as real, editable text in the same place.",
    )
    parser.add_argument("input", metavar="INPUT", type=Path, help="raster figure: PNG, JPEG or WebP")
    parser.add_argument(
        "--to", required=True, choices=MODES,
        help="pptx: one slide with the text-free picture and a text box per label; "
        "svg-text: SVG with the text-free picture embedded plus <text> labels; "
        "svg-vector: SVG with the picture traced into paths plus <text> labels",
    )
    parser.add_argument(
        "-o", dest="output", metavar="OUTPUT", type=Path,
        help="output file (default: INPUT with a .pptx or .svg extension); never INPUT itself",
    )
    parser.add_argument(
        "--no-text", action="store_true",
        help="skip OCR and erasing: plain trace (svg-vector) or picture-only slide (pptx)",
    )
    parser.add_argument(
        "--min-confidence", type=float, default=0.5, metavar="FLOAT",
        help="OCR items below this confidence stay in the picture untouched (default: 0.5)",
    )
    parser.add_argument("--json", action="store_true", help="print one JSON object instead of the summary")
    args = parser.parse_args(argv)
    if args.no_text and args.to == "svg-text":
        parser.error("--no-text leaves nothing to do for --to svg-text (it would only re-wrap the picture)")
    if args.output is None:
        args.output = args.input.with_suffix(".pptx" if args.to == "pptx" else ".svg")
    return args


def load_image(path):
    """Read an image as a BGR uint8 array; transparency is flattened onto white."""
    image = Image.open(path)
    if image.mode.startswith("I;16"):
        # Pillow's own conversion clips 16-bit values above 255 to white.
        image = image.convert("I").point(lambda value: value * (1 / 256)).convert("L")
    rgba = image.convert("RGBA")
    flat = Image.alpha_composite(Image.new("RGBA", rgba.size, "white"), rgba)
    return np.ascontiguousarray(np.asarray(flat)[:, :, 2::-1])


def read_text(bgr, as_it_stands=False):
    """OCR the image into [(text, 4x2 quad, confidence)]. as_it_stands leaves out the step that
    turns a line it takes to be upside down, which now and then turns one that is not."""
    # onnxruntime uploads usage telemetry and keeps a device id under the home directory unless
    # this is set before it loads (see Privacy.md in its wheel).
    os.environ["ORT_DISABLE_TELEMETRY"] = "1"
    from rapidocr_onnxruntime import RapidOCR  # imported here: only needed when OCR runs

    # text_score=0 returns every item; --min-confidence is applied in split_items.
    found, _ = RapidOCR(text_score=0.0)(bgr, use_cls=not as_it_stands)
    return [(text, np.array(quad, np.float32), float(score)) for quad, text, score in found or []]


def box_sides(quad):
    """(width, height) of a quad whose corners run top-left, top-right, bottom-right, bottom-left."""
    width = (math.dist(quad[0], quad[1]) + math.dist(quad[3], quad[2])) / 2
    height = (math.dist(quad[0], quad[3]) + math.dist(quad[1], quad[2])) / 2
    return width, height


def baseline_angle(quad):
    """Degrees between the text baseline and horizontal, 0 to 90."""
    width, height = box_sides(quad)
    if height >= 1.5 * width:  # RapidOCR reads boxes this tall as vertical text
        return 90.0
    dx, dy = quad[1] - quad[0] + quad[2] - quad[3]
    return abs(math.degrees(math.atan2(dy, dx)))


def polygon(quad):
    return [np.round(quad).astype(np.int32)]


def box_masks(quad, shape):
    """Return (window, inside, mask) for a quad: the image window around it and, within that window,
    the pixels inside the quad and the pixels to erase.

    The pixels to erase are the quad grown by about 10% of the box height (at least 2 px).
    """
    grow = max(2, round(0.1 * box_sides(quad)[1]))
    pad = grow + RING
    left, top = np.floor(quad.min(axis=0)).astype(int) - pad
    right, bottom = np.ceil(quad.max(axis=0)).astype(int) + pad + 1
    rows, cols = slice(max(top, 0), min(bottom, shape[0])), slice(max(left, 0), min(right, shape[1]))
    inside = np.zeros((rows.stop - rows.start, cols.stop - cols.start), np.uint8)
    cv2.fillPoly(inside, polygon(quad - (cols.start, rows.start)), 255)
    mask = cv2.dilate(inside, np.ones((2 * grow + 1, 2 * grow + 1), np.uint8))
    return (rows, cols), inside > 0, mask > 0


def split_items(found, min_confidence, shape):
    """Return (items to re-create, number skipped as rotated, number skipped for low confidence).

    A kept item carries its box_masks. An item whose erasing would cut into a skipped one is
    skipped for the same reason: text that stays in the picture stays whole.
    """
    stays = np.zeros(shape, np.uint8)  # ROTATED or UNSURE wherever skipped text stays
    skipped = {ROTATED: 0, UNSURE: 0}

    def skip(quad, reason):
        skipped[reason] += 1
        cv2.fillPoly(stays, polygon(quad), reason)

    readable, kept = [], []
    for text, quad, confidence in found:
        if baseline_angle(quad) > MAX_TILT:
            skip(quad, ROTATED)
        elif confidence < min_confidence or not text.strip():
            skip(quad, UNSURE)
        else:
            readable.append((text.strip(), quad))
    for text, quad in readable:
        window, inside, mask = box_masks(quad, shape)
        if neighbour := int(stays[window][mask].max()):
            skip(quad, neighbour)
        else:
            kept.append({"text": text, "window": window, "inside": inside, "mask": mask})
    return kept, skipped[ROTATED], skipped[UNSURE]


def glyph_extent(text):
    """How far `text` reaches above and below its baseline, as fractions of the font size."""
    chars = "".join(text.split())
    if any(ord(char) >= 0x2E80 for char in chars):
        return CJK_TOP, CJK_DEPTH
    return max(TOP.get(char, CAP_HEIGHT) for char in chars), max(DEPTH.get(char, 0.0) for char in chars)


def measure_strokes(pixels, inside, corner, background, text):
    """Colour, start, baseline, font size and width (px) of the text strokes inside a box.

    `pixels` is the BGR window around the box, whose top left pixel is at image row and column
    `corner`; `inside` marks the box in it; `background` is the colour around the box.
    """
    contrast = np.abs(pixels.astype(np.int32) - background).sum(axis=2)
    # Ink is what reaches half the contrast of the text's own strokes, not half that of the darkest
    # thing in the window: else a dark rule under grey text is all there is to measure. The text
    # reaches its contrast in at least a quarter of the rows, and of the columns, that hold
    # anything; a line in only a few rows or a few columns. What is far darker than the text is a
    # rule, an outline or an arrow: it is left out, with its anti-aliased edge.
    rows, columns = contrast.max(axis=1), contrast.max(axis=0)
    marked = 0.1 * contrast.max()  # fainter rows and columns count as empty
    own = min(np.percentile(rows[rows >= marked], 75), np.percentile(columns[columns >= marked], 75))
    darker = cv2.dilate((contrast > 1.5 * own).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    strokes = inside & ~darker
    if not strokes.any():  # the box holds nothing else: measure what is there
        strokes = inside
    strongest = contrast[strokes].max()
    ys, xs = np.nonzero(strokes & (contrast >= 0.5 * strongest))
    blue, green, red = np.median(pixels[strokes & (contrast >= 0.9 * strongest)], axis=0)  # stroke cores
    top, bottom = corner[0] + ys.min(), corner[0] + ys.max() + 1
    left, right = corner[1] + xs.min(), corner[1] + xs.max() + 1
    rise, depth = glyph_extent(text)
    font_px = (bottom - top) / (rise + depth)
    return {
        "color": (int(red), int(green), int(blue)),
        "x": float(left - SIDE_BEARING * font_px),
        "baseline": float(bottom - depth * font_px),
        "font_px": float(font_px),
        "width": float(right - left),
    }


def erase_labels(bgr, items):
    """Measure every item's strokes (stored on the item), then return `bgr` with the items erased.

    A box whose surround is one flat colour is filled with that colour; the rest is inpainted.
    """
    covered = np.zeros(bgr.shape[:2], bool)
    for item in items:
        covered[item["window"]] |= item["mask"]
    erased = bgr.copy()
    to_inpaint = np.zeros(bgr.shape[:2], np.uint8)
    for item in items:
        window, mask = item["window"], item["mask"]
        ring = cv2.dilate(mask.astype(np.uint8), np.ones((2 * RING + 1, 2 * RING + 1), np.uint8)) > 0
        around = bgr[window][ring & ~covered[window]]  # the pixels just outside the box
        if not len(around):  # nothing but text boxes around: the box's own main colour stands in
            around = np.median(bgr[window][mask], axis=0, keepdims=True)
        background = np.median(around, axis=0)
        # Strokes are measured inside the box proper, where nothing but the text should be.
        corner = (window[0].start, window[1].start)
        item.update(measure_strokes(bgr[window], item["inside"], corner, background, item["text"]))
        # Flat if three quarters of the surround match: a line or a neighbour crossing it does not count.
        spread = np.abs(around.astype(np.int32) - background).max(axis=1)
        if np.percentile(spread, 75) <= FLAT_TOLERANCE:
            erased[window][mask] = background
        else:
            to_inpaint[window][mask] = 255
    if to_inpaint.any():
        erased = cv2.inpaint(erased, to_inpaint, 3, cv2.INPAINT_NS)
    return erased


def reading_order(items):
    """Sort top to bottom, then left to right; items sharing a baseline form one row."""
    rows = []
    for item in sorted(items, key=lambda item: item["baseline"]):
        if rows and item["baseline"] - rows[-1][0]["baseline"] < 0.5 * rows[-1][0]["font_px"]:
            rows[-1].append(item)
        else:
            rows.append([item])
    return [item for row in rows for item in sorted(row, key=lambda item: item["x"])]


def encode_png(bgr):
    return cv2.imencode(".png", bgr)[1].tobytes()


def trace_artwork(bgr):
    """Trace the picture into an SVG <g id="artwork"> of filled paths, in image pixel coordinates."""
    import vtracer  # imported here: only svg-vector needs it

    # vtracer loses strokes a pixel or two wide, so all but huge pictures are traced at twice
    # their size and scaled back. Patches under about 3x3 source pixels are dropped as speckle; the
    # other settings are vtracer's defaults (stacked layers, splines, 6-bit colour), which suit flat art.
    scale = 2 if bgr.shape[0] * bgr.shape[1] <= TRACE_2X_LIMIT else 1
    if scale > 1:
        bgr = cv2.resize(bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    svg = vtracer.convert_raw_image_to_svg(
        encode_png(bgr), img_format="png", colormode="color",
        filter_speckle=3 * scale, length_threshold=4.0 * scale, path_precision=1,
    )
    paths = re.findall(r"<path[^>]*/>", svg)
    return "\n".join([f'<g id="artwork" transform="scale({1 / scale:g})">', *paths, "</g>"])


def number(value):
    return f"{round(value, 1):g}"


def labels_group(items):
    lines = [
        f'<text x="{number(item["x"])}" y="{number(item["baseline"])}" font-size="{number(item["font_px"])}" '
        f'font-family="Arial, Helvetica, sans-serif" fill="#{"%02x%02x%02x" % item["color"]}">'
        f'{escape(item["text"])}</text>'
        for item in items
    ]
    return "\n".join(['<g id="labels">', *lines, "</g>"])


def write_svg(path, size, picture, items):
    """Write an SVG in image pixel coordinates: the picture markup, then the labels on top."""
    width, height = size
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'viewBox="0 0 {width} {height}" width="{width}" height="{height}">\n'
        f"{picture}\n{labels_group(items)}\n</svg>\n",
        encoding="utf-8",
    )


def write_pptx(path, size, png, items):
    """Write one slide: the picture across the whole slide, then a text box per item."""
    from pptx import Presentation  # imported here: only pptx needs it
    from pptx.dml.color import RGBColor
    from pptx.enum.text import MSO_AUTO_SIZE
    from pptx.util import Inches, Pt

    width, height = size
    deck = Presentation()
    deck.slide_width = Inches(SLIDE_WIDTH_IN)
    deck.slide_height = round(deck.slide_width * height / width)
    emu = deck.slide_width / width  # EMU per image pixel
    slide = deck.slides.add_slide(deck.slide_layouts[6])  # the blank layout
    slide.shapes.add_picture(io.BytesIO(png), 0, 0, deck.slide_width, deck.slide_height)
    for item in items:
        font_px = item["font_px"]
        # A little wider than the strokes: Keynote wraps text that overflows its box.
        box = slide.shapes.add_textbox(
            round(item["x"] * emu), round((item["baseline"] - ASCENT * font_px) * emu),
            round((1.1 * item["width"] + 0.5 * font_px) * emu), round(LINE_HEIGHT * font_px * emu),
        )
        frame = box.text_frame
        frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
        frame.word_wrap = False
        frame.auto_size = MSO_AUTO_SIZE.NONE
        run = frame.paragraphs[0].add_run()
        run.text = item["text"]
        run.font.name = "Arial"
        # python-pptx takes 1 to 4000 pt only: one label measured wrong must not stop the slide.
        run.font.size = Pt(min(max(round(font_px * emu / Pt(1), 1), 1), 4000))
        run.font.color.rgb = RGBColor(*item["color"])
    deck.save(path)


def convert(source, output, mode, no_text, min_confidence):
    """Run the whole pipeline and return the report dict."""
    if output.resolve() == source.resolve():
        raise ValueError(f"refusing to overwrite the input file {source}")
    bgr = load_image(source)
    size = (bgr.shape[1], bgr.shape[0])
    items, rotated, unsure, warnings = [], 0, 0, []
    if not no_text:
        found = read_text(bgr)
        items, rotated, unsure = split_items(found, min_confidence, bgr.shape[:2])
        bgr = erase_labels(bgr, items)
        items = reading_order(items)
        if not items:
            warnings.append("no editable text: OCR found no horizontal text above the confidence threshold")
        if 4 * (rotated + unsure) > len(found):
            warnings.append(
                f"{rotated + unsure} of {len(found)} OCR items were skipped and remain part of the picture"
            )

    if mode == "pptx":
        write_pptx(output, size, encode_png(bgr), items)
    elif mode == "svg-text":
        href = "data:image/png;base64," + base64.b64encode(encode_png(bgr)).decode("ascii")
        write_svg(output, size, f'<image width="{size[0]}" height="{size[1]}" xlink:href="{href}"/>', items)
    else:
        write_svg(output, size, trace_artwork(bgr), items)
    return {
        "output": str(output.absolute()),
        "mode": mode,
        "size": list(size),
        "text_items": len(items),
        # What was read, in reading order, for proofreading against the original figure.
        "labels": [{"text": item["text"], "font_px": round(item["font_px"], 1)} for item in items],
        "skipped_low_confidence": unsure,
        "skipped_rotated": rotated,
        "warnings": warnings,
    }


def summary(report):
    lines = [
        "wrote {output} ({mode}, {size[0]}x{size[1]} px)".format(**report),
        "text items: {text_items} editable, {skipped_low_confidence} skipped for low confidence, "
        "{skipped_rotated} skipped as rotated".format(**report),
    ]
    lines += [f'label "{label["text"]}", {label["font_px"]:g} px' for label in report["labels"]]
    return "\n".join(lines + [f"warning: {warning}" for warning in report["warnings"]])


def main(argv=None):
    # A Windows pipe takes the ANSI code page, which has no ₂, ↑, κ or Chinese: print UTF-8.
    if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    logging.disable(logging.CRITICAL)  # the libraries' own logging stays out of the output
    try:
        with contextlib.redirect_stdout(sys.stderr):  # stdout carries the report and nothing else
            report = convert(args.input, args.output, args.to, args.no_text, args.min_confidence)
    except Exception as exc:
        print(f"editable.py: error: {' '.join(str(exc).split()) or type(exc).__name__}", file=sys.stderr)
        return 1
    print(json.dumps(report) if args.json else summary(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
