"""手写 SVG 坐标、规范与遮罩快检及透明底内联网页打包脚本（纯 Python 标准库，零外部依赖）

用法：
  python check_svg.py "<svg或内联html路径>"
  python check_svg.py "<svg路径>" --html "<内联网页路径>"
"""
from __future__ import annotations
import argparse
import colorsys
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

_NUM_RE = re.compile(r"[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?")
_TRANSLATE_RE = re.compile(r"translate\(\s*([^,\s)]+)(?:[\s,]+([^)]+))?\s*\)")
_PATH_TOK_RE = re.compile(r"[MmLlHhVvCcQqZz]|[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?")
_LATEX_CMD_RE = re.compile(
    r"\\(?:frac|sqrt|sum|int|prod|lim|partial|nabla|infty|cdot|times|div|pm|mp|to|rightarrow|leftarrow|"
    r"Rightarrow|leq?|geq?|neq|approx|equiv|propto|notin|in|subseteq|subset|cup|cap|forall|exists|"
    r"mathrm|mathbf|mathcal|mathbb|text|operatorname|hat|bar|vec|tilde|ddot|dot|overline|underline|"
    r"left|right|sin|cos|tan|exp|log|ln|"
    r"alpha|beta|gamma|delta|varepsilon|epsilon|zeta|eta|vartheta|theta|iota|kappa|lambda|mu|nu|xi|"
    r"pi|rho|sigma|tau|upsilon|varphi|phi|chi|psi|omega|"
    r"Gamma|Delta|Theta|Lambda|Xi|Pi|Sigma|Upsilon|Phi|Psi|Omega)\b"
)
_INLINE_LATEX_RE = re.compile(r"(?<!\d)\$(?=[A-Za-z\\{])[^$\n]{1,50}\$")
_NAMED_COLORS = {
    "red": (1.0, 0.0, 0.0),
    "blue": (0.0, 0.0, 1.0),
    "green": (0.0, 0.502, 0.0),
    "orange": (1.0, 0.647, 0.0),
    "purple": (0.502, 0.0, 0.502),
    "yellow": (1.0, 1.0, 0.0),
    "cyan": (0.0, 1.0, 1.0),
    "aqua": (0.0, 1.0, 1.0),
    "magenta": (1.0, 0.0, 1.0),
    "pink": (1.0, 0.753, 0.796),
    "brown": (0.647, 0.165, 0.165),
    "teal": (0.0, 0.502, 0.502),
    "navy": (0.0, 0.0, 0.502),
    "indigo": (0.294, 0.0, 0.510),
    "violet": (0.933, 0.510, 0.933),
    "gold": (1.0, 0.843, 0.0),
    "coral": (1.0, 0.498, 0.314),
    "crimson": (0.863, 0.078, 0.235),
    "maroon": (0.502, 0.0, 0.0),
    "olive": (0.502, 0.502, 0.0),
    "lime": (0.0, 1.0, 0.0),
}


def _local_tag(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _parse_style(el: ET.Element) -> dict[str, str]:
    st: dict[str, str] = {}
    raw = el.attrib.get("style", "")
    for item in raw.split(";"):
        if ":" in item:
            k, v = item.split(":", 1)
            st[k.strip().lower()] = v.strip()
    return st


def _attr(el: ET.Element, style: dict[str, str], name: str, default: str = "") -> str:
    return style.get(name, el.attrib.get(name, default)).strip()


def _num(val: str | None, total: float = 0.0, default: float = 0.0) -> float:
    if not val:
        return default
    s = val.strip()
    if s.endswith("%") and total > 0:
        m = _NUM_RE.match(s[:-1])
        return (float(m.group(0)) / 100.0) * total if m else default
    m = _NUM_RE.match(s)
    return float(m.group(0)) if m else default


def _is_opaque_fill(fill: str, opacity: float, fill_opacity: float) -> bool:
    f = fill.strip().lower()
    if f in {"none", "transparent", "rgba(0,0,0,0)"}:
        return False
    return opacity >= 0.85 and fill_opacity >= 0.85


def _is_dark_color(fill: str) -> bool:
    f = fill.strip().lower()
    if f in {"black", "#000", "#000000"}:
        return True
    if f.startswith("#") and len(f) in {4, 7}:
        hx = f[1:] if len(f) == 7 else "".join(c * 2 for c in f[1:])
        try:
            r, g, b = int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16)
            return (0.299 * r + 0.587 * g + 0.114 * b) < 120
        except ValueError:
            return False
    return False


