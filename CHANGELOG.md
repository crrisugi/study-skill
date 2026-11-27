# Changelog

All notable changes to `study-skill` will be documented in this file.

## [0.2.10] - 2026-11-27

### Added
- `skills/study/scripts/plot_helper.py` 新增公式框图三原语：`new_diagram`（无坐标轴浅底画布）、`draw_box`（自适应贴合公式大小或固定格子尺寸的圆角公式框）与 `flow_arrow`（连接坐标或 `draw_box` 对象自动接边并带白底短标）。

### Changed
- 细化绘图分工并防臃肿：`skills/study/workflows/plotting.md` 按内容公式复杂度划界，曲线/谱图/热力图/几何矢量与含分式、导数、积分、求和、矩阵元、转置或多重上下标的结构流向框图走 Python `plot_helper.py`（优先横排并保持简标签），纯文字/代码短词与简单符号流程状态图继续手写 `<svg>` + `check_svg.py`，二三节标题同步改为按工具命名；清理 `tensor-array.md`、`conservation-network.md`、`probability-stochastic.md`、`proof-logic.md`、`discrete-state.md` 第 3 节框图描述中的“手写 `<svg>`”限定（只保留画圆角框图/切面）。
- 升级 `plot_helper.py` 防呆与体检：出图前硬拦截 `$...$` 内 `\begin{...}` 与中文及原件式号/章节索引；将矩形框（`ax.patches` 与文字 `bbox`）纳入 `<= 3` 种主色聚类统计，并新增固定尺寸框文字撑破体检。
- 升级 `scripts/lint_study.py`：新增 `plot_helper.py` 顶部速查注释超 `25` 行软预警，并补全公式框图、3 项拦截、4 主色与固定框撑破离线冒烟断言。

## [0.2.9] - 2026-11-25

### Changed
- 符号保原与前置补讲规范：明确非同式写不开时不擅自改添下标、英文缩写上下标与多字母缩略记号首次出场须写全英文原词与中文含义；厘清原书略过前置的“直接引用”与“拆开补讲”分界并支持联网核实；正卡成段补讲前置须用 `前置铺垫：…` 隔开且补完切回目标正卡免重测、补讲均讲到接通正卡即收手；同步对齐 `skills/study/workflows/{archiving,long-corpus}.md` 的先修切面免测边界及速通节选“从零搭桥”单发调档题。
- 倒数域原域尺度先行与前提校准：`skills/study/references/transform-phasor.md` 第 2 节拆清“原域尺度先行（倒数域变量与原域尺度联立约束时先回同量纲原域立画面并按需举原域小例，再取倒数翻回）”与“单向切域核对（限定于解微分或卷积方程）”，并在主干对照表轻提；顺带为 `skills/study/references/discrete-state.md` 补齐“讲解算法优化且存在可对照的朴素解法”前提。
- 多步搭桥逐段落地与边界临界分段：`skills/study/SKILL.md` 第二步将“兑现符号与选答”与“逐段兑现搭桥”拆短单列，要求“从零搭桥”含多步链条时须用易心算小例逐段搭通至临界分界与分支跳转；第三步放宽同算例调临界参数对比限制，并新增全理工通用的“边界临界分段”（并列边界来源与约束范围 $\to$ 判明主导限制与受截断物理量/定义域并按需配易心算对照 $\to$ 按主导边界分段、明确临界等号归属并如实命名分段）。
- 全套 `15` 份规程文档专业化措辞统一清理：全面清除 `skills/study/SKILL.md`、4 份 `workflows/*.md` 与 10 份 `references/*.md` 中的口语俗词与江湖比喻，统一对齐 `teaching-style.md` 的清朗现代书面语风格。
- 实测边界收口：`skills/study/SKILL.md` 收紧外部定理/略证规律免摸底边界（仅借结论过渡时免摸底，凡须凭其联立推导、分析机制或划临界分段者仍按独立底座测含义、趋势与约束而不追溯证明）；强化“边界临界分段”对定义域越界与无量纲比值分界伪装的识别，要求分段前先并列写出各独立边界并代入临界取等点核对定性结论定等号归属；`skills/study/references/transform-phasor.md` 扩展覆盖衰减率/时间常数并要求各方统一换算原域完成比较后再整体转回变换域，杜绝单方中途折返消元。

## [0.2.8] - 2026-11-25

