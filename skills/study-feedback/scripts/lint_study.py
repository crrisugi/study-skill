"""study 与 study-feedback 双技能静态门禁、防耦合红线、隐私零残留与绘图库冒烟自检脚本

用法：
  uv run "<study-feedback目录>/scripts/lint_study.py"
  uv run "<study-feedback目录>/scripts/lint_study.py" --dist-check
  uv run "<study-feedback目录>/scripts/lint_study.py" --bundle "<scratch>/study_bundle.md"
  uv run "<study-feedback目录>/scripts/lint_study.py" --sync-to "<开源合仓根目录>"
"""
from __future__ import annotations
import argparse
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

FEEDBACK_DIR = pathlib.Path(__file__).resolve().parents[1]
STUDY_DIR = pathlib.Path(os.environ.get("STUDY_DIR") or (FEEDBACK_DIR.parent / "study"))
REPO_ROOT = STUDY_DIR.parent.parent if STUDY_DIR.parent.name == "skills" else None
STUDY_MD = STUDY_DIR / "SKILL.md"
STUDY_VERSION = STUDY_DIR / "VERSION"
FEEDBACK_MD = FEEDBACK_DIR / "SKILL.md"
REFS_DIR = STUDY_DIR / "references"
WORKFLOWS_DIR = STUDY_DIR / "workflows"
SCRIPTS_DIR = STUDY_DIR / "scripts"
PLOT_HELPER = SCRIPTS_DIR / "plot_helper.py"
CHECK_SVG = SCRIPTS_DIR / "check_svg.py"
CHECK_NOTES = SCRIPTS_DIR / "check_notes.py"
CHECK_UPDATE = SCRIPTS_DIR / "check_update.py"
SUBMIT_FEEDBACK = FEEDBACK_DIR / "scripts" / "submit_feedback.py"
STUDY_MAX_LINES = 200
STUDY_MAX_CHARS = 12500
STUDY_WARN_LINE_CHARS = 260
SEMVER_RE = re.compile(r"^[vV]?(\d+)\.(\d+)\.(\d+)(?:-[0-9A-Za-z.-]+)?$")

SLASH_CMD_RE = re.compile(
    r"(?<![A-Za-z0-9_.:/<>\\~-])/(?!(?:study(?:-feedback)?|tmp|home|Users|usr|etc|var|dev|bin)\b)([a-z][a-z0-9_-]{2,})\b"
)
EXT_SKILL_RE = re.compile(r"\b(?!study[-_]skill\b)[a-zA-Z0-9_]+[-_]skill\b", re.I)
COUPLED_TOOL_RE = re.compile(r"\b(?:ask_question|write_file|AskUserQuestion|request_user_input)\b")
CI_DEFAULT_USERS = {"runner", "ubuntu", "root", "admin", "administrator", "codespace", "git", "user", "default"}


def strip_code_and_templates(md_text: str) -> str:
    head = md_text.split("## 产出文档模板")[0]
    head = re.sub(r"```.*?```", "", head, flags=re.S)
    head = re.sub(r"`[^`]*`", "", head)
    return head


def find_external_skill_mention(raw_text: str) -> str | None:
    cleaned = re.sub(r"https?://\S+", "", raw_text)
    if m := SLASH_CMD_RE.search(cleaned):
        return f"/{m.group(1)}"
    if m := EXT_SKILL_RE.search(cleaned):
        return m.group(0)
    extra = [s.strip() for s in os.environ.get("EXTRA_FORBIDDEN_SKILLS", "").split(",") if s.strip()]
    if extra:
        extra_re = re.compile(r"\b(?:" + "|".join(re.escape(s) for s in extra) + r")\b")
        if m := extra_re.search(cleaned):
            return m.group(0)
    return None


