# /// script
# requires-python = ">=3.11,<3.13"
# dependencies = [
#   "rapidocr-onnxruntime==1.4.4",
#   "opencv-python-headless>=5.0,<6",
#   "numpy>=2,<3",
#   "pillow>=13,<14",
# ]
#
# [tool.uv]
# # rapidocr-onnxruntime asks for the GUI build of OpenCV; the headless build is the same cv2.
# override-dependencies = ["opencv-python ; sys_platform == 'never'"]
# # The packages as they were on the day these scripts were tested: a later release cannot change their results.
# exclude-newer = "2026-11-14T00:00:00Z"
# ///
"""Compare the text in a generated figure with the labels its brief asked for.

    uv run check_text.py figure.png --labels labels.txt

The figure is read with OCR, offline, and nothing is written unless --crops names a folder.
List a text once for each place it stands in the figure. Each label is reported with the
number of places it was read in; a label that was not read comes with the closest text that
was; text that no label explains is reported as extra. Every text that no label explains is
read a second time, cut out and enlarged. A label found that way counts as found. A label
whose closest text both readings spell the same way, and not as the label, is reported as
DIFFERS: the picture is wrong there. OCR leaves out and misreads symbols, Greek letters,
subscripts and numbers that stand apart, and runs a doubled letter together, so a MISSING,
COUNT or EXTRA line is a place to look at in the figure, not a verdict: --crops writes those
places, enlarged.
"""
import argparse
import collections
import contextlib
import difflib
import json
import logging
import math
import sys
import unicodedata
from pathlib import Path

if __name__ == "__main__":
    sys.dont_write_bytecode = True  # as a command, leave no __pycache__ next to this file

NEAR = 1.5  # text heights: the lines or parts of one label lie no further apart than this
CLOSE_ENOUGH = 0.6  # similarity from which a text in the image is offered as the closest one
ENLARGED = 3  # times: the size at which the place of a text is read a second time
AROUND = 0.6  # text heights of the picture kept around that place, in which OCR finds the line


DASHES = dict.fromkeys(map(ord, "\u2010\u2011\u2012\u2013\u2014\u2212"), "-")  # hyphens, dashes and the minus sign
ALIKE = {**DASHES, ord("\u00d7"): "x", ord("l"): "I", ord("0"): "O", ord("_"): None}
AS_LETTERS = {ord("|"): "I", ord("\u221a"): "V"}  # a bar and a root sign, as OCR reads them inside a text


def squash(text):
    """The text as OCR can tell it apart: without spaces, in one Unicode form, with x for the
    times sign, one kind of dash, capital I for small l and capital O for zero, which are one
    stroke and one ring in a sans-serif face, and without the underscore that stands for a
    subscript."""
    return "".join(unicodedata.normalize("NFKC", text).translate(ALIKE).split())


def letters(text):
    """The letters and digits of a text, which OCR reads more surely than its symbols."""
    return "".join(character for character in squash(text) if character.isalnum())


def within(short, long):
    """Is short what is left of long when some of its characters are taken out, or all of it?"""
    rest = iter(long)
    return all(character in rest for character in short)


def lacks_words(text, label):
    """Is a text the label with whole words of it left out, or with none? OCR leaves out a
    number that stands apart, a symbol, a line."""
    read, reached = letters(text).casefold(), {0}
    for word in filter(None, (letters(word).casefold() for word in label.split())):
        reached |= {start + len(word) for start in reached if read.startswith(word, start)}
    return len(read) in reached


STROKES = set("i1|!")  # what OCR makes of a line that stands beside a text: the border of a box, an arrow shaft


def one_of_doubled(text, start, end):
    """Is text[start:end] some copies of one letter that stands beside a copy of it that is kept, as
    OCR leaves one out where a word doubles a letter: "Illumina", read "llumina"?"""
    gone = set(text[start:end])
    return len(gone) == 1 and (text[start - 1 : start] in gone or text[end : end + 1] in gone)


