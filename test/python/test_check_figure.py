"""Tests for skills/scifig/scripts/check_figure.py, run as a CLI through uv.

The colour maths is checked against the small textbook implementation below (sRGB D65 to
CIELAB, Machado et al. 2009 matrices on linear RGB), written independently of the script.
"""
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageCms, ImageDraw

os.environ.setdefault("MPLBACKEND", "Agg")  # for the charts drawn below

import matplotlib.pyplot as plt  # noqa: E402

SCRIPTS = Path(__file__).resolve().parents[2] / "skills" / "scifig" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import journals  # noqa: E402
import scistyle  # noqa: E402

SCRIPT = SCRIPTS / "check_figure.py"
UV = os.environ.get("UV", "uv")
REPORT_KEYS = [
    "input", "format", "mode", "pixels", "journal", "journal_note", "kind", "checks", "overall", "fills", "lines", "previews",
]
CHECK_IDS = ["format", "effective_dpi", "transparency", "color_mode", "grayscale", "colorblind"]
PREVIEWS = ["grayscale", "deuteranopia", "protanopia", "tritanopia"]
BLUE = (0, 114, 178)
RED = (214, 39, 40)  # matplotlib's "tab:red"
RED_GREEN = ["#D62728", "#008200"]  # equal lightness, and one colour to a deuteranope
BLUE_ORANGE = ["#0072B2", "#E69F00"]  # the first two colours of the default palette
HEX_PAIR = re.compile(r"#[0-9A-F]{6} / #[0-9A-F]{6}")

# --- reference colour maths -------------------------------------------------------------------

MACHADO = {
    "protanopia": [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
    "deuteranopia": [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]],
    "tritanopia": [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]],
}


def to_linear(value):
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def to_srgb(value):
    return 12.92 * value if value <= 0.0031308 else 1.055 * value ** (1 / 2.4) - 0.055


