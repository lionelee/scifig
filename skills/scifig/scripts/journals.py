"""Numeric figure presets per publisher.

Hand-encoded from ../references/journal-figure-requirements.json
(SciDraw AI, "Journal figure requirements", CC BY 4.0, last verified 2026-07-21).
Publisher guides change: confirm against the journal's current author guide before submitting.

Conventions:
- widths and heights are millimetres at final printed size; font sizes are points. other_mm lists
  the widths between one and two columns that the publisher names.
- dpi values are minimums at final size. None = that dataset records no value for the
  publisher; "vector" = the publisher requires vector artwork, so no raster dpi satisfies it.
- accepts and rejects name file formats out of FORMATS only. accepts = those the dataset lists
  for the publisher (None = it lists none of them); rejects = those it says are not accepted.
"""
import math

VERIFIED = "2026-07-21"
MM_PER_INCH = 25.4
KINDS = ("photo", "combination", "line_art")
FORMATS = ("tiff", "png", "jpeg", "pdf", "eps")

JOURNALS = {
    "default": {
        "label": "Generic journal",
        "single_mm": 89, "double_mm": 178, "other_mm": (), "max_height_mm": None,
        "fonts": ["Arial", "Helvetica"], "font_pt": 7, "min_font_pt": 6,
        "panel_case": "lower", "panel_pt": 8,
        "dpi": {"photo": 300, "combination": 600, "line_art": 1000},
        "accepts": None, "rejects": (),
        "note": "Common values, not a publisher rule. Check your journal's guide.",
    },
    "nature": {
        "label": "Nature Portfolio",
        "single_mm": 88, "double_mm": 180, "other_mm": (120, 136), "max_height_mm": 247,
        "fonts": ["Helvetica", "Arial"], "font_pt": 7, "min_font_pt": 5,
        "panel_case": "lower", "panel_pt": 8,
        "dpi": {"photo": 300, "combination": 300, "line_art": "vector"},
        "accepts": ("pdf", "eps"), "rejects": ("jpeg", "tiff", "png"),
        "note": "Line art and text must stay vector. 88/180 mm fits both official guides; "
                "Nature itself allows 89/183 mm. Its final-artwork guide says it cannot use JPEG, TIFF or PNG; "
                "its current figure guide prefers PDF or EPS.",
    },
    "science": {
        "label": "Science (AAAS)",
        "single_mm": 57, "double_mm": 121, "other_mm": (), "max_height_mm": None,
        "fonts": ["Helvetica", "Arial"], "font_pt": 7, "min_font_pt": 5,
        "panel_case": "upper", "panel_pt": 10,
        "dpi": {"photo": 300, "combination": None, "line_art": None},
        "accepts": None, "rejects": (),
        "note": "Three-column width is 184 mm (pass it as a number).",
    },
    "cell": {
        "label": "Cell Press",
        "single_mm": 85, "double_mm": 174, "other_mm": (114,), "max_height_mm": 279.4,
        "fonts": ["Arial"], "font_pt": 7, "min_font_pt": 6,
        "panel_case": "upper", "panel_pt": None,
        "dpi": {"photo": 300, "combination": 500, "line_art": 1000},
        "accepts": ("tiff", "pdf", "jpeg", "eps"), "rejects": (),
        "note": "The whole figure must fit one 8.5 x 11 in page. Cell Press asks not to use red and green together.",
    },
    "plos": {
        "label": "PLOS",
        "single_mm": 66.8, "double_mm": 190.5, "other_mm": (), "max_height_mm": 222.3,
        "fonts": ["Arial", "Times New Roman"], "font_pt": 8, "min_font_pt": 8,
        "panel_case": None, "panel_pt": None,
        "dpi": {"photo": 300, "combination": 300, "line_art": 300},
        "accepts": ("tiff", "eps"), "rejects": (),
        "note": "Width is a range (6.68-19.05 cm), not columns. 300-600 dpi is accepted for all artwork.",
    },
    "wiley": {
        "label": "Wiley (general guidance)",
        "single_mm": 80, "double_mm": 180, "other_mm": (), "max_height_mm": None,
        "fonts": None, "font_pt": None, "min_font_pt": None,
        "panel_case": None, "panel_pt": None,
        "dpi": {"photo": 300, "combination": 600, "line_art": 600},
        "accepts": ("pdf", "eps", "png", "tiff"), "rejects": (),
        "note": "Width is a range (80-180 mm), not columns.",
    },
    "elsevier": {
        "label": "Elsevier (general guidance)",
        "single_mm": 90, "double_mm": 190, "other_mm": (140,), "max_height_mm": None,
        "fonts": ["Arial", "Helvetica"], "font_pt": 7, "min_font_pt": 6,
        "panel_case": None, "panel_pt": None,
        "dpi": {"photo": 300, "combination": 500, "line_art": 1000},
        "accepts": ("eps", "pdf", "tiff", "jpeg"), "rejects": (),
        "note": "Elsevier prefers EPS for vector artwork and asks for 1200 dpi when line art has very fine lines.",
    },
    "springer": {
        "label": "Springer",
        "single_mm": 84, "double_mm": 174, "other_mm": (129,), "max_height_mm": 234,
        "fonts": ["Helvetica", "Arial"], "font_pt": 8, "min_font_pt": 8,
        "panel_case": "lower", "panel_pt": None,
        "dpi": {"photo": 300, "combination": 600, "line_art": 1200},
        "accepts": ("eps", "tiff"), "rejects": (),
        "note": None,
    },
    "ieee": {
        "label": "IEEE journals",
        "single_mm": 88.9, "double_mm": 182, "other_mm": (), "max_height_mm": 220,
        "fonts": ["Helvetica", "Arial", "Times New Roman"], "font_pt": 9, "min_font_pt": 9,
        "panel_case": None, "panel_pt": None,
        "dpi": {"photo": 300, "combination": None, "line_art": 600},
        "accepts": ("eps", "pdf", "png", "tiff"), "rejects": (),
        "note": None,
    },
    "rsc": {
        "label": "RSC (Chemical Science)",
        "single_mm": 83, "double_mm": 171, "other_mm": (), "max_height_mm": 233,
        "fonts": ["Arial", "Helvetica"], "font_pt": 7, "min_font_pt": 7,
        "panel_case": None, "panel_pt": None,
        "dpi": {"photo": 600, "combination": 600, "line_art": 600},
        "accepts": ("tiff", "eps", "pdf"), "rejects": (),
        "note": None,
    },
    "jci": {
        "label": "Journal of Clinical Investigation",
        "single_mm": 90, "double_mm": 180, "other_mm": (), "max_height_mm": 172.5,
        "fonts": ["Helvetica", "Arial"], "font_pt": 8, "min_font_pt": 8,
        "panel_case": "upper", "panel_pt": None,
        "dpi": {"photo": 600, "combination": 600, "line_art": 600},
        "accepts": ("tiff", "pdf", "eps"), "rejects": ("jpeg",),
        "note": "A complete figure is 9-18 cm wide; there are no separate column widths.",
    },
}


