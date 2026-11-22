# /// script
# requires-python = ">=3.10,<3.15"
# dependencies = ["pillow>=10.3", "numpy"]
#
# [tool.uv]
# # The packages as they were on the day these scripts were tested: a later release cannot change their results.
# exclude-newer = "2026-11-14T00:00:00Z"
# ///
"""Pre-submission checks for one raster figure.

Six checks, each pass, warn or fail: file format, effective dpi at the printed width,
transparency, colour mode, and whether the figure's main colours stay apart in greyscale print
and for colour-blind readers. The last two say skip when the figure has no two colours strong
and widespread enough to compare. The exit status is 0 whenever the checks ran, whatever they found.
With --look it also measures how strong the figure's colours and how heavy its lines are, which
no check judges.
"""
import argparse
import io
import json
import math
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
from PIL import Image, ImageCms, ImageOps

if __name__ == "__main__":
    sys.dont_write_bytecode = True  # as a command, leave no __pycache__ next to this file

import journals

KIND_LABELS = {"photo": "photos", "combination": "combination figures", "line_art": "line art"}
FORMAT_NAMES = {"PNG": "png", "TIFF": "tiff", "JPEG": "jpeg", "MPO": "jpeg"}  # MPO: a JPEG with extra pictures
RANK = {"skip": -1, "pass": 0, "warn": 1, "fail": 2}  # a check that compared nothing never sets the overall status
FEW_COLOURS = (
    "Fewer than two salient colours (at least 3% of the pixels outside the most common colour, "
    "chroma 15 or more): nothing to compare. Faint tints and fine coloured lines are not judged: "
    "look at them in the files that --previews writes."
)
TOOL_PIXELS = 1.57e6  # what an image tool returns, whatever the shape of the picture
HAIRLINE_PX, HEAVY_PX = 2, 3  # in such a picture: in 16:9, 0.12% and 0.18% of the width, as in the finer published figures
LINE_PIXELS = 15e6  # the most pixels whose lines --look measures: a larger picture is averaged in blocks, to bound memory

# sRGB (D65) to CIE XYZ, and the white point that goes with it.
RGB_TO_XYZ = np.array([
    [0.4124564, 0.3575761, 0.1804375],
    [0.2126729, 0.7151522, 0.0721750],
    [0.0193339, 0.1191920, 0.9503041],
])
WHITE = RGB_TO_XYZ.sum(axis=1)

# Machado, Oliveira & Fernandes (2009), severity 1.0. They apply to linear RGB.
DEFICIENCIES = {
    "deuteranopia": np.array([
        [0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881],
    ]),
    "protanopia": np.array([
        [0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998],
    ]),
    "tritanopia": np.array([
        [1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900],
    ]),
}


# --- colour maths: sRGB values are floats in 0..1, the last axis holds the three channels ------


def to_linear(srgb):
    return np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)


def to_srgb(linear):
    return np.where(linear <= 0.0031308, linear * 12.92, 1.055 * linear ** (1 / 2.4) - 0.055)


def to_lab(srgb):
    """CIELAB (D65)."""
    xyz = to_linear(srgb) @ RGB_TO_XYZ.T / WHITE
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], axis=-1)


def simulate(srgb, deficiency):
    """The colours as seen with a colour-vision deficiency."""
    return to_srgb(np.clip(to_linear(srgb) @ DEFICIENCIES[deficiency].T, 0, 1))


def to_grey(srgb):
    """Greys of the same luminance, so colours of equal L* come out as the same grey."""
    return to_srgb(np.clip(to_linear(srgb) @ RGB_TO_XYZ[1], 0, 1))


def hex_code(srgb):
    return "#%02X%02X%02X" % tuple(np.rint(srgb * 255).astype(int))


# --- the image ---------------------------------------------------------------------------------


def flatten(image):
    """8-bit RGB copy of the image, with transparency composited over white."""
    if image.mode.startswith("I;16"):
        # Pillow's own conversion clips 16-bit values above 255 to white.
        image = image.convert("I").point(lambda value: value * (1 / 256)).convert("L")
    rgba = image.convert("RGBA")
    return Image.alpha_composite(Image.new("RGBA", rgba.size, "white"), rgba).convert("RGB")


