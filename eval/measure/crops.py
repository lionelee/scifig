"""Details of figures at the same share of their width, side by side.   crops.py OUT HEIGHT LABEL=PATH:x0,y0,x1,y1 ...  (box in fractions of the width and height)"""
import sys
from PIL import Image, ImageDraw, ImageFont

out, height = sys.argv[1], int(sys.argv[2])
font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 20)
tiles = []
for item in sys.argv[3:]:
    label, _, rest = item.partition("=")
    path, _, box = rest.rpartition(":")
    x0, y0, x1, y1 = map(float, box.split(","))
    image = Image.open(path).convert("RGB")
    crop = image.crop((round(x0 * image.width), round(y0 * image.height), round(x1 * image.width), round(y1 * image.height)))
    crop = crop.resize((round(crop.width * height / crop.height), height), Image.Resampling.LANCZOS)
    tiles.append((label, crop))
gap = 14
sheet = Image.new("RGB", (sum(crop.width for _, crop in tiles) + gap * (len(tiles) - 1), height + 30), "white")
draw = ImageDraw.Draw(sheet)
x = 0
for label, crop in tiles:
    draw.text((x + 4, 4), label, font=font, fill=(200, 30, 30) if label.startswith("OURS") else (20, 20, 20))
    sheet.paste(crop, (x, 30))
    x += crop.width + gap
sheet.save(out)
print(out, sheet.size)
