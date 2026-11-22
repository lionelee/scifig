"""Tests for skills/scifig/scripts/export_figure.py, run as a CLI through uv."""
import json
import os
import re
import shutil
import subprocess
import sys
import zlib
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageCms, ImageDraw

SCRIPTS = Path(__file__).resolve().parents[2] / "skills" / "scifig" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import journals  # noqa: E402

SCRIPT = SCRIPTS / "export_figure.py"
UV = os.environ.get("UV", "uv")
BLUE = (0, 114, 178)
REPORT_KEYS = ["output", "format", "pixels", "dpi", "physical_mm", "upscaled", "scale", "notes"]


def run(*args, cwd):
    return subprocess.run(
        [UV, "run", "--quiet", str(SCRIPT), *map(str, args)], cwd=cwd, capture_output=True, text=True
    )


def export(*args, cwd):
    """Run with --json, expect success and return the parsed report."""
    proc = run(*args, "--json", cwd=cwd)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def flat(path, size, mode="RGB", colour=BLUE, **save_kwargs):
    Image.new(mode, size, colour).save(path, **save_kwargs)
    return path


def chart(path, size):
    """A small chart-like picture: thin coloured lines and filled bars on white."""
    image = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(image)
    width, height = size
    for i, colour in enumerate(["#0072B2", "#D55E00", "#009E73", "#CC79A7"]):
        draw.line([(10, 20 + 30 * i), (width - 10, height - 120 + 25 * i)], fill=colour, width=2)
        draw.rectangle([40 + 90 * i, height - 70, 100 + 90 * i, height - 15], fill=colour)
    image.save(path)
    return path