def get(journal="default"):
    """Return the preset for a journal key, or raise ValueError naming the valid keys."""
    try:
        return JOURNALS[journal]
    except KeyError:
        raise ValueError(f"unknown journal {journal!r}; choose from: {', '.join(JOURNALS)}") from None


def width_mm(journal, width):
    """Resolve "single", "double" or a number of millimetres to a width in mm."""
    if width in ("single", "double"):
        return float(get(journal)[f"{width}_mm"])
    try:
        value = float(width)
    except (TypeError, ValueError):
        raise ValueError(f"width must be 'single', 'double' or millimetres, got {width!r}") from None
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"width must be positive and finite, got {value}")
    return value


def required_dpi(journal, kind):
    """Return (dpi, basis) for a figure kind.

    basis is "stated" (from the publisher guide), "generic" (publisher states nothing, so the
    generic default applies; always the case for the "default" journal) or "vector" (publisher
    requires vector artwork; dpi is None).
    """
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {', '.join(KINDS)}, got {kind!r}")
    value = get(journal)["dpi"][kind]
    if value == "vector":
        return None, "vector"
    if value is None or journal == "default":
        return JOURNALS["default"]["dpi"][kind], "generic"
    return value, "stated"


def pixels_for(mm, dpi):
    """Fewest pixels that print `mm` wide at `dpi` or more."""
    # The tolerance keeps an exact width exact: 76.2 mm at 300 dpi is 900.0000000000001 in floating point.
    return math.ceil(mm / MM_PER_INCH * dpi - 1e-9)


def format_problem(journal, fmt):
    """Return one sentence when the publisher does not take file format `fmt`, else None.

    fmt is one of FORMATS. None also when the dataset lists none of them for the publisher.
    """
    if fmt not in FORMATS:
        raise ValueError(f"format must be one of {', '.join(FORMATS)}, got {fmt!r}")
    preset = get(journal)
    listed = ", ".join(name.upper() for name in preset["accepts"] or ())
    source = f"(bundled data, verified {VERIFIED})"
    if fmt in preset["rejects"]:
        return f"{preset['label']} does not accept {fmt.upper()} for final artwork; it lists {listed} {source}."
    if preset["accepts"] is not None and fmt not in preset["accepts"]:
        return f"{fmt.upper()} is not among the formats listed for {preset['label']}: {listed} {source}."
    return None
