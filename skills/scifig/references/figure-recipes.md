# Figure recipes

Layouts and wording to put into the brief of `references/illustration.md`. Pick one figure type
and one visual language. A type that does not match the content pulls the image in two
directions; if nothing fits, describe the layout yourself.

## Figure types

| Type | Aspect ratio | Layout | Visual language | Keep in mind |
|---|---|---|---|---|
| Graphical abstract, or the summary of one study in scenes | Set by the journal (see below); 16:9 where no journal sets it | One panel. The story of the study in four or five scenes, left to right or top to bottom: starting point, intervention, key result, meaning. | Soft scenes | This is the type for what one study did and found. A method, a pipeline or a process with steps is a workflow, also when the user calls it an overview. For a journal, its guide sets the words: few, and no heading. Anywhere else (a talk, a poster, a web page) a heading and one or two short lines under each scene. No plot of data that you do not have, no large empty areas. |
| Mechanism | 16:9 or 4:3 | A numbered heading for each step across the top, three to five steps, the columns parted by thin dotted lines. Under the headings one continuous scene of the cell or tissue, stimulus at one side and outcome at the other, each step drawn where it happens. Around it an outcome panel, a key and one closing sentence. | Soft scenes | One mechanism per figure. Name every molecule. Every arrow has one meaning. Draw a step as the things it happens to, with the change written beside them, not as a box with a name. |
| Signalling pathway | 3:4 or 4:3 | Membrane at the top, nucleus at the bottom: ligand and receptor, cascade, transcription factor, target genes. | Soft scenes | Pointed arrows activate, flat bars inhibit. Mark compartments. |
| Experimental workflow, protocol | 16:9 | Numbered steps left to right in one row of tall cards, up to eight, with the panels under the row. With more steps, or where the lines are long, two rows: the second runs back from right to left, so that the line between the rows is a short one down the right side. | Icon cards | Draw the sample or instrument at each step; conditions (time, temperature, dose) go under it. |
| Research roadmap (technical route, 技术路线图) | 16:9; 3:4 for a page of its own with large type | A technical route: one band per stage, top to bottom; the steps of a stage as boxes inside its band, parallel work side by side; the final output below the last band. A plan over years: a time axis across the top, one column per year or phase, its tasks as cards in the column, a milestone at the foot of each column, and a band along the bottom for what runs through all of them. | Stage bands | Say which box each arrow leaves and enters, and where two arrows join. Place each box under the one that feeds it, so that no arrow crosses another. |
| Conceptual framework | 4:3 | Variables as boxes; hypotheses as labelled arrows ("H1", "H2"). Few boxes, so large ones, each with a picture: "A figure of few elements" below. | Block diagram | Mediators sit between two boxes; a moderator points at an arrow. A hypothesis of mediation has no arrow of its own: write it beside the mediator. |
| Model architecture (a network, an algorithm) | 16:9 or 2:1 | Stacks read bottom to top, or stages read left to right. A repeated block sits in a frame with its count. | Block diagram; layer stacks when tensors change size | One colour per kind of module, and a legend when there are more than three. Write the tensor shape or the size beside each stage of the main path. |
| System architecture, pipeline | 16:9 | One row of modules per path, read left to right; a dashed line between rows. | Icon cards | Name each row. Say where one row feeds the other. |
| Comparison | 16:9 or 1:1 | Two or more panels with the same layout, scale and viewpoint. | The one of its content | Mark what differs with a single accent colour. |
| Labelled diagram (anatomy, cell, apparatus) | 4:3 or 1:1 | One central object; labels in the margin joined by leader lines. | Soft scenes | Leader lines never cross. Check that each line ends on the structure it names. For a worksheet version, ask for the same figure with empty label boxes. |
| Journal cover | The journal's trim size, usually portrait | One striking central image. | A style from the second table below | No text or labels. Keep the top quarter calm for the masthead. |
| Single icon | 1:1 | One object, centred, on white. | Soft scenes | No text. For assembling into a larger figure by hand. |

## What a full figure carries