def verdict(texts, label):
    """What the texts read for a label, one per line, say about its spelling in the picture:
    "differs" when they show letters or digits that are not the label's, or lack some inside a
    word; "merged" when all they lack is one copy of a letter that the label doubles, which OCR
    runs together, so that the picture may be right; else "same". Capitals aside. Not counted:
    what stands where the label has a symbol, a Greek letter, a subscript, a superscript or a
    character OCR does not read, which it reads as something else the same way every time or
    leaves out, and what it puts in beside one (a degree Celsius sign read with a C too many); and a stroke put in
    at the very start or end of a text, where a border or an arrow stood beside it."""
    if lacks_words(" ".join(texts), label):
        return "same"
    ours = [  # the label as it is compared, and for each character whether OCR reads it
        (folded, reads(character)) for character in label for squashed in squash(character) for folded in squashed.casefold()
    ]
    wanted, known = "".join(folded for folded, _ in ours), [sure for _, sure in ours]
    read = [squash(text).casefold() for text in texts]
    theirs = "".join(read)
    edges = {sum(map(len, read[:count])) for count in range(len(read) + 1)}
    merged = False
    for tag, start, end, low, high in difflib.SequenceMatcher(None, wanted, theirs, autojunk=False).get_opcodes():
        at = known[start:end] if end > start else known[max(start - 1, 0) : start + 1]  # what was put in: its neighbours
        if tag == "equal" or not all(at) or (end == start and not letters(theirs[low:high])):
            continue
        if end == start and set(theirs[low:high]) <= STROKES and (low in edges or high in edges):
            continue  # a border or an arrow beside the text
        if tag == "delete" and one_of_doubled(wanted, start, end):
            merged = True
            continue
        return "differs"
    return "merged" if merged else "same"


def variants(key):
    """key as it was read, and without the symbols at its start, at its end and at both: a bullet,
    an arrow or a leader line next to a label is read with it. A bar or a root sign that is left
    stands as the letter OCR reads it as."""
    start, end = 0, len(key)
    while start < end and not key[start].isalnum():
        start += 1
    while end > start and not key[end - 1].isalnum():
        end -= 1
    forms = filter(None, (key, key[start:], key[:end], key[start:end]))
    return tuple(dict.fromkeys(form.translate(AS_LETTERS) for form in forms))


def is_cjk(character):
    """Chinese characters, kana and hangul."""
    return "\u2e80" <= character <= "\u9fff" or "\uac00" <= character <= "\ud7af" or "\uf900" <= character <= "\ufaff"


def reads(character):
    """Does the OCR model read this character: a Latin letter or a digit, or a Chinese character? It
    leaves kana and hangul out."""
    return (character.isascii() and character.isalnum()) or "\u3400" <= character <= "\u9fff" or "\uf900" <= character <= "\ufaff"


def is_weak(label):
    """Does a label hold fewer than two letters or digits? OCR misses a plus sign in a circle, a
    white number on a badge and often a lone italic letter."""
    return sum(character.isalnum() for character in squash(label)) < 2


def is_mark(key, cjk_labels):
    """Is a text that no label explains a drawing and not wording? OCR reads circles and icons as
    single characters, often Chinese ones, and repeated shapes as repeated characters: a lipid
    bilayer as a row of zeros, a DNA helix as "DXOXOXO". Characters of a script that no label
    uses are no wording either. A number is wording however its zeros repeat: "p < 0.0001"."""
    letters = [
        character.casefold() for character in key if character.isalnum() and (cjk_labels or not is_cjk(character))
    ]
    kinds = len(set(letters))
    number = any(character in "123456789" for character in letters)
    return kinds <= 1 or (not number and len(letters) >= 6 and kinds <= len(letters) / 2)


def near(a, b):
    """Do two text boxes (left, top, right, bottom) lie close enough to belong to one label?"""
    reach = NEAR * max(a[3] - a[1], b[3] - b[1])
    return max(a[0], b[0]) - min(a[2], b[2]) <= reach and max(a[1], b[1]) - min(a[3], b[3]) <= reach


def follows(a, b):
    """Does text box b come after a as one reads: further down, or on the same line and to its right?"""
    lower = (b[1] + b[3]) - (a[1] + a[3])  # twice the distance between the middles of the two
    return lower > min(a[3] - a[1], b[3] - b[1]) or (lower > -min(a[3] - a[1], b[3] - b[1]) and b[0] > a[0])


SEPARATORS = set(";,/\u00b7\u2022\u3001")  # what stands between two labels read as one line: "AMPK: ...; ACC: ..."


def split_into(key, keys):
    """key as a run of whole label keys, with separators between them, or None. keys are tried in the
    order given."""
    runs = [[]] + [None] * len(key)
    for end in range(1, len(key) + 1):
        for part in keys:
            start = end - len(part)
            if start >= 0 and runs[start] is not None and key.startswith(part, start):
                runs[end] = runs[start] + [part]
                break
        else:
            if key[end - 1] in SEPARATORS and runs[end - 1] is not None:
                runs[end] = runs[end - 1]
    return runs[-1] or None


