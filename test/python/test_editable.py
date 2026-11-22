"""End-to-end tests for skills/scifig/scripts/editable.py.

Every test runs the script the way a user does (`uv run editable.py ...`) on a synthetic
figure drawn with Pillow, then inspects the PPTX or SVG it wrote.
"""
import base64
import io
import json
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageChops, ImageDraw, ImageFont
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.enum.text import MSO_AUTO_SIZE
from pptx.util import Inches

SCRIPT = Path(__file__).resolve().parents[2] / "skills" / "scifig" / "scripts" / "editable.py"
UV = shutil.which("uv") or "uv"
SVG = "{http://www.w3.org/2000/svg}"
XLINK = "{http://www.w3.org/1999/xlink}"
REPORT_KEYS = {
    "output", "mode", "size", "text_items", "labels", "skipped_low_confidence", "skipped_rotated", "warnings",
}

W, H = 1600, 900
FONT_PX = 64
OUTLINE = (60, 60, 60)
# label -> (rounded box, box fill, text colour), listed in reading order
BOXES = {
    "Nucleus": ((180, 80, 700, 300), (207, 226, 243), (31, 58, 95)),
    "Mitochondria": ((980, 80, 1500, 300), (252, 229, 205), (122, 31, 31)),
    "Golgi": ((180, 520, 700, 740), (217, 234, 211), (0, 0, 0)),
    "Ribosome": ((980, 520, 1500, 740), (69, 90, 120), (255, 255, 255)),
}
CAPTION, CAPTION_PX = "Threshold", 40  # a label sitting just above a dashed line
TILTED, VERTICAL = "Cytosol", "Relative viability"  # rotated by 45 and by 90 degrees
NEIGHBOUR = "ATP"  # a horizontal label so close to the vertical one that their OCR boxes overlap
BLUE, ORANGE = (0, 120, 200), (200, 120, 0)  # two crossing lines, 2 px wide


