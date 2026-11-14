# /// script
# requires-python = ">=3.10,<3.15"
# dependencies = ["pillow>=10.3", "numpy"]
#
# [tool.uv]
# # The packages as they were on the day these scripts were tested: a later release cannot change their results.
# exclude-newer = "2026-11-14T00:00:00Z"
# ///
"""Enlarge a generated figure with detail from the image tool, tile by tile.

`split` cuts the figure along clear lines and writes one tile for each part: tiles of one size,
which overlap where the parts meet. The image tool then redraws each tile as a sharper copy,
which comes back larger. `join` lays every redraw over its tile, keeps the flat colours of the
original and puts the parts together again; along a cut, the two redraws pass into each other.
A redraw that moved or changed is left out: its tile is enlarged plainly, and the report says
so. The exit status is 0 whenever the command ran.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps

LONGEST = 2.9  # image tools take pictures up to 3:1
REACHES = (0.34, 0.16, 0.0)  # how much longer than its even share a part may get: more, and more tiles buy nothing
CLEAR = 3  # px that a cut keeps away from anything drawn, where there is room
EDGE = 48  # grey levels: the most one step of grey counts when the edges a cut crosses are counted, faint or dark
MARGIN = 12  # px that a tile reaches past each cut: over twice that, the redraws of two neighbours pass into each other
SEARCH = 2  # px of the tile that a redraw may sit off its tile and still be laid back
BLOCK = 64  # px of the tile: the size of the blocks whose likeness is measured
SLACK = 1  # px of the tile that the content of a block may sit off: image tools place a fine line that exactly
MATCH_MIN = 0.85  # the likeness that the least alike block must reach
SMOOTH = 6  # px of the tile: areas larger than this keep the colour of the original
EVEN = 24  # grey levels: a tile that changes less than this on the way across a cut shows one thing on both sides


def load(path):
    """The picture as RGB, upright, on white, with its ICC profile where that still describes it."""
    with Image.open(path) as image:
        ImageOps.exif_transpose(image, in_place=True)
        # An ICC profile stays valid only while the colour model does, and the picture becomes RGB.
        icc = image.info.get("icc_profile") if image.mode in ("RGB", "RGBA", "P") else None
        if image.mode.startswith("I;16"):
            # Pillow's own conversion clips 16-bit values above 255 to white.
            image = image.convert("I").point(lambda value: value * (1 / 256)).convert("L")
        elif image.mode in ("I", "F"):
            raise ValueError(
                f"cannot reduce a 32-bit {image.mode} image to 8-bit without its display range; save an 8-bit copy first"
            )
        rgba = image.convert("RGBA")
    picture = Image.alpha_composite(Image.new("RGBA", rgba.size, "white"), rgba).convert("RGB")
    if icc:
        picture.info["icc_profile"] = icc
    return picture


def grown(core, size):
    """A part of the figure and MARGIN px past each of its sides that is a cut: what its tile gives to the figure."""
    left, top, right, bottom = core
    return max(left - MARGIN, 0), max(top - MARGIN, 0), min(right + MARGIN, size[0]), min(bottom + MARGIN, size[1])


# --- split --------------------------------------------------------------------------------------


def crossings(grey, weigh):
    """For each column of a picture, what a cut along it would cross, every step of grey weighed with `weigh`."""
    width = grey.shape[1]
    cost = weigh(np.diff(grey, axis=0)).sum(axis=0)  # what the cut line runs through
    cost[1:-1] += weigh(grey[:, 2:] - grey[:, :-2]).sum(axis=0)  # what it would split lengthwise
    padded = np.pad(cost, CLEAR, mode="edge")
    return np.max([padded[shift : shift + width] for shift in range(2 * CLEAR + 1)], axis=0)  # the worst within CLEAR px


def quiet_cuts(grey, parts, reach):
    """Columns to cut a picture at: near each even split, one that crosses and touches little of the drawing."""
    width = grey.shape[1]
    cost = crossings(grey, np.abs)
    edges = crossings(grey, lambda step: np.minimum(np.abs(step), EDGE))  # how many edges rather than how dark
    span = reach * width / parts / (1 if parts == 2 else 2)  # an inner part lies between two cuts that may both move
    cuts = []
    for part in range(1, parts):
        centre = part * width / parts
        low, high = max(1, round(centre - span)), min(width - 1, round(centre + span) + 1)
        quiet = cost[low:high] <= 1.5 * cost[low:high].min()
        fewest = edges[low:high][quiet].min()
        rims = np.flatnonzero(np.diff(np.concatenate(([False], quiet, [False])).astype(np.int8))) + low
        spots = []
        for first, last in zip(rims[::2], rims[1::2] - 1):  # each clear band: the spot in it nearest the even split
            inset = min(MARGIN, (last - first) // 2)  # so that the stretch where neighbours pass into each other is clear
            spot = int(np.clip(round(centre), first + inset, last - inset))
            # Bands about as far from the even split (to a fifth of a part) count as equally near. Of those, one
            # that crosses half again as many edges as the fewest yields to the rest: an empty stretch of a box,
            # whose two outlines together can cost less than one dark line across open space. Then the widest
            # wins, which is open space rather than the rim of a box.
            more = bool(edges[first : last + 1].min() > 1.5 * fewest)
            spots.append((round(abs(spot - centre) / (0.2 * width / parts)), more, first - last, spot))
        cuts.append(min(spots)[3])
    return cuts


def windows(cores, size):
    """One box per part, all of one size: the part, MARGIN px past each cut, and whatever the largest part has
    more. Tiles of one size come back from the image tool at one scale: it draws the lines of a smaller tile
    heavier, and the same line would change weight from tile to tile."""
    reaches = [grown(core, size) for core in cores]
    width = max(right - left for left, _, right, _ in reaches)
    height = max(bottom - top for _, top, _, bottom in reaches)
    boxes = []
    for left, top, right, bottom in reaches:  # around the part, as far as the figure goes
        x = min(max((left + right - width) // 2, 0), size[0] - width)
        y = min(max((top + bottom - height) // 2, 0), size[1] - height)
        boxes.append((x, y, x + width, y + height))
    return boxes


def cut_up(grey, cols, rows):
    """(cores, boxes): the parts the figure is cut into, rows first and then each row into columns of its own,
    and the box of the tile that is written for each part."""
    height, width = grey.shape
    for reach in REACHES:  # cuts nearer the middle when the quiet ones make the tiles too long
        edges = [0, *quiet_cuts(grey.T, rows, reach), height]
        cores = []
        for top, bottom in zip(edges, edges[1:]):
            columns = [0, *quiet_cuts(grey[top:bottom], cols, reach), width]
            cores += [(left, top, right, bottom) for left, right in zip(columns, columns[1:])]
        boxes = windows(cores, (width, height))
        left, top, right, bottom = boxes[0]
        if max((right - left) / (bottom - top), (bottom - top) / (right - left)) <= LONGEST:
            return cores, boxes
    raise ValueError(
        f"tiles of {right - left} x {bottom - top} px are longer than 3:1, which image tools do not take: "
        "choose another --tiles"
    )


def split(args):
    source = Path(args.figure)
    image = load(source)
    folder = Path(args.output) if args.output else source.with_suffix(".tiles")
    if folder.exists() and any(folder.iterdir()):
        raise ValueError(f"{folder.name} already holds files: remove it or name another folder with -o")
    shape = image.width / image.height
    cols, rows = args.tiles or ((3, 1) if shape > 2.4 else (1, 3) if shape < 1 / 2.4 else (2, 2))
    cores, boxes = cut_up(np.asarray(image.convert("L"), dtype=np.float32), cols, rows)
    folder.mkdir(parents=True, exist_ok=True)
    tiles = []
    for number, (core, box) in enumerate(zip(cores, boxes), start=1):
        tiles.append({"file": f"tile-{number}.png", "redraw": f"redraw-{number}.png", "box": list(box), "core": list(core)})
        image.crop(box).save(folder / tiles[-1]["file"], icc_profile=image.info.get("icc_profile"))
    layout = {"source": source.name, "size": list(image.size), "tiles": tiles}
    (folder / "tiles.json").write_text(json.dumps(layout, indent=2) + "\n", encoding="utf-8")
    return {"input": str(source), "size": list(image.size), "folder": str(folder), "tiles": tiles}


# --- join ---------------------------------------------------------------------------------------


def grey(image, blur):
    return np.asarray(image.convert("L").filter(ImageFilter.BoxBlur(blur)), dtype=np.float32)


def low(image, radius):
    """The picture without its detail: what is left of areas larger than about `radius`."""
    return np.asarray(image.filter(ImageFilter.BoxBlur(radius)).filter(ImageFilter.BoxBlur(radius)), dtype=np.float32)


def correlation(a, b):
    a, b = a - a.mean(), b - b.mean()
    return float((a * b).sum() / max(math.sqrt(float((a * a).sum()) * float((b * b).sum())), 1e-9))


def offset(target, redraw, reach):
    """The shift (dx, dy) within `reach` px that lays the redraw best over the target: the smallest of the best."""
    rows, columns = target.shape
    core = target[reach : rows - reach, reach : columns - reach]
    shifts = sorted(
        ((dx, dy) for dx in range(-reach, reach + 1) for dy in range(-reach, reach + 1)),
        key=lambda shift: abs(shift[0]) + abs(shift[1]),
    )
    return max(
        shifts,
        key=lambda shift: correlation(
            core, redraw[reach - shift[1] : rows - reach - shift[1], reach - shift[0] : columns - reach - shift[0]]
        ),
    )


def match(target, redraw, block, slack):
    """The likeness of the least alike block among those that hold drawing in either picture. The content
    of a block may sit up to `slack` px off."""
    worst = 1.0
    padded = np.pad(redraw, slack, mode="edge")
    shifts = [(dx, dy) for dx in range(2 * slack + 1) for dy in range(2 * slack + 1)]
    for top in range(0, target.shape[0], block):
        for left in range(0, target.shape[1], block):
            a, b = target[top : top + block, left : left + block], redraw[top : top + block, left : left + block]
            if a.size >= block * block // 4 and max(a.std(), b.std()) >= 8:
                rows, columns = a.shape
                worst = min(worst, max(
                    correlation(a, padded[top + dy : top + dy + rows, left + dx : left + dx + columns]) for dx, dy in shifts
                ))
    return worst


def place(plain, sharp, part, scale):
    """The part `part` of a tile from its redraw: laid over the tile and with the flat colours of the tile.
    With it, the shift that took and the likeness of the two."""
    blur, before = max(1, round(scale)), plain.crop(part)
    shift = offset(grey(before, blur), grey(sharp.crop(part), blur), math.ceil(SEARCH * scale))
    moved = plain.copy()
    moved.paste(sharp, shift)  # what the shifted redraw leaves bare at an edge of the tile stays plain
    after = moved.crop(part)
    likeness = match(grey(before, blur), grey(after, blur), round(BLOCK * scale), math.ceil(SLACK * scale))
    radius = round(SMOOTH * scale)
    fixed = np.asarray(after, dtype=np.float32) + low(before, radius) - low(after, radius)  # flat colours as before
    return Image.fromarray(np.clip(fixed + 0.5, 0, 255).astype(np.uint8)), shift, likeness


def turned(pixels, side):
    """A view of the pixels with the given side as its first rows."""
    if side in ("left", "right"):
        pixels = pixels.swapaxes(0, 1)
    return pixels[::-1] if side in ("bottom", "right") else pixels


def feather(plain, bands, blur):
    """How much of a tile goes into the figure, pixel by pixel: all of it, and less and less across the band
    along each cut, where the neighbour takes over. `bands` gives the depth of that band for each side that is
    a cut; the cut runs down its middle.

    Where the tile shows one thing all the way across the band (clear space, a line that crosses the cut), the
    two tiles pass into each other over the whole band: a line that one redraw draws heavier than the other
    changes its weight little by little. Where it does not (text, an icon), the tile ends at the cut, so that
    nothing shows twice.
    """
    shade = grey(plain, blur)  # blurred: the edge of a crossing line wavers by a pixel on its way
    weights = np.ones(shade.shape, dtype=np.float32)
    for side, band in bands.items():
        strip = turned(shade, side)[:band]
        even = strip.max(axis=0) - strip.min(axis=0) < EVEN
        depth = np.arange(band, dtype=np.float32) + 0.5
        gradual, sudden = depth / band, np.clip(depth - band / 2 + 0.5, 0, 1)
        turned(weights, side)[:band] *= np.where(even, gradual[:, None], sudden[:, None])
    return weights


def read_redraw(folder, tile, original):
    """(the redraw, None) when it can be used, else (None, why not)."""
    name = Path(tile["redraw"]).name
    if not (folder / name).is_file():
        return None, f"{name} is missing"
    try:
        redraw = load(folder / name)
    except Image.UnidentifiedImageError:  # nothing in the file that Pillow knows as a picture
        return None, f"{name} is {'not a picture' if (folder / name).stat().st_size else 'empty'}"
    except OSError as exc:  # cut short or damaged on its way
        return None, f"{name} cannot be read ({exc})"
    if min(redraw.width / original.width, redraw.height / original.height) < 1.1:
        return None, f"{name} came back no larger"
    if abs(math.log(redraw.width / redraw.height * original.height / original.width)) > 0.03:
        return None, f"{name} came back in another shape ({redraw.width} x {redraw.height} px)"
    return redraw, None


def join(args):
    folder = Path(args.folder)
    if not (folder / "tiles.json").is_file():
        raise ValueError(f"{folder.name} holds no tiles.json: run split first")
    layout = json.loads((folder / "tiles.json").read_text(encoding="utf-8"))
    pieces = []
    for tile in layout["tiles"]:
        original = load(folder / Path(tile["file"]).name)
        pieces.append((tile, original, *read_redraw(folder, tile, original)))
    scales = [min(redraw.width / original.width, redraw.height / original.height) for _, original, redraw, _ in pieces if redraw]
    if not scales:
        raise ValueError("no tile has a redraw that can be used: nothing to join")
    scale = min(scales)

    def at(place_in_figure):
        """Where a place in the figure lies in the enlarged one."""
        return round(place_in_figure * scale)

    width, height = layout["size"]
    total = np.zeros((at(height), at(width), 3), dtype=np.float32)  # the tiles, each weighted with its share
    shares = np.zeros((at(height), at(width), 1), dtype=np.float32)
    tiles = []
    for tile, original, redraw, reason in pieces:
        box, core = tile["box"], tile["core"]
        reach = grown(core, (width, height))  # the part of the tile that goes into the figure
        size = (at(box[2]) - at(box[0]), at(box[3]) - at(box[1]))
        part = (at(reach[0]) - at(box[0]), at(reach[1]) - at(box[1]), at(reach[2]) - at(box[0]), at(reach[3]) - at(box[1]))
        plain = original.resize(size, Image.Resampling.LANCZOS)
        picture, shift, likeness = plain.crop(part), None, None
        if redraw:
            sharp, shift, likeness = place(plain, redraw.resize(size, Image.Resampling.LANCZOS), part, scale)
            if likeness < MATCH_MIN:
                reason = f"{Path(tile['redraw']).name} does not match it (match {likeness:.2f})"
            else:
                picture = sharp
        is_cut = (core[0] > 0, core[1] > 0, core[2] < width, core[3] < height)
        bands = {
            side: at(edge + MARGIN) - at(edge - MARGIN)
            for side, edge, cut in zip(("left", "top", "right", "bottom"), core, is_cut) if cut
        }
        share = feather(plain.crop(part), bands, max(1, round(scale)))[..., None]
        rows, columns = slice(at(reach[1]), at(reach[3])), slice(at(reach[0]), at(reach[2]))
        total[rows, columns] += share * np.asarray(picture, dtype=np.float32)
        shares[rows, columns] += share
        tiles.append({
            "file": tile["file"], "redraw": tile["redraw"], "status": "plain" if reason else "redrawn",
            "shift": list(shift) if shift else None, "match": round(likeness, 3) if likeness is not None else None,
            "reason": reason,
        })
    output = Path(args.output) if args.output else folder.parent / f"{Path(layout['source']).stem}-enlarged.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    # A redraw copies the values of its tile, so the figure keeps the profile that split gave every tile.
    icc = pieces[0][1].info.get("icc_profile")
    Image.fromarray(np.clip(total / shares + 0.5, 0, 255).astype(np.uint8)).save(output, icc_profile=icc)
    return {
        "input": str(folder), "output": str(output), "size": [at(width), at(height)], "scale": round(scale, 3),
        "redrawn": sum(tile["status"] == "redrawn" for tile in tiles), "tiles": tiles,
    }


# --- the command --------------------------------------------------------------------------------


def grid(text):
    try:
        cols, rows = (int(part) for part in text.lower().split("x"))
    except ValueError:
        raise argparse.ArgumentTypeError(f"must be COLUMNSxROWS, such as 2x2, got {text}") from None
    if not (1 <= cols <= 4 and 1 <= rows <= 4 and cols * rows >= 2):
        raise argparse.ArgumentTypeError(f"must be one to four columns and rows, and two tiles or more, got {text}")
    return cols, rows


def build_parser():
    parser = argparse.ArgumentParser(
        description="Enlarge a generated figure with detail from the image tool: split it into tiles, have the tool "
        "redraw each tile as a sharper copy, and join the redraws.",
        epilog="The exit status is 0 whenever the command ran: read each tile's line, or \"tiles\" with --json.",
    )
    commands = parser.add_subparsers(dest="command", required=True, metavar="{split,join}")
    cut = commands.add_parser("split", help="cut a figure along clear lines and write a tile for each part")
    cut.add_argument("figure", metavar="FIGURE", help="the figure to enlarge")
    cut.add_argument(
        "--tiles", type=grid, metavar="COLUMNSxROWS",
        help="how many tiles (default: 2x2, or three in a row for a figure longer than 2.4:1); more tiles give a "
        "larger figure and cost one redraw each",
    )
    cut.add_argument("-o", "--output", metavar="DIR", help="folder for the tiles (default: FIGURE's name with .tiles)")
    cut.add_argument("--json", action="store_true", help="print one JSON object instead of the lines")
    cut.set_defaults(run=split)
    paste = commands.add_parser("join", help="put the redrawn tiles together")
    paste.add_argument("folder", metavar="DIR", help="the folder that split wrote, with a redraw beside each tile")
    paste.add_argument("-o", "--output", metavar="FILE", help="the enlarged figure (default: FIGURE's name with -enlarged.png)")
    paste.add_argument("--json", action="store_true", help="print one JSON object instead of the lines")
    paste.set_defaults(run=join)
    return parser


def main():
    # A Windows pipe takes the ANSI code page, which cannot print a file name in Chinese: print UTF-8.
    if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args()
    try:
        report = args.run(args)
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        sys.exit(f"enlarge: {exc}")
    if args.json:
        print(json.dumps(report, indent=2))
    elif args.command == "split":
        print(f"wrote {len(report['tiles'])} tiles to {report['folder']}")
        for tile in report["tiles"]:
            left, top, right, bottom = tile["box"]
            print(f"{tile['file']}  {right - left} x {bottom - top} px, redraw it as {tile['redraw']}")
    else:
        for tile in report["tiles"]:
            if tile["status"] == "redrawn":
                print(f"redrawn  {tile['file']}  laid {tile['shift'][0]},{tile['shift'][1]} px over its tile, match {tile['match']:.2f}")
            else:
                print(f"plain    {tile['file']}  {tile['reason']}: enlarged without new detail")
        print(f"wrote {report['output']}")
        kind = Path(report["output"]).suffix.lstrip(".").lower()
        print(
            f"{kind}, {report['size'][0]} x {report['size'][1]} px, {report['scale']:.3g} times the original; "
            f"{report['redrawn']} of {len(report['tiles'])} tiles redrawn"
        )


if __name__ == "__main__":
    sys.dont_write_bytecode = True  # as a command, leave no __pycache__ next to this file
    main()
