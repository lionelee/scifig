"""Compare two regress_text.sh runs label by label: every label whose verdict changed, and the totals."""
import collections, glob, json, os, sys

def kind(label):
    if label["found"] == label["listed"]:
        return "FOUND" + ("(2nd)" if label["second"] == "found" else "")
    if label["second"] == "differs":
        return "DIFFERS"
    if label["found"]:
        return "COUNT" + (f"/{label['second']}" if label["second"] else "")
    if label["closest"]:
        return "MISSING~" + (f"/{label['second']}" if label["second"] else "")
    return "MISSING"

def load(folder):
    runs = {}
    for f in sorted(glob.glob(os.path.join(folder, "*.json"))):
        if os.path.getsize(f):
            runs[os.path.basename(f)[:-5]] = json.load(open(f))
    return runs

a, b = load(sys.argv[1]), load(sys.argv[2])
totals = {name: collections.Counter() for name in ("before", "after")}
for name, runs in (("before", a), ("after", b)):
    for report in runs.values():
        for label in report["labels"]:
            totals[name][kind(label)] += 1
        totals[name]["EXTRA"] += len(report["extra"])
        totals[name]["UNREAD"] += len(report["unread"])
print("figures:", len(a), len(b))
for name in totals:
    print(name, dict(sorted(totals[name].items())))
for fig in sorted(set(a) & set(b)):
    la = {l["text"]: l for l in a[fig]["labels"]}
    lb = {l["text"]: l for l in b[fig]["labels"]}
    for text in la:
        ka, kb = kind(la[text]), kind(lb[text])
        if ka != kb:
            print(f"{fig}: {text!r}: {ka} {la[text]['closest']!r} -> {kb} {lb[text]['closest']!r}")
    ea, eb = a[fig]["extra"], b[fig]["extra"]
    if sorted(ea) != sorted(eb):
        print(f"{fig}: EXTRA {sorted(set(ea) - set(eb))} -> {sorted(set(eb) - set(ea))}")
