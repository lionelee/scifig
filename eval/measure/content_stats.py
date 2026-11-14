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
"""How much does a figure carry? Texts read by OCR, their characters, and the share of the page that is not white.

Usage: content_stats.py SCRIPTS_DIR [--each] NAME=PATH[,PATH...] ...
"""
import statistics
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
import check_text  # noqa: E402
import editable  # noqa: E402


def measure(path):
    picture = editable.load_image(path)
    texts = [text.strip() for text, _, confidence in editable.read_text(picture) if confidence >= 0.5 and text.strip()]
    keys = [check_text.squash(text) for text in texts]
    words = [key for key in keys if sum(ch.isalnum() for ch in key) >= 2]
    ink = (picture.min(axis=2) < 235).mean()
    return {"texts": len(words), "chars": sum(len(key) for key in words), "ink": float(ink), "sample": words}


each = "--each" in sys.argv
for group in (arg for arg in sys.argv[2:] if arg != "--each"):
    name, _, spec = group.partition("=")
    paths = []
    for part in spec.split(","):
        p = Path(part)
        paths += sorted(p.glob("*.png")) if p.is_dir() else [p]
    rows = [(path, measure(path)) for path in paths]
    if each:
        for path, row in rows:
            print(f"    {row['texts']:4d} texts {row['chars']:5d} chars  ink {row['ink']:5.1%}  {path.parent.name}/{path.name}")
    med = lambda key: statistics.median(row[key] for _, row in rows)
    low = lambda key: min(row[key] for _, row in rows)
    high = lambda key: max(row[key] for _, row in rows)
    print(f"{name:30s} n={len(rows):2d}  texts: median {med('texts'):5.1f} ({low('texts')}-{high('texts')})  chars: median {med('chars'):6.1f} ({low('chars')}-{high('chars')})  ink: median {med('ink'):5.1%}")
