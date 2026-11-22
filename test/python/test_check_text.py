"""Tests for skills/scifig/scripts/check_text.py.

The comparison of labels with the text read from a figure is plain Python and is tested directly.
The command is then run the way a user does (`uv run check_text.py ...`) on figures drawn with
Pillow, so that the text really goes through OCR.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

SCRIPTS = Path(__file__).resolve().parents[2] / "skills" / "scifig" / "scripts"
SCRIPT = SCRIPTS / "check_text.py"
sys.path.insert(0, str(SCRIPTS))

import check_text  # noqa: E402

UV = shutil.which("uv") or "uv"
LATIN_FONTS = ("/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf")
CHINESE_FONTS = ("/System/Library/Fonts/STHeiti Medium.ttc", "/System/Library/Fonts/Supplemental/Songti.ttc")


# --- the comparison ---------------------------------------------------------------------------


def read(text, left=0, top=0, height=20):
    """One text as OCR reports it: (text, (left, top, right, bottom))."""
    return text, (left, top, left + 11 * len(text), top + height)


def found(result):
    return {label["text"]: label["found"] for label in result["labels"]}


def test_a_label_is_found_however_the_reader_spaces_it():
    result = check_text.compare(["Feed Forward", "Add & Norm"], [read("FeedForward"), read("Add &Norm", top=60)])

    assert found(result) == {"Feed Forward": 1, "Add & Norm": 1}
    assert result["extra"] == []


def test_a_label_counts_once_for_each_place_it_stands():
    texts = [read("Add & Norm", top=top) for top in (0, 80, 160)]

    assert found(check_text.compare(["Add & Norm"], texts)) == {"Add & Norm": 3}


def test_a_label_set_on_two_lines_is_one_label():
    texts = [read("Positional", left=100, top=100), read("Encoding", left=105, top=126)]

    result = check_text.compare(["Positional Encoding"], texts)

    assert found(result) == {"Positional Encoding": 1}
    assert result["extra"] == []


def test_a_two_line_label_whose_first_line_is_a_label_of_its_own_keeps_both():
    # "PD-L1" stands beside the protein; "PD-L1 silencing" stands on two lines beside an arrow.
    texts = [read("PD-L1", left=900, top=100), read("PD-L1", left=880, top=560), read("silencing", left=870, top=588)]

    result = check_text.compare(["PD-L1", "PD-L1 silencing"], texts)

    assert found(result) == {"PD-L1": 1, "PD-L1 silencing": 1}
    assert result["extra"] == []


def test_lines_far_apart_are_not_joined_into_a_label():
    texts = [read("Positional", left=100, top=100), read("Encoding", left=900, top=700)]

    assert found(check_text.compare(["Positional Encoding"], texts)) == {"Positional Encoding": 0}


def test_neighbouring_labels_read_as_one_line_are_each_found():
    result = check_text.compare(["Flatten", "Fully connected"], [read("Flatten Fully connected Fully connected")])

    assert found(result) == {"Flatten": 1, "Fully connected": 2}
    assert result["extra"] == []


def test_a_misspelt_label_is_missing_and_the_misspelling_is_named():
    result = check_text.compare(["Mitochondria", "Nucleus"], [read("Mitocondria"), read("Nucleus", top=60)])

    assert result["labels"][0] == {"text": "Mitochondria", "found": 0, "listed": 1, "closest": "Mitocondria", "second": None, "crop": None}
    assert result["labels"][1] == {"text": "Nucleus", "found": 1, "listed": 1, "closest": None, "second": None, "crop": None}
    assert result["extra"] == []  # named once, as the closest text, not a second time as extra text


def test_a_difference_in_capitals_is_not_a_match():
    result = check_text.compare(["Add & Norm"], [read("Add & norm")])

    assert result["labels"] == [{"text": "Add & Norm", "found": 0, "listed": 1, "closest": "Add & norm", "second": None, "crop": None}]


def test_text_that_no_label_explains_is_extra():
    result = check_text.compare(["Nucleus"], [read("Nucleus"), read("Lorem ipsum", top=60)])

    assert result["extra"] == ["Lorem ipsum"]


def test_marks_without_letters_or_digits_are_ignored():
    result = check_text.compare(["Nucleus"], [read("Nucleus"), read("...", top=60), read(":", top=90)])

    assert result["extra"] == []
    assert result["ignored_marks"] == 2


def test_single_characters_read_from_shapes_are_marks_not_extra_text():
    # OCR reads a circle as "O" and an icon as "8"; a label of one letter that was asked for still counts.
    result = check_text.compare(["Query", "K"], [read("Query"), read("K", top=40), read("O", top=80), read("8", top=120)])

    assert found(result) == {"Query": 1, "K": 1}
    assert result["extra"] == []
    assert result["ignored_marks"] == 2


def test_characters_of_a_script_that_no_label_uses_are_marks():
    # The rungs of a drawn RNA ladder come back as Chinese characters in a figure labelled in English.
    result = check_text.compare(["siRNA"], [read("siRNA"), read("目具", top=60)])

    assert result["extra"] == []
    assert result["ignored_marks"] == 1
    assert check_text.compare(["实验室测定"], [read("实验室测定"), read("目具", top=60)])["extra"] == ["目具"]


def test_a_row_of_shapes_read_as_a_letter_a_symbol_and_a_foreign_character_is_a_mark():
    # A circle, a triangle and a square above a funnel came back as "O△口" in a figure labelled in English.
    result = check_text.compare(["Split Data"], [read("Split Data"), read("O△口", top=60)])

    assert result["extra"] == []
    assert result["ignored_marks"] == 1
    assert check_text.compare(["Split Data"], [read("Split Data"), read("Figure 口", top=60)])["extra"] == ["Figure 口"]


def test_a_symbol_drawn_next_to_a_label_does_not_hide_the_label():
    result = check_text.compare(["PD-L1", "Mask (opt.)"], [read("PD-L1↓"), read("Mask (opt.)", top=60)])

    assert found(result) == {"PD-L1": 1, "Mask (opt.)": 1}
    assert result["extra"] == []


def test_full_width_and_half_width_forms_are_one_text():
    result = check_text.compare(["野外采样（n = 120）"], [read("野外采样(n=120)")])

    assert found(result) == {"野外采样（n = 120）": 1}


def test_a_label_listed_once_for_each_place_is_counted_against_that_number():
    # The decoder should hold three "Add & Norm" boxes; a figure that draws two is short of one.
    result = check_text.compare(["Add & Norm"] * 3, [read("Add & Norm"), read("Add & Norm", top=80)])

    assert result["labels"] == [{"text": "Add & Norm", "found": 2, "listed": 3, "closest": None, "second": None, "crop": None}]


def test_the_times_sign_and_the_letter_x_are_one_text():
    result = check_text.compare(["N ×", "224×224×3"], [read("Nx"), read("224x224x3", top=60)])

    assert found(result) == {"N ×": 1, "224×224×3": 1}
    assert result["extra"] == []


def test_a_symbol_or_single_character_that_was_not_read_is_set_aside_not_called_missing():
    # OCR does not read a plus sign in a circle or a white number on a badge, and often misses a lone
    # italic letter; calling them missing would send the agent after faults that are not there.
    result = check_text.compare(["+", "1", "Q", "K", "Softmax"], [read("Softmax"), read("K", top=60)])

    assert result["labels"] == [
        {"text": "K", "found": 1, "listed": 1, "closest": None, "second": None, "crop": None},
        {"text": "Softmax", "found": 1, "listed": 1, "closest": None, "second": None, "crop": None},
    ]
    assert result["unread"] == ["+", "1", "Q"]


def test_a_line_of_a_bulleted_list_is_found_without_its_bullet():
    texts = [read("·Handle missing values"), read("•Track the loss", top=40), read("√ Fix the random seeds", top=80)]

    result = check_text.compare(["Handle missing values", "Track the loss", "Fix the random seeds"], texts)

    assert found(result) == {"Handle missing values": 1, "Track the loss": 1, "Fix the random seeds": 1}
    assert result["extra"] == []


def test_a_bullet_is_dropped_but_the_sign_that_ends_the_label_is_kept():
    result = check_text.compare(["Train set 70-80%", "Good enough?"], [read("·Train set 70-80%"), read("Good enough?", top=60)])

    assert found(result) == {"Train set 70-80%": 1, "Good enough?": 1}
    assert result["extra"] == []


def test_a_bulleted_line_that_wraps_after_a_comma_is_one_label():
    texts = [read("·Accuracy, precision,", left=100, top=100), read("recall, F1", left=118, top=126)]

    result = check_text.compare(["Accuracy, precision, recall, F1"], texts)

    assert found(result) == {"Accuracy, precision, recall, F1": 1}
    assert result["extra"] == []


def test_capital_i_and_small_l_are_one_letter_to_the_reader():
    # In a sans-serif face the two are the same stroke, and OCR picks either.
    result = check_text.compare(["databases and APIs", "Illumina"], [read("databasesandAPls"), read("lllumina", top=60)])

    assert found(result) == {"databases and APIs": 1, "Illumina": 1}
    assert result["extra"] == []


def test_a_bulleted_line_that_wraps_is_one_label():
    texts = [read("·Remove duplicates", left=100, top=100), read("and outliers", left=118, top=126)]

    result = check_text.compare(["Remove duplicates and outliers"], texts)

    assert found(result) == {"Remove duplicates and outliers": 1}
    assert result["extra"] == []


def test_a_wrapped_line_takes_the_line_under_it_not_the_end_of_the_line_above():
    # Two bullets of a narrow card, each on two lines, and both end in the same word.
    texts = [
        read("Scale numeric", left=100, top=100), read("features", left=100, top=126),
        read("Create and select", left=100, top=160), read("features", left=100, top=186),
    ]

    result = check_text.compare(["Scale numeric features", "Create and select features"], texts)

    assert found(result) == {"Scale numeric features": 1, "Create and select features": 1}
    assert result["extra"] == []


def test_a_label_read_together_with_its_leader_line_is_found():
    texts = [read("Kinase-", left=420, top=490), read("inhibitor", left=420, top=516)]

    result = check_text.compare(["Kinase inhibitor"], texts)

    assert found(result) == {"Kinase inhibitor": 1}
    assert result["extra"] == []


def test_dashes_are_one_character_however_they_are_typed():
    result = check_text.compare(["0–20 cm 表层土", "Train set 70−80%"], [read("·0-20cm表层土"), read("Train set 70-80%", top=60)])

    assert found(result) == {"0–20 cm 表层土": 1, "Train set 70−80%": 1}


def test_drawn_patterns_read_as_letters_are_marks_not_extra_text():
    # A lipid bilayer comes back as a row of zeros, a DNA helix as "DXOXOXO", the rungs of an RNA strand as "HH".
    texts = [read("Nucleus"), read("000000000O0", top=40), read("DXOXOXO", top=80), read("HH", top=120), read("EFEFEEF", top=160)]

    result = check_text.compare(["Nucleus"], texts)

    assert result["extra"] == []
    assert result["ignored_marks"] == 4
    assert check_text.compare(["Nucleus"], [read("Nucleus"), read("Figure data", top=40)])["extra"] == ["Figure data"]


def test_a_bar_a_small_l_and_a_capital_i_are_one_stroke_to_the_reader():
    # The bars that part a line came back as "|" once and as "I" twice.
    label = "Data versions  |  Code & config  |  Random seeds  |  Metrics & artifacts"
    texts = [read("Data versions | Code & config I Random seeds I Metrics & artifacts")]

    assert found(check_text.compare([label], texts)) == {label: 1}


def test_a_root_sign_and_the_letter_v_are_one_text():
    result = check_text.compare(["Scale by √dₖ", "QKᵀ"], [read("Scale by Vdk"), read("QKT", top=60)])

    assert found(result) == {"Scale by √dₖ": 1, "QKᵀ": 1}


def test_the_underscore_that_marks_a_subscript_in_a_label_is_not_compared():
    # A brief writes d_model; the picture sets "model" as a subscript, which is read as "dmodel" or "d model".
    result = check_text.compare(["d_model = 512", "d_ff = 2048"], [read("dmodel = 512"), read("d ff =2048", top=60)])

    assert found(result) == {"d_model = 512": 1, "d_ff = 2048": 1}
    assert result["extra"] == []


def test_the_closest_text_of_a_label_on_two_lines_is_both_lines():
    # One line of the label is misspelt in the picture: the report names the label's two lines together.
    texts = [read("AMP/ATP", left=100, top=100), read("ratiio↑", left=105, top=126), read("Nucleus", left=600, top=100)]

    result = check_text.compare(["AMP/ATP ratio ↑", "Nucleus"], texts)

    assert result["labels"][0] == {"text": "AMP/ATP ratio ↑", "found": 0, "listed": 1, "closest": "AMP/ATP ratiio↑", "second": None, "crop": None}
    assert result["extra"] == []


def test_a_line_that_brings_the_closest_text_no_closer_is_left_out_of_it():
    # The third line of the label was read upside down.
    texts = [read("Hepatic", left=100, top=100), read("glucose", left=100, top=126), read("↑ ndno", left=100, top=152)]

    result = check_text.compare(["Hepatic glucose output ↓"], texts)

    assert result["labels"][0]["closest"] == "Hepatic glucose"
    assert result["extra"] == ["↑ ndno"]


def test_a_capital_o_and_a_zero_are_one_letter_to_the_reader():
    # In most sans-serif faces the two differ by a hair; OCR reads either for either.
    texts = [read("C02 uptake"), read("02 sensing", top=60), read("H20 flux", top=120), read("1OO cells", top=180)]

    result = check_text.compare(["CO₂ uptake", "O₂ sensing", "H₂O flux", "100 cells"], texts)

    assert found(result) == {"CO₂ uptake": 1, "O₂ sensing": 1, "H₂O flux": 1, "100 cells": 1}


def test_labels_read_as_one_line_with_separators_between_them_are_each_found():
    # A row of abbreviations: OCR reads two entries, and the semicolons between them, as one line.
    labels = ["AMPK: AMP-activated protein kinase", "ACC: acetyl-CoA carboxylase", "G6Pase", "PEPCK"]
    texts = [read("AMPK: AMP-activated protein kinase; ACC: acetyl-CoA carboxylase;"), read("G6Pase, PEPCK", top=60)]

    result = check_text.compare(labels, texts)

    assert found(result) == dict.fromkeys(labels, 1)
    assert result["extra"] == []


def test_a_misspelt_label_in_a_row_with_separators_still_differs():
    line = read("AMPK: AMP-activated prottein kinase; ACC: acetyl-CoA carboxylase;")

    result = check_text.compare(["AMPK: AMP-activated protein kinase", "ACC: acetyl-CoA carboxylase"], [line], reader({(0, 0): [line]}))

    assert result["labels"][0]["second"] == "differs"


def test_numbers_that_no_label_explains_are_extra_text_not_marks():
    # An image tool writes a statistic into a picture now and then. Its zeros repeat, but it is text.
    texts = [read("Nucleus"), read("p < 0.0001", top=40), read("n = 10000", top=80), read("2010-2020", top=120), read("1:100,000", top=160)]

    result = check_text.compare(["Nucleus"], texts)

    assert result["extra"] == ["p < 0.0001", "n = 10000", "2010-2020", "1:100,000"]


# --- the second reading -----------------------------------------------------------------------


def reader(readings):
    """A second reading: readings maps the left edge and top of a place to the texts read there, enlarged."""
    asked = []

    def again(box):
        asked.append(box[:2])
        return readings[box[:2]]

    again.asked = asked
    return again


def test_a_label_read_wrong_at_first_and_right_when_enlarged_is_found():
    # The 6 on a badge was read as 5 in the whole picture.
    again = reader({(0, 0): [read("6"), read("User question", left=30)]})

    result = check_text.compare(["6  User question"], [read("5 User question")], again)

    assert result["labels"] == [
        {"text": "6  User question", "found": 1, "listed": 1, "closest": "5 User question", "second": "found", "crop": None}
    ]
    assert result["extra"] == []


def test_letters_read_the_same_twice_that_are_not_those_of_the_label_differ():
    # The picture says "Questoin"; enlarged, the plus signs are read otherwise and the letters are not.
    again = reader({(0, 0): [read("Questoin - + evidence - + rules")]})

    result = check_text.compare(["Question + evidence + rules"], [read("Questoin+evidence+rules")], again)

    assert result["labels"] == [
        {"text": "Question + evidence + rules", "found": 0, "listed": 1, "closest": "Questoin+evidence+rules", "second": "differs", "crop": None}
    ]


def test_a_text_read_twice_that_only_lacks_part_of_its_label_does_not_differ():
    # OCR leaves out a number that stands apart or a symbol, and can do so twice.
    again = reader({(0, 0): [read("Knowledge index")], (0, 60): [read("TRAINING &. EVALUATION", top=60)]})
    texts = [read("Knowledge index"), read("TRAINING&.EVALUATION", top=60)]

    result = check_text.compare(["5  Knowledge index", "TRAINING & EVALUATION"], texts, again)

    assert [(label["found"], label["second"]) for label in result["labels"]] == [(0, "same"), (0, "same")]


def test_a_letter_left_out_of_a_word_differs():
    again = reader({(0, 0): [read("Mitocondria")]})

    result = check_text.compare(["Mitochondria"], [read("Mitocondria")], again)

    assert result["labels"][0]["second"] == "differs"


def test_a_letter_read_twice_where_the_label_has_a_symbol_does_not_differ():
    # The degree sign came back as a small o, and the arrow as a letter, both times.
    texts = [read("-80 oC"), read("ATP l", top=60)]
    again = reader({(0, 0): [texts[0]], (0, 60): [texts[1]]})

    result = check_text.compare(["−80 °C", "ATP ↓"], texts, again)

    assert [(label["found"], label["second"]) for label in result["labels"]] == [(0, "same"), (0, "same")]


def test_a_second_reading_that_only_leaves_out_a_letter_of_the_first_is_not_believed():
    # The picture says "ratiio". Enlarged, OCR ran the two i together and read the word the label asks for.
    texts = [read("AMP/ATP", left=100, top=100), read("ratiio↑", left=105, top=126)]
    again = reader({(100, 100): [texts[0]], (105, 126): [read("ratio ↑", left=105, top=126)]})

    result = check_text.compare(["AMP/ATP ratio ↑"], texts, again)

    assert result["labels"] == [
        {"text": "AMP/ATP ratio ↑", "found": 0, "listed": 1, "closest": "AMP/ATP ratiio↑", "second": "differs", "crop": None}
    ]


def test_what_ocr_reads_for_a_greek_letter_a_subscript_or_a_superscript_does_not_differ():
    labels = ["NF-κB", "CO₂ flux", "Ω resistance", "π/2 phase", "10⁶ cells", "ΔG = −30 kJ/mol"]
    # "cOflux": the subscript left out and, as often with a letter of one shape in both cases, the capital read small.
    texts = [read(text, top=60 * row) for row, text in enumerate(["NF-kB", "cOflux", "Q resistance", "TT/2 phase", "10 cells", "△G = -30 kJ/mol"])]
    again = reader({(0, 60 * row): [text] for row, text in enumerate(texts)})

    result = check_text.compare(labels, texts, again)

    assert [(label["found"], label["second"]) for label in result["labels"]] == [(0, "same")] * 6


def test_letters_ocr_puts_beside_a_symbol_do_not_differ():
    # "−80 ℃" came back as "-80°℃C", read twice: OCR spells a symbol out around it as well as in its place.
    again = reader({(0, 0): [read("-80°℃C 保存")], (0, 60): [read("NF-kBb", top=60)]})

    result = check_text.compare(["−80 ℃ 保存", "NF-κB"], [read("-80°℃C 保存"), read("NF-kBb", top=60)], again)

    assert [label["second"] for label in result["labels"]] == ["same", "differs"]  # the b stands beside a B, not a κ


def test_a_capital_read_as_a_small_letter_does_not_differ():
    again = reader({(0, 0): [read("cross-attention")]})

    result = check_text.compare(["Cross-attention"], [read("cross-attention")], again)

    assert result["labels"][0]["second"] == "same"


def test_a_stroke_read_as_a_letter_at_the_edge_of_a_text_does_not_differ():
    # The border of a card stood right before the label "If approved" and was read as a letter, both times.
    again = reader({(0, 0): [read("Iif approved")]})

    result = check_text.compare(["If approved"], [read("Iifapproved")], again)

    assert result["labels"] == [{"text": "If approved", "found": 0, "listed": 1, "closest": "Iifapproved", "second": "same", "crop": None}]


def test_a_stroke_at_the_edge_of_the_second_line_of_a_text_does_not_differ_either():
    texts = [read("Feed", left=100, top=100), read("Forward1", left=100, top=126)]
    again = reader({(100, 100): [texts[0]], (100, 126): [texts[1]]})

    result = check_text.compare(["Feed Forward"], texts, again)

    assert result["labels"][0]["second"] == "same"


def test_a_letter_too_many_inside_a_word_still_differs_when_it_is_a_stroke():
    again = reader({(0, 0): [read("ratiio")], (0, 60): [read("Additiion", top=60)]})

    result = check_text.compare(["ratio", "Addition"], [read("ratiio"), read("Additiion", top=60)], again)

    assert [label["second"] for label in result["labels"]] == ["differs", "differs"]


def test_a_bar_read_at_the_edge_of_a_label_does_not_hide_the_label():
    result = check_text.compare(["Nucleus", "Golgi"], [read("|Nucleus"), read("Golgi|", top=60)])

    assert found(result) == {"Nucleus": 1, "Golgi": 1}


def test_a_second_reading_that_explains_no_more_is_not_used():
    again = reader({(0, 0): [read("Mitocandrla")]})

    result = check_text.compare(["Mitochondria"], [read("Mitocondria")], again)

    assert result["labels"] == [{"text": "Mitochondria", "found": 0, "listed": 1, "closest": "Mitocondria", "second": None, "crop": None}]


def test_a_word_put_before_a_label_is_extra_once_the_second_reading_parts_the_two():
    label = "Retrieve relevant evidence, then answer."
    again = reader({(0, 0): [read("Takeaway:"), read("Retrieve relevant evidence, then answer.", left=110)]})

    result = check_text.compare([label], [read("Takeaway:Retrieve relevant evidence,then answer.")], again)

    assert found(result) == {label: 1}
    assert result["labels"][0]["second"] == "found"
    assert result["extra"] == ["Takeaway:"]


def test_a_word_put_before_a_label_and_read_with_it_twice_differs():
    label = "Retrieve relevant evidence, then answer."
    again = reader({(0, 0): [read("Takeaway: Retrieve relevant evidence, then answer.")]})

    result = check_text.compare([label], [read("Takeaway:Retrieve relevant evidence,then answer.")], again)

    assert result["labels"][0]["second"] == "differs"


def test_a_misspelt_line_of_a_label_on_two_lines_differs():
    texts = [read("AMP/ATP", left=100, top=100), read("ratiio↑", left=105, top=126)]
    again = reader({(100, 100): [texts[0]], (105, 126): [read("ratiio ↑", left=105, top=126)]})

    result = check_text.compare(["AMP/ATP ratio ↑"], texts, again)

    assert result["labels"] == [
        {"text": "AMP/ATP ratio ↑", "found": 0, "listed": 1, "closest": "AMP/ATP ratiio↑", "second": "differs", "crop": None}
    ]


def test_a_second_reading_that_holds_the_letter_the_first_left_out_does_not_differ():
    # The first reading left the h out. Enlarged, it was read, with the border before the word read as an I.
    again = reader({(0, 0): [read("IMitochondria")]})

    result = check_text.compare(["Mitochondria"], [read("Mitocondria")], again)

    assert result["labels"][0]["second"] == "same"


def test_a_second_reading_that_holds_the_left_out_letter_and_reads_an_i_as_an_l_does_not_differ():
    again = reader({(0, 0): [read("Mitochondrla")]})

    result = check_text.compare(["Mitochondria"], [read("Mitocondria")], again)

    assert result["labels"][0]["second"] == "same"


def test_a_letter_read_at_the_edge_of_the_first_reading_only_is_not_held_against_the_figure():
    # The border of a card came back as a J before "Oscillation"; enlarged, it was gone.
    again = reader({(0, 0): [read("Oscillation")]})

    result = check_text.compare(["Oscillation"], [read("JOscillation")], again)

    assert (result["labels"][0]["found"], result["labels"][0]["second"]) == (1, "found")


def test_a_letter_inside_a_word_that_only_the_first_reading_has_still_differs():
    # An image tool puts letters into words, and enlarged, OCR may leave one out: inside a word the
    # first reading stands. Read whole, OCR has hardly ever put a letter in.
    again = reader({(0, 0): [read("Question")]})

    result = check_text.compare(["Question"], [read("Questiopn")], again)

    assert (result["labels"][0]["found"], result["labels"][0]["second"]) == (0, "differs")


def test_a_capital_read_before_its_small_letter_is_no_doubled_letter():
    # The border of a card came back as an S before "Skill"; enlarged, it was gone.
    again = reader({(0, 0): [read("Skill set")]})

    result = check_text.compare(["Skill set"], [read("Sskill set")], again)

    assert (result["labels"][0]["found"], result["labels"][0]["second"]) == (1, "found")


def test_a_run_of_strokes_read_one_short_twice_is_no_verdict():
    # "Ill" is three equal bars in a sans-serif face, and OCR read two, whole and enlarged; "ll" in
    # "Oscillation" the same way. The picture may be right: only a look at it can tell.
    texts = [read("llumina"), read("Oscilation", top=60)]
    again = reader({(0, 0): [texts[0]], (0, 60): [texts[1]]})

    result = check_text.compare(["Illumina", "Oscillation"], texts, again)

    assert [label["second"] for label in result["labels"]] == ["merged", "merged"]


def test_a_run_of_thin_letters_that_are_not_all_one_letter_is_no_verdict_either():
    # "observability" was read "observabiity": OCR took "ili" for two strokes.
    again = reader({(0, 0): [read("Evaluation&observabiity")]})

    result = check_text.compare(["Evaluation & observability"], [read("Evaluation&observabiity")], again)

    assert result["labels"][0]["second"] == "merged"


def test_a_letter_left_out_beside_a_doubled_one_still_differs():
    # Only the run itself is in doubt: "Colagen" lacks an l of "ll", "Colgen" an a, which no run explains.
    texts = [read("Colagen fibre"), read("Colgen gel", top=60)]
    again = reader({(0, 0): [texts[0]], (0, 60): [texts[1]]})

    result = check_text.compare(["Collagen fibre", "Collagen gel"], texts, again)

    assert [label["second"] for label in result["labels"]] == ["merged", "differs"]


def test_kana_that_ocr_does_not_read_is_not_held_against_the_figure():
    # The OCR model reads Chinese characters but not Japanese kana, which it leaves out.
    again = reader({(0, 0): [read("質の合成")]})

    result = check_text.compare(["タンパク質の合成"], [read("質の合成")], again)

    assert result["labels"][0]["second"] == "same"


def test_a_wrong_chinese_character_still_differs():
    again = reader({(0, 0): [read("明确间题")]})

    result = check_text.compare(["明确问题"], [read("明确间题")], again)

    assert result["labels"][0]["second"] == "differs"


def test_a_misspelt_copy_of_a_label_listed_several_times_differs():
    # Three "Add & Norm" boxes; the third says "Add & Nrom".
    texts = [read("Add & Norm"), read("Add & Norm", top=60), read("Add & Nrom", top=120)]
    again = reader({(0, 120): [texts[2]]})

    result = check_text.compare(["Add & Norm"] * 3, texts, again)

    assert result["labels"] == [
        {"text": "Add & Norm", "found": 2, "listed": 3, "closest": "Add & Nrom", "second": "differs", "crop": None}
    ]
    assert result["extra"] == []


def test_a_line_read_right_only_when_enlarged_completes_its_label():
    texts = [read("Hepatic", left=100, top=100), read("glucose", left=100, top=126), read("↑ ndno", left=100, top=152)]
    again = reader({(100, 100): [texts[0]], (100, 126): [texts[1]], (100, 152): [read("output ↓", left=100, top=152)]})

    result = check_text.compare(["Hepatic glucose output ↓"], texts, again)

    assert result["labels"] == [
        {"text": "Hepatic glucose output ↓", "found": 1, "listed": 1, "closest": "Hepatic glucose", "second": "found", "crop": None}
    ]
    assert result["extra"] == []


def test_only_the_texts_that_no_label_explains_are_read_a_second_time():
    texts = [read("Nucleus"), read("Mitocondria", top=60), read("Lorem ipsum", top=120), read("O", top=180)]
    again = reader({(0, 60): [texts[1]], (0, 120): [texts[2]]})

    check_text.compare(["Nucleus", "Mitochondria"], texts, again)

    assert sorted(again.asked) == [(0, 60), (0, 120)]  # not the label that was found, and not the mark


def test_what_is_read_around_a_place_is_not_part_of_its_second_reading():
    place = (100, 100, 300, 130)

    assert check_text.centred_in((110, 102, 290, 128), place)
    assert check_text.centred_in((90, 96, 200, 134), place)  # a piece of the line itself, cut a little wider
    assert not check_text.centred_in((100, 132, 300, 160), place)  # the line below, half of it inside the cut
    assert not check_text.centred_in((310, 100, 420, 130), place)  # the text to its right


def report_of(labels, texts, again=None):
    return {**check_text.compare(labels, texts, again), "unsure": 0, "type": None, "overall": "look"}


def test_a_label_that_differs_is_reported_as_what_the_image_says():
    again = reader({(0, 0): [read("Questoin + evidence + rules")], (0, 60): [read("Knowledge index", top=60)]})
    texts = [read("Questoin+evidence+rules"), read("Knowledge index", top=60)]

    lines = check_text.summary(report_of(["Question + evidence + rules", "5  Knowledge index"], texts, again)).splitlines()

    assert lines[0] == 'DIFFERS      Question + evidence + rules   the image says "Questoin+evidence+rules"'
    assert lines[1] == 'MISSING      5  Knowledge index   closest text in the image, read twice: "Knowledge index"'
    assert lines[-1].startswith(
        "OVERALL LOOK  1 labels differ from the image, 1 others not read as listed, 0 texts not in the list. "
        "Correct what a DIFFERS line names, and do not check it against the figure"
    )


def test_a_label_found_on_the_second_reading_says_what_the_first_was():
    again = reader({(0, 0): [read("6"), read("User question", left=30)]})

    lines = check_text.summary(report_of(["6  User question"], [read("5 User question")], again)).splitlines()

    assert lines[0] == 'FOUND    1x  6  User question   on the second reading, enlarged; the first was "5 User question"'


def test_a_run_read_one_short_is_reported_as_a_place_to_count_letters_in():
    texts = [read("llumina")]
    again = reader({(0, 0): [texts[0]]})

    lines = check_text.summary(report_of(["Illumina"], texts, again)).splitlines()

    assert lines[0] == (
        'MISSING      Illumina   read twice as "llumina", one letter short in a doubled letter or a run of thin '
        "ones (ll, ili): OCR runs those together, so count the letters in the picture"
    )
    assert lines[-1].startswith("OVERALL LOOK  0 labels differ from the image, 1 others not read as listed")


def test_a_misspelt_copy_is_reported_with_the_places_that_were_right():
    texts = [read("Add & Norm"), read("Add & Norm", top=60), read("Add & Nrom", top=120)]
    again = reader({(0, 120): [texts[2]]})

    lines = check_text.summary(report_of(["Add & Norm"] * 3, texts, again)).splitlines()

    assert lines[0] == 'DIFFERS      Add & Norm   found 2x of 3; in the other place the image says "Add & Nrom"'
    assert lines[-1].startswith("OVERALL LOOK  1 labels differ from the image, 0 others not read as listed")


def matching(labels, texts):
    return {**check_text.compare(labels, texts), "unsure": 0, "type": None, "overall": "match"}


def test_the_last_line_of_a_match_does_not_claim_the_labels_that_were_left_unread():
    texts = [read("Define goal"), read("Train", top=60)]

    all_read = check_text.summary(matching(["Define goal", "Train"], texts)).splitlines()[-1]
    two_unread = check_text.summary(matching(["Define goal", "Train", "1", "7"], texts)).splitlines()[-1]

    assert all_read.startswith("OVERALL MATCH  Every label was read in as many places as listed, and no other text. ")
    assert two_unread.startswith(
        "OVERALL MATCH  Every label except the 2 marked UNREAD was read in as many places as listed, and no other text. "
    )


# --- the command ------------------------------------------------------------------------------


def load_font(size, candidates=LATIN_FONTS):
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def make_figure(path, texts, font=None):
    """A white page with one boxed text per row; a text may hold a line break."""
    font = font or load_font(44)
    image = Image.new("RGB", (1200, 150 * len(texts) + 60), "white")
    draw = ImageDraw.Draw(image)
    for row, text in enumerate(texts):
        top = 40 + 150 * row
        draw.rounded_rectangle((80, top, 1120, top + 120), radius=18, fill=(222, 235, 247), outline=(49, 104, 157), width=3)
        draw.multiline_text((600, top + 60), text, font=font, fill=(30, 30, 30), anchor="mm", align="center")
    image.save(path)
    return path


def run(*args, cwd):
    return subprocess.run([UV, "run", "--quiet", str(SCRIPT), *map(str, args)], cwd=cwd, capture_output=True, text=True)


def test_every_label_of_a_correct_figure_is_found(tmp_path):
    make_figure(tmp_path / "fig.png", ["Multi-Head Attention", "Add & Norm", "Feed Forward", "Add & Norm"])

    labels = ["Multi-Head Attention", "Add & Norm", "Feed Forward", "Add & Norm"]  # once for each place
    proc = run("fig.png", *(part for label in labels for part in ("--label", label)), cwd=tmp_path)

    assert proc.returncode == 0, proc.stderr
    lines = proc.stdout.splitlines()
    assert "FOUND    1x  Multi-Head Attention" in lines
    assert "FOUND    2x  Add & Norm" in lines
    assert "FOUND    1x  Feed Forward" in lines
    assert lines[-1].startswith("OVERALL MATCH")


def test_a_wrong_label_in_the_figure_is_reported_with_what_stands_there(tmp_path):
    make_figure(tmp_path / "fig.png", ["Nucleus", "Mitocondria"])
    (tmp_path / "labels.txt").write_text("Nucleus\nMitochondria\n\n", encoding="utf-8")

    proc = run("fig.png", "--labels", "labels.txt", cwd=tmp_path)

    assert proc.returncode == 0, proc.stderr  # the check ran; its findings are in the lines
    lines = proc.stdout.splitlines()
    assert 'DIFFERS      Mitochondria   the image says "Mitocondria"' in lines
    assert lines[-1].startswith("OVERALL LOOK  1 labels differ from the image, 0 others not read as listed, 0 texts not in the list. ")


def test_a_label_of_which_the_figure_shows_only_a_part_is_missing_not_different(tmp_path):
    make_figure(tmp_path / "fig.png", ["Nucleus", "Knowledge index"])

    proc = run("fig.png", "--label", "Nucleus", "--label", "5  Knowledge index", cwd=tmp_path)

    assert 'MISSING      5  Knowledge index   closest text in the image, read twice: "Knowledge index"' in proc.stdout.splitlines()


def test_the_second_reading_of_a_line_leaves_out_the_lines_above_and_below_it(tmp_path):
    # Three lines set close together; the middle one is misspelt.
    image = Image.new("RGB", (1200, 300), "white")
    draw = ImageDraw.Draw(image)
    for row, line in enumerate(["Outer membrane", "Mitocondria", "Inner membrane"]):
        draw.text((120, 60 + 56 * row), line, font=load_font(44), fill=(30, 30, 30))
    image.save(tmp_path / "fig.png")

    proc = run("fig.png", "--label", "Outer membrane", "--label", "Mitochondria", "--label", "Inner membrane", "--json", cwd=tmp_path)

    report = json.loads(proc.stdout)
    assert report["labels"][1] == {"text": "Mitochondria", "found": 0, "listed": 1, "closest": "Mitocondria", "second": "differs", "crop": None}
    assert [label["found"] for label in report["labels"]] == [1, 0, 1]
    assert report["extra"] == []


def test_a_label_found_in_fewer_places_than_listed_is_reported(tmp_path):
    make_figure(tmp_path / "fig.png", ["Add & Norm", "Softmax", "Add & Norm"])
    (tmp_path / "labels.txt").write_text("Add & Norm\nAdd & Norm\nAdd & Norm\nSoftmax\n+\n", encoding="utf-8")

    proc = run("fig.png", "--labels", "labels.txt", cwd=tmp_path)

    lines = proc.stdout.splitlines()
    assert "COUNT    2x  Add & Norm   listed 3x" in lines
    assert "FOUND    1x  Softmax" in lines
    assert "UNREAD       +   a symbol or a single character, which OCR often misses: look for it in the image" in lines
    assert lines[-1].startswith("OVERALL LOOK")


def test_a_misspelt_copy_of_a_label_in_the_figure_differs(tmp_path):
    make_figure(tmp_path / "fig.png", ["Add & Norm", "Add & Nrom", "Add & Norm"])

    proc = run("fig.png", *(["--label", "Add & Norm"] * 3), cwd=tmp_path)

    assert 'DIFFERS      Add & Norm   found 2x of 3; in the other place the image says "Add & Nrom"' in proc.stdout.splitlines()


def test_the_report_prints_on_a_pipe_whose_code_page_lacks_its_characters(tmp_path):
    # A Windows pipe takes the ANSI code page, which has no subscript two and no Chinese.
    make_figure(tmp_path / "fig.png", ["Nucleus"])

    proc = subprocess.run(
        [UV, "run", "--quiet", str(SCRIPT), "fig.png", "--label", "Nucleus", "--label", "CO₂ 通量"],
        cwd=tmp_path, capture_output=True, env={**os.environ, "PYTHONIOENCODING": "cp1252"},
    )

    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
    assert "MISSING      CO₂ 通量" in proc.stdout.decode("utf-8").splitlines()


def test_text_the_brief_did_not_ask_for_is_reported(tmp_path):
    make_figure(tmp_path / "fig.png", ["Nucleus", "Figure 1"])

    proc = run("fig.png", "--label", "Nucleus", cwd=tmp_path)

    assert 'EXTRA        "Figure 1"' in proc.stdout.splitlines()
    assert proc.stdout.splitlines()[-1].startswith("OVERALL LOOK")


def test_a_label_on_two_lines_in_the_figure_is_found(tmp_path):
    make_figure(tmp_path / "fig.png", ["Positional\nEncoding", "Softmax"])

    proc = run("fig.png", "--label", "Positional Encoding", "--label", "Softmax", "--json", cwd=tmp_path)

    report = json.loads(proc.stdout)
    assert {label["text"]: label["found"] for label in report["labels"]} == {"Positional Encoding": 1, "Softmax": 1}
    assert report["extra"] == [] and report["overall"] == "match"


def test_json_report_has_the_documented_keys(tmp_path):
    make_figure(tmp_path / "fig.png", ["Nucleus"])

    proc = run("fig.png", "--label", "Nucleus", "--json", cwd=tmp_path)

    report = json.loads(proc.stdout)
    assert list(report) == ["input", "size", "labels", "unread", "extra", "extra_crops", "ignored_marks", "unsure", "type", "overall"]
    assert report["extra_crops"] == []
    assert report["size"] == [1200, 210]
    assert report["labels"] == [{"text": "Nucleus", "found": 1, "listed": 1, "closest": None, "second": None, "crop": None}]


def test_the_size_of_the_type_is_measured(tmp_path):
    # Four lines set in 44 px and two in 24 px, on a picture 960 px high.
    texts = ["Collect and label the data", "Split by time and by group", "Fit on the training set", "Select on validation"]
    image = Image.new("RGB", (1600, 960), "white")
    draw = ImageDraw.Draw(image)
    for row, line in enumerate(texts):
        draw.text((80, 60 + 110 * row), line, font=load_font(44), fill=(30, 30, 30))
    for row, line in enumerate(["Report the held-out metrics", "Keep the test data apart"]):
        draw.text((80, 600 + 80 * row), line, font=load_font(24), fill=(30, 30, 30))
    image.save(tmp_path / "fig.png")
    labels = [part for line in texts + ["Report the held-out metrics", "Keep the test data apart"] for part in ("--label", line)]

    report = json.loads(run("fig.png", *labels, "--json", cwd=tmp_path).stdout)
    lines = run("fig.png", *labels, cwd=tmp_path).stdout.splitlines()

    assert report["type"]["lines"] == 6
    assert report["type"]["median_px"] == pytest.approx(44, abs=2)
    assert report["type"]["small_px"] == pytest.approx(24, abs=2)
    (line,) = [line for line in lines if line.startswith("TYPE  ")]
    # A picture 960 px high that fills a slide 540 pt high: 44 px are 24.8 pt, and 24 px are 13.5 pt.
    assert re.fullmatch(
        r"TYPE  6 lines measured: 4\d(\.\d)? px at the median and 2\d(\.\d)? px in the smallest tenth, "
        r"4\.\d% and 2\.\d% of the picture's height; on a slide of 13\.33 x 7\.5 in that the picture fills, "
        r"2[45](\.\d)? and 1[34](\.\d)? pt",
        line,
    ), line
    assert lines.index(line) == len(lines) - 2  # just before the OVERALL line


def test_the_size_of_the_type_in_print_takes_the_printed_width(tmp_path):
    make_figure(tmp_path / "fig.png", ["Multi-Head Attention", "Feed Forward"])  # 44 px type on a picture 1200 px wide

    proc = run("fig.png", "--label", "Multi-Head Attention", "--label", "Feed Forward", "--width-mm", "100", cwd=tmp_path)

    (line,) = [line for line in proc.stdout.splitlines() if line.startswith("TYPE  ")]
    # 1200 px across 100 mm are 304.8 dpi: 44 px are 10.4 pt.
    assert re.search(r"; printed 100 mm wide, 1\d(\.\d)? and 1\d(\.\d)? pt$", line), line
    printed = float(re.search(r"printed 100 mm wide, ([\d.]+) and", line).group(1))
    assert printed == pytest.approx(10.4, abs=0.6)


@pytest.mark.skipif(not any(Path(path).exists() for path in CHINESE_FONTS), reason="no Chinese font to draw the figure with")
def test_chinese_labels_are_compared(tmp_path):
    make_figure(tmp_path / "fig.png", ["实验室测定", "遥感影像获取（Sentinel-2）"], font=load_font(44, CHINESE_FONTS))
    (tmp_path / "labels.txt").write_text("实验室测定\n遥感影像获取（Sentinel-2）\n特征构建\n", encoding="utf-8")

    proc = run("fig.png", "--labels", "labels.txt", "--json", cwd=tmp_path)

    report = json.loads(proc.stdout)
    assert {label["text"]: label["found"] for label in report["labels"]} == {
        "实验室测定": 1, "遥感影像获取（Sentinel-2）": 1, "特征构建": 0,
    }


def test_the_places_of_labels_that_were_not_found_are_written_enlarged_on_request(tmp_path):
    make_figure(tmp_path / "fig.png", ["Nucleus", "Mitocondria", "Knowledge index"])
    labels = ["Nucleus", "Mitochondria", "5  Knowledge index", "Ribosome"]

    proc = run("fig.png", *(part for label in labels for part in ("--label", label)), "--crops", "look", cwd=tmp_path)

    assert proc.returncode == 0, proc.stderr
    lines = proc.stdout.splitlines()
    assert 'DIFFERS      Mitochondria   the image says "Mitocondria"   see look/1.png' in lines
    assert 'MISSING      5  Knowledge index   closest text in the image, read twice: "Knowledge index"   see look/2.png' in lines
    assert "MISSING      Ribosome" in lines  # nothing close was read, so there is no place to show
    assert sorted(path.name for path in (tmp_path / "look").iterdir()) == ["1.png", "2.png"]
    with Image.open(tmp_path / "look" / "1.png") as crop:
        # The word is about 250 x 45 px in the figure; the cut has room around it and is three times as large.
        assert 900 < crop.width < 2400 and 300 < crop.height < 900
        assert crop.convert("L").getextrema()[0] < 80  # the dark type is in it


def test_the_place_of_a_text_that_no_label_explains_is_written_too(tmp_path):
    # Is it a word the tool added, or a drawing that OCR took for letters? The cut-out shows which.
    make_figure(tmp_path / "fig.png", ["Nucleus", "Mitocondria", "Figure 1"])

    proc = run("fig.png", "--label", "Nucleus", "--label", "Mitochondria", "--crops", "look", cwd=tmp_path)
    report = json.loads(run("fig.png", "--label", "Nucleus", "--label", "Mitochondria", "--crops", "look", "--json", cwd=tmp_path).stdout)

    lines = proc.stdout.splitlines()
    assert 'DIFFERS      Mitochondria   the image says "Mitocondria"   see look/1.png' in lines
    assert 'EXTRA        "Figure 1"   see look/2.png' in lines
    assert sorted(path.name for path in (tmp_path / "look").iterdir()) == ["1.png", "2.png"]
    assert report["extra"] == ["Figure 1"] and report["extra_crops"] == ["look/2.png"]


def test_the_report_names_the_file_of_each_place_in_json_too(tmp_path):
    make_figure(tmp_path / "fig.png", ["Nucleus", "Mitocondria"])

    proc = run("fig.png", "--label", "Nucleus", "--label", "Mitochondria", "--crops", "look", "--json", cwd=tmp_path)

    report = json.loads(proc.stdout)
    assert [label["crop"] for label in report["labels"]] == [None, "look/1.png"]


def test_the_check_writes_nothing_and_needs_only_the_conversion_script_beside_it(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    for name in ("check_text.py", "editable.py"):  # it reads the figure with editable.py's OCR
        shutil.copy(SCRIPTS / name, scripts / name)
    make_figure(tmp_path / "fig.png", ["Nucleus"])

    proc = subprocess.run(
        [UV, "run", "--quiet", str(scripts / "check_text.py"), "fig.png", "--label", "Nucleus"],
        cwd=tmp_path, capture_output=True, text=True,
    )

    assert proc.returncode == 0, proc.stderr
    assert sorted(path.name for path in scripts.iterdir()) == ["check_text.py", "editable.py"]
    assert sorted(path.name for path in tmp_path.iterdir()) == ["fig.png", "scripts"]


def test_a_missing_figure_fails_with_one_line_on_stderr(tmp_path):
    proc = run("nope.png", "--label", "Nucleus", cwd=tmp_path)

    assert proc.returncode == 1
    assert proc.stdout == ""
    assert len(proc.stderr.strip().splitlines()) == 1 and "nope.png" in proc.stderr


@pytest.mark.parametrize("options", [[], ["--labels", "labels.txt", "--label", "Nucleus"]])
def test_the_labels_come_from_a_file_or_from_options_not_from_neither_or_both(tmp_path, options):
    make_figure(tmp_path / "fig.png", ["Nucleus"])
    (tmp_path / "labels.txt").write_text("Nucleus\n", encoding="utf-8")

    assert run("fig.png", *options, cwd=tmp_path).returncode == 2


def test_an_empty_label_file_is_an_error(tmp_path):
    make_figure(tmp_path / "fig.png", ["Nucleus"])
    (tmp_path / "labels.txt").write_text("\n\n", encoding="utf-8")

    proc = run("fig.png", "--labels", "labels.txt", cwd=tmp_path)

    assert proc.returncode == 1
    assert "no labels" in proc.stderr
