# /// script
# requires-python = ">=3.10,<3.15"
# dependencies = ["pillow>=10.3"]
#
# [tool.uv]
# # The packages as they were on the day these scripts were tested: a later release cannot change their results.
# exclude-newer = "2026-11-14T00:00:00Z"
# ///
"""Convert a raster figure to a submission file (PNG, TIFF or PDF) at a print resolution.

Upscaling interpolates: it adds pixels, not detail. Re-render from the source when you can.
"""
import argparse
import json
import math
import sys
import zlib
from pathlib import Path

from PIL import Image, ImageOps

if __name__ == "__main__":
    sys.dont_write_bytecode = True  # as a command, leave no __pycache__ next to this file

import journals

INPUT_FORMATS = ("PNG", "JPEG", "MPO", "WEBP", "TIFF")  # MPO: a JPEG that carries extra pictures
KEPT_MODES = ("RGB", "RGBA", "L", "LA")  # every other mode is converted to RGB


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


def build_parser():
    parser = argparse.ArgumentParser(
        description="Convert a raster figure (PNG, JPEG, WebP or TIFF) to a submission file at a print resolution.",
        epilog="With --width-mm or --column the image gets the pixels that --dpi needs at that printed width. "
        "Without them the longer side is brought to at least 1024 px (dpi <= 300), 2048 px (dpi <= 600) "
        "or 4096 px. An image is never downscaled. Upscaling interpolates: it adds pixels, not detail.",
    )
    parser.add_argument("input", metavar="INPUT", help="PNG, JPEG, WebP or TIFF image")
    parser.add_argument("-f", "--format", required=True, choices=("png", "tiff", "pdf"), help="output format")
    parser.add_argument("--dpi", type=positive_int, default=600, metavar="N", help="print resolution (default: 600)")
    width = parser.add_mutually_exclusive_group()
    width.add_argument("--width-mm", type=positive_float, metavar="MM", help="printed width in millimetres")
    width.add_argument("--column", choices=("single", "double"), help="printed width: a column of --journal")
    parser.add_argument(
        "--journal", default="default", choices=list(journals.JOURNALS), metavar="KEY",
        help=f"journal whose column widths --column uses (default: default): {', '.join(journals.JOURNALS)}",
    )
    parser.add_argument(
        "-o", "--output", metavar="OUTPUT",
        help="output file (default: INPUT's name plus _<dpi>dpi.<format>, next to INPUT)",
    )
    parser.add_argument("--json", action="store_true", help="print one JSON object instead of the summary")
    return parser


def normalise(image, fmt, notes):
    """Return an 8-bit RGB, RGBA, L or LA image; transparency survives only when the target is PNG."""
    if image.mode.startswith("I;16"):
        # Pillow's own conversion clips 16-bit values above 255 to white.
        image = image.convert("I").point(lambda value: value * (1 / 256)).convert("L")
        notes.append("Reduced 16-bit greyscale to 8-bit.")
    elif image.mode in ("I", "F"):
        raise ValueError(
            f"cannot reduce a 32-bit {image.mode} image to 8-bit without its display range; save an 8-bit copy first"
        )
    transparent = image.has_transparency_data
    if image.mode not in KEPT_MODES or "transparency" in image.info:
        target = "RGBA" if transparent else "RGB"
        if image.mode == "CMYK":
            notes.append("Converted CMYK to RGB without colour management; check the colours.")
        elif image.mode not in KEPT_MODES:
            notes.append(f"Converted {image.mode} to {target}.")
        image = image.convert(target)
    if transparent and fmt != "png":
        rgba = image.convert("RGBA")
        if rgba.getchannel("A").getextrema()[0] < 255:
            notes.append("Flattened transparency onto white.")
        image = Image.alpha_composite(Image.new("RGBA", rgba.size, "white"), rgba).convert("RGB")
    return image


def upscale_factor(size, dpi, width_mm):
    """How much to enlarge to reach the print width, or the preset long side. Never below 1."""
    if width_mm:
        factor = journals.pixels_for(width_mm, dpi) / size[0]
    else:
        factor = (1024 if dpi <= 300 else 2048 if dpi <= 600 else 4096) / max(size)
    return max(factor, 1.0)