def salient_colours(rgb_image):
    """The figure's colours as sRGB rows, most widespread first.

    Sample the image down to 512 px and quantize it to 32 colours. The most common one is
    usually the background: keep it, and every colour that covers at least 3% of the pixels
    outside it, so that thin lines and small markers on a large background count. Then drop
    the colours whose CIELAB chroma is under 15.
    """
    small = rgb_image.copy()
    small.thumbnail((512, 512), Image.Resampling.NEAREST)  # a plain sample: averaging would wash thin lines out
    quantized = small.quantize(32)
    palette = quantized.getpalette()
    background, *others = sorted(quantized.getcolors(), reverse=True)
    rest = small.width * small.height - background[0]
    kept = [background] + [entry for entry in others if entry[0] * 100 >= 3 * rest]
    colours = np.array([palette[3 * index : 3 * index + 3] for _, index in kept]) / 255
    lab = to_lab(colours)
    return colours[np.hypot(lab[:, 1], lab[:, 2]) >= 15]


def measure_fills(rgb_image):
    """How strong the colours of a figure are.

    A fill is a pixel that is light (L* 70 or more) and coloured (chroma 4 or more): a tinted
    box, card or cell, not the background, a line or a text. Returns the share of the figure
    they cover, their median chroma and lightness, and the share of the figure in strong colour
    (chroma 30 or more, light or dark: outlines, icons, saturated blocks).
    """
    small = rgb_image.copy()
    small.thumbnail((512, 512), Image.Resampling.NEAREST)  # a plain sample, as for the salient colours
    lab = to_lab(np.asarray(small) / 255)
    lightness, chroma = lab[..., 0], np.hypot(lab[..., 1], lab[..., 2])
    fills = (lightness >= 70) & (chroma >= 4)
    measured = fills.mean() >= 0.002  # fewer pixels than that are edges, not areas
    return {
        "share": round(float(fills.mean()), 3) if measured else 0.0,
        "chroma": round(float(np.median(chroma[fills])), 1) if measured else None,
        "lightness": round(float(np.median(lightness[fills])), 1) if measured else None,
        "strong_share": round(float((chroma >= 30).mean()), 3),
    }


def long_runs(mask, length):
    """The pixels of a boolean mask that lie in a horizontal run at least `length` pixels long."""
    height, width = mask.shape
    if width < length:
        return np.zeros_like(mask)
    before = np.cumsum(np.pad(mask, ((0, 0), (1, 0))), axis=1)  # set pixels left of each column
    full = before[:, length:] - before[:, :-length] == length  # windows of `length` pixels that are all set
    starts = np.cumsum(np.pad(full, ((0, 0), (1, 0))), axis=1)  # full windows that start left of each column
    columns = np.arange(width)
    return starts[:, np.minimum(columns, width - length) + 1] - starts[:, np.maximum(columns - length + 1, 0)] > 0


