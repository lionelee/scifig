# scifig

[English](README.md) | 中文

给 AI 编程 agent 用的科研绘图技能包。一条命令就能把 `scifig` skill 装进 Codex、Claude Code、Antigravity 等检测到的 agent：

```sh
npx scifig-agents setup
```

装好后，在 agent 里直接提需求就行，例如："画一张 Transformer 模型架构图"、"画一张图文摘要"、"用这个 CSV 画一张 Nature 单栏的图"、"把这张图导出成 600 dpi 的 TIFF"、"看看这张图能不能投 Cell"。

**示例画廊**：<https://lionelee.github.io/scifig/>，都是 Codex 按这个 skill 从一句话需求做到交付的图。

## 它做什么

| 能力 | 做法 |
|---|---|
| 概念图和结构图：图文摘要、机制图、通路图、流程图、技术路线图、框架图、模型和系统架构图；文生图、草图转图、改图 | agent 把需求写成详细的出图要求，交给 **agent 自带的生图工具**（Codex 的 `image_gen`、Antigravity 的 `generate_image`）出成品。skill 提供这些内容：<br>• 出图要求的写法、各类图的版式；<br>• 内容按六层规划：主体、每个元素里的要点、连线上的标注、输入与产出、阅读辅助、配图；<br>• 实测过的视觉样式；<br>• 带色值的低饱和度配色、细框线的写法；<br>• 逐项核对步骤。<br>本包不调用任何图像 API，也不需要 API key。 |
| 图中文字核对 | `check_text.py` 用 OCR 读出图里的文字，和标签清单逐个比对。没对上的地方会裁出来放大，再读一遍。各种结论：<br>• `DIFFERS`：两遍都读成同一个和清单不一样的拼写，说明图上写错了，要改图；<br>• `MISSING`：OCR 认不准（编号、符号、希腊字母、上下标，或者双写字母被读成一个），要人看；<br>• `COUNT`：标签出现的次数不对；<br>• `EXTRA`：多出来的文字。<br>它还会量出图中文字的字号。 |
| 放大成高分辨率 | `enlarge.py` 把生成的图沿空白处切成大小相同、彼此重叠的几块，由生图工具把每块照原样重画成清晰版，再对齐拼回，得到 1.6–2 倍大的图。细节是重画出来的，不是插值。位置偏了、内容变了或读不出来的块，改用普通放大，并在报告里写明。每块多花一次生成。 |
| 必须用代码画的图：PRISMA / CONSORT 这类数字要能逐个核对的流程图，以及电路图、质粒图谱、系统发育树等规范记号 | agent 写绘图代码，在毫米坐标的画布上画框和箭头，文字和数字逐字准确，输出矢量 PDF。以下情况，其它结构图也走这条路，观感比生图朴素：没有生图工具的 agent、投稿方不接受 AI 图片、你明确要矢量图。 |
| 数据图表 | agent 写 matplotlib 代码，`scistyle.py` 负责期刊栏宽、字体字号、色盲友好配色和矢量输出。选图指引覆盖 46 种图表。数据不经过生图模型。 |
| 投稿文件导出 | `export_figure.py` 按期刊栏宽和 dpi 导出 TIFF、PNG、PDF。 |
| 多面板拼图 | `panels.py` 把多张位图按期刊栏宽排成一张图，自动加 a、b、c 面板字母（PDF 里的字母保持为文字）。 |
| 可编辑版本 | `editable.py` 识别图中文字，从图上擦除，再还原成可编辑文本。可输出 PPTX、SVG（仅文字可编辑）或 SVG（图形也转成矢量）。 |
| 投稿前检查 | `check_figure.py` 检查文件格式、有效 dpi、透明度、色彩模式、灰度可读性和色盲安全，可输出灰度和色盲模拟预览图。<br>• 图里没有足够醒目的颜色可比时，两项颜色检查报 SKIP 而不是 PASS。<br>• 加 `--look` 会量出色块的彩度和框线的粗细。<br>• 加 `--screen` 表示图只用于幻灯片或网页。 |
| 图注 | agent 看图起草；缺的事实留 `[placeholder]`，不从图里猜。 |
| 期刊规范和 AI 图片政策 | 内置 10 家出版社的图片规格和 9 家的 AI 图片政策，都带核实日期。 |

