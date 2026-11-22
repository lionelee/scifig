# /// script
# requires-python = ">=3.11,<3.13"
# dependencies = ["rapidocr-onnxruntime==1.4.4", "opencv-python-headless>=5.0,<6", "numpy>=2,<3", "pillow>=13,<14"]
# [tool.uv]
# override-dependencies = ["opencv-python ; sys_platform == 'never'"]
# ///
"""How a text reads when its place is cut out in different ways, with the OCR code of this repository.   uv run vary.py FIGURE TEXT"""
import contextlib, logging, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skills" / "scifig" / "scripts"))
sys.dont_write_bytecode = True
import cv2
import numpy as np
import editable
logging.disable(logging.CRITICAL)
figure, wanted = sys.argv[1], sys.argv[2]
picture = editable.load_image(figure)
with contextlib.redirect_stdout(sys.stderr):
    found = editable.read_text(picture)
for text, quad, confidence in found:
    if wanted not in text:
        continue
    left, top, right, bottom = quad[:, 0].min(), quad[:, 1].min(), quad[:, 0].max(), quad[:, 1].max()
    print(f"whole picture: {text!r} ({confidence:.2f})  {right - left:.0f} x {bottom - top:.0f} px")
    for factor in (1, 1.5, 2, 3, 4):
        for around in (0.3, 0.6, 1.0):
            for name, method in (("cubic", cv2.INTER_CUBIC), ("linear", cv2.INTER_LINEAR), ("lanczos", cv2.INTER_LANCZOS4)):
                pad = around * (bottom - top)
                rows = slice(max(0, math.floor(top - pad)), math.ceil(bottom + pad))
                cols = slice(max(0, math.floor(left - pad)), math.ceil(right + pad))
                large = cv2.resize(picture[rows, cols], None, fx=factor, fy=factor, interpolation=method)
                with contextlib.redirect_stdout(sys.stderr):
                    pieces = editable.read_text(large)
                kept = []
                for t, q, c in pieces:
                    x, y = q.mean(axis=0) / factor + (cols.start, rows.start)
                    if left <= x <= right and top <= y <= bottom:
                        kept.append((float(q[:, 0].min()), f"{t.strip()} ({c:.2f})"))
                print(f"   x{factor:<3} around {around}  {name:7}: " + " | ".join(t for _, t in sorted(kept)))
    break
