# study-skill

面向公式截图、学术论文、教材章节与工程源码的理工及专业技术通用伴学 Agent Skills 仓库，内含独立运行的伴学主技能 `study` 与可选的现场反馈记录工具 `study-feedback`。

## 仓库结构与技能分工

```text
study-skill/
├── VERSION                     # 单一版本真源（与 skills/study/VERSION 同步）
├── CHANGELOG.md                # 版本变更记录
├── scripts/
│   └── lint_study.py           # 仓库级静态门禁、隐私零残留与绘图库冒烟自检脚本
├── skills/
│   ├── study/                  # 独立伴学主技能（零外部技能依赖，可单独安装运行）
│   │   ├── SKILL.md            # 精炼主干规程（内聚意图分流、单轮定性探针、通用推演防坑与讲义语感）
│   │   ├── VERSION             # 技能版本号
│   │   ├── workflows/          # 3 份真按需外挂：绘图选型与施工（plotting.md）、落盘与双模板（archiving.md）、百页长卷总图（long-corpus.md）
│   │   └── scripts/            # 绘图底座（plot_helper.py）、SVG/笔记快检（check_svg.py / check_notes.py）与更新检查（check_update.py）
│   └── study-feedback/         # 伴学现场反馈记录与提报技能（可选安装）
│       ├── SKILL.md            # 四要素高保真现场记录单生成与邮件 / GitHub Issue 外发规程
│       └── scripts/            # 反馈外发脚本（submit_feedback.py）
├── .github/workflows/
│   ├── ci.yml                  # 跨三端（Linux / macOS / Windows）静态门禁与绘图冒烟 CI
│   └── release.yml             # Git Tag 发布门禁与 GitHub Release 自动创建
└── LICENSE                     # MIT License
```

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

若因权限限制改为**手动复制**目录，可直接用 `python`（或 `uv run --no-project`，纯标准库零依赖秒开）运行内置更新工具拉取对应 Release Tag 升级（升级前会展示变更摘要并备份旧目录）：

```bash
uv run --no-project skills/study/scripts/check_update.py --upgrade
```

## 版本更新感知与隐私退出

- **非阻塞感知**：绘图底座与落盘验收脚本退出时自动在后台刷新本地版本缓存（成功 `72` 小时、失败 `6` 小时负缓存），仅通过 GitHub Releases 重定向头探测最新版本，不消耗 REST API 配额；离线或沙箱网络异常时静默放行，仅在结课或提报反馈收尾时按需附一行轻量提示，不打断伴学流程。
- **按来源分流**：脚本自动识别 `npx skills`、官方 Git 克隆、宿主插件托管与手动复制目录，绝不越权覆盖托管渠道；同时安装 `study-feedback` 时提示一并升级。
- **手动检查与退出控制**：

```bash
# 主动检查最新版本与当前安装来源
uv run --no-project skills/study/scripts/check_update.py --check

# 暂缓提醒 7 天 / 忽略特定版本 / 永久关闭
uv run --no-project skills/study/scripts/check_update.py --snooze 7
uv run --no-project skills/study/scripts/check_update.py --ignore-version 0.5.0
uv run --no-project skills/study/scripts/check_update.py --disable
```

亦可设置环境变量 `STUDY_NO_UPDATE_CHECK=1` 或 `NO_UPDATE_NOTIFIER=1` 禁用检查（`CI` 环境默认自动禁用）。

## 使用说明

两份技能均设有显式触发门禁，日常对话不会误触发：

1. **启动伴学（`/study`）**：
   - 输入 `/study` 并附上问题、公式截图、论文段落或源码路径；
   - 单点概念或单步推导自动走**靶向直答**（零额外文件读取，首轮一屏答清）；整节论文、多步推导或源码模块自动走**分卡伴学**（首轮一站式确认深度档位与首卡关键探针 $\rightarrow$ 定稿蓝图并开讲首卡 $\rightarrow$ 沉静现代讲义推演、按需小例与 `.svg` 矢量配图 $\rightarrow$ 确认继续默认归档推进）。
2. **记录伴学失真反馈（`/study-feedback`）**：
   - 伴学过程中若遇到分卡失当、跳步或探针跑偏，直接输入 `/study-feedback`；
   - 自动回扫当前伴学会话生成保真洗净的四要素 Markdown 记录单代码块，探测本机 `gh` 登录状态后，可按用户选择直接推送给维护者邮箱、通过 `gh` 一键提交至本仓库 GitHub Issues，或保留代码块手动提交。

## 贡献与本地门禁校验

修改任何文档或脚本后，请执行仓库内置门禁脚本完成版本号一致、行数预算、双向路由对齐、文风红线、隐私路径零残留、更新自检与矢量绘图冒烟自检：

```bash
uv run scripts/lint_study.py --dist-check
```

## 开源许可

本项目采用 [MIT License](LICENSE) 开源。