def load_font(size):
    for path in ("/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def draw_label(img, centre, text, font, colour):
    """Draw `text` centred on `centre`; return its true geometry.

    {"x": where the text starts, "baseline": y, "ink": the box of the pixels it actually covers}
    """
    left, top, right, bottom = font.getbbox(text, anchor="ls")
    x, baseline = round(centre[0] - (left + right) / 2), round(centre[1] - (top + bottom) / 2)
    ImageDraw.Draw(img).text((x, baseline), text, font=font, fill=colour, anchor="ls")
    stencil = Image.new("L", img.size, 0)
    ImageDraw.Draw(stencil).text((x, baseline), text, font=font, fill=255, anchor="ls")
    return {"x": x, "baseline": baseline, "ink": stencil.getbbox()}


def paste_rotated(img, centre, text, font, angle):
    """Paste `text` rotated by `angle` degrees around `centre`; return the box of the pixels it covers."""
    left, top, right, bottom = font.getbbox(text)
    layer = Image.new("RGBA", (right + 20, bottom + 20), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((10, 10), text, font=font, fill=(40, 40, 40, 255))
    layer = layer.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
    x, y = centre[0] - layer.width // 2, centre[1] - layer.height // 2
    img.paste(layer, (x, y), layer)
    left, top, right, bottom = layer.getbbox()
    return (x + left, y + top, x + right, y + bottom)


def draw_arrow(draw, start, end):
    """Draw a horizontal or vertical arrow from `start` to `end`."""
    draw.line([start, end], fill=OUTLINE, width=8)
    (x0, y0), (x1, y1) = start, end
    if y0 == y1:
        back = x1 - 26 if x1 > x0 else x1 + 26
        draw.polygon([(x1, y1), (back, y1 - 13), (back, y1 + 13)], fill=OUTLINE)
    else:
        back = y1 - 26 if y1 > y0 else y1 + 26
        draw.polygon([(x1, y1), (x1 - 13, back), (x1 + 13, back)], fill=OUTLINE)


def make_figure(path):
    """Four labelled boxes joined by arrows, a caption on a dashed line, two rotated labels (one
    with a close neighbour) and two thin crossing lines. Returns {label: true geometry}; rotated
    labels only have "ink".
    """
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    font = load_font(FONT_PX)
    truth = {}
    for label, (rect, fill, colour) in BOXES.items():
        draw.rounded_rectangle(rect, radius=36, fill=fill, outline=OUTLINE, width=4)
        truth[label] = draw_label(img, ((rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2), label, font, colour)
    draw_arrow(draw, (700, 190), (972, 190))
    draw_arrow(draw, (1240, 300), (1240, 512))
    draw_arrow(draw, (980, 630), (708, 630))

    truth[CAPTION] = draw_label(img, (440, 395), CAPTION, load_font(CAPTION_PX), (20, 20, 20))
    dash_top = truth[CAPTION]["baseline"] + 9  # close enough to count as the caption's surround
    for x in range(200, 680, 24):
        draw.rectangle((x, dash_top, x + 12, dash_top + 2), fill=OUTLINE)
    truth[TILTED] = {"ink": paste_rotated(img, (840, 410), TILTED, font, 45)}
    small = load_font(44)
    truth[VERTICAL] = {"ink": paste_rotated(img, (70, 400), VERTICAL, small, 90)}
    cap_height = -small.getbbox(NEIGHBOUR, anchor="ls")[1]  # its strokes start 10 px below the vertical label
    truth[NEIGHBOUR] = draw_label(img, (70, truth[VERTICAL]["ink"][3] + 10 + cap_height / 2), NEIGHBOUR, small, (0, 0, 0))
    draw.line([(200, 790), (1400, 860)], fill=BLUE, width=2)
    draw.line([(200, 860), (1400, 790)], fill=ORANGE, width=2)
    img.save(path)
    return truth


def run_cli(*args, **kwargs):
    """Run the script through uv; the long timeout covers the first run building its environment."""
    return subprocess.run(
        [UV, "run", "--quiet", str(SCRIPT), *map(str, args)],
        capture_output=True, text=True, timeout=1800, **kwargs,
    )


def convert(src, out, mode, *extra):
    """Convert `src` and return the parsed --json report."""
    proc = run_cli(src, "--to", mode, "-o", out, "--json", *extra)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def svg_root(path):
    return ET.parse(path).getroot()


def svg_texts(path):
    """The <text> elements inside <g id="labels">, in document order."""
    groups = [g for g in svg_root(path).iter(f"{SVG}g") if g.get("id") == "labels"]
    return [t for g in groups for t in g.iter(f"{SVG}text")]


def embedded_picture(path):
    """Decode the single embedded <image> of an svg-text output."""
    (image,) = svg_root(path).iter(f"{SVG}image")
    href = image.get(f"{XLINK}href") or image.get("href")
    assert href.startswith("data:image/png;base64,")
    return Image.open(io.BytesIO(base64.b64decode(href.split(",", 1)[1]))).convert("RGB")


def same_pixels(a, b):
    return ImageChops.difference(a, b).getbbox() is None


def channel_spread(img, colour):
    """Largest per-channel distance between any pixel of `img` and `colour`."""
    diff = ImageChops.difference(img, Image.new("RGB", img.size, colour))
    return max(high for _, high in diff.getextrema())


def hex_rgb(text):
    return tuple(int(text[i:i + 2], 16) for i in (1, 3, 5))


def close(a, b, tolerance):
    return all(abs(x - y) <= tolerance for x, y in zip(a, b))


def grown(box, pad):
    return (box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad)


@pytest.fixture(scope="module")
def figure(tmp_path_factory):
    path = tmp_path_factory.mktemp("figure") / "figure.png"
    return path, make_figure(path)


@pytest.fixture(scope="module")
def pptx_out(figure, tmp_path_factory):
    out = tmp_path_factory.mktemp("pptx") / "figure.pptx"
    return out, convert(figure[0], out, "pptx")


@pytest.fixture(scope="module")
def svg_text_out(figure, tmp_path_factory):
    out = tmp_path_factory.mktemp("svg-text") / "figure.svg"
    return out, convert(figure[0], out, "svg-text")


@pytest.fixture(scope="module")
def svg_vector_out(figure, tmp_path_factory):
    out = tmp_path_factory.mktemp("svg-vector") / "figure.svg"
    return out, convert(figure[0], out, "svg-vector")


def test_pptx_has_one_slide_with_picture_and_label_text_boxes(figure, pptx_out):
    truth = figure[1]
    prs = Presentation(str(pptx_out[0]))
    assert len(prs.slides) == 1
    assert abs(prs.slide_width - Inches(13.333)) <= Inches(0.001)
    assert abs(prs.slide_width / prs.slide_height - W / H) <= 0.01 * W / H

    shapes = list(prs.slides[0].shapes)
    (picture,) = [s for s in shapes if s.shape_type == MSO_SHAPE_TYPE.PICTURE]
    assert shapes[0].shape_type == MSO_SHAPE_TYPE.PICTURE  # at the back, under the text boxes
    assert (picture.left, picture.top) == (0, 0)
    assert (picture.width, picture.height) == (prs.slide_width, prs.slide_height)
    assert Image.open(io.BytesIO(picture.image.blob)).size == (W, H)

    boxes = [s for s in shapes if s.shape_type == MSO_SHAPE_TYPE.TEXT_BOX]
    assert len(boxes) == len(shapes) - 1
    texts = [s.text_frame.text for s in boxes]
    matched = [label for label in BOXES if label in texts]
    assert len(matched) >= 3, texts
    assert [t for t in texts if t in BOXES] == matched  # top to bottom, then left to right
    assert set(texts) <= {*BOXES, CAPTION}  # nothing from the rotated labels or their neighbour
    emu = prs.slide_width / W
    for label in matched:
        box = boxes[texts.index(label)]
        left, top, right, bottom = truth[label]["ink"]
        assert abs((box.left + box.width / 2) / prs.slide_width - (left + right) / 2 / W) <= 0.05, label
        assert abs((box.top + box.height / 2) / prs.slide_height - (top + bottom) / 2 / H) <= 0.05, label
        # The box starts where the text starts and holds all of it, with only a little to spare.
        assert abs(box.left / emu - truth[label]["x"]) <= 0.06 * FONT_PX, label
        assert right <= (box.left + box.width) / emu <= right + 1.5 * FONT_PX, label
        assert box.top / emu <= top and bottom <= (box.top + box.height) / emu, label


def test_pptx_text_boxes_are_unwrapped_arial_in_the_label_colour(pptx_out):
    prs = Presentation(str(pptx_out[0]))
    boxes = {s.text_frame.text: s for s in prs.slides[0].shapes if s.shape_type == MSO_SHAPE_TYPE.TEXT_BOX}
    matched = [label for label in BOXES if label in boxes]
    assert len(matched) >= 3
    expected_pt = FONT_PX * (prs.slide_width / W) / 12700  # 12700 EMU per point
    for label in matched:
        frame = boxes[label].text_frame
        assert (frame.margin_left, frame.margin_right, frame.margin_top, frame.margin_bottom) == (0, 0, 0, 0)
        assert frame.word_wrap is False
        assert frame.auto_size == MSO_AUTO_SIZE.NONE
        (paragraph,) = frame.paragraphs
        (run,) = paragraph.runs
        assert run.font.name == "Arial"
        assert abs(run.font.size.pt - expected_pt) <= 0.1 * expected_pt, (label, run.font.size.pt)
        assert close(run.font.color.rgb, BOXES[label][2], 12), (label, run.font.color.rgb)


def test_svg_text_embeds_the_picture_and_editable_labels(figure, svg_text_out):
    truth = figure[1]
    root = svg_root(svg_text_out[0])
    assert root.tag == f"{SVG}svg"
    assert root.get("viewBox") == f"0 0 {W} {H}"
    assert (root.get("width"), root.get("height")) == (str(W), str(H))
    assert len(list(root.iter(f"{SVG}image"))) == 1
    assert embedded_picture(svg_text_out[0]).size == (W, H)

    texts = {t.text: t for t in svg_texts(svg_text_out[0])}
    matched = [label for label in BOXES if label in texts]
    assert len(matched) >= 3, list(texts)
    assert [t for t in texts if t in BOXES] == matched
    assert set(texts) <= {*BOXES, CAPTION}
    for label in matched:
        text = texts[label]
        assert text.get("font-family") == "Arial, Helvetica, sans-serif"
        assert abs(float(text.get("font-size")) - FONT_PX) <= 0.1 * FONT_PX, label
        assert abs(float(text.get("x")) - truth[label]["x"]) <= 0.06 * FONT_PX, label
        assert abs(float(text.get("y")) - truth[label]["baseline"]) <= 0.08 * FONT_PX, label
        assert re.fullmatch("#[0-9a-f]{6}", text.get("fill"))
        assert close(hex_rgb(text.get("fill")), BOXES[label][2], 12), (label, text.get("fill"))


def test_svg_vector_traces_the_picture_into_paths(svg_text_out, svg_vector_out):
    root = svg_root(svg_vector_out[0])
    assert root.get("viewBox") == f"0 0 {W} {H}"
    assert list(root.iter(f"{SVG}image")) == []
    groups = {g.get("id"): g for g in root.iter(f"{SVG}g")}
    assert list(groups) == ["artwork", "labels"]  # labels come last so they paint over the artwork
    paths = list(groups["artwork"].iter(f"{SVG}path"))
    assert len(paths) >= 10
    assert len(list(root.iter(f"{SVG}path"))) == len(paths)

    fills = [hex_rgb(p.get("fill")) for p in paths]
    for label, (_, fill, _) in BOXES.items():
        assert any(close(f, fill, 4) for f in fills), label  # every box keeps its flat colour
    # Each 2 px line survives in its own colour (traced at the picture's own size they merge into grey).
    assert any(f[2] - f[0] >= 80 for f in fills), "the blue line is missing"
    assert any(f[0] - f[2] >= 80 for f in fills), "the orange line is missing"

    def labels(path):
        return [(t.text, t.get("x"), t.get("y"), t.get("font-size"), t.get("fill")) for t in svg_texts(path)]

    assert labels(svg_vector_out[0]) == labels(svg_text_out[0])  # same labels in the same pixel coordinates
    assert len([label for label in BOXES if label in dict.fromkeys(t[0] for t in labels(svg_vector_out[0]))]) >= 3


def test_erased_labels_leave_only_the_box_fill(figure, svg_text_out):
    src, truth = figure
    before = Image.open(src).convert("RGB")
    after = embedded_picture(svg_text_out[0])
    assert after.size == before.size
    texts = [t.text for t in svg_texts(svg_text_out[0])]
    erased = [label for label in BOXES if label in texts]
    assert len(erased) >= 3
    for label in erased:
        assert channel_spread(after.crop(truth[label]["ink"]), BOXES[label][1]) <= 2, label

    # Away from the erased labels nothing changed: outlines, arrows, lines and rotated labels survive.
    untouched_before, untouched_after = before.copy(), after.copy()
    for label in [label for label in (*BOXES, CAPTION) if label in texts]:
        for img in (untouched_before, untouched_after):
            img.paste((0, 0, 0), grown(truth[label]["ink"], FONT_PX // 2))
    assert same_pixels(untouched_before, untouched_after)


def test_caption_on_a_dashed_line_is_measured_and_erased_cleanly(figure, svg_text_out):
    truth = figure[1][CAPTION]
    texts = {t.text: t for t in svg_texts(svg_text_out[0])}
    assert CAPTION in texts, list(texts)
    text = texts[CAPTION]
    assert abs(float(text.get("font-size")) - CAPTION_PX) <= 0.1 * CAPTION_PX  # the dashes are not taken for strokes
    assert abs(float(text.get("y")) - truth["baseline"]) <= 0.08 * CAPTION_PX
    # The dashes do not smear into the erased box: it is plain white.
    assert channel_spread(embedded_picture(svg_text_out[0]).crop(truth["ink"]), (255, 255, 255)) <= 2


def test_rotated_labels_are_skipped_and_stay_in_the_picture(figure, svg_text_out):
    src, truth = figure
    out, report = svg_text_out
    assert report["skipped_rotated"] >= 3
    assert NEIGHBOUR not in [t.text for t in svg_texts(out)]  # its box runs into the vertical label's
    before, after = Image.open(src).convert("RGB"), embedded_picture(out)
    for label in (TILTED, VERTICAL, NEIGHBOUR):
        box = grown(truth[label]["ink"], 3)
        assert channel_spread(before.crop(box), (255, 255, 255)) > 200  # the crop really holds the dark label
        assert same_pixels(before.crop(box), after.crop(box)), label


def test_json_report_is_the_only_stdout(figure, tmp_path):
    out = tmp_path / "report.svg"
    proc = run_cli(figure[0], "--to", "svg-text", "-o", out, "--json")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.startswith("{") and proc.stdout.count("\n") == 1
    report = json.loads(proc.stdout)
    assert set(report) == REPORT_KEYS
    assert Path(report["output"]).samefile(out)
    assert report["mode"] == "svg-text"
    assert report["size"] == [W, H]
    assert report["text_items"] == len(svg_texts(out)) >= 3
    assert report["skipped_low_confidence"] >= 0
    skipped = report["skipped_low_confidence"] + report["skipped_rotated"]
    # The only possible warning here: more than a quarter of the OCR items were skipped.
    assert len(report["warnings"]) == int(4 * skipped > report["text_items"] + skipped)
    assert all(isinstance(warning, str) for warning in report["warnings"])


def test_default_output_is_next_to_the_input(figure, tmp_path):
    src = tmp_path / "in" / "my figure.png"
    src.parent.mkdir()
    shutil.copy(figure[0], src)
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    proc = run_cli(src, "--to", "pptx", "--no-text", cwd=cwd)
    assert proc.returncode == 0, proc.stderr
    assert sorted(p.name for p in src.parent.iterdir()) == ["my figure.png", "my figure.pptx"]
    assert list(cwd.iterdir()) == []
    assert "my figure.pptx" in proc.stdout and not proc.stdout.startswith("{")
    shapes = Presentation(str(src.with_suffix(".pptx"))).slides[0].shapes
    assert [s.shape_type for s in shapes] == [MSO_SHAPE_TYPE.PICTURE]  # --no-text: picture only


def test_the_report_prints_through_a_pipe_whose_code_page_lacks_its_characters(figure, tmp_path):
    """On Windows a pipe takes the ANSI code page, cp1252 in the West: no Chinese, ₂, ↑ or κ."""
    out = tmp_path / "图 1.pptx"
    env = {**os.environ, "PYTHONIOENCODING": "cp1252"}
    proc = run_cli(figure[0], "--to", "pptx", "--no-text", "-o", out, env=env, encoding="utf-8")
    assert proc.returncode == 0, proc.stderr
    assert "图 1.pptx" in proc.stdout.splitlines()[0]


def test_writes_nothing_but_the_output(figure, tmp_path):
    """onnxruntime would keep a telemetry database and device id under the home directory."""
    home, out_dir = tmp_path / "home", tmp_path / "out"
    home.mkdir()
    out_dir.mkdir()

    def uv_dir(kind):
        return subprocess.run([UV, kind, "dir"], capture_output=True, text=True, check=True).stdout.strip()

    env = {
        **os.environ, "HOME": str(home),
        "XDG_CACHE_HOME": str(home / "cache"), "XDG_DATA_HOME": str(home / "data"), "XDG_CONFIG_HOME": str(home / "config"),
        "UV_CACHE_DIR": uv_dir("cache"), "UV_PYTHON_INSTALL_DIR": uv_dir("python"),  # uv itself stays where it is
    }
    env.pop("ORT_DISABLE_TELEMETRY", None)
    proc = run_cli(figure[0], "--to", "pptx", "-o", out_dir / "figure.pptx", env=env)
    assert proc.returncode == 0, proc.stderr
    assert list(home.iterdir()) == []
    assert [p.name for p in out_dir.iterdir()] == ["figure.pptx"]


def test_no_text_svg_vector_is_a_pure_trace(figure, tmp_path):
    out = tmp_path / "trace.svg"
    report = convert(figure[0], out, "svg-vector", "--no-text")
    root = svg_root(out)
    assert len(list(root.iter(f"{SVG}path"))) >= 10
    assert list(root.iter(f"{SVG}text")) == []
    assert list(root.iter(f"{SVG}image")) == []
    assert (report["text_items"], report["skipped_low_confidence"], report["skipped_rotated"]) == (0, 0, 0)
    assert report["warnings"] == []  # no OCR was asked for, so finding no text is not worth a warning


def test_no_text_with_svg_text_is_a_usage_error(figure, tmp_path):
    out = tmp_path / "nothing.svg"
    proc = run_cli(figure[0], "--to", "svg-text", "--no-text", "-o", out)
    assert proc.returncode == 2
    assert "--no-text" in proc.stderr
    assert proc.stdout == ""
    assert not out.exists()


def test_refuses_to_overwrite_the_input(figure, tmp_path):
    src = tmp_path / "figure.png"
    shutil.copy(figure[0], src)
    original = src.read_bytes()
    proc = run_cli(src, "--to", "svg-text", "-o", tmp_path / "." / "figure.png")
    assert proc.returncode == 1
    assert len(proc.stderr.strip().splitlines()) == 1
    assert src.read_bytes() == original


def test_missing_input_fails_with_a_one_line_message(tmp_path):
    proc = run_cli(tmp_path / "absent.png", "--to", "pptx", "--json")
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert len(proc.stderr.strip().splitlines()) == 1
    assert "absent.png" in proc.stderr


def test_min_confidence_leaves_unsure_text_in_the_picture(figure, tmp_path):
    out = tmp_path / "strict.svg"
    report = convert(figure[0], out, "svg-text", "--min-confidence", "1.01")
    assert report["text_items"] == 0
    assert report["skipped_low_confidence"] >= 3
    assert svg_texts(out) == []
    assert same_pixels(Image.open(figure[0]).convert("RGB"), embedded_picture(out))
    assert len(report["warnings"]) == 2  # no text items at all, and more than a quarter skipped


def test_text_on_a_gradient_is_inpainted(tmp_path):
    width, height = 900, 300
    src = tmp_path / "gradient.png"
    plain = Image.new("RGB", (width, height))
    plain.putdata([(255 - x // 10, 235 - x // 30, 190 + x // 14) for _ in range(height) for x in range(width)])
    img = plain.copy()
    truth = draw_label(img, (width / 2, height / 2), "Cytoplasm", load_font(56), (30, 30, 30))
    img.save(src)

    out = tmp_path / "gradient.svg"
    report = convert(src, out, "svg-text")
    assert [t.text for t in svg_texts(out)] == ["Cytoplasm"]
    assert (report["text_items"], report["warnings"]) == (1, [])
    after = embedded_picture(out)
    # The gradient is continued across the erased box instead of being replaced by one flat colour.
    difference = ImageChops.difference(after, plain).crop(grown(truth["ink"], 28))
    assert max(high for _, high in difference.getextrema()) <= 6
    for picture in (img, after):
        picture.paste((0, 0, 0), grown(truth["ink"], 28))
    assert same_pixels(img, after)


def test_grey_text_beside_a_darker_line_is_measured_on_its_own_strokes(tmp_path):
    """A rule, a box outline or a vertical line far darker than the text, inside its OCR box,
    used to set the threshold for ink: the text fell below it and only the line was measured."""
    grey, black, size = (150, 150, 150), (0, 0, 0), 34
    font = load_font(size)
    img = Image.new("RGB", (1600, 600), "white")
    draw = ImageDraw.Draw(img)
    truth = {
        label: draw_label(img, centre, label, font, grey)
        for label, centre in (("Feature extraction", (450, 150)), ("Classifier", (1150, 150)), ("Evaluation", (800, 420)))
    }
    rule = truth["Feature extraction"]["baseline"] + 4  # a 2 px rule just under the text
    draw.rectangle((200, rule, 700, rule + 1), fill=black)
    outline = truth["Classifier"]["baseline"] + 6  # the bottom of a box outline just under the text
    draw.rounded_rectangle((950, 60, 1350, outline), radius=12, outline=(20, 20, 20), width=3)
    left, top, _, bottom = truth["Evaluation"]["ink"]  # a vertical line just left of the text
    draw.rectangle((left - 6, top - 12, left - 4, bottom + 12), fill=black)
    src = tmp_path / "lines.png"
    img.save(src)

    out = tmp_path / "lines.svg"
    convert(src, out, "svg-text")
    texts = {t.text: t for t in svg_texts(out)}
    assert set(truth) <= set(texts), list(texts)
    for label, geometry in truth.items():
        text = texts[label]
        assert abs(float(text.get("font-size")) - size) <= 0.1 * size, (label, text.get("font-size"))
        assert abs(float(text.get("x")) - geometry["x"]) <= 0.06 * size, (label, text.get("x"))
        assert abs(float(text.get("y")) - geometry["baseline"]) <= 0.08 * size, (label, text.get("y"))
        assert close(hex_rgb(text.get("fill")), grey, 12), (label, text.get("fill"))


def test_a_label_measured_too_small_for_powerpoint_still_converts(tmp_path):
    """python-pptx takes font sizes from 1 to 4000 pt only. Text this faint is not told apart
    from the black rule under it, so the 2 px rule alone is measured: under 1 pt on a slide
    that a picture 3200 px wide fills. The label comes out at 1 pt instead of stopping the slide."""
    img = Image.new("RGB", (3200, 400), "white")
    truth = draw_label(img, (1600, 180), "Feature extraction", load_font(60), (235, 235, 235))
    ImageDraw.Draw(img).rectangle((1000, truth["baseline"] + 4, 2200, truth["baseline"] + 5), fill=(0, 0, 0))
    src = tmp_path / "wide.png"
    img.save(src)

    out = tmp_path / "wide.pptx"
    convert(src, out, "pptx")
    boxes = [s for s in Presentation(str(out)).slides[0].shapes if s.shape_type == MSO_SHAPE_TYPE.TEXT_BOX]
    assert [box.text_frame.text for box in boxes] == ["Feature extraction"]
    assert boxes[0].text_frame.paragraphs[0].runs[0].font.size.pt == 1


def test_large_text_is_erased_to_the_last_fringe(tmp_path):
    """OCR boxes hug large text: only the grown mask reaches the outermost stroke pixels."""
    fill = (207, 226, 243)
    src = tmp_path / "large.png"
    img = Image.new("RGB", (W, H), fill)
    truths = [
        draw_label(img, (420, 200), "Mitochondria", load_font(110), (31, 58, 95)),
        draw_label(img, (1100, 450), "Nucleus", load_font(110), (31, 58, 95)),
    ]
    img.save(src)
    out = tmp_path / "large.svg"
    convert(src, out, "svg-text")
    assert sorted(t.text for t in svg_texts(out)) == ["Mitochondria", "Nucleus"]
    after = embedded_picture(out)
    for truth in truths:
        assert channel_spread(after.crop(grown(truth["ink"], 4)), fill) <= 2


@pytest.mark.parametrize("suffix", [".jpg", ".webp"])
def test_reads_jpeg_and_webp(figure, tmp_path, suffix):
    src = tmp_path / f"figure{suffix}"
    Image.open(figure[0]).save(src, quality=90)
    out = tmp_path / "figure.pptx"
    report = convert(src, out, "pptx", "--no-text")
    assert report["size"] == [W, H]
    (picture,) = Presentation(str(out)).slides[0].shapes
    assert Image.open(io.BytesIO(picture.image.blob)).size == (W, H)


def test_transparent_background_is_flattened_onto_white(tmp_path):
    src = tmp_path / "transparent.png"
    img = Image.new("RGBA", (320, 200), (0, 0, 0, 0))
    ImageDraw.Draw(img).rectangle((100, 60, 220, 140), fill=(200, 30, 30, 255))
    img.save(src)
    out = tmp_path / "transparent.pptx"
    convert(src, out, "pptx", "--no-text")
    (picture,) = Presentation(str(out)).slides[0].shapes
    flat = Image.open(io.BytesIO(picture.image.blob)).convert("RGB")
    assert flat.getpixel((10, 10)) == (255, 255, 255)
    assert flat.getpixel((160, 100)) == (200, 30, 30)


@pytest.mark.parametrize("suffix, byte_order", [(".png", "<u2"), (".tif", "<u2"), (".tif", ">u2")])  # ImageJ writes big-endian TIFFs
def test_a_16_bit_greyscale_image_is_reduced_to_8_bit_not_turned_white(tmp_path, suffix, byte_order):
    ramp = np.tile(np.linspace(0, 65535, 600).astype(np.uint16), (100, 1))
    src = tmp_path / f"ramp{suffix}"
    Image.fromarray(ramp.astype(byte_order)).save(src)
    out = tmp_path / "ramp.pptx"
    convert(src, out, "pptx", "--no-text")
    (picture,) = Presentation(str(out)).slides[0].shapes
    with Image.open(src) as original:
        assert original.mode.startswith("I;16")
    grey = np.asarray(Image.open(io.BytesIO(picture.image.blob)).convert("RGB"))
    assert (grey == (ramp >> 8)[:, :, np.newaxis]).all()


def test_report_lists_every_label_with_its_text_and_size_for_proofreading(figure, tmp_path):
    out = tmp_path / "labels.svg"
    report = convert(figure[0], out, "svg-text")
    texts = svg_texts(out)
    assert [label["text"] for label in report["labels"]] == [text.text for text in texts]  # same reading order
    assert [label["font_px"] for label in report["labels"]] == [float(text.get("font-size")) for text in texts]
    assert len(report["labels"]) == report["text_items"]
    sizes = {label["text"]: label["font_px"] for label in report["labels"]}
    for label in BOXES:
        assert abs(sizes[label] - FONT_PX) <= 0.1 * FONT_PX, label

    proc = run_cli(figure[0], "--to", "svg-text", "-o", tmp_path / "again.svg")
    assert proc.returncode == 0, proc.stderr
    for label in report["labels"]:
        assert f'label "{label["text"]}", {label["font_px"]:g} px' in proc.stdout