def _parse_rgb_color(color_str: str) -> tuple[float, float, float] | None:
    c = color_str.strip().lower()
    if not c or c in {"none", "transparent", "currentcolor", "inherit", "black", "white", "gray", "grey", "silver"}:
        return None
    if c.startswith("url("):
        return None
    if c in _NAMED_COLORS:
        return _NAMED_COLORS[c]
    if c.startswith("#"):
        hx = c[1:]
        if len(hx) in {3, 4}:
            if len(hx) == 4 and int(hx[3] * 2, 16) / 255.0 <= 0.05:
                return None
            try:
                return tuple(int(hx[i] * 2, 16) / 255.0 for i in range(3))
            except ValueError:
                return None
        if len(hx) in {6, 8}:
            if len(hx) == 8 and int(hx[6:8], 16) / 255.0 <= 0.05:
                return None
            try:
                return tuple(int(hx[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
            except ValueError:
                return None
        return None
    m = re.match(r"rgba?\(\s*([^)]+)\)", c)
    if m:
        parts = [p.strip() for p in m.group(1).replace("/", ",").split(",")]
        if len(parts) >= 3:
            try:
                if len(parts) >= 4 and float(parts[3]) <= 0.05:
                    return None
                vals: list[float] = []
                for p in parts[:3]:
                    if p.endswith("%"):
                        vals.append(max(0.0, min(1.0, float(p[:-1]) / 100.0)))
                    else:
                        vals.append(max(0.0, min(1.0, float(p) / 255.0)))
                return (vals[0], vals[1], vals[2])
            except ValueError:
                return None
    return None


def _cluster_main_hues(colors: list[str]) -> list[float]:
    hue_clusters: list[float] = []
    for col in colors:
        rgb = _parse_rgb_color(col)
        if rgb is None:
            continue
        if max(rgb) - min(rgb) < 0.18:
            continue
        h, s, v = colorsys.rgb_to_hsv(*rgb)
        if s < 0.14 or v < 0.22:
            continue
        if not any(min(abs(h - ch), 1.0 - abs(h - ch)) < (30.0 / 360.0) for ch in hue_clusters):
            hue_clusters.append(h)
    return hue_clusters


def _est_text_width(text: str, fs: float) -> float:
    w = 0.0
    for ch in text:
        if ord(ch) > 0x2E7F:
            w += 1.0 * fs
        elif ch in "mwMW@":
            w += 0.78 * fs
        elif ch in "ilIjtfr.,:;!| ":
            w += 0.34 * fs
        elif ch.isupper():
            w += 0.68 * fs
        else:
            w += 0.56 * fs
    return w


def _overlap_area(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))


def _seg_intersects_box(p0: tuple[float, float], p1: tuple[float, float], box: tuple[float, float, float, float]) -> bool:
    x0, y0 = p0
    x1, y1 = p1
    bx0, by0, bx1, by1 = box
    dx, dy = x1 - x0, y1 - y0
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x0 - bx0), (dx, bx1 - x0), (-dy, y0 - by0), (dy, by1 - y0)):
        if abs(p) < 1e-9:
            if q < 0:
                return False
        else:
            r = q / p
            if p < 0:
                if r > t1:
                    return False
                if r > t0:
                    t0 = r
            else:
                if r < t0:
                    return False
                if r < t1:
                    t1 = r
    return t0 <= t1


