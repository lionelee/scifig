"""Line thickness of figures with the measure of check_figure.py (fractions of a pixel).

Usage: stroke_fine.py SCRIPTS_DIR [--each] NAME=PATH[,PATH...] ...
A PATH that is a folder stands for every PNG below it, the copies under "architecture" left out.
Prints, for each group, the median and the quartiles of the thickness in the picture's own
pixels and as a share of its width, for the coloured and for the dark lines.
"""
import statistics
import sys
from pathlib import Path

from PIL import Image

sys.dont_write_bytecode = True  # leave no __pycache__ in the skill's scripts folder
sys.path.insert(0, sys.argv[1])
import check_figure  # noqa: E402


def summary(values):
    if len(values) < 2:
        return f"{values[0]:.2f}" if values else "-"
    low, _, high = statistics.quantiles(values, n=4)
    return f"{statistics.median(values):.2f} ({low:.2f}-{high:.2f})"


each = "--each" in sys.argv
for group in (arg for arg in sys.argv[2:] if arg != "--each"):
    name, _, spec = group.partition("=")
    paths = []
    for part in spec.split(","):
        p = Path(part)
        paths += sorted(q for q in p.rglob("*.png") if q.parent.name != "architecture") if p.is_dir() else [p]
    rows = []
    for path in paths:
        with Image.open(path) as image:
            rows.append((path, image.width, image.width * image.height, check_figure.measure_lines(image.convert("RGB"))))
    for label, chosen in (
        ("all", rows),
        ("up to 1.7 MP", [row for row in rows if row[2] < 1.7e6]),
        ("larger", [row for row in rows if row[2] >= 1.7e6]),
    ):
        if not chosen or (label != "all" and len(chosen) == len(rows)):
            continue
        line = f"{name:14s} {label:13s} n={len(chosen):2d}"
        for kind in ("coloured", "dark"):
            px = [m[f"{kind}_px"] for _, _, _, m in chosen if m[f"{kind}_px"] is not None]
            share = [100 * m[f"{kind}_share"] for _, _, _, m in chosen if m[f"{kind}_share"] is not None]
            line += f" | {kind} in {len(px):2d}: {summary(px)} px, {summary(share)} %"
        print(line)
    if each:
        for path, width, _, m in rows:
            print(f"      {width:5d} px wide  coloured {m['coloured_px']} px  dark {m['dark_px']} px   {path.parent.name}/{path.name}")
