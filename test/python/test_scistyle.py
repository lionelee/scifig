"""Tests for skills/scifig/scripts/scistyle.py."""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

os.environ["MPLBACKEND"] = "Agg"  # headless; inherited by the subprocesses below

import matplotlib

matplotlib.use("Agg")  # also covers another test module having imported matplotlib first
import matplotlib.pyplot as plt
import pytest
from PIL import Image

SCRIPTS = Path(__file__).resolve().parents[2] / "skills" / "scifig" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import journals  # noqa: E402
import scistyle  # noqa: E402

UV = os.environ.get("UV", "uv")
NATURE_SINGLE_IN = 88 / 25.4
NATURE_DOUBLE_IN = 180 / 25.4
DEFAULT_SINGLE_IN = 89 / 25.4


@pytest.fixture(autouse=True)
def isolated_style():
    """scistyle.use() edits the global rcParams and remembers the journal: undo both after each test."""
    with matplotlib.rc_context():
        yield
        scistyle.use()  # back to the default journal; leaving the context then restores the rcParams
    plt.close("all")


def run_cli(*args, cwd):
    return subprocess.run(
        [UV, "run", "--quiet", str(SCRIPTS / "scistyle.py"), *args], cwd=cwd, capture_output=True, text=True
    )


def plotted_figure(width="single"):
    fig, ax = scistyle.figure(width)
    ax.plot([0, 1, 2, 3], [0, 1, 4, 9], label="signal")
    ax.set_xlabel("time (s)")
    ax.set_ylabel("signal (a.u.)")
    return fig