The layers are those of `references/illustration.md`, section 2. The last column is the number
of text lines that OCR reads in public reference figures of the type, measured on 2026-11-12.
They come in two kinds. The plainer half of each type holds 10 to
33 lines (roadmaps up to 81). The fuller half holds two to four times as many, and those are
the figures that read as designed: the column gives their median and range. Make the full
kind unless the user asks for a simple figure: the number of the type, or 100 where the
number is higher, which is as much as one picture has been seen to hold. For a standard
subject the standard knowledge fills it: what
each step does, the usual methods, tools and measures by name. For the user's own work the
number is no target. All of their material goes in, with what general knowledge says about
the things it names (`references/illustration.md`, section 2, step 3) and every reading aid;
what that comes to is the figure, and its richness is then in the pictures. Never fill with
padding: no time, count, condition or example that you would have to make up. What you
compare with the number in the table is the count of the entries of your `labels.txt`,
not counting the number badges, which stay in the file. How the figure breaks the entries
into lines does not enter into it.

A full figure has small type, as the published ones have: on a slide that the figure fills,
8 to 9 pt in the full published samples, 10.5 to 12 pt in ours of 60 to 96 lines. Aim for
the number in the table wherever the figure goes, a slide included, and hand over the size of the type, which
`scripts/check_text.py` gives on its `TYPE` line. Under about 10 pt on a slide, type is hard
to read from the back of a room: where the smallest tenth falls below that, say so and name
the way out, which is the plain kind or the content split over two figures.

A full figure speaks at two levels. Besides its lines it carries glosses: the tool, the
format, an example or a state, in parentheses and in smaller type after the line it belongs
to: "Quality check (FastQC)", "Raw reads (FASTQ)", "AMPK (active)". In the full samples
about one line in ten carries one, 6 to 13% by type. For a standard subject, name the usual
tools and examples there. For the user's own work a gloss says what they said of the thing,
or what general knowledge says of it (`references/illustration.md`, section 2, step 3).

| Type | Detail in each element | Annotations | Frames | Reading aids worth adding | Text lines of a full figure |
|---|---|---|---|---|---|
| Mechanism, pathway | A label for every named molecule and structure; the state of a step ("inactive", "no phosphorylation") | What is blocked, what is passed on | An outcome panel: untreated and treated, or before and after | A numbered heading for each step; a key to arrows and shapes; a take-home sentence | 50 (37 to 76) |
| Experimental workflow, pipeline | A card for each step: name, picture, three or four actions or conditions, a footer with what the step hands on, or with its time or quantity where the material gives one | The condition on a branch; a decision with its yes and its no | Inputs before the first step, outputs after the last; a loop back | Step numbers; panels for metrics and cautions; a colour legend; the total time | 89 (65 to 112) |
| Research roadmap: a technical route, what is done in which order | A box for each step with a title and one to three lines: method, data, tool; a picture of the step in each box | Which step feeds which | The goal or question at the top; outputs or deliverables at the bottom | Stage names; a legend of line styles | 25 (23 to 46), three samples: their richness is in the pictures |
| Research roadmap: a plan over months or years, with aims, tasks and milestones | A card for each task with two to four lines | Which task depends on which | Preliminary work before the first aim; deliverables and a final goal after the last; a milestone for each aim | A time axis; a legend of line styles and marks; abbreviations spelled out | 111 (56 to 132), six samples: aim for 100 |
| Conceptual framework | The dimensions or items of each construct, listed in its box | The number and sign of each hypothesis on its arrow | Controls and context in a side panel | A key to arrow types | 39 (23 to 51) |
| Model architecture | What a module does, where its name does not say | Tensor shapes or sizes along the main path; what an arrow carries | One sub-module opened up in an inset | A legend of module kinds; a notation panel for the symbols | 58 (43 to 102) |
| System architecture | One line in each module on what it does or what it runs on | The data named on each arrow; the condition on a loop | Users and outside systems at the edges | Numbered stages; a legend | 91 (55 to 125) |
| Graphical abstract, or the summary of one study in scenes | For a journal none: few words. Elsewhere a heading and one or two lines for each scene | What passes from scene to scene | The starting point and the outcome | For a journal none in words. Elsewhere a title and a closing sentence. Either way the richness goes into the drawing: the structures and textures of the real thing | The publisher's limit for a journal; elsewhere 43 (20 to 84) |

Figures briefed this way with up to about 100 text lines came out right at the first
attempt, every label read back as listed. More has not been tried in a picture of 1.5
megapixels: beyond that, split the content over two figures. A figure that full has small
type: `references/illustration.md`, section 5, step 6, makes it larger and sharper.

