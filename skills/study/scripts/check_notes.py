"""伴学落盘笔记与配图完整度体检脚本（纯 Python 标准库，零外部依赖）

用法：
  python check_notes.py "<单张笔记.md路径>"
  python check_notes.py "<笔记目录路径>"
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

_FENCED_CODE_RE = re.compile(r"(?:```.*?```|~~~.*?~~~)", re.S)
_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
_EMBED_TAG_RE = re.compile(r"<agent-embed\b", re.I)
_MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)\n]+)\)")
_COLOR_CODE_RE = re.compile(r"(?:\\textcolor\b|\\color\s*\{|<span\b[^>]*\bcolor\s*:)", re.I)
_ABS_TARGET_RE = re.compile(r"^(?:file:|https?://|[A-Za-z]:[/\\]|/|\\\\)", re.I)
_PLAN_ROW_RE = re.compile(r"^\|\s*卡\s*([0-9]+(?:\.[0-9]+)?)(?![\d.])")
_CARD_FILE_RE = re.compile(r"^卡\s*([0-9]+(?:\.[0-9]+)?)(?:[_\-\s]|$)")


def _strip_code(text: str) -> str:
    no_fence = _FENCED_CODE_RE.sub("", text)
    return _INLINE_CODE_RE.sub("", no_fence)


def _normalize_card_id(raw_id: str) -> str:
    if "." in raw_id:
        main_part, sub_part = raw_id.split(".", 1)
        return f"{main_part.zfill(2)}.{sub_part}"
    return raw_id.zfill(2)


def _extract_image_target(raw_inside: str) -> str:
    s = raw_inside.strip()
    if s.startswith("<") and ">" in s:
        target = s[1 : s.index(">")].strip()
    else:
        m = re.match(r'^(\S+)(?:\s+(?:"[^"]*"|\'[^\']*\'))?$', s)
        target = m.group(1) if m else s
    return target.split("#", 1)[0].split("?", 1)[0].strip()


def check_note_file(md_path: pathlib.Path) -> tuple[list[str], set[pathlib.Path]]:
    errors: list[str] = []
    referenced: set[pathlib.Path] = set()
    try:
        raw = md_path.read_text(encoding="utf-8")
    except OSError as err:
        return [f"无法读取笔记文件 {md_path.name}: {err}"], referenced

    prose = _strip_code(raw)
    name = md_path.name

    if _EMBED_TAG_RE.search(prose):
        errors.append(f"{name} 正文残留 <agent-embed> 标签（落盘笔记须改用相对 Markdown 图片引用）")

    for m in _MD_IMAGE_RE.finditer(prose):
        target = _extract_image_target(m.group(1))
        if not target:
            errors.append(f"{name} 存在空路径图片引用")
            continue
        if re.match(r"^https?://", target, re.I):
            continue
        if _ABS_TARGET_RE.match(target):
            errors.append(f"{name} 图片引用禁止绝对路径或 file:// 链接: {target}")
            continue

        asset_path = (md_path.parent / target).resolve()
        referenced.add(asset_path)
        if not asset_path.is_file() or asset_path.stat().st_size == 0:
            errors.append(f"{name} 引用的配图文件缺失或为空: {target}")
            continue
        if asset_path.suffix.lower() == ".svg":
            try:
                svg_raw = asset_path.read_text(encoding="utf-8")
                if "<svg" not in svg_raw.lower():
                    errors.append(f"{name} 引用的 SVG 缺少 <svg> 根节点: {target}")
                else:
                    ET.fromstring(svg_raw)
            except (OSError, UnicodeDecodeError, ET.ParseError) as err:
                errors.append(f"{name} 引用的 SVG 无法解析 ({target}): {err}")

    if _COLOR_CODE_RE.search(prose):
        errors.append(f"{name} 正文含禁用公式或文字染色代码")

    if "！" in prose:
        errors.append(f"{name} 正文含禁用全角感叹号 '！'")

    return errors, referenced


def _parse_blueprint_cards(blueprint_path: pathlib.Path) -> list[str]:
    planned: list[str] = []
    try:
        lines = blueprint_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return planned
    for line in lines:
        if m := _PLAN_ROW_RE.match(line.strip()):
            cid = _normalize_card_id(m.group(1))
            if cid not in planned:
                planned.append(cid)
    return planned


def check_notes_dir(dir_path: pathlib.Path) -> tuple[list[str], list[str], dict]:
    errors: list[str] = []
    warnings: list[str] = []
    md_files = sorted(p for p in dir_path.glob("*.md") if p.is_file())
    if not md_files:
        return [f"目录中未找到任何 .md 笔记文件: {dir_path}"], warnings, {}

    all_refs: set[pathlib.Path] = set()
    disk_cards: dict[str, pathlib.Path] = {}
    for md in md_files:
        f_errs, f_refs = check_note_file(md)
        errors.extend(f_errs)
        all_refs.update(f_refs)
        if cm := _CARD_FILE_RE.match(md.stem):
            disk_cards[_normalize_card_id(cm.group(1))] = md

    assets_dir = dir_path / "assets"
    orphans: list[pathlib.Path] = []
    if assets_dir.is_dir():
        for svg in sorted(assets_dir.glob("*.svg")):
            if svg.is_file() and svg.resolve() not in all_refs:
                orphans.append(svg)
                warnings.append(f"assets/{svg.name} 未被任何笔记 .md 引用（疑似孤儿图）")

    blueprint = dir_path / "00_伴学脉络蓝图.md"
    summary_card = dir_path / "01_全篇脉络总卡.md"
    has_summary_card = summary_card.is_file()
    planned_ids = _parse_blueprint_cards(blueprint) if blueprint.is_file() else []
    missing_cards: list[str] = []
    if planned_ids and not has_summary_card:
        for cid in planned_ids:
            if cid not in disk_cards:
                missing_cards.append(cid)
                warnings.append(f"蓝图计划卡 卡 {cid} 尚未落盘")

    latest_card = sorted(disk_cards.values(), key=lambda p: p.name)[-1].name if disk_cards else (summary_card.name if has_summary_card else "")
    summary = {
        "md_count": len(md_files),
        "card_count": len(disk_cards),
        "has_summary_card": has_summary_card,
        "latest_card": latest_card,
        "planned_count": len(planned_ids),
        "missing_cards": missing_cards,
        "referenced_asset_count": len(all_refs),
        "orphan_asset_count": len(orphans),
    }
    return errors, warnings, summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="伴学落盘笔记与配图完整度体检工具")
    ap.add_argument("target", type=pathlib.Path, help="待检查的单张笔记 .md 文件或笔记目录路径")
    args = ap.parse_args(argv)
    target = args.target

    if not target.exists():
        print(f"[FAIL] 目标不存在: {target}", file=sys.stderr)
        return 1

    if target.is_file():
        errors, refs = check_note_file(target)
        if errors:
            print("[FAIL] 笔记单卡体检未通过:\n- " + "\n- ".join(errors), file=sys.stderr)
            return 1
        print(f"[PASS] 单卡体检通过: {target.name}（引用配图 {len(refs)} 张）")
        return 0

    if target.is_dir():
        errors, warnings, summary = check_notes_dir(target)
        if warnings:
            print("[WARN] 目录核对提醒:\n- " + "\n- ".join(warnings))
        if errors:
            print("[FAIL] 笔记目录体检未通过:\n- " + "\n- ".join(errors), file=sys.stderr)
            return 1
        latest = summary.get("latest_card") or "无"
        mode_note = "含全篇脉络总卡" if summary.get("has_summary_card") else f"已存卡片 {summary.get('card_count', 0)}/{summary.get('planned_count', 0) or summary.get('card_count', 0)} 张"
        print(
            f"[PASS] 笔记目录体检通过: {target.name} | 共 {summary.get('md_count', 0)} 份文档 | "
            f"{mode_note} | 最新: {latest} | 引用配图 {summary.get('referenced_asset_count', 0)} 张"
        )
        return 0

    print(f"[FAIL] 不支持的目标类型: {target}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