def _parse_path_segments(d: str, tx: float, ty: float) -> tuple[list[tuple[tuple[float, float], tuple[float, float]]], bool, int]:
    tokens = _PATH_TOK_RE.findall(d)
    segs: list[tuple[tuple[float, float], tuple[float, float]]] = []
    i = 0
    cmd = ""
    cx = cy = sx = sy = 0.0
    closed = False
    verts = 0

    def has_num(idx: int) -> bool:
        return idx < len(tokens) and not tokens[idx].isalpha()

    while i < len(tokens):
        if tokens[i].isalpha():
            cmd = tokens[i]
            i += 1
            if cmd in {"Z", "z"}:
                closed = True
                if (cx, cy) != (sx, sy):
                    segs.append(((cx + tx, cy + ty), (sx + tx, sy + ty)))
                cx, cy = sx, sy
                continue
        if not has_num(i):
            break
        if cmd in {"M", "m", "L", "l"}:
            nx, ny = float(tokens[i]), float(tokens[i + 1]) if i + 1 < len(tokens) and not tokens[i + 1].isalpha() else 0.0
            i += 2
            if cmd.islower():
                nx, ny = cx + nx, cy + ny
            if cmd in {"M", "m"}:
                sx, sy = nx, ny
                cmd = "L" if cmd == "M" else "l"
            else:
                segs.append(((cx + tx, cy + ty), (nx + tx, ny + ty)))
            cx, cy = nx, ny
            verts += 1
        elif cmd in {"H", "h"}:
            nx = float(tokens[i]) + (cx if cmd == "h" else 0.0)
            i += 1
            segs.append(((cx + tx, cy + ty), (nx + tx, cy + ty)))
            cx = nx
            verts += 1
        elif cmd in {"V", "v"}:
            ny = float(tokens[i]) + (cy if cmd == "v" else 0.0)
            i += 1
            segs.append(((cx + tx, cy + ty), (cx + tx, ny + ty)))
            cy = ny
            verts += 1
        elif cmd in {"C", "c"} and i + 5 < len(tokens):
            vals = [float(tokens[i + k]) for k in range(6)]
            i += 6
            if cmd == "c":
                p1 = (cx + vals[0], cy + vals[1])
                p2 = (cx + vals[2], cy + vals[3])
                p3 = (cx + vals[4], cy + vals[5])
            else:
                p1, p2, p3 = (vals[0], vals[1]), (vals[2], vals[3]), (vals[4], vals[5])
            prev = (cx, cy)
            for s in range(1, 9):
                t = s / 8.0
                mt = 1.0 - t
                qx = mt**3 * cx + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0]
                qy = mt**3 * cy + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1]
                segs.append(((prev[0] + tx, prev[1] + ty), (qx + tx, qy + ty)))
                prev = (qx, qy)
            cx, cy = p3
            verts += 1
        elif cmd in {"Q", "q"} and i + 3 < len(tokens):
            vals = [float(tokens[i + k]) for k in range(4)]
            i += 4
            if cmd == "q":
                p1, p2 = (cx + vals[0], cy + vals[1]), (cx + vals[2], cy + vals[3])
            else:
                p1, p2 = (vals[0], vals[1]), (vals[2], vals[3])
            prev = (cx, cy)
            for s in range(1, 7):
                t = s / 6.0
                mt = 1.0 - t
                qx = mt**2 * cx + 2 * mt * t * p1[0] + t**2 * p2[0]
                qy = mt**2 * cy + 2 * mt * t * p1[1] + t**2 * p2[1]
                segs.append(((prev[0] + tx, prev[1] + ty), (qx + tx, qy + ty)))
                prev = (qx, qy)
            cx, cy = p2
            verts += 1
        else:
            i += 1
    return segs, closed, verts


def _extract_svg(raw_text: str) -> str:
    m = re.search(r"<svg\b.*?</svg>", raw_text, flags=re.S | re.I)
    return m.group(0) if m else raw_text