## 安装

需要 Node.js 18.3 以上。运行 Python 脚本需要 [uv](https://docs.astral.sh/uv/)，脚本的依赖在第一次运行时由 uv 自动下载，版本固定在测试通过的那一天。

```sh
npx scifig-agents setup              # 列出计划，确认后安装到检测到的 agent
npx scifig-agents setup --dry-run    # 只看计划，不写任何文件
npx scifig-agents setup --client codex --client claude_code --yes
npx scifig-agents setup --dir ~/somewhere/skills --yes
npx scifig-agents doctor             # 各 agent 的安装状态、生图工具、uv
npx scifig-agents uninstall          # 只删除本工具安装的目录
```

自动检测的 agent 和 [rea-agents](https://www.npmjs.com/package/rea-agents) 6.9.0 一样，共 29 个。判断规则也一样：agent 的配置文件或它自己的目录存在，就算装了。`--client` 用的也是同一套 id，`doctor` 会列出这台机器上找到了哪些。skill 装到哪里分两种情况：

| skill 装到哪里 | Agent（`--client` 的 id） |
|---|---|
| 各自的 skill 目录 | Claude Code `claude_code`（`$CLAUDE_CONFIG_DIR` 或 `~/.claude` 下的 `skills/`）、CodeBuddy `codebuddy`（`~/.codebuddy/skills`）、Antigravity `antigravity`（`~/.gemini/config/skills`）、Trae `trae`（`~/.trae/skills`）、WorkBuddy `workbuddy`（`~/.workbuddy/skills`）、Hermes `hermes`（`~/.hermes/skills`，或 `$HERMES_HOME` 及当前 profile 下的）、Qoder `qoder`（`$QODER_CONFIG_DIR` 或 `~/.qoder` 下的 `skills/`）、Factory Droid `droid`（`~/.factory/skills`）、ZCode `zcode`（`~/.zcode/skills`） |
| 共用的 `~/.agents/skills`，只装一份 | Codex `codex`、Claude Desktop `claude_desktop`、Cursor `cursor`、Cline CLI `cline`、Gemini CLI `gemini_cli`、Windsurf `windsurf`、Devin `devin`、OpenCode `opencode`、GitHub Copilot CLI `copilot_cli`、Command Code `commandcode`、Qwen Code `qwen_code`、Kimi Code `kimi`、VS Code `vscode`、LM Studio `lm_studio`、Grok Build `grok_build`、OMP `omp`、Pi `pi`、DeepSeek Harness `dsh`、FreeBuff `freebuff`、Grok Bot `grok_bot` |

Gemini CLI 和 DeepSeek Harness 设了 `GEMINI_CLI_HOME`、`DSH_AGENTS_HOME` 时，改装到那里的 `.agents/skills/`。

能不能出生图成品，取决于 agent 自带的生图工具：

- **Codex**：内置 `image_gen`。只有它做过实测。
- **Antigravity**：内置 `generate_image`。只按官方文档核对过，没有实际跑过。
- **其它 agent**：没有已知的内置生图工具。数据图表、代码绘图、导出、拼图、可编辑版本、投稿检查、图注都能用；概念图和结构图只能用代码画（观感朴素一些），或者另外接入生图工具。

某个 agent 实际会不会从这些目录加载 skill，由它自己决定；目录的选法和 rea-agents 保持一致。

安装器的行为：

- 每个安装目录里写一个 `.scifig-install.json`，记录版本和内容摘要。再次执行时，内容相同就不动，不同就整体替换。
- 目标位置已经有一个不是本工具安装的 `scifig` 目录时，拒绝操作，不覆盖。
- 几个 agent 读同一个目录时，只装一份，计划里会列出读它的所有 agent。
- 无法交互确认时必须显式加 `--yes`，否则不做任何修改。
- 上次安装被中断时会留下复制了一半的临时目录，下次 setup 会先清掉。
- 装好后要新开一个 agent 会话，才会加载到这个 skill。

同一个包在 GitHub Packages 上叫 `@lionelee/scifig-agents`。不经过 npm 仓库的话，可以直接从 GitHub 运行 `npx github:lionelee/scifig setup`，或者克隆仓库后运行 `node bin/scifig.mjs setup`。

## 使用前须知

下面提到的实测数字都记在 [CALIBRATION.md](CALIBRATION.md)（英文）里。

- **成品观感取决于 agent 自带的生图工具。** 出图效果只在 Codex 的 `image_gen` 上实测过（191 张图，63 次端到端测试），Antigravity 没有实测。没有内置生图工具的 agent（例如 Claude Code）只能用代码画，观感朴素一些。
- **连线是首稿最常出问题的地方。** 内容画满的图里，大约每五张就有一张要为连线改一次图。skill 里的连线规则就是针对这些问题写的：
  - 行和色带的名称放在左端竖栏里；
  - 连线逐条编号，并写明总数；
  - 每条线只画一个箭头；
  - 尽量不让连线交叉。
- **文字靠核对脚本把关，脚本的结论不能凭看图否决。** 生图工具偶尔会写错字。早期测试里，有两张带错字的图被 agent 看一眼就判成"OCR 认错"交付了，所以 `DIFFERS` 必须改图。有三点局限：
  - 双写字母 OCR 常读成一个，这类地方只报 `MISSING`，并提示数一数字母；
  - 希腊字母、上下标和符号 OCR 认不准，只提示"请人看"；
  - 改过字之后，要放大看一眼那处文字。

  个别错字改两次也改不掉，这时把那一行抹掉，用代码写上正确的字。
- **观感按 SciDraw 的 79 张公开样例校准过。** 配色、内容量、字号、框线粗细、配图的画法和细节都是量出来再对齐的，没有凭看图判断：
  - 色块是淡彩，带色值；
  - 通用主题按样例里较满的那一半来画；
  - 框线约 2 px；
  - 配图是三四件物体组成的实心小插画。
- **内容多少取决于你给的材料。** 如果是你自己的研究，图里的事实只来自你说过的话。agent 可以补"这个方法本身是什么、输入什么、产出什么"这类通用内容，会先列出来问你，没人回答时就补上，并在交付说明里逐条列出，供你删改。研究特有的数字、名称、结果和选择不会替你编。教科书式的通用主题（如 Transformer、训练流程）则按通用知识画满，并在交付说明里写明来源。
- **图文摘要分两种。** 投期刊的按期刊要求来（字少，不放数据图）；放在海报、报告、网页上的"研究总览图"画成四五个场景，每个场景配标题和一两行说明。
- **生成的图属于 AI 生成图片。** 架构图、路线图这类结构图现在也由生图工具生成，出版社的 AI 图片政策对它们同样适用（例如 Nature 系列不接受 AI 生成的示意图）。skill 会先问图用在哪里，不允许时改用代码画。
- **生成图的分辨率有限，可以多花几次生成补上。** Codex 的生图工具每次返回约 150 万像素（16:9 时为 1672 × 941），没有尺寸参数。`enlarge.py` 用同一个生图工具分块重画再拼回：
  - 分 4 块，约放大到 1.6–2 倍，多花 4 次生成；
  - 分 6 块，约放大到 2.1 倍，多花 6 次生成。

  没有人可问时，只有需求里写了要大图、清晰图或者指明了分辨率，才会自动放大。不想多花生成时，`export_figure.py` 可以插值放大，脚本会如实说明那不是真细节。
- **横版还是竖版要看用途。** 横版像素多、线条细，适合幻灯片和内容密的图。按固定宽度印刷时，竖版的字更大。所以单独占一页、字要大的图（学位论文常见）用竖版，再用 `enlarge.py` 补像素。
- **`editable.py` 和 `check_text.py` 第一次运行较慢。** 两者都用 OCR，uv 会下载约 100 MB 的依赖（含 OCR 模型），解压后约 600 MB，放在 uv 缓存里；之后每次运行只要几秒。其它脚本只依赖 matplotlib、numpy、pillow。
- **遥测。** onnxruntime 是 OCR 的运行库，它的官方构建默认向 Microsoft 上报使用数据，并在用户目录写入设备标识。`editable.py` 在加载它之前设置了 `ORT_DISABLE_TELEMETRY=1` 来关闭上报，`check_text.py` 复用同一段代码。测试里有一项专门检查运行后用户目录没有新增文件。
- **OCR 的范围。** 模型覆盖英文和中文。希腊字母、上下标、带重音的字母和符号经常识别错；日文假名、韩文、西里尔字母不支持，核对时不拿这些字下结论。转换结果要逐个标签核对。
- **中文。** 图表和结构化图里的中文会自动回退到已安装的中文字体（macOS 上默认是 Heiti SC），拉丁文字仍用期刊字体，PDF 里两者都是可编辑文字。学位论文、基金申请书这类不由期刊排版的文档，可以指定字号和字体，例如五号字、Times New Roman 加宋体：`scistyle.use("default", font_pt=10.5, fonts=["Times New Roman", "Songti SC"])`。
- **期刊数据有日期。** 内置的期刊规格和 AI 图片政策核实于 2026-07-21，投稿前以期刊官网为准。

## 目录

```
bin/scifig.mjs            安装器入口：setup、uninstall、doctor
lib/                      各 agent 的 skill 目录和安装逻辑
skills/scifig/
  SKILL.md                入口：按需求分流
  references/             插图、版式、结构化图、图表、导出与检查、AI 图片政策、期刊规格数据
  scripts/                journals.py、scistyle.py、export_figure.py、panels.py、check_figure.py、check_text.py、enlarge.py、editable.py
test/                     安装器、文档、打包的 Node 测试；脚本的 pytest 测试
eval/                     真实出图的端到端测试、文字核对的回归、和 SciDraw 样例对比的量法（不随 npm 包发布）
docs/                     GitHub Pages 示例画廊
CALIBRATION.md            规则背后的实测数字
```

## 与 sci-draw.com 的关系

本项目参考了 SciDraw AI（sci-draw.com）公开的产品能力：三种绘图模式、数据图表、导出转换、投稿前检查。它是独立实现：

- 不调用 sci-draw.com 的任何接口，不包含它的代码或提示词。
- 打包了它以 CC BY 4.0 发布的参考数据（期刊图片规格、出版社 AI 图片政策、记号表），出处和核实日期见 `NOTICE.md`。
- 想直接使用 SciDraw 的服务，请用它的官方插件 `TopLocalAI/scidraw-plugins`。

## 参与开发

流程和约定见 [CONTRIBUTING.md](CONTRIBUTING.md)（英文），安全问题的报告方式见 [SECURITY.md](SECURITY.md)。常用命令：

```sh
npm test
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest --with pillow --with numpy --with matplotlib --with python-pptx pytest test/python -q -p no:cacheprovider
```

单元测试之外，改 skill 的文档或脚本之后，还要用 `eval/` 里的工具做真实回归（用法见 `eval/README.md`）：

- 改了 `check_text.py`，就在全部端到端图上和上一版逐条对比；
- 改了出图规则，就开几个全新的 Codex 会话复验，这一步会花生图额度。

## 许可

[MIT](LICENSE) © lionelee。第三方材料见 [NOTICE.md](NOTICE.md)。