### Changed
- 优化 `skills/study/SKILL.md` 开局蓝图可见时机：第二轮发首卡摸底题前，先在正文开头亮出初拟分卡路线并注明摸底后定稿，避免“蒙眼答题”；收齐摸底后再按真实底座定稿写入 `00_伴学脉络蓝图.md` 并同轮开讲 `卡 01`。
- 废止单篇合存 `01_全篇脉络总卡.md` 并清理 `skills/study/workflows/long-corpus.md` 重复条目：单篇与长卷全面统一为逐卡落盘（`直觉速通` 存轻量短卡、`标准推演 / 深度精读` 存完整讲义卡），解决单篇速通与中间核心卡临时升档之间的编号割裂问题。
- 统一各档整卡末尾落盘选择权与配图延迟入库：写目录模式下非末卡提供“落盘 / 落盘并继续 / 继续（跳过本卡存盘）”、末卡提供“落盘 / 继续（跳过存盘结课）”；`skills/study/workflows/plotting.md` 与 `archiving.md` 明确讲卡阶段配图先存系统临时目录，确认落盘该卡后再写入工作区 `assets/`。
- 蓝图未落盘留痕与校验升级：跳过存盘的卡片照常在蓝图 `## 三、已学主线与阶段收获` 补写收获并括注 `（未落盘）`；升级 `skills/study/scripts/check_notes.py` 解析该标记以放行未落盘计划卡并统计跳过张数，同步在 `scripts/lint_study.py` 补全离线断言。

## [0.2.7] - 2026-11-23

### Changed
- 优化 `skills/study/SKILL.md` 算式引用与独立可读规程：将原“引用直写算式”拆为精简版 `不夹原件编号` 与 `引用直写算式` 两短项，明确跨卡、隔小节、对比两式结构或代入替换前先完整复写当前用到的原式（对比时一并写全），且同一统称下包含总式或多条子式时引用其中某一条须写明具体子式名或作用、不拿统称笼统代指。
- 优化蓝图主线账本与开讲顶部路线回放：取消 `skills/study/workflows/archiving.md` 的 `25~45` 字硬限与 `SKILL.md` 的“更早步骤并成半句”要求，改为 `1` 条 `1~2` 句通顺动作白话（说清卡在什么麻烦、做了什么转化、还差哪一步；先修卡 `1` 句短话挂在正卡前），超过 `5` 条时将更早正卡与已用完的先修铺垫卡合并为 `1` 条完整白话句、最近 `3~4` 张正卡原样列出。
- 明确交互提问工具触发边界与静谧收尾：仅在开讲前选档、筛符号、摸底、分流、调档与总图确认等短提示发选择题时调用交互提问工具；长讲义与半步停顿末尾一律禁调弹窗控件，同时取消 `k-A` 半步预测与整卡末尾轻自核单选，改以一句平实短话收尾确认。
- 全套说明文档去重瘦身：清理 `skills/study/SKILL.md`（精简至 `129` 行 / `10,753` 字，零 `>260` 字长行）、`workflows/archiving.md`、`workflows/plotting.md`、`workflows/long-corpus.md`、`scripts/plot_helper.py` 顶部注释及 `6` 份 `references/*.md` 共 `11` 处跨文件复读、长清单、脚本已检重复提醒与配图底色口径微差。
- 优化讲义排版防断渲染与落盘防呆：`skills/study/workflows/teaching-style.md` 将多步拆块升级为按体量分层（轻量单层编号、重载改用 `###` 三级小标题，禁止嵌套子列表夹写 `$$` 或 4 空格缩进续行）；`skills/study/scripts/check_notes.py` 新增 CommonMark 状态机扫描，硬拦截会被误判为缩进代码块的含公式缩进行，并在 `lint_study.py` 补齐正反离线断言。
- 剥离维护者私有工具与公开分发边界：将仓库级静态门禁移至 `scripts/lint_study.py`（移除 `--bundle`、`--sync-to` 等本地维护参数，更新 `.github/workflows/{ci,release}.yml`）；移除 `skills/study-feedback/local_config.example.json`、`skills/study-feedback/SKILL.md` 中的模式二复盘维护分支及 `.gitignore` 私有规则，使公开版 `study-feedback` 专注于现场脱敏诊断与邮件 / GitHub Issue 提报。

## [0.2.6] - 2026-11-23

### Added
- 新增独立按需读取的伴学讲义语言风格卡 `skills/study/workflows/teaching-style.md`：确立对话与落盘一致的清朗现代书面讲义腔、零“我们”轻路标与平实现代动作动词、路线式 `##` 小标题与 `1. **短动作标题**：` 多步拆块、真拐点停半拍说透操作画面、`---` 分割线接 `核心结论/成立前提` 同框、框外零复读 `得失权衡/易混边界` 及 4 组通用正反改写标尺。
- 在 `00_伴学脉络蓝图.md` 设立动态 `## 三、已学主线与阶段收获` 账本（每卡落盘追加 `1` 行因果人话、开新卡原样贴出并超 `5` 项压早留近、结课补 `2` 行收官核心式与总前提），并在 `skills/study/scripts/check_notes.py` 扩展 `--recap`（优先读取蓝图主线账本，旧目录自动兜底抓取卡片核心结论并兼容引用框写法）。