def line_thicknesses(mask, strength, length, limit):
    """Thicknesses in pixels of the straight lines of a mask, horizontal and vertical: runs at
    least `length` long and at most `limit` thick, measured across the run.

    A pixel counts for the share of the line's strength that it has over the ground beside the
    line, so that a soft edge is part of a pixel and a line that straddles two rows is not read
    a pixel thicker. Crossings with something else within two pixels are left out.
    """
    found = []
    offsets = np.arange(-2, limit + 2)  # from two pixels before a run to one pixel after the longest
    for lines, values in ((mask, strength), (mask.T, strength.T)):
        steps = np.diff(np.pad(long_runs(lines, length), ((1, 1), (0, 0))).astype(np.int8), axis=0)
        tops, bottoms = np.argwhere(steps.T == 1), np.argwhere(steps.T == -1)  # both column by column, so they pair up
        kept = bottoms[:, 1] - tops[:, 1] <= limit
        columns, starts, sizes = tops[kept, 0], tops[kept, 1], (bottoms[:, 1] - tops[:, 1])[kept]
        rows = np.clip(starts[:, None] + offsets, 0, len(values) - 1)
        across = values[rows, columns[:, None]]  # one row per crossing: the strengths across the line
        in_run = (offsets >= 0) & (offsets < sizes[:, None])
        core, peak = np.where(in_run, across, -np.inf).max(axis=1), np.where(in_run, across, -np.inf).argmax(axis=1)
        before, after = across[:, 0], np.take_along_axis(across, sizes[:, None] + 3, axis=1)[:, 0]
        ground = np.where(np.arange(len(offsets)) <= peak[:, None], before[:, None], after[:, None])
        share = np.clip((across - ground) / np.maximum(core[:, None] - ground, 1e-9), 0, 1)
        near = (offsets >= -1) & (offsets <= sizes[:, None])  # the run and one pixel on each side
        clear = (before < core / 2) & (after < core / 2)
        found.append((share * near).sum(axis=1)[clear])
    return np.concatenate(found)


def measure_lines(rgb_image):
    """How heavy the long straight lines of a figure are: box outlines, frames, arrow shafts.

    A line is a straight run of clearly coloured pixels (chroma 20 or more, below L* 85) or of
    dark ones (L* below 60) that is at least 4% of the width long and at most 1.2% of it thick,
    which leaves out text, icons and filled shapes. Returns the median thickness of the coloured
    and of the dark lines, in pixels of the file to a tenth and as a share of its width.
    """
    block = math.ceil(math.sqrt(rgb_image.width * rgb_image.height / LINE_PIXELS))
    small = rgb_image.reduce(block) if block > 1 else rgb_image  # averaged: a soft edge stays part of a pixel, as a sample would not
    pixels = np.asarray(small)
    lightness, chroma = np.empty(pixels.shape[:2]), np.empty(pixels.shape[:2])
    for top in range(0, len(pixels), 256):  # a band of rows at a time: the colour maths takes ten times the picture
        lab = to_lab(pixels[top : top + 256] / 255)
        lightness[top : top + 256], chroma[top : top + 256] = lab[..., 0], np.hypot(lab[..., 1], lab[..., 2])
    length, limit = round(0.04 * small.width), round(0.012 * small.width)
    result = {}
    for name, mask, strength in (
        ("coloured", (chroma >= 20) & (lightness < 85), chroma),
        ("dark", (lightness < 60) & (chroma < 20), 100 - lightness),
    ):
        found = line_thicknesses(mask, strength, length, limit)
        measured = len(found) >= 200  # fewer crossings than that are stray edges, not lines
        median = float(np.median(found)) if measured else None
        result[f"{name}_px"] = round(median * rgb_image.width / small.width, 1) if measured else None
        result[f"{name}_share"] = round(median / small.width, 4) if measured else None
    return result


def distinct_pairs(colours):
    """Index pairs of colours that are clearly different on screen (CIE76 deltaE >= 25)."""
    lab = to_lab(colours)
    return [(i, j) for i, j in combinations(range(len(colours)), 2) if np.linalg.norm(lab[i] - lab[j]) >= 25]


def listing(items):
    """Up to five items, then how many more there are."""
    more = f" and {len(items) - 5} more" if len(items) > 5 else ""
    return ", ".join(items[:5]) + more


def icc_description(image):
    """Description of the embedded ICC profile, or None when there is none."""
    icc = image.info.get("icc_profile")
    if not icc:
        return None
    try:
        return ImageCms.getProfileDescription(io.BytesIO(icc)).strip() or "unnamed"
    except ImageCms.PyCMSError:
        return "unreadable"


# --- the checks: each returns (status, detail) -------------------------------------------------


def check_format(fmt, journal):
    name = FORMAT_NAMES.get(fmt)
    problem = journals.format_problem(journal, name) if name else None
    if problem:
        return "warn", problem
    if name == "png":
        return "pass", "PNG: lossless."
    if name == "tiff":
        return "pass", "TIFF: widely accepted for raster figures."
    if name == "jpeg":
        return "warn", "JPEG is lossy; re-export from the source as TIFF."
    return "warn", f"{fmt}: few publishers accept it; re-export as TIFF or PNG."


