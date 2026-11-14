# Contributing to scifig

Thanks for helping. This file says how the project is built and checked, so that a change can be judged the same way as the ones before it. Issues and pull requests can be written in English or Chinese.

## Ground rules

- **No image API, no API key.** Figures come from the host agent's own image tool (Codex `image_gen`, Antigravity `generate_image`). Do not add calls to an image API or a key setting; an agent without an image tool draws in code instead.
- **Measure, do not eyeball.** The look of generated figures (fill colours, line weight, how much they carry) was tuned against measurements of published samples, and over-saturated fills went unnoticed by eye until they were measured. Judge such a change with `check_figure.py --look` or the tools in `eval/measure/`, and record the numbers in [CALIBRATION.md](CALIBRATION.md).
- **The skill is read by agents, literally.** Agents follow `skills/scifig/` to the letter: a rule written as "never" is applied everywhere, and evidence in the text persuades them. Keep `SKILL.md` a short router (the tests hold it to 500 words) and do not name the two long references in it together: agents then read both in one command, past their host's output limit.
- **Facts belong to the user.** The skill must never make up numbers, names or results of the user's own study. Keep that line where it is.

## Set up

You need Node.js 18.3 or later and [uv](https://docs.astral.sh/uv/). uv brings the Python version and packages each script asks for in its PEP 723 header.

```sh
npm test
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pillow --with numpy --with matplotlib --with python-pptx pytest test/python -q -p no:cacheprovider
```

The first Python run downloads about 100 MB for the OCR tests. `PYTHONDONTWRITEBYTECODE=1` keeps `__pycache__` out of `skills/scifig/scripts/`.

## Making a change

1. **Test first.** Add a test that fails for the reason you are fixing, watch it fail, then make it pass. Node tests are in `test/*.test.mjs`, script tests in `test/python/`.
2. **Match the code around you.** Docstrings and comments are plain English and say why. Scripts keep their dependencies in the PEP 723 header, pinned with `exclude-newer`; when you move that date, rerun every test.
3. **Check against real figures where the change touches them:**
   - `check_text.py`: run `eval/text/regress_text.sh` with the old and the new version over the end-to-end figures, and compare the two runs with `eval/text/compare_runs.py`. Every true `DIFFERS` must survive; explain every verdict that changes. Run the stress tests in `eval/text/` as well.
   - `enlarge.py` and `check_figure.py --look`: rerun them on real generated figures and compare the numbers before and after.
   - The skill's documents (`SKILL.md`, `references/`): validate with fresh Codex sessions (`eval/sessions/run_e2e.sh`) and compare their figures with the measurements in `CALIBRATION.md`. Each session spends image generations on your own account, so count them before you start.
4. **Keep the docs in step.** `README.md` and `README.zh-CN.md` say the same things; add a line to `CHANGELOG.md`; put new measurements in `CALIBRATION.md`.

See [eval/README.md](eval/README.md) for the evaluation tools and the local data they read.

## Adding an agent

Agent detection mirrors [rea-agents](https://www.npmjs.com/package/rea-agents) (`dist/application/SupportedClients.js`): the same ids, the same evidence that an agent is present, and the same skills folder, or the shared `~/.agents/skills` when the agent has none of its own. Add an agent there first if you can, then mirror it in `lib/clients.mjs` with a test in `test/cli.test.mjs`. If the agent has a built-in image tool, say which in `imageTool` and describe it in `skills/scifig/references/illustration.md`, section 1.

## Pull requests

- Say what changed, why, and how you checked it: tests, regression runs, sessions and their cost.
- Keep a pull request to one subject.
- CI runs the Node and Python tests on Linux; they must pass.

## Reporting problems

Use the issue templates. For a figure that came out wrong, attach the brief, `labels.txt`, the output of `check_text.py` and `check_figure.py --look`, and the image: they show whether the brief, the image tool or a check went wrong. Security problems go through [SECURITY.md](SECURITY.md), not public issues.

## Code of conduct

Everyone taking part follows the [Code of Conduct](CODE_OF_CONDUCT.md).
