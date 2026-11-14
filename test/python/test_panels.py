"""Tests for skills/scifig/scripts/panels.py, run as a CLI through uv."""
import json
import os
import re
import struct
import subprocess
import sys
from itertools import groupby
from pathlib import Path

import pytest
from PIL import Image, ImageCms

SCRIPTS = Path(__file__).resolve().parents[2] / "skills" / "scifig" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import journals  # noqa: E402

SCRIPT = SCRIPTS / "panels.py"
UV = os.environ.get("UV", "uv")
RED, GREEN, BLUE, WHITE = (213, 94, 0), (0, 158, 115), (0, 114, 178), (255, 255, 255)
REPORT_KEYS = ["output", "format", "pixels", "dpi", "size_mm", "panels", "notes"]
P3_PRIMARIES = {b"rXYZ": (0.5151, 0.2412, -0.0011), b"gXYZ": (0.2920, 0.6922, 0.0419), b"bXYZ": (0.1571, 0.0666, 0.7841)}


def run(*args, cwd):
    return subprocess.run([UV, "run", "--quiet", str(SCRIPT), *map(str, args)], cwd=cwd, capture_output=True, text=True)


def compose(*args, cwd):
    """Run with --json, expect success and return the parsed report."""
    proc = run(*args, "--json", cwd=cwd)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def solid(path, size, colour, mode="RGB"):
    Image.new(mode, size, colour).save(path)
    return path


def runs(image, y):
    """[(colour, first x, last x)] of the runs of equal colour along row y."""
    row = [image.getpixel((x, y)) for x in range(image.width)]
    out, x = [], 0
    for colour, group in groupby(row):
        n = len(list(group))
        out.append((colour, x, x + n - 1))
        x += n
    return out


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


@pytest.fixture
def two(tmp_path):
    """A 4:3 red panel and a square green one."""
    return [solid(tmp_path / "a.png", (800, 600), RED), solid(tmp_path / "b.png", (600, 600), GREEN)]


# --- layout -------------------------------------------------------------------------------------