### A figure of few elements

A figure of few elements gives each of them more room. In the samples, figures of 30 lines
or fewer have type of 3.5% of the picture's height at the median, those of more than 60
lines 2.3%: the same canvas, filled either way. Small boxes in the middle of a white canvas
read as unfinished. So where the content comes to 30 lines or fewer (a conceptual
framework, a simple roadmap, a model of a few stages):

- say in the brief that the figure fills its canvas and has no large empty areas;
- give each box its place and size in percent of the canvas, so that the boxes do fill it;
- make the names large and bold;
- put a picture of three or four objects into each box, about a third of the box high.

## Visual languages

Each of these produced a figure with the finish of a designed one at the first attempt, with
Codex's `image_gen` on 2026-11-12. Put the wording into the Style line of the brief, with the
line-weight sentence of the section "Line weight" after it. Then describe the elements the way
the last column says, with the colours and the pictures of the sections below.

| Language | Wording for the Style line | Describe each element as |
|---|---|---|
| Block diagram | "Flat vector diagram as in a figure of a machine-learning paper. Every box is a rounded rectangle whose fill is barely tinted, close to white, with a hairline outline in a medium shade of the same hue. Restrained, low-saturation colour: stronger colour appears only in the outlines and in the pictures. Label text is dark grey, sans-serif, centred in its box, one size for all boxes. Frames have a white fill and a hairline coloured outline. Black arrows with small solid heads, only horizontal and vertical segments with rounded corners. No shadows, no gradients, no 3D, no decoration." | A box with its text and the colour of its kind. A frame around a repeated group, with a bold title above its corner and its count ("N x") beside it. A small circle with a plus sign where two signals are added, a small symbol where one stands for a part (a sine wave for a positional encoding). A legend panel: one swatch and one name per kind. Where the boxes are few, each is large and holds a picture above its name. |
| Layer stacks | "Clean flat technical figure. Translucent planes with crisp edges, no shadows, no gradients, no glow. Black sans-serif text; the sizes above the stages are bold. Even spacing between the stages." | All stages in one row, nine or ten of them too: two rows halve the stacks. A tensor as a stack of thin translucent planes, one behind the other, each offset slightly up and to the left, in one pale colour with darker edges; say how many planes, six to ten (three read as a pictogram), and that each stack is smaller than the one before. The input as what it is: for an image model a small picture in flat colours as the front plane of its stack. A fully connected layer as a tall rounded column that holds circles, with a web of thin lines from every circle to every circle of the next column: without the webs the columns read as lists. The webs belong to the pictures and are no connectors. The output as a small panel of bars of different lengths, without words. The size above each stage, the operation below it. |
| Icon cards | "Flat vector infographic with small finished pictures, in the manner of a figure in a machine-learning paper. Restrained, low-saturation colour: the fills are faint tints, and stronger colour appears only in the outlines, the number badges, the names and the pictures. No shadows, no gradients, no 3D. Dark grey sans-serif text." | A card: a tall rounded rectangle with a white body and a hairline outline in the colour of its group; a header band with a faint tint, a number badge and the name in bold; in the body a picture of three or four related objects, about a quarter of the card high, with thin arrows inside it where one object feeds another; below it three or four lines of detail, each with a small bullet, and after a line, where a tool, a format or an example belongs to it, a gloss in parentheses in smaller grey type; a footer strip in the faint tint with a small mark and what the step hands on, or its time or quantity where the material gives one. A panel under the cards: a bold heading and rows, each row a small picture of its own and one line, not a bullet. Short arrows between neighbouring cards. Where the rows have names, each name in bold in a rail at the left end of its row, with the cards and all lines to the right of it: no name above a row. |
| Stage bands | "Flat vector diagram. Restrained, low-saturation colour: the bands are faint tints, and stronger colour appears only in the outlines, the stage names and the pictures. Step boxes are white rounded rectangles with a hairline dark-grey outline, all the same size. Type in a clean sans-serif face, dark grey. No shadows, no gradients, no 3D, no decoration." | A band per stage: a wide rounded rectangle whose fill is barely tinted, close to white, with a hairline outline in a medium shade of the same hue. In a rail at its left end, as high as the band, a picture of two or three objects and under it the stage name in bold, both in that outline colour, on the band itself: no filled tab, and no strip along the top of the band, which every line from band to band would have to pass. The boxes and all lines keep to the right of the rail. A step box: a small picture of two or three objects at its left, a bold title, then its lines of detail. Hairline dark-grey arrows, vertical or with right-angle corners. The final output as boxes with a faint tint and an outline, not as a filled block. |
| Soft scenes | "Soft scientific illustration in the manner of a figure in a review journal. Muted, low-saturation colours. <Cells and vesicles> have pale bodies with a hairline rim in a medium shade of the same hue and very gentle shading that gives them a little volume. Small parts (<RNA pieces, receptors, granules>) are drawn in the medium shade so that they stand out. No black outlines, no glossy highlights, no hard shadows, no photorealism." Name your own shapes in the angle brackets. | A scene per step, each with the cells, molecules or instruments it needs. Say of every thing its form and its parts, in the words of "The things of a scene" below: a line for the cell membrane and a blob for a protein is what comes back when the brief only names them. Grey arrows between scenes, drawn with the same fine line as everything else, and a flat bar in place of the head on a line that inhibits; a label beside each named thing, with a leader line where the thing is small, and under the label, where it has one, its state in parentheses and smaller type. The picture sentence of "Pictures" is not for scenes: their Style wording says how things are shaded. |
| Flat scenes | "Flat 2D vector illustration, simple shapes, uniform hairline dark-grey outlines, flat fills, no gradients, no shadows." | As soft scenes, for a flatter look like a set of icons. Ask for muted fills in the Palette line all the same. |