def check_dpi(width_px, journal, kind, widths, min_dpi=None):
    """Judge the pixel width at each (millimetres, description) in widths.

    min_dpi replaces the minimum of the journal preset: for a graphical abstract, a thesis or a
    report, whose own guide sets the figure.
    """
    label = journals.get(journal)["label"]
    required, basis = (min_dpi, "asked") if min_dpi else journals.required_dpi(journal, kind)
    readings, too_low = [], 0
    for mm, name in widths:
        # Whole dpi: a file a pixel short of pixels_for() still counts
        # (2102 px at 89 mm is 599.9 dpi).
        effective = round(width_px / (mm / journals.MM_PER_INCH))
        reading = f"{effective} dpi at {mm:g} mm" + (f" ({name})" if name else "")
        if required and effective < required:
            reading += f", needs {journals.pixels_for(mm, required)} px"
            too_low += 1
        readings.append(reading)
    measured = f"{width_px} px wide: {'; '.join(readings)}."
    if basis == "vector":
        return "warn", (
            f"{label} requires vector artwork for {KIND_LABELS[kind]}, so no raster file satisfies it. {measured}"
        )
    if basis == "asked":
        detail = f"{measured} Minimum: {required:g} dpi (given with --min-dpi)."
    else:
        source = "generic default, not a publisher rule" if basis == "generic" else f"stated by {label}"
        detail = f"{measured} Minimum for {KIND_LABELS[kind]}: {required} dpi ({source})."
    if not too_low:
        return "pass", detail
    if too_low < len(widths):
        return "warn", f"{detail} Fine at single column but too low for double column."
    # Only a minimum that the publisher states can fail a file; a common value is advice.
    return ("warn" if basis == "generic" else "fail"), detail


def check_transparency(image):
    if not image.has_transparency_data:
        return "pass", "No alpha channel."
    translucent = np.asarray(image.convert("RGBA").getchannel("A")) < 255
    if not translucent.any():
        return "pass", "The alpha channel is fully opaque."
    return "warn", (
        f"Not fully opaque: {translucent.sum()} pixels ({translucent.mean():.1%} of the image). "
        "Many production systems flatten transparency unpredictably; flatten it onto white before submitting."
    )


def check_color_mode(image):
    profile = icc_description(image)
    icc = f" Embedded ICC profile: {profile}." if profile else ""
    if image.mode in ("RGB", "RGBA", "L", "LA"):
        return "pass", f"{image.mode} mode.{icc}"
    if image.mode == "CMYK":
        return "warn", (
            f"CMYK mode; most publishers in the bundled dataset ask for RGB. Confirm with the journal.{icc}"
        )
    return "warn", f"{image.mode} mode; convert to RGB.{icc}"


def check_grayscale(colours):
    if len(colours) < 2:
        return "skip", FEW_COLOURS
    lightness = to_lab(colours)[:, 0]
    alike = [
        f"{hex_code(colours[i])} / {hex_code(colours[j])}"
        for i, j in distinct_pairs(colours)
        if abs(lightness[i] - lightness[j]) < 10
    ]
    if alike:
        return "warn", f"Would look alike in greyscale print (lightness less than 10 apart): {listing(alike)}."
    return "pass", (
        f"{len(colours)} salient colours; every clearly different pair is at least 10 apart in lightness."
    )


def check_colorblind(colours):
    if len(colours) < 2:
        return "skip", FEW_COLOURS
    confusable = []
    for i, j in distinct_pairs(colours):
        for deficiency in DEFICIENCIES:
            first, second = to_lab(simulate(colours[[i, j]], deficiency))
            if np.linalg.norm(first - second) < 10:
                confusable.append(f"{hex_code(colours[i])} / {hex_code(colours[j])} ({deficiency})")
    if confusable:
        return "warn", f"Hard to tell apart with a colour-vision deficiency: {listing(confusable)}."
    return "pass", (
        f"{len(colours)} salient colours; every clearly different pair stays apart under simulated "
        "deuteranopia, protanopia and tritanopia."
    )