def chain(target, items, picked=()):
    """Indexes of unused items, each near the one before and after it as one reads, whose texts
    join into target; or None."""
    if not target:
        return picked
    for index, item in enumerate(items):
        if item["used"] or index in picked:
            continue
        if picked and not (near(items[picked[-1]]["box"], item["box"]) and follows(items[picked[-1]]["box"], item["box"])):
            continue
        for key in item["keys"]:
            if target.startswith(key) and (found := chain(target[len(key):], items, (*picked, index))):
                return found
    return None


def closest(key, items):
    """Indexes of the unused items that come closest to a label: the one most like it and, with
    it, the lines next to it for as long as each brings the whole closer. None when even they
    are not close."""

    def likeness(indexes):
        read = "".join(items[index]["key"] for index in indexes)
        return difflib.SequenceMatcher(None, key.casefold(), read.casefold()).ratio()

    rest = [index for index, item in enumerate(items) if not item["used"]]
    if not rest:
        return None
    group = [max(rest, key=lambda index: likeness([index]))]
    while True:
        beside = [
            index for index in rest
            if index not in group and any(near(items[index]["box"], items[member]["box"]) for member in group)
        ]
        longer = max((order for index in beside for order in ([*group, index], [index, *group])), key=likeness, default=group)
        if likeness(longer) <= likeness(group):
            return group if likeness(group) >= CLOSE_ENOUGH else None
        group = longer


def compare(labels, texts, again=None):
    """Compare the labels a figure should carry with the texts read from it.

    labels names a text once for each place it stands; texts is [(text, (left, top, right,
    bottom))]. Returns the labels with the number of places each was listed for and found in and,
    for one not found, the closest text; the symbols and single characters that were not read,
    which says nothing about the figure; the texts no label explains; and the number of marks
    ignored: texts without a letter or digit, and unexplained ones that OCR made of a drawing.

    again(box) is a second reading of the place of a text, as [(text, box)]. It is asked for
    every text that no label explains. OCR leaves letters out and runs a doubled one together,
    and it hardly ever puts one in, but for a border or an arrow beside a text that it reads as a
    letter. So a second reading that has every letter of the first and more stands in for the
    first; one that lacks letters of the first does so only where all it lacks stands at its
    start or its end, and inside a word the first stands, as where the picture says "ratiio" and
    the enlarged reading "ratio"; and one that is spelt otherwise is used where it lets more
    labels be found. Each label then says what the second reading did for it: "found" (its
    closest text is then what was read at first); "differs" when its closest text, read twice,
    is spelt otherwise than the label; "merged" when all that text lacks is one copy of a letter
    the label doubles, which OCR runs together; "same" when the two readings agree and it is
    not spelt otherwise. "places" gives, for each label that was not found in every place, the
    boxes of its closest text, and "extra_places" the box of each text that no label explains.
    """
    texts = list(texts)
    result, loose = explain(labels, texts)
    first = {label["text"]: label for label in result["labels"]}
    twice = {}  # the place of a text read a second time: do the two readings agree in the letters both show?
    for place in loose if again else ():
        pieces = again(place[1])
        before, after = letters(place[0]).casefold(), letters("".join(text for text, _ in pieces)).casefold()
        agree = bool(after) and (within(after, before) or within(before, after))
        twice.update(dict.fromkeys([place[1], *(box for _, box in pieces)], agree))
        if after != before and within(after, before) and after not in before:
            continue  # enlarged, OCR left letters inside the text out: the first reading stands
        trial = [pair for pair in texts if pair is not place] + pieces
        better, _ = explain(labels, trial)
        fuller = agree and after != before  # the first reading left letters out, or read a border as one
        if places_read(better) > places_read(result) or (fuller and places_read(better) == places_read(result)):
            texts, result = trial, better
    places = {}  # a label that was not found: where its closest text stands
    for label in result["labels"]:
        boxes, lines = label.pop("places"), label.pop("lines")
        was = first.get(label["text"], {"found": 0, "closest": None})
        label["second"], label["crop"] = None, None
        if label["found"] > was["found"]:
            label["closest"], label["second"] = was["closest"], "found"
        elif boxes:
            places[label["text"]] = boxes
            if all(twice.get(box) for box in boxes):
                label["second"] = verdict(lines, label["text"])
    return {**result, "places": places}


