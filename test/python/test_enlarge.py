"""Tests for skills/scifig/scripts/enlarge.py, run as a CLI through uv.

The image tool is played by Pillow: a "redraw" is the tile made larger, sometimes moved, tinted
or changed, the way a real redraw can come back.
"""
import json
import os
import re
import struct
import subprocess
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageCms, ImageDraw

SCRIPT = Path(__file__).resolve().parents[2] / "skills" / "scifig" / "scripts" / "enlarge.py"
UV = os.environ.get("UV", "uv")
SIZE = (1200, 700)
GAP_X, GAP_Y = (630, 690), (290, 340)  # the white bands between the cards: the only clear lines near the middle
TINT, BLUE, DARK = "#E8F2FC", "#1D83BB", "#3B3B3B"
P3_PRIMARIES = {b"rXYZ": (0.5151, 0.2412, -0.0011), b"gXYZ": (0.2920, 0.6922, 0.0419), b"bXYZ": (0.1571, 0.0666, 0.7841)}


def run(*args, cwd):
    return subprocess.run([UV, "run", "--quiet", str(SCRIPT), *map(str, args)], cwd=cwd, capture_output=True, text=True)


def report(*args, cwd):
    """Run with --json, expect success and return the parsed report."""
    proc = run(*args, "--json", cwd=cwd)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def figure(path, size=SIZE):
    """Four tinted cards with outlines and lines of text, a gap between the columns and one between the rows."""
    image = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(image)
    for left, right in ((40, GAP_X[0]), (GAP_X[1], size[0] - 40)):
        for top, bottom in ((40, GAP_Y[0]), (GAP_Y[1], size[1] - 40)):
            if right - left < 80 or bottom - top < 80:
                continue  # no room for this card in a narrow or a low figure
            draw.rounded_rectangle((left, top, right, bottom), radius=14, fill=TINT, outline=BLUE, width=2)
            for row in range(5):
                draw.text((left + 24, top + 24 + 40 * row), f"Step {row + 1}: measure and compare", fill=DARK, font_size=26)
    image.save(path)
    return path


def split(tmp_path, *args, size=SIZE):
    """Draw the figure, split it, and return (the folder of tiles, the report)."""
    source = figure(tmp_path / "fig.png", size)
    result = report("split", source, *args, cwd=tmp_path)
    return tmp_path / "fig.tiles", result


def redraw(folder, tile, factor=2.0, change=None):
    """Play the image tool for one tile: the tile, `factor` times as large, after `change`."""
    image = Image.open(folder / tile["file"]).convert("RGB")
    image = image.resize((round(image.width * factor), round(image.height * factor)), Image.Resampling.LANCZOS)
    if change:
        image = change(image)
    image.save(folder / tile["redraw"])


def enlarged(source, factor, how=Image.Resampling.LANCZOS):
    image = Image.open(source).convert("RGB")
    return image.resize((round(image.width * factor), round(image.height * factor)), how)


def difference(first, second, box=None):
    """The mean absolute difference of two pictures, in grey levels, over a box."""
    a, b = (np.asarray(image.convert("RGB").crop(box) if box else image.convert("RGB"), dtype=float) for image in (first, second))
    return float(np.abs(a - b).mean())


def scaled(box, factor):
    return tuple(round(value * factor) for value in box)


def display_p3():
    """An ICC profile of Display P3: the profile of sRGB with the wider primaries of Display P3 in place of its own
    (adapted to D50, as a profile holds them). Display P3 has the curve of sRGB."""
    profile = bytearray(ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes())
    (count,) = struct.unpack_from(">I", profile, 128)
    for index in range(count):
        tag, offset, _ = struct.unpack_from(">4sII", profile, 132 + 12 * index)
        if tag in P3_PRIMARIES:
            struct.pack_into(">3i", profile, offset + 8, *(round(value * 65536) for value in P3_PRIMARIES[tag]))
    profile[84:100] = bytes(16)  # no profile ID: it would not match the new primaries
    return bytes(profile)


# --- split --------------------------------------------------------------------------------------


def test_split_cuts_along_the_clear_lines_and_the_cores_cover_the_figure(tmp_path):
    # The core of a tile is its share of the figure: the cores lie side by side, with the cuts between them.
    _, result = split(tmp_path)

    cores = [tuple(tile["core"]) for tile in result["tiles"]]
    assert len(cores) == 4
    (left, top, right, bottom) = cores[0]
    assert (left, top) == (0, 0)
    assert GAP_X[0] + 4 < right < GAP_X[1] - 4 and GAP_Y[0] + 4 < bottom < GAP_Y[1] - 4  # a few pixels clear of the cards
    assert cores[1] == (right, 0, SIZE[0], bottom)
    assert cores[2][:2] == (0, bottom) and cores[2][3] == SIZE[1] and GAP_X[0] < cores[2][2] < GAP_X[1]
    assert cores[3] == (cores[2][2], bottom, *SIZE)