# --- command line ------------------------------------------------------------------------------


def write_previews(rgb_image, directory):
    """Write greyscale and colour-blind renderings of the image; return {name: path}."""
    directory.mkdir(parents=True, exist_ok=True)
    preview = rgb_image.copy()
    preview.thumbnail((1600, 1600))
    srgb = np.asarray(preview) / 255
    renderings = {"grayscale": to_grey(srgb)}
    renderings.update((name, simulate(srgb, name)) for name in DEFICIENCIES)
    paths = {}
    for name, values in renderings.items():
        paths[name] = str(directory / f"{name}.png")
        Image.fromarray(np.rint(values * 255).astype(np.uint8)).save(paths[name])
    return paths


def widths_to_check(args):
    """[(millimetres, description)]: the width asked for, or both columns of the journal."""
    if args.width_mm:
        return [(args.width_mm, None)]
    columns = [args.column] if args.column else ["single", "double"]
    return [(journals.width_mm(args.journal, column), f"{column} column") for column in columns]


def run_checks(args):
    if Path(args.input).suffix.lower() in (".pdf", ".eps", ".svg", ".ai"):
        raise OSError(
            f"{Path(args.input).name} is a vector file, which has no pixels to check: "
            "run it on a PNG of the same figure and read the grayscale and colorblind lines"
        )
    with Image.open(args.input) as image:
        ImageOps.exif_transpose(image, in_place=True)  # a rotated photo, the way viewers show it
        rgb_image = flatten(image)
        colours = salient_colours(rgb_image)
        results = {
            "format": check_format(image.format, args.journal),
            "effective_dpi": (
                ("pass", f"{image.width} x {image.height} px, for the screen: no printed width applies.")
                if args.screen
                else check_dpi(image.width, args.journal, args.kind, widths_to_check(args), args.min_dpi)
            ),
            "transparency": check_transparency(image),
            "color_mode": check_color_mode(image),
            "grayscale": check_grayscale(colours),
            "colorblind": check_colorblind(colours),
        }
        facts = {"input": args.input, "format": image.format, "mode": image.mode, "pixels": list(image.size)}
        fills = measure_fills(rgb_image) if args.look else None
        lines = measure_lines(rgb_image) if args.look else None
    checks = [{"id": name, "status": status, "detail": detail} for name, (status, detail) in results.items()]
    return {
        **facts,
        "journal": args.journal,
        # The generic preset's note is about print and journals: it says nothing to a figure for the screen.
        "journal_note": None if args.screen and args.journal == "default" else journals.get(args.journal)["note"],
        "kind": args.kind,
        "checks": checks,
        "overall": max((check["status"] for check in checks), key=RANK.get),
        "fills": fills,
        "lines": lines,
        "previews": write_previews(rgb_image, Path(args.previews)) if args.previews else None,
    }


def positive_float(text):
    value = float(text)
    if not (math.isfinite(value) and value > 0):
        raise argparse.ArgumentTypeError(f"must be a positive number, got {text}")
    return value


