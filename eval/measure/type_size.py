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
"""How large is the type of a figure? The height of the text lines that OCR reads, against the height of the picture.

Usage: type_size.py SCRIPTS_DIR NAME=PATH[,PATH...] ...
Prints per picture the number of lines, and the median and the smallest tenth of their heights
as a share of the picture's height, in pixels of a picture 941 px high, and in points on a
slide 540 pt high that the picture fills.
"""
import statistics
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
import editable  # noqa: E402

for group in sys.argv[2:]:
    name, _, spec = group.partition("=")
    for part in spec.split(","):
        picture = editable.load_image(Path(part))
        heights = []
        for text, quad, confidence in editable.read_text(picture):
            if confidence >= 0.5 and sum(ch.isalnum() for ch in text) >= 4:
                heights.append(float(quad[:, 1].max() - quad[:, 1].min()))
        heights = np.array(heights) / picture.shape[0]
        median, small = float(np.median(heights)), float(np.percentile(heights, 10))
        print(f"{name:10s} {len(heights):3d} lines  median {median:.2%} of the height = {median * 941:4.1f} px at 941 = {median * 540 * 0.75:4.1f} pt"
              f"   smallest tenth {small:.2%} = {small * 941:4.1f} px = {small * 540 * 0.75:4.1f} pt   {Path(part).parent.name}/{Path(part).name}")