def check_docs_and_assets() -> list[str]:
    errs: list[str] = []
    if not STUDY_DIR.exists() or not STUDY_MD.exists():
        return [f"未找到同级 study 技能目录（可通过 STUDY_DIR 环境变量指定）: {STUDY_DIR}"]

    study_raw = STUDY_MD.read_text(encoding="utf-8")
    study_lines = study_raw.splitlines()
    study_chars = sum(len(line) for line in study_lines)
    if len(study_lines) > STUDY_MAX_LINES:
        errs.append(f"study/SKILL.md 行数超限: {len(study_lines)} > {STUDY_MAX_LINES}")
    if study_chars > STUDY_MAX_CHARS:
        errs.append(f"study/SKILL.md 总字数超限: {study_chars} > {STUDY_MAX_CHARS}")

    fb_lines = FEEDBACK_MD.read_text(encoding="utf-8").splitlines()
    if len(fb_lines) > 85:
        errs.append(f"study-feedback/SKILL.md 行数超限: {len(fb_lines)} > 85")

    disk_refs = {p.name for p in REFS_DIR.glob("*.md")} if REFS_DIR.exists() else set()
    linked_refs = set(re.findall(r"\(references/([a-zA-Z0-9_-]+\.md)\)", study_raw))
    if not disk_refs:
        errs.append("缺失 study/references/*.md 草稿纸表征核心子文件")
    if disk_refs != linked_refs:
        missing_on_disk = sorted(linked_refs - disk_refs)
        unregistered = sorted(disk_refs - linked_refs)
        if missing_on_disk:
            errs.append(f"SKILL.md 表征表存在断链文件: {missing_on_disk}")
        if unregistered:
            errs.append(f"references/ 存在未注册到 SKILL.md 表征表的孤儿文件: {unregistered}")

    for ref in sorted(REFS_DIR.glob("*.md")):
        ref_text = ref.read_text(encoding="utf-8")
        n = len(ref_text.splitlines())
        if not (15 <= n <= 35):
            errs.append(f"{ref.name} 行数越界: {n} (要求 15~35)")
        slots = re.findall(r"^## (\d+)\.\s+\S+", ref_text, flags=re.M)
        if slots != ["1", "2", "3", "4"]:
            errs.append(f"{ref.name} 未严格遵循四槽同构标题 (## 1. ~ ## 4.): 实测 {slots}")

    disk_wfs = {p.name for p in WORKFLOWS_DIR.glob("*.md")} if WORKFLOWS_DIR.exists() else set()
    linked_wfs = set(re.findall(r"\(workflows/([a-zA-Z0-9_-]+\.md)\)", study_raw))
    if disk_wfs != linked_wfs:
        missing_wfs = sorted(linked_wfs - disk_wfs)
        unregistered_wfs = sorted(disk_wfs - linked_wfs)
        if missing_wfs:
            errs.append(f"SKILL.md 流程链接存在断链文件: {missing_wfs}")
        if unregistered_wfs:
            errs.append(f"workflows/ 存在未注册到 SKILL.md 的孤儿文件: {unregistered_wfs}")
    for wf in sorted(WORKFLOWS_DIR.glob("*.md")) if WORKFLOWS_DIR.exists() else []:
        wn = len(wf.read_text(encoding="utf-8").splitlines())
        if not (20 <= wn <= 80):
            errs.append(f"workflows/{wf.name} 行数越界: {wn} (要求 20~80)")

    for req_asset in (PLOT_HELPER, CHECK_SVG, CHECK_NOTES, CHECK_UPDATE, SCRIPTS_DIR / "pyproject.toml", SCRIPTS_DIR / "uv.lock"):
        if not req_asset.exists():
            errs.append(f"缺失 study/scripts 核心运行资产: {req_asset.name}")
    if not SUBMIT_FEEDBACK.exists():
        errs.append(f"缺失 study-feedback/scripts 核心运行资产: {SUBMIT_FEEDBACK.name}")

    if not STUDY_VERSION.exists():
        errs.append("缺失 study/VERSION 版本号文件")
    else:
        study_ver = STUDY_VERSION.read_text(encoding="utf-8").strip()
        if not SEMVER_RE.match(study_ver):
            errs.append(f"study/VERSION 非法 semver 格式: {study_ver!r}")
        elif REPO_ROOT and (REPO_ROOT / "VERSION").exists():
            root_ver = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
            if root_ver != study_ver:
                errs.append(f"仓库根目录 VERSION ({root_ver}) 与 study/VERSION ({study_ver}) 不一致")

    fb_gitignore = FEEDBACK_DIR / ".gitignore"
    if not fb_gitignore.exists() or "local_config.json" not in fb_gitignore.read_text(encoding="utf-8"):
        errs.append("study-feedback/.gitignore 必须包含 local_config.json 隐私隔离项")

    wf_files = sorted(WORKFLOWS_DIR.glob("*.md")) if WORKFLOWS_DIR.exists() else []
    base_dir = REPO_ROOT or STUDY_DIR.parent
    spec_docs = [STUDY_MD, FEEDBACK_MD, *wf_files, *sorted(REFS_DIR.glob("*.md"))]
    for doc in spec_docs:
        raw_doc = doc.read_text(encoding="utf-8")
        prose = strip_code_and_templates(raw_doc)
        rel = doc.relative_to(base_dir)
        if "！" in prose or "!" in prose:
            errs.append(f"{rel} 正文含禁用感叹号")
        for m in re.finditer(r"（([^）]{16,})）", prose):
            errs.append(f"{rel} 含超长圆括号补丁 (>15字): （{m.group(1)[:18]}...）")
        if ext_sk := find_external_skill_mention(raw_doc):
            errs.append(f"{rel} 违规点名外部技能或命令: {ext_sk}")
        if m_tl := COUPLED_TOOL_RE.search(raw_doc):
            errs.append(f"{rel} 违规写死特定宿主私有工具名: {m_tl.group(0)}")

    raw_user = os.environ.get("USERNAME") or os.environ.get("USER") or os.environ.get("LOGNAME") or ""
    username = "" if raw_user.lower() in CI_DEFAULT_USERS else raw_user
    public_files = [
        STUDY_MD,
        STUDY_VERSION,
        FEEDBACK_MD,
        *wf_files,
        *sorted(REFS_DIR.glob("*.md")),
        PLOT_HELPER,
        CHECK_SVG,
        CHECK_NOTES,
        CHECK_UPDATE,
        SCRIPTS_DIR / "pyproject.toml",
        FEEDBACK_DIR / "scripts" / "lint_study.py",
        SUBMIT_FEEDBACK,
        FEEDBACK_DIR / "local_config.example.json",
        STUDY_DIR / ".gitignore",
        FEEDBACK_DIR / ".gitignore",
    ]
    if REPO_ROOT and REPO_ROOT.exists():
        for root_doc in ("README.md", "LICENSE", "CHANGELOG.md", "VERSION", ".gitignore", ".gitattributes"):
            p = REPO_ROOT / root_doc
            if p.exists():
                public_files.append(p)
        gh_dir = REPO_ROOT / ".github"
        if gh_dir.exists():
            public_files.extend(sorted(p for p in gh_dir.rglob("*") if p.is_file()))

    priv_re = re.compile(r"(?:[A-Za-z]:[/\\](?:Users|DESKTOP)|/(?:Users|home)/[a-zA-Z0-9_\u4e00-\u9fa5]+)", re.I)
    for pf in public_files:
        if not pf.exists():
            continue
        raw = pf.read_text(encoding="utf-8")
        if (username and len(username) >= 2 and username in raw) or priv_re.search(raw):
            errs.append(f"公开文件含本地私人路径或用户名残留: {pf.relative_to(base_dir)}")

    return errs