def build_parser():
    parser = argparse.ArgumentParser(
        description="Pre-submission checks for one raster figure: format, effective dpi, transparency, "
        "colour mode, greyscale legibility and colour-blind safety.",
        epilog="Without --width-mm or --column the dpi is judged at both column widths of the journal. "
        "The exit status is 0 whenever the checks ran: read the OVERALL line, or \"overall\" with --json.",
    )
    parser.add_argument("input", metavar="INPUT", help="image file to check")
    parser.add_argument(
        "--journal", default="default", choices=list(journals.JOURNALS), metavar="KEY",
        help=f"journal preset (default: default): {', '.join(journals.JOURNALS)}",
    )
    parser.add_argument(
        "--kind", default="combination", choices=journals.KINDS,
        help="what the figure shows; it sets the required dpi (default: combination)",
    )
    width = parser.add_mutually_exclusive_group()
    width.add_argument("--width-mm", type=positive_float, metavar="MM", help="printed width in millimetres")
    width.add_argument("--column", choices=("single", "double"), help="printed width: a column of --journal")
    width.add_argument(
        "--screen", action="store_true",
        help="the figure is for a slide, a blog or another screen: there is no printed width to judge its resolution at",
    )
    parser.add_argument(
        "--min-dpi", type=positive_float, metavar="N",
        help="judge the resolution against this minimum instead of the preset's: for a graphical abstract, "
        "a thesis or a report, whose own guide sets it",
    )
    parser.add_argument(
        "--look", action="store_true",
        help="also measure the look of the figure: how strong its colours are (chroma and lightness of the light "
        "coloured areas, share of strong colour) and how heavy its long straight lines are; it changes no verdict",
    )
    parser.add_argument(
        "--previews", metavar="DIR",
        help="write grayscale.png, deuteranopia.png, protanopia.png and tritanopia.png into DIR",
    )
    parser.add_argument("--json", action="store_true", help="print one JSON object instead of the lines")
    return parser


def fills_line(fills):
    strong = f"Strong colour (chroma 30 or more) covers {fills['strong_share']:.0%}."
    if fills["chroma"] is None:
        return f"No light coloured areas: nothing to measure. {strong}" if fills["strong_share"] else "No light coloured areas: nothing to measure."
    return (
        f"Light coloured areas cover {fills['share']:.0%} of the figure: median chroma {fills['chroma']:.0f}, "
        f"median lightness {fills['lightness']:.0f}. {strong} "
        "A faint tint has a chroma of 12 or less, a pastel about 20, a saturated colour 50 or more."
    )


def lines_line(lines, size):
    def weight(kind):
        return f"{lines[f'{kind}_px']:g} px", f"{lines[f'{kind}_share']:.2%}"

    coloured, dark = lines["coloured_px"] is not None, lines["dark_px"] is not None
    if not (coloured or dark):
        return "No long straight lines: nothing to measure."
    if coloured and dark:
        text = "the coloured ones are {} thick at the median ({} of the width), the dark ones {} ({}).".format(*weight("coloured"), *weight("dark"))
    else:
        kind = "coloured" if coloured else "dark"
        text = "the {} ones are {} thick at the median ({} of the width).".format(kind, *weight(kind))
    larger = max(1, math.sqrt(size[0] * size[1] / TOOL_PIXELS))  # in proportion to its side; a smaller picture has no less
    return (
        f"Long straight lines: {text} A hairline is {HAIRLINE_PX * larger:.2g} px in a picture of this size; "
        f"more than {HEAVY_PX * larger:.2g} px reads as heavy."
    )


def main():
    # A Windows pipe takes the ANSI code page, which cannot print a folder or a profile named in Chinese: print UTF-8.
    if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
    parser = build_parser()
    args = parser.parse_args()
    if args.screen and args.min_dpi:
        parser.error("--min-dpi is a print resolution; it does not go with --screen")
    try:
        report = run_checks(args)
    except (OSError, Image.DecompressionBombError) as exc:
        sys.exit(f"check_figure: {exc}")
    if args.json:
        print(json.dumps(report, indent=2))
        return
    for check in report["checks"]:
        print(f"{check['status'].upper()}  {check['id']}  {check['detail']}")
    if report["fills"]:
        print(f"FILLS  {fills_line(report['fills'])}")
        print(f"LINES  {lines_line(report['lines'], report['pixels'])}")
    for name, path in (report["previews"] or {}).items():
        print(f"PREVIEW  {name}  {path}")
    if report["journal_note"]:
        print(f"NOTE  {report['journal_note']}")
    skipped = [check["id"] for check in report["checks"] if check["status"] == "skip"]
    print(f"OVERALL {report['overall'].upper()}" + (f"  not judged: {', '.join(skipped)}" if skipped else ""))


if __name__ == "__main__":
    main()
