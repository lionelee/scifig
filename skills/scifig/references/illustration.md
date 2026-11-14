# Figures from your host's image tool

For every figure that explains something: graphical abstracts, mechanisms, pathways, workflows,
roadmaps, frameworks, model and system architectures, labelled teaching diagrams, covers, single
icons. A chart of data is plotting code (`references/charts.md`). The few diagrams that must be
drawn in code are listed at the top of `references/diagrams.md`.

## 1. Find your image tool

| Host | Tool | What to know |
|---|---|---|
| Codex | built-in `image_gen` | Results are saved under `$CODEX_HOME/generated_images/`: copy the chosen file into the workspace before anything else. To edit a file on disk, look at it with `view_image`, then name it in `referenced_image_paths`; with one call per tile or per variant, the path says which image is meant. It takes no size, resolution or quality argument, and a pixel size written into the prompt changes nothing: the aspect ratio in the Canvas line is all you choose. A very full brief now and then comes back 3:2 where it said 16:9: look at the pixel size it reports, and where the proportion is wrong generate anew. Left to itself Codex draws a diagram in code, because its own `imagegen` skill sends diagrams there; with this skill the user has chosen `image_gen` for them (in that skill's terms the use case is `scientific-educational` or `infographic-diagram`). |
| Antigravity | `generate_image` | Its documentation lists the arguments `Prompt`, `ImageName` and, optional, `ImagePaths`: up to three absolute paths, for a sketch, a reference or the image to edit. An `AspectRatio` argument appears in Google's own example but not in that list: read the tool's schema, and state the aspect ratio in the Canvas line as well. It returns the absolute path of a file in the conversation's artifact folder; copy the file into the workspace. No size or model option is documented. |
| Any other host | the image-generation tool in your tool list (built in or from an MCP server) | Read its schema. Do not assume argument names. |
| No image tool | none | Say so first. Then offer what still works: the finished brief as a prompt the user can paste into an image-capable agent, or the figure drawn in code, plainer but exact: `references/diagrams.md`. |

The Antigravity row comes from Antigravity's documentation (the list of tools on its hooks
page) and from a post by Google AI about the tool, both read on 2026-11-13. This skill has not
been run in Antigravity. Where the tool's own description differs, the tool is right.

Everything in this file that says what an image tool can do was measured with Codex's
`image_gen` on 2026-11-12. Another tool may do less: section 5 finds out.

Each generation spends the user's quota. Make one image unless the user asked for variants.

## 2. Before you generate

1. **Destination and policy.** If you do not know where the figure will be used, ask. For a
   journal, read the publisher's row in `references/ai-image-policies.md` and tell the user what
   it says, with its verification date, before generating.
   - The policy allows it: go on.
   - The policy does not allow it for this use: generate nothing if the user says no. If they
     want the figure for that journal anyway, offer it drawn in code
     (`references/diagrams.md`). Otherwise, including when they leave the choice to you,
     generate one image as a draft for discussion.

   A draft has "draft" in its file name, as does every file converted from it. Your hand-over
   opens with what the policy says and what the user can submit instead: the figure drawn in
   code, a figure made in a dedicated scientific illustration tool where the publisher points
   to those, or one they draw themselves.
