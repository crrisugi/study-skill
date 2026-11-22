# Changelog

All notable changes to `study-skill` will be documented in this file.

## [0.2.3] - 2026-11-22

### Added
- 新增按需加载的归档细则与产出模板 `skills/study/workflows/archiving.md`，将合并慢嚼卡、总卡/短卡形态、相对配图规范、`check_notes.py` 校验命令及蓝图/单卡模板从主干剥离，为 `study/SKILL.md` 释放两千余字上下文空间。

### Changed
- 升级 `skills/study/workflows/long-corpus.md`：明确失真长卷派并行只读子代理侦察时的交接范围与四项压缩回执契约（章节标题、页数、核心推导/图示位置与跨章前置依赖），禁抄正文、禁越权定档。
- 升级 `skills/study/workflows/plotting.md`：新增连续失败熔断机制，脚本报错或手写 SVG 体检碰撞连修 2 次仍未过时立即停手，改拆简图、换数表或说明卡点交用户定夺。
- 升级 `skills/study-feedback/SKILL.md`：模式一零打字回扫遇到多处明显卡顿且归因不唯一时，先一句列出候选现场请用户确认再写池，避免脑补根因。

## [0.2.2] - 2026-11-22

### Changed
- 统一 `skills/study/SKILL.md` 先修铺垫卡编号规范：开局先修、大断层分流切片及中后卡/子卡前插先修统一编为 `目标卡号_0.1 / _0.2`（如 `卡 01_0.1`、`卡 02_0.1 / 02_0.2`、`卡 03.1_0.1`），实现 Windows / macOS / VS Code / Obsidian 跨平台排序一致，并明确与同卡多机制拆分 `k.1 / k.2` 彻底隔离。
- 升级 `skills/study/scripts/check_notes.py`：支持 `目标卡号_0.1 / _0.2` 与子卡前先修，修复蓝图正则对带后缀卡号的静默截断漏洞并防正卡 `0.x` 标题误判；改按真实学习顺序计算 `latest_card`；新增同目录重号卡 `[WARN]` 提醒，并兼容旧版 `03.0 / 02.0a / 02.0.1` 写法（放行且打印温和迁移提醒）。
- 升级 `skills/study-feedback/scripts/lint_study.py`：补齐 `check_notes.py` 新旧先修编号、防误判、语义排序与重号提醒离线断言。

## [0.2.1] - 2026-11-21

### Added
- 新增按需下钻绘图细则 `skills/study/workflows/plotting.md`，将两类图分工、曲线顺带打印特征点小表、手写快检与跨宿主内联展示拆离主干并清单化。
- 新增纯 Python 标准库零依赖脚本 `skills/study/scripts/check_svg.py`，全量检查手写 `<svg>` 的 XML、4 数值 `viewBox`、柔和浅底防暗黑隐身、越界、连线穿字、文字重叠、裸 LaTeX 源码泄露与按色相聚类 `<= 3` 主色系，并支持 `--html` 过检自动补自适应样式打透明底网页壳。
- 新增纯 Python 标准库零依赖脚本 `skills/study/scripts/check_notes.py`，在带图单卡落盘后与末卡结课前核验 `<agent-embed>` 残留、绝对路径、引用 `assets/*.svg` 实存、正文染色/全角感叹号、孤儿图与蓝图进度。
- 新增纯 Python 标准库零依赖脚本 `skills/study-feedback/scripts/submit_feedback.py`，封装 `gh` 登录探测、邮箱接口 JSON 校验、GitHub Issue 提交与成功后清理临时文件。

### Changed
- 升级 `skills/study/scripts/plot_helper.py`：启用 `svg.fonttype="path"` 矢量文字转曲防字体回退错位，强拦截裸 Unicode 上下标、自动去含公式混排粗体，放宽双子图画布并启用 `constrained` 布局，新增自动空角说明框 `note_box`、16 向防压线 `label_point`、可见图例框自动避让与防撞体检、`save_svg(..., html_path=...)` 及纯文字碰撞自检（默认不读图省开销）。
- 精简 `skills/study/SKILL.md` 并拆短超长单行（零 `>260` 字预警）：新增独立单轮新符号多选快筛、按需引出动机、补钻下位断点硬触发、中后卡断层承接、三类隐形符号兜底与 `k-A/k-B` 边界；主干绘图小节瘦身为硬底线与按需读取 `workflows/plotting.md` 入口。
- 升级 `skills/study/workflows/long-corpus.md`：补齐长卷单元深浅实核、摸底双向调档、速通章节不免测与长卷速通按节拆存三块短卡。
- 升级 `skills/study-feedback/SKILL.md` 与 `lint_study.py`：外发流程改调 `submit_feedback.py`；门禁将 `study/SKILL.md` 调整为 `<= 200` 行与 `<= 12,500` 字（单行 `> 260` 字软提醒），并将全部新脚本纳入隐私检查、离线冒烟测试与 `--sync-to` 同步。

## [0.2.0] - 2026-11-20

### Added
- 新增百页长卷伴学总图与跨单元按需规程 `skills/study/workflows/long-corpus.md`，支持自适应深浅摸底、独立目录隔离与跨单元前提继承。
- 新增跨宿主低打扰更新探测与按来源分流升级脚本 `skills/study/scripts/check_update.py`（纯标准库，支持 `npx skills` / `git-clone` / 宿主插件 / 手动复制识别、`72h` 缓存与 `6h` 失败负缓存、GitHub Releases 302 探测）。
- 在 `plot_helper.py` 退出阶段挂载非阻塞更新提示旁路，并在 `study-feedback` 补入轻量版本提示入口与 `lint_study.py` 版本一致性和更新自检门禁。

### Changed
- 优化分卡伴学主干推演：`SKILL.md` 明确多物理量并列概览节按原序排卡并先立主线骨架、收紧 `k-A/k-B` 适用范围、原式首次出场逐一交代新符号下标与正斜体区分，以及降维算例先说明暂略层。

## [0.1.0] - 2026-11-18

### Added
- 初始发布 `study` 与 `study-feedback` 双技能、`10` 份正交草稿纸表征文件、`plot_helper.py` 科学矢量绘图底座及跨三端 `lint_study.py` 静态与冒烟 CI 门禁。