def test_every_tile_is_a_window_of_one_size_that_reaches_past_the_cuts_of_its_core(tmp_path):
    # One size, so that the image tool redraws every tile at one scale: it draws the lines of a
    # smaller tile heavier. Past each cut, so that neighbours overlap where they are joined.
    folder, result = split(tmp_path)

    boxes, cores = ([tuple(tile[key]) for tile in result["tiles"]] for key in ("box", "core"))
    assert len({(right - left, bottom - top) for left, top, right, bottom in boxes}) == 1
    for (left, top, right, bottom), core in zip(boxes, cores):
        assert 0 <= left and 0 <= top and right <= SIZE[0] and bottom <= SIZE[1]
        assert left <= max(core[0] - 12, 0) and top <= max(core[1] - 12, 0)
        assert right >= min(core[2] + 12, SIZE[0]) and bottom >= min(core[3] + 12, SIZE[1])
    assert boxes[0] == (0, 0, cores[0][2] + 12, cores[2][3] - cores[2][1] + 12)  # no larger than the largest core needs
    source = Image.open(tmp_path / "fig.png")
    for tile in result["tiles"]:
        assert difference(Image.open(folder / tile["file"]), source.crop(tile["box"])) == 0


def test_a_cut_keeps_its_distance_from_what_lies_beside_it(tmp_path):
    # Neighbouring redraws pass into each other over 12 px on each side of a cut: that stretch
    # is clear when the cut lies 12 px inside the clear band and not at its rim.
    _, result = split(tmp_path)

    _, _, right, bottom = result["tiles"][0]["core"]
    assert GAP_X[0] + 12 <= right <= GAP_X[1] - 12
    assert GAP_Y[0] + 12 <= bottom <= GAP_Y[1] - 12
    assert GAP_X[0] + 12 <= result["tiles"][2]["core"][2] <= GAP_X[1] - 12


def test_in_a_narrow_clear_band_a_cut_lies_in_the_middle(tmp_path):
    image = Image.new("RGB", SIZE, "white")
    draw = ImageDraw.Draw(image)
    for left, right in ((40, 590), (606, 1160)):  # 16 px between the columns
        for top, bottom in ((40, 342), (358, 660)):  # 16 px between the rows
            draw.rounded_rectangle((left, top, right, bottom), radius=14, fill=TINT, outline=BLUE, width=2)
            for row in range(5):
                draw.text((left + 24, top + 24 + 40 * row), f"Step {row + 1}: measure and compare", fill=DARK, font_size=26)
    image.save(tmp_path / "fig.png")

    result = report("split", "fig.png", cwd=tmp_path)

    _, _, right, bottom = result["tiles"][0]["core"]
    assert right == pytest.approx(598, abs=2) and bottom == pytest.approx(350, abs=2)


def test_split_names_the_tiles_and_the_files_their_redraws_go_to(tmp_path):
    folder, result = split(tmp_path)

    assert list(result) == ["input", "size", "folder", "tiles"]
    assert result["size"] == list(SIZE) and Path(result["folder"]) == folder
    assert [list(tile) for tile in result["tiles"]] == [["file", "redraw", "box", "core"]] * 4
    assert [(tile["file"], tile["redraw"]) for tile in result["tiles"]] == [
        (f"tile-{n}.png", f"redraw-{n}.png") for n in (1, 2, 3, 4)
    ]
    assert sorted(path.name for path in folder.iterdir()) == ["tile-1.png", "tile-2.png", "tile-3.png", "tile-4.png", "tiles.json"]


def test_split_prints_one_line_per_tile(tmp_path):
    figure(tmp_path / "fig.png")

    proc = run("split", "fig.png", cwd=tmp_path)

    assert proc.returncode == 0, proc.stderr
    lines = proc.stdout.splitlines()
    left, top, right, bottom = json.loads((tmp_path / "fig.tiles" / "tiles.json").read_text())["tiles"][0]["box"]
    assert lines[0] == "wrote 4 tiles to fig.tiles"
    assert lines[1:] == [
        f"tile-{n}.png  {right - left} x {bottom - top} px, redraw it as redraw-{n}.png" for n in (1, 2, 3, 4)
    ]


def test_tiles_can_be_asked_for_by_columns_and_rows(tmp_path):
    _, result = split(tmp_path, "--tiles", "3x1")

    cores = [tile["core"] for tile in result["tiles"]]
    assert len(cores) == 3
    assert all(core[1] == 0 and core[3] == SIZE[1] for core in cores)
    assert cores[0][0] == 0 and cores[0][2] == cores[1][0] and cores[1][2] == cores[2][0] and cores[2][2] == SIZE[0]
    assert len({(box[2] - box[0], box[3] - box[1]) for box in (tile["box"] for tile in result["tiles"])}) == 1