Other styles, for covers and teaching material. Not measured:

| Style | Wording for the Style line | Suits |
|---|---|---|
| Schematic line art | "Clean schematic line drawing, black lines of one weight on white, minimal fills." | Apparatus, protocols, textbook figures. |
| Isometric 3D | "Isometric 3D illustration, consistent 30-degree projection, soft even lighting, simple materials." | Devices, layered materials, lab set-ups. |
| Realistic 3D render | "Realistic 3D scientific rendering, soft studio lighting, accurate proportions, shallow depth cues." | Covers, molecular and cellular scenes. Hard to edit afterwards. |
| Textbook hand-drawn | "Hand-drawn textbook illustration, ink outlines with light watercolour fills." | Teaching material. |
| Abstract artistic | "Abstract artistic interpretation, bold composition, no labels." | Covers only. |

## Colour

A designed figure is mostly white: its fills are faint tints, and stronger colour is kept for
thin outlines, icons and small parts. An image tool drifts towards stronger colour unless the
brief pins it down. Asked for "pale pastel" fills, it returned fills twice as strong as when
it was asked for fills "barely tinted, close to white" with the codes below. So give every
colour as a code in the Palette line.

| Hue | Faint tint: boxes, cards, bands | Soft tint: bodies in a scene | Line: outlines, icons, small parts, stage names |
|---|---|---|---|
| Blue | `#E8F2FC` | `#D9EAFA` | `#1D83BB` |
| Teal | `#E3F4F4` | `#D1EEEE` | `#0E9296` |
| Green | `#E9F3EB` | `#DBEDDE` | `#4D9262` |
| Yellow | `#FBF3DC` | `#F5EBCC` | `#B5913A` |
| Orange | `#FCEEE5` | `#F8E5D7` | `#CA7F48` |
| Rose | `#FEEDEE` | `#FDE2E3` | `#C56777` |
| Violet | `#F3EFFA` | `#ECE5F8` | `#8E79BA` |
| Grey | `#F1F1F1` | `#E8E8E8` | `#848484` |

Text and arrows are dark grey, `#3B3B3B`. The background is plain white, except on a cover.

- **Write the Palette line** as one entry per kind of element: "Attention: fill #E8F2FC,
  outline #1D83BB (blue)." End it with: "No fill anywhere is stronger than these tints. The
  colour codes are instructions, not text to draw."
- **Layer stacks keep more colour.** A translucent plane has to show against white: ask for
  "pale blue with darker blue edges" there, without the tint codes.
- **Measure the result** with `scripts/check_figure.py --look`: `references/illustration.md`,
  section 5, step 3, says what it should read and how to mend it.
- **A name in colour is coloured type.** Told that stage names carry the stronger colour,
  the image tool once set them in white on filled shapes, which took the strong colour to
  8%. Say "the name in bold type of the outline colour, on the faint tint: no white type
  on a filled shape".