def places_read(result):
    return sum(min(label["found"], label["listed"]) for label in result["labels"])


def explain(labels, texts):
    """One comparison of the labels with the texts: the report, in which each label carries the
    places and the lines of its closest text, and the texts that no label explains."""
    listed = collections.Counter(labels)
    wanted = [label for label in listed if any(character.isalnum() for character in squash(label))]
    keys = {squash(label).translate(AS_LETTERS): label for label in wanted}
    longest_first = sorted(keys, key=len, reverse=True)
    counts = dict.fromkeys(wanted, 0)
    items, ignored = [], 0
    for pair in texts:
        text, box = pair
        key = squash(text)
        if any(character.isalnum() for character in key):
            items.append({"text": text, "key": key, "keys": variants(key), "box": box, "used": False, "pair": pair})
        else:
            ignored += 1
    # Whole labels first, the longest first: a label is one text or one text per line, and the
    # first line of a long label may be a shorter label of its own.
    for key in longest_first:
        while pieces := chain(key, items):
            counts[keys[key]] += 1
            for index in pieces:
                items[index]["used"] = True
    for item in items:  # then several labels read as one line, or a label with a symbol at its end
        if item["used"]:
            continue
        if parts := next(filter(None, (split_into(key, longest_first) for key in item["keys"])), None):
            item["used"] = True
            for part in parts:
                counts[keys[part]] += 1
    report, unread, loose = [], [], []
    for label in listed:
        if label not in counts or (is_weak(label) and counts[label] != listed[label]):
            unread.append(label)
            continue
        # A label found in fewer places than listed: the closest text may be a misspelt copy of it.
        group = [] if counts[label] >= listed[label] else [items[index] for index in closest(squash(label), items) or ()]
        for item in group:
            item["used"] = True  # reported here, so not again as extra text
        loose += group
        report.append({
            "text": label, "found": counts[label], "listed": listed[label],
            "closest": " ".join(item["text"] for item in group) or None,
            "places": [item["box"] for item in group], "lines": [item["text"] for item in group],
        })
    cjk_labels = any(is_cjk(character) for key in keys for character in key)
    extra = []
    for item in items:
        if not item["used"]:
            if is_mark(item["key"], cjk_labels):
                ignored += 1
            else:
                extra.append(item)
                loose.append(item)
    result = {
        "labels": report, "unread": unread, "extra": [item["text"] for item in extra],
        "extra_places": [[item["box"]] for item in extra], "ignored_marks": ignored,
    }
    return result, [item["pair"] for item in loose]


SLIDE_PT = (960, 540)  # a widescreen slide in PowerPoint, 13.333 x 7.5 inches


def type_sizes(items, width, height, width_mm):
    """How large the type is: the font sizes of the lines of text (four characters and more), measured on their strokes."""
    import numpy as np

    sizes = [item["font_px"] for item in items if sum(character.isalnum() for character in item["text"]) >= 4]
    if not sizes:
        return None
    pixels = [float(np.median(sizes)), float(np.percentile(sizes, 10))]
    on_slide = min(SLIDE_PT[0] / width, SLIDE_PT[1] / height)  # points per pixel when the picture fills the slide
    in_print = 72 * width_mm / (25.4 * width) if width_mm else None
    return {
        "lines": len(sizes),
        "median_px": round(pixels[0], 1),
        "small_px": round(pixels[1], 1),
        "share_of_height": [round(value / height, 4) for value in pixels],
        "slide_pt": [round(value * on_slide, 1) for value in pixels],
        "print_pt": [round(value * in_print, 1) for value in pixels] if in_print else None,
        "width_mm": width_mm,
    }


def bounds(quad):
    return float(quad[:, 0].min()), float(quad[:, 1].min()), float(quad[:, 0].max()), float(quad[:, 1].max())


def centred_in(box, place):
    """Does the middle of a text box lie in a place? What is read around a place belongs to its neighbours."""
    across, down = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    return place[0] <= across <= place[2] and place[1] <= down <= place[3]