def test_one_row_fills_the_column_width_and_keeps_every_aspect_ratio(two, tmp_path):
    report = compose(*two, "-f", "png", "--journal", "nature", "--column", "double", "--dpi", 300, "--no-labels", cwd=tmp_path)

    width = journals.pixels_for(180, 300)  # Nature's double column
    assert list(report) == REPORT_KEYS
    assert report["pixels"][0] == width
    with Image.open(report["output"]) as out:
        assert out.size == tuple(report["pixels"])
        assert out.mode == "RGB"
        (red, r0, r1), (white, g0, g1), (green, b0, b1) = runs(out, out.height // 2)
        assert (red, white, green) == (RED, WHITE, GREEN)
        assert r0 == 0 and b1 == width - 1  # the row spans the whole width
        assert g1 - g0 + 1 == pytest.approx(3 / 25.4 * 300, abs=1)  # the default 3 mm gap
        assert (r1 - r0 + 1) / out.height == pytest.approx(800 / 600, rel=0.01)
        assert (b1 - b0 + 1) / out.height == pytest.approx(600 / 600, rel=0.01)
        # Without labels the panels reach the top and the bottom edge.
        assert out.getpixel((5, 0)) == RED and out.getpixel((5, out.height - 1)) == RED


def test_rows_stack_with_the_gap_between_them(two, tmp_path):
    wide = solid(tmp_path / "c.png", (1200, 300), BLUE)

    report = compose(*two, wide, "-f", "png", "--rows", "2,1", "--dpi", 300, "--no-labels", cwd=tmp_path)

    boxes = [panel["box_px"] for panel in report["panels"]]  # x, y, width, height
    width, height = report["pixels"]
    assert boxes[0][1] == boxes[1][1] == 0 and boxes[0][3] == boxes[1][3]  # first row: same top, same height
    assert boxes[2][0] == 0 and boxes[2][2] == width  # the third panel is a row of its own
    gap = boxes[2][1] - boxes[0][3]
    assert gap == pytest.approx(3 / 25.4 * 300, abs=1)
    assert boxes[2][1] + boxes[2][3] == height
    assert boxes[2][2] / boxes[2][3] == pytest.approx(1200 / 300, rel=0.01)
    with Image.open(report["output"]) as out:
        assert out.getpixel((width // 2, boxes[0][3] + gap // 2)) == WHITE
        assert out.getpixel((width // 2, height - 5)) == BLUE


def test_the_gap_can_be_changed(two, tmp_path):
    report = compose(*two, "-f", "png", "--dpi", 300, "--no-labels", "--gap-mm", 10, cwd=tmp_path)

    first, second = (panel["box_px"] for panel in report["panels"])
    assert second[0] - (first[0] + first[2]) == pytest.approx(10 / 25.4 * 300, abs=1)


@pytest.mark.parametrize("options, width_mm", [(["--width-mm", "120"], 120), (["--column", "single", "--journal", "cell"], 85), ([], 178)])
def test_the_width_comes_from_millimetres_a_journal_column_or_the_double_column_default(two, tmp_path, options, width_mm):
    report = compose(*two, "-f", "png", "--dpi", 300, *options, cwd=tmp_path)

    assert report["pixels"][0] == journals.pixels_for(width_mm, 300)
    assert report["size_mm"][0] == pytest.approx(width_mm, abs=0.1)


def test_a_figure_taller_than_the_journal_allows_is_refused(tmp_path):
    tall = [solid(tmp_path / f"{i}.png", (300, 900), RED) for i in range(2)]

    proc = run(*tall, "-f", "png", "--journal", "nature", "--column", "single", "--rows", "1,1", cwd=tmp_path)

    assert proc.returncode == 1
    assert "247" in proc.stderr  # Nature's maximum height in mm
    assert sorted(path.name for path in tmp_path.iterdir()) == ["0.png", "1.png"]


# --- labels -------------------------------------------------------------------------------------


def test_labels_sit_in_a_band_above_each_row(two, tmp_path):
    plain = compose(*two, "-f", "png", "--dpi", 300, "--no-labels", "-o", tmp_path / "plain.png", cwd=tmp_path)
    labelled = compose(*two, "-f", "png", "--dpi", 300, "-o", tmp_path / "labelled.png", cwd=tmp_path)

    band = labelled["pixels"][1] - plain["pixels"][1]
    assert band > 0
    boxes = [panel["box_px"] for panel in labelled["panels"]]
    assert all(box[1] == band for box in boxes)
    with Image.open(labelled["output"]) as out:
        for x, _, width, _ in boxes:
            # The letter is dark ink at the left end of the band above its panel; the rest of the band is white.
            left = out.crop((x, 0, x + 2 * band, band)).convert("L")
            rest = out.crop((x + 3 * band, 0, x + width, band)).convert("L")
            assert left.getextrema()[0] < 80
            assert rest.getextrema()[0] > 250


@pytest.mark.parametrize("journal, expected", [("nature", ["a", "b"]), ("cell", ["A", "B"]), ("wiley", ["a", "b"])])
def test_letters_follow_the_journal(two, tmp_path, journal, expected):
    report = compose(*two, "-f", "png", "--dpi", 300, "--journal", journal, cwd=tmp_path)

    assert [panel["label"] for panel in report["panels"]] == expected


def test_labels_can_be_given(two, tmp_path):
    report = compose(*two, "-f", "png", "--dpi", 300, "--labels", "i,ii", cwd=tmp_path)

    assert [panel["label"] for panel in report["panels"]] == ["i", "ii"]


def test_no_labels_reports_none(two, tmp_path):
    report = compose(*two, "-f", "png", "--dpi", 300, "--no-labels", cwd=tmp_path)

    assert [panel["label"] for panel in report["panels"]] == [None, None]


# --- resolution ---------------------------------------------------------------------------------


def test_each_panel_reports_the_resolution_its_own_pixels_give(two, tmp_path):
    report = compose(*two, "-f", "png", "--dpi", 300, "--no-labels", cwd=tmp_path)

    for panel, source_width in zip(report["panels"], (800, 600)):
        assert panel["file"].endswith((".png",))
        assert panel["effective_dpi"] == pytest.approx(source_width * 300 / panel["box_px"][2], abs=1)
        assert panel["scale"] == pytest.approx(panel["box_px"][2] / source_width, abs=0.001)
        assert panel["upscaled"] is True  # 800 and 600 px are fewer than half of 2103 px needs
    (note,) = [note for note in report["notes"] if "not detail" in note]
    assert re.search(r"a\.png \(1\.\d\dx\), b\.png \(1\.\d\dx\)", note), note  # each with how much it was enlarged


def test_a_panel_resampled_by_under_one_percent_is_not_called_enlarged(tmp_path):
    # Two single-column chart previews (88 mm at 300 dpi) side by side in a double column: a pixel of rounding.
    previews = [solid(tmp_path / f"{name}.png", (1039, 727), RED) for name in "ab"]

    report = compose(*previews, "-f", "tiff", "--journal", "elsevier", "--width-mm", 180, "--gap-mm", 4, "--dpi", 300, "--no-labels", cwd=tmp_path)

    assert [panel["box_px"][2] for panel in report["panels"]] == [1040, 1040]
    assert [panel["upscaled"] for panel in report["panels"]] == [False, False]
    assert report["notes"] == []


def test_panels_with_enough_pixels_are_not_flagged(tmp_path):
    big = [solid(tmp_path / f"{name}.png", (3000, 2000), colour) for name, colour in (("a", RED), ("b", GREEN))]

    report = compose(*big, "-f", "png", "--dpi", 300, cwd=tmp_path)

    assert [panel["upscaled"] for panel in report["panels"]] == [False, False]
    assert report["notes"] == []


# --- formats ------------------------------------------------------------------------------------


def test_tiff_is_lzw_rgb_with_the_resolution_tag(two, tmp_path):
    report = compose(*two, "-f", "tiff", "--dpi", 600, "--journal", "elsevier", cwd=tmp_path)

    assert report["dpi"] == pytest.approx(600, abs=0.2)  # the tag that prints 4489 px at exactly 190 mm
    with Image.open(report["output"]) as out:
        assert out.mode == "RGB"
        assert out.info["compression"] == "tiff_lzw"
        assert out.info["dpi"][0] == pytest.approx(600, abs=0.5)
        assert out.width == journals.pixels_for(190, 600)


def test_pdf_keeps_the_letters_as_text_and_each_panel_as_one_image(two, tmp_path):
    report = compose(*two, "-f", "pdf", "--dpi", 300, "--journal", "nature", cwd=tmp_path)

    data = Path(report["output"]).read_bytes()
    assert data.startswith(b"%PDF")
    assert len(re.findall(rb"/Subtype\s*/Image", data)) == 2
    assert re.search(rb"/Type\s*/Font\b", data)  # the letters are text, set in an embedded font
    box = re.search(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]", data)
    assert float(box[1]) / 72 * 25.4 == pytest.approx(180, abs=0.2)  # Nature's double column


def test_a_format_the_journal_does_not_take_is_noted(tmp_path):
    big = [solid(tmp_path / f"{name}.png", (3000, 2000), RED) for name in "ab"]

    report = compose(*big, "-f", "tiff", "--dpi", 300, "--journal", "nature", cwd=tmp_path)

    assert report["notes"] == [journals.format_problem("nature", "tiff")]


def test_transparency_is_flattened_onto_white(tmp_path):
    clear = solid(tmp_path / "a.png", (600, 600), (255, 0, 0, 0), mode="RGBA")
    opaque = solid(tmp_path / "b.png", (600, 600), GREEN)

    report = compose(clear, opaque, "-f", "png", "--dpi", 300, "--no-labels", cwd=tmp_path)

    with Image.open(report["output"]) as out:
        assert out.getpixel((10, out.height // 2)) == WHITE


def test_a_panel_in_another_colour_space_is_converted_to_srgb(tmp_path):
    # Panels can come in different colour spaces and a figure has one: sRGB, which a file without a profile
    # means. Display P3 (200, 60, 40) is sRGB (217, 42, 23); taken for sRGB, the panel would look duller.
    Image.new("RGB", (600, 600), (200, 60, 40)).save(tmp_path / "a.png", icc_profile=display_p3())
    plain = solid(tmp_path / "b.png", (600, 600), (200, 60, 40))

    report = compose(tmp_path / "a.png", plain, "-f", "png", "--dpi", 300, "--no-labels", cwd=tmp_path)

    with Image.open(report["output"]) as out:
        (converted, _, _), _, (untouched, _, _) = runs(out, out.height // 2)
        assert "icc_profile" not in out.info
    assert converted == pytest.approx((217, 42, 23), abs=1)
    assert untouched == (200, 60, 40)


@pytest.mark.parametrize(
    "profile",
    [b"not an icc profile", ImageCms.ImageCmsProfile(ImageCms.createProfile("LAB")).tobytes()],
    ids=["unreadable", "not for RGB"],
)
def test_a_panel_whose_profile_cannot_be_used_is_taken_as_srgb(tmp_path, profile):
    Image.new("RGB", (600, 600), (200, 60, 40)).save(tmp_path / "a.png", icc_profile=profile)

    report = compose(tmp_path / "a.png", "-f", "png", "--dpi", 300, "--no-labels", cwd=tmp_path)

    with Image.open(report["output"]) as out:
        assert out.getpixel((10, 10)) == (200, 60, 40)


# --- files and errors ---------------------------------------------------------------------------


def test_the_default_output_sits_next_to_the_first_panel(two, tmp_path):
    cwd = tmp_path / "elsewhere"
    cwd.mkdir()

    report = compose(*two, "-f", "png", "--dpi", 300, cwd=cwd)

    assert Path(report["output"]) == tmp_path / "a_panels.png"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["a.png", "a_panels.png", "b.png", "elsewhere"]
    assert list(cwd.iterdir()) == []


def test_it_refuses_to_overwrite_a_panel(two, tmp_path):
    proc = run(*two, "-f", "png", "-o", two[1], cwd=tmp_path)

    assert proc.returncode == 1
    assert "overwrite" in proc.stderr
    with Image.open(two[1]) as untouched:
        assert untouched.size == (600, 600)


def test_a_missing_panel_fails_with_one_line_on_stderr(two, tmp_path):
    proc = run(two[0], tmp_path / "nope.png", "-f", "png", cwd=tmp_path)

    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr.startswith("panels: ") and proc.stderr.count("\n") == 1


@pytest.mark.parametrize(
    "options",
    [
        ["--rows", "1,2"],  # three panels for two files
        ["--rows", "2,x"],
        ["--labels", "a,b,c"],  # three letters for two panels
        ["--labels", "a,b", "--no-labels"],
        ["--width-mm", "100", "--column", "single"],
        ["--gap-mm", "-1"],
    ],
)
def test_usage_errors_exit_2_and_write_nothing(two, tmp_path, options):
    proc = run(*two, "-f", "png", *options, cwd=tmp_path)

    assert proc.returncode == 2, proc.stderr
    assert "usage: panels.py" in proc.stderr
    assert sorted(path.name for path in tmp_path.iterdir()) == ["a.png", "b.png"]


def test_without_json_it_prints_a_readable_summary(two, tmp_path):
    proc = run(*two, "-f", "png", "--dpi", 300, cwd=tmp_path)

    assert proc.returncode == 0, proc.stderr
    assert not proc.stdout.startswith("{")
    for fact in ("a_panels.png", "178.0", "a.png", "b.png", "not detail"):
        assert fact in proc.stdout, fact


def test_the_summary_prints_through_a_pipe_whose_code_page_lacks_its_characters(tmp_path):
    # On Windows a pipe takes the ANSI code page, cp1252 in the West, which has no Chinese.
    panels = [solid(tmp_path / "图甲.png", (800, 600), RED), solid(tmp_path / "图乙.png", (600, 600), GREEN)]

    proc = subprocess.run(
        [UV, "run", "--quiet", str(SCRIPT), *map(str, panels), "-f", "png", "--dpi", "300"], cwd=tmp_path,
        capture_output=True, env={**os.environ, "PYTHONIOENCODING": "cp1252"},
    )

    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
    lines = proc.stdout.decode("utf-8").splitlines()
    assert lines[0] == f"wrote {tmp_path / '图甲_panels.png'}"
    assert lines[2].startswith("panel a  图甲.png  ")


def test_it_writes_nothing_next_to_itself(two, tmp_path):
    def listing():
        return sorted(str(path.relative_to(SCRIPTS)) for path in SCRIPTS.rglob("*"))

    before = listing()
    compose(*two, "-f", "png", "--dpi", 300, cwd=tmp_path)
    assert listing() == before  # no bytecode cache either