@pytest.mark.parametrize("size, tiles", [((1672, 941), 4), ((2172, 724), 3), ((724, 2172), 3)])
def test_a_long_figure_is_cut_into_three_tiles_in_a_row(tmp_path, size, tiles):
    # An image tool takes pictures up to 3:1: a 3:1 strip in four tiles would give it tiles of that shape.
    _, result = split(tmp_path, size=size)

    assert len(result["tiles"]) == tiles
    for left, top, right, bottom in (tile["box"] for tile in result["tiles"]):
        assert max((right - left) / (bottom - top), (bottom - top) / (right - left)) <= 2.9


def test_more_tiles_are_smaller_tiles(tmp_path):
    # Clear lines at 850 and 950 of 1800 px: cut there, three tiles would be as wide as two,
    # and the third redraw would buy nothing. No part gets more than a third longer than its even share.
    image = Image.new("RGB", (1800, 600), "white")
    draw = ImageDraw.Draw(image)
    for left, right in ((20, 840), (860, 940), (960, 1780)):
        draw.rounded_rectangle((left, 20, right, 580), radius=14, fill=TINT, outline=BLUE, width=2)
        for row in range(12 if right - left > 300 else 0):
            draw.text((left + 24, 44 + 40 * row), f"Step {row + 1}: measure and compare", fill=DARK, font_size=26)
    image.save(tmp_path / "fig.png")

    result = report("split", "fig.png", "--tiles", "3x1", cwd=tmp_path)

    widths = [core[2] - core[0] for core in (tile["core"] for tile in result["tiles"])]
    assert sum(widths) == 1800 and max(widths) <= 1.34 * 600 + 1


def test_a_clear_line_is_not_taken_when_it_makes_the_tiles_too_long(tmp_path):
    # A banner whose only clear line lies at two thirds of its width: tiles as wide as the larger
    # part would be more than three times as wide as high, which an image tool does not take.
    image = Image.new("RGB", (2400, 500), "white")
    draw = ImageDraw.Draw(image)
    for left, right in ((20, 1540), (1580, 2380)):
        draw.rounded_rectangle((left, 20, right, 480), radius=14, fill=TINT, outline=BLUE, width=2)
        for row in range(10):
            draw.text((left + 24, 44 + 40 * row), f"Step {row + 1}: measure and compare", fill=DARK, font_size=26)
    image.save(tmp_path / "fig.png")

    result = report("split", "fig.png", "--tiles", "2x1", cwd=tmp_path)

    left, top, right, bottom = result["tiles"][0]["box"]
    assert (right - left) / (bottom - top) <= 2.9
    assert result["tiles"][0]["core"][2] < 1540


def test_split_does_not_write_into_a_folder_that_holds_something(tmp_path):
    folder, _ = split(tmp_path)

    proc = run("split", "fig.png", cwd=tmp_path)

    assert proc.returncode != 0
    assert proc.stderr.strip() == f"enlarge: {folder.name} already holds files: remove it or name another folder with -o"


@pytest.mark.parametrize("mode, name", [("I;16", "fig.png"), ("I;16", "fig.tif"), ("I;16B", "fig.tif")])
def test_a_16_bit_greyscale_figure_keeps_its_tones(tmp_path, mode, name):
    # Pillow's own conversion clips every 16-bit value above 255 to white.
    ramp = np.tile(np.linspace(0, 65535, SIZE[0]).astype(np.uint16), (SIZE[1], 1))
    Image.fromarray(ramp.astype(">u2") if mode == "I;16B" else ramp).save(tmp_path / name)
    assert Image.open(tmp_path / name).mode == mode

    result = report("split", name, cwd=tmp_path)

    left, _, right, _ = result["tiles"][0]["box"]
    tile = np.asarray(Image.open(tmp_path / "fig.tiles" / "tile-1.png").convert("L"), dtype=int)
    assert tile[0] == pytest.approx(ramp[0, left:right] >> 8, abs=1)


# --- join ---------------------------------------------------------------------------------------


def test_join_puts_the_redraws_together_at_their_size(tmp_path):
    folder, result = split(tmp_path)
    for tile in result["tiles"]:
        redraw(folder, tile)

    joined = report("join", folder, cwd=tmp_path)

    assert list(joined) == ["input", "output", "size", "scale", "redrawn", "tiles"]
    assert Path(joined["output"]) == tmp_path / "fig-enlarged.png"
    assert joined["size"] == [2400, 1400] and joined["scale"] == 2 and joined["redrawn"] == 4
    for tile in joined["tiles"]:
        assert list(tile) == ["file", "redraw", "status", "shift", "match", "reason"]
        assert tile["status"] == "redrawn" and tile["shift"] == [0, 0] and tile["match"] > 0.95 and tile["reason"] is None
    output = Image.open(joined["output"])
    assert output.size == (2400, 1400)
    assert difference(output, enlarged(tmp_path / "fig.png", 2)) < 1