2. **Content, in layers.** A figure that shows only its main elements reads as thin beside a
   designed one. Plan what yours will carry, layer by layer, before you write the brief:

   | Layer | What it holds | Who supplies it |
   |---|---|---|
   | Spine | The main elements and how they connect: modules, steps, stages, cells | The user |
   | Detail | Three or four short lines inside or under each element: what it does, the method, the data, a setting. After a line, in parentheses, the tool, the format, the state or an example that belongs to it | The user's material; for a standard subject, its source |
   | Annotations | What an arrow carries, the condition on a branch, the numbers: sizes, doses, times, n | The user's material; the source |
   | Frames | What goes in and what comes out: inputs or earlier work before the first element; outputs, deliverables or the outcome after the last; a loop back | The user's material; the source |
   | Reading aids | Step numbers, a heading for each group, a key to colours, line styles and symbols, abbreviations spelled out, a time axis where dates were given, one take-home sentence where a conclusion was given, a title | You: they restate what the figure already says |
   | Pictures | An illustration for every element at every level: each card, each task inside it, each panel, each output. Small marks that mean something: a badge, a check mark, a flag, a clock | You: how a named thing is drawn is yours to decide |

   Fill every layer the material can fill. `references/figure-recipes.md` says what a full
   figure of each type carries, and how many texts and pictures published ones hold. How full
   yours should be depends on where it goes:

   - **A figure that stands alone** (a slide, a poster, a blog post, a handout): all six
     layers.
   - **A figure that gets a caption** (a journal article, a thesis, a report, a proposal): all
     six, except the title and the take-home sentence, which belong in the caption.
   - **A graphical abstract for a journal:** the spine, with the few words its publisher
     allows. Its richness goes into the drawing.
   - **The summary of one study for anything else** (a talk, a poster, a web page): the
     spine in four or five scenes, with a heading and one or two short lines under each.

   Take the material from what the user gave you. From an abstract or a methods section,
   extract it yourself: question, approach, the steps with their methods and numbers, key
   result, conclusion. You also need the exact label texts and their language, the reading
   direction and the aspect ratio. Ask one round of questions only for gaps that would change
   the picture; state every other assumption in the hand-over. Where nobody can answer, as in
   an unattended run, put the questions into the hand-over, each with the assumption you
   made.