def translucent(path, size):
    """RGBA thirds: fully transparent red, half-transparent blue, opaque blue."""
    width, height = size
    image = Image.new("RGBA", size, (255, 0, 0, 0))
    image.paste((0, 0, 255, 128), (width // 3, 0, 2 * width // 3, height))
    image.paste((0, 0, 255, 255), (2 * width // 3, 0, width, height))
    image.save(path)
    return path


def thirds(image):
    """The pixel at the centre of each third of the image, left to right."""
    return [image.getpixel((image.width * k // 6, image.height // 2)) for k in (1, 3, 5)]


def pdf_page_points(path):
    box = re.search(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]", Path(path).read_bytes())
    return float(box[1]), float(box[2])


def pdf_objects(path):
    """{number: body} of the objects of a PDF, found through its cross-reference table."""
    data = Path(path).read_bytes()
    assert data.startswith(b"%PDF-1.4\n")
    start = int(re.search(rb"startxref\n(\d+)\n%%EOF\n$", data)[1])
    count = int(re.match(rb"xref\n0 (\d+)\n", data[start:])[1])
    table = data[start:].split(b"\n", 2)[2]
    entries = [table[20 * i : 20 * i + 20] for i in range(count)]
    assert entries[0] == b"0000000000 65535 f \n"
    objects = {}
    for number, entry in enumerate(entries[1:], start=1):
        assert re.fullmatch(rb"\d{10} 00000 n \n", entry), entry
        offset, head = int(entry[:10]), b"%d 0 obj\n" % number
        assert data[offset : offset + len(head)] == head, number
        objects[number] = data[offset + len(head) : data.index(b"\nendobj\n", offset)]
    assert table[20 * count :].startswith(b"trailer\n<< /Size %d /Root 1 0 R >>\n" % count)
    return objects


def pdf_picture(path):
    """The picture a PDF shows, rebuilt from its only image stream."""
    (body,) = [body for body in pdf_objects(path).values() if b"/Subtype /Image" in body]
    dictionary, stream = body.split(b"stream\n", 1)

    def field(name):
        return re.search(rb"/%s /?(\w+)" % name, dictionary)[1]

    length = int(field(b"Length"))
    assert stream[length:] == b"\nendstream"
    assert field(b"Filter") == b"FlateDecode"
    assert field(b"BitsPerComponent") == b"8"
    mode = {b"DeviceRGB": "RGB", b"DeviceGray": "L"}[field(b"ColorSpace")]
    return Image.frombytes(mode, (int(field(b"Width")), int(field(b"Height"))), zlib.decompress(stream[:length]))


# --- sized mode: --column / --width-mm ----------------------------------------------------------


def test_a_narrow_image_is_upscaled_to_the_column_width_as_an_lzw_tiff(tmp_path):
    source = flat(tmp_path / "fig.png", (1000, 600))

    report = export(source, "-f", "tiff", "--column", "single", "--journal", "nature", "--dpi", 600, cwd=tmp_path)

    target = journals.pixels_for(88, 600)  # Nature's single column
    assert target == 2079
    assert list(report) == REPORT_KEYS
    assert Path(report["output"]) == tmp_path / "fig_600dpi.tiff"
    assert report["format"] == "tiff"
    assert report["pixels"] == [target, 1247]
    assert report["dpi"] == pytest.approx(600.1, abs=0.01)  # 2079 px over 88 mm
    assert report["physical_mm"] == pytest.approx([88.0, 52.8], abs=0.05)
    assert report["upscaled"] is True
    assert report["scale"] == pytest.approx(2.079)
    assert any("not detail" in note for note in report["notes"])
    with Image.open(report["output"]) as out:
        assert out.size == (target, 1247)
        assert out.mode == "RGB"
        assert out.info["compression"] == "tiff_lzw"
        assert out.info["dpi"][0] == pytest.approx(600.1, abs=0.03)
        assert out.info["dpi"][1] == pytest.approx(600.1, abs=0.03)


def test_a_wide_image_is_never_downscaled_and_reports_its_higher_dpi(tmp_path):
    source = flat(tmp_path / "fig.png", (4000, 2000))

    report = export(source, "-f", "tiff", "--column", "single", "--journal", "nature", "--dpi", 600, cwd=tmp_path)

    assert report["pixels"] == [4000, 2000]
    assert report["dpi"] == pytest.approx(1154.5, abs=0.01)  # 4000 px over 88 mm
    assert report["physical_mm"] == pytest.approx([88.0, 44.0], abs=0.05)
    assert report["upscaled"] is False
    assert report["scale"] == 1.0
    assert not any("not detail" in note for note in report["notes"])
    with Image.open(report["output"]) as out:
        assert out.size == (4000, 2000)
        assert out.info["dpi"][0] == pytest.approx(1154.5, abs=0.05)


@pytest.mark.parametrize(
    "options, width_mm",
    [
        (["--width-mm", "120"], 120),
        (["--column", "double", "--journal", "science"], 121),
        (["--column", "single"], 89),  # the default journal
    ],
)
def test_the_print_width_comes_from_millimetres_or_the_journal_column(tmp_path, options, width_mm):
    source = flat(tmp_path / "fig.png", (1000, 500))

    report = export(source, "-f", "png", "--dpi", 300, *options, cwd=tmp_path)

    assert report["pixels"][0] == journals.pixels_for(width_mm, 300)
    assert report["physical_mm"][0] == pytest.approx(width_mm, abs=0.05)


def test_upscaling_resamples_with_lanczos(tmp_path):
    source = chart(tmp_path / "fig.png", (500, 300))

    report = export(source, "-f", "tiff", "--dpi", 300, cwd=tmp_path)

    with Image.open(source) as original, Image.open(report["output"]) as out:
        expected = original.resize((1024, 614), Image.Resampling.LANCZOS)
        assert out.size == expected.size
        assert out.tobytes() == expected.tobytes()


# --- preset mode: no width given ----------------------------------------------------------------


def test_preset_mode_keeps_an_image_that_is_large_enough(tmp_path):
    source = chart(tmp_path / "fig.png", (1500, 900))

    report = export(source, "-f", "png", "--dpi", 300, cwd=tmp_path)

    assert report["pixels"] == [1500, 900]
    assert report["dpi"] == 300.0
    assert report["physical_mm"] == pytest.approx([127.0, 76.2], abs=0.05)
    assert report["upscaled"] is False
    with Image.open(source) as original, Image.open(report["output"]) as out:
        assert out.tobytes() == original.tobytes()
        assert out.info["dpi"][0] == pytest.approx(300, abs=0.01)


@pytest.mark.parametrize(
    "size, dpi, expected",
    [
        ((500, 300), 300, (1024, 614)),
        ((500, 300), 600, (2048, 1229)),
        ((500, 300), 601, (4096, 2458)),
        ((300, 500), 300, (614, 1024)),  # the longer side counts, whichever it is
    ],
)
def test_preset_mode_upscales_a_small_image_by_its_longer_side(tmp_path, size, dpi, expected):
    source = flat(tmp_path / "fig.png", size)

    report = export(source, "-f", "tiff", "--dpi", dpi, cwd=tmp_path)

    assert report["pixels"] == list(expected)
    assert report["dpi"] == float(dpi)
    assert report["upscaled"] is True
    assert report["scale"] == pytest.approx(max(expected) / max(size))
    with Image.open(report["output"]) as out:
        assert out.size == expected
        assert out.info["dpi"][0] == pytest.approx(dpi, abs=0.01)


def test_the_default_resolution_is_600_dpi(tmp_path):
    source = flat(tmp_path / "fig.png", (500, 300))

    report = export(source, "-f", "png", cwd=tmp_path)

    assert Path(report["output"]).name == "fig_600dpi.png"
    assert report["pixels"] == [2048, 1229]
    assert report["dpi"] == 600.0


# --- transparency and colour modes --------------------------------------------------------------


def test_tiff_output_flattens_transparency_onto_white(tmp_path):
    source = translucent(tmp_path / "fig.png", (1200, 1100))

    report = export(source, "-f", "tiff", "--dpi", 300, cwd=tmp_path)

    assert any("white" in note for note in report["notes"])
    with Image.open(report["output"]) as out:
        assert out.mode == "RGB"
        clear, half, solid = thirds(out)
        assert clear == (255, 255, 255)
        assert half == pytest.approx((127, 127, 255), abs=1)
        assert solid == (0, 0, 255)


def test_pdf_output_flattens_transparency_onto_white(tmp_path):
    source = translucent(tmp_path / "fig.png", (1200, 1100))

    report = export(source, "-f", "pdf", "--dpi", 300, cwd=tmp_path)

    image = pdf_picture(report["output"])
    assert image.mode == "RGB"
    clear, half, solid = thirds(image)
    assert clear == (255, 255, 255)
    assert half == pytest.approx((127, 127, 255), abs=1)
    assert solid == (0, 0, 255)


def test_an_opaque_alpha_channel_is_dropped_without_a_flattening_note(tmp_path):
    # What matplotlib writes: RGBA with nothing transparent in it.
    source = flat(tmp_path / "fig.png", (1200, 1100), mode="RGBA", colour=(*BLUE, 255))

    report = export(source, "-f", "tiff", "--dpi", 300, cwd=tmp_path)

    assert report["notes"] == []
    with Image.open(report["output"]) as out:
        assert out.mode == "RGB"
        assert out.getpixel((5, 5)) == BLUE


def test_png_output_keeps_the_alpha_channel_even_when_upscaled(tmp_path):
    source = translucent(tmp_path / "fig.png", (600, 540))

    report = export(source, "-f", "png", "--dpi", 300, cwd=tmp_path)

    assert not any("white" in note for note in report["notes"])
    with Image.open(report["output"]) as out:
        assert out.mode == "RGBA"
        assert out.width == 1024
        assert [pixel[3] for pixel in thirds(out)] == [0, 128, 255]


def test_a_palette_image_becomes_rgb_so_that_lanczos_applies(tmp_path):
    source = tmp_path / "fig.png"
    with Image.open(chart(tmp_path / "rgb.png", (500, 300))) as rgb:
        rgb.quantize(8).save(source)

    report = export(source, "-f", "tiff", "--dpi", 300, cwd=tmp_path)

    assert any("P" in note and "RGB" in note for note in report["notes"])
    with Image.open(source) as original, Image.open(report["output"]) as out:
        assert original.mode == "P"
        assert out.mode == "RGB"
        expected = original.convert("RGB").resize((1024, 614), Image.Resampling.LANCZOS)
        assert out.tobytes() == expected.tobytes()


@pytest.mark.parametrize("fmt, mode, corner", [("tiff", "RGB", (255, 255, 255)), ("png", "RGBA", (255, 0, 0, 0))])
def test_palette_transparency_is_treated_as_alpha(tmp_path, fmt, mode, corner):
    image = Image.new("P", (1200, 1100), 0)
    image.putpalette([255, 0, 0, 0, 0, 255])  # index 0 red (made transparent), index 1 blue
    image.paste(1, (600, 0, 1200, 1100))
    image.save(tmp_path / "fig.png", transparency=0)

    report = export(tmp_path / "fig.png", "-f", fmt, "--dpi", 300, cwd=tmp_path)

    with Image.open(report["output"]) as out:
        assert out.mode == mode
        assert out.getpixel((10, 10)) == corner
        assert out.getpixel((1190, 10))[:3] == (0, 0, 255)


def test_cmyk_is_converted_to_rgb_with_a_note_and_without_its_profile(tmp_path):
    source = flat(tmp_path / "fig.tif", (1200, 1100), mode="CMYK", colour=(255, 0, 0, 0), icc_profile=b"a cmyk profile")

    report = export(source, "-f", "tiff", "--dpi", 300, cwd=tmp_path)

    assert any("CMYK to RGB without colour management" in note for note in report["notes"])
    with Image.open(source) as original, Image.open(report["output"]) as out:
        assert original.info["icc_profile"] == b"a cmyk profile"
        assert out.mode == "RGB"
        assert out.getpixel((5, 5)) == (0, 255, 255)
        assert "icc_profile" not in out.info


def test_greyscale_stays_greyscale(tmp_path):
    source = flat(tmp_path / "fig.png", (1200, 1100), mode="L", colour=90)

    report = export(source, "-f", "tiff", "--dpi", 300, cwd=tmp_path)

    assert report["notes"] == []
    with Image.open(report["output"]) as out:
        assert out.mode == "L"
        assert out.getpixel((5, 5)) == 90


def test_a_merely_translucent_image_is_flattened_with_a_note_too(tmp_path):
    source = flat(tmp_path / "fig.png", (1200, 1100), mode="RGBA", colour=(0, 0, 255, 128))

    report = export(source, "-f", "tiff", "--dpi", 300, cwd=tmp_path)

    assert any("white" in note for note in report["notes"])
    with Image.open(report["output"]) as out:
        assert out.getpixel((5, 5)) == pytest.approx((127, 127, 255), abs=1)


def test_an_icc_profile_survives_flattening(tmp_path):
    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    source = flat(tmp_path / "fig.png", (1200, 1100), mode="RGBA", colour=(0, 0, 255, 128), icc_profile=profile)

    report = export(source, "-f", "tiff", "--dpi", 300, cwd=tmp_path)

    with Image.open(report["output"]) as out:
        assert out.mode == "RGB"
        assert out.info["icc_profile"] == profile


@pytest.mark.parametrize("byte_order", ["<u2", ">u2"])  # ImageJ writes big-endian TIFFs
def test_a_16_bit_greyscale_image_is_reduced_to_8_bit_without_clipping(tmp_path, byte_order):
    ramp = np.tile(np.linspace(0, 65535, 1200).astype(np.uint16), (40, 1))
    source = tmp_path / "fig.tif"
    Image.fromarray(ramp.astype(byte_order)).save(source)

    report = export(source, "-f", "tiff", "--dpi", 300, cwd=tmp_path)

    assert any("16-bit" in note for note in report["notes"])
    with Image.open(source) as original, Image.open(report["output"]) as out:
        assert original.mode.startswith("I;16")
        assert out.mode == "L"
        assert (np.asarray(out) == ramp >> 8).all()


def test_a_32_bit_image_is_refused_because_its_display_range_is_unknown(tmp_path):
    source = tmp_path / "fig.tif"
    Image.fromarray(np.full((300, 500), 0.5, dtype=np.float32)).save(source)

    proc = run(source, "-f", "tiff", cwd=tmp_path)

    assert proc.returncode == 1
    assert "32-bit" in proc.stderr
    assert len(proc.stderr.strip().splitlines()) == 1
    assert [path.name for path in tmp_path.iterdir()] == ["fig.tif"]


# --- output formats -----------------------------------------------------------------------------


def test_pdf_is_a_single_page_that_prints_at_the_requested_width(tmp_path):
    source = flat(tmp_path / "fig.png", (1000, 600))

    report = export(source, "-f", "pdf", "--column", "single", "--journal", "nature", "--dpi", 600, cwd=tmp_path)

    output = Path(report["output"])
    assert output.name == "fig_600dpi.pdf"
    assert report["pixels"] == [2079, 1247]
    objects = pdf_objects(output)
    assert len(objects) == 5
    assert b"/Type /Catalog" in objects[1] and b"/Pages 2 0 R" in objects[1]
    assert b"/Kids [3 0 R]" in objects[2] and b"/Count 1" in objects[2]
    width_pt, height_pt = pdf_page_points(output)
    assert width_pt / 72 * 25.4 == pytest.approx(88.0, abs=0.001)  # Nature's single column
    assert height_pt / 72 * 25.4 == pytest.approx(88.0 * 1247 / 2079, abs=0.001)
    assert pdf_picture(output).size == (2079, 1247)


def test_pdf_draws_the_image_over_the_whole_page(tmp_path):
    source = flat(tmp_path / "fig.png", (1500, 900))

    report = export(source, "-f", "pdf", "--dpi", 300, cwd=tmp_path)

    page, content = pdf_objects(report["output"])[3], pdf_objects(report["output"])[5]
    assert b"/MediaBox [0 0 360.0000 216.0000]" in page  # 1500 x 900 px at 300 dpi, in points
    assert b"/Resources << /XObject << /Im0 4 0 R >> >>" in page and b"/Contents 5 0 R" in page
    assert content.split(b"stream\n")[1] == b"q 360.0000 0 0 216.0000 0 0 cm /Im0 Do Q\nendstream"
    assert report["physical_mm"] == [127.0, 76.2]


def test_pdf_is_lossless(tmp_path):
    source = chart(tmp_path / "fig.png", (1500, 900))

    report = export(source, "-f", "pdf", "--dpi", 300, cwd=tmp_path)

    data = Path(report["output"]).read_bytes()
    assert b"/DCTDecode" not in data  # no JPEG inside
    assert b"/ColorSpace /DeviceRGB" in data
    assert report["notes"] == []
    with Image.open(source) as original:
        picture = pdf_picture(report["output"])
        assert picture.mode == "RGB"
        assert picture.size == original.size
        assert picture.tobytes() == original.tobytes()


def test_pdf_of_a_greyscale_image_stays_greyscale(tmp_path):
    ramp = np.tile(np.linspace(0, 255, 1200).astype(np.uint8), (1100, 1))
    Image.fromarray(ramp).save(tmp_path / "fig.png")

    report = export(tmp_path / "fig.png", "-f", "pdf", "--dpi", 300, cwd=tmp_path)

    assert b"/ColorSpace /DeviceGray" in Path(report["output"]).read_bytes()
    picture = pdf_picture(report["output"])
    assert picture.mode == "L"
    assert picture.tobytes() == ramp.tobytes()


def test_pdf_says_when_it_drops_an_icc_profile(tmp_path):
    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    source = flat(tmp_path / "fig.png", (1500, 900), icc_profile=profile)

    report = export(source, "-f", "pdf", "--dpi", 300, cwd=tmp_path)

    assert report["notes"] == ["The embedded ICC profile is not carried into the PDF."]
    assert b"ICCBased" not in Path(report["output"]).read_bytes()


@pytest.mark.parametrize(
    "journal, fmt, sentence",
    [
        ("nature", "tiff", "Nature Portfolio does not accept TIFF for final artwork; it lists PDF, EPS"),
        ("plos", "png", "PNG is not among the formats listed for PLOS: TIFF, EPS"),
        ("springer", "pdf", "PDF is not among the formats listed for Springer: EPS, TIFF"),
    ],
)
def test_a_format_the_journal_does_not_take_is_noted(tmp_path, journal, fmt, sentence):
    source = flat(tmp_path / "fig.png", (4600, 900))  # wide enough for every double column at 600 dpi: no upscaling note

    report = export(source, "-f", fmt, "--journal", journal, "--column", "double", cwd=tmp_path)

    assert report["notes"] == [f"{sentence} (bundled data, verified 2026-07-21)."]
    assert report["notes"] == [journals.format_problem(journal, fmt)]


@pytest.mark.parametrize("journal, fmt", [("nature", "pdf"), ("wiley", "png"), ("science", "tiff"), ("default", "png")])
def test_a_format_the_journal_lists_or_says_nothing_about_gets_no_note(tmp_path, journal, fmt):
    source = flat(tmp_path / "fig.png", (4600, 900))

    report = export(source, "-f", fmt, "--journal", journal, "--column", "double", cwd=tmp_path)

    assert report["notes"] == []


def test_png_and_tiff_report_no_notes_for_a_plain_rgb_image(tmp_path):
    source = flat(tmp_path / "fig.png", (1500, 900))

    assert export(source, "-f", "png", "--dpi", 300, cwd=tmp_path)["notes"] == []
    assert export(source, "-f", "tiff", "--dpi", 300, cwd=tmp_path)["notes"] == []


# --- inputs -------------------------------------------------------------------------------------


@pytest.mark.parametrize("name, pil_format", [("fig.jpg", "JPEG"), ("fig.webp", "WEBP"), ("fig.tif", "TIFF")])
def test_jpeg_webp_and_tiff_inputs_are_read(tmp_path, name, pil_format):
    source = flat(tmp_path / name, (1200, 1100), format=pil_format)

    report = export(source, "-f", "tiff", "--dpi", 300, cwd=tmp_path)

    assert report["pixels"] == [1200, 1100]
    with Image.open(report["output"]) as out:
        assert out.format == "TIFF"


def test_a_photo_is_exported_the_way_viewers_show_it(tmp_path):
    # Stored 2200 x 1100 with a blue corner, tagged "rotate 90 degrees clockwise to display".
    image = Image.new("RGB", (2200, 1100), "white")
    image.paste((0, 0, 255), (0, 0, 400, 400))
    exif = Image.Exif()
    exif[0x0112] = 6
    image.save(tmp_path / "photo.jpg", quality=95, exif=exif)

    report = export(tmp_path / "photo.jpg", "-f", "tiff", "--dpi", 300, cwd=tmp_path)

    assert report["pixels"] == [1100, 2200]
    with Image.open(report["output"]) as out:
        assert out.size == (1100, 2200)
        assert out.getpixel((1000, 100)) == pytest.approx((0, 0, 255), abs=8)  # the corner is now top right
        assert out.getpixel((100, 100)) == pytest.approx((255, 255, 255), abs=8)
        assert out.getexif().get(0x0112) is None


def test_a_jpeg_that_carries_extra_pictures_is_still_a_jpeg(tmp_path):
    # Phone photos often embed a second picture (depth or gain map); Pillow calls such a file MPO.
    extra = Image.new("RGB", (300, 200), "black")
    Image.new("RGB", (1200, 1100), BLUE).save(tmp_path / "photo.jpg", "MPO", save_all=True, append_images=[extra])

    report = export(tmp_path / "photo.jpg", "-f", "tiff", "--dpi", 300, cwd=tmp_path)

    assert report["pixels"] == [1200, 1100]
    with Image.open(tmp_path / "photo.jpg") as original, Image.open(report["output"]) as out:
        assert original.format == "MPO"
        assert out.getpixel((5, 5)) == pytest.approx(BLUE, abs=4)


def test_other_input_formats_are_refused(tmp_path):
    source = flat(tmp_path / "fig.bmp", (1200, 1100))

    proc = run(source, "-f", "tiff", cwd=tmp_path)

    assert proc.returncode == 1
    assert "BMP" in proc.stderr
    assert [path.name for path in tmp_path.iterdir()] == ["fig.bmp"]


def test_a_missing_input_fails_with_one_line_on_stderr(tmp_path):
    proc = run(tmp_path / "nope.png", "-f", "tiff", "--json", cwd=tmp_path)

    assert proc.returncode == 1
    assert proc.stdout == ""
    assert len(proc.stderr.strip().splitlines()) == 1
    assert "nope.png" in proc.stderr


# --- output path --------------------------------------------------------------------------------


def test_the_default_output_sits_next_to_the_input_and_nothing_else_is_written(tmp_path):
    (tmp_path / "figs").mkdir()
    flat(tmp_path / "figs" / "fig.png", (1200, 1100))

    report = export("figs/fig.png", "-f", "tiff", "--dpi", 300, cwd=tmp_path)

    assert report["output"] == str(Path("figs") / "fig_300dpi.tiff")
    assert sorted(path.name for path in (tmp_path / "figs").iterdir()) == ["fig.png", "fig_300dpi.tiff"]
    assert [path.name for path in tmp_path.iterdir()] == ["figs"]


def test_the_output_option_names_the_file(tmp_path):
    source = flat(tmp_path / "fig.png", (1200, 1100))

    report = export(source, "-f", "tiff", "--dpi", 300, "-o", tmp_path / "Figure 1.tif", cwd=tmp_path)

    assert Path(report["output"]) == tmp_path / "Figure 1.tif"
    with Image.open(tmp_path / "Figure 1.tif") as out:
        assert out.format == "TIFF"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["Figure 1.tif", "fig.png"]


@pytest.mark.parametrize("alias", ["{dir}/fig.png", "./fig.png", "sub/../fig.png"])
def test_it_refuses_to_overwrite_the_input(tmp_path, alias):
    (tmp_path / "sub").mkdir()
    source = flat(tmp_path / "fig.png", (1200, 1100))
    before = source.read_bytes()

    proc = run(source, "-f", "png", "-o", alias.format(dir=tmp_path), cwd=tmp_path)

    assert proc.returncode == 1
    assert "overwrite" in proc.stderr
    assert len(proc.stderr.strip().splitlines()) == 1
    assert source.read_bytes() == before


def test_it_does_not_create_missing_directories(tmp_path):
    source = flat(tmp_path / "fig.png", (1200, 1100))

    proc = run(source, "-f", "tiff", "-o", tmp_path / "new" / "fig.tiff", cwd=tmp_path)

    assert proc.returncode == 1
    assert len(proc.stderr.strip().splitlines()) == 1
    assert [path.name for path in tmp_path.iterdir()] == ["fig.png"]


def test_it_writes_nothing_next_to_itself(tmp_path):
    # Not even a __pycache__ for journals.py. Run a copy, with this interpreter rather than uv,
    # which would keep one cached environment per copy.
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    for name in ("export_figure.py", "journals.py"):
        shutil.copy(SCRIPTS / name, scripts / name)
    source = flat(tmp_path / "fig.png", (1200, 1100))

    proc = subprocess.run(
        [sys.executable, str(scripts / "export_figure.py"), str(source), "-f", "tiff", "--dpi", "300"],
        cwd=tmp_path, capture_output=True, text=True,
    )

    assert proc.returncode == 0, proc.stderr
    assert sorted(path.name for path in scripts.iterdir()) == ["export_figure.py", "journals.py"]
    assert sorted(path.name for path in tmp_path.iterdir()) == ["fig.png", "fig_300dpi.tiff", "scripts"]


# --- command line -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "options",
    [
        ["-f", "tiff", "--width-mm", "89", "--column", "single"],
        ["-f", "tiff", "--dpi", "0"],
        ["-f", "tiff", "--dpi", "-300"],
        ["-f", "tiff", "--dpi", "72.5"],
        ["-f", "tiff", "--width-mm", "0"],
        ["-f", "tiff", "--journal", "not-a-journal"],
        ["-f", "jpeg"],
        [],  # -f is required
    ],
)
def test_usage_errors_exit_2_and_write_nothing(tmp_path, options):
    source = flat(tmp_path / "fig.png", (1200, 1100))

    proc = run(source, *options, cwd=tmp_path)

    assert proc.returncode == 2
    assert "usage: export_figure.py" in proc.stderr  # argparse's message, not a uv failure
    assert proc.stdout == ""
    assert [path.name for path in tmp_path.iterdir()] == ["fig.png"]


def test_without_json_it_prints_a_readable_summary_of_the_same_facts(tmp_path):
    source = flat(tmp_path / "fig.png", (1000, 600))

    proc = run(source, "-f", "tiff", "--column", "single", "--journal", "nature", "--dpi", 600, cwd=tmp_path)

    assert proc.returncode == 0, proc.stderr
    with pytest.raises(json.JSONDecodeError):
        json.loads(proc.stdout)
    facts = (
        str(tmp_path / "fig_600dpi.tiff"), "tiff", "2079 x 1247", "600.1", "88.0 x 52.8", "2.079", "not detail",
        "Nature Portfolio does not accept TIFF",
    )
    for fact in facts:
        assert fact in proc.stdout, fact


def test_the_dpi_tag_never_falls_below_the_requested_resolution(tmp_path):
    # 190 mm at 500 dpi is 3740.16 px: 3740 px would be tagged 499.98 dpi, under the publisher's minimum.
    source = flat(tmp_path / "fig.png", (1536, 864))

    report = export(source, "-f", "tiff", "--journal", "elsevier", "--column", "double", "--dpi", 500, cwd=tmp_path)

    assert report["pixels"][0] == 3741
    with Image.open(report["output"]) as out:
        assert out.info["dpi"][0] >= 500
