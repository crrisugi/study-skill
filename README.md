# study-skill

面向公式截图、学术论文、教材章节与工程源码的理工及专业技术通用伴学 Agent Skills 仓库，内含独立运行的伴学主技能 `study` 与可选的现场反馈诊断工具 `study-feedback`。

## 仓库结构与技能分工

```text
study-skill/
├── VERSION                     # 单一版本真源（与 skills/study/VERSION 同步）
├── CHANGELOG.md                # 版本变更记录
├── scripts/
│   └── lint_study.py           # 仓库级静态门禁、隐私零残留与绘图库冒烟自检脚本
├── skills/
│   ├── study/                  # 独立伴学主技能（零外部技能依赖，可单独安装运行）
│   │   ├── SKILL.md            # 伴学分流、前置摸底、推演语感与笔记沉淀规程
│   │   ├── VERSION             # 技能版本号
│   │   ├── workflows/          # 按需加载的长卷总图（long-corpus.md）、绘图细则（plotting.md）、归档模板（archiving.md）与语言风格卡（teaching-style.md）
│   │   ├── references/         # 10 份正交草稿纸表征抓手（按单卡核心对象动态读取）
│   │   └── scripts/            # 绘图底座（plot_helper.py）、SVG/笔记快检（check_svg.py / check_notes.py）与更新检查（check_update.py）
│   └── study-feedback/         # 伴学失真诊断与外发提报技能（可选安装）
│       ├── SKILL.md            # 现场脱敏诊断出单与邮件 / GitHub Issue 外发规程
│       └── scripts/            # 脱敏反馈外发脚本（submit_feedback.py）
├── .github/workflows/
│   ├── ci.yml                  # 跨三端（Linux / macOS / Windows）静态门禁与绘图冒烟 CI
│   └── release.yml             # Git Tag 发布门禁与 GitHub Release 自动创建
└── LICENSE                     # MIT License
```

### 10 类正交草稿纸表征（`skills/study/references/`）

| 表征文件 | 适用对象形态 |
| :--- | :--- |
| `continuous-operator.md` | 连续函数、微积分算子、含参/路径积分、卷积与基展开 |
| `spatial-geometry.md` | 二维/三维几何向量、光线/场矢追迹、投影叉乘、刚体旋转与曲线坐标 |
| `transform-phasor.md` | 傅里叶/拉氏/Z 变换、波动复振幅/频谱色散与复相量 |
| `tensor-array.md` | 矩阵代数与线性映射/特征分解、多维张量重排掩码与反向求导 |
| `probability-stochastic.md` | 概率统计、贝叶斯推断、潜变量期望、换元与马尔可夫链 |
| `conservation-network.md` | 电路阻抗网络、热流流体输运、守恒控制体与反馈框图 |
| `discrete-state.md` | 离散算法、指针与递归、状态机、并发协议与工程源码控制流 |
| `proof-logic.md` | 逻辑量词、充要条件、数学归纳、定理证明与组合计数 |
| `optimization-variational.md` | 不等式约束极值、拉格朗日/KKT、凸对偶间隙与变分法 |
| `numerical-precision.md` | 浮点舍入抵消、低精度训练、网格差分稳定性与病态系统 |

## 环境前提

- **必备**：[uv](https://docs.astral.sh/uv/)（用于按需隔离运行 `study/scripts` 下的 `Python >= 3.10` 与 `NumPy / Matplotlib / SciPy` 矢量绘图环境，首次调用时自动拉取锁定的依赖）。
- **Linux 无头环境可选**：如在未预装中文字体的极简 Linux 容器中运行绘图，建议安装开源中文字体（如 `sudo apt-get install fonts-noto-cjk`）以消除紧凑边框测算时的字形告警。

## 安装与升级方式

### 方式一：通过 `skills` CLI 安装（推荐，原生支持版本检查与升级）

```bash
# 同时安装 study 与 study-feedback
npx skills add crrisugi/study-skill

# 或仅单独安装 study 主技能
npx skills add crrisugi/study-skill --skill study

# 检查与升级已安装技能
npx skills check
npx skills update
```

### 方式二：Git 克隆 + 软链（第二推荐，一次拉取同步全宿主）

克隆本仓库后，将 `skills/study`（及可选 `skills/study-feedback`）**软链**至对应 Agent 宿主的技能目录，后续只需在克隆目录执行 `git pull --ff-only` 即可同步全宿主：

- **Claude Code**：`~/.claude/skills/`（或项目级 `.claude/skills/`）
- **Antigravity / Gemini**：`~/.gemini/config/skills/`（或工作区 `.agents/skills/`）
- **Codex / 通用工作区**：项目根目录 `.agents/skills/`

若因权限限制改为**手动复制**目录，可运行内置更新工具拉取对应 Release Tag 升级（升级前会展示变更摘要并备份旧目录）：

```bash
uv run skills/study/scripts/check_update.py --upgrade
```

## 版本更新感知与隐私退出

- **非阻塞感知**：绘图底座退出时自动在后台刷新本地版本缓存（成功 `72` 小时、失败 `6` 小时负缓存），仅通过 GitHub Releases 重定向头探测最新版本，不消耗 REST API 配额；离线或沙箱网络异常时静默放行，不阻塞伴学流程。
- **按来源分流**：脚本自动识别 `npx skills`、Git 克隆、宿主插件托管与手动复制目录，绝不越权覆盖托管渠道。
- **手动检查与退出控制**：

```bash
# 主动检查最新版本与当前安装来源
uv run skills/study/scripts/check_update.py --check

# 暂缓提醒 7 天 / 忽略特定版本 / 永久关闭
uv run skills/study/scripts/check_update.py --snooze 7
uv run skills/study/scripts/check_update.py --ignore-version 0.2.0
uv run skills/study/scripts/check_update.py --disable
```

亦可设置环境变量 `STUDY_NO_UPDATE_CHECK=1` 或 `NO_UPDATE_NOTIFIER=1` 禁用检查（`CI` 环境默认自动禁用）。

## 使用说明

两份技能均设有显式触发门禁，日常对话不会误触发：

1. **启动伴学（`/study`）**：
   - 输入 `/study` 并附上问题、公式截图、论文段落或源码路径；
   - 单点概念或单步推导自动走**靶向直答**（一屏答清）；整节论文、多步推导或源码模块自动走**分卡伴学**（首轮选定深度档位 $\rightarrow$ 按需摸底与先修分流 $\rightarrow$ 排定蓝图 $\rightarrow$ 草稿纸推演、按需小例与 `.svg` 矢量配图 $\rightarrow$ 确认后落盘笔记）。
2. **记录伴学失真反馈（`/study-feedback`）**：
   - 伴学过程中若遇到分卡失当、跳步或摸底跑偏，直接输入 `/study-feedback`；
   - 自动回扫当前伴学会话并生成脱敏的五要素 Markdown 诊断代码块，探测本机 `gh` 登录状态后，可按用户选择直接推送匿名诊断给维护者、通过 `gh` 一键提交至本仓库 GitHub Issues，或保留代码块手动提交。

## 贡献与本地门禁校验

修改任何文档、表征文件或绘图脚本后，请执行仓库内置门禁脚本完成版本号一致、行数预算、双向路由对齐、四槽骨架、文风红线、纯自包含、隐私路径零残留、更新自检与矢量绘图冒烟自检：

```bash
uv run scripts/lint_study.py --dist-check
```

## 开源许可

本项目采用 [MIT License](LICENSE) 开源。
