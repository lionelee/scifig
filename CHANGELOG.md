# Changelog

All notable changes to this project are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-11-14

First public release.

### Added

- The `scifig-agents` installer with `setup`, `uninstall` and `doctor`. It detects the 29 agents that rea-agents 6.9.0 detects and installs the skill into each agent's own skills folder, or once into the shared `~/.agents/skills`. Each install records its version and a content digest; the installer refuses folders it did not install and clears what an interrupted setup left behind.
- The `scifig` skill, which routes a figure request to the right method:
  - briefs for the host agent's image tool, with layouts per figure type, a six-layer content plan, tested visual styles, a low-saturation palette with colour codes, hairline weights, rules for routing connectors and a verification procedure;
  - code-drawn diagrams for PRISMA and CONSORT flows and formal notations;
  - journal-style charts, with guidance for 46 chart types;
  - export, multi-panel figures, editable PPTX and SVG, pre-submission checks and figure legends;
  - figure specifications of 10 publishers and AI-image policies of 9, each dated.
- Scripts:
  - `check_text.py` compares a figure's text with its labels by OCR, with the verdicts `DIFFERS`, `MISSING`, `COUNT` and `EXTRA`, and measures the type size.
  - `enlarge.py` redraws a figure tile by tile to make it 1.6 to 2.1 times larger.
  - `check_figure.py` checks format, effective dpi, colour mode, greyscale and colour-blind legibility; `--look` measures fill chroma and line weight.
  - `export_figure.py`, `panels.py`, `editable.py`, `scistyle.py` and `journals.py`.
- `eval/`: tools for end-to-end runs with Codex, a regression of the text check over real figures, and comparisons with published samples. `CALIBRATION.md` holds the measurements behind the rules.
- A gallery on GitHub Pages.

[Unreleased]: https://github.com/lionelee/scifig/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/lionelee/scifig/releases/tag/v0.1.0