def test_join_prints_one_line_per_tile_then_the_file(tmp_path):
    folder, result = split(tmp_path)
    for tile in result["tiles"][:3]:
        redraw(folder, tile)

    proc = run("join", "fig.tiles", cwd=tmp_path)

    assert proc.returncode == 0, proc.stderr
    lines = proc.stdout.splitlines()
    assert len(lines) == 6
    assert all(line.startswith(f"redrawn  tile-{n}.png  ") for n, line in enumerate(lines[:3], start=1))
    assert lines[3] == "plain    tile-4.png  redraw-4.png is missing: enlarged without new detail"
    assert lines[4] == "wrote fig-enlarged.png"
    assert lines[5] == "png, 2400 x 1400 px, 2 times the original; 3 of 4 tiles redrawn"


def test_split_and_join_print_through_a_pipe_whose_code_page_lacks_the_name_of_the_figure(tmp_path):
    # On Windows a pipe takes the ANSI code page, cp1252 in the West, which has no Chinese.
    figure(tmp_path / "流程图.png")

    def piped(*args):
        proc = subprocess.run(
            [UV, "run", "--quiet", str(SCRIPT), *args], cwd=tmp_path, capture_output=True,
            env={**os.environ, "PYTHONIOENCODING": "cp1252"},
        )
        assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
        return proc.stdout.decode("utf-8").splitlines()

    assert piped("split", "流程图.png")[0] == "wrote 4 tiles to 流程图.tiles"
    for tile in json.loads((tmp_path / "流程图.tiles" / "tiles.json").read_text(encoding="utf-8"))["tiles"]:
        redraw(tmp_path / "流程图.tiles", tile)
    assert piped("join", "流程图.tiles")[-2] == "wrote 流程图-enlarged.png"


def test_the_tiles_come_together_at_the_scale_of_the_smallest_redraw(tmp_path):
    folder, result = split(tmp_path)
    for tile, factor in zip(result["tiles"], (2.0, 1.5, 2.4, 2.0)):
        redraw(folder, tile, factor)

    joined = report("join", folder, cwd=tmp_path)

    assert joined["scale"] == pytest.approx(1.5, abs=0.005) and joined["redrawn"] == 4
    assert joined["size"] == [pytest.approx(1800, abs=3), pytest.approx(1050, abs=3)]
    plain = Image.open(tmp_path / "fig.png").convert("RGB").resize(joined["size"], Image.Resampling.LANCZOS)
    assert difference(Image.open(joined["output"]), plain) < 1.5


def test_a_redraw_that_sits_two_pixels_off_is_laid_back_over_its_tile(tmp_path):
    folder, result = split(tmp_path)
    for index, tile in enumerate(result["tiles"]):
        moved = (lambda image: Image.fromarray(np.roll(np.asarray(image), (3, -2), axis=(0, 1)))) if index == 1 else None
        redraw(folder, tile, change=moved)

    joined = report("join", folder, cwd=tmp_path)

    assert joined["tiles"][1]["status"] == "redrawn" and joined["tiles"][1]["shift"] == [2, -3]
    assert joined["tiles"][0]["shift"] == [0, 0]
    assert difference(Image.open(joined["output"]), enlarged(tmp_path / "fig.png", 2)) < 1


def test_a_redraw_that_does_not_show_its_tile_is_left_out(tmp_path):
    folder, result = split(tmp_path)
    for tile in result["tiles"]:
        redraw(folder, tile)
    wrong = Image.open(folder / "redraw-4.png").resize(Image.open(folder / "redraw-1.png").size)
    wrong.save(folder / "redraw-1.png")  # the picture of another tile, in the right shape

    joined = report("join", folder, cwd=tmp_path)

    first = joined["tiles"][0]
    assert first["status"] == "plain" and first["match"] < 0.8
    assert first["reason"] == f"redraw-1.png does not match it (match {first['match']:.2f})"
    assert joined["redrawn"] == 3
    box = scaled(result["tiles"][0]["core"], 2)
    assert difference(Image.open(joined["output"]), enlarged(tmp_path / "fig.png", 2), box) < 1


def test_content_that_moved_far_is_a_mismatch(tmp_path):
    folder, result = split(tmp_path)
    for index, tile in enumerate(result["tiles"]):
        moved = (lambda image: Image.fromarray(np.roll(np.asarray(image), 24, axis=1))) if index == 2 else None
        redraw(folder, tile, change=moved)

    joined = report("join", folder, cwd=tmp_path)

    assert [tile["status"] for tile in joined["tiles"]] == ["redrawn", "redrawn", "plain", "redrawn"]


def test_something_drawn_into_an_empty_part_of_a_tile_is_a_mismatch(tmp_path):
    folder, result = split(tmp_path)

    def added(image):
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((60, 20, 500, 76), radius=10, outline=BLUE, width=4)  # in the white margin above the card
        draw.text((80, 30), "Something the tool made up", fill=DARK, font_size=30)
        return image

    for index, tile in enumerate(result["tiles"]):
        redraw(folder, tile, change=added if index == 0 else None)

    joined = report("join", folder, cwd=tmp_path)

    assert joined["tiles"][0]["status"] == "plain"
    assert [tile["status"] for tile in joined["tiles"][1:]] == ["redrawn"] * 3


