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
"""How many pictorial elements does a figure carry, besides its text and its straight lines?

Usage: element_stats.py SCRIPTS_DIR [--each] [--overlay DIR] NAME=PATH[,PATH...] ...
Stroke pixels (clearly coloured or dark) outside the text that OCR reads, minus long thin
straight lines (box outlines, frames, arrow shafts), are grouped into connected shapes. A shape
between 1.8% and 20% of the image width, and not line-like, counts as a pictorial element: an
icon, a symbol, a drawn object. Also given: the share of the image those shapes cover.
"""
import statistics
import sys
from pathlib import Path

import cv2
import numpy as np

sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
sys.path.insert(0, str(Path(__file__).parent))
import editable  # noqa: E402
from colour_stats import lab  # noqa: E402


def elements(path, overlay=None):
    picture = editable.load_image(path)
    L, C = lab(picture[:, :, ::-1])
    h, w = L.shape
    stroke = (((C >= 20) & (L < 85)) | (L < 60)).astype(np.uint8)
    text = np.zeros((h, w), np.uint8)
    texts = 0
    for content, quad, confidence in editable.read_text(picture):
        if confidence >= 0.5 and sum(ch.isalnum() for ch in content) >= 2:
            cv2.fillPoly(text, [np.round(quad).astype(np.int32)], 1)
            texts += 1
    text = cv2.dilate(text, np.ones((7, 7), np.uint8))
    drawn = stroke & (1 - text)
    long_px, thick = round(0.04 * w), max(3, round(0.008 * w))
    lines = np.zeros_like(drawn)
    for kernel, across in ((np.ones((1, long_px), np.uint8), np.ones((thick + 1, 1), np.uint8)),
                           (np.ones((long_px, 1), np.uint8), np.ones((1, thick + 1), np.uint8))):
        runs = cv2.morphologyEx(drawn, cv2.MORPH_OPEN, kernel)
        lines |= runs & (1 - cv2.morphologyEx(runs, cv2.MORPH_OPEN, across))  # long and thin: a line, not a filled shape
    shapes = drawn & (1 - cv2.dilate(lines, np.ones((3, 3), np.uint8)))
    joined = cv2.morphologyEx(shapes, cv2.MORPH_CLOSE, np.ones((max(3, round(0.006 * w)),) * 2, np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(joined, connectivity=8)
    kept, area, marks = [], 0, 0
    for index in range(1, count):
        x, y, bw, bh, pixels = stats[index]
        if 0.018 * w <= max(bw, bh) <= 0.20 * w and min(bw, bh) >= 0.010 * w and pixels >= 0.00006 * w * h:
            kept.append((x, y, bw, bh))
            area += int(pixels)
        elif 0.006 * w <= max(bw, bh) < 0.018 * w and min(bw, bh) >= 0.004 * w:
            marks += 1  # a small mark: a bullet badge, a clock, a check, a swatch, an arrow head
    if overlay:
        view = picture.copy()
        for x, y, bw, bh in kept:
            cv2.rectangle(view, (x, y), (x + bw, y + bh), (255, 0, 255), 2)
        cv2.imwrite(str(Path(overlay) / f"{Path(path).parent.name}_{Path(path).stem}_elements.png"), view)
    return {"elements": len(kept), "marks": marks, "share": area / (w * h), "drawn": float(shapes.mean()), "texts": texts}


args = sys.argv[2:]
each = "--each" in args
overlay = args[args.index("--overlay") + 1] if "--overlay" in args else None
groups = [a for i, a in enumerate(args) if a not in ("--each", "--overlay") and (i == 0 or args[i - 1] != "--overlay")]
for group in groups:
    name, _, spec = group.partition("=")
    paths = []
    for part in spec.split(","):
        p = Path(part)
        paths += sorted(p.glob("*.png")) if p.is_dir() else [p]
    rows = [(path, elements(path, overlay)) for path in paths]
    if each:
        for path, row in rows:
            print(f"    {row['elements']:4d} elements {row['marks']:4d} marks  drawn {row['drawn']:5.1%}  {row['texts']:4d} texts  {path.parent.name}/{path.name}")
    med = lambda key: statistics.median(row[key] for _, row in rows)
    quart = lambda key, p: sorted(row[key] for _, row in rows)[min(len(rows) - 1, round(p * (len(rows) - 1)))]
    print(f"{name:32s} n={len(rows):2d}  elements: median {med('elements'):5.1f} (quartiles {quart('elements', .25)}-{quart('elements', .75)})  small marks: median {med('marks'):5.1f}  drawn ink: median {med('drawn'):5.1%}")