### Changed
- 升级 `skills/study/SKILL.md` 与 `skills/study/workflows/archiving.md`：协同为 `SKILL.md` 讲义语感段瘦身并挂接 `teaching-style.md` 按需入口；单卡模板骨架同步更新为路线式小标题、`1. **动作**：` 拆块、`---` 分割线接结论前提同框与框外零复读两项。
- 算例改按需克制与心算底线：划清必须举小例与禁推完硬代数字验算边界，保留“拆结构简化”；彻底废止蓝图全篇共用底座算例，改由单卡就地取干净小整数或精确简式并单卡锁死不换例；多源对照表按需附表后；取消趋势曲线图正文强制附特征点小数表；同步对齐靶向直答、速通与落盘自查（禁存盘补编算例）。
- 教学推演与交互优化：无未验新符号与新底座时开篇用一句短话明示免摸底依据再直讲（落盘剥离）；动笔前先亮出本卡终点与核心招数再顺推；对称重复式只写代表，异号或异界项逐一明说；`k-A` 关键转折预测与整卡天然易混点自核改用跨宿主零打字按需单选（答对自核同轮直接落盘）。
- 明确 `10` 份 `skills/study/references/*.md` 的按需工具书定位（本卡不需算例时跳过第 1 节，并统一加“确需举算例时”轻提示）；`skills/study/workflows/plotting.md` 同步改为按需打印特征点小表；`skills/study-feedback/scripts/lint_study.py` 补全全部新增离线断言。

## [0.2.5] - 2026-11-22

### Changed
- 重构 `skills/study/workflows/archiving.md`：废止单卡五块黑括号列表模板，改以对话已讲顺的推演为底稿轻整理落盘，保留 `##` 自然人话小标题、短段落、居中大公式、关键展开步与就近配图，不再压缩成干提纲或将同一算例拆成两头重复写；剥离路线报幕、摸底选择题与答题记录、试错闲话、`k-A / k-B` 中间停顿语、卡末心算问句及交互提示，自然揉顺多轮追问解释与换路小例；摸底勾选新符号与本卡轻铺垫无痕留正文、答错易混点无痕收进结尾并优先讲透、答对跳过的基础不单辟前置框；原五要素退居落盘前自查清单，单卡模板改为清爽 `##` 骨架示例。
- 升级 `skills/study/workflows/long-corpus.md` 与 `skills/study/SKILL.md`：长卷 `直觉速通` 分节短卡与单篇 `直觉速通` 总卡同步撤掉黑括号外壳，统一改用自然 `##` 小标题短讲义；清理主干中旧“完整笔记卡模板”残留表述，拉齐对话与笔记均采用自然小标题的写法。

## [0.2.4] - 2026-11-22

### Changed
- 升级 `skills/study/SKILL.md`：明确讲解与落盘笔记独立可读定位，原件章节、页码或函数位置只留蓝图和卡头且不记公式号；对话小标题、推演正文、核心结论、配图与笔记正文均不夹带公式号、章节号、附录或引理裸编号及裸行号，整卡不另编公式号；跨卡或隔段引用直接复写对应算式、条件或关键代码，紧邻步骤用“上式”或名字与作用承接（保留公认定理名与真实函数名）；旁支与延后留账只点明内容、不甩空指路，原件附录步骤按主干必走当场算通或支线说清结论分流。
- 升级 `skills/study/SKILL.md`、`skills/study/workflows/plotting.md` 与 `skills/study/workflows/archiving.md`：原件已有清晰图示不再仅靠文字指认，改为按“现成独立图直接复制 → 整页图干净截取并裁掉旧图注 → 截不出或模糊杂乱照意思 `.svg` 重画”搬进对话内联展示并保留原格式存入 `assets/`；图内文字禁写原件式号、章节号与附录索引；单卡模板标题行收口为 `原位置`，相对配图路径兼容原图后缀。
- 升级 `skills/study/scripts/check_svg.py`、`skills/study/scripts/check_notes.py` 与 `skills/study-feedback/scripts/lint_study.py`：`check_svg.py` 拦截手写 `<svg>` 夹带原件式号与章节/附录索引；`check_notes.py` 将 `assets/` 孤儿图检查扩展至 `.svg / .png / .jpg / .jpeg / .webp`，并在跳过首行卡头、代码块与蓝图/总图后对正文漏网原件索引输出 `[WARN]` 提醒（不阻断落盘）；`lint_study.py` 补齐正反离线断言。

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
