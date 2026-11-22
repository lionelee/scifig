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
"""How bold and how colourful are the pictures of a figure?

Usage: bold.py SCRIPTS_DIR [--each] NAME=PATH[,PATH...] ...
Per figure: the share of it in visible colour (C* >= 15) and in strong colour (C* >= 30); the
number of hue families (of 12) that each hold a twelfth or more of its coloured pixels; and for
its pictorial elements (as element_stats.py finds them): how many, their median size against
the width of the figure, how much of their box is ink (a line drawing has little, a filled
shape much), and the share of the figure they cover.
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


def hue_angle(rgb):
    c = rgb.astype(np.float64) / 255
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    m = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
    xyz = c @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    a, b = 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])
    return np.degrees(np.arctan2(b, a)) % 360


def measure(path):
    picture = editable.load_image(path)
    rgb = picture[:, :, ::-1]
    L, C = lab(rgb)
    h, w = L.shape
    coloured = C >= 12
    bins = np.bincount((hue_angle(rgb)[coloured] // 30).astype(int), minlength=12) if coloured.any() else np.zeros(12)
    hues = int((bins >= coloured.sum() / 12).sum()) if coloured.any() else 0
    stroke = (((C >= 20) & (L < 85)) | (L < 60)).astype(np.uint8)
    text = np.zeros((h, w), np.uint8)
    with contextlib.redirect_stdout(sys.stderr):
        found = editable.read_text(picture)
    for content, quad, confidence in found:
        if confidence >= 0.5 and sum(ch.isalnum() for ch in content) >= 2:
            cv2.fillPoly(text, [np.round(quad).astype(np.int32)], 1)
    text = cv2.dilate(text, np.ones((7, 7), np.uint8))
    drawn = stroke & (1 - text)
    long_px, thick = round(0.04 * w), max(3, round(0.008 * w))
    lines = np.zeros_like(drawn)
    for kernel, across in ((np.ones((1, long_px), np.uint8), np.ones((thick + 1, 1), np.uint8)),
                           (np.ones((long_px, 1), np.uint8), np.ones((1, thick + 1), np.uint8))):
        runs = cv2.morphologyEx(drawn, cv2.MORPH_OPEN, kernel)
        lines |= runs & (1 - cv2.morphologyEx(runs, cv2.MORPH_OPEN, across))
    shapes = drawn & (1 - cv2.dilate(lines, np.ones((3, 3), np.uint8)))
    joined = cv2.morphologyEx(shapes, cv2.MORPH_CLOSE, np.ones((max(3, round(0.006 * w)),) * 2, np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(joined, connectivity=8)
    sizes, fills, chroma, area = [], [], [], 0
    for index in range(1, count):
        x, y, bw, bh, pixels = stats[index]
        if 0.018 * w <= max(bw, bh) <= 0.20 * w and min(bw, bh) >= 0.010 * w and pixels >= 0.00006 * w * h:
            inside = (labels[y:y + bh, x:x + bw] == index) & (shapes[y:y + bh, x:x + bw] > 0)
            sizes.append(max(bw, bh) / w)
            fills.append(float(inside.sum()) / (bw * bh))
            chroma.append(float(np.median(C[y:y + bh, x:x + bw][inside])) if inside.any() else 0.0)
            area += int(inside.sum())
    return {
        "mid": float((C >= 15).mean()), "strong": float((C >= 30).mean()), "hues": hues,
        "elements": len(sizes), "size": statistics.median(sizes) if sizes else 0.0,
        "ink": statistics.median(fills) if fills else 0.0, "chroma": statistics.median(chroma) if chroma else 0.0,
        "cover": area / (w * h),
    }


args = [a for a in sys.argv[2:] if a != "--each"]
each = "--each" in sys.argv
print(f"{'group':15} n   mid%  strong%  hues  elements  size%w  ink-of-box  element C*  cover%")
for group in args:
    name, _, spec = group.partition("=")
    paths = []
    for part in spec.split(","):
        p = Path(part)
        paths += sorted(p.glob("*.png")) if p.is_dir() else [p]
    rows = [(path, measure(path)) for path in paths]
    if each:
        for path, row in rows:
            print(f"   {row['mid']:6.1%} {row['strong']:7.1%} {row['hues']:5d} {row['elements']:8d} {row['size']:8.1%} {row['ink']:10.0%} {row['chroma']:10.0f} {row['cover']:7.1%}  {path.parent.name}/{path.name}")
    med = lambda key: statistics.median(row[key] for _, row in rows)
    print(f"{name:15} {len(rows):2} {med('mid'):6.1%} {med('strong'):7.1%} {med('hues'):5.1f} {med('elements'):8.1f} {med('size'):8.1%} {med('ink'):10.0%} {med('chroma'):10.0f} {med('cover'):7.1%}")
    sys.stdout.flush()