def lightness(hex_code):
    """CIE L* (D65) of an sRGB colour such as "#0072B2"."""
    channels = [int(hex_code[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = (c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels)
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    return 116 * (y ** (1 / 3) if y > (6 / 29) ** 3 else y / (3 * (6 / 29) ** 2) + 4 / 29) - 16


# --- palettes ---------------------------------------------------------------------------------


def test_palettes_are_ordered_colour_cycles():
    assert scistyle.PALETTES["okabe_ito"] == [
        "#0072B2", "#E69F00", "#009E73", "#D55E00", "#56B4E9", "#CC79A7", "#F0E442", "#000000",
    ]
    assert scistyle.PALETTES["tol_bright"][0] == "#4477AA"
    assert scistyle.PALETTES["tol_muted"][0] == "#CC6677"
    assert {name: len(colours) for name, colours in scistyle.PALETTES.items()} == {
        "okabe_ito": 8,
        "tol_bright": 7,
        "tol_muted": 9,
    }


def test_the_first_three_okabe_ito_colours_survive_greyscale_print():
    # Blue, orange and bluish green: every pair is at least 10 L* apart.
    first = [lightness(colour) for colour in scistyle.PALETTES["okabe_ito"][:3]]

    assert lightness("#FFFFFF") == pytest.approx(100) and lightness("#000000") == pytest.approx(0)
    assert abs(first[0] - first[1]) >= 10  # 24.6
    assert abs(first[0] - first[2]) >= 10  # 11.8
    assert abs(first[1] - first[2]) >= 10  # 12.9


# --- use() ------------------------------------------------------------------------------------


def test_use_sets_the_journal_font_size_and_the_palette_cycle():
    preset = scistyle.use("nature")

    assert preset == journals.get("nature")
    assert matplotlib.rcParams["font.size"] == 7
    assert matplotlib.rcParams["axes.prop_cycle"].by_key()["color"][0] == "#0072B2"


def test_use_cycles_through_the_whole_chosen_palette():
    scistyle.use("default", palette="tol_bright")

    assert matplotlib.rcParams["axes.prop_cycle"].by_key()["color"] == scistyle.PALETTES["tol_bright"]


def test_use_prefers_the_journal_fonts_and_always_ends_with_dejavu_sans():
    scistyle.use("nature")

    assert matplotlib.rcParams["font.family"] == ["sans-serif", *installed_cjk_fonts()]  # then fonts for Chinese text
    assert matplotlib.rcParams["font.sans-serif"] == ["Helvetica", "Arial", "DejaVu Sans"]


def test_use_falls_back_to_the_default_fonts_and_size_when_the_journal_states_none():
    scistyle.use("wiley")  # fonts and font_pt are None in this preset

    default = journals.get("default")
    assert matplotlib.rcParams["font.sans-serif"] == [*default["fonts"], "DejaVu Sans"]
    assert matplotlib.rcParams["font.size"] == default["font_pt"]


def test_use_sizes_titles_ticks_labels_and_legend_from_the_journal():
    scistyle.use("ieee")  # 9 pt

    sized = ("font.size", "axes.titlesize", "axes.labelsize", "xtick.labelsize", "ytick.labelsize", "legend.fontsize")
    for key in sized:
        assert matplotlib.rcParams[key] == 9, key


@pytest.mark.parametrize(
    "key, value",
    [
        ("axes.linewidth", 0.6),
        ("lines.linewidth", 1.0),
        ("axes.spines.top", False),
        ("axes.spines.right", False),
        ("legend.frameon", False),
        ("pdf.fonttype", 42),
        ("ps.fonttype", 42),
        ("svg.fonttype", "none"),
        ("figure.constrained_layout.use", True),
    ],
)
def test_use_sets_the_publication_rcparams(key, value):
    scistyle.use()

    assert matplotlib.rcParams[key] == value


def test_use_rejects_an_unknown_journal_and_lists_the_choices():
    with pytest.raises(ValueError, match="nature"):
        scistyle.use("not-a-journal")


def test_use_rejects_an_unknown_palette_and_lists_the_choices():
    with pytest.raises(ValueError, match="okabe_ito"):
        scistyle.use(palette="rainbow")


def test_a_rejected_use_keeps_the_current_journal():
    scistyle.use("nature")
    with pytest.raises(ValueError):
        scistyle.use("science", palette="rainbow")

    fig, _ = scistyle.figure("single")
    assert fig.get_size_inches()[0] == pytest.approx(NATURE_SINGLE_IN, abs=1e-6)


# --- figure() ---------------------------------------------------------------------------------


def test_figure_single_column_width_matches_the_journal():
    scistyle.use("nature")

    fig, _ = scistyle.figure("single")

    width, height = fig.get_size_inches()
    assert width == pytest.approx(NATURE_SINGLE_IN, abs=1e-6)
    assert height == pytest.approx(NATURE_SINGLE_IN * 0.75, abs=1e-6)


def test_figure_accepts_double_column_an_aspect_and_a_grid_of_axes():
    scistyle.use("nature")

    fig, axes = scistyle.figure("double", aspect=0.5, nrows=2, ncols=3, sharex=True)

    assert list(fig.get_size_inches()) == pytest.approx([NATURE_DOUBLE_IN, NATURE_DOUBLE_IN * 0.5])
    assert axes.shape == (2, 3)
    assert axes[0, 0].get_shared_x_axes().joined(axes[0, 0], axes[1, 2])


def test_figure_accepts_a_width_in_millimetres():
    scistyle.use("nature")

    fig, _ = scistyle.figure(120)

    assert fig.get_size_inches()[0] == pytest.approx(120 / 25.4)


def test_figure_raises_when_taller_than_the_journal_allows():
    scistyle.use("nature")  # maximum height 247 mm

    with pytest.raises(ValueError, match="247"):
        scistyle.figure("single", aspect=3)  # 88 mm * 3 = 264 mm


def test_figure_has_no_height_limit_when_the_journal_states_none():
    scistyle.use("default")

    fig, _ = scistyle.figure("single", aspect=5)

    assert fig.get_size_inches()[1] == pytest.approx(DEFAULT_SINGLE_IN * 5)


# --- panel_labels() ---------------------------------------------------------------------------


def test_panel_labels_are_bold_lowercase_letters_at_the_journal_size():
    scistyle.use("nature")  # lower case, 8 pt
    _, axes = scistyle.figure("double", nrows=2, ncols=2)

    scistyle.panel_labels(axes)

    labels = [ax.texts[-1] for ax in axes.flat]
    assert [label.get_text() for label in labels] == ["a", "b", "c", "d"]
    assert all(label.get_fontweight() == "bold" and label.get_fontsize() == 8 for label in labels)


def test_panel_labels_are_capitals_for_an_uppercase_journal():
    scistyle.use("science")  # upper case, 10 pt
    _, axes = scistyle.figure("double", ncols=2)

    scistyle.panel_labels(axes)

    assert [ax.texts[-1].get_text() for ax in axes] == ["A", "B"]
    assert axes[0].texts[-1].get_fontsize() == 10


def test_panel_labels_default_to_8_pt_lowercase_when_the_journal_states_nothing():
    scistyle.use("wiley")  # panel_case and panel_pt are None
    _, ax = scistyle.figure()

    scistyle.panel_labels(ax)

    assert ax.texts[-1].get_text() == "a"
    assert ax.texts[-1].get_fontsize() == 8


def test_panel_labels_accept_custom_labels_and_a_list_of_axes():
    scistyle.use()
    _, axes = scistyle.figure("double", ncols=2)

    scistyle.panel_labels(list(axes), labels=["i", "ii"])

    assert [ax.texts[-1].get_text() for ax in axes] == ["i", "ii"]


def test_panel_labels_sit_outside_the_top_left_corner_of_the_axes():
    scistyle.use("nature")
    fig, ax = scistyle.figure()

    scistyle.panel_labels(ax)

    fig.canvas.draw()
    label = ax.texts[-1].get_window_extent()
    frame = ax.get_window_extent()
    assert label.x1 <= frame.x0
    assert label.y0 >= frame.y1


# --- save() -----------------------------------------------------------------------------------


def test_save_writes_each_requested_format(tmp_path):
    scistyle.use("nature")
    fig = plotted_figure("single")

    paths = scistyle.save(fig, tmp_path / "fig1", formats=("pdf", "png", "tiff"))

    assert paths == [str(tmp_path / f"fig1.{ext}") for ext in ("pdf", "png", "tiff")]
    assert all(Path(path).stat().st_size > 0 for path in paths)
    assert Path(paths[0]).read_bytes().startswith(b"%PDF")
    with Image.open(paths[1]) as png:
        # Nature asks 300 dpi for combination figures. The canvas is the whole figure, untrimmed.
        assert png.width == pytest.approx(round(NATURE_SINGLE_IN * 300), abs=1)
        assert png.height == pytest.approx(round(NATURE_SINGLE_IN * 0.75 * 300), abs=1)
    with Image.open(paths[2]) as tiff:
        assert tiff.info["compression"] == "tiff_lzw"
        assert tiff.width == pytest.approx(round(NATURE_SINGLE_IN * 300), abs=1)


def test_save_writes_pdf_and_png_by_default(tmp_path):
    scistyle.use()
    fig = plotted_figure()

    scistyle.save(fig, tmp_path / "fig")

    assert sorted(path.name for path in tmp_path.iterdir()) == ["fig.pdf", "fig.png"]


def test_save_raster_dpi_defaults_to_the_journal_requirement(tmp_path):
    scistyle.use("default")  # 600 dpi for combination figures
    fig = plotted_figure("single")

    (path,) = scistyle.save(fig, tmp_path / "fig", formats=("png",))

    with Image.open(path) as png:
        assert png.width == pytest.approx(round(DEFAULT_SINGLE_IN * 600), abs=1)


def test_save_uses_600_dpi_when_the_journal_wants_vector_artwork(tmp_path, monkeypatch):
    vector_only = {**journals.get("nature"), "dpi": {"photo": 300, "combination": "vector", "line_art": "vector"}}
    monkeypatch.setitem(journals.JOURNALS, "vector-only", vector_only)
    scistyle.use("vector-only")
    fig = plotted_figure("single")

    (path,) = scistyle.save(fig, tmp_path / "fig", formats=("png",))

    with Image.open(path) as png:
        assert png.width == pytest.approx(round(NATURE_SINGLE_IN * 600), abs=1)


def test_save_honours_an_explicit_dpi(tmp_path):
    scistyle.use("nature")
    fig = plotted_figure("single")

    (path,) = scistyle.save(fig, tmp_path / "fig", formats=("png",), dpi=150)

    with Image.open(path) as png:
        assert png.width == pytest.approx(round(NATURE_SINGLE_IN * 150), abs=1)


@pytest.mark.parametrize("journal, column", [("nature", "single"), ("nature", "double"), ("science", "single")])
def test_a_saved_figure_passes_the_resolution_check_at_its_own_column(tmp_path, journal, column):
    # Science's 57 mm column is the narrowest of the presets, where a pixel weighs the most.
    scistyle.use(journal)
    fig = plotted_figure(column)
    (path,) = scistyle.save(fig, tmp_path / "fig", formats=("png",))

    proc = subprocess.run(
        [UV, "run", "--quiet", str(SCRIPTS / "check_figure.py"), path, "--journal", journal, "--column", column, "--json"],
        cwd=tmp_path, capture_output=True, text=True,
    )

    assert proc.returncode == 0, proc.stderr
    resolution = {check["id"]: check for check in json.loads(proc.stdout)["checks"]}["effective_dpi"]
    assert resolution["status"] == "pass", resolution["detail"]


def test_save_keeps_text_as_text_in_svg_and_writes_eps(tmp_path):
    scistyle.use("nature")
    fig = plotted_figure()

    svg, eps = scistyle.save(fig, tmp_path / "fig", formats=("svg", "eps"))

    assert "signal (a.u.)" in Path(svg).read_text()
    assert Path(eps).read_bytes().startswith(b"%!PS")


def test_save_rejects_an_unknown_format_before_writing_anything(tmp_path):
    scistyle.use()
    fig = plotted_figure()

    with pytest.raises(ValueError, match="jpg"):
        scistyle.save(fig, tmp_path / "fig", formats=("png", "jpg"))

    assert list(tmp_path.iterdir()) == []


# --- command line and real-world use ----------------------------------------------------------


def test_list_prints_one_json_object_with_journals_and_palettes(tmp_path):
    proc = run_cli("--list", cwd=tmp_path)

    assert proc.returncode == 0, proc.stderr
    listing = json.loads(proc.stdout)
    assert "nature" in listing["journals"]
    assert "okabe_ito" in listing["palettes"]
    assert listing["verified"] == journals.VERIFIED == "2026-07-21"  # the date the presets were checked
    expected = {"verified": journals.VERIFIED, "journals": journals.JOURNALS, "palettes": scistyle.PALETTES}
    assert listing == json.loads(json.dumps(expected))


def test_list_can_be_limited_to_the_journals_named(tmp_path):
    # The whole listing is more than 300 lines, which agents see cut off.
    proc = run_cli("--list", "nature", "cell", cwd=tmp_path)

    assert proc.returncode == 0, proc.stderr
    listing = json.loads(proc.stdout)
    assert list(listing["journals"]) == ["nature", "cell"]
    assert listing["journals"]["nature"] == json.loads(json.dumps(journals.JOURNALS["nature"]))
    assert listing["verified"] == journals.VERIFIED and "okabe_ito" in listing["palettes"]


def test_list_names_the_presets_when_asked_for_an_unknown_journal(tmp_path):
    proc = run_cli("--list", "natur", cwd=tmp_path)

    assert proc.returncode == 2
    assert proc.stdout == ""
    assert "natur" in proc.stderr and "nature, science" in proc.stderr


def test_the_cli_needs_list(tmp_path):
    proc = run_cli(cwd=tmp_path)

    assert proc.returncode == 2
    assert "usage: scistyle.py" in proc.stderr  # argparse's message, not a uv failure
    assert proc.stdout == ""


def test_the_cli_writes_nothing_next_to_itself(tmp_path):
    # Not even a __pycache__ for journals.py. Run a copy, with this interpreter rather than uv,
    # which would keep one cached environment per copy.
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    for name in ("scistyle.py", "journals.py"):
        shutil.copy(SCRIPTS / name, scripts / name)

    proc = subprocess.run(
        [sys.executable, str(scripts / "scistyle.py"), "--list"], cwd=tmp_path, capture_output=True, text=True
    )

    assert proc.returncode == 0, proc.stderr
    assert "okabe_ito" in json.loads(proc.stdout)["palettes"]
    assert sorted(path.name for path in scripts.iterdir()) == ["journals.py", "scistyle.py"]
    assert [path.name for path in tmp_path.iterdir()] == ["scripts"]


def test_importing_scistyle_alone_leaves_interpreter_settings_to_the_caller(tmp_path):
    code = (
        "import sys, matplotlib\n"
        "before = sys.dont_write_bytecode\n"
        "import scistyle\n"
        "print(matplotlib.get_backend().lower(), sys.dont_write_bytecode == before)\n"
    )
    env = {**os.environ, "MPLBACKEND": "svg", "PYTHONPATH": str(SCRIPTS)}

    proc = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, env=env, capture_output=True, text=True)

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.split() == ["svg", "True"]


@pytest.mark.parametrize("backend", [None, "svg"])
def test_use_selects_the_agg_backend_because_scistyle_only_renders_to_files(tmp_path, backend):
    # With MPLBACKEND unset matplotlib would pick a GUI backend where there is one (macosx on a Mac).
    code = (
        "import matplotlib, scistyle\n"
        "scistyle.use('nature')\n"
        "fig, ax = scistyle.figure()\n"
        "scistyle.save(fig, 'fig', formats=('png',))\n"
        "print(matplotlib.get_backend().lower())\n"
    )
    env = {key: value for key, value in os.environ.items() if key != "MPLBACKEND"}
    env["PYTHONPATH"] = str(SCRIPTS)
    if backend:
        env["MPLBACKEND"] = backend

    proc = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, env=env, capture_output=True, text=True)

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.split() == ["agg"]
    assert (tmp_path / "fig.png").stat().st_size > 0


CHART_SCRIPT = """\
import sys

sys.path.insert(0, sys.argv[1])
import numpy as np
import scistyle

scistyle.use("nature")
fig, axes = scistyle.figure("double", aspect=0.4, ncols=2)
x = np.linspace(0, 6, 50)
for ax in axes:
    ax.plot(x, np.sin(x), label="sin")
    ax.plot(x, np.cos(x), label="cos")
    ax.legend()
scistyle.panel_labels(axes)
print("\\n".join(scistyle.save(fig, sys.argv[2])))
"""


def test_a_chart_script_can_import_scistyle_from_the_skill_folder_and_save(tmp_path):
    script = tmp_path / "chart.py"
    script.write_text(CHART_SCRIPT)
    stem = tmp_path / "out"

    proc = subprocess.run(
        [sys.executable, str(script), str(SCRIPTS), str(stem)], cwd=tmp_path, capture_output=True, text=True
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines() == [f"{stem}.pdf", f"{stem}.png"]
    with Image.open(f"{stem}.png") as png:
        assert png.width == pytest.approx(round(NATURE_DOUBLE_IN * 300), abs=1)


def test_saving_a_pdf_prints_no_font_subsetting_warnings(tmp_path):
    # While matplotlib embeds a font, fontTools warns about harmless quirks of some system fonts
    # (macOS Helvetica: "1 extra bytes in post.stringData array").
    script = tmp_path / "chart.py"
    script.write_text(CHART_SCRIPT)

    proc = subprocess.run(
        [sys.executable, str(script), str(SCRIPTS), str(tmp_path / "out")], cwd=tmp_path, capture_output=True, text=True
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stderr == ""


def test_a_saved_tiff_has_no_alpha_channel(tmp_path):
    # Publishers ask for RGB; matplotlib writes RGBA. The resolution tag and the compression must survive.
    scistyle.use("plos")
    fig = plotted_figure()

    (path,) = scistyle.save(fig, tmp_path / "fig", formats=("tiff",))

    with Image.open(path) as tiff:
        assert tiff.mode == "RGB"
        assert tiff.info["compression"] == "tiff_lzw"
        assert tiff.info["dpi"][0] == pytest.approx(300, abs=0.5)  # what PLOS asks for combination figures
        assert tiff.getpixel((2, 2)) == (255, 255, 255)  # the white page, not a transparent one turned black


def test_canvas_is_a_full_page_axes_in_millimetres():
    scistyle.use("elsevier")

    fig, ax = scistyle.canvas("double", 108)

    assert list(fig.get_size_inches()) == pytest.approx([190 / 25.4, 108 / 25.4])
    assert list(ax.get_position().bounds) == pytest.approx([0, 0, 1, 1])
    assert ax.get_xlim() == (0, 190) and ax.get_ylim() == (0, 108)
    assert not ax.axison
    assert type(fig.get_layout_engine()).__name__ == "PlaceHolderLayoutEngine"  # nothing moves what is drawn


def test_a_point_on_the_canvas_lands_where_its_millimetres_say(tmp_path):
    scistyle.use("elsevier")
    fig, ax = scistyle.canvas(100, 50)
    ax.add_patch(plt.Rectangle((75, 0), 25, 25, color="black"))  # the bottom-right quarter of the right half

    (path,) = scistyle.save(fig, tmp_path / "canvas", formats=("png",), dpi=254)  # 10 px per mm

    with Image.open(path) as png:
        assert png.size == (1000, 500)
        assert png.convert("L").getpixel((875, 375)) < 10  # inside the square
        assert png.convert("L").getpixel((700, 375)) > 245 and png.convert("L").getpixel((875, 200)) > 245


def test_canvas_takes_the_same_widths_as_figure_and_refuses_a_page_that_is_too_tall():
    scistyle.use("nature")

    fig, _ = scistyle.canvas("single", 60)
    assert fig.get_size_inches()[0] == pytest.approx(88 / 25.4)
    with pytest.raises(ValueError, match="247"):
        scistyle.canvas("single", 300)


def test_saving_a_canvas_in_two_formats_stays_quiet_and_keeps_the_layout_off(tmp_path):
    # matplotlib re-enables the rc layout engine after the first save of a figure that has none,
    # and the second save then warns that it has nothing to lay out.
    code = (
        "import scistyle\n"
        "scistyle.use('elsevier')\n"
        "fig, ax = scistyle.canvas('single', 60)\n"
        "a = ax.text(20, 40, 'A', bbox=dict(boxstyle='square'))\n"
        "b = ax.text(60, 20, 'B', bbox=dict(boxstyle='square'))\n"
        "ax.annotate('', xy=b.get_position(), xytext=a.get_position(), arrowprops=dict(arrowstyle='-|>'))\n"
        "scistyle.save(fig, 'diagram', formats=('pdf', 'png'))\n"
        "print(type(fig.get_layout_engine()).__name__)\n"
    )
    env = {**os.environ, "PYTHONPATH": str(SCRIPTS)}

    proc = subprocess.run([sys.executable, "-W", "error", "-c", code], cwd=tmp_path, env=env, capture_output=True, text=True)

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.split() == ["PlaceHolderLayoutEngine"]
    assert proc.stderr == ""


def installed_cjk_fonts():
    from matplotlib import font_manager

    installed = {font.name for font in font_manager.fontManager.ttflist}
    return [name for name in scistyle.CJK_FONTS if name in installed]


@pytest.mark.skipif(not installed_cjk_fonts() if hasattr(scistyle, "CJK_FONTS") else False, reason="no Chinese font installed")
def test_chinese_text_falls_back_to_a_chinese_font_glyph_by_glyph(tmp_path):
    # The journal font has no Chinese glyphs; without a fallback matplotlib draws empty boxes.
    code = (
        "import scistyle\n"
        "scistyle.use('nature')\n"
        "fig, ax = scistyle.figure()\n"
        "ax.set_xlabel('Time 时间 (s)')\n"
        "scistyle.save(fig, 'cjk', formats=('pdf', 'png'))\n"
    )
    env = {**os.environ, "PYTHONPATH": str(SCRIPTS)}

    proc = subprocess.run([sys.executable, "-W", "error", "-c", code], cwd=tmp_path, env=env, capture_output=True, text=True)

    assert proc.returncode == 0, proc.stderr  # no "Glyph missing from font" warning
    assert proc.stderr == ""
    pdf = (tmp_path / "cjk.pdf").read_bytes()
    fonts = set(re.findall(rb"/BaseFont\s*/(?:[A-Z]{6}\+)?([\w-]+)", pdf))
    assert not any(b"LastResort" in name for name in fonts)
    assert len(fonts) == 2, fonts  # the journal's Latin font and one Chinese font


def test_small_type_in_the_journal_font_draws_at_screen_resolution():
    # macOS Helvetica cannot be loaded with its own hinting below 8 pixels per em. At 7 pt the superscripts
    # of a log axis are smaller than that whenever something draws the figure on screen, as seaborn does.
    scistyle.use("nature")
    fig, ax = scistyle.figure()
    ax.semilogx([1e-3, 1e2], [0, 1])
    ax.text(0.01, 0.5, "the smallest type Nature allows", fontsize=5)

    fig.canvas.draw()  # raised "FT_Load_Glyph failed with error 0x85: division by zero"


def test_subscripts_superscripts_and_greek_letters_are_set_in_the_journal_font(tmp_path):
    # matplotlib sets "$...$" in a maths font of its own (DejaVu Sans, slanted) unless told to use the text font.
    scistyle.use("nature")
    fig, ax = scistyle.figure()
    ax.set_xlabel(r"IC$_{50}$ ($\mu$M)")
    ax.set_ylabel("Area (mm$^2$)")

    (path,) = scistyle.save(fig, tmp_path / "maths", formats=("pdf",))

    fonts = set(re.findall(rb"/BaseFont\s*/(?:[A-Z]{6}\+)?([\w-]+)", Path(path).read_bytes()))
    assert len(fonts) == 1, fonts  # the journal font alone


# --- diagrams: boxes of a fixed size, connectors, and the fit check ---------------------------


def dark(image, x_mm, y_mm, px_per_mm, height_mm):
    """Is the page dark at (x_mm, y_mm), measured from the bottom-left corner?"""
    return image.getpixel((round(x_mm * px_per_mm), round((height_mm - y_mm) * px_per_mm))) < 128


def test_box_draws_a_frame_of_the_given_size_and_returns_where_to_attach_lines(tmp_path):
    scistyle.use("elsevier")
    fig, ax = scistyle.canvas(100, 50)

    node = scistyle.box(ax, 20, 10, 40, 20, "Screened")

    assert (node.left, node.right, node.bottom, node.top) == ((20, 20), (60, 20), (40, 10), (40, 30))
    assert node.text.get_text() == "Screened"
    (path,) = scistyle.save(fig, tmp_path / "box", formats=("png",), dpi=254)  # 10 px per mm
    with Image.open(path) as png:
        page = png.convert("L")
        for x, y in ((20, 20), (60, 20), (40, 10), (40, 30)):  # the four sides of the frame
            assert dark(page, x, y, 10, 50), (x, y)
        assert not dark(page, 10, 20, 10, 50) and not dark(page, 40, 40, 10, 50)  # nothing outside it


def test_save_refuses_a_box_whose_text_does_not_fit(tmp_path):
    scistyle.use("elsevier")
    fig, ax = scistyle.canvas(100, 50)
    scistyle.box(ax, 10, 10, 12, 8, "Reports assessed for eligibility")  # 12 mm is far too narrow at 7 pt

    with pytest.raises(ValueError, match="does not fit.*Reports assessed for eligibility"):
        scistyle.save(fig, tmp_path / "overflow", formats=("png",))
    assert not (tmp_path / "overflow.png").exists()


def test_a_box_can_set_its_lines_from_the_left(tmp_path):
    scistyle.use("elsevier")
    fig, ax = scistyle.canvas(100, 50)

    node = scistyle.box(ax, 10, 10, 60, 20, "Reports excluded:\nnot randomized (n = 110)", align="left")

    assert node.text.get_ha() == "left"
    assert 10 < node.text.get_position()[0] < 13  # just inside the left side of the frame
    scistyle.save(fig, tmp_path / "left", formats=("png",))


def test_connect_draws_through_its_points_and_ends_in_a_head(tmp_path):
    scistyle.use("elsevier")
    fig, ax = scistyle.canvas(100, 50)

    scistyle.connect(ax, (10, 40), (50, 40), (50, 10))  # right, then down: an elbow

    (path,) = scistyle.save(fig, tmp_path / "elbow", formats=("png",), dpi=254)
    with Image.open(path) as png:
        page = png.convert("L")
        assert dark(page, 30, 40, 10, 50) and dark(page, 50, 25, 10, 50)  # both legs
        assert not dark(page, 30, 25, 10, 50)  # no diagonal
        head = page.crop((485, 370, 516, 400))  # the 3 mm above the end point (50, 10)
        plain = page.crop((485, 200, 516, 230))  # the same strip higher up the leg
        assert sum(value < 128 for value in head.tobytes()) > 2 * sum(value < 128 for value in plain.tobytes())


@pytest.mark.parametrize("head, wider", [("bar", True), ("none", False)])
def test_connect_can_end_in_a_bar_or_in_nothing(tmp_path, head, wider):
    scistyle.use("elsevier")
    fig, ax = scistyle.canvas(100, 50)

    scistyle.connect(ax, (10, 25), (60, 25), head=head)

    (path,) = scistyle.save(fig, tmp_path / head, formats=("png",), dpi=254)
    with Image.open(path) as png:
        page = png.convert("L")
        assert dark(page, 35, 25, 10, 50)
        # A bar stands 1 mm before the end point. Just above and below the line there:
        end = [dark(page, 59, 25 + offset, 10, 50) for offset in (0.6, -0.6)]
        assert all(end) == wider and any(end) == wider
        # A bar is a short stroke, about 3 mm across: it must not reach 2.5 mm to either side.
        assert not dark(page, 59, 25 + 2.5, 10, 50) and not dark(page, 59, 25 - 2.5, 10, 50)


def test_a_bar_stands_clear_of_the_box_it_points_at(tmp_path):
    # Drawn on the frame itself, the bar vanishes into it and "inhibits" reads as a plain line.
    scistyle.use("elsevier")
    fig, ax = scistyle.canvas(100, 50)
    target = scistyle.box(ax, 60, 15, 30, 20, "Growth")

    scistyle.connect(ax, (10, 25), target.left, head="bar")

    (path,) = scistyle.save(fig, tmp_path / "inhibits", formats=("png",), dpi=254)  # 10 px per mm
    with Image.open(path) as png:
        page = png.convert("L")
        assert dark(page, 59, 26, 10, 50) and dark(page, 59, 24, 10, 50)  # the bar, 1 mm in front of the frame
        for y in (24, 25, 26):  # white between the bar and the frame: the line stops at the bar
            assert not dark(page, 59.5, y, 10, 50), y


def test_connect_rejects_an_unknown_head():
    scistyle.use("elsevier")
    _, ax = scistyle.canvas(100, 50)
    with pytest.raises(ValueError, match="arrow, bar, none"):
        scistyle.connect(ax, (0, 0), (10, 10), head="circle")


def test_use_can_set_the_font_size_for_a_document_that_is_not_a_journal():
    scistyle.use("default", font_pt=10.5)

    assert matplotlib.rcParams["font.size"] == 10.5
    assert matplotlib.rcParams["axes.labelsize"] == 10.5
    scistyle.use("default")
    assert matplotlib.rcParams["font.size"] == 7


def embedded_fonts(path):
    return set(re.findall(rb"/BaseFont\s*/(?:[A-Z]{6}\+)?([\w-]+)", Path(path).read_bytes()))


def test_use_can_take_the_typefaces_of_a_document_that_is_not_a_journal(tmp_path):
    scistyle.use("default", font_pt=10.5, fonts=["DejaVu Serif"])  # a face that ships with matplotlib
    fig, ax = scistyle.figure(150)
    ax.set_xlabel("Soil organic carbon (g kg$^{-1}$)")

    (path,) = scistyle.save(fig, tmp_path / "thesis", formats=("pdf",))

    assert embedded_fonts(path) == {b"DejaVuSerif"}  # labels, tick labels and the superscript alike


@pytest.mark.skipif(
    not {"Times New Roman", "Songti SC"} <= {font.name for font in matplotlib.font_manager.fontManager.ttflist},
    reason="needs Times New Roman and Songti SC",
)
def test_a_chinese_thesis_gets_its_latin_and_its_chinese_typeface(tmp_path):
    scistyle.use("default", font_pt=10.5, fonts=["Times New Roman", "Songti SC"])
    fig, ax = scistyle.canvas(150, 30)
    scistyle.box(ax, 10, 5, 80, 20, "遥感影像获取（Sentinel-2）")

    (path,) = scistyle.save(fig, tmp_path / "roadmap", formats=("pdf",))

    fonts = embedded_fonts(path)
    assert len(fonts) == 2, fonts
    assert any(b"Times" in name for name in fonts) and any(b"Song" in name for name in fonts), fonts


def test_use_names_a_typeface_that_is_not_installed_and_changes_nothing():
    scistyle.use("nature")
    before = list(matplotlib.rcParams["font.family"])

    with pytest.raises(ValueError, match="not installed: No Such Typeface"):
        scistyle.use("default", fonts=["DejaVu Serif", "No Such Typeface"])

    assert matplotlib.rcParams["font.family"] == before
    assert scistyle.figure("single")[0].get_size_inches()[0] == pytest.approx(88 / 25.4)  # still the Nature column


def test_canvas_can_show_a_millimetre_grid_for_finding_positions(tmp_path):
    scistyle.use("elsevier")
    fig, ax = scistyle.canvas(100, 50, grid_mm=10)

    (path,) = scistyle.save(fig, tmp_path / "grid", formats=("png",), dpi=254)

    with Image.open(path) as png:
        page = png.convert("L")
        assert page.getpixel((300, 255)) < 235 and page.getpixel((455, 300)) < 235  # lines at x = 30 mm and y = 20 mm
        assert page.getpixel((455, 255)) > 250  # white between the lines
    assert {"30", "20"} <= {text.get_text() for text in ax.texts}  # the lines carry their millimetres