3. **Source of every fact.** The reading aids and the pictures are yours to add. Everything
   else says something about someone's science, and it depends on whose.
   - *The user's own work* (their mechanism, method, model or result). Each named element,
     relation, number and line of detail traces to something the user said. How to draw a
     named thing is yours to decide: a cell has a nucleus, a database is a cylinder, an
     exosome is a small vesicle. Such parts get no label. So is an example that only shows
     what a thing is: a photograph as the input of an image classifier, a small scatter
     plot beside a regression. It carries no numbers and claims nothing about the user's
     data. Adding a named thing or a fact is not yours to decide: no extra receptor,
     module, method or step. That holds for a box that only collects or passes on what
     other boxes hold, put in to even out a row or to spare a line a detour: lines may join
     at a point instead, and a line may run through a band.

     Between the two lies what general knowledge says about a thing the user named: what
     a named method does, what goes into it and what comes out of it, what an instrument
     measures, what a standard step consists of. That is true whoever does the work, so it
     may fill the Detail layer, in the words of a textbook: under "Random forest", "many
     trees on bootstrap samples" and "averaged prediction". It stops at what belongs to
     this study alone: a number, a setting, a name, a result, a choice among alternatives.
     Write out the lines you would add and ask the user to confirm or correct them in your
     round of questions. If nobody answers, or the user leaves it to you, put them in, and
     list in the hand-over every line that came from you, under a heading of its own, so
     that the user can strike what does not hold for their work.
   - *A standard subject named without its parts* (the Transformer, a training pipeline, a
     nephron, the Krebs cycle, how a class of drug acts). The standard knowledge is the
     content, in every layer: the parts, what each does, what passes between them, the usual
     numbers. Write the outline of what you will show, at the level the user named (school,
     undergraduate, specialist), and put it in your round of questions, with a request for
     the figure or the paper they work from: it becomes your reference image. Ask too
     whether they want the figure full or plain (`references/figure-recipes.md`, "What a full
     figure carries"); unanswered, make it full. If they leave the outline to you and you
     have web access, take it from the paper or textbook that introduced the subject, or
     from a standard reference for it, and name that source. Otherwise use yours, and say in
     the hand-over that it comes from your general knowledge and was not checked against a
     source.

## 3. Write the brief

The image tool draws what the brief says and guesses the rest, so a good brief leaves nothing
to guess: every element, where it stands, how it looks, its exact wording, and every line
between two elements. Write it as a specification for a draughtsman, in this order:

```text
Figure type and purpose: <overview figure of a training pipeline, for a technical report>. It must read like a carefully designed vector figure: dense with information, yet tidy and easy to scan.

Canvas: <landscape 16:9>, plain white background, small even margins, nothing touching the edges.

Layout: <one paragraph: the title, if the figure has one; the rows, columns or stacks; where each panel stands; the reading direction; what is aligned with what; where the headings stand; which gaps are lanes, kept clear for lines>

<Name of the first row, column or stack>, <its reading direction>. <What every element of it is made of: a header with a number and a name, an icon, a list of lines, a footer.>
1. <What the element is>. Picture: <the three or four objects it shows, each with its parts>. Name "<exact text>". Lines: "<detail>", "<detail (gloss)>", "<detail>", "<detail (gloss)>". Footer: "<what the step hands on>".
2. ...

<One paragraph for each panel: where it stands, its heading in quotes, each entry in quotes.>

Connections: <how many lines there are; then each line under its number: where it leaves, the lane it runs in, which side of which element it enters, and the text beside it in quotes if it has one>. Every line has one arrowhead, at the end where it arrives, and none at a bend<; the lines that stand for both directions, named here, have one at each end><; the lines that inhibit, named here, end in a flat bar instead>.

Text: All text is in <language>. Use exactly the texts quoted above, spelled exactly as written. No caption, no other text. Illustrations and icons contain no letters or numbers.

Style: <one of the visual languages of figure-recipes.md> <The picture sentence of figure-recipes.md, except for a scene, and its line-weight sentence.> Small text must stay crisp and legible.

Palette: <for each kind of element, its colour codes from figure-recipes.md: fill and outline>. No fill anywhere is stronger than these tints. The colour codes are instructions, not text to draw.

Do not add: anything not listed above, logos, watermarks, decorative people, background shapes.
```

- **List every element, one per line, in reading order.** A box, an icon, a group frame, a
  legend entry, a plain word beside an arrow: each is an element.
- **Describe a repeated element once, then fill each one in.** Say what every card of a row is
  made of, then give each card its name, its icon, its lines and its footer.
- **Quote every text, once for each place it stands.** As you write the brief, write the same
  texts into `labels.txt`, one per line and once for each place: a label on five boxes is
  five lines. Section 5 compares the result with that file. An image tool also prints the
  name the brief gives a thing: "Legend:", "Takeaway:". Call a closing sentence "one
  sentence in bold at the foot" and a legend "a row of swatches with their names", and say
  that nothing stands before them.
- **Count before you generate.** Count the entries of `labels.txt`, without the number
  badges (they stay in the file, or the check reports them as extra), against the number
  to aim for (`references/figure-recipes.md`, "What a full figure
  carries": the number for the type, on a slide as anywhere else). For a standard subject,
  where the count falls short of that number by more than a tenth, go back through the row
  of the type in that table and through the layers. Is every panel and reading aid of the
  row there? Has each element its three or four lines, and do they say what is done and
  with what, by name? For the user's own work the number is no target: put in what general
  knowledge says about each thing they named (section 2, step 3) and every reading aid,
  one by one: a number on each step, a heading for each group, a key to every colour, line
  style and symbol the figure uses, and each abbreviation spelled out in the figure
  itself, in the key or in a row at its foot. Where the content
  comes to 30 lines or fewer, make the figure fill its canvas:
  `references/figure-recipes.md`, "A figure of few elements".
- **Give every line a lane, and keep headings out of the lanes.** "Leaves the top of the
  encoder frame, turns right and enters the left side of the box labelled ..." is drawn as
  written far more often than "connected to the decoder". Lines are still where a first
  attempt goes wrong most often, and the fuller the figure, the more often: about one full
  figure in five needs an edit for a line, such as a loop that leaves the wrong card or an
  arrow that stops at a frame. Each rule below answers a fault seen in figures made from
  this file, with the number of figures it was seen in:
  - *A heading in the way* (six figures): a line ran through the name of a row or of a
    band, or broke off at it. A line that comes from the row or the band above has to pass
    whatever lies along the top of the next one, so no name stands there, neither on a
    line of its own nor in a strip. The name of a row or a band stands in a rail at its
    left end, as high as the row, and the boxes and all lines keep to the right of the
    rail. All nine figures with rails came out right; of thirteen with the names above
    their rows or bands, six had a line through a name. The gaps between rows, columns and
    bands are then lanes: say in the Layout paragraph which they are, and send every line
    through them. The name of a drawn thing can be in the way too (one figure: a line
    that came down on a mitochondrion ran through the name above it): say on which side
    of its thing each name stands, and choose the side where no line arrives.
  - *Arrowheads* (three): a second head at a bend, a head at both ends of a loop. Say once
    that every line has one head, at the end where it arrives, and name the lines that
    stand for both directions, which have one at each end, and those that inhibit, which
    end in a flat bar.
  - *Lines that share an end* (two): one store read by four modules; a line drawn into
    another. Give each its own route and its own point of arrival.
  - *Lines that cross* (one): the tool joined each source to the nearer box instead, and no
    edit undid that. Lay the boxes out until no line crosses another, each box beside or
    under the one that feeds it; a line may pass through the edge of a band or a frame.
    Laid out that way, the same figure came out right. Some figures cannot be laid out so:
    three things that each join the same three always cross somewhere. Then let the two
    lines that cross be of two kinds, a solid dark one and a dashed coloured one, cross
    them at a right angle in open space, and say that they cross without joining. Drawn
    so, such crossings came out right. The web of thin lines between two fully connected
    layers is no set of connectors: it belongs to the picture of the layers.
  - *Lines left out* (one): two of seven arrows in a row were missing. Number the lines in
    the brief and say how many there are; then count them in the result.
  - *Lines that leave a line* (one): the five residual connections of a Transformer, each
    of which leaves the axis under a box and enters the box above it, came out run
    together or begun at nothing, and it took two edits to part them. Give such a line
    its three legs and a dot where it starts: it "branches off the vertical axis at a
    small filled dot just below the box, runs out to the left, up beside the box, and
    into the left side of the box directly above, where its arrowhead is; it passes this
    one box only". Say how many such lines there are and that no other line runs inside
    the frame, and where a well-known figure draws them so, name it. Written that way,
    the same figure had all five right at the first attempt. Without the dot and the
    sentence about other lines, two trials each had one line too many, along the inside
    of a frame.
- **Choose the canvas for its pixels and its type.** An image tool returns about 1.5
  megapixels whatever the shape: 1672 px across in 16:9, 1448 in 4:3, 1086 in 3:4. Printed
  150 mm wide, that is 283, 245 and 184 dpi, and the lines are finer in the wider picture.
  The type goes the other way, since a taller figure covers more of the page: at that width
  the same roadmap of 33 texts had type of 7 to 8 pt in 16:9 and of 10 to 12 pt in 3:4. So
  choose landscape for a slide, for a figure that shares its page and for a dense one, also
  when it reads from top to bottom: its stages become wide bands. Choose 3:4 where the
  figure has a page to itself and its type must be large, as a thesis often asks; it then
  lacks pixels, which section 5, step 6, gives it. Say which you chose and what it costs.
- **Length is no problem, and neither is text.** Briefs of 350 to 950 words came out right at
  the first attempt, text for text, with up to 102 texts, Chinese, sizes such as "112x112x32"
  and a formula set as a stacked fraction with a root, a superscript and subscripts.
- **Pin the colours and the line weight down.** Left to a word such as "pale", an image tool
  fills boxes with a colour about twice as strong as a designed figure carries; left to
  "thin", it draws outlines up to twice as heavy. Give every colour as a code from the table
  in `references/figure-recipes.md`, keep the sentence of its visual language that says where
  stronger colour may appear, call every outline a hairline and add the line-weight sentence.
- **Draw every element.** Give each card, each task inside it and each panel a picture, and
  say what the picture shows: `references/figure-recipes.md`, "Pictures".
- **Reference pictures.** A sketch from the user fixes the layout; a figure whose look they
  like fixes the style. Pass it as an input image and say which of the two it is for.
- One figure per brief. Panels in different styles are separate generations, joined afterwards
  with `scripts/panels.py`.

`references/figure-recipes.md` has the layout for each figure type, six visual languages with
the wording that produced them, and the palette with its colour codes.

## 4. Three modes

| Mode | Input image | Prompt |
|---|---|---|
| Text to image | none | The brief from section 3. |
| Sketch to image | The user's sketch or photo of it | "Redraw this sketch as a clean figure. Keep the position of every element and the wording of every label. Change nothing else." Then the Text, Style and Palette lines. |
| Edit | The figure to change | The change, then what stays: "Change the title of the card 'Vector DB' to 'Vector store'. Keep everything else exactly unchanged: every other card, icon, label, arrow, colour and position." One or two changes per call. |

An edit redraws the whole picture; there is no mask. The edit above changed that one title and
nothing else the eye could find, yet pixels shifted along edges all over the picture. After
every edit, verify the whole figure again, not only the part you changed.

## 5. Verify every result

1. **Text.** Run the label check:

   ```text
   uv run <skill-dir>/scripts/check_text.py figure.png --labels labels.txt --crops look/
   ```

   It reads the figure with OCR, reads a second time, cut out and enlarged, every text that
   no label explains, and prints one line per label. With `--crops` it also writes the place
   of each label it did not find in every place and of each extra text, enlarged, and names
   the file at the end of the line:

   - `FOUND` with the number of places, and "on the second reading" where only that one
     found the label.
   - `COUNT` when that number differs from the lines in your file, which is how a missing
     or doubled box shows; where a place is missing, the line names the closest text.
   - `DIFFERS` with what the image says, and for a label listed more than once, in how many
     places it was right. Both readings, the second enlarged, spell the text the same way,
     and not as the label: a letter too many, one left out of a word, two in the wrong
     order, a wrong character, a word put in front. This line is a verdict. Correct the
     text with an edit, and do not check it against the picture first: in a figure you read
     the word you expect. Of forty-three figures made end to end from this file, two were
     handed over with a misspelling, `Questoin` and `ratiio`, which this check had named and
     a look at the picture had passed as a misreading. It has since named a wrong Chinese
     character, 间 where the label had 问, and a `prottein` that the agent took for a
     misreading, and was right each time. If you doubt a line, open the file it names and
     read that text letter by letter, not the whole figure: a stray mark between two words
     can be read as a letter.
   - `MISSING`, with the closest text where there is one: the label was not read as listed
     and the check cannot tell why. OCR leaves out a number that stands apart, reads a Greek
     letter, a subscript or a superscript as something else (`NF-kB` for `NF-κB`, `COflux`
     for `CO₂ flux`) and takes one look-alike for another. Open the file the line names and
     look. Where the line says the text is one letter short in a doubled letter or a run of
     thin ones ("Illumina" read as "llumina", "observability" as "observabiity"), OCR may have
     run them together: count the letters in the picture, one by one.
   - `EXTRA` is text the brief did not ask for: a word the tool added, such as `Legend:`, a
     number in a picture, or drawn detail that OCR took for letters. The file the line names
     shows which.
   - `UNREAD` names a label that is a symbol or a single character, such as "+" or the
     number on a badge, when OCR did not read it: that says nothing about the figure, so
     look for it yourself.

   Bullets, line breaks, the lines of a list, the kind of dash, capital O against zero and
   capital I against small l are allowed for. `OVERALL MATCH` is not proof, since OCR can
   read the right word where the picture has a letter twice: the next step still applies.
   And an edit can leave the fault in. In one figure the tool kept `ratiio` through two
   edits, and after the second this check read `ratio`. So after an edit that was to correct
   a text, cut that text out of the new picture, enlarge it and read it yourself, whatever
   the check says.

   The `TYPE` line gives the size of the type, at the median and for the smallest tenth of
   the lines: in pixels, against the height of the picture, in points on a widescreen slide
   that the picture fills and, with `--width-mm`, in points at the printed width. For a web
   page the pixels are the measure, at the width the picture is shown.
2. **Picture.** Open the image and compare it with the brief: every element present and
   nothing added; as many lines as the brief counts, each starting and ending where it
   says, with the heads it gives them and clear of every heading; the reading order;
   nothing cut off at an edge.
3. **Look.** Measure the colour and the line weight; the eye does not judge them well:

   ```text
   uv run <skill-dir>/scripts/check_figure.py figure.png --look --screen
   ```

   (`--screen` leaves the print resolution out of it, which is step 5.)

   - The `FILLS` line gives the median chroma of the light coloured areas and the share of
     the figure in strong colour. Faint tints read 12 or less (a figure in soft scenes up to
     15, in layer stacks up to 25), with strong colour on 8% of the figure or less. One or
     two above that is no fault: an edit to the lines alone took a scene from 15 to 16.
     When the fills read stronger still, one edit recolours them, and only them: "Recolour
     only the large fills: each box keeps its hue but becomes a faint tint that is close to
     white (blue boxes #E8F2FC, ...). Keep every picture, icon and small part in its present
     colours, and every outline, arrow, text, position and size exactly unchanged." In a
     scene the large fills are the bodies of cells, organelles and tissues, and they take
     the soft tints of `references/figure-recipes.md` (blue bodies #D9EAFA, ...), not the
     faint tints of boxes. Measure again. Where the fills read under 30 before the edit, the
     strong colour was in the pictures and outlines; if its share has fallen by half or
     more, the edit drained them too (one took a scene's from 3% to 1%, and left it washed
     out): keep the figure from before it. One such edit is enough.
   - The `LINES` line gives the thickness of the long straight lines, in pixels and against
     the width of the figure, and names the hairline for a picture of that size and the
     weight that reads as heavy: 2 px and 3 px for every shape an image tool returns, and
     more for an enlarged figure, in proportion. Up to the heavy weight a figure is as fine
     as most published ones, and finer than a hairline is no fault. When the coloured or the dark
     lines read heavier, one edit thins them: "Redraw only the line weights. Make every
     outline of a card, a frame and a legend box a hairline about 2 pixels wide, and every
     arrow and connector the same weight, with smaller arrow heads to match. Keep every
     colour, fill, icon, text, position and size exactly unchanged." One such edit is enough.

   Both edits left the texts and the layout in place. The same command says `skip` for
   greyscale and colour-blind safety when the colours are faint tints, as they should be:
   then nothing was judged. Add `--previews checks/`, look at the four pictures it writes,
   and say in the hand-over that you looked, not that the check passed.
4. **Fix.** One targeted edit per fault, or one for two small faults, in the wording of
   section 4. After two edits with the same fault still there, stop editing:
   - a text that will not come out right: have that one text taken out with an edit
     ("Remove only the line '...', and leave the clean background of its box in its
     place") and set it as real text (`references/diagrams.md`, "Real text over a
     picture"), or convert with `scripts/editable.py` and correct the label in the
     converted file (`references/export-and-checks.md`). In the figure with `ratiio`, the
     edit that removed the line worked where two that were to correct it had not;
   - a line that will not come out right: move the boxes in the brief until that line runs
     straight between two neighbours with nothing to cross, and generate the figure anew;
   - anything else: show the user the best result with its faults listed.
5. **File.** The same check, given the journal or the printed width, judges the file. An image
   tool chooses the pixel size itself: Codex returned 1672 x 941 px for 16:9, 1774 x 887 for 2:1, 1448 x 1086 for 4:3 and
   1086 x 1448 for 3:4. At 300 dpi a 16:9 figure is then 141 mm wide at most, so a
   double-column figure needs more pixels: step 6 gets them from the image tool. Where less
   than a fifth is missing, let `scripts/export_figure.py` interpolate, and say that it did.
   Where no publisher sets a minimum (a thesis, a report, a conference paper), aim for
   300 dpi at the printed width and tell the check so with `--min-dpi 300`; a graphical
   abstract takes the figure of its own guide the same way. A blog or a slide has no printed
   width: say so with `--screen`. A portrait figure has the fewest pixels across, 1086, which
   is 300 dpi at 92 mm: where the page allows, lay a wide figure out in landscape.
6. **Enlarge.** An image tool returns about 1.5 megapixels and no more, but it redraws a part
   of a figure at that size too. So a figure that has passed steps 1 to 4 can be made 1.6 to
   2 times as large, with real detail:

   ```text
   uv run <skill-dir>/scripts/enlarge.py split figure.png
   uv run <skill-dir>/scripts/enlarge.py join figure.tiles
   ```

   `split` cuts the figure in four along clear lines and writes a tile for each part. The
   tiles are all of one size and overlap where the parts meet. It prints, for each tile,
   its file and the file its redraw goes to: `redraw-1.png` beside `tile-1.png`, and so on
   (`tiles.json` in the same folder holds where each tile lies); `--tiles 3x2` cuts in
   six, for a larger result: a figure of 1672 x 941 px came back at 3545 x 1995, with its
   87 texts read back as listed. The figure comes out about as many times larger as the square
   root of 1.5 million over the pixels of one tile, which `split` prints: work out before
   the redraws whether four tiles reach the width you need, and cut in six where they do
   not. Every tile is as large as the largest part, so the figure comes out twice the size
   when the clear lines lie in the middle and smaller when they do not. Between the two
   commands, edit every tile with the image tool, one call per tile, naming the tile's file
   (in Codex, in `referenced_image_paths`), and save each result under the redraw name
   `split` printed for it:
   "Redraw this picture exactly as it is, as a sharper copy. It is one part of a larger
   figure, so nothing may move: keep every element, text, line, icon and colour at exactly
   the same position and the same size relative to the picture. Shapes and lines that are cut
   off at an edge stay cut off at the same place. Add nothing, remove nothing, add no
   margins, re-centre nothing, change no wording. Render crisp text and clean hairlines, each
   line as fine relative to the text as it is now." `join` lays each redraw over its tile,
   keeps the flat colours of the original and writes `figure-enlarged.png`. Along a cut the
   two redraws pass into each other, so that a line shows no step where it crosses; where
   a cut runs through a word or an icon, each side comes from one redraw. A redraw that
   moved or changed visibly, that came back in another shape or that cannot be read is left
   out and its tile enlarged plainly: its line begins with `plain` and says why. Redraw such
   a tile once more, or leave it.

   A changed letter `join` cannot see, so run steps 1 to 3 again on the enlarged figure.
   Whatever you find now, do not give the enlarged figure to the image tool: an edit comes
   back at the tool's own size, and the detail is gone. Mend the one tile instead, with one
   more redraw of it, and `join` again.

   It costs one generation per tile, so the user decides: say what it gives and ask. It is
   worth proposing when the type has few pixels (the `TYPE` line of step 1 gives less than
   18 px for the smallest tenth, as full figures have: enlarged, the type is no larger on
   the page, but sharper), when the print width needs over a fifth more pixels than the
   figure has, or when the user wants a large or sharp file. Where nobody can answer, do
   it only when the request itself asks for a large, a sharp or a high-resolution file, or
   names the resolution it needs. A print width alone is no such request: export at that
   width with `scripts/export_figure.py`, which interpolates, and say in the hand-over
   what the enlargement would add and what it costs.

## 6. Hand over

- The file in the workspace, with its pixel size and, for a figure that will be printed, the
  widest print width it supports.
- What you checked: the label check's result, the colour reading, the size of the type on the slide or
  in print, and what you compared by eye. What you cannot
  check: the science. Ask the user to verify every label, structure and relationship before
  the figure is used.
- The tool name, the brief and every edit instruction, in the order you used them: the user
  needs them for a journal's AI disclosure (`references/export-and-checks.md`, "Disclosure").
- Your assumptions, as a list the user can correct.