def check_svg_text(raw_text: str) -> list[str]:
    svg_src = _extract_svg(raw_text)
    try:
        root = ET.fromstring(svg_src)
    except ET.ParseError as err:
        return [f"SVG XML 解析失败: {err}"]

    issues: list[str] = []
    vb_raw = root.attrib.get("viewBox", "")
    vb_nums = [float(x) for x in _NUM_RE.findall(vb_raw)]
    if len(vb_nums) == 4 and vb_nums[2] > 0 and vb_nums[3] > 0:
        vx, vy, vw, vh = vb_nums
    else:
        issues.append("缺少有效的 4 数值 viewBox 属性（窄屏缩放易裁切）")
        vx, vy = 0.0, 0.0
        vw = _num(root.attrib.get("width"), default=800.0) or 800.0
        vh = _num(root.attrib.get("height"), default=400.0) or 400.0
    vb_area = max(vw * vh, 1.0)

    rects: list[tuple[int, tuple[float, float, float, float], bool, bool]] = []
    lines: list[tuple[int, tuple[float, float], tuple[float, float]]] = []
    texts: list[tuple[int, str, tuple[float, float, float, float]]] = []
    raw_colors: list[str] = []
    z_counter = 0

    def walk(el: ET.Element, tx: float, ty: float, fs: float, anchor: str) -> None:
        nonlocal z_counter
        tag = _local_tag(el.tag)
        if tag in {"defs", "style", "title", "desc", "metadata"}:
            return
        style = _parse_style(el)
        cur_fs = _num(_attr(el, style, "font-size"), default=fs)
        cur_anchor = _attr(el, style, "text-anchor", anchor) or anchor
        tr = el.attrib.get("transform", "")
        cur_tx, cur_ty = tx, ty
        for m in _TRANSLATE_RE.finditer(tr):
            cur_tx += float(m.group(1))
            cur_ty += float(m.group(2)) if m.group(2) is not None else 0.0

        opacity = _num(_attr(el, style, "opacity"), default=1.0)
        if opacity <= 0.05:
            return

        if tag == "rect":
            z_counter += 1
            rx = _num(el.attrib.get("x"), vw, 0.0) + cur_tx
            ry = _num(el.attrib.get("y"), vh, 0.0) + cur_ty
            rw = _num(el.attrib.get("width"), vw, 0.0)
            rh = _num(el.attrib.get("height"), vh, 0.0)
            fill = _attr(el, style, "fill", "black")
            stroke = _attr(el, style, "stroke", "none")
            fop = _num(_attr(el, style, "fill-opacity"), default=1.0)
            opaque = _is_opaque_fill(fill, opacity, fop)
            is_bg = opaque and rw >= 0.85 * vw and rh >= 0.85 * vh and not _is_dark_color(fill)
            if not is_bg:
                if fop > 0.05:
                    raw_colors.append(fill)
                raw_colors.append(stroke)
            rects.append((z_counter, (rx, ry, rx + rw, ry + rh), opaque, is_bg))
            return

        for attr_name in ("fill", "stroke"):
            if val := _attr(el, style, attr_name, ""):
                if attr_name == "fill" and _num(_attr(el, style, "fill-opacity"), default=1.0) <= 0.05:
                    continue
                raw_colors.append(val)

        if tag == "line":
            stroke = _attr(el, style, "stroke", "none").lower()
            if stroke != "none":
                z_counter += 1
                p0 = (_num(el.attrib.get("x1"), vw, 0.0) + cur_tx, _num(el.attrib.get("y1"), vh, 0.0) + cur_ty)
                p1 = (_num(el.attrib.get("x2"), vw, 0.0) + cur_tx, _num(el.attrib.get("y2"), vh, 0.0) + cur_ty)
                lines.append((z_counter, p0, p1))
            return

        if tag == "polyline":
            stroke = _attr(el, style, "stroke", "none").lower()
            if stroke != "none":
                nums = [float(x) for x in _NUM_RE.findall(el.attrib.get("points", ""))]
                pts = [(nums[k] + cur_tx, nums[k + 1] + cur_ty) for k in range(0, len(nums) - 1, 2)]
                z_counter += 1
                for k in range(len(pts) - 1):
                    lines.append((z_counter, pts[k], pts[k + 1]))
            return

        if tag == "path":
            stroke = _attr(el, style, "stroke", "none").lower()
            fill = _attr(el, style, "fill", "black").lower()
            fop = _num(_attr(el, style, "fill-opacity"), default=1.0)
            has_marker = bool(el.attrib.get("marker-end") or el.attrib.get("marker-start"))
            segs, closed, verts = _parse_path_segments(el.attrib.get("d", ""), cur_tx, cur_ty)
            if (stroke != "none" or has_marker) and not (closed and verts >= 3 and _is_opaque_fill(fill, opacity, fop) and not has_marker):
                z_counter += 1
                for p0, p1 in segs:
                    lines.append((z_counter, p0, p1))
            return

        if tag == "text":
            z_counter += 1
            base_x = _num(el.attrib.get("x"), vw, 0.0) + cur_tx
            base_y = _num(el.attrib.get("y"), vh, 0.0) + cur_ty
            tspans = [c for c in el if _local_tag(c.tag) == "tspan"]
            if not tspans:
                content = "".join(el.itertext()).strip()
                if content:
                    w = _est_text_width(content, cur_fs)
                    bx0 = base_x - w / 2 if cur_anchor == "middle" else (base_x - w if cur_anchor == "end" else base_x)
                    texts.append((z_counter, content, (bx0, base_y - 0.82 * cur_fs, bx0 + w, base_y + 0.22 * cur_fs)))
            else:
                cx, cy = base_x, base_y
                line_buf: list[str] = []
                line_x, line_y, line_fs, line_anchor = cx, cy, cur_fs, cur_anchor

                def flush_line() -> None:
                    txt = "".join(line_buf).strip()
                    if txt:
                        w = _est_text_width(txt, line_fs)
                        bx0 = line_x - w / 2 if line_anchor == "middle" else (line_x - w if line_anchor == "end" else line_x)
                        texts.append((z_counter, txt, (bx0, line_y - 0.82 * line_fs, bx0 + w, line_y + 0.22 * line_fs)))
                    line_buf.clear()

                if el.text and el.text.strip():
                    line_buf.append(el.text)
                for ts in tspans:
                    ts_style = _parse_style(ts)
                    ts_fs = _num(_attr(ts, ts_style, "font-size"), default=cur_fs)
                    ts_anchor = _attr(ts, ts_style, "text-anchor", cur_anchor) or cur_anchor
                    for attr_name in ("fill", "stroke"):
                        if val := _attr(ts, ts_style, attr_name, ""):
                            raw_colors.append(val)
                    has_x = "x" in ts.attrib
                    has_y = "y" in ts.attrib
                    dy = _num(ts.attrib.get("dy"), default=0.0) if "dy" in ts.attrib else 0.0
                    dx = _num(ts.attrib.get("dx"), default=0.0) if "dx" in ts.attrib else 0.0
                    new_x = (_num(ts.attrib.get("x"), vw, 0.0) + cur_tx) if has_x else (cx + dx)
                    new_y = (_num(ts.attrib.get("y"), vh, 0.0) + cur_ty) if has_y else (cy + dy)
                    if (has_x or has_y or abs(dy) > 0.1) and line_buf:
                        flush_line()
                    if not line_buf:
                        line_x, line_y, line_fs, line_anchor = new_x, new_y, ts_fs, ts_anchor
                    cx, cy = new_x, new_y
                    piece = "".join(ts.itertext())
                    if piece:
                        line_buf.append(piece)
                    if ts.tail:
                        line_buf.append(ts.tail)
                flush_line()
            return

        for child in el:
            walk(child, cur_tx, cur_ty, cur_fs, cur_anchor)

    walk(root, 0.0, 0.0, 14.0, "start")

    if not any(is_bg for *_, is_bg in rects):
        issues.append("缺少覆盖底部的柔和浅底背景 <rect>（防暗黑模式黑字隐身）")

    hue_clusters = _cluster_main_hues(raw_colors)
    if len(hue_clusters) > 4:
        issues.append(f"整图主色系达 {len(hue_clusters)} 种，超过 4 种上限")

    for _, rb, _, is_bg in rects:
        if is_bg:
            continue
        if rb[0] < vx - 2 or rb[1] < vy - 2 or rb[2] > vx + vw + 2 or rb[3] > vy + vh + 2:
            issues.append(f"矩形框越出 viewBox 边界: ({rb[0]:.0f},{rb[1]:.0f},{rb[2]:.0f},{rb[3]:.0f})")

    for z_t, label, tb in texts:
        short = label[:12]
        if _LATEX_CMD_RE.search(label) or _INLINE_LATEX_RE.search(label):
            issues.append(f"手写 SVG 含未渲染 LaTeX 源码 {short!r}（请改写可读 Unicode 字符或纯文本）")
        if tb[0] < vx - 2 or tb[1] < vy - 2 or tb[2] > vx + vw + 2 or tb[3] > vy + vh + 2:
            issues.append(f"文字 {short!r} 越出 viewBox 边界")

        inner = (tb[0] + 1.0, tb[1] + 1.0, tb[2] - 1.0, tb[3] - 1.0)
        if inner[0] < inner[2] and inner[1] < inner[3]:
            tb_area = max((tb[2] - tb[0]) * (tb[3] - tb[1]), 1.0)
            for z_l, p0, p1 in lines:
                if _seg_intersects_box(p0, p1, inner):
                    masked = any(
                        opaque and z_l < z_r < z_t and (_overlap_area(tb, rb) / tb_area) >= 0.80
                        for z_r, rb, opaque, _ in rects
                    )
                    if not masked:
                        issues.append(f"连线/箭杆穿过文字 {short!r}（未错开坐标或未先垫不透明遮罩 <rect>）")
                        break

    for i in range(len(texts)):
        _, l1, b1 = texts[i]
        s1 = (b1[0] + 1.5, b1[1] + 1.5, b1[2] - 1.5, b1[3] - 1.5)
        if s1[0] >= s1[2] or s1[1] >= s1[3]:
            continue
        for j in range(i + 1, len(texts)):
            _, l2, b2 = texts[j]
            s2 = (b2[0] + 1.5, b2[1] + 1.5, b2[2] - 1.5, b2[3] - 1.5)
            if s2[0] >= s2[2] or s2[1] >= s2[3]:
                continue
            ix = min(s1[2], s2[2]) - max(s1[0], s2[0])
            iy = min(s1[3], s2[3]) - max(s1[1], s2[1])
            if ix > 4.0 and iy > 3.0:
                issues.append(f"文字互相重叠: {l1[:10]!r} 与 {l2[:10]!r}")

    _ = vb_area
    return list(dict.fromkeys(issues))