- **Colour is a second cue.** The line colours share one lightness, so several of them look
  alike in greyscale print and to colour-blind readers. Every box carries its name, which is
  what tells the kinds apart. Where colour alone must separate two kinds of thing (two cell
  types), take blue and orange, which stay apart in all three forms of colour blindness, give
  a third kind another shape, and label them all.

## Line weight

Published figures carry fine lines: their outlines are about 0.15% of the width, 2 to 3 px in
a picture of an image tool's size. Told only that an outline is "thin", an image tool drew it
up to 4.3 px wide, and told "about 2 pixels wide", up to 3.4. So put this sentence after the
Style wording, and call every outline in the brief a hairline:

"Every outline, frame, divider, arrow shaft and connector is one fine hairline, 1 to 2 pixels
wide in the finished picture and never wider than 2 pixels: finer than the strokes of the small
text. The illustrations are drawn with the same fine line."

With it, outlines came back at about 2 px. Measure yours with `scripts/check_figure.py --look`, which names the hairline for a picture
of your size. A portrait picture is only 1086 px wide, so that its 2 px are 0.18% of the
width: the same lines look finer in a landscape picture.

## Pictures

A designed figure draws its elements: every card, step and panel has a picture, and small
marks say what a thing is. Published figures hold a dozen to thirty such pictures, filled
drawings of several objects and not outlines. How a named thing is drawn is yours to decide,
so this layer costs the user no facts.

- **A picture for every element, at every level:** each card or step, each task inside a
  band, each side panel, each output.
- **A finished little picture, not "an icon".** Say the three or four related objects it
  shows: "a database cylinder with arrows to a document, a sensor and a cloud", "a funnel
  that takes in a square, a circle and a triangle, with a gear at its side and a small
  histogram". Give it room: about a quarter of the height of a card, a third of a large
  box. Where space is tight, as in a task card, a picture of one or two objects will do: "a
  laboratory flask on a stand".
- **Put the picture sentence into the Style line,** before the line-weight sentence, for
  every visual language but the scenes:

  "The pictures are small flat drawings of several objects, each drawn with two or three
  of its own parts: their shapes are filled with pale tints and outlined in a medium shade
  of the element's hue, with white and one or two other pale hues for variety; they look
  like finished little pictures, not like thin pictograms."

  Told only "a small illustration, drawn in fine lines", the image tool returns outlines:
  as many shapes, on half the area.
- **Name the parts of an object:** "a database cylinder of three discs", "a gear with
  eight teeth", "a monitor that shows a grid of shaded cells", "a checklist with three
  ticks". And where one object of a picture feeds another, a thin arrow between them:
  those arrows belong to the picture.
- **Every entry its own mark.** In a panel, a row of a list has a small picture of what it
  says (a padlock before "No leakage from test data"), a legend entry its swatch, a
  footer its small mark. Bullets are for the lines inside a card. Name the mark of each
  row in the brief: told only that every row has one, the image tool set the same column
  of marks into all three panels of a figure. Where no picture fits a row, a small check
  mark does.
- **A small chart as one of the objects,** where a step makes or reads data: "a small
  scatter plot of dots with a fitted line", "a monitor that shows a grid of shaded cells",
  "a small histogram". No axis labels and no numbers: it shows the kind of thing, not a
  result.
- **An example as the picture of an input or an output:** a landscape in flat colours as
  the input of an image classifier, a row of bars of different lengths as its output. It
  shows what the thing is and claims nothing about the user's data.
- **Small marks that mean something:** a number badge on each step, a check mark before each
  item of a list of things done, a flag at each milestone, a clock beside each duration, dots
  in the colours of the groups along a time axis, a swatch for each entry of a legend.
- **Shapes that say what a thing is:** a cylinder for a store, a sheet for a document, a
  diamond for a decision, a cloud for a service, a figure for a person.
- **A picture does not count.** Asked for ten bars and for a strip of ten cells, the image
  tool drew nine and eight, and it took an edit each to put right. Where a number matters,
  it stands in a label; the picture shows "a column of bars", "a strip of cells".
- **No text inside a picture.** Say "illustrations and icons contain no letters or numbers":
  left alone, the image tool labels them itself. In one measurement it wrote "Train (70-80%)"
  into the picture of a data split; `scripts/check_text.py` reported it as `EXTRA`.


