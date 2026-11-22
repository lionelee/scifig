# /// script
# requires-python = ">=3.11,<3.13"
# dependencies = [
#   "rapidocr-onnxruntime==1.4.4",
#   "opencv-python-headless>=5.0,<6",
#   "numpy>=2,<3",
#   "pillow>=13,<14",
# ]
#
# [tool.uv]
# override-dependencies = ["opencv-python ; sys_platform == 'never'"]
# ///
"""How fine is the grain of a figure?

Usage: detail.py SCRIPTS_DIR [--each] NAME=PATH[,PATH...] ...
Per figure: the lines of text and their characters; the share of the lines that carry a
parenthesis; the parts that the drawing is made of (connected shapes of stroke outside the
text, from 0.35% of the width up, long straight lines left out); the length of all outlines
of the drawing against the diagonal of the figure; and how many parts an average pictorial
element (as element_stats.py finds them) is made of.
"""
import contextlib
import logging
import os
import statistics
import sys
from pathlib import Path

os.environ["ORT_DISABLE_TELEMETRY"] = "1"
import cv2
import numpy as np

sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
sys.path.insert(0, str(Path(__file__).parent))  # the other measures sit beside this file
import editable  # noqa: E402
from colour_stats import lab  # noqa: E402

logging.disable(logging.CRITICAL)


def measure(path):
    picture = editable.load_image(path)
    L, C = lab(picture[:, :, ::-1])
    h, w = L.shape
    stroke = (((C >= 20) & (L < 85)) | (L < 60)).astype(np.uint8)
    text = np.zeros((h, w), np.uint8)
    with contextlib.redirect_stdout(sys.stderr):
        found = editable.read_text(picture)
    lines = [content.strip() for content, quad, confidence in found if confidence >= 0.5 and sum(ch.isalnum() for ch in content) >= 2]
    for content, quad, confidence in found:
        if confidence >= 0.5 and sum(ch.isalnum() for ch in content) >= 2:
            cv2.fillPoly(text, [np.round(quad).astype(np.int32)], 1)
    text = cv2.dilate(text, np.ones((7, 7), np.uint8))
    drawn = stroke & (1 - text)
    long_px, thick = round(0.04 * w), max(3, round(0.008 * w))
    straight = np.zeros_like(drawn)
    for kernel, across in ((np.ones((1, long_px), np.uint8), np.ones((thick + 1, 1), np.uint8)),
                           (np.ones((long_px, 1), np.uint8), np.ones((1, thick + 1), np.uint8))):
        runs = cv2.morphologyEx(drawn, cv2.MORPH_OPEN, kernel)
        straight |= runs & (1 - cv2.morphologyEx(runs, cv2.MORPH_OPEN, across))
    shapes = drawn & (1 - cv2.dilate(straight, np.ones((3, 3), np.uint8)))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(shapes, connectivity=8)
    parts = [index for index in range(1, count) if max(stats[index][2], stats[index][3]) >= 0.0035 * w]
    outline = shapes & (1 - cv2.erode(shapes, np.ones((3, 3), np.uint8)))
    # pictorial elements, as in element_stats.py, and the parts inside each
    joined = cv2.morphologyEx(shapes, cv2.MORPH_CLOSE, np.ones((max(3, round(0.006 * w)),) * 2, np.uint8))
    n, _, big, _ = cv2.connectedComponentsWithStats(joined, connectivity=8)
    inside = []
    for index in range(1, n):
        x, y, bw, bh, pixels = big[index]
        if 0.018 * w <= max(bw, bh) <= 0.20 * w and min(bw, bh) >= 0.010 * w and pixels >= 0.00006 * w * h:
            window = labels[y:y + bh, x:x + bw]
            inside.append(len({int(v) for v in np.unique(window) if v and max(stats[v][2], stats[v][3]) >= 0.0035 * w}))
    return {
        "lines": len(lines), "chars": sum(len("".join(line.split())) for line in lines),
        "paren": sum("(" in line or "（" in line for line in lines) / max(1, len(lines)),
        "parts": len(parts), "outline": float(outline.sum()) / (w * w + h * h) ** 0.5,
        "pictures": len(inside), "per_picture": statistics.median(inside) if inside else 0.0,
    }


args = [a for a in sys.argv[2:] if a != "--each"]
each = "--each" in sys.argv
print(f"{'group':14} n  lines  chars  paren%  parts  outline/diag  pictures  parts/picture")
for group in args:
    name, _, spec = group.partition("=")
    paths = []
    for part in spec.split(","):
        p = Path(part)
        paths += sorted(p.glob("*.png")) if p.is_dir() else [p]
    rows = [(path, measure(path)) for path in paths]
    if each:
        for path, row in rows:
            print(f"   {row['lines']:5d} {row['chars']:6d} {row['paren']:6.0%} {row['parts']:6d} {row['outline']:10.1f} {row['pictures']:9d} {row['per_picture']:10.1f}   {path.parent.name}/{path.name}")
    med = lambda key: statistics.median(row[key] for _, row in rows)
    print(f"{name:14} {len(rows):2} {med('lines'):5.0f} {med('chars'):6.0f} {med('paren'):6.0%} {med('parts'):6.0f} {med('outline'):10.1f} {med('pictures'):9.0f} {med('per_picture'):10.1f}")
    sys.stdout.flush()