def normalize_svg_for_embed(svg_src: str) -> str:
    clean = _extract_svg(svg_src).strip()
    target_styles = {
        "width": "100%",
        "height": "auto",
        "max-height": "420px",
        "display": "block",
        "margin": "0 auto",
    }

    def _patch_open_tag(m: re.Match[str]) -> str:
        tag_text = m.group(0)
        style_re = re.compile(r"""(\sstyle\s*=\s*)(["'])(.*?)\2""", flags=re.S | re.I)
        if sm := style_re.search(tag_text):
            existing: dict[str, str] = {}
            for item in sm.group(3).split(";"):
                if ":" in item:
                    k, v = item.split(":", 1)
                    existing[k.strip().lower()] = v.strip()
            existing.update(target_styles)
            merged = "; ".join(f"{k}:{v}" for k, v in existing.items()) + ";"
            return tag_text[: sm.start()] + f'{sm.group(1)}"{merged}"' + tag_text[sm.end() :]
        default_style = "; ".join(f"{k}:{v}" for k, v in target_styles.items()) + ";"
        return re.sub(r"^<svg\b", f'<svg style="{default_style}"', tag_text, count=1, flags=re.I)

    return re.sub(r"<svg\b[^>]*>", _patch_open_tag, clean, count=1, flags=re.S | re.I)