def enlarged(editable, picture, min_confidence):
    """A second reading for compare(): the place of a text is cut out with a little of the
    picture around it and read at ENLARGED times its size, where OCR parts close-set numbers,
    and as it stands, where the first reading may have turned the line upside down. Only what
    lies in the place itself is returned."""
    import cv2

    def again(box):
        left, top, right, bottom = box
        around = AROUND * (bottom - top)
        rows = slice(max(0, math.floor(top - around)), math.ceil(bottom + around))
        columns = slice(max(0, math.floor(left - around)), math.ceil(right + around))
        large = cv2.resize(picture[rows, columns], None, fx=ENLARGED, fy=ENLARGED, interpolation=cv2.INTER_CUBIC)
        pieces = []
        for text, quad, confidence in editable.read_text(large, as_it_stands=True):
            piece = bounds(quad / ENLARGED + (columns.start, rows.start))
            if text.strip() and confidence >= min_confidence and centred_in(piece, box):
                pieces.append((text.strip(), piece))
        return sorted(pieces, key=lambda piece: piece[1][0])

    return again


def write_crops(editable, picture, places, folder):
    """Write each place, the boxes of one text, with room around it for a number or a line that
    stands apart, at ENLARGED times its size: 1.png, 2.png and so on. Returns the files."""
    import cv2

    folder.mkdir(parents=True, exist_ok=True)
    files = []
    for number, boxes in enumerate(places, 1):
        room = 2 * max(bottom - top for _, top, _, bottom in boxes)
        rows = slice(max(0, math.floor(min(box[1] for box in boxes) - room)), math.ceil(max(box[3] for box in boxes) + room))
        columns = slice(max(0, math.floor(min(box[0] for box in boxes) - room)), math.ceil(max(box[2] for box in boxes) + room))
        large = cv2.resize(picture[rows, columns], None, fx=ENLARGED, fy=ENLARGED, interpolation=cv2.INTER_CUBIC)
        files.append(str(folder / f"{number}.png"))
        Path(files[-1]).write_bytes(editable.encode_png(large))
    return files


def check(path, labels, min_confidence, width_mm=None, crops=None):
    import editable  # here, so that compare() needs none of the OCR packages

    picture = editable.load_image(path)
    found = [(text.strip(), quad, confidence) for text, quad, confidence in editable.read_text(picture)]
    sure = [(text, bounds(quad)) for text, quad, confidence in found if text and confidence >= min_confidence]
    result = compare(labels, sure, enlarged(editable, picture, min_confidence))
    places, extra_places = result.pop("places"), result.pop("extra_places")
    shown = [label for label in result["labels"] if label["text"] in places]
    files = write_crops(editable, picture, [places[label["text"]] for label in shown] + extra_places, crops) if crops else []
    for label, file in zip(shown, files):
        label["crop"] = file
    clean = all(label["found"] == label["listed"] for label in result["labels"]) and not result["extra"]
    lines, _, _ = editable.split_items(found, min_confidence, picture.shape[:2])
    editable.erase_labels(picture, lines)  # this measures the strokes of every line; the erased copy is not used
    return {
        "input": str(path),
        "size": [picture.shape[1], picture.shape[0]],
        "labels": result["labels"], "unread": result["unread"],
        "extra": result["extra"], "extra_crops": files[len(shown):],
        "ignored_marks": result["ignored_marks"],
        "unsure": len(found) - len(sure),
        "type": type_sizes(lines, picture.shape[1], picture.shape[0], width_mm),
        "overall": "match" if clean else "look",
    }


def closest_text(label):
    """What a report line says about the closest text of a label that was not found in every place."""
    if label["second"] == "merged":
        return (
            f'read twice as "{label["closest"]}", one letter short in a doubled letter or a run of thin ones '
            "(ll, ili): OCR runs those together, so count the letters in the picture"
        )
    twice = ", read twice" if label["second"] == "same" else ""
    return f'closest text in the image{twice}: "{label["closest"]}"'


