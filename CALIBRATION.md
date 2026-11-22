# Calibration record

> The version number was reset to 0.1.0 on 2026-11-14 for the first public release. The 0.4.x–0.5.x numbers below are those of the internal iterations before it; 0.5.2 is what became 0.1.0.

The skill's documents carry the rules and the reasons they need; the measurements behind the rules are kept here, to compare against when a rule changes. This file is not installed with the skill, so agents never read it. The measuring scripts and how to run them are in [eval/README.md](eval/README.md).

Unless a line says otherwise:

- every figure was generated with Codex `image_gen` on 2026-11-12 and 13;
- the comparison is with public reference figures ("the samples" below);
- an "end-to-end run" is a fresh Codex session that gets only the skill and the request, and works from the brief to the delivered file.

## Connectors

- Of 63 end-to-end runs, 18 had a connector fault in the first draft. 17 were put right with one or two edits; one was still wrong after two. By kind of fault:
  - a line through the name of a row or a band: 6;
  - an extra arrowhead: 3;
  - several lines that share an end drawn as a tangle: 2;
  - lines that had to cross joined to the wrong boxes: 1;
  - a line left out: 1;
  - a line through the name of a drawn object: 1;
  - lines that branch off another line (a Transformer's residual connections) drawn as a tangle: 1;
  - faults that appeared once figures were drawn full: 4, namely a feedback line to the wrong card, an arrow stopping at a frame, an arrowhead on its own, and an arrowhead where a flat bar was asked for.
- Of 39 runs made under the current connector rules, 31 had every line right at the first attempt.
  - Of the last 20 of these, made as full as the skill now asks, 4 needed an edit for a line.
  - All 9 figures with names in a left rail had every line right at the first attempt.
  - Of 13 figures with names above their rows or bands, 6 had a line through a name.
  - With the residual connections described as three legs and a dot where each branches off, all 5 were right in the first draft. Without the dot and the sentence that no other line runs inside the frame, two trials each had one line too many.

## Text

- In the first 43 end-to-end runs, the text check reported two typos in a figure ("Questoin", "ratiio"), and the agent glanced at the whole figure, blamed OCR and delivered it. That is why `DIFFERS` was added, as a verdict that a look at the figure does not overrule.
- Rerun under 0.4.2 on about 2,400 labels in 61 figures:
  - 4 `DIFFERS`, all real typos;
  - it later also caught a wrong Chinese character (间 written for 问);
  - one false verdict: the border of a card right before a label, read as the letter I.
- Three fresh sessions were each given an old figure with a text fault to verify, and all three edited it as the rules say:
  - two were right after one edit;
  - one still had the typo after two edits, and was right once the line was erased and rewritten, as the rules then say.
- The 0.5.2 check compared with 0.5.1, label by label, on about 4,100 labels in 98 end-to-end figures:
  - all 5 real typos are still reported ("Questoin", "ratiio" twice, 间题, and a "Takeaway:" put before a label);
  - no new false verdict;
  - one picture fewer is reported as text (a ribosome and its peptide chain, read as "N000");
  - a repeated label missing in one place now names the closest text there.
- Synthetic stress tests (`eval/text/stress_*.py`): correct labels reported as `DIFFERS`:

  | Test | 0.5.1 | 0.5.2 |
  |---|---|---|
  | Labels in cards | 3 of 1,040, all "Illumina" read as "llumina" | 0 |
  | A card border right before the text | 31 of 1,260 | 6 |

  The 6 left in the border test are all a letter that OCR put in inside a word. There the rules go by the first reading, because an image tool's own extra letter inside a word ("ratiio") looks just the same.
- How OCR (RapidOCR 1.4.4) behaves:
  - reading a whole figure at its own size, it hardly ever puts in a letter that is not there (once in about 3,000 labels: the card border read as I);
  - it often reads two identical thin letters in a row as one: "ratiio", read in 45 different crops, came back as "ratio" 10 times, with a confidence still above 0.95;
  - it misreads Greek letters, sub- and superscripts, the same way every time;
  - it often swaps capital O and zero, and capital I and small l.

## Look, against the reference figures

- **Colour**
  - The samples' fill chroma (CIELAB) has a median of about 8–9: 8 for 31 box and card diagrams, half of them between 7 and 11, with strong colour on 2% of the figure; 9 for 21 scenes, with strong colour on 4%.
  - With colour codes in the brief, 7 figures read 7–15, with strong colour on 2–6%; 9 without them read 10–73.
  - "Pale pastel" fills came back twice as strong as "barely tinted, close to white" with colour codes.
  - For reference on this scale: faint tints read 12 or less, pastels about 20, saturated colours 50 or more.
  - One edit that changed only the colours took a figure from 24 to 8.
- **How much a figure carries**
  - The samples come in two kinds: the plainer half of each type has 10–33 lines of text (roadmaps up to 81); the fuller half has two to four times as many, and those are the figures that look designed.
  - Medians of the fuller kind: workflows 89, system architectures 91, research plans by year 111.
  - Ours: a machine-learning training workflow with 81 labels (the sample on the same subject: 109 lines), a RAG architecture with 91, a four-year PhD research plan with 100 (the sample on the same subject: 99), every label read back as listed.
  - Technical roadmaps are another kind: the samples have only 23–46 lines, and their richness is in the picture of each step.
  - Five figures briefed this way on 2026-11-12 held 31–99 lines, all right at the first attempt; so was a workflow of 89 lines on 2026-11-13 (8 cards, each with an illustration of three or four objects).
- **Glosses**
  - A workflow briefed with glosses in parentheses, parts named in its pictures and a small icon on every row of its panels: 105 lines, 12% of them glossed, 253 drawn parts.
  - The sample on the same subject: 112 lines, 8%, 306 parts.
  - Without them: 81 lines, none glossed, 183 parts.
- **Type size**
  - The fuller the figure, the smaller its type. On a slide the figure fills: 12 pt at 60 and 81 lines, 11 pt at 89, 10.5 pt at 96; the fuller samples run at 8–9 pt.
  - The same technical roadmap of 33 texts, printed 150 mm wide: 7–8 pt in landscape, 10–12 pt in portrait.
- **Line weight**
  - The samples' outlines are 0.15% of the figure's width at the median: 0.16% (2.7 px) in samples of an image tool's size, 0.12% in larger ones.
  - Our outlines by the wording of the brief:

    | Wording in the brief | Outline width |
    |---|---|
    | "thin" only | 2.6–4.3 px |
    | "about 2 pixels wide" | 2.8 and 3.4 px in two landscape figures |
    | the current line-weight sentence | 2.1 px for the same two briefs |

  - Of 5 landscape figures made with the line-weight sentence, 4 read 2.0–2.3 px (0.12–0.14% of the width) and one read 3.2 px on the frames of its bands; arrows read 1.8–2.3 px.
  - One edit that changed only the line weights took outlines from 4.3 px to 2.0, and from 3.2 px to 2.5.
- **Pictures**
  - The samples' pictures are small solid illustrations of three or four objects, not line icons. Icon-sized shapes per figure, median by type:

    | Type | Count |
    |---|---|
    | Workflow | 29 |
    | Graphical abstract | 25 |
    | Mechanism | 24 |
    | Roadmap | 19 |
    | Model architecture | 15 |
    | System architecture | 12 |
    | Framework | 11 |

    These shapes cover 1–3% of a figure.
  - On 2026-11-12, the same briefs with and without a picture for every element: a pipeline went from 27 shapes to 36, a work plan from 9 to 16, a roadmap in Chinese from none to 23, with every label still read back as listed.
  - On 2026-11-13, with pictures of three or four objects and the picture sentence:
    - a workflow of 8 cards: 55 shapes on 2.5% of its area (before: 24 on 1.4%; the sample on the same subject: 35 on 1.7%);
    - a framework: 19 on 4.0% (before: 13 on 0.3%);
    - a network of layer stacks: 24 on 0.9% (before: 6 on 0.1%).

    The fills of cards and boxes kept their chroma of 7–9: the colour that came in is inside the pictures.
  - Asked only for "a small illustration, drawn in fine lines", the image tool returned outline drawings: as many shapes, on half the area.
- **Figures of few elements**: a framework of four constructs, briefed to fill its canvas with large boxes, had type of 3.6% of its height and 19 pictorial shapes covering 4% of it; the same content in small boxes had 2.8%, 13 shapes and 0.3%.
- **Scenes and detail**
  - A mechanism whose things were described by form and parts: 9% of its lines with a gloss in parentheses, and an outline length of 15–19 times the figure's diagonal.
  - The same mechanism with things only named: none, and 12 times.
  - Published mechanism figures: 6%, and 21 times.
  - Drawn parts went from 183 to 373 in a machine-learning training workflow (the sample on the same subject: 306), and from 191 to 238 in a RAG architecture.

## Edits

- An edit redraws the whole picture; there is no mask. An edit that changed one title changed nothing else the eye could find, yet about one pixel in a hundred shifted along edges all over the picture.
- With very full content, the image tool now and then returns about 3:2 instead of 16:9: twice in 13 runs in the 0.5.0 round, once in over fifty figures before.

## Resolution and enlargement

- Codex's image tool returns about 1.5 megapixels per image (1672 × 941 at 16:9) and takes no size argument; a pixel size written into the brief changes nothing. More than half of the reference figures are 2048 × 1152 or larger.
- `enlarge.py` with 4 tiles:
  - two figures of 1672 × 941 came back 2696 and 3000 px wide;
  - a portrait roadmap in Chinese went from 1086 × 1448 to 1843 × 2458, from 184 to 312 dpi when printed 150 mm wide;
  - their 35, 82 and 102 texts were read back as listed, but for one capital O that OCR took for a zero;
  - all 12 redrawn tiles lay within 2 px of their place;
  - lines came out as fine or finer: 0.08–0.18% of the width.
- With 6 tiles: a figure of 1672 × 941 came back at 3545 × 1995 (2.12×), with all 87 texts read back.
- The weight of one line on the two sides of a cut:
  - differs between two redraws by 5% at the median and 18% at most;
  - differs over the same stretch in the original by 3% at the median and 19% at most;
  - joined edge to edge, the difference showed as a step; passed into each other across the cut, it showed none (21 lines measured).
- On 2026-11-14, the correction that keeps the original's flat colours when joining was measured on 4 real enlargements: white background 8–24 px from ink changed by 0 to +1.4 grey levels on average, and at most 2% of those pixels darkened by 5 levels or more. No visible halo.

## Fresh-session validation of 0.5.2 (2026-11-14)

- 7 fresh Codex sessions, 19 generations in all:
  - 4 sessions made new figures from the same requests as the 0.5.1 runs e2e60–63, 8 generations;
  - 1 session enlarged an existing figure in 6 tiles, 6 generations;
  - 2 confirmation sessions, 5 generations.
- Every edit and every tile redraw named its source file in `referenced_image_paths`.
- Against 0.5.1 on the same requests (OCR lines, share of glossed lines, drawn parts, pictures, fill chroma, line weight):

  | Figure | 0.5.1 | 0.5.2 |
  |---|---|---|
  | RAG | 102 lines, 5%, 238, 30, 10, 2.0 px | 94 lines, 4%, 312, 40, 9, 1.8 px |
  | Training workflow | 83 lines, 2%, 373, 36, 10, 2.1 px | 83 lines, 2%, 286, 40, 8, 2.0 px |
  | Mechanism | 43 lines, 9%, 72, 11, 13, 2.2 px | 43 lines, 9%, 169, 13, 6, 1.6 px (confirmation session) |
  | 16S workflow | 51 lines, 6%, 228, 42, 11, 2.1 px | 33–34 lines, 3%, 203–208, 38–40, 9–10, 1.7–2.1 px |

- **A change that made things worse, and was taken back:**
  - 0.5.2 first named `figure-recipes.md` in SKILL.md's routing table.
  - All 4 figure sessions then read several references in one command, or at the same time. Codex cuts a command's output at about 16,900 tokens, so the output was truncated and the sessions re-read only parts of it. The mechanism figure's glosses fell from 8–9% to 3%.
  - The 0.5.1 sessions had read `illustration.md` first and `figure-recipes.md` on its own afterwards. The three sessions without truncation are exactly the figures with the most glosses.
  - With SKILL.md back to its 0.5.1 text, both confirmation sessions read the files one after the other, without truncation, and the mechanism's glosses were back at 9%.
- **The text check:**
  - Of 9 `DIFFERS` across all 113 real figures, 8 were real faults. 3 of them were new in this round: a rewritten title, a malformed "n" in "validation", and "prottein".
  - In the last two cases the session believed afterwards that OCR had misread, and only the enlarged crop showed the fault was real. The rule that a look at the figure does not overrule the check stays.
  - The one false verdict was a lone "g" that OCR read between two words ("Hepatic g glucose"). Only reading the crop letter by letter rules that out, and the documents give that way of checking.
  - Two more kinds of false verdict found in this round are fixed:
    - two abbreviations in one legend row, separated by a semicolon, read as one line;
    - a C that OCR read beside a ℃ sign.
- **Enlargement:** all 6 redrawn tiles were used (match 0.964–0.988); 1672 × 941 became 3715 × 2091 (2.22×), every text read back as listed, and no seam is visible at the cuts.
- **Fixed: a recolour edit that washed out the pictures** (on 2026-11-14 the mechanism figure was found too pale, and was to be brought to the colour level of the other figures):
  - Cause: after an edit to its line weights, the mechanism's fill chroma drifted from 15 to 16, one above the limit of 15 for scenes, and that set off an edit that paled everything. The edit's wording was written for boxes: the session put the box tints on the cells, and paled the small parts too.
  - The fix, in `illustration.md`, section 5, step 3:
    - a reading one or two above the limit is no fault;
    - a recolour edit changes only the large fills and keeps pictures, icons and small parts in their colours; in a scene, the bodies of cells take the soft tints;
    - measure again after the edit: where the fills read under 30 and the share in strong colour fell by half or more, the edit drained the pictures, so keep the figure from before it.
  - Three versions of the same figure:

    | Version | Fill chroma | Strong colour | Visible colour | Colour inside the pictures |
    |---|---|---|---|---|
    | Before the recolour | 16 | 3% | 8.3% | 23% |
    | Recoloured with the old wording | 6 | 1% | 2.7% | 4% |
    | Recoloured with the new wording (one real edit) | 10 | 2% | 4.1% | 14% |
    | The other figures | 8–10 | 2–3% | 6–9% | 14–22% |

    Under the new rules this figure is not recoloured at all: the version before the recolour is the one delivered. Where a recolour is needed, the new wording also lands within the range of the other figures.
  - After the edit with the new wording, OCR cut a correct "Fatty acid synthesis ↓" into two overlapping boxes and reported a `DIFFERS`; the crop shows the text is right. This is a third, rare kind of false verdict, ruled out by reading the crop letter by letter, as the documents say.
- **Still open:** a line weight of 3.2 px, just above the limit of 3 px, also set off an edit. Whether the limits should have some slack is undecided.