def check_dist_isolation(scan_root: pathlib.Path | None = None) -> list[str]:
    errs: list[str] = []
    targets = [scan_root] if scan_root else ([REPO_ROOT] if REPO_ROOT else [STUDY_DIR, FEEDBACK_DIR])
    base = scan_root or REPO_ROOT or STUDY_DIR.parent
    for root in targets:
        if not root or not root.exists():
            continue
        for p in sorted(root.rglob("*")):
            if ".git" in p.parts:
                continue
            if p.name in {"local_config.json", ".venv", "__pycache__", "evals"} or p.suffix in {".pyc", ".pyo"} or "golden_cases" in p.name:
                errs.append(f"发版目录残留本地私有文件或缓存产物: {p.relative_to(base)}")
    if scan_root or REPO_ROOT:
        repo = scan_root or REPO_ROOT
        for req in ("README.md", "LICENSE", ".gitignore", ".gitattributes"):
            if not (repo / req).exists():
                errs.append(f"开源合仓根目录缺失工程文件: {req}")
    return errs


def smoke_test_plot() -> list[str]:
    with tempfile.TemporaryDirectory() as tmp:
        test_py = pathlib.Path(tmp) / "smoke.py"
        out_svg = pathlib.Path(tmp) / "out.svg"
        out_html = pathlib.Path(tmp) / "out.html"
        out_png = pathlib.Path(tmp) / "out.png"
        test_py.write_text(
            "import contextlib, io, pathlib, numpy as np, plot_helper as ph\n"
            "buf = io.StringIO()\n"
            "with contextlib.redirect_stderr(buf):\n"
            "    fig, axes = ph.new_subplots(1, 2)\n"
            "    assert fig.get_size_inches()[0] >= 8.5\n"
            "    axes[0].plot([0, 1, 2, 3], [1.0, 0.75, 0.4, 0.2])\n"
            "    ph.vec2d(axes[0], (2.0, 1.5), label='v')\n"
            "    assert axes[0].get_xlim()[1] > 2.0 and axes[0].get_ylim()[1] > 1.5\n"
            "    ph.note_box(axes[0], '说明', loc='auto')\n"
            "    ph.label_point(axes[0], (1.0, 0.75), r'点 $P_1$')\n"
            "    ph.heatmap(axes[1], [[1.0, -np.inf], [-0.5, 0.0]])\n"
            f"    s1 = ph.save_svg(fig, {out_svg.as_posix()!r}, html_path={out_html.as_posix()!r}, preview_png={out_png.as_posix()!r})\n"
            "assert '[plot_helper 自检提示]' not in buf.getvalue(), buf.getvalue()\n"
            "assert '<path' in s1 and '<text' not in s1 and len(s1.encode('utf-8')) < 65000\n"
            f"assert '<svg' in pathlib.Path({out_html.as_posix()!r}).read_text(encoding='utf-8')\n"
            f"assert pathlib.Path({out_png.as_posix()!r}).stat().st_size > 1000\n"
            "fig_b, ax_b = ph.new_fig()\n"
            "tt = ax_b.set_title('系数 $a_1$', weight='bold')\n"
            "ph.save_svg(fig_b)\n"
            "assert tt.get_fontweight() == 'normal'\n"
            "try:\n"
            "    fig_u, ax_u = ph.new_fig()\n"
            "    ax_u.text(0.5, 0.5, 'N₂')\n"
            "    ph.save_svg(fig_u)\n"
            "    raise AssertionError('未拦截裸 Unicode 下标')\n"
            "except ValueError:\n"
            "    pass\n"
            "dbuf = io.StringIO()\n"
            "with contextlib.redirect_stderr(dbuf):\n"
            "    fig_d, ax_d = ph.new_fig()\n"
            "    for c in (ph.COLORS['blue'], ph.COLORS['red'], ph.COLORS['green'], ph.COLORS['orange']):\n"
            "        ax_d.plot([0, 1], [0.5, 0.5], color=c)\n"
            "    ax_d.text(0.5, 0.5, '重甲')\n"
            "    ax_d.text(0.51, 0.51, '重乙')\n"
            "    ph.save_svg(fig_d)\n"
            "assert '[plot_helper 自检提示]' in dbuf.getvalue()\n"
            "fig3, ax3 = ph.new_3d_fig()\n"
            "ph.vec3d_drop(ax3, (3, 0, 4), label='k')\n"
            "y0, y1 = ax3.get_ylim3d()\n"
            "assert (y1 - y0) > 1.0\n"
            "s2 = ph.save_svg(fig3)\n"
            "assert '<svg' in s2\n"
            "fig_l, ax_l = ph.new_fig()\n"
            "ax_l.plot([0, 1, 2, 3], [0.2, 0.3, 0.5, 0.9], label='曲线甲')\n"
            "ax_l.legend(loc='upper left')\n"
            "ph.note_box(ax_l, '空角说明', loc='auto')\n"
            "ph.label_point(ax_l, (1.5, 0.4), '关键点')\n"
            "lbuf = io.StringIO()\n"
            "with contextlib.redirect_stderr(lbuf):\n"
            "    ph.save_svg(fig_l)\n"
            "assert '[plot_helper 自检提示]' not in lbuf.getvalue(), lbuf.getvalue()\n"
            "fig_lb, ax_lb = ph.new_fig()\n"
            "ax_lb.plot([0, 1, 2], [0.0, 0.5, 1.0], label='压线图例')\n"
            "ax_lb.legend(loc='center')\n"
            "ax_lb.text(0.5, 0.5, '重叠文字', transform=ax_lb.transAxes, ha='center', va='center')\n"
            "lbbuf = io.StringIO()\n"
            "with contextlib.redirect_stderr(lbbuf):\n"
            "    ph.save_svg(fig_lb)\n"
            "assert '图例框' in lbbuf.getvalue(), lbbuf.getvalue()\n",
            encoding="utf-8",
        )
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["STUDY_NO_UPDATE_CHECK"] = "1"
        if not (SCRIPTS_DIR / ".venv").exists():
            env["UV_PROJECT_ENVIRONMENT"] = str(pathlib.Path(tmp) / "venv")
        try:
            proc = subprocess.run(
                ["uv", "run", "--project", str(SCRIPTS_DIR), str(test_py)],
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except FileNotFoundError:
            return ["未检测到 uv 命令，请先安装 uv: https://docs.astral.sh/uv/"]
        if proc.returncode != 0:
            return [f"plot_helper 冒烟测试失败:\n{proc.stderr or proc.stdout}"]
    return []


def _load_module(mod_name: str, file_path: pathlib.Path):
    import importlib.util

    prev_dont_write = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec = importlib.util.spec_from_file_location(mod_name, file_path)
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.dont_write_bytecode = prev_dont_write


def collect_study_warnings() -> list[str]:
    if not STUDY_MD.exists():
        return []
    head_lines = STUDY_MD.read_text(encoding="utf-8").split("## 产出文档模板")[0].splitlines()
    return [
        f"study/SKILL.md 第 {idx} 行偏长 ({len(line)} 字 > {STUDY_WARN_LINE_CHARS})"
        for idx, line in enumerate(head_lines, start=1)
        if len(line) > STUDY_WARN_LINE_CHARS
    ]


def smoke_test_check_svg() -> list[str]:
    if not CHECK_SVG.exists():
        return []
    mod = _load_module("study_check_svg_test", CHECK_SVG)
    if mod is None:
        return ["无法加载 check_svg.py 进行离线自检"]

    try:
        bad = (
            '<svg viewBox="0 0 600 260"><rect x="0" y="0" width="600" height="260" fill="#f4f6f8"/>'
            '<line x1="200" y1="40" x2="200" y2="220" stroke="#2563EB" stroke-width="3"/>'
            '<text x="200" y="130" text-anchor="middle" font-size="13">箭杆正穿文字</text></svg>'
        )
        assert any("穿过文字" in x for x in mod.check_svg_text(bad))
        masked = (
            '<svg viewBox="0 0 600 260"><rect x="0" y="0" width="600" height="260" fill="#f4f6f8"/>'
            '<line x1="200" y1="40" x2="200" y2="220" stroke="#2563EB" stroke-width="3"/>'
            '<rect x="150" y="114" width="100" height="26" fill="#ffffff"/>'
            '<text x="200" y="130" text-anchor="middle" font-size="13">遮罩保护</text></svg>'
        )
        assert mod.check_svg_text(masked) == []
        offset = (
            '<svg viewBox="0 0 600 260"><rect x="0" y="0" width="600" height="260" fill="#f4f6f8"/>'
            '<line x1="160" y1="40" x2="160" y2="220" stroke="#2563EB" stroke-width="3"/>'
            '<text x="180" y="130" text-anchor="start" font-size="13">错开通道</text></svg>'
        )
        assert mod.check_svg_text(offset) == []
        dirty = (
            '<svg viewBox="0 0 300 120"><text x="80" y="60" font-size="14">甲乙重叠</text>'
            '<text x="90" y="62" font-size="14">乙甲重叠</text>'
            '<text x="295" y="110" font-size="14">超出边界长文本</text></svg>'
        )
        d_issues = mod.check_svg_text(dirty)
        assert len(d_issues) >= 3, d_issues

        no_vb = '<svg width="300" height="120"><rect x="0" y="0" width="300" height="120" fill="#f4f6f8"/><text x="30" y="60">无视框</text></svg>'
        assert any("viewBox" in x for x in mod.check_svg_text(no_vb))

        latex_svg = (
            r'<svg viewBox="0 0 400 160"><rect x="0" y="0" width="400" height="160" fill="#f4f6f8"/>'
            r'<text x="40" y="60" font-size="13">$\alpha_1$ 与 \frac{a}{b}</text></svg>'
        )
        assert any("LaTeX" in x for x in mod.check_svg_text(latex_svg))
        safe_text_svg = (
            r'<svg viewBox="0 0 400 160"><rect x="0" y="0" width="400" height="160" fill="#f4f6f8"/>'
            r'<text x="40" y="60" font-size="13">路径\n示例 售价$100 变量$HOME</text></svg>'
        )
        assert mod.check_svg_text(safe_text_svg) == []

        four_colors = (
            '<svg viewBox="0 0 400 160"><rect x="0" y="0" width="400" height="160" fill="#f4f6f8"/>'
            '<rect x="20" y="20" width="60" height="40" fill="#2563EB"/>'
            '<rect x="100" y="20" width="60" height="40" fill="#DC2626"/>'
            '<rect x="180" y="20" width="60" height="40" fill="#059669"/>'
            '<rect x="260" y="20" width="60" height="40" fill="#7C3AED"/></svg>'
        )
        assert any("主色系" in x for x in mod.check_svg_text(four_colors))
        same_hues = (
            '<svg viewBox="0 0 400 160"><rect x="0" y="0" width="400" height="160" fill="#f4f6f8"/>'
            '<rect x="20" y="20" width="60" height="40" fill="#BFDBFE" stroke="#2563EB"/>'
            '<rect x="100" y="20" width="60" height="40" fill="#FEE2E2" stroke="#DC2626"/>'
            '<rect x="180" y="20" width="60" height="40" fill="#DCFCE7" stroke="#059669"/>'
            '<text x="30" y="100" fill="#334155">中性灰文字</text></svg>'
        )
        assert mod.check_svg_text(same_hues) == []

        with tempfile.TemporaryDirectory() as tmp:
            tdir = pathlib.Path(tmp)
            ok_svg = tdir / "ok.svg"
            bad_svg = tdir / "bad.svg"
            ok_html = tdir / "ok.html"
            bad_html = tdir / "bad.html"
            ok_svg.write_text(
                '<svg style="font-family:sans-serif;" viewBox="0 0 320 120">'
                '<rect x="0" y="0" width="320" height="120" fill="#f4f6f8"/>'
                '<text x="30" y="60" font-size="13">规范框图</text></svg>',
                encoding="utf-8",
            )
            bad_svg.write_text(r'<svg width="200" height="100"><text x="10" y="20">$\alpha$</text></svg>', encoding="utf-8")
            r_ok = subprocess.run(
                [sys.executable, str(CHECK_SVG), str(ok_svg), "--html", str(ok_html)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            assert r_ok.returncode == 0, r_ok.stderr
            h_txt = ok_html.read_text(encoding="utf-8")
            assert "background:transparent" in h_txt and "width:100%" in h_txt and "font-family:sans-serif" in h_txt
            assert h_txt.count("style=") <= 2
            r_bad = subprocess.run(
                [sys.executable, str(CHECK_SVG), str(bad_svg), "--html", str(bad_html)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            assert r_bad.returncode != 0 and not bad_html.exists()
    except AssertionError as err:
        return [f"check_svg 离线断言失败: {err}"]
    except Exception as err:
        return [f"check_svg 离线自检异常: {err}"]
    return []


def smoke_test_check_notes() -> list[str]:
    if not CHECK_NOTES.exists():
        return []
    mod = _load_module("study_check_notes_test", CHECK_NOTES)
    if mod is None:
        return ["无法加载 check_notes.py 进行离线自检"]

    try:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            assets = root / "assets"
            assets.mkdir()
            valid_svg = '<svg viewBox="0 0 100 60"><rect x="0" y="0" width="100" height="60" fill="#f4f6f8"/></svg>'
            (assets / "卡01_示例.svg").write_text(valid_svg, encoding="utf-8")
            (assets / "孤儿图.svg").write_text(valid_svg, encoding="utf-8")
            (root / "00_伴学脉络蓝图.md").write_text(
                "| 顺序 | 主题 | 说明 |\n| :--- | :--- | :--- |\n| 卡 01 | 示例一 | 测 |\n| 卡 02 | 示例二 | 测 |\n",
                encoding="utf-8",
            )
            good_card = root / "卡01_示例.md"
            good_card.write_text(
                "# 卡 01｜示例\n\n算例阶乘 `5!` 与推导 $n! = n(n-1)!$。\n\n"
                "![图注](assets/卡01_示例.svg)\n\n"
                "```html\n<agent-embed src=\"demo.html\"></agent-embed>\n```\n",
                encoding="utf-8",
            )
            errs_good, refs_good = mod.check_note_file(good_card)
            assert errs_good == [] and len(refs_good) == 1, errs_good

            bad_card = root / "卡99_脏稿.md"
            bad_card.write_text(
                '<agent-embed src="bad.html"></agent-embed>\n'
                "![坏图1](D:/abs/bad.svg)\n"
                "![坏图2](assets/不存在.svg)\n"
                r"这里有 $\textcolor{red}{x}$ 与感叹号！" + "\n",
                encoding="utf-8",
            )
            errs_bad, _ = mod.check_note_file(bad_card)
            assert len(errs_bad) >= 5, errs_bad
            bad_card.unlink()

            d_errs, d_warns, d_sum = mod.check_notes_dir(root)
            assert d_errs == [] and d_sum["card_count"] == 1
            assert any("孤儿图" in w for w in d_warns)
            assert any("卡 02" in w for w in d_warns)

            (root / "01_全篇脉络总卡.md").write_text("# 总卡\n", encoding="utf-8")
            _, d_warns_sum, _ = mod.check_notes_dir(root)
            assert not any("卡 02" in w for w in d_warns_sum)
    except AssertionError as err:
        return [f"check_notes 离线断言失败: {err}"]
    except Exception as err:
        return [f"check_notes 离线自检异常: {err}"]
    return []


def smoke_test_submit_feedback() -> list[str]:
    if not SUBMIT_FEEDBACK.exists():
        return []
    mod = _load_module("study_submit_feedback_test", SUBMIT_FEEDBACK)
    if mod is None:
        return ["无法加载 submit_feedback.py 进行离线自检"]

    try:
        payload = mod.build_email_payload(" 测试标题 ", "诊断单正文")
        assert payload == {
            "_subject": "[study-feedback] 测试标题",
            "source": "study-skill",
            "title": "测试标题",
            "report": "诊断单正文",
        }
        assert mod.is_email_response_ok(200, '{"ok": true}') is True
        assert mod.is_email_response_ok(200, '{"ok": false}') is False
        assert mod.is_email_response_ok(500, '{"ok": true}') is False
        assert mod.is_email_response_ok(200, "not json") is False
        cmd = mod.build_gh_issue_cmd(" 标题 ", pathlib.Path("report.md"))
        assert cmd[:5] == ["gh", "issue", "create", "-R", "crrisugi/study-skill"]
        assert "--body-file" in cmd and "report.md" in cmd
    except AssertionError as err:
        return [f"submit_feedback 离线断言失败: {err}"]
    except Exception as err:
        return [f"submit_feedback 离线自检异常: {err}"]
    return []


def smoke_test_update_checker() -> list[str]:
    if not CHECK_UPDATE.exists():
        return []
    mod = _load_module("study_check_update_test", CHECK_UPDATE)
    if mod is None:
        return ["无法加载 check_update.py 进行离线自检"]

    try:
        assert mod.parse_semver("v0.2.0")[:3] == (0, 2, 0)
        assert mod.is_strictly_newer("0.2.1", "0.2.0") is True
        assert mod.is_strictly_newer("0.2.0", "0.2.0") is False
        assert mod.is_strictly_newer("0.2.0", "0.3.0") is False
        assert mod.is_strictly_newer("0.2.0", "0.2.0-rc.1") is True
        assert mod.is_strictly_newer("0.2.0-rc.1", "0.2.0") is False
        assert mod.extract_tag_from_location("https://github.com/crrisugi/study-skill/releases/tag/v0.3.0") == "v0.3.0"
        assert mod.extract_tag_from_location("https://github.com/crrisugi/study-skill/releases") is None

        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            p_dir = root / ".claude" / "plugins" / "cache" / "study"
            p_dir.mkdir(parents=True)
            assert mod.detect_install_channel(p_dir, cwd=root)["channel"] == "plugin-managed"

            proj = root / "proj"
            proj_skill = proj / ".agents" / "skills" / "study"
            proj_skill.mkdir(parents=True)
            (proj / "skills-lock.json").write_text('{"version":2,"skills":{"study":{}}}', encoding="utf-8")
            proj_ch = mod.detect_install_channel(proj_skill, cwd=proj, home_dir=root / "empty_home")
            assert proj_ch["channel"] == "npx-skills" and proj_ch["scope"] == "project"

            home = root / "home"
            (home / ".agents").mkdir(parents=True)
            (home / ".agents" / ".skill-lock.json").write_text('{"version":3,"skills":{"study":{}}}', encoding="utf-8")
            g_skill = home / ".agents" / "skills" / "study"
            g_skill.mkdir(parents=True)
            glob_ch = mod.detect_install_channel(g_skill, cwd=root, home_dir=home)
            assert glob_ch["channel"] == "npx-skills" and glob_ch["scope"] == "global"

            git_repo = root / "study-skill"
            (git_repo / ".git").mkdir(parents=True)
            git_skill = git_repo / "skills" / "study"
            git_skill.mkdir(parents=True)
            assert mod.detect_install_channel(git_skill, cwd=root, home_dir=home)["channel"] == "git-clone"

            man_skill = root / "manual" / "study"
            man_skill.mkdir(parents=True)
            assert mod.detect_install_channel(man_skill, cwd=root, home_dir=home)["channel"] == "manual-copy"
    except AssertionError as err:
        return [f"check_update 离线断言失败: {err}"]
    except Exception as err:
        return [f"check_update 离线自检异常: {err}"]
    return []


def sync_public_skills(dest_repo: pathlib.Path) -> None:
    dst_study = dest_repo / "skills" / "study"
    dst_fb = dest_repo / "skills" / "study-feedback"
    for d in (dst_study / "references", dst_study / "workflows", dst_study / "scripts", dst_fb / "scripts"):
        d.mkdir(parents=True, exist_ok=True)
    for stale in (dst_study / "references").glob("*.md"):
        if not (REFS_DIR / stale.name).exists():
            stale.unlink()
    for stale in (dst_study / "workflows").glob("*.md"):
        if not WORKFLOWS_DIR.exists() or not (WORKFLOWS_DIR / stale.name).exists():
            stale.unlink()
    wf_pairs = [(p, dst_study / "workflows" / p.name) for p in sorted(WORKFLOWS_DIR.glob("*.md"))] if WORKFLOWS_DIR.exists() else []
    pairs = [
        (STUDY_DIR / ".gitignore", dst_study / ".gitignore"),
        (STUDY_MD, dst_study / "SKILL.md"),
        (STUDY_VERSION, dst_study / "VERSION"),
        (STUDY_VERSION, dest_repo / "VERSION"),
        *wf_pairs,
        *[(p, dst_study / "references" / p.name) for p in sorted(REFS_DIR.glob("*.md"))],
        (PLOT_HELPER, dst_study / "scripts" / "plot_helper.py"),
        (CHECK_SVG, dst_study / "scripts" / "check_svg.py"),
        (CHECK_NOTES, dst_study / "scripts" / "check_notes.py"),
        (CHECK_UPDATE, dst_study / "scripts" / "check_update.py"),
        (SCRIPTS_DIR / "pyproject.toml", dst_study / "scripts" / "pyproject.toml"),
        (SCRIPTS_DIR / "uv.lock", dst_study / "scripts" / "uv.lock"),
        (FEEDBACK_DIR / ".gitignore", dst_fb / ".gitignore"),
        (FEEDBACK_MD, dst_fb / "SKILL.md"),
        (FEEDBACK_DIR / "local_config.example.json", dst_fb / "local_config.example.json"),
        (FEEDBACK_DIR / "scripts" / "lint_study.py", dst_fb / "scripts" / "lint_study.py"),
        (SUBMIT_FEEDBACK, dst_fb / "scripts" / "submit_feedback.py"),
    ]
    for src, dst in pairs:
        shutil.copyfile(src, dst)


def write_bundle(out_path: pathlib.Path) -> None:
    parts = [
        f"# 受审全套文件\n\n## study/SKILL.md\n\n{STUDY_MD.read_text(encoding='utf-8')}",
    ]
    if WORKFLOWS_DIR.exists():
        for wf in sorted(WORKFLOWS_DIR.glob("*.md")):
            parts.append(f"\n---\n## workflows/{wf.name}\n\n{wf.read_text(encoding='utf-8')}")
    parts.append(f"\n---\n## study-feedback/SKILL.md\n\n{FEEDBACK_MD.read_text(encoding='utf-8')}")
    for ref in sorted(REFS_DIR.glob("*.md")):
        parts.append(f"\n---\n## references/{ref.name}\n\n{ref.read_text(encoding='utf-8')}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(parts), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", type=pathlib.Path, help="输出合并盲审稿路径")
    ap.add_argument("--dist-check", action="store_true", help="检查发布目录是否零私有配置与零缓存残留")
    ap.add_argument("--sync-to", type=pathlib.Path, help="门禁通过后将纯净公开技能同步至指定开源合仓根目录")
    args = ap.parse_args()
    if args.bundle:
        write_bundle(args.bundle)
        print(f"[OK] 已导出合并受审稿: {args.bundle}")

    errors = (
        check_docs_and_assets()
        + smoke_test_plot()
        + smoke_test_check_svg()
        + smoke_test_check_notes()
        + smoke_test_submit_feedback()
        + smoke_test_update_checker()
    )
    if args.dist_check:
        errors.extend(check_dist_isolation())
    if errors:
        print("[FAIL] 门禁未通过:\n- " + "\n- ".join(errors))
        sys.exit(1)

    if args.sync_to:
        dest = args.sync_to.resolve()
        sync_public_skills(dest)
        print(f"[OK] 已同步纯净双技能至: {dest / 'skills'}")

    if warns := collect_study_warnings():
        print("[WARN] 可选排版提醒:\n- " + "\n- ".join(warns))

    wf_cnt = len(list(WORKFLOWS_DIR.glob("*.md"))) if WORKFLOWS_DIR.exists() else 0
    ver_str = STUDY_VERSION.read_text(encoding="utf-8").strip() if STUDY_VERSION.exists() else "?"
    study_lines = STUDY_MD.read_text(encoding="utf-8").splitlines()
    study_chars = sum(len(line) for line in study_lines)
    print(
        f"[PASS] version=v{ver_str} | study={len(study_lines)}行/{study_chars}字 | "
        f"workflows={wf_cnt}份双向对齐 | "
        f"refs={len(list(REFS_DIR.glob('*.md')))}份四槽双向对齐 | "
        f"study-feedback={len(FEEDBACK_MD.read_text(encoding='utf-8').splitlines())}行 | "
        f"plot_helper={len(PLOT_HELPER.read_text(encoding='utf-8').splitlines())}行 | "
        f"check_svg={len(CHECK_SVG.read_text(encoding='utf-8').splitlines())}行 | "
        f"check_notes={len(CHECK_NOTES.read_text(encoding='utf-8').splitlines())}行 | "
        f"submit_feedback={len(SUBMIT_FEEDBACK.read_text(encoding='utf-8').splitlines())}行 | "
        "文风、纯自包含、文字转曲、隐私零残留、笔记体检与双类绘图冒烟全部通过"
    )


if __name__ == "__main__":
    main()
