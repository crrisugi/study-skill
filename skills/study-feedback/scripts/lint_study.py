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
FEEDBACK_MD = FEEDBACK_DIR / "SKILL.md"
REFS_DIR = STUDY_DIR / "references"
SCRIPTS_DIR = STUDY_DIR / "scripts"
PLOT_HELPER = SCRIPTS_DIR / "plot_helper.py"

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
    if len(study_lines) > 170:
        errs.append(f"study/SKILL.md 行数超限: {len(study_lines)} > 170")

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

    for req_asset in (PLOT_HELPER, SCRIPTS_DIR / "pyproject.toml", SCRIPTS_DIR / "uv.lock"):
        if not req_asset.exists():
            errs.append(f"缺失 study/scripts 核心运行资产: {req_asset.name}")

    fb_gitignore = FEEDBACK_DIR / ".gitignore"
    if not fb_gitignore.exists() or "local_config.json" not in fb_gitignore.read_text(encoding="utf-8"):
        errs.append("study-feedback/.gitignore 必须包含 local_config.json 隐私隔离项")

    if PLOT_HELPER.exists():
        pn = len(PLOT_HELPER.read_text(encoding="utf-8").splitlines())
        if pn > 150:
            errs.append(f"plot_helper.py 行数超限: {pn} > 150")

    base_dir = REPO_ROOT or STUDY_DIR.parent
    spec_docs = [STUDY_MD, FEEDBACK_MD, *sorted(REFS_DIR.glob("*.md"))]
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
        FEEDBACK_MD,
        *sorted(REFS_DIR.glob("*.md")),
        PLOT_HELPER,
        SCRIPTS_DIR / "pyproject.toml",
        FEEDBACK_DIR / "scripts" / "lint_study.py",
        FEEDBACK_DIR / "local_config.example.json",
        STUDY_DIR / ".gitignore",
        FEEDBACK_DIR / ".gitignore",
    ]
    if REPO_ROOT and REPO_ROOT.exists():
        for root_doc in ("README.md", "LICENSE", ".gitignore", ".gitattributes"):
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
        test_py.write_text(
            "import numpy as np, plot_helper as ph\n"
            "fig, axes = ph.new_subplots(1, 2)\n"
            "ph.vec2d(axes[0], (2.0, 1.5), label='v')\n"
            "assert axes[0].get_xlim()[1] > 2.0 and axes[0].get_ylim()[1] > 1.5\n"
            "ph.heatmap(axes[1], [[1.0, -np.inf], [-0.5, 0.0]])\n"
            f"s1 = ph.save_svg(fig, {out_svg.as_posix()!r})\n"
            "fig3, ax3 = ph.new_3d_fig()\n"
            "ph.vec3d_drop(ax3, (3, 0, 4), label='k')\n"
            "y0, y1 = ax3.get_ylim3d()\n"
            "assert (y1 - y0) > 1.0\n"
            "s2 = ph.save_svg(fig3)\n"
            "assert '<text' in s1 and len(s1.encode('utf-8')) < 25000 and '<svg' in s2\n",
            encoding="utf-8",
        )
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
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


def sync_public_skills(dest_repo: pathlib.Path) -> None:
    dst_study = dest_repo / "skills" / "study"
    dst_fb = dest_repo / "skills" / "study-feedback"
    for d in (dst_study / "references", dst_study / "scripts", dst_fb / "scripts"):
        d.mkdir(parents=True, exist_ok=True)
    for stale in (dst_study / "references").glob("*.md"):
        if not (REFS_DIR / stale.name).exists():
            stale.unlink()
    pairs = [
        (STUDY_DIR / ".gitignore", dst_study / ".gitignore"),
        (STUDY_MD, dst_study / "SKILL.md"),
        *[(p, dst_study / "references" / p.name) for p in sorted(REFS_DIR.glob("*.md"))],
        (PLOT_HELPER, dst_study / "scripts" / "plot_helper.py"),
        (SCRIPTS_DIR / "pyproject.toml", dst_study / "scripts" / "pyproject.toml"),
        (SCRIPTS_DIR / "uv.lock", dst_study / "scripts" / "uv.lock"),
        (FEEDBACK_DIR / ".gitignore", dst_fb / ".gitignore"),
        (FEEDBACK_MD, dst_fb / "SKILL.md"),
        (FEEDBACK_DIR / "local_config.example.json", dst_fb / "local_config.example.json"),
        (FEEDBACK_DIR / "scripts" / "lint_study.py", dst_fb / "scripts" / "lint_study.py"),
    ]
    for src, dst in pairs:
        shutil.copyfile(src, dst)


def write_bundle(out_path: pathlib.Path) -> None:
    parts = [
        f"# 受审全套文件\n\n## study/SKILL.md\n\n{STUDY_MD.read_text(encoding='utf-8')}",
        f"\n---\n## study-feedback/SKILL.md\n\n{FEEDBACK_MD.read_text(encoding='utf-8')}",
    ]
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

    errors = check_docs_and_assets() + smoke_test_plot()
    if args.dist_check:
        errors.extend(check_dist_isolation())
    if errors:
        print("[FAIL] 门禁未通过:\n- " + "\n- ".join(errors))
        sys.exit(1)

    if args.sync_to:
        dest = args.sync_to.resolve()
        sync_public_skills(dest)
        print(f"[OK] 已同步纯净双技能至: {dest / 'skills'}")

    print(
        f"[PASS] study={len(STUDY_MD.read_text(encoding='utf-8').splitlines())}行 | "
        f"refs={len(list(REFS_DIR.glob('*.md')))}份四槽双向对齐 | "
        f"study-feedback={len(FEEDBACK_MD.read_text(encoding='utf-8').splitlines())}行 | "
        f"plot_helper={len(PLOT_HELPER.read_text(encoding='utf-8').splitlines())}行 | "
        "文风、纯自包含、跨平台字体、隐私零残留与绘图冒烟全部通过"
    )


if __name__ == "__main__":
    main()