def pdf_bytes(image, dpi):
    """A one-page PDF 1.4 showing an RGB or L image, losslessly, at pixels / dpi.

    Written by hand because Pillow's PDF writer stores the page as a JPEG.
    """
    width_pt, height_pt = (side / dpi * 72 for side in image.size)
    colour_space = b"DeviceGray" if image.mode == "L" else b"DeviceRGB"
    pixels = zlib.compress(image.tobytes())
    draw = b"q %.4f 0 0 %.4f 0 0 cm /Im0 Do Q" % (width_pt, height_pt)
    bodies = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.4f %.4f] "
        b"/Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>" % (width_pt, height_pt),
        b"<< /Type /XObject /Subtype /Image /Width %d /Height %d /ColorSpace /%s /BitsPerComponent 8 "
        b"/Filter /FlateDecode /Length %d >>\nstream\n%s\nendstream"
        % (image.width, image.height, colour_space, len(pixels), pixels),
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(draw), draw),
    ]
    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")  # the second line marks the file as binary
    offsets = []
    for number, body in enumerate(bodies, start=1):
        offsets.append(len(pdf))
        pdf += b"%d 0 obj\n%s\nendobj\n" % (number, body)
    xref = len(pdf)
    pdf += b"xref\n0 %d\n0000000000 65535 f \n" % (len(bodies) + 1)
    pdf += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    pdf += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(bodies) + 1, xref)
    return bytes(pdf)


def save(image, path, fmt, dpi, icc):
    if fmt == "png":
        image.save(path, "PNG", dpi=(dpi, dpi), icc_profile=icc)
    elif fmt == "tiff":
        image.save(path, "TIFF", dpi=(dpi, dpi), icc_profile=icc, compression="tiff_lzw")
    else:
        Path(path).write_bytes(pdf_bytes(image, dpi))


def export(args):
    source = Path(args.input)
    output = Path(args.output) if args.output else source.with_name(f"{source.stem}_{args.dpi}dpi.{args.format}")
    width_mm = None
    if args.width_mm or args.column:
        width_mm = journals.width_mm(args.journal, args.width_mm or args.column)
    notes = []
    with Image.open(source) as original:
        if original.format not in INPUT_FORMATS:
            raise ValueError(f"unsupported input format {original.format}; expected PNG, JPEG, WebP or TIFF")
        if output.exists() and output.samefile(source):
            raise ValueError("refusing to overwrite the input; choose another path with -o")
        ImageOps.exif_transpose(original, in_place=True)  # a rotated photo, the way viewers show it
        image = normalise(original, args.format, notes)
        # An ICC profile stays valid only while the colour model does.
        same_model = original.mode in ("RGB", "RGBA", "P") or image.mode in ("L", "LA")
        icc = original.info.get("icc_profile") if same_model else None
        scale = upscale_factor(image.size, args.dpi, width_mm)
        if scale > 1:
            size = (round(image.width * scale), round(image.height * scale))
            image = image.resize(size, Image.Resampling.LANCZOS)
            notes.append(
                f"Upscaled {scale:.2f}x with Lanczos interpolation, which adds pixels, not detail; "
                "re-render from the source if you can."
            )
        # In sized mode the tag makes the file print at exactly the requested width.
        dpi = image.width / (width_mm / journals.MM_PER_INCH) if width_mm else float(args.dpi)
        save(image, output, args.format, dpi, icc)
    if args.format == "pdf" and icc:
        notes.append("The embedded ICC profile is not carried into the PDF.")
    problem = journals.format_problem(args.journal, args.format)
    if problem:
        notes.append(problem)
    return {
        "output": str(output),
        "format": args.format,
        "pixels": [image.width, image.height],
        "dpi": round(dpi, 1),
        "physical_mm": [round(side / dpi * journals.MM_PER_INCH, 1) for side in image.size],
        "upscaled": scale > 1,
        "scale": round(scale, 4),
        "notes": notes,
    }


def summary(result):
    width, height = result["pixels"]
    width_mm, height_mm = result["physical_mm"]
    lines = [
        f"wrote {result['output']}",
        f"{result['format']}, {width} x {height} px at {result['dpi']} dpi = {width_mm} x {height_mm} mm in print",
        f"upscaled {result['scale']}x" if result["upscaled"] else "not resized",
    ]
    return "\n".join(lines + [f"note: {note}" for note in result["notes"]])


def main():
    args = build_parser().parse_args()
    try:
        result = export(args)
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        sys.exit(f"export_figure: {exc}")
    print(json.dumps(result, indent=2) if args.json else summary(result))


if __name__ == "__main__":
    main()
