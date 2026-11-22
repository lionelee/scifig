"""How pale are the fills of a figure? Lightness and chroma (CIELAB) of its coloured areas.

Usage: colour_stats.py [--clusters] IMAGE_OR_DIR ...
For each image: the share of the picture that is a light coloured area ("fill": L* >= 70 and
C* >= 4), the median and 90th percentile of the chroma of those pixels, their median lightness,
and the share of the picture in strong colour (C* >= 30).
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def lab(rgb):
    c = rgb.astype(np.float64) / 255
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
    xyz = c @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    L = 116 * f[..., 1] - 16
    a = 500 * (f[..., 0] - f[..., 1])
    b = 200 * (f[..., 1] - f[..., 2])
    return L, np.hypot(a, b)


def stats(path, clusters=False):
    image = Image.open(path).convert("RGB")
    image = image.resize((640, round(640 * image.height / image.width)), Image.Resampling.NEAREST)
    rgb = np.asarray(image)
    L, C = lab(rgb)
    fill = (L >= 70) & (C >= 4)
    row = {
        "fill_share": fill.mean(),
        "fill_c_med": float(np.median(C[fill])) if fill.any() else 0.0,
        "fill_c_p90": float(np.percentile(C[fill], 90)) if fill.any() else 0.0,
        "fill_l_med": float(np.median(L[fill])) if fill.any() else 0.0,
        "strong_share": (C >= 30).mean(),
    }
    if clusters:
        quant = image.quantize(colors=24, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        palette = np.array(quant.getpalette()[: 24 * 3]).reshape(-1, 3)
        index = np.asarray(quant)
        found = []
        for k in range(len(palette)):
            share = (index == k).mean()
            l, c = lab(palette[k][None, :].astype(np.uint8))
            if share >= 0.012 and not (l[0] >= 96 and c[0] <= 4) and l[0] >= 45:
                found.append((share, "#%02X%02X%02X" % tuple(palette[k]), l[0], c[0]))
        row["clusters"] = sorted(found, reverse=True)
    return row


def main():
    args = sys.argv[1:]
    clusters = "--clusters" in args
    paths = []
    for arg in (a for a in args if a != "--clusters"):
        p = Path(arg)
        paths += sorted(p.glob("*.png")) if p.is_dir() else [p]
    print(f"{'fill%':>6} {'C*med':>6} {'C*p90':>6} {'L*med':>6} {'strong%':>8}  file")
    rows = []
    for path in paths:
        row = stats(path, clusters)
        rows.append(row)
        print(f"{row['fill_share']:6.1%} {row['fill_c_med']:6.1f} {row['fill_c_p90']:6.1f} {row['fill_l_med']:6.1f} {row['strong_share']:8.1%}  {path.parent.name}/{path.name}")
        for share, hexcode, l, c in row.get("clusters", []):
            print(f"         {share:5.1%} {hexcode}  L* {l:4.0f}  C* {c:4.0f}")
    if len(rows) > 1:
        med = lambda key: float(np.median([row[key] for row in rows]))
        print(f"{med('fill_share'):6.1%} {med('fill_c_med'):6.1f} {med('fill_c_p90'):6.1f} {med('fill_l_med'):6.1f} {med('strong_share'):8.1%}  MEDIAN of {len(rows)}")


if __name__ == "__main__":
    main()