def lab(rgb):
    """CIELAB (D65) of an sRGB colour given as 0..255 values."""
    r, g, b = (to_linear(value / 255) for value in rgb)
    xyz = (
        (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / 0.95047,
        0.2126729 * r + 0.7151522 * g + 0.0721750 * b,
        (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / 1.08883,
    )
    fx, fy, fz = (t ** (1 / 3) if t > (6 / 29) ** 3 else t / (3 * (6 / 29) ** 2) + 4 / 29 for t in xyz)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def simulate(rgb, deficiency):
    """What a colour (0..255) looks like with a colour-vision deficiency, as 0..255 floats."""
    linear = [to_linear(value / 255) for value in rgb]
    mixed = (sum(m * value for m, value in zip(row, linear)) for row in MACHADO[deficiency])
    return tuple(255 * to_srgb(min(max(value, 0.0), 1.0)) for value in mixed)


def grey_level(rgb):
    """The grey (0..255) with the same luminance as a colour."""
    r, g, b = (to_linear(value / 255) for value in rgb)
    return 255 * to_srgb(0.2126729 * r + 0.7151522 * g + 0.0721750 * b)


def lightness(rgb):
    return lab(rgb)[0]


def chroma(rgb):
    return math.hypot(*lab(rgb)[1:])


def delta_e(first, second):
    return math.dist(lab(first), lab(second))


def simulated_delta_e(first, second):
    """The smallest CIE76 difference left between two colours under the three deficiencies."""
    return min(delta_e(simulate(first, name), simulate(second, name)) for name in MACHADO)


def rgb(hex_code):
    return tuple(int(hex_code[i : i + 2], 16) for i in (1, 3, 5))


def hex_code(colour):
    return "#%02X%02X%02X" % tuple(colour)


def equal_lightness_green(colour):
    """The pure green (0, g, 0) whose L* is closest to the colour's."""
    return min(((0, g, 0) for g in range(256)), key=lambda green: abs(lightness(green) - lightness(colour)))


# --- helpers ----------------------------------------------------------------------------------


def run(*args, cwd):
    return subprocess.run(
        [UV, "run", "--quiet", str(SCRIPT), *map(str, args)], cwd=cwd, capture_output=True, text=True
    )


def check(*args, cwd):
    """Run with --json, expect exit 0 and return (report, checks by id)."""
    proc = run(*args, "--json", cwd=cwd)
    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    return report, {entry["id"]: entry for entry in report["checks"]}


def flat(path, size=(2102, 1200), mode="RGB", colour=BLUE, **save_kwargs):
    Image.new(mode, size, colour).save(path, **save_kwargs)
    return path


def halves(path, left, right, size=(1200, 600)):
    """Two large blocks of flat colour, side by side."""
    image = Image.new("RGB", size, left)
    image.paste(right, (size[0] // 2, 0, size[0], size[1]))
    image.save(path)
    return path


def swatches(path, colours, block=300, gap=60):
    """Large equal blocks of flat colour on white."""
    image = Image.new("RGB", (gap + len(colours) * (block + gap), block + 2 * gap), "white")
    for i, colour in enumerate(colours):
        left = gap + i * (block + gap)
        image.paste(colour, (left, gap, left + block, gap + block))
    image.save(path)
    return path


def inset(path, background, colour, box, size=(200, 200)):
    """A small rectangle of one colour inside another, small enough not to be resampled."""
    image = Image.new("RGB", size, background)
    image.paste(colour, (0, 0, *box))
    image.save(path)
    return path


def chart(path, colours, dpi, kind="lines"):
    """A real matplotlib chart, single column: white background, black axes and text, 1 pt lines."""
    rng = np.random.default_rng(0)
    x = np.linspace(0, 10, 200)
    with plt.style.context("default"):
        fig, ax = plt.subplots(figsize=(89 / 25.4, 0.75 * 89 / 25.4), layout="constrained")
        for k, colour in enumerate(colours):
            if kind == "lines":
                ax.plot(x, np.sin(x + 1.5 * k), color=colour, linewidth=1)
            else:
                ax.scatter(rng.normal(k, 1, 80), rng.normal(0.5 * k, 1, 80), s=4, color=colour)
        ax.set_xlabel("time (s)")
        ax.set_ylabel("signal (a.u.)")
        fig.savefig(path, dpi=dpi)
        plt.close(fig)
    return path


def listed_pairs(detail):
    return [set(pair.split(" / ")) for pair in HEX_PAIR.findall(detail)]


# --- report shape -----------------------------------------------------------------------------


def test_json_report_has_the_documented_shape(tmp_path):
    source = flat(tmp_path / "fig.png")

    report, _ = check(source, "--column", "single", cwd=tmp_path)

    assert list(report) == REPORT_KEYS
    assert report["input"] == str(source)
    assert report["format"] == "PNG"
    assert report["mode"] == "RGB"
    assert report["pixels"] == [2102, 1200]
    assert report["journal"] == "default"
    assert report["journal_note"] == journals.get("default")["note"]
    assert report["kind"] == "combination"
    assert report["previews"] is None
    assert [entry["id"] for entry in report["checks"]] == CHECK_IDS
    for entry in report["checks"]:
        assert list(entry) == ["id", "status", "detail"]
        assert entry["status"] in ("pass", "warn", "fail", "skip")
        assert entry["detail"]


def test_a_clean_figure_passes_every_check(tmp_path):
    source = halves(tmp_path / "fig.png", *map(rgb, BLUE_ORANGE), size=(4205, 1200))

    report, checks = check(source, cwd=tmp_path)

    assert {name: entry["status"] for name, entry in checks.items()} == dict.fromkeys(CHECK_IDS, "pass")
    assert report["overall"] == "pass"
    assert run(source, cwd=tmp_path).stdout.splitlines()[-1] == "OVERALL PASS"


def test_overall_is_the_worst_status_and_a_failed_check_still_exits_0(tmp_path):
    source = flat(tmp_path / "fig.jpg", size=(1000, 600))

    report, checks = check(source, "--journal", "elsevier", "--column", "double", cwd=tmp_path)

    assert checks["format"]["status"] == "warn"
    assert checks["effective_dpi"]["status"] == "fail"  # 134 dpi where Elsevier states 500
    assert report["overall"] == "fail"


def test_overall_is_warn_when_nothing_fails(tmp_path):
    source = flat(tmp_path / "fig.jpg", size=(4205, 1200))

    report, checks = check(source, cwd=tmp_path)

    assert checks["format"]["status"] == "warn"
    assert report["overall"] == "warn"


def test_without_json_it_prints_one_line_per_check_then_the_overall_status(tmp_path):
    source = flat(tmp_path / "fig.jpg")

    proc = run(source, "--journal", "elsevier", "--column", "double", cwd=tmp_path)

    assert proc.returncode == 0, proc.stderr
    lines = proc.stdout.splitlines()
    assert len(lines) == 8
    assert [line.split("  ")[1] for line in lines[:6]] == CHECK_IDS
    assert all(re.fullmatch(r"(PASS|WARN|FAIL|SKIP)  \w+  \S.*", line) for line in lines[:6])
    assert lines[0].startswith("WARN  format  ")
    assert lines[1].startswith("FAIL  effective_dpi  ")  # 281 dpi where Elsevier states 500
    assert lines[2].startswith("PASS  transparency  ")
    assert lines[6] == f"NOTE  {journals.get('elsevier')['note']}"
    assert lines[7] == "OVERALL FAIL  not judged: grayscale, colorblind"  # one flat colour: nothing to compare


def test_the_report_carries_the_note_of_the_journal_preset(tmp_path):
    # This is how a reader learns that the PLOS widths are a range, not columns.
    source = flat(tmp_path / "fig.png")

    plos, _ = check(source, "--journal", "plos", cwd=tmp_path)
    springer, _ = check(source, "--journal", "springer", cwd=tmp_path)

    assert plos["journal_note"] == journals.get("plos")["note"]
    assert "not columns" in plos["journal_note"]
    assert springer["journal_note"] is None


def test_without_json_a_journal_without_a_note_gets_no_note_line(tmp_path):
    source = flat(tmp_path / "fig.png")

    proc = run(source, "--journal", "springer", cwd=tmp_path)

    assert proc.returncode == 0, proc.stderr
    lines = proc.stdout.splitlines()
    assert len(lines) == 7
    assert not any(line.startswith("NOTE") for line in lines)
    assert lines[6].startswith("OVERALL ")


def test_a_photo_is_measured_the_way_viewers_show_it(tmp_path):
    # Stored 1200 x 2400, tagged "rotate 90 degrees clockwise to display": 2400 px wide on screen.
    exif = Image.Exif()
    exif[0x0112] = 6
    image = Image.new("RGB", (1200, 2400), "white")
    image.paste((0, 0, 255), (0, 0, 600, 600))
    image.save(tmp_path / "photo.jpg", quality=95, exif=exif)

    report, checks = check(tmp_path / "photo.jpg", "--column", "single", "--previews", "previews", cwd=tmp_path)

    assert report["format"] == "JPEG"
    assert report["pixels"] == [2400, 1200]
    assert "2400 px wide" in checks["effective_dpi"]["detail"]
    with Image.open(tmp_path / "previews" / "tritanopia.png") as preview:
        assert preview.size == (1600, 800)
        assert preview.getpixel((1500, 100))[2] > preview.getpixel((1500, 100))[0] + 50  # the blue corner, top right
        assert preview.getpixel((100, 100)) == pytest.approx((255, 255, 255), abs=8)


# --- format -----------------------------------------------------------------------------------


@pytest.mark.parametrize("name, pil_format", [("fig.png", "PNG"), ("fig.tif", "TIFF")])
def test_png_and_tiff_pass_the_format_check(tmp_path, name, pil_format):
    report, checks = check(flat(tmp_path / name), cwd=tmp_path)

    assert report["format"] == pil_format
    assert checks["format"]["status"] == "pass"
    assert pil_format in checks["format"]["detail"]


@pytest.mark.parametrize("journal", ["default", "cell"])  # Cell Press lists JPEG; it is lossy all the same
def test_jpeg_gets_a_format_warning_because_it_is_lossy(tmp_path, journal):
    report, checks = check(flat(tmp_path / "fig.jpg"), "--journal", journal, cwd=tmp_path)

    assert report["format"] == "JPEG"
    assert checks["format"] == {
        "id": "format", "status": "warn", "detail": "JPEG is lossy; re-export from the source as TIFF.",
    }


def test_jpeg_gets_the_rejection_sentence_where_the_publisher_does_not_accept_it(tmp_path):
    _, checks = check(flat(tmp_path / "fig.jpg"), "--journal", "jci", cwd=tmp_path)

    assert checks["format"]["status"] == "warn"
    assert checks["format"]["detail"] == (
        "Journal of Clinical Investigation does not accept JPEG for final artwork; it lists TIFF, PDF, EPS "
        "(bundled data, verified 2026-07-21)."
    )


@pytest.mark.parametrize(
    "journal, listed", [("nature", "PDF, EPS"), ("elsevier", "EPS, PDF, TIFF, JPEG"), ("plos", "TIFF, EPS")]
)
def test_png_gets_a_format_warning_where_the_publisher_does_not_take_it(tmp_path, journal, listed):
    _, checks = check(flat(tmp_path / "fig.png"), "--journal", journal, cwd=tmp_path)

    assert checks["format"]["status"] == "warn"
    assert checks["format"]["detail"] == journals.format_problem(journal, "png")
    assert "PNG" in checks["format"]["detail"]
    assert listed in checks["format"]["detail"]
    assert journals.get(journal)["label"] in checks["format"]["detail"]


@pytest.mark.parametrize("journal", ["wiley", "default"])
def test_png_passes_the_format_check_where_it_is_listed_or_nothing_is_listed(tmp_path, journal):
    _, checks = check(flat(tmp_path / "fig.png"), "--journal", journal, cwd=tmp_path)

    assert checks["format"]["status"] == "pass"


def test_tiff_gets_a_format_warning_at_nature(tmp_path):
    _, checks = check(flat(tmp_path / "fig.tif"), "--journal", "nature", cwd=tmp_path)

    assert checks["format"]["status"] == "warn"
    assert checks["format"]["detail"] == (
        "Nature Portfolio does not accept TIFF for final artwork; it lists PDF, EPS "
        "(bundled data, verified 2026-07-21)."
    )


def test_a_jpeg_that_carries_extra_pictures_gets_the_same_warning(tmp_path):
    # Phone photos often embed a second picture (depth or gain map); Pillow calls such a file MPO.
    extra = Image.new("RGB", (300, 200), "black")
    Image.new("RGB", (1200, 600), BLUE).save(tmp_path / "photo.jpg", "MPO", save_all=True, append_images=[extra])

    report, checks = check(tmp_path / "photo.jpg", cwd=tmp_path)

    assert report["format"] == "MPO"
    assert checks["format"]["status"] == "warn"
    assert "JPEG is lossy" in checks["format"]["detail"]


@pytest.mark.parametrize("name, pil_format", [("fig.webp", "WEBP"), ("fig.bmp", "BMP")])
def test_other_formats_get_a_format_warning(tmp_path, name, pil_format):
    _, checks = check(flat(tmp_path / name, size=(800, 400)), cwd=tmp_path)

    assert checks["format"]["status"] == "warn"
    assert pil_format in checks["format"]["detail"]
    assert "few publishers accept" in checks["format"]["detail"]


# --- effective_dpi ----------------------------------------------------------------------------


def test_effective_dpi_passes_at_the_single_column_width(tmp_path):
    # 2102 px at 89 mm is 599.9 dpi, one pixel short of journals.pixels_for(89, 600): it still counts as 600.
    assert journals.pixels_for(89, 600) == 2103
    source = flat(tmp_path / "fig.png")

    _, checks = check(source, "--journal", "default", "--column", "single", cwd=tmp_path)

    entry = checks["effective_dpi"]
    assert entry["status"] == "pass"
    assert "600 dpi at 89 mm (single column)" in entry["detail"]
    assert "needs" not in entry["detail"]


def test_effective_dpi_fails_at_the_double_column_width_and_says_what_is_needed(tmp_path):
    source = flat(tmp_path / "fig.png")

    _, checks = check(source, "--journal", "elsevier", "--column", "double", cwd=tmp_path)

    entry = checks["effective_dpi"]
    assert entry["status"] == "fail"
    assert "281 dpi at 190 mm (double column)" in entry["detail"]  # 2102 / (190 / 25.4)
    assert "500 dpi" in entry["detail"]
    assert f"needs {journals.pixels_for(190, 500)} px" in entry["detail"]


def test_a_shortfall_is_a_failure_only_against_a_minimum_the_publisher_states(tmp_path):
    # A blog, a thesis or a conference has no dpi rule: the common values are advice there, not a requirement.
    source = flat(tmp_path / "fig.png")

    _, generic = check(source, "--journal", "default", "--column", "double", cwd=tmp_path)
    _, unstated = check(source, "--journal", "science", "--width-mm", "178", cwd=tmp_path)  # Science states none for combination figures
    _, stated = check(source, "--journal", "elsevier", "--column", "double", cwd=tmp_path)

    for checks in (generic, unstated):
        entry = checks["effective_dpi"]
        assert entry["status"] == "warn"
        assert "300 dpi at 178 mm" in entry["detail"]
        assert f"needs {journals.pixels_for(178, 600)} px" in entry["detail"]  # 4205
        assert "generic default, not a publisher rule" in entry["detail"]
    assert stated["effective_dpi"]["status"] == "fail"
    assert "stated by Elsevier" in stated["effective_dpi"]["detail"]


def test_effective_dpi_warns_without_a_width_when_only_the_single_column_is_sharp_enough(tmp_path):
    source = flat(tmp_path / "fig.png")

    _, checks = check(source, cwd=tmp_path)

    entry = checks["effective_dpi"]
    assert entry["status"] == "warn"
    assert "600 dpi at 89 mm (single column)" in entry["detail"]
    assert "300 dpi at 178 mm (double column), needs 4205 px" in entry["detail"]
    assert "needs 2103 px" not in entry["detail"]
    assert "fine at single column but too low for double column" in entry["detail"].lower()


def test_effective_dpi_without_a_width_passes_when_both_columns_are_sharp_enough(tmp_path):
    source = flat(tmp_path / "fig.png", size=(4205, 1200))

    _, checks = check(source, cwd=tmp_path)

    assert checks["effective_dpi"]["status"] == "pass"
    assert "needs" not in checks["effective_dpi"]["detail"]


def test_effective_dpi_without_a_width_fails_when_neither_column_is_sharp_enough(tmp_path):
    source = flat(tmp_path / "fig.png", size=(2000, 1200))

    _, checks = check(source, "--journal", "elsevier", "--kind", "line_art", cwd=tmp_path)

    entry = checks["effective_dpi"]
    assert entry["status"] == "fail"
    assert f"564 dpi at 90 mm (single column), needs {journals.pixels_for(90, 1000)} px" in entry["detail"]
    assert f"267 dpi at 190 mm (double column), needs {journals.pixels_for(190, 1000)} px" in entry["detail"]


@pytest.mark.parametrize("width, shown, status", [(2100, 599, "warn"), (2101, 600, "pass")])
def test_effective_dpi_is_compared_as_a_whole_number(tmp_path, width, shown, status):
    # At 89 mm, 2101 px is 599.6 dpi, which counts as 600; 2100 px is 599.3 dpi, which does not.
    assert round(width / (89 / 25.4)) == shown
    source = flat(tmp_path / "fig.png", size=(width, 1200))

    _, checks = check(source, "--column", "single", cwd=tmp_path)

    entry = checks["effective_dpi"]
    assert entry["status"] == status
    assert f"{shown} dpi at 89 mm (single column)" in entry["detail"]
    assert ("needs 2103 px" in entry["detail"]) == (status == "warn")


def test_effective_dpi_at_a_width_in_millimetres(tmp_path):
    source = flat(tmp_path / "fig.png")

    _, narrow = check(source, "--width-mm", "50", cwd=tmp_path)
    _, wide = check(source, "--width-mm", "200", cwd=tmp_path)

    assert narrow["effective_dpi"]["status"] == "pass"
    assert "1068 dpi at 50 mm" in narrow["effective_dpi"]["detail"]  # 2102 / (50 / 25.4)
    assert wide["effective_dpi"]["status"] == "warn"  # below a common value; no publisher was named
    assert "267 dpi at 200 mm" in wide["effective_dpi"]["detail"]
    assert f"needs {journals.pixels_for(200, 600)} px" in wide["effective_dpi"]["detail"]


def test_the_figure_kind_selects_the_required_dpi(tmp_path):
    source = flat(tmp_path / "fig.png")  # 2102 px is also what 300 dpi needs at 178 mm

    photo, photo_checks = check(source, "--kind", "photo", cwd=tmp_path)
    _, line_checks = check(source, "--kind", "line_art", "--column", "single", cwd=tmp_path)

    assert photo["kind"] == "photo"
    assert photo_checks["effective_dpi"]["status"] == "pass"
    assert "300 dpi" in photo_checks["effective_dpi"]["detail"]
    assert line_checks["effective_dpi"]["status"] == "warn"
    assert f"needs {journals.pixels_for(89, 1000)} px" in line_checks["effective_dpi"]["detail"]


def test_a_publisher_that_wants_vector_artwork_gets_a_warning_with_the_dpi_figures(tmp_path):
    source = flat(tmp_path / "fig.png")

    report, checks = check(source, "--journal", "nature", "--kind", "line_art", cwd=tmp_path)

    entry = checks["effective_dpi"]
    assert report["journal"] == "nature"
    assert entry["status"] == "warn"
    assert "vector" in entry["detail"]
    assert "no raster file satisfies" in entry["detail"]
    assert "607 dpi at 88 mm (single column)" in entry["detail"]  # 2102 / (88 / 25.4)
    assert "297 dpi at 180 mm (double column)" in entry["detail"]


def test_vector_artwork_is_a_warning_even_at_a_given_width(tmp_path):
    source = flat(tmp_path / "fig.png", size=(8000, 1200))

    _, checks = check(source, "--journal", "nature", "--kind", "line_art", "--column", "single", cwd=tmp_path)

    assert checks["effective_dpi"]["status"] == "warn"
    assert "vector" in checks["effective_dpi"]["detail"]


def test_the_detail_says_when_the_publisher_states_the_requirement(tmp_path):
    source = flat(tmp_path / "fig.png")

    _, checks = check(source, "--journal", "cell", "--kind", "line_art", "--column", "single", cwd=tmp_path)

    entry = checks["effective_dpi"]
    assert entry["status"] == "fail"  # 2102 px at 85 mm is 628 dpi; Cell Press asks 1000 for line art
    assert "628 dpi at 85 mm (single column)" in entry["detail"]
    assert "1000 dpi" in entry["detail"]
    assert "stated by Cell Press" in entry["detail"]
    assert "generic" not in entry["detail"]
    assert f"needs {journals.pixels_for(85, 1000)} px" in entry["detail"]


def test_a_minimum_given_on_the_command_line_replaces_the_one_of_the_preset(tmp_path):
    # A graphical-abstract guide, a thesis or a report sets its own figure: here 300 dpi, where the
    # preset holds the 500 dpi that Cell Press states for figures in the text.
    source = flat(tmp_path / "fig.png", size=(1650, 1650))
    place = ("--journal", "cell", "--width-mm", "139.7")

    _, preset = check(source, *place, cwd=tmp_path)
    _, asked = check(source, *place, "--min-dpi", "300", cwd=tmp_path)
    _, short = check(source, *place, "--min-dpi", "400", cwd=tmp_path)

    assert preset["effective_dpi"]["status"] == "fail"
    assert asked["effective_dpi"]["status"] == "pass"
    assert "300 dpi at 139.7 mm" in asked["effective_dpi"]["detail"]
    assert "Minimum: 300 dpi (given with --min-dpi)" in asked["effective_dpi"]["detail"]
    assert "Cell Press" not in asked["effective_dpi"]["detail"]
    assert short["effective_dpi"]["status"] == "fail"  # the caller's own minimum is a requirement
    assert f"needs {journals.pixels_for(139.7, 400)} px" in short["effective_dpi"]["detail"]


def test_a_figure_for_the_screen_is_not_judged_for_print(tmp_path):
    # A slide or a blog post has no printed width; without this, every agent had to explain a warning away.
    source = flat(tmp_path / "fig.png", size=(1672, 941))

    plain, plain_checks = check(source, cwd=tmp_path)
    report, checks = check(source, "--screen", cwd=tmp_path)

    assert plain_checks["effective_dpi"]["status"] == "warn" and plain["overall"] == "warn"
    assert checks["effective_dpi"] == {
        "id": "effective_dpi", "status": "pass", "detail": "1672 x 941 px, for the screen: no printed width applies.",
    }
    assert report["overall"] == "pass"
    assert report["journal_note"] is None  # the generic preset's remark is about print and journals


@pytest.mark.parametrize("journal", ["science", "default"])
def test_the_detail_says_when_the_requirement_is_only_the_generic_default(tmp_path, journal):
    # Science states no dpi for combination figures; "default" is not a publisher at all.
    source = flat(tmp_path / "fig.png")

    _, checks = check(source, "--journal", journal, "--column", "single", cwd=tmp_path)

    entry = checks["effective_dpi"]
    assert entry["status"] == "pass"
    assert "600 dpi" in entry["detail"]
    assert "generic default" in entry["detail"]
    assert "stated by" not in entry["detail"]


# --- how strong the fills are -----------------------------------------------------------------

FAINT = ["#E8F2FC", "#E9F3EB", "#FCEEE5"]  # tints close to white: CIELAB chroma 6 to 7, lightness 95
PASTEL = ["#BBDAF9", "#D7EFCF", "#F6DDBF"]  # what "pale pastel" came back as from an image tool: chroma 18 to 19


def test_fills_measures_how_strong_the_light_coloured_areas_are(tmp_path):
    faint, _ = check(swatches(tmp_path / "faint.png", FAINT), "--look", cwd=tmp_path)
    pastel, _ = check(swatches(tmp_path / "pastel.png", PASTEL), "--look", cwd=tmp_path)

    assert list(faint["fills"]) == ["share", "chroma", "lightness", "strong_share"]
    assert faint["fills"]["strong_share"] == pastel["fills"]["strong_share"] == 0.0
    assert faint["fills"]["chroma"] == pytest.approx(6.5, abs=1)
    assert faint["fills"]["lightness"] == pytest.approx(95, abs=1)
    assert pastel["fills"]["chroma"] == pytest.approx(18.5, abs=1.5)
    assert pastel["fills"]["lightness"] == pytest.approx(88, abs=4)
    # Three 300 px blocks on a 1140 x 420 px page.
    assert faint["fills"]["share"] == pytest.approx(3 * 300 * 300 / (1140 * 420), abs=0.01)


def test_strong_colour_is_counted_apart_from_the_fills(tmp_path):
    # White page, black frame, one block of saturated blue, one faint tint: only the tint is a fill,
    # and the blue block is what a designer would call the strong colour of the figure.
    image = Image.new("RGB", (1200, 600), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 40, 1160, 560), outline="black", width=6)
    draw.rectangle((100, 150, 500, 450), fill="#0072B2")
    draw.rectangle((700, 150, 1100, 450), fill="#E9F3EB")
    image.save(tmp_path / "mixed.png")
    alone, _ = check(swatches(tmp_path / "alone.png", ["#E9F3EB"]), "--look", cwd=tmp_path)

    mixed, _ = check(tmp_path / "mixed.png", "--look", cwd=tmp_path)

    assert mixed["fills"]["chroma"] == pytest.approx(alone["fills"]["chroma"], abs=0.2)
    assert mixed["fills"]["share"] == pytest.approx(400 * 300 / (1200 * 600), abs=0.01)
    assert mixed["fills"]["strong_share"] == pytest.approx(400 * 300 / (1200 * 600), abs=0.01)
    assert alone["fills"]["strong_share"] == 0.0


def test_fills_are_measured_only_when_asked_and_change_no_verdict(tmp_path):
    source = swatches(tmp_path / "fig.png", PASTEL)

    plain = run(source, cwd=tmp_path)
    asked = run(source, "--look", cwd=tmp_path)
    report, _ = check(source, cwd=tmp_path)

    assert report["fills"] is None and report["lines"] is None
    assert "FILLS" not in plain.stdout and "LINES" not in plain.stdout
    lines = asked.stdout.splitlines()
    (line,) = [text for text in lines if text.startswith("FILLS  ")]
    assert re.fullmatch(
        r"FILLS  Light coloured areas cover \d+% of the figure: median chroma \d+, median lightness \d+\. "
        r"Strong colour \(chroma 30 or more\) covers \d+%\. .*", line,
    )
    assert "median chroma 1" in line  # 18 or 19
    assert [text for text in lines if not text.startswith(("FILLS", "LINES"))] == plain.stdout.splitlines()


def test_a_figure_without_light_colour_has_no_fills_to_measure(tmp_path):
    source = flat(tmp_path / "fig.png", size=(600, 400), colour="white")

    report, _ = check(source, "--look", cwd=tmp_path)
    proc = run(source, "--look", cwd=tmp_path)

    assert report["fills"] == {"share": 0.0, "chroma": None, "lightness": None, "strong_share": 0.0}
    assert "FILLS  No light coloured areas: nothing to measure." in proc.stdout.splitlines()


# --- how heavy the lines are ------------------------------------------------------------------


def boxes(path, outline_px, arrow_px=3, size=(1672, 941)):
    """Four tinted boxes with a blue outline of a known width, joined by dark lines of a known width."""
    image = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(image)
    for i in range(4):
        left = 80 + 380 * i
        draw.rounded_rectangle((left, 200, left + 300, 500), radius=18, fill="#E8F2FC", outline="#1D83BB", width=outline_px)
        if i < 3:
            draw.line((left + 310, 350, left + 370, 350), fill="#3B3B3B", width=arrow_px)
    draw.line((80, 700, 1500, 700), fill="#3B3B3B", width=arrow_px)
    image.save(path)
    return path


@pytest.mark.parametrize("outline_px", [2, 4, 6])
def test_look_measures_how_thick_the_long_straight_lines_are(tmp_path, outline_px):
    report, _ = check(boxes(tmp_path / "fig.png", outline_px), "--look", cwd=tmp_path)

    assert report["lines"] == {
        "coloured_px": outline_px, "coloured_share": round(outline_px / 1672, 4), "dark_px": 3, "dark_share": round(3 / 1672, 4),
    }


def test_the_lines_line_gives_the_thickness_in_pixels_and_against_the_width(tmp_path):
    proc = run(boxes(tmp_path / "fig.png", 4), "--look", cwd=tmp_path)

    (line,) = [text for text in proc.stdout.splitlines() if text.startswith("LINES  ")]
    assert line.startswith(
        "LINES  Long straight lines: the coloured ones are 4 px thick at the median (0.24% of the width), "
        "the dark ones 3 px (0.18%). "
    )


def soft_boxes(path, outline_quarters, shift_quarters=0, size=(1672, 941)):
    """boxes() with soft edges, as a renderer draws them: drawn four times as large with an outline
    of that many quarter pixels, moved down by a few quarter pixels, then averaged down."""
    image = Image.new("RGB", (4 * size[0], 4 * size[1]), "white")
    draw = ImageDraw.Draw(image)
    for i in range(4):
        left, top = 4 * (80 + 380 * i) + shift_quarters, 4 * 200 + shift_quarters
        draw.rectangle((left, top, left + 1200, top + 1200), fill="#E8F2FC", outline="#1D83BB", width=outline_quarters)
    image.reduce(4).save(path)
    return path


@pytest.mark.parametrize("outline_quarters", [8, 10, 12])
def test_a_line_with_soft_edges_is_measured_in_fractions_of_a_pixel(tmp_path, outline_quarters):
    report, _ = check(soft_boxes(tmp_path / "fig.png", outline_quarters, shift_quarters=1), "--look", cwd=tmp_path)

    assert report["lines"]["coloured_px"] == pytest.approx(outline_quarters / 4, abs=0.15)


def test_a_line_that_straddles_two_rows_of_pixels_is_not_read_a_pixel_thicker(tmp_path):
    # Two pixels thick, half a pixel off the grid: it darkens three rows, and is still 2 px.
    on_grid, _ = check(soft_boxes(tmp_path / "on.png", 8), "--look", cwd=tmp_path)
    off_grid, _ = check(soft_boxes(tmp_path / "off.png", 8, shift_quarters=2), "--look", cwd=tmp_path)

    assert on_grid["lines"]["coloured_px"] == 2
    assert off_grid["lines"]["coloured_px"] == pytest.approx(2, abs=0.15)


@pytest.mark.parametrize(
    "size, hairline, heavy",
    [
        ((1672, 941), "2", "3"), ((1086, 1448), "2", "3"), ((640, 480), "2", "3"),  # what an image tool returns
        ((1797, 2396), "3.3", "5"), ((2817, 1585), "3.4", "5.1"), ((3054, 1719), "3.7", "5.5"),  # the same, enlarged
    ],
)
def test_the_lines_line_names_the_hairline_for_a_picture_of_that_size(tmp_path, size, hairline, heavy):
    # 2 px is a hairline and more than 3 px is heavy in a picture of 1.57 megapixels, which is what an image
    # tool returns in any shape; in a 16:9 picture that is 0.12% and 0.18% of the width, as in the finer
    # published figures. A larger picture has more in proportion to its side, so that an enlarged figure is
    # judged as it was before it was enlarged, a tall one too; a smaller picture has no less.
    proc = run(boxes(tmp_path / "fig.png", 4, size=size), "--look", cwd=tmp_path)

    (line,) = [text for text in proc.stdout.splitlines() if text.startswith("LINES  ")]
    assert line.endswith(f" A hairline is {hairline} px in a picture of this size; more than {heavy} px reads as heavy.")


def test_text_and_filled_shapes_are_not_lines(tmp_path):
    # A paragraph of words and a solid block: nothing long and thin, so no line to measure.
    image = Image.new("RGB", (1200, 600), "white")
    draw = ImageDraw.Draw(image)
    for row in range(8):
        draw.text((60, 40 + 40 * row), "Scaled dot-product attention over keys and values", fill="#3B3B3B", font_size=28)
    draw.rectangle((700, 300, 1100, 520), fill="#1D83BB")
    image.save(tmp_path / "fig.png")

    report, _ = check(tmp_path / "fig.png", "--look", cwd=tmp_path)
    proc = run(tmp_path / "fig.png", "--look", cwd=tmp_path)

    assert report["lines"] == {"coloured_px": None, "coloured_share": None, "dark_px": None, "dark_share": None}
    assert "LINES  No long straight lines: nothing to measure." in proc.stdout.splitlines()


def soft_frames(path, size, line_px):
    """Two blue frames and two dark ones whose outlines are line_px thick and half a pixel off the grid: drawn
    twice as large, then averaged down, so that the pixels along each edge of an outline are half covered."""
    width, height = size
    image = Image.new("RGB", (2 * width, 2 * height), "white")
    draw = ImageDraw.Draw(image)
    for i, colour in enumerate(["#1D83BB", "#3B3B3B"] * 2):
        left, top = 2 * round((0.06 + 0.23 * i) * width) + 1, 2 * round(0.2 * height) + 1
        draw.rectangle((left, top, left + 2 * round(0.18 * width), top + 2 * round(0.6 * height)), outline=colour, width=2 * line_px)
    image.reduce(2).save(path)
    return path


@pytest.mark.parametrize("size, line_px", [((3545, 1995), 3), ((3545, 1995), 4), ((3545, 1995), 5), ((5016, 2822), 3)])
def test_the_lines_of_an_enlarged_figure_are_measured_in_fractions_of_a_pixel(tmp_path, size, line_px):
    # An enlarged figure has more pixels than an image tool returns. Measured on a sample of them, its lines lost
    # the soft edges that the thickness is read from to a tenth of a pixel.
    report, _ = check(soft_frames(tmp_path / "fig.png", size, line_px), "--look", cwd=tmp_path)

    assert report["lines"]["coloured_px"] == pytest.approx(line_px, abs=0.15)
    assert report["lines"]["dark_px"] == pytest.approx(line_px, abs=0.15)


def test_a_picture_too_large_to_measure_whole_is_still_read_in_pixels_of_the_file(tmp_path):
    # Over 15 megapixels, --look first averages blocks of pixels, to bound its memory: here blocks of 2 x 2. Every
    # edge lies between two blocks, so that the lines it measures are 3 and 2 px thick: 6 and 4 px of the file.
    image = Image.new("RGB", (4000, 4000), "white")
    draw = ImageDraw.Draw(image)
    for left in range(400, 3600, 800):
        draw.rectangle((left, 400, left + 599, 3599), outline="#1D83BB", width=6)
        draw.rectangle((left, 3800, left + 599, 3803), fill="#3B3B3B")
    image.save(tmp_path / "fig.png")

    report, _ = check(tmp_path / "fig.png", "--look", cwd=tmp_path)

    assert (report["lines"]["coloured_px"], report["lines"]["dark_px"]) == (6, 4)


# --- transparency -----------------------------------------------------------------------------


def test_an_image_without_alpha_passes_the_transparency_check(tmp_path):
    _, checks = check(flat(tmp_path / "fig.png"), cwd=tmp_path)

    assert checks["transparency"]["status"] == "pass"


def test_a_fully_opaque_alpha_channel_passes_the_transparency_check(tmp_path):
    source = flat(tmp_path / "fig.png", mode="RGBA", colour=(*BLUE, 255))

    report, checks = check(source, cwd=tmp_path)

    assert report["mode"] == "RGBA"
    assert checks["transparency"]["status"] == "pass"
    assert "opaque" in checks["transparency"]["detail"]


def test_a_transparent_region_gets_a_transparency_warning(tmp_path):
    image = Image.new("RGBA", (1200, 600), (*BLUE, 255))
    image.paste((0, 0, 0, 0), (0, 0, 300, 600))  # a quarter of the figure
    image.save(tmp_path / "fig.png")

    _, checks = check(tmp_path / "fig.png", cwd=tmp_path)

    assert checks["transparency"]["status"] == "warn"
    assert "25.0%" in checks["transparency"]["detail"]
    assert "flatten" in checks["transparency"]["detail"].lower()


def test_a_single_translucent_pixel_is_enough_for_the_transparency_warning(tmp_path):
    image = Image.new("RGBA", (1200, 600), (*BLUE, 255))
    image.putpixel((7, 7), (*BLUE, 254))
    image.save(tmp_path / "fig.png")

    _, checks = check(tmp_path / "fig.png", cwd=tmp_path)

    assert checks["transparency"]["status"] == "warn"


def test_a_transparent_palette_colour_counts_as_transparency(tmp_path):
    image = Image.new("P", (1200, 600), 0)
    image.putpalette([255, 255, 255, *BLUE])
    image.paste(1, (600, 0, 1200, 600))
    image.save(tmp_path / "fig.png", transparency=0)

    _, checks = check(tmp_path / "fig.png", cwd=tmp_path)

    assert checks["transparency"]["status"] == "warn"


# --- color_mode -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mode, colour", [("RGB", BLUE), ("RGBA", (*BLUE, 255)), ("L", 90), ("LA", (90, 255))]
)
def test_rgb_and_greyscale_modes_pass_and_are_named(tmp_path, mode, colour):
    report, checks = check(flat(tmp_path / "fig.png", mode=mode, colour=colour), cwd=tmp_path)

    assert report["mode"] == mode
    assert checks["color_mode"]["status"] == "pass"
    assert re.search(rf"\b{mode}\b", checks["color_mode"]["detail"])
    assert "ICC" not in checks["color_mode"]["detail"]


def test_cmyk_gets_a_color_mode_warning(tmp_path):
    source = flat(tmp_path / "fig.tif", mode="CMYK", colour=(255, 0, 0, 0))

    report, checks = check(source, cwd=tmp_path)

    assert report["mode"] == "CMYK"
    assert checks["color_mode"]["status"] == "warn"
    assert "CMYK" in checks["color_mode"]["detail"]
    assert "RGB" in checks["color_mode"]["detail"]
    assert "confirm with the journal" in checks["color_mode"]["detail"].lower()


@pytest.mark.parametrize("mode", ["P", "1"])
def test_other_modes_get_a_color_mode_warning(tmp_path, mode):
    source = tmp_path / "fig.png"
    Image.new("RGB", (800, 400), "white").convert(mode).save(source)

    report, checks = check(source, cwd=tmp_path)

    assert report["mode"] == mode
    assert checks["color_mode"]["status"] == "warn"
    assert "convert to RGB" in checks["color_mode"]["detail"]


def test_a_16_bit_image_gets_a_color_mode_warning_and_the_other_checks_still_run(tmp_path):
    source = tmp_path / "fig.tif"
    Image.fromarray(np.full((400, 800), 30000, dtype=np.uint16)).save(source)

    report, checks = check(source, cwd=tmp_path)

    assert report["mode"] == "I;16"
    assert checks["color_mode"]["status"] == "warn"
    assert checks["grayscale"]["status"] == "skip"  # one grey: no colours to compare
    assert checks["colorblind"]["status"] == "skip"


def test_an_embedded_icc_profile_is_named(tmp_path):
    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB"))
    name = ImageCms.getProfileDescription(profile).strip()
    source = flat(tmp_path / "fig.png", icc_profile=profile.tobytes())

    _, checks = check(source, cwd=tmp_path)

    assert name
    assert checks["color_mode"]["status"] == "pass"
    assert f"ICC profile: {name}" in checks["color_mode"]["detail"]


def test_an_unreadable_icc_profile_does_not_stop_the_checks(tmp_path):
    source = flat(tmp_path / "fig.png", icc_profile=b"not an icc profile")

    report, checks = check(source, cwd=tmp_path)

    assert checks["color_mode"]["status"] == "pass"
    assert "unreadable" in checks["color_mode"]["detail"]
    assert report["overall"] in ("pass", "warn")


# --- grayscale --------------------------------------------------------------------------------


def test_a_red_and_a_green_of_equal_lightness_get_both_colour_warnings(tmp_path):
    green = equal_lightness_green(RED)
    assert abs(lightness(RED) - lightness(green)) < 1
    assert delta_e(RED, green) > 100  # very different colours on screen ...
    assert delta_e(simulate(RED, "deuteranopia"), simulate(green, "deuteranopia")) < 10  # ... but not to a deuteranope
    source = halves(tmp_path / "fig.png", RED, green)

    _, checks = check(source, cwd=tmp_path)

    pair = {hex_code(RED), hex_code(green)}
    assert checks["grayscale"]["status"] == "warn"
    assert set(HEX_PAIR.search(checks["grayscale"]["detail"])[0].split(" / ")) == pair
    assert checks["colorblind"]["status"] == "warn"
    assert "(deuteranopia)" in checks["colorblind"]["detail"]
    assert "(tritanopia)" not in checks["colorblind"]["detail"]
    assert set(HEX_PAIR.search(checks["colorblind"]["detail"])[0].split(" / ")) == pair


def test_colours_of_different_lightness_pass_the_grayscale_check(tmp_path):
    dark_blue, yellow = rgb("#0072B2"), rgb("#F0E442")
    assert abs(lightness(dark_blue) - lightness(yellow)) > 40
    source = halves(tmp_path / "fig.png", dark_blue, yellow)

    _, checks = check(source, cwd=tmp_path)

    assert checks["grayscale"]["status"] == "pass"
    assert "2 salient colours" in checks["grayscale"]["detail"]


@pytest.mark.parametrize("green, status", [("#009E00", "warn"), ("#00A000", "pass")])
def test_lightness_within_10_looks_alike_in_greyscale(tmp_path, green, status):
    difference = lightness(rgb(green)) - lightness(RED)
    assert 9.5 < difference < 10.5 and (difference < 10) == (status == "warn")
    source = halves(tmp_path / "fig.png", RED, rgb(green))

    _, checks = check(source, cwd=tmp_path)

    assert checks["grayscale"]["status"] == status


@pytest.mark.parametrize("pink, status", [("#C8507A", "pass"), ("#C8507C", "warn")])
def test_only_colours_at_least_25_apart_are_compared(tmp_path, pink, status):
    # Two shades with the same lightness. Under 25 they count as one colour, so nothing is reported.
    base = rgb("#C85050")
    difference = delta_e(base, rgb(pink))
    assert 24 < difference < 26 and (difference >= 25) == (status == "warn")
    assert abs(lightness(base) - lightness(rgb(pink))) < 2
    assert simulated_delta_e(base, rgb(pink)) < 10  # tritanopia merges them
    source = halves(tmp_path / "fig.png", base, rgb(pink))

    _, checks = check(source, cwd=tmp_path)

    assert checks["grayscale"]["status"] == status
    assert checks["colorblind"]["status"] == status


@pytest.mark.parametrize("dull_green, salient", [("#607460", False), ("#607560", True)])
def test_only_colours_with_a_chroma_of_at_least_15_are_salient(tmp_path, dull_green, salient):
    assert 14 < chroma(rgb(dull_green)) < 16 and (chroma(rgb(dull_green)) >= 15) == salient
    assert abs(lightness(RED) - lightness(rgb(dull_green))) < 1
    source = halves(tmp_path / "fig.png", RED, rgb(dull_green))

    _, checks = check(source, cwd=tmp_path)

    assert checks["grayscale"]["status"] == ("warn" if salient else "skip")
    assert ("fewer than two salient colours" in checks["grayscale"]["detail"].lower()) == (not salient)
    assert ("fewer than two salient colours" in checks["colorblind"]["detail"].lower()) == (not salient)


@pytest.mark.parametrize("box, salient", [((13, 23), False), ((15, 20), True)])
def test_a_colour_needs_3_percent_of_the_pixels_outside_the_most_common_colour(tmp_path, box, salient):
    # On white: 9700 red pixels and 299 or 300 green ones, just under and exactly 3% of the two.
    image = Image.new("RGB", (200, 200), "white")
    image.paste(RED, (0, 0, 97, 100))
    image.paste(equal_lightness_green(RED), (100, 100, 100 + box[0], 100 + box[1]))
    image.save(tmp_path / "fig.png")

    _, checks = check(tmp_path / "fig.png", cwd=tmp_path)

    assert checks["grayscale"]["status"] == ("warn" if salient else "skip")
    assert checks["colorblind"]["status"] == ("warn" if salient else "skip")


def test_small_marks_on_a_large_background_count(tmp_path):
    # Two 10 x 10 squares on white: each is 0.25% of the image, and half of what is not background.
    green = equal_lightness_green(RED)
    image = Image.new("RGB", (200, 200), "white")
    image.paste(RED, (20, 20, 30, 30))
    image.paste(green, (120, 120, 130, 130))
    image.save(tmp_path / "fig.png")

    _, checks = check(tmp_path / "fig.png", cwd=tmp_path)

    assert listed_pairs(checks["grayscale"]["detail"]) == [{hex_code(RED), hex_code(green)}]
    assert checks["colorblind"]["status"] == "warn"


def test_the_most_common_colour_is_a_colour_of_the_figure_too(tmp_path):
    # A red figure with a small green patch: the red is the background here, and still counts.
    green = equal_lightness_green(RED)
    source = inset(tmp_path / "fig.png", RED, green, (19, 21))

    _, checks = check(source, cwd=tmp_path)

    assert listed_pairs(checks["grayscale"]["detail"]) == [{hex_code(RED), hex_code(green)}]


# --- real charts: thin lines and small markers ------------------------------------------------


@pytest.mark.parametrize("dpi", [300, 600])
@pytest.mark.parametrize("kind", ["lines", "markers"])
def test_a_chart_in_a_red_and_a_green_of_equal_lightness_gets_both_colour_warnings(tmp_path, kind, dpi):
    source = chart(tmp_path / "fig.png", RED_GREEN, dpi, kind)

    _, checks = check(source, cwd=tmp_path)

    assert checks["grayscale"]["status"] == "warn"
    assert set(RED_GREEN) in listed_pairs(checks["grayscale"]["detail"])
    assert checks["colorblind"]["status"] == "warn"
    assert set(RED_GREEN) in listed_pairs(checks["colorblind"]["detail"])


@pytest.mark.parametrize("dpi", [300, 600])
@pytest.mark.parametrize("kind", ["lines", "markers"])
def test_a_chart_in_blue_and_orange_passes_both_colour_checks(tmp_path, kind, dpi):
    source = chart(tmp_path / "fig.png", BLUE_ORANGE, dpi, kind)

    _, checks = check(source, cwd=tmp_path)

    assert checks["grayscale"]["status"] == "pass", checks["grayscale"]["detail"]
    assert checks["colorblind"]["status"] == "pass", checks["colorblind"]["detail"]


def test_a_greyscale_figure_has_nothing_to_compare(tmp_path):
    image = Image.new("L", (1200, 600), 255)
    image.paste(60, (0, 0, 400, 600))
    image.paste(150, (400, 0, 800, 600))
    image.save(tmp_path / "fig.png")

    _, checks = check(tmp_path / "fig.png", cwd=tmp_path)

    for name in ("grayscale", "colorblind"):
        assert checks[name]["status"] == "skip"
        assert "fewer than two salient colours" in checks[name]["detail"].lower()


def test_a_figure_in_faint_tints_is_not_compared_and_that_is_not_called_a_pass(tmp_path):
    # Tinted boxes with hairline outlines, as an image tool draws them: no colour is strong and
    # widespread enough to count, so neither check says anything about the figure.
    source = boxes(tmp_path / "fig.png", 1, size=(4205, 1200))

    report, checks = check(source, cwd=tmp_path)
    proc = run(source, cwd=tmp_path)

    for name in ("grayscale", "colorblind"):
        assert checks[name]["status"] == "skip"
        assert "faint tints and fine coloured lines are not judged" in checks[name]["detail"].lower()
    assert report["overall"] == "pass"  # a skipped check never sets the overall status
    assert [line.split("  ")[0] for line in proc.stdout.splitlines()[4:6]] == ["SKIP", "SKIP"]
    assert proc.stdout.splitlines()[-1] == "OVERALL PASS  not judged: grayscale, colorblind"


def test_at_most_five_pairs_are_listed(tmp_path):
    colours = [rgb(code) for code in scistyle.PALETTES["okabe_ito"][:-1]]
    alike = [
        (a, b)
        for i, a in enumerate(colours)
        for b in colours[i + 1 :]
        if delta_e(a, b) >= 25 and abs(lightness(a) - lightness(b)) < 10
    ]
    assert len(alike) == 7  # for example orange #E69F00 and sky blue #56B4E9
    source = swatches(tmp_path / "fig.png", colours)

    _, checks = check(source, cwd=tmp_path)

    entry = checks["grayscale"]
    assert entry["status"] == "warn"
    listed = [set(pair.split(" / ")) for pair in HEX_PAIR.findall(entry["detail"])]
    assert len(listed) == 5
    assert all(pair in [{hex_code(a), hex_code(b)} for a, b in alike] for pair in listed)
    assert "and 2 more" in entry["detail"]


def test_pairs_are_listed_most_widespread_colours_first(tmp_path):
    # Three colours of the same lightness covering 15%, 25% and 60% of the figure.
    green = equal_lightness_green(RED)
    blue = min(((0, g, 255) for g in range(256)), key=lambda colour: abs(lightness(colour) - lightness(RED)))
    assert max(map(lightness, (RED, green, blue))) - min(map(lightness, (RED, green, blue))) < 1
    assert min(delta_e(RED, green), delta_e(RED, blue), delta_e(green, blue)) > 25
    image = Image.new("RGB", (1000, 400), blue)
    image.paste(RED, (0, 0, 150, 400))
    image.paste(green, (150, 0, 400, 400))
    image.save(tmp_path / "fig.png")

    _, checks = check(tmp_path / "fig.png", cwd=tmp_path)

    listed = [pair.split(" / ") for pair in HEX_PAIR.findall(checks["grayscale"]["detail"])]
    assert listed == [
        [hex_code(blue), hex_code(green)],
        [hex_code(blue), hex_code(RED)],
        [hex_code(green), hex_code(RED)],
    ]


def test_transparent_areas_count_as_white(tmp_path):
    # Fully transparent red must not be taken for a colour of the figure.
    green = equal_lightness_green(RED)
    image = Image.new("RGBA", (1200, 600), (*RED, 0))
    image.paste((*green, 255), (600, 0, 1200, 600))
    image.save(tmp_path / "fig.png")

    _, checks = check(tmp_path / "fig.png", cwd=tmp_path)

    assert checks["grayscale"]["status"] == "skip"
    assert "fewer than two salient colours" in checks["grayscale"]["detail"].lower()


# --- colorblind -------------------------------------------------------------------------------


@pytest.mark.parametrize("palette, salient", [("okabe_ito", 7), ("tol_bright", 6), ("tol_muted", 9)])
def test_the_bundled_palettes_pass_the_colorblind_check(tmp_path, palette, salient):
    # Whole palettes as large equal blocks on white. Okabe-Ito's black and Tol's grey have no
    # chroma, so they are not among the salient colours.
    assert set(scistyle.PALETTES) == {"okabe_ito", "tol_bright", "tol_muted"}
    colours = [rgb(code) for code in scistyle.PALETTES[palette]]
    assert sum(chroma(colour) >= 15 for colour in colours) == salient
    source = swatches(tmp_path / "fig.png", colours)

    _, checks = check(source, cwd=tmp_path)

    assert checks["colorblind"]["status"] == "pass"
    assert f"{salient} salient colours" in checks["colorblind"]["detail"]


@pytest.mark.parametrize(
    "red, green, status", [("#E62828", "#008B00", "warn"), ("#EE2828", "#009000", "pass")]
)
def test_a_pair_is_confusable_when_its_simulated_difference_is_under_10(tmp_path, red, green, status):
    left = simulated_delta_e(rgb(red), rgb(green))
    assert 9.5 < left < 10.5 and (left < 10) == (status == "warn")
    assert delta_e(rgb(red), rgb(green)) > 100
    source = halves(tmp_path / "fig.png", rgb(red), rgb(green))

    _, checks = check(source, cwd=tmp_path)

    assert checks["colorblind"]["status"] == status


def test_each_deficiency_is_simulated(tmp_path):
    # Blue and green merge for a tritanope only; red and green for a deuteranope only.
    blue, teal = rgb("#0000FF"), rgb("#008080")
    green = equal_lightness_green(RED)
    confusions = {}
    for name, first, second in [("blue_teal", blue, teal), ("red_green", RED, green)]:
        confusions[name] = sorted(
            deficiency
            for deficiency in MACHADO
            if delta_e(first, second) >= 25
            and delta_e(simulate(first, deficiency), simulate(second, deficiency)) < 10
        )
    halves(tmp_path / "blue_teal.png", blue, teal)
    halves(tmp_path / "red_green.png", RED, green)

    for name, expected in confusions.items():
        _, checks = check(tmp_path / f"{name}.png", cwd=tmp_path)
        found = sorted(set(re.findall(r"\((\w+)\)", checks["colorblind"]["detail"])) & set(MACHADO))
        assert found == expected, name

    assert confusions["red_green"] == ["deuteranopia"]


# --- previews ---------------------------------------------------------------------------------


def test_previews_are_written_only_on_request(tmp_path):
    source = flat(tmp_path / "fig.png", size=(800, 400))

    report, _ = check(source, cwd=tmp_path)

    assert report["previews"] is None
    assert [path.name for path in tmp_path.iterdir()] == ["fig.png"]


def test_previews_writes_four_png_files_and_reports_their_paths(tmp_path):
    source = flat(tmp_path / "fig.png", size=(3200, 1000))
    directory = tmp_path / "new" / "previews"

    report, _ = check(source, "--previews", directory, cwd=tmp_path)

    assert report["previews"] == {name: str(directory / f"{name}.png") for name in PREVIEWS}
    assert sorted(path.name for path in directory.iterdir()) == sorted(f"{name}.png" for name in PREVIEWS)
    assert sorted(path.name for path in tmp_path.iterdir()) == ["fig.png", "new"]
    for name in PREVIEWS:
        with Image.open(directory / f"{name}.png") as preview:
            assert preview.format == "PNG"
            assert preview.size == (1600, 500)  # long side at most 1600 px, same shape
            assert preview.mode == ("L" if name == "grayscale" else "RGB")


def test_previews_of_a_small_figure_keep_its_size(tmp_path):
    source = flat(tmp_path / "fig.png", size=(800, 400))

    check(source, "--previews", "previews", cwd=tmp_path)

    with Image.open(tmp_path / "previews" / "protanopia.png") as preview:
        assert preview.size == (800, 400)


@pytest.mark.parametrize("colour", [(255, 0, 0), (0, 0, 255), BLUE, RED, (255, 255, 255), (0, 0, 0)])
def test_previews_show_the_simulated_colours(tmp_path, colour):
    source = flat(tmp_path / "fig.png", size=(400, 200), colour=colour)

    check(source, "--previews", tmp_path / "previews", cwd=tmp_path)

    with Image.open(tmp_path / "previews" / "grayscale.png") as preview:
        assert preview.getpixel((200, 100)) == pytest.approx(grey_level(colour), abs=0.51)
    for deficiency in MACHADO:
        with Image.open(tmp_path / "previews" / f"{deficiency}.png") as preview:
            assert preview.getpixel((200, 100)) == pytest.approx(simulate(colour, deficiency), abs=0.51), deficiency


def test_protanopia_turns_pure_red_into_a_dark_olive(tmp_path):
    # For pure red the linear result is the first column of the matrix: 0.152286, 0.114503, -0.003882.
    expected = (255 * to_srgb(0.152286), 255 * to_srgb(0.114503), 0)
    assert expected == pytest.approx((108.8, 95.0, 0), abs=0.05)
    source = flat(tmp_path / "fig.png", size=(400, 200), colour=(255, 0, 0))

    check(source, "--previews", tmp_path / "previews", cwd=tmp_path)

    with Image.open(tmp_path / "previews" / "protanopia.png") as preview:
        assert preview.getpixel((200, 100)) == (109, 95, 0)


def test_the_greyscale_preview_merges_colours_of_equal_lightness(tmp_path):
    green = equal_lightness_green(RED)
    source = halves(tmp_path / "fig.png", RED, green)

    check(source, "--previews", tmp_path / "previews", cwd=tmp_path)

    with Image.open(tmp_path / "previews" / "grayscale.png") as preview:
        left, right = preview.getpixel((300, 300)), preview.getpixel((900, 300))
    assert abs(left - right) <= 1
    assert left == pytest.approx(grey_level(RED), abs=0.51)


def test_previews_show_transparent_areas_as_white(tmp_path):
    image = Image.new("RGBA", (400, 200), (255, 0, 0, 0))
    image.paste((*BLUE, 255), (200, 0, 400, 200))
    image.save(tmp_path / "fig.png")

    check(tmp_path / "fig.png", "--previews", tmp_path / "previews", cwd=tmp_path)

    with Image.open(tmp_path / "previews" / "grayscale.png") as preview:
        assert preview.getpixel((100, 100)) == 255
    with Image.open(tmp_path / "previews" / "deuteranopia.png") as preview:
        assert preview.getpixel((100, 100)) == (255, 255, 255)


def test_previews_of_a_16_bit_image_keep_its_tones(tmp_path):
    ramp = np.tile(np.linspace(0, 65535, 800).astype(np.uint16), (400, 1))
    Image.fromarray(ramp).save(tmp_path / "fig.tif")

    check(tmp_path / "fig.tif", "--previews", tmp_path / "previews", cwd=tmp_path)

    with Image.open(tmp_path / "previews" / "grayscale.png") as preview:
        assert np.asarray(preview)[200] == pytest.approx(ramp[200] >> 8, abs=1)


def test_without_json_the_preview_paths_are_printed_before_the_overall_line(tmp_path):
    source = flat(tmp_path / "fig.png", size=(800, 400))

    proc = run(source, "--previews", "previews", cwd=tmp_path)

    assert proc.returncode == 0, proc.stderr
    lines = proc.stdout.splitlines()
    assert lines[6:10] == [f"PREVIEW  {name}  {Path('previews') / f'{name}.png'}" for name in PREVIEWS]
    assert lines[10].startswith("NOTE  ")
    assert lines[11].startswith("OVERALL ")
    assert len(lines) == 12


def test_the_lines_print_through_a_pipe_whose_code_page_lacks_their_characters(tmp_path):
    # On Windows a pipe takes the ANSI code page, cp1252 in the West, which has no Chinese.
    source = flat(tmp_path / "图.png", size=(800, 400))

    proc = subprocess.run(
        [UV, "run", "--quiet", str(SCRIPT), str(source), "--previews", "检查"], cwd=tmp_path, capture_output=True,
        env={**os.environ, "PYTHONIOENCODING": "cp1252"},
    )

    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
    assert f"PREVIEW  grayscale  {Path('检查') / 'grayscale.png'}" in proc.stdout.decode("utf-8").splitlines()


# --- failures and usage -----------------------------------------------------------------------


def test_it_writes_nothing_next_to_itself(tmp_path):
    # Not even a __pycache__ for journals.py. Run a copy, with this interpreter rather than uv,
    # which would keep one cached environment per copy.
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    for name in ("check_figure.py", "journals.py"):
        shutil.copy(SCRIPTS / name, scripts / name)
    source = flat(tmp_path / "fig.png", size=(800, 400))

    proc = subprocess.run(
        [sys.executable, str(scripts / "check_figure.py"), str(source)], cwd=tmp_path, capture_output=True, text=True
    )

    assert proc.returncode == 0, proc.stderr
    assert sorted(path.name for path in scripts.iterdir()) == ["check_figure.py", "journals.py"]
    assert sorted(path.name for path in tmp_path.iterdir()) == ["fig.png", "scripts"]


def test_a_missing_input_fails_with_one_line_on_stderr(tmp_path):
    proc = run(tmp_path / "nope.png", "--json", cwd=tmp_path)

    assert proc.returncode == 1
    assert proc.stdout == ""
    assert len(proc.stderr.strip().splitlines()) == 1
    assert "nope.png" in proc.stderr


@pytest.mark.parametrize("name", ["fig.pdf", "fig.eps", "fig.svg"])
def test_a_vector_file_is_refused_with_what_to_check_instead(tmp_path, name):
    # The vector file is what a chart's author submits, so it is the first thing they point the check at.
    scistyle.use()
    fig, _ = scistyle.figure()
    fig.savefig(tmp_path / name)
    plt.close(fig)

    proc = run(name, cwd=tmp_path)

    assert proc.returncode == 1
    assert proc.stdout == ""
    assert len(proc.stderr.strip().splitlines()) == 1
    assert re.search(rf"{name} is a vector file.*run it on a PNG of the same figure", proc.stderr), proc.stderr


def test_a_file_that_is_not_an_image_fails_without_writing_previews(tmp_path):
    (tmp_path / "notes.txt").write_text("not an image")

    proc = run("notes.txt", "--previews", "previews", cwd=tmp_path)

    assert proc.returncode == 1
    assert proc.stdout == ""
    assert len(proc.stderr.strip().splitlines()) == 1
    assert [path.name for path in tmp_path.iterdir()] == ["notes.txt"]


@pytest.mark.parametrize(
    "options",
    [
        ["--width-mm", "89", "--column", "single"],
        ["--width-mm", "0"],
        ["--width-mm", "wide"],
        ["--column", "triple"],
        ["--journal", "not-a-journal"],
        ["--kind", "diagram"],
        ["--min-dpi", "0"],
        ["--screen", "--column", "single"],
        ["--screen", "--min-dpi", "300"],
    ],
)
def test_usage_errors_exit_2(tmp_path, options):
    source = flat(tmp_path / "fig.png", size=(800, 400))

    proc = run(source, *options, cwd=tmp_path)

    assert proc.returncode == 2
    assert "usage: check_figure.py" in proc.stderr  # argparse's message, not a uv failure
    assert proc.stdout == ""
