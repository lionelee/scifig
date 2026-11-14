# eval：skill 的实测与回归工具

> 版本号在 2026-11-14 重置为 0.1.0，作为第一个公开版本。下文里的 0.4.x–0.5.x 是公开前内部迭代的编号；其中 0.5.2 就是重置后的 0.1.0。

这里放的是开发时用来验证 skill 的脚本，不随 npm 包发布（`package.json` 的 `files` 只列了 `bin`、`lib`、`skills`）。样例图、生成的图和会话记录都不在仓库里，脚本通过 `env.sh` 里的变量找到它们：

| 变量 | 默认值 | 是什么 |
|---|---|---|
| `SCIFIG_SKILL` | 本仓库的 `skills/scifig` | 给 Codex 会话用的 skill |
| `SCIFIG_GEN` | `eval/runs` | 端到端测试的产物，每次会话一个文件夹（图、`labels.txt`、`run.log`） |
| `SCIDRAW_SAMPLES` | `eval/samples` | SciDraw 的公开样例，只用来对照 |
| `UV_CACHE_DIR` | `~/.cache/uv` | 会话里跑脚本要写的 uv 缓存 |

`eval/runs` 和 `eval/samples` 放的是本地数据，不提交到仓库。数据已经放在别处的话，建成软链接即可，例如 `ln -s ~/data/scifig-runs eval/runs`。

## sessions：真实出图（花生图额度）

都调用本机的 `codex exec`，走你自己的 Codex 账号和生图额度，跑之前先估算次数。

- `run_e2e.sh 工作目录 需求文件`：开一个全新会话，只给 skill 和需求，从写出图要求一路做到交付。会话结束时会列出 skill 里不清楚、写错或多花了一次生成的地方（`NOTES ON THE SKILL`）。
- `run_fix.sh 工作目录 需求文件`：给全新会话一张做好但没核对过的图（`figure.png`、`brief.txt`、`labels.txt`），看它能否按 skill 核对并改对。
- `run_brief.sh 工作目录 出图要求文件 输出名`：把一份出图要求原样交给生图工具，生成一次。
- `run_edit.sh 工作目录 原图 输出名 指令`：用生图工具改一次图。
- `redraw_tiles.sh 图块目录`：把 `enlarge.py split` 切出的每一块重画一遍，每块花一次生成。

## text：文字核对的回归

- `regress_text.sh 输出目录 [脚本目录]`：用 `check_text.py` 核对 `SCIFIG_GEN` 下所有带 `labels.txt` 的端到端图，每张图存一份 JSON。脚本目录默认是本仓库的；拿旧版本的副本跑一遍，就是基线。约 100 张图一分半钟。
- `compare_runs.py 基线目录 新目录`：逐个标签比较两次结果，列出结论变了的标签和总数。改 `check_text.py` 之后必须跑：0.5.1 的基线在 98 张图上有 5 处 `DIFFERS`（"Questoin"、两处 "ratiio"、"间题"、"Takeaway:"），全是真错字，一处都不能丢。
- `stress_cards.py 输出目录 [脚本目录]`：用卡片版式画出写对的标签（5 种字体、4 种字号、PNG 和 JPEG），报告误判的 `DIFFERS`。0.5.1 是 3/1040，0.5.2 是 0。
- `stress_edges.py 输出目录 [脚本目录]`：标签左边 3 px、6 px 处有卡片边框，或者没有边框。0.5.1 误判 31/1260，0.5.2 是 6，剩下的都是 OCR 在词中间多读出字母。在词中间时，按规则以第一遍读数为准，这样才能抓住生图工具在词中间多写的字母。
- `vary.py 图 文字`：同一处文字换多种裁法和放大倍数各读一遍，看 OCR 的读数怎么变。双写字母的规则就是用它量出来的。

## measure：和 SciDraw 样例对比观感

工具目录参数一律传 `$SCIFIG_SKILL/scripts`（`measure.sh` 会自动传），分组写法是 `名字=路径[,路径...]`，路径是文件夹时表示其中所有 PNG。

- `colour_stats.py`：色块的明度和彩度（CIELAB）、强色面积。
- `content_stats.py`：OCR 读出的文字行数和字符数。
- `type_size.py`：字号占图高的比例，以及铺满幻灯片时的磅数。
- `stroke_fine.py`：线宽，量法和 `check_figure.py --look` 相同，精确到 0.1 px。
- `element_stats.py`：图形元素（图标大小的形状）的个数和面积。
- `bold.py`：配图的实心程度和可见颜色的面积。
- `detail.py`：细节，包括图画由多少个小部件组成、带括号注释的行占多少、轮廓总长。
- `groups.sh`：2026-11-13 那次对比的分组（`sd-*` 是 SciDraw 样例，`our-*` 是我们的图）。新的一轮要改里面的路径。
- `measure.sh 工具名 [--each]`：对 `groups.sh` 的每组跑一种量法。
- `measure_one.sh 名字=路径 ...`：一次量出几张图的丰富程度、颜色、字号和线宽。
- `density.py`：按文字行数把样例和我们的图分档比较，读的是 `measure.sh` 输出的 `type.out`、`colour.out`、`bold.out`、`stroke-each.out`。
- `crops.py 输出图 高度 标签=路径:x0,y0,x1,y1 ...`：把几张图的同一相对位置裁出来并排放，用来看细节。

量观感不要只凭看图：饱和度偏高这个问题，逐张看图时没看出来，是量出来的。量法本身也要先验证，线宽一开始按整像素计算就读错过。
