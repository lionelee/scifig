"""Tests for skills/scifig/scripts/journals.py."""
import json
import sys
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[2] / "skills" / "scifig"
sys.path.insert(0, str(SKILL / "scripts"))

import journals  # noqa: E402

DATASET = json.loads((SKILL / "references" / "journal-figure-requirements.json").read_text())
PUBLISHERS = [key for key in journals.JOURNALS if key != "default"]  # in the order of the dataset records
FORMAT_NAMES = {"tiff", "png", "jpeg", "pdf", "eps"}


# --- presets ----------------------------------------------------------------------------------


def test_every_preset_has_the_same_fields():
    fields = set(journals.JOURNALS["default"])

    assert {"accepts", "rejects", "note", "dpi", "single_mm", "double_mm"} <= fields
    for key, preset in journals.JOURNALS.items():
        assert set(preset) == fields, key
        assert set(preset["dpi"]) == set(journals.KINDS), key


def test_nature_uses_the_widths_that_fit_both_official_guides():
    nature = journals.get("nature")

    assert (nature["single_mm"], nature["double_mm"]) == (88, 180)
    assert nature["note"] == (
        "Line art and text must stay vector. 88/180 mm fits both official guides; Nature itself allows 89/183 mm. "
        "Its final-artwork guide says it cannot use JPEG, TIFF or PNG; its current figure guide prefers PDF or EPS."
    )


def test_the_default_preset_keeps_the_common_widths():
    default = journals.get("default")

    assert (default["single_mm"], default["double_mm"]) == (89, 178)


def test_plos_mandates_no_panel_label_case():
    assert journals.get("plos")["panel_case"] is None


def test_rsc_states_one_resolution_for_every_kind_of_figure():
    assert journals.get("rsc")["dpi"] == {"photo": 600, "combination": 600, "line_art": 600}


def test_a_cell_press_figure_must_fit_an_11_inch_page():
    assert journals.get("cell")["max_height_mm"] == pytest.approx(11 * 25.4)


def test_get_rejects_an_unknown_journal_and_names_the_valid_keys():
    with pytest.raises(ValueError, match="unknown journal 'lancet'.*nature"):
        journals.get("lancet")


# --- widths and resolutions -------------------------------------------------------------------


def test_width_mm_resolves_columns_and_numbers():
    assert journals.width_mm("nature", "single") == 88.0
    assert journals.width_mm("nature", "double") == 180.0
    assert journals.width_mm("default", "single") == 89.0
    assert journals.width_mm("nature", 120) == 120.0
    assert journals.width_mm("nature", "66.8") == 66.8


@pytest.mark.parametrize("width", [0, -5, "wide", None, float("nan"), float("inf"), float("-inf"), "nan", "inf"])
def test_width_mm_rejects_what_is_not_a_positive_finite_number(width):
    with pytest.raises(ValueError, match="width"):
        journals.width_mm("default", width)


def test_required_dpi_tells_a_stated_requirement_from_the_generic_default():
    assert journals.required_dpi("cell", "line_art") == (1000, "stated")
    assert journals.required_dpi("science", "combination") == (600, "generic")
    assert journals.required_dpi("rsc", "line_art") == (600, "stated")
    assert journals.required_dpi("nature", "line_art") == (None, "vector")


@pytest.mark.parametrize("kind, dpi", [("photo", 300), ("combination", 600), ("line_art", 1000)])
def test_the_default_journal_is_the_generic_default_not_a_publisher_rule(kind, dpi):
    assert journals.required_dpi("default", kind) == (dpi, "generic")


def test_required_dpi_rejects_an_unknown_kind():
    with pytest.raises(ValueError, match="kind"):
        journals.required_dpi("default", "diagram")


def test_pixels_for_rounds_up_so_a_file_never_falls_short_of_the_dpi():
    assert journals.pixels_for(89, 600) == 2103  # 2102.36
    assert journals.pixels_for(178, 600) == 4205  # 4204.72
    assert journals.pixels_for(88, 300) == 1040  # 1039.37
    assert journals.pixels_for(190, 500) == 3741  # 3740.16; 3740 px would print at 499.98 dpi


def test_pixels_for_keeps_exact_widths_exact():
    assert journals.pixels_for(25.4, 300) == 300
    assert journals.pixels_for(76.2, 300) == 900  # 76.2 / 25.4 is 3.0000000000000004 in floating point


# --- formats ----------------------------------------------------------------------------------


def test_the_verification_date_is_the_one_of_the_bundled_dataset():
    assert journals.VERIFIED == "2026-07-21" == DATASET["lastVerified"]