### The things of a scene

In a scene the richness is in how the things are drawn. Describe each one by its form and
its parts; these wordings came back as written:

- **A membrane:** "a lipid bilayer: two rows of small round heads with fine wavy tails
  between them", and where it runs: "across columns 1 to 3, just under the headings".
  Show a cell by this band, with the outside above it and the cytoplasm below, and not by
  a closed outline around everything in it: the outline costs the membrane its detail and
  the scene its room.
- **A receptor:** "two Y-shaped halves that span the membrane, standing together as a
  pair"; its ligand "a small ball in the cleft at its top".
- **An enzyme or another protein:** "three rounded lobes that fit together, with gentle
  shading and a darker rim"; a complex "a cluster of small lobes"; an active one "with a
  few short rays around it".
- **A state:** "a small round badge that holds the letter P on its shoulder", "a small red
  cross on its path". The letter of such a badge is the one text a picture may hold: say
  so in the Text line.
- **A small molecule** of which no structure is given: a pictogram, "a ball with three
  small beads in a row", "a blue hexagon". A structural formula only where the user
  supplied it: a drawn formula is a statement about the molecule.
- **A nucleus:** "a large half-ellipse with a double rim and a few pores, which holds a
  short DNA double helix". **A mitochondrion:** "an outer membrane, a folded inner
  membrane with cristae and a pale matrix". **A vesicle:** "a ring of small lipid heads
  around a pale body".
- **Cells:** "a rounded body with a nucleus"; a tissue or a tumour "a cluster of seven
  round cells", its outcome "a cluster of three".
- **An organ, an animal, an instrument:** its outline with two or three of its parts: "a
  liver with its two lobes", "a short piece of blood vessel, cut open at one end".

Give the scene its frame as well: the columns parted by thin dotted lines, a key panel
whose rows show the symbols as they are drawn, an outcome panel with the two states side
by side.

## Graphical abstract sizes

A graphical abstract is sized by its own rule, not by column width. Dimensions differ by
publisher and are not in the bundled journal data; read the journal's own guide. Two rules,
both read on 2026-11-11:

- **Elsevier journals, except Cell Press titles** (Elsevier's graphical-abstract page): at
  least 1328 x 531 px (width x height) at 300 dpi or more, in a 500 : 200 proportion; shown in a
  500 x 200 px window, so type must stay readable at that size; reading top to bottom or left to
  right; no "graphical abstract" heading and no unnecessary white space inside the image.
- **Cell Press journals**, such as Cell, Cell Reports and Neuron (Cell Press graphical-abstract
  guide, a PDF dated 2014; the journal's current author page may give other pixel sizes):
  5.5 inches square at 300 dpi, which is 1650 x 1650 px; Arial, 12 to 16 pt; one single panel;
  TIFF, PDF or JPG; reading top to bottom or left to right; distinct from the model figures in
  the paper; no data items; simple labels; no heavily saturated primary colours.

An image tool does not take a pixel size or a font size. Ask it for the proportion, through
its aspect-ratio argument or, if it has none, in the Canvas line of the brief. Then bring the
file to size with `scripts/export_figure.py` (`--width-mm` and `--dpi`), and measure the type
on the result (`references/export-and-checks.md`).

Check the publisher's AI policy as well: `references/ai-image-policies.md`.

## Arrow meanings

The Systems Biology Graphical Notation (Process Description) defines these line endings:

| Meaning | Line ending |
|---|---|
| Consumption (a reactant enters a process) | plain line, no symbol |
| Production | filled arrowhead |
| Stimulation, activation | open arrowhead |
| Catalysis | open circle |
| Inhibition | flat bar (T-bar) |
| Modulation, sign not specified | open diamond |
| Necessary stimulation | bar followed by an open arrowhead |

Outside a figure that declares SBGN, "pointed arrow activates, flat bar inhibits" is a shared
convention, not a standard. Image models do not reliably separate open from filled arrowheads:
in a generated figure rely on the two-way distinction and state anything subtler in a label.
Use the full notation in code-drawn or hand-edited figures.

Source of this table: SBGN specifications, https://sbgn.github.io/specifications, as summarised
in a reference published under CC BY 4.0 (verified 2026-07-21; source and attribution:
https://github.com/lionelee/scifig/blob/main/NOTICE.md).