def wrap_html(svg_str: str) -> str:
    return (
        '<!DOCTYPE html><html><head><meta charset="utf-8"></head>'
        '<body style="margin:0;padding:8px;background:transparent;">\n'
        f"{svg_str}\n</body></html>\n"
    )


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="手写 SVG 坐标、规范与遮罩快检及透明底内联网页打包工具")
    ap.add_argument("path", type=pathlib.Path, help="待检查的 .svg 或 .html 文件路径")
    ap.add_argument("--html", type=pathlib.Path, help="过检后自动写入透明底响应式内联网页路径")
    args = ap.parse_args(argv)
    p = args.path
    if not p.exists():
        print(f"文件不存在: {p}", file=sys.stderr)
        sys.exit(1)
    raw = p.read_text(encoding="utf-8")
    issues = check_svg_text(raw)
    if issues:
        print("[FAIL] 手写 SVG 快检发现问题:\n- " + "\n- ".join(issues), file=sys.stderr)
        sys.exit(1)
    if args.html is not None:
        svg_norm = normalize_svg_for_embed(raw)
        args.html.parent.mkdir(parents=True, exist_ok=True)
        args.html.write_text(wrap_html(svg_norm), encoding="utf-8")
        print(f"[OK] 手写 SVG 快检通过并已写入内联网页: {args.html}")
    else:
        print(f"[OK] 手写 SVG 快检通过: {p.name}")


if __name__ == "__main__":
    main()