def test_format_lists_use_only_the_known_names():
    for key, preset in journals.JOURNALS.items():
        assert preset["accepts"] is None or isinstance(preset["accepts"], tuple), key
        assert isinstance(preset["rejects"], tuple), key
        assert set(preset["accepts"] or ()) | set(preset["rejects"]) <= FORMAT_NAMES, key
        assert not set(preset["accepts"] or ()) & set(preset["rejects"]), key
        assert preset["accepts"] or not preset["rejects"], key  # a rejection can always name the alternatives


def test_the_default_preset_lists_no_formats():
    assert journals.get("default")["accepts"] is None
    assert journals.get("default")["rejects"] == ()


@pytest.mark.parametrize("key, record", list(zip(PUBLISHERS, DATASET["records"])), ids=PUBLISHERS)
def test_format_lists_agree_with_the_bundled_dataset(key, record):
    preset = journals.get(key)
    listed = {name for name in FORMAT_NAMES if name in record["formats"].lower()}
    rejected = {name for name in FORMAT_NAMES if name in record["rejectedFormats"].lower()}

    assert key in record["journal"].lower()
    assert set(preset["accepts"] or ()) == listed - rejected
    assert set(preset["rejects"]) == rejected


@pytest.mark.parametrize(
    "key, accepts, rejects",
    [
        ("nature", ("pdf", "eps"), ("jpeg", "tiff", "png")),
        ("science", None, ()),
        ("cell", ("tiff", "pdf", "jpeg", "eps"), ()),
        ("plos", ("tiff", "eps"), ()),
        ("wiley", ("pdf", "eps", "png", "tiff"), ()),
        ("elsevier", ("eps", "pdf", "tiff", "jpeg"), ()),
        ("springer", ("eps", "tiff"), ()),
        ("ieee", ("eps", "pdf", "png", "tiff"), ()),
        ("rsc", ("tiff", "eps", "pdf"), ()),
        ("jci", ("tiff", "pdf", "eps"), ("jpeg",)),
    ],
)
def test_format_lists_keep_the_order_of_the_publisher_guide(key, accepts, rejects):
    assert journals.get(key)["accepts"] == accepts
    assert journals.get(key)["rejects"] == rejects


def test_format_problem_names_a_rejected_format_and_the_alternatives():
    assert journals.format_problem("nature", "png") == (
        "Nature Portfolio does not accept PNG for final artwork; it lists PDF, EPS "
        "(bundled data, verified 2026-07-21)."
    )
    assert journals.format_problem("jci", "jpeg") == (
        "Journal of Clinical Investigation does not accept JPEG for final artwork; it lists TIFF, PDF, EPS "
        "(bundled data, verified 2026-07-21)."
    )


def test_format_problem_names_a_format_the_publisher_does_not_list():
    assert journals.format_problem("plos", "png") == (
        "PNG is not among the formats listed for PLOS: TIFF, EPS (bundled data, verified 2026-07-21)."
    )
    assert journals.format_problem("elsevier", "png") == (
        "PNG is not among the formats listed for Elsevier (general guidance): EPS, PDF, TIFF, JPEG "
        "(bundled data, verified 2026-07-21)."
    )


@pytest.mark.parametrize(
    "key, fmt", [("wiley", "png"), ("plos", "tiff"), ("nature", "pdf"), ("default", "png"), ("science", "jpeg")]
)
def test_format_problem_is_none_for_a_listed_format_or_when_nothing_is_listed(key, fmt):
    assert journals.format_problem(key, fmt) is None


@pytest.mark.parametrize("fmt", ["PNG", "tif", "jpg", "webp", "", None])
def test_format_problem_rejects_an_unknown_format_name(fmt):
    with pytest.raises(ValueError, match="format"):
        journals.format_problem("nature", fmt)


def test_format_problem_rejects_an_unknown_journal():
    with pytest.raises(ValueError, match="unknown journal"):
        journals.format_problem("lancet", "png")


def test_notes_read_as_publisher_rules_not_as_findings():
    # check_figure prints the note under every report, whatever the figure looks like.
    assert "red and green" in journals.get("cell")["note"]  # the data set's colour rule for Cell Press
    assert "1200 dpi" in journals.get("elsevier")["note"]
    assert "prefers EPS" in journals.get("elsevier")["note"]  # the data set: "EPS (preferred for vector)"


def test_presets_carry_the_intermediate_widths_the_data_set_gives():
    # Widths between one and two columns, in mm; an empty tuple where the publisher states none.
    expected = {"nature": (120, 136), "cell": (114,), "elsevier": (140,), "springer": (129,)}
    for key, preset in journals.JOURNALS.items():
        assert preset["other_mm"] == expected.get(key, ()), key
