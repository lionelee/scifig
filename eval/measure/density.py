"""SciDraw's samples and ours, grouped by how much text a figure carries: do the sparse ones look bolder?"""
import collections, re, statistics
rows = collections.defaultdict(dict)
group_of = {}
for line in open("type.out", encoding="utf-8"):
    m = re.match(r"(\S+)\s+(\d+) lines\s+median ([\d.]+)% of the height.*\s(\S+/\S+\.png)\s*$", line)
    if m:
        rows[m.group(4)].update(lines=int(m.group(2)), type=float(m.group(3)))
        group_of[m.group(4)] = m.group(1)
for line in open("colour.out", encoding="utf-8"):
    m = re.match(r"\s*([\d.]+)%\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)%\s+(\S+/\S+\.png)", line)
    if m:
        rows[m.group(6)].update(fill=float(m.group(1)), cmed=float(m.group(2)), cp90=float(m.group(3)))
for line in open("bold.out", encoding="utf-8"):
    m = re.match(r"\s+([\d.]+)%\s+([\d.]+)%\s+(\d+)\s+(\d+)\s+([\d.]+)%\s+(\d+)%\s+(\d+)\s+([\d.]+)%\s+(\S+/\S+\.png)", line)
    if m:
        rows[m.group(9)].update(mid=float(m.group(1)), strong=float(m.group(2)), elements=int(m.group(4)), size=float(m.group(5)), ink=float(m.group(6)), cover=float(m.group(8)))
for line in open("stroke-each.out", encoding="utf-8"):
    m = re.match(r"\s+(\d+) px wide\s+coloured (\S+) px\s+dark (\S+) px\s+(\S+/\S+\.png)", line)
    if m:
        width = int(m.group(1))
        for key, value in (("coloured", m.group(2)), ("dark", m.group(3))):
            if value != "None":
                rows[m.group(4)][key] = 100 * float(value) / width

def med(items, key):
    values = [row[key] for row in items if key in row]
    return f"{statistics.median(values):6.2f}" if values else "     -"

keys = ("type", "coloured", "dark", "cmed", "cp90", "mid", "strong", "size", "ink", "cover")
print(f"{'set':6} {'lines':8} {'n':>3} " + " ".join(f"{key:>8}" for key in keys))
for who in ("sd", "our"):
    for name, low, high in (("<=30", 0, 30), ("31-60", 31, 60), (">60", 61, 999)):
        items = [row for path, row in rows.items() if group_of.get(path, "").startswith(who) and low <= row.get("lines", -1) <= high]
        print(f"{who:6} {name:8} {len(items):3} " + " ".join(f"{med(items, key):>8}" for key in keys))
print()
print("ours, one by one:")
for path, row in rows.items():
    if group_of.get(path, "").startswith("our"):
        print(f"  {path:40} lines {row.get('lines', 0):3}  type {row.get('type', 0):.2f}%  coloured {row.get('coloured', 0):.2f}%  dark {row.get('dark', 0):.2f}%  C* {row.get('cmed', 0):4.1f}/{row.get('cp90', 0):4.1f}  mid {row.get('mid', 0):4.1f}%  ink {row.get('ink', 0):3.0f}%  cover {row.get('cover', 0):.1f}%")

print()
print("SciDraw samples used in the pairs:")
for path, row in rows.items():
    if any(name in path for name in ("workflow-diagram-generator/mlTraining", "workflow-diagram-generator/rnaSeq", "rag-architecture-diagram-generator/ragPipeline", "ai-architecture-diagram-generator/transformer.png", "neural-network-diagram-generator/cnnArchitecture", "employeePerformance", "drugAction", "thesisTechnicalRoute", "proposalOverallDesign", "graphical-abstract/drugDiscovery")):
        print(f"  {path:62} lines {row.get('lines', 0):3}  type {row.get('type', 0):.2f}%  coloured {row.get('coloured', 0):.2f}%  dark {row.get('dark', 0):.2f}%  C* {row.get('cmed', 0):4.1f}/{row.get('cp90', 0):4.1f}  mid {row.get('mid', 0):4.1f}%  ink {row.get('ink', 0):3.0f}%  cover {row.get('cover', 0):.1f}%")