def test_something_drawn_where_the_tile_is_empty_is_a_mismatch(tmp_path):
    # A figure whose left half is white: the tiles there hold nothing, so nothing may appear in their redraws.
    image = Image.open(figure(tmp_path / "fig.png"))
    ImageDraw.Draw(image).rectangle((0, 0, GAP_X[0] + 20, SIZE[1]), fill="white")
    image.save(tmp_path / "fig.png")
    result = report("split", "fig.png", cwd=tmp_path)
    folder = tmp_path / "fig.tiles"

    def added(picture):
        ImageDraw.Draw(picture).rounded_rectangle((300, 200, 700, 330), radius=12, fill=TINT, outline=BLUE, width=4)
        return picture

    for index, tile in enumerate(result["tiles"]):
        redraw(folder, tile, change=added if index == 0 else None)

    joined = report("join", folder, cwd=tmp_path)

    assert joined["tiles"][0]["status"] == "plain"
    assert joined["tiles"][2]["status"] == "redrawn" and joined["tiles"][2]["shift"] == [0, 0]  # empty, and left where it is


@pytest.mark.parametrize("moved, status", [(3, "redrawn"), (10, "plain")])
def test_a_fine_line_that_sits_a_pixel_off_is_no_mismatch(tmp_path, moved, status):
    # A connector through an empty stretch of the first tile: the card beside it holds the tile in place,
    # and in the redraw the line alone sits `moved` px lower (1.5 and 5 px of the tile).
    image = Image.open(figure(tmp_path / "fig.png"))
    draw = ImageDraw.Draw(image)
    draw.rectangle((340, 0, GAP_X[0] + 20, GAP_Y[0] + 20), fill="white")
    draw.rounded_rectangle((40, 40, 330, GAP_Y[0]), radius=14, outline=BLUE, width=2)
    draw.line((370, 165, 610, 165), fill=DARK, width=1)
    image.save(tmp_path / "fig.png")
    result = report("split", "fig.png", cwd=tmp_path)
    folder = tmp_path / "fig.tiles"

    def lowered(picture):
        pixels = np.asarray(picture).copy()
        pixels[2 * 140 : 2 * 190, 2 * 350 : 2 * 625] = np.roll(pixels[2 * 140 : 2 * 190, 2 * 350 : 2 * 625], moved, axis=0)
        return Image.fromarray(pixels)

    for index, tile in enumerate(result["tiles"]):
        redraw(folder, tile, change=lowered if index == 0 else None)

    joined = report("join", folder, cwd=tmp_path)

    assert joined["tiles"][0]["shift"] == [0, 0]
    assert joined["tiles"][0]["status"] == status


def connected(path):
    """The figure with a connector from each upper card down to the card below it, across the cut between the rows."""
    image = Image.open(figure(path))
    draw = ImageDraw.Draw(image)
    for x in (200, 900):
        draw.line((x, GAP_Y[0], x, GAP_Y[1]), fill=DARK, width=2)
    image.save(path)
    return path


def test_a_cut_runs_through_open_space_rather_than_through_a_box(tmp_path):
    # Two connectors cross the band between the rows, and a cut through the tops of the lower cards
    # would cross little more and lie nearer the middle: it would leave a sliver of each card in the
    # tile above, whose redraw then draws the sliver in its own way.
    connected(tmp_path / "fig.png")

    result = report("split", "fig.png", cwd=tmp_path)

    for tile in result["tiles"][:2]:
        assert GAP_Y[0] + 12 <= tile["core"][3] <= GAP_Y[1] - 12


@pytest.mark.parametrize("colour", [DARK, "black"])
def test_a_line_across_open_space_does_not_send_the_cut_into_a_box(tmp_path, colour):
    # A connector across the gap between the upper cards costs that gap a little. A cut through the empty right
    # part of the left card would cross the card's two faint outlines instead, together little more than one dark
    # line, and leave a sliver of the card in the tile beside it.
    image = Image.open(connected(tmp_path / "fig.png"))
    ImageDraw.Draw(image).line((GAP_X[0], 165, GAP_X[1], 165), fill=colour, width=2)
    image.save(tmp_path / "fig.png")

    result = report("split", "fig.png", cwd=tmp_path)

    for tile in (result["tiles"][0], result["tiles"][2]):
        assert GAP_X[0] + 12 <= tile["core"][2] <= GAP_X[1] - 12


