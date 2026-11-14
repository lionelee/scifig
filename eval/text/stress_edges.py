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
# # rapidocr-onnxruntime asks for the GUI build of OpenCV; the headless build is the same cv2.
# override-dependencies = ["opencv-python ; sys_platform == 'never'"]
# ///
"""False verdicts of the text check on correct figures where the border of a card stands 3 or 6 px before a
label, or nothing does: the place where OCR reads a stroke as a letter. Every DIFFERS it prints is a false
one; the run of 0.5.1 had 31 among 1260 labels, the fixed check 6, all letters put in inside a word.

    uv run stress_edges.py OUT_DIR [SCRIPTS_DIR]
"""
from pathlib import Path
import sys, time
sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[2] if len(sys.argv) > 2 else str(Path(__file__).resolve().parents[2] / "skills" / "scifig" / "scripts"))
from PIL import Image, ImageDraw, ImageFont
import check_text as ct

FONTS = {"arial": "/System/Library/Fonts/Supplemental/Arial.ttf", "helv": "/System/Library/Fonts/Helvetica.ttc",
         "verdana": "/System/Library/Fonts/Supplemental/Verdana.ttf", "arialn": "/System/Library/Fonts/Supplemental/Arial Narrow.ttf"}
LABELS = ["Pooling layer", "Skill set", "Cell wall", "Fully connected", "Little effect", "Attention", "Bottleneck",
          "Illumina", "Collagen fibre", "Pollen grain", "Small cell", "Spillover", "Villi", "Ciliated cells",
          "Shell", "Willow", "Scroll bar", "Oscillation", "Skip connection", "Softmax", "Overall"]
out = sys.argv[1]
bad = 0
for name, fp in FONTS.items():
    for size in (13, 15, 17, 20, 24):
        for gap in (None, 3, 6):
            font = ImageFont.truetype(fp, size)
            rows = len(LABELS)
            pitch = int(size * 2.6)
            img = Image.new("RGB", (900, pitch * rows + 40), "white")
            d = ImageDraw.Draw(img)
            for i, label in enumerate(LABELS):
                top = 20 + pitch * i
                x = 100
                if gap is not None:  # a card border right before the text
                    d.rectangle((x - gap - 2, top - 4, x - gap, top + size + 6), fill=(49, 104, 157))
                d.text((x, top), label, font=font, fill=(30, 30, 30))
            path = f"{out}/sweep_{name}_{size}_{gap}.png"
            img.save(path)
            rep = ct.check(path, LABELS, 0.5)
            for l in rep["labels"]:
                if l["second"] == "differs":
                    bad += 1
                    print(f"FALSE DIFFERS  {name} {size}px gap={gap}: {l['text']!r} -> image says {l['closest']!r}")
            others = [l for l in rep["labels"] if l["found"] != l["listed"] and l["second"] != "differs"]
            if others:
                print(f"  ({name} {size}px gap={gap}: not found: " + ", ".join(f"{l['text']!r}->{l['closest']!r}/{l['second']}" for l in others) + ")")
print("false DIFFERS:", bad)