def summary(report):
    lines = []
    for label in report["labels"]:
        see = f"   see {label['crop']}" if label["crop"] else ""
        if label["found"] == label["listed"]:
            line = f"FOUND    {label['found']}x  {label['text']}"
            if label["second"] == "found":
                line += "   on the second reading, enlarged"
                line += f'; the first was "{label["closest"]}"' if label["closest"] else ""
            lines.append(line)
        elif label["second"] == "differs":
            where = ""
            if label["found"]:
                other = "the other place" if label["listed"] - label["found"] == 1 else "another place"
                where = f"found {label['found']}x of {label['listed']}; in {other} "
            lines.append(f'DIFFERS      {label["text"]}   {where}the image says "{label["closest"]}"{see}')
        elif label["found"]:
            line = f"COUNT    {label['found']}x  {label['text']}   listed {label['listed']}x"
            lines.append(line + (f"; {closest_text(label)}{see}" if label["closest"] else ""))
        elif label["closest"]:
            lines.append(f"MISSING      {label['text']}   {closest_text(label)}{see}")
        else:
            lines.append(f"MISSING      {label['text']}")
    lines += [
        f"UNREAD       {text}   a symbol or a single character, which OCR often misses: look for it in the image"
        for text in report["unread"]
    ]
    crops = report.get("extra_crops") or [None] * len(report["extra"])
    lines += [f'EXTRA        "{text}"' + (f"   see {crop}" if crop else "") for text, crop in zip(report["extra"], crops)]
    if report["ignored_marks"] or report["unsure"]:
        lines.append(
            f"NOTE  {report['ignored_marks']} marks were ignored (what OCR makes of icons, bullets and repeated shapes); "
            f"{report['unsure']} texts were read too uncertainly to count."
        )
    if size := report["type"]:
        share = size["share_of_height"]
        line = (
            f"TYPE  {size['lines']} lines measured: {size['median_px']:g} px at the median and {size['small_px']:g} px "
            f"in the smallest tenth, {share[0]:.1%} and {share[1]:.1%} of the picture's height; on a slide of "
            f"13.33 x 7.5 in that the picture fills, {size['slide_pt'][0]:g} and {size['slide_pt'][1]:g} pt"
        )
        if size["print_pt"]:
            line += f"; printed {size['width_mm']:g} mm wide, {size['print_pt'][0]:g} and {size['print_pt'][1]:g} pt"
        lines.append(line)
    if report["overall"] == "match":
        which = f"Every label except the {len(report['unread'])} marked UNREAD" if report["unread"] else "Every label"
        lines.append(
            f"OVERALL MATCH  {which} was read in as many places as listed, and no other text. "
            "OCR can miss an error: read the labels in the image too."
        )
    else:
        differs = sum(label["second"] == "differs" for label in report["labels"])
        others = sum(label["found"] != label["listed"] for label in report["labels"]) - differs
        line = (
            f"OVERALL LOOK  {differs} labels differ from the image, {others} others not read as listed, "
            f"{len(report['extra'])} texts not in the list."
        )
        if differs:
            line += (
                " Correct what a DIFFERS line names, and do not check it against the figure, where you read the word you "
                "expect: two readings, the second of them enlarged, spell it the same way, and not as the label."
            )
        if others or report["extra"]:
            line += " Look at the other lines in the image: OCR leaves out and misreads numbers, symbols and subscripts."
        lines.append(line)
    return "\n".join(lines)


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="check_text.py",
        description="Compare the text in a generated figure, read with OCR, with the labels its brief asked for.",
        epilog="List a text once for each place it stands in the figure. The lines of one label count as one "
        "label. Spaces are not compared; capitals are.",
    )
    parser.add_argument("input", metavar="IMAGE", type=Path, help="raster figure: PNG, JPEG or WebP")
    labels = parser.add_mutually_exclusive_group(required=True)
    labels.add_argument("--labels", metavar="FILE", type=Path, help="text file (UTF-8) with one label per line")
    labels.add_argument("--label", metavar="TEXT", action="append", help="one label; repeat for more")
    parser.add_argument(
        "--min-confidence", type=float, default=0.5, metavar="FLOAT",
        help="texts read with less confidence than this are counted, not compared (default: 0.5)",
    )
    parser.add_argument(
        "--width-mm", type=float, metavar="MM",
        help="the width the figure is printed at: the size of its type is then given in points at that width too",
    )
    parser.add_argument(
        "--crops", type=Path, metavar="DIR",
        help="write the place of each label that was not found and of each extra text, enlarged, as a PNG in this folder",
    )
    parser.add_argument("--json", action="store_true", help="print one JSON object instead of the lines")
    return parser.parse_args(argv)


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")  # a Windows pipe takes the ANSI code page, which lacks subscripts and Chinese
    args = parse_args(argv)
    logging.disable(logging.CRITICAL)  # the libraries' own logging stays out of the output
    try:
        labels = args.label or [line.strip() for line in args.labels.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
        if not labels:
            raise ValueError(f"no labels in {args.labels}")
        with contextlib.redirect_stdout(sys.stderr):  # stdout carries the report and nothing else
            report = check(args.input, labels, args.min_confidence, args.width_mm, args.crops)
    except Exception as exc:
        print(f"check_text.py: error: {' '.join(str(exc).split()) or type(exc).__name__}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False) if args.json else summary(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
