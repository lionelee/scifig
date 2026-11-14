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
"""False verdicts of the text check on correct figures: labels centred in padded cards, the way generated
figures set them, in five faces at four sizes, as PNG and as JPEG. The labels are rich in doubled thin
letters, which OCR runs together. Every DIFFERS it prints is a false one.

    uv run stress_cards.py OUT_DIR [SCRIPTS_DIR]
"""
from pathlib import Path
import sys, io
sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[2] if len(sys.argv) > 2 else str(Path(__file__).resolve().parents[2] / "skills" / "scifig" / "scripts"))
from PIL import Image, ImageDraw, ImageFont
import check_text as ct

FONTS = {"arial": "/System/Library/Fonts/Supplemental/Arial.ttf", "helv": "/System/Library/Fonts/Helvetica.ttc",
         "verdana": "/System/Library/Fonts/Supplemental/Verdana.ttf", "arialn": "/System/Library/Fonts/Supplemental/Arial Narrow.ttf",
         "avenir": "/System/Library/Fonts/Avenir Next Condensed.ttc"}
LABELS = ["Pooling layer", "Skill set", "Cell wall", "Fully connected", "Little effect", "Attention", "Bottleneck",
          "Illumina", "Collagen fibre", "Pollen grain", "Small cell", "Spillover", "Villi", "Ciliated cells",
          "Shell", "Willow", "Scroll bar", "Oscillation", "Skip connection", "Softmax", "Overall", "Hidden state",
          "Feed Forward", "Allele frequency", "Billing", "Dropout"]
out = sys.argv[1]
total = bad = 0
for name, fp in FONTS.items():
    for size in (14, 16, 18, 22):
        for jpeg in (False, True):
            font = ImageFont.truetype(fp, size)
            cols, rows = 3, (len(LABELS) + 2) // 3
            cw, ch = 300, size * 3
            img = Image.new("RGB", (cols * cw + 40, rows * (ch + 24) + 40), (250, 250, 248))
            d = ImageDraw.Draw(img)
            for i, label in enumerate(LABELS):
                c, r = i % cols, i // cols
                x0, y0 = 20 + c * cw, 20 + r * (ch + 24)
                d.rounded_rectangle((x0 + 10, y0, x0 + cw - 10, y0 + ch), radius=10, fill=(232, 242, 252), outline=(70, 110, 160), width=2)
                d.text((x0 + cw / 2, y0 + ch / 2), label, font=font, fill=(25, 25, 25), anchor="mm")
            path = f"{out}/cards_{name}_{size}_{'jpg' if jpeg else 'png'}.{'jpg' if jpeg else 'png'}"
            img.save(path, quality=85) if jpeg else img.save(path)
            rep = ct.check(path, LABELS, 0.5)
            total += len(LABELS)
            for l in rep["labels"]:
                if l["second"] == "differs":
                    bad += 1
                    print(f"FALSE DIFFERS  {path.split('/')[-1]}: {l['text']!r} -> image says {l['closest']!r}")
print(f"false DIFFERS: {bad} of {total} correct labels")