def tall_gap(path, width=2):
    """Two rows of cards 170 px apart, each upper card joined to the one below it by a line of the given width."""
    image = Image.new("RGB", SIZE, "white")
    draw = ImageDraw.Draw(image)
    for left, right in ((40, GAP_X[0]), (GAP_X[1], SIZE[0] - 40)):
        for top, bottom in ((40, 260), (430, 660)):
            draw.rounded_rectangle((left, top, right, bottom), radius=14, fill=TINT, outline=BLUE, width=2)
            for row in range(4):
                draw.text((left + 24, top + 24 + 40 * row), f"Step {row + 1}: measure and compare", fill=DARK, font_size=26)
        draw.line(((left + right) // 2, 260, (left + right) // 2, 430), fill=DARK, width=width)
    image.save(path)
    return path


def ink(output, x, rows):
    """How much ink the vertical line at x holds in each of the rows of the enlarged figure."""
    return (255 - np.asarray(output.convert("L"), dtype=float))[rows, 2 * x - 14 : 2 * x + 14].sum(axis=1)


def test_a_line_drawn_heavier_in_one_redraw_passes_into_the_other_without_a_step(tmp_path):
    # The image tool does not draw a line with one weight in every tile. Here the lines that cross
    # the cut between the rows come back half as heavy again in the upper tiles as in the lower ones.
    tall_gap(tmp_path / "fig.png")
    heavy = Image.open(tall_gap(tmp_path / "heavy.png", width=3))
    result = report("split", "fig.png", cwd=tmp_path)
    folder = tmp_path / "fig.tiles"
    for index, tile in enumerate(result["tiles"]):
        if index < 2:
            part = heavy.crop(tile["box"])
            part.resize((2 * part.width, 2 * part.height), Image.Resampling.LANCZOS).save(folder / tile["redraw"])
        else:
            redraw(folder, tile)

    joined = report("join", folder, cwd=tmp_path)

    assert [tile["status"] for tile in joined["tiles"]] == ["redrawn"] * 4
    along = ink(Image.open(joined["output"]), 335, slice(2 * 265, 2 * 425))
    above, below = along[:100].mean(), along[-100:].mean()
    assert above > 1.3 * below  # each side keeps the weight of its own redraw
    assert np.abs(np.diff(along)).max() < 0.1 * (above - below)  # and between them the weight changes little by little


def test_text_that_a_cut_runs_through_comes_from_one_redraw_on_each_side(tmp_path):
    # Two redraws never draw a letter alike: passed into each other, the letters would show twice.
    image = Image.new("RGB", SIZE, "white")
    draw = ImageDraw.Draw(image)
    for top, bottom in ((40, GAP_Y[0]), (GAP_Y[1], SIZE[1] - 40)):  # cards as wide as the figure: no clear line to cut along
        draw.rounded_rectangle((40, top, SIZE[0] - 40, bottom), radius=14, fill=TINT, outline=BLUE, width=2)
        for row in range(5):
            sentence = "Collect the samples, measure them twice and compare the two series of results with care"
            draw.text((70, top + 24 + 40 * row), sentence, fill=DARK, font_size=26)
    image.save(tmp_path / "fig.png")
    result = report("split", "fig.png", cwd=tmp_path)
    folder = tmp_path / "fig.tiles"
    cut = result["tiles"][0]["core"][2]

    def letters_in_blue(tile):
        first = 2 * (cut - 12 - tile["box"][0])  # where the 24 px begin in which this tile and its neighbour overlap

        def change(picture):
            pixels = np.asarray(picture).copy()
            strip = pixels[:, first : first + 48]
            strip[strip[..., 0] < 128] = (0, 0, 200)
            return Image.fromarray(pixels)

        return change

    for index, tile in enumerate(result["tiles"]):
        redraw(folder, tile, change=letters_in_blue(tile) if index == 1 else None)

    joined = report("join", folder, cwd=tmp_path)

    assert [tile["status"] for tile in joined["tiles"]] == ["redrawn"] * 4
    output = np.asarray(Image.open(joined["output"]).convert("RGB"), dtype=int)[2 * 50 : 2 * 280]  # the rows of the upper card
    blue = output[..., 2] - output[..., 0] > 60
    assert not blue[:, 2 * (cut - 12) : 2 * cut - 2].any()  # left of the cut: the letters of the left redraw alone
    letters = output[:, 2 * cut + 2 : 2 * (cut + 12), 0] < 100
    assert letters.sum() > 200 and blue[:, 2 * cut + 2 : 2 * (cut + 12)][letters].mean() > 0.9  # right of it: of the right one


def test_what_a_redraw_shows_beyond_its_share_of_the_figure_does_not_matter(tmp_path):
    # A tile is larger than its share: what the image tool does to the rest is the business of the neighbour.
    folder, result = split(tmp_path)
    first = result["tiles"][0]
    assert first["box"][3] - first["core"][3] > 40  # the first tile shows more than 40 px of the cards below its own

    def spoiled(picture):
        ImageDraw.Draw(picture).rectangle((2 * 100, 2 * (first["core"][3] + 24), 2 * 300, 2 * first["box"][3]), fill=DARK)
        return picture

    for index, tile in enumerate(result["tiles"]):
        redraw(folder, tile, change=spoiled if index == 0 else None)

    joined = report("join", folder, cwd=tmp_path)

    assert joined["tiles"][0]["status"] == "redrawn" and joined["tiles"][0]["match"] > 0.95
    assert difference(Image.open(joined["output"]), enlarged(tmp_path / "fig.png", 2)) < 1


def test_a_line_whose_first_pixels_are_missing_at_the_edge_of_a_tile_is_whole(tmp_path):
    # What an image tool does to a line that enters a tile: it drops its first pixels. The neighbour,
    # which reaches 12 px past the cut, has them.
    tall_gap(tmp_path / "fig.png")
    result = report("split", "fig.png", cwd=tmp_path)
    folder, lower = tmp_path / "fig.tiles", result["tiles"][2]
    assert lower["box"][1] == lower["core"][1] - 12  # the lower tile begins 12 px above the cut

    def shortened(picture):
        ImageDraw.Draw(picture).rectangle((2 * 335 - 12, 0, 2 * 335 + 12, 2 * 8), fill="white")
        return picture

    for index, tile in enumerate(result["tiles"]):
        redraw(folder, tile, change=shortened if index == 2 else None)

    joined = report("join", folder, cwd=tmp_path)

    assert joined["tiles"][2]["status"] == "redrawn"
    along = ink(Image.open(joined["output"]), 335, slice(2 * 265, 2 * 425))
    assert along.min() > 0.6 * np.median(along)


def test_a_redraw_in_another_shape_is_left_out(tmp_path):
    folder, result = split(tmp_path)
    for tile in result["tiles"]:
        redraw(folder, tile)
    square = Image.open(folder / "redraw-2.png").resize((1024, 1024))
    square.save(folder / "redraw-2.png")

    joined = report("join", folder, cwd=tmp_path)

    second = joined["tiles"][1]
    assert second["status"] == "plain" and second["reason"] == "redraw-2.png came back in another shape (1024 x 1024 px)"


def test_a_redraw_that_is_no_larger_than_its_tile_is_left_out(tmp_path):
    folder, result = split(tmp_path)
    for index, tile in enumerate(result["tiles"]):
        redraw(folder, tile, factor=1.0 if index == 3 else 2.0)

    joined = report("join", folder, cwd=tmp_path)

    assert joined["scale"] == 2
    assert joined["tiles"][3]["status"] == "plain" and joined["tiles"][3]["reason"] == "redraw-4.png came back no larger"


@pytest.mark.parametrize(
    "damage, reason",
    [
        ("empty", "redraw-2.png is empty"),
        ("text", "redraw-2.png is not a picture"),
        ("cut short", "redraw-2.png cannot be read (image file is truncated)"),
    ],
)
def test_a_redraw_that_cannot_be_read_is_left_out(tmp_path, damage, reason):
    # What a save that failed, an answer saved as the picture or a copy cut off leaves: the other tiles still join.
    folder, result = split(tmp_path)
    for tile in result["tiles"]:
        redraw(folder, tile)
    data = (folder / "redraw-2.png").read_bytes()
    damaged = {"empty": b"", "text": b"Too many requests", "cut short": data[: len(data) // 2]}
    (folder / "redraw-2.png").write_bytes(damaged[damage])

    joined = report("join", folder, cwd=tmp_path)

    assert [tile["status"] for tile in joined["tiles"]] == ["redrawn", "plain", "redrawn", "redrawn"]
    assert joined["tiles"][1]["reason"].startswith(reason)  # Pillow may say how many bytes it could not read
    assert Image.open(joined["output"]).size == (2400, 1400)


def test_the_flat_colours_come_from_the_original_and_the_detail_from_the_redraw(tmp_path):
    folder, result = split(tmp_path)

    def tinted_and_crisp(tile):
        # What a redraw looks like: hard edges, and fills a shade off the original's.
        image = Image.open(folder / tile["file"]).convert("RGB")
        image = image.resize((2 * image.width, 2 * image.height), Image.Resampling.NEAREST)
        pixels = np.asarray(image).astype(int)
        pixels[..., 0] = np.where(pixels[..., 0] > 200, pixels[..., 0] - 12, pixels[..., 0])
        Image.fromarray(pixels.astype(np.uint8)).save(folder / tile["redraw"])

    for tile in result["tiles"]:
        tinted_and_crisp(tile)

    joined = report("join", folder, cwd=tmp_path)

    output, plain = Image.open(joined["output"]).convert("RGB"), enlarged(tmp_path / "fig.png", 2)
    crisp = enlarged(tmp_path / "fig.png", 2, Image.Resampling.NEAREST)  # the redraws without their cast
    assert joined["redrawn"] == 4
    inside_a_card = (2 * 300, 2 * 250, 2 * 420, 2 * 280)  # flat tint, clear of text and outline
    assert difference(output, plain, inside_a_card) < 2  # the cast of the redraw is gone
    text_and_outline = (2 * 30, 2 * 50, 2 * 400, 2 * 250)
    assert difference(output, crisp, text_and_outline) < 0.5 * difference(plain, crisp, text_and_outline)  # its edges are kept


def test_the_output_can_be_named(tmp_path):
    folder, result = split(tmp_path)
    for tile in result["tiles"]:
        redraw(folder, tile)

    joined = report("join", folder, "-o", "large/figure.png", cwd=tmp_path)

    assert joined["output"] == "large/figure.png"
    assert Image.open(tmp_path / "large" / "figure.png").size == (2400, 1400)
    assert not (tmp_path / "fig-enlarged.png").exists()


def test_the_tiles_and_the_enlarged_figure_keep_the_colour_profile_of_the_figure(tmp_path):
    # Without it, viewers take the colours of a Display P3 figure for sRGB ones. The image tool redraws a tile as a
    # copy of its values and returns it without the profile: the enlarged figure is in the colours of the figure.
    profile = display_p3()
    source = figure(tmp_path / "fig.png")
    Image.open(source).save(source, icc_profile=profile)
    result = report("split", "fig.png", cwd=tmp_path)
    folder = tmp_path / "fig.tiles"
    for tile in result["tiles"]:
        assert Image.open(folder / tile["file"]).info.get("icc_profile") == profile
        redraw(folder, tile, change=lambda image: Image.fromarray(np.asarray(image)))

    joined = report("join", folder, cwd=tmp_path)

    assert "icc_profile" not in Image.open(folder / "redraw-1.png").info
    assert Image.open(joined["output"]).info.get("icc_profile") == profile


def test_the_profile_of_a_greyscale_figure_stays_behind(tmp_path):
    # The tiles are RGB, so no profile of a greyscale figure describes them: as in export_figure.py, a profile
    # goes along only while the colour model stays.
    source = figure(tmp_path / "fig.png")
    Image.open(source).convert("L").save(source, icc_profile=display_p3())

    result = report("split", "fig.png", cwd=tmp_path)

    assert ["icc_profile" in Image.open(tmp_path / "fig.tiles" / tile["file"]).info for tile in result["tiles"]] == [False] * 4


# --- errors -------------------------------------------------------------------------------------


def test_join_without_any_usable_redraw_is_an_error(tmp_path):
    folder, _ = split(tmp_path)

    proc = run("join", folder, cwd=tmp_path)

    assert proc.returncode != 0
    assert proc.stderr.strip() == "enlarge: no tile has a redraw that can be used: nothing to join"
    assert not (tmp_path / "fig-enlarged.png").exists()


def test_join_on_a_folder_that_split_did_not_make_is_an_error(tmp_path):
    (tmp_path / "empty").mkdir()

    proc = run("join", "empty", cwd=tmp_path)

    assert proc.returncode != 0
    assert proc.stderr.strip() == "enlarge: empty holds no tiles.json: run split first"


def test_a_missing_figure_fails_with_one_line_on_stderr(tmp_path):
    proc = run("split", "nothing.png", cwd=tmp_path)

    assert proc.returncode != 0
    assert proc.stdout == ""
    assert len(proc.stderr.strip().splitlines()) == 1 and proc.stderr.startswith("enlarge: ")


@pytest.mark.parametrize("mode, values", [("F", np.linspace(0, 1, SIZE[0])), ("I", np.linspace(0, 65535, SIZE[0]))])
def test_a_32_bit_figure_is_refused_as_export_figure_refuses_it(tmp_path, mode, values):
    # Floats or 32-bit integers say nothing of which value is white: Pillow made a float figure black.
    Image.fromarray(np.tile(values, (SIZE[1], 1)).astype(np.float32 if mode == "F" else np.int32)).save(tmp_path / "fig.tif")
    assert Image.open(tmp_path / "fig.tif").mode == mode

    proc = run("split", "fig.tif", cwd=tmp_path)

    assert proc.returncode == 1
    assert proc.stderr.strip() == (
        f"enlarge: cannot reduce a 32-bit {mode} image to 8-bit without its display range; save an 8-bit copy first"
    )
    assert not (tmp_path / "fig.tiles").exists()


@pytest.mark.parametrize("tiles", ["1x1", "5x1", "2by2", "0x2"])
def test_tiles_must_be_a_grid_of_two_to_sixteen(tmp_path, tiles):
    figure(tmp_path / "fig.png")

    proc = run("split", "fig.png", "--tiles", tiles, cwd=tmp_path)

    assert proc.returncode == 2
    assert "--tiles" in proc.stderr


def test_the_script_leaves_nothing_beside_itself(tmp_path):
    before = sorted(path.name for path in SCRIPT.parent.iterdir())
    folder, result = split(tmp_path)
    for tile in result["tiles"]:
        redraw(folder, tile)
    report("join", folder, cwd=tmp_path)

    assert sorted(path.name for path in SCRIPT.parent.iterdir()) == before
