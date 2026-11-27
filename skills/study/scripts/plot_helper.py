r"""study 伴学绘图底座与高频图元库（通过 uv run --project 调用；日常伴学期间只读不改）

速查接口（未覆盖的新图型，直接用返回的原生 fig, ax 配合 Matplotlib / SciPy 自由绘制）：
- COLORS: dict -> 语义高对比色盘 {'blue', 'green', 'orange', 'red', 'gray'}（单图主色 <= 3 种）
- BWR_CMAP / SEQ_CMAP -> 红蓝双极色盘 / 浅蓝顺序色盘
- new_fig(figsize=(6.8, 3.2), **subplot_kw) -> (fig, ax): 自适应排版白底网格画布
- new_subplots(nrows=1, ncols=2, figsize=None, **kwargs) -> (fig, axes): 自动宽幅对照画布
- new_3d_fig(figsize=(6.6, 3.3), elev=28, azim=38) -> (fig, ax): 偏开坐标轴的三维画布
- new_diagram(figsize=(7.8, 3.6), xlim=(0, 10), ylim=(0, 4.8)) -> (fig, ax): 无坐标轴浅底公式框图画布
- vec2d(ax, vec, label="", color=COLORS['blue'], origin=(0,0)): 二维箭头 + 自动扩轴
- vec3d_drop(ax, vec, label="", color=COLORS['blue'], origin=(0,0,0)): 三维落影矢量箭头
- draw_box(ax, xy, text, color=COLORS['blue'], size=None, facecolor=None, fontsize=9.5) -> artist: 圆角公式框（size=None自适应，传(w,h)固定对齐）
- flow_arrow(ax, start, end, label="", color=COLORS['gray'], rad=0.0): 连接坐标或draw_box对象并可附白底短标
- heatmap(ax, data, mask=None, fmt=".2g", vcenter_zero=True, cmap=None): 热力图 + 屏蔽格斜纹
- note_box(ax, text, loc="auto", color="#334155"): 自动避开曲线的最空角落浅底说明框
- label_point(ax, xy, text, offset=None, color=COLORS['blue'], dot=True): 16向防压线白底点位标注
- save_svg(fig, svg_path=None, html_path=None, preview_png=None) -> str: 矢量文字转曲导出瘦身SVG
提示：上下标一律用 $...$（勿敲裸上下标如 N₂ 或 10⁻⁸），中文放 $...$ 外，不用 \mathcal 与 \begin{...}（分块阵用矩形分格），含公式无需加粗。
"""
from __future__ import annotations
import atexit, colorsys, importlib.util, io, pathlib, re, sys
import matplotlib
matplotlib.use("Agg")
from matplotlib import cycler, patches
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
import numpy as np

COLORS = {"blue": "#2563EB", "green": "#059669", "orange": "#D97706", "red": "#DC2626", "gray": "#64748B"}
BWR_CMAP = LinearSegmentedColormap.from_list("study_bwr", [COLORS["blue"], "#FFFFFF", COLORS["red"]])
SEQ_CMAP = LinearSegmentedColormap.from_list("study_seq", ["#FFFFFF", COLORS["blue"]])
_BARE_SUBSUP_RE = re.compile(r"[\u00b2\u00b3\u00b9\u2070-\u209f\u1d40-\u1d6a]")
_CORNER_MAP = {
    "upper right": (0.97, 0.96, "right", "top"),
    "upper left": (0.03, 0.96, "left", "top"),
    "lower right": (0.97, 0.04, "right", "bottom"),
    "lower left": (0.03, 0.04, "left", "bottom"),
}
_CAND_OFFSETS = [
    (14, 14), (14, -14), (-14, 14), (-14, -14),
    (0, 18), (0, -18), (18, 0), (-18, 0),
    (26, 22), (26, -22), (-26, 22), (-26, -22),
    (34, 18), (34, -18), (-34, 18), (-34, -18),
]


def apply_rc() -> None:
    plt.rcParams.update({
        "font.sans-serif": ["PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Source Han Sans CN", "WenQuanYi Micro Hei", "DejaVu Sans", "sans-serif"],
        "mathtext.fontset": "dejavusans",
        "axes.unicode_minus": False,
        "svg.fonttype": "path",
        "font.size": 10,
        "axes.titleweight": "normal",
        "axes.titlepad": 8,
        "axes.edgecolor": "#94A3B8",
        "axes.labelcolor": "#1E293B",
        "text.color": "#0F172A",
        "xtick.color": "#94A3B8",
        "ytick.color": "#94A3B8",
        "xtick.labelcolor": "#475569",
        "ytick.labelcolor": "#475569",
        "axes.prop_cycle": cycler(color=[COLORS["blue"], COLORS["red"], COLORS["green"]]),
        "axes.xmargin": 0.06,
        "axes.ymargin": 0.12,
        "grid.color": "#E2E8F0",
        "grid.linestyle": "--",
        "grid.alpha": 0.75,
    })


def _style_2d_ax(ax) -> None:
    if hasattr(ax, "zaxis") or getattr(ax, "name", "") == "polar":
        ax.grid(True)
        return
    [ax.spines[s].set_visible(False) for s in ("top", "right") if s in ax.spines]
    ax.grid(True)


def new_fig(figsize: tuple[float, float] = (6.8, 3.2), **subplot_kw):
    apply_rc()
    fig, ax = plt.subplots(figsize=figsize, layout="constrained", subplot_kw=subplot_kw or None)
    fig.patch.set_facecolor("white")
    _style_2d_ax(ax)
    return fig, ax


def new_subplots(nrows: int = 1, ncols: int = 2, figsize: tuple[float, float] | None = None, **kwargs):
    apply_rc()
    if figsize is None:
        w = 6.8 if ncols == 1 else min(10.2, 4.6 * ncols)
        h = 3.5 if nrows == 1 else min(7.2, 3.1 * nrows)
        figsize = (w, h)
    kwargs.setdefault("layout", "constrained")
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=figsize, **kwargs)
    fig.patch.set_facecolor("white")
    for ax in np.ravel(axes):
        _style_2d_ax(ax)
    return fig, axes


def new_3d_fig(figsize: tuple[float, float] = (6.6, 3.3), elev: float = 28.0, azim: float = 38.0):
    apply_rc()
    fig = plt.figure(figsize=figsize, facecolor="white")
    ax = fig.add_subplot(111, projection="3d")
    ax.view_init(elev=elev, azim=azim)
    ax.xaxis.pane.fill = ax.yaxis.pane.fill = ax.zaxis.pane.fill = False
    return fig, ax


def _soft_tint(color: str, mix: float = 0.90) -> str:
    try:
        rgb = mcolors.to_rgb(color)
    except Exception:
        return "#FFFFFF"
    if max(rgb) - min(rgb) < 0.08:
        return "#FFFFFF"
    tinted = tuple((1.0 - mix) * ch + mix for ch in rgb)
    return mcolors.to_hex(tinted)


def new_diagram(
    figsize: tuple[float, float] = (7.8, 3.6),
    xlim: tuple[float, float] = (0.0, 10.0),
    ylim: tuple[float, float] = (0.0, 4.8),
    facecolor: str = "#F8FAFC",
):
    apply_rc()
    fig, ax = plt.subplots(figsize=figsize, layout="constrained")
    fig.patch.set_facecolor(facecolor)
    ax.set_facecolor(facecolor)
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    ax.axis("off")
    return fig, ax


def draw_box(
    ax,
    xy: tuple[float, float],
    text: str,
    color: str = COLORS["blue"],
    size: tuple[float, float] | None = None,
    facecolor: str | None = None,
    fontsize: float = 9.5,
    text_color: str = "#0F172A",
    lw: float = 1.4,
):
    cx, cy = map(float, xy)
    bg = _soft_tint(color) if facecolor is None else facecolor
    w = "normal" if "$" in text else "bold"
    if size is None:
        t = ax.text(
            cx, cy, text, ha="center", va="center", color=text_color, fontsize=fontsize,
            weight=w, linespacing=1.35, zorder=4,
            bbox=dict(boxstyle="round,pad=0.45,rounding_size=0.18", facecolor=bg, edgecolor=color, lw=lw),
        )
        t._study_box_center = (cx, cy)
        return t
    bw, bh = map(float, size)
    r = min(0.14, 0.18 * min(bw, bh))
    rect = patches.FancyBboxPatch(
        (cx - bw / 2.0, cy - bh / 2.0), bw, bh,
        boxstyle=f"round,pad=0.0,rounding_size={r}",
        facecolor=bg, edgecolor=color, lw=lw, zorder=3,
    )
    ax.add_patch(rect)
    t = ax.text(cx, cy, text, ha="center", va="center", color=text_color, fontsize=fontsize, weight=w, linespacing=1.35, zorder=4)
    t._study_box_patch = rect
    t._study_box_center = (cx, cy)
    return t


def _endpoint_xy(ep) -> tuple[float, float]:
    if hasattr(ep, "_study_box_center"):
        return ep._study_box_center
    if hasattr(ep, "get_position"):
        return tuple(map(float, ep.get_position()))
    return (float(ep[0]), float(ep[1]))


def flow_arrow(
    ax,
    start,
    end,
    label: str = "",
    color: str = COLORS["gray"],
    rad: float = 0.0,
    lw: float = 1.6,
    fontsize: float = 8.6,
):
    p0, p1 = _endpoint_xy(start), _endpoint_xy(end)
    arr = patches.FancyArrowPatch(
        p0, p1, arrowstyle="-|>", mutation_scale=13,
        connectionstyle=f"arc3,rad={rad}", color=color, lw=lw,
        shrinkA=2, shrinkB=2, zorder=2.5,
    )
    ax.add_patch(arr)
    arr._study_flow_endpoints = (start, end, float(rad))
    if label:
        mx = 0.5 * (p0[0] + p1[0]) + 0.5 * rad * (p1[1] - p0[1])
        my = 0.5 * (p0[1] + p1[1]) - 0.5 * rad * (p1[0] - p0[0])
        lbl = ax.text(
            mx, my, label, ha="center", va="center", color=color, fontsize=fontsize,
            weight="normal", linespacing=1.25, zorder=5,
            bbox=dict(boxstyle="round,pad=0.18", facecolor="white", edgecolor="none", alpha=0.92),
        )
        arr._study_flow_label = lbl
    return arr


def vec2d(ax, vec, label: str = "", color: str = COLORS["blue"], origin=(0.0, 0.0)) -> None:
    ox, oy = map(float, origin)
    vx, vy = map(float, vec)
    ex, ey = ox + vx, oy + vy
    pad = 0.18 * max(abs(vx), abs(vy), 1.0)
    ax.plot([min(ox, ex) - pad, max(ox, ex) + pad], [min(oy, ey) - pad, max(oy, ey) + pad], alpha=0.0)
    ax.annotate("", xy=(ex, ey), xytext=(ox, oy), arrowprops=dict(arrowstyle="-|>", color=color, lw=2.1, shrinkA=0, shrinkB=0, mutation_scale=13))
    if label:
        w = "normal" if "$" in label else "bold"
        ax.text(ex + 0.05 * (vx if abs(vx) > 1e-6 else pad), ey + 0.05 * (vy if abs(vy) > 1e-6 else pad), label, color=color, weight=w)


def vec3d_drop(ax, vec, label: str = "", color: str = COLORS["blue"], origin=(0.0, 0.0, 0.0)) -> None:
    ox, oy, oz = map(float, origin)
    vx, vy, vz = map(float, vec)
    ex, ey, ez = ox + vx, oy + vy, oz + vz
    pad = 0.25 * max(abs(vx), abs(vy), abs(vz), 1.0)
    ax.plot([min(ox, ex) - pad * (abs(vx) < 1e-6), max(ox, ex) + pad * (abs(vx) < 1e-6)],
            [min(oy, ey) - pad * (abs(vy) < 1e-6), max(oy, ey) + pad * (abs(vy) < 1e-6)],
            [min(oz, ez) - pad * (abs(vz) < 1e-6), max(oz, ez) + pad * (abs(vz) < 1e-6)], alpha=0.0)
    ax.plot([ox, ex], [oy, ey], [oz, oz], color="#94A3B8", ls="--", lw=1.3)
    ax.plot([ex, ex], [ey, ey], [oz, ez], color=COLORS["gray"], ls=":", lw=1.4)
    horiz = float(np.hypot(vx, vy))
    if horiz > 1e-6 and abs(vz) > 1e-6:
        s = 0.08 * min(horiz, abs(vz))
        ux, uy, uz = -vx / horiz * s, -vy / horiz * s, np.sign(vz) * s
        ax.plot([ex + ux, ex + ux, ex], [ey + uy, ey + uy, ey], [oz, oz + uz, oz + uz], color="#64748B", lw=1.0)
    ax.quiver(ox, oy, oz, vx, vy, vz, color=color, arrow_length_ratio=0.14, lw=2.2)
    if label:
        w = "normal" if "$" in label else "bold"
        ax.text(ex + 0.05 * (vx or 1.0), ey + 0.05 * (vy or 1.0), ez + 0.06 * (vz or 1.0), label, color=color, weight=w)


def heatmap(ax, data, mask=None, fmt: str = ".2g", vcenter_zero: bool = True, cmap=None):
    arr = np.asarray(data, dtype=float)
    auto_mask = ~np.isfinite(arr)
    mask_arr = auto_mask if mask is None else (np.asarray(mask, dtype=bool) | auto_mask)
    safe = np.where(mask_arr, 0.0, arr)
    valid = arr[~mask_arr]
    vmax_abs = float(np.max(np.abs(valid))) if valid.size and np.max(np.abs(valid)) > 0 else 1.0
    if vcenter_zero and valid.size and (np.min(valid) < 0):
        im = ax.imshow(safe, cmap=cmap or BWR_CMAP, norm=TwoSlopeNorm(0.0, vmin=-vmax_abs, vmax=vmax_abs), aspect="equal")
    else:
        im = ax.imshow(safe, cmap=cmap or SEQ_CMAP, vmin=0.0, vmax=vmax_abs, aspect="equal")
    ax.grid(False)
    ax.margins(0.0)
    nrows, ncols = arr.shape
    for r, c in np.ndindex(nrows, ncols):
        if mask_arr[r, c]:
            ax.add_patch(patches.Rectangle((c - 0.5, r - 0.5), 1, 1, facecolor="#E2E8F0", edgecolor="#94A3B8", hatch="///", lw=0.8))
            if nrows * ncols <= 36:
                t = ax.text(c, r, "-∞" if np.isneginf(arr[r, c]) else "MASK", ha="center", va="center", color="#475569", fontsize=8.5)
                t._study_cell_text = True
        elif nrows * ncols <= 36:
            txt_c = "white" if abs(arr[r, c]) > 0.62 * vmax_abs else "#0F172A"
            t = ax.text(c, r, format(arr[r, c], fmt), ha="center", va="center", color=txt_c, fontsize=9.5)
            t._study_cell_text = True
    return im


def _is_visible_artist(art) -> bool:
    if not art.get_visible():
        return False
    a = art.get_alpha()
    return a is None or a > 0


def _sample_lines_display(ax, step_px: float = 3.0) -> np.ndarray:
    pts: list[np.ndarray] = []
    for ln in ax.lines:
        if not _is_visible_artist(ln):
            continue
        xy = np.asarray(ln.get_xydata(), dtype=float)
        if xy.ndim != 2 or xy.shape[0] == 0:
            continue
        dp = ax.transData.transform(xy)
        dp = dp[np.isfinite(dp).all(axis=1)]
        if dp.shape[0] == 0:
            continue
        pts.append(dp)
        for i in range(dp.shape[0] - 1):
            d = float(np.hypot(dp[i + 1, 0] - dp[i, 0], dp[i + 1, 1] - dp[i, 1]))
            if d > step_px:
                n = min(80, int(np.ceil(d / step_px)))
                t = np.linspace(0.0, 1.0, n + 1)[1:-1, None]
                pts.append(dp[i] * (1.0 - t) + dp[i + 1] * t)
    return np.vstack(pts) if pts else np.empty((0, 2))


def _collect_scatter_display(ax) -> np.ndarray:
    pts: list[np.ndarray] = []
    for col in ax.collections:
        if not _is_visible_artist(col) or not hasattr(col, "get_offsets"):
            continue
        offs = np.asarray(col.get_offsets(), dtype=float)
        if offs.ndim != 2 or offs.shape[0] == 0:
            continue
        dp = col.get_offset_transform().transform(offs)
        dp = dp[np.isfinite(dp).all(axis=1)]
        if dp.shape[0]:
            pts.append(dp)
    return np.vstack(pts) if pts else np.empty((0, 2))


def _text_bbox_px(t, renderer, use_patch: bool = True):
    patch = (t.get_bbox_patch() or getattr(t, "_study_box_patch", None)) if use_patch else None
    if patch is not None:
        return patch.get_window_extent(renderer)
    return matplotlib.text.Text.get_window_extent(t, renderer)


def _ray_box_exit_px(origin_px: tuple[float, float], target_px: tuple[float, float], bb, pad_px: float = 3.0) -> tuple[float, float]:
    sx, sy = origin_px
    dx, dy = target_px[0] - sx, target_px[1] - sy
    if abs(dx) < 1e-6 and abs(dy) < 1e-6:
        return origin_px
    bx0, by0, bx1, by1 = bb.x0 - pad_px, bb.y0 - pad_px, bb.x1 + pad_px, bb.y1 + pad_px
    ts: list[float] = []
    if dx > 1e-6:
        ts.append((bx1 - sx) / dx)
    elif dx < -1e-6:
        ts.append((bx0 - sx) / dx)
    if dy > 1e-6:
        ts.append((by1 - sy) / dy)
    elif dy < -1e-6:
        ts.append((by0 - sy) / dy)
    pos_ts = [t for t in ts if t > 0]
    if not pos_ts:
        return origin_px
    t = min(pos_ts)
    if t >= 0.95:
        return origin_px
    return (sx + t * dx, sy + t * dy)


def _resolve_flow_arrows(fig) -> None:
    renderer = fig.canvas.get_renderer()
    for ax in fig.axes:
        if hasattr(ax, "zaxis"):
            continue
        inv = ax.transData.inverted()
        for pt in ax.patches:
            ep = getattr(pt, "_study_flow_endpoints", None)
            if ep is None:
                continue
            start, end, rad = ep
            q0 = tuple(map(float, ax.transData.transform(_endpoint_xy(start))))
            q1 = tuple(map(float, ax.transData.transform(_endpoint_xy(end))))
            ctrl = (0.5 * (q0[0] + q1[0]) + rad * (q1[1] - q0[1]), 0.5 * (q0[1] + q1[1]) - rad * (q1[0] - q0[0]))
            q0_edge = _ray_box_exit_px(q0, ctrl if abs(rad) > 1e-6 else q1, _text_bbox_px(start, renderer, use_patch=True)) if isinstance(start, matplotlib.text.Text) else q0
            q1_edge = _ray_box_exit_px(q1, ctrl if abs(rad) > 1e-6 else q0, _text_bbox_px(end, renderer, use_patch=True)) if isinstance(end, matplotlib.text.Text) else q1
            p0_new = tuple(map(float, inv.transform(q0_edge)))
            p1_new = tuple(map(float, inv.transform(q1_edge)))
            pt.set_positions(p0_new, p1_new)
            if (lbl := getattr(pt, "_study_flow_label", None)) is not None:
                qm = (
                    0.5 * (q0_edge[0] + q1_edge[0]) + 0.5 * rad * (q1_edge[1] - q0_edge[1]),
                    0.5 * (q0_edge[1] + q1_edge[1]) - 0.5 * rad * (q1_edge[0] - q0_edge[0]),
                )
                lbl.set_position(tuple(map(float, inv.transform(qm))))


def _rect_overlap_area(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ix0, iy0 = max(a[0], b[0]), max(a[1], b[1])
    ix1, iy1 = min(a[2], b[2]), min(a[3], b[3])
    return max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)


def _visible_legend_bboxes(ax, renderer) -> list[tuple[float, float, float, float]]:
    leg = ax.get_legend()
    if leg is None or not _is_visible_artist(leg):
        return []
    bb = leg.get_window_extent(renderer)
    if bb.width <= 1.0 or bb.height <= 1.0:
        return []
    return [(float(bb.x0), float(bb.y0), float(bb.x1), float(bb.y1))]


def _resolve_auto_notes(fig) -> None:
    renderer = fig.canvas.get_renderer()
    for ax in fig.axes:
        if hasattr(ax, "zaxis"):
            continue
        notes = [t for t in ax.texts if getattr(t, "_study_auto_note", False) and _is_visible_artist(t)]
        if not notes:
            continue
        line_px = _sample_lines_display(ax, step_px=4.0)
        dot_px = _collect_scatter_display(ax)
        pts_px = np.vstack([p for p in (line_px, dot_px) if p.size]) if (line_px.size or dot_px.size) else np.empty((0, 2))
        ax_bb = ax.bbox
        inv_ax = ax.transAxes.inverted()
        pts_ax = inv_ax.transform(pts_px) if pts_px.size else np.empty((0, 2))
        if pts_ax.size:
            keep = (pts_ax[:, 0] >= -0.08) & (pts_ax[:, 0] <= 1.08) & (pts_ax[:, 1] >= -0.08) & (pts_ax[:, 1] <= 1.08)
            pts_ax = pts_ax[keep]
        fixed_ax_boxes: list[tuple[float, float, float, float]] = []
        for ot in ax.texts:
            if ot in notes or getattr(ot, "_study_cell_text", False) or not ot.get_text().strip() or not _is_visible_artist(ot):
                continue
            bb = _text_bbox_px(ot, renderer, use_patch=True)
            c0, c1 = inv_ax.transform((bb.x0, bb.y0)), inv_ax.transform((bb.x1, bb.y1))
            fixed_ax_boxes.append((float(c0[0]), float(c0[1]), float(c1[0]), float(c1[1])))
        for lx0, ly0, lx1, ly1 in _visible_legend_bboxes(ax, renderer):
            c0, c1 = inv_ax.transform((lx0, ly0)), inv_ax.transform((lx1, ly1))
            fixed_ax_boxes.append((float(c0[0]), float(c0[1]), float(c1[0]), float(c1[1])))
        for nt in notes:
            nbb = _text_bbox_px(nt, renderer, use_patch=True)
            nw = float(nbb.width / max(ax_bb.width, 1.0)) if nbb.width > 1 else 0.28
            nh = float(nbb.height / max(ax_bb.height, 1.0)) if nbb.height > 1 else 0.14
            best_loc, best_score = "upper right", None
            for loc_name, (cx, cy, ha, va) in _CORNER_MAP.items():
                bx0, bx1 = (cx - nw, cx) if ha == "right" else (cx, cx + nw)
                by0, by1 = (cy - nh, cy) if va == "top" else (cy, cy + nh)
                cand = (bx0 - 0.02, by0 - 0.02, bx1 + 0.02, by1 + 0.02)
                t_ov = sum(_rect_overlap_area(cand, fb) for fb in fixed_ax_boxes)
                if pts_ax.size:
                    hits = int(((pts_ax[:, 0] >= cand[0]) & (pts_ax[:, 0] <= cand[2]) & (pts_ax[:, 1] >= cand[1]) & (pts_ax[:, 1] <= cand[3])).sum())
                    dx = np.maximum(0.0, np.maximum(bx0 - pts_ax[:, 0], pts_ax[:, 0] - bx1))
                    dy = np.maximum(0.0, np.maximum(by0 - pts_ax[:, 1], pts_ax[:, 1] - by1))
                    dmin = float(np.min(np.hypot(dx, dy)))
                else:
                    hits, dmin = 0, 1.0
                score = (t_ov > 1e-4, hits, -round(dmin, 4))
                if best_score is None or score < best_score:
                    best_score, best_loc = score, loc_name
            cx, cy, ha, va = _CORNER_MAP[best_loc]
            nt.set_position((cx, cy))
            nt.set_ha(ha)
            nt.set_va(va)
            bx0, bx1 = (cx - nw, cx) if ha == "right" else (cx, cx + nw)
            by0, by1 = (cy - nh, cy) if va == "top" else (cy, cy + nh)
            fixed_ax_boxes.append((bx0, by0, bx1, by1))


def _resolve_auto_annotations(fig) -> None:
    renderer = fig.canvas.get_renderer()
    px_per_pt = float(fig.dpi) / 72.0
    for ax in fig.axes:
        if hasattr(ax, "zaxis"):
            continue
        anns = [t for t in ax.texts if getattr(t, "_study_auto_offset", False) and _is_visible_artist(t)]
        if not anns:
            continue
        ax_bb = ax.bbox
        line_px = _sample_lines_display(ax, step_px=3.0)
        dot_px = _collect_scatter_display(ax)
        fixed_boxes: list[tuple[float, float, float, float]] = []
        for ot in [*ax.texts, ax.title, ax.xaxis.label, ax.yaxis.label]:
            if ot in anns or getattr(ot, "_study_cell_text", False) or not ot.get_text().strip() or not _is_visible_artist(ot):
                continue
            bb = _text_bbox_px(ot, renderer, use_patch=True)
            fixed_boxes.append((float(bb.x0), float(bb.y0), float(bb.x1), float(bb.y1)))
        fixed_boxes.extend(_visible_legend_bboxes(ax, renderer))
        for ann in anns:
            bb = _text_bbox_px(ann, renderer, use_patch=True)
            w, h = max(float(bb.width), 12.0), max(float(bb.height), 10.0)
            px, py = map(float, ax.transData.transform(ann.xy))
            near_line = line_px[np.hypot(line_px[:, 0] - px, line_px[:, 1] - py) > 8.0] if line_px.size else line_px
            near_dot = dot_px[np.hypot(dot_px[:, 0] - px, dot_px[:, 1] - py) > 4.0] if dot_px.size else dot_px
            best_cand, best_score = _CAND_OFFSETS[0], None
            for ox_pt, oy_pt in _CAND_OFFSETS:
                ha = "left" if ox_pt > 2 else ("right" if ox_pt < -2 else "center")
                va = "bottom" if oy_pt > 2 else ("top" if oy_pt < -2 else "center")
                tx, ty = px + ox_pt * px_per_pt, py + oy_pt * px_per_pt
                rx0, rx1 = (tx, tx + w) if ha == "left" else ((tx - w, tx) if ha == "right" else (tx - w / 2, tx + w / 2))
                ry0, ry1 = (ty, ty + h) if va == "bottom" else ((ty - h, ty) if va == "top" else (ty - h / 2, ty + h / 2))
                out_x = max(0.0, (ax_bb.x0 + 2) - rx0) + max(0.0, rx1 - (ax_bb.x1 - 2))
                out_y = max(0.0, (ax_bb.y0 + 2) - ry0) + max(0.0, ry1 - (ax_bb.y1 - 2))
                pad_box = (rx0 - 2.0, ry0 - 2.0, rx1 + 2.0, ry1 + 2.0)
                t_ov = sum(_rect_overlap_area(pad_box, fb) for fb in fixed_boxes)
                l_hits = int(((near_line[:, 0] >= pad_box[0]) & (near_line[:, 0] <= pad_box[2]) & (near_line[:, 1] >= pad_box[1]) & (near_line[:, 1] <= pad_box[3])).sum()) if near_line.size else 0
                d_hits = int(((near_dot[:, 0] >= pad_box[0]) & (near_dot[:, 0] <= pad_box[2]) & (near_dot[:, 1] >= pad_box[1]) & (near_dot[:, 1] <= pad_box[3])).sum()) if near_dot.size else 0
                stem_hits = 0
                if near_line.size:
                    cx, cy = 0.5 * (rx0 + rx1), 0.5 * (ry0 + ry1)
                    ex = min(max(px, rx0), rx1)
                    ey = min(max(py, ry0), ry1)
                    tx_end, ty_end = (ex, ey) if np.hypot(ex - px, ey - py) > 4.0 else (cx, cy)
                    for st in (0.2, 0.35, 0.5, 0.65, 0.8, 0.95):
                        sx, sy = px + st * (tx_end - px), py + st * (ty_end - py)
                        if np.hypot(sx - px, sy - py) > 7.5 and np.any(np.hypot(near_line[:, 0] - sx, near_line[:, 1] - sy) < 4.0):
                            stem_hits += 1
                score = 1e4 * (out_x + out_y) + 500.0 * t_ov + 100.0 * l_hits + 200.0 * d_hits + 20.0 * stem_hits + 0.1 * float(np.hypot(ox_pt, oy_pt))
                if best_score is None or score < best_score:
                    best_score, best_cand = score, (ox_pt, oy_pt, ha, va, rx0, ry0, rx1, ry1)
            ox_pt, oy_pt, ha, va, rx0, ry0, rx1, ry1 = best_cand
            ann.set_position((ox_pt, oy_pt))
            ann.set_ha(ha)
            ann.set_va(va)
            fixed_boxes.append((rx0, ry0, rx1, ry1))


def note_box(ax, text: str, loc: str = "auto", color: str = "#334155"):
    if loc != "auto" and loc not in _CORNER_MAP:
        raise ValueError(f"Unsupported loc={loc!r}; choose 'auto' or one of {tuple(_CORNER_MAP)}")
    cx, cy, ha, va = _CORNER_MAP["upper right" if loc == "auto" else loc]
    t = ax.text(
        cx, cy, text, transform=ax.transAxes, ha=ha, va=va, color=color, fontsize=8.8, zorder=6,
        bbox=dict(boxstyle="round,pad=0.35", facecolor="#F8FAFC", edgecolor="#CBD5E1", lw=0.9, alpha=0.93),
    )
    if loc == "auto":
        t._study_auto_note = True
        if ax.figure is not None:
            ax.figure.canvas.draw()
            _resolve_auto_notes(ax.figure)
    return t


def label_point(ax, xy, text: str, offset: tuple[float, float] | None = None, color: str = COLORS["blue"], dot: bool = True):
    x, y = float(xy[0]), float(xy[1])
    if dot:
        ax.scatter([x], [y], s=36, color=color, edgecolors="white", linewidths=1.1, zorder=5)
    init_off = (14.0, 14.0) if offset is None else (float(offset[0]), float(offset[1]))
    ha = "left" if init_off[0] > 2 else ("right" if init_off[0] < -2 else "center")
    va = "bottom" if init_off[1] > 2 else ("top" if init_off[1] < -2 else "center")
    ann = ax.annotate(
        text, xy=(x, y), xytext=init_off, textcoords="offset points", ha=ha, va=va, color=color, fontsize=9.0, zorder=7,
        bbox=dict(boxstyle="round,pad=0.22", facecolor="white", edgecolor="none", alpha=0.88),
        arrowprops=dict(arrowstyle="-", color=color, lw=1.0, alpha=0.75, shrinkA=2, shrinkB=4),
    )
    if offset is None:
        ann._study_auto_offset = True
    return ann


def _audit_figure(fig) -> list[str]:
    issues: list[str] = []
    renderer = fig.canvas.get_renderer()
    fig_bb = fig.bbox
    hue_clusters: list[float] = []

    def add_color(c) -> None:
        try:
            rgb = mcolors.to_rgb(c)
        except Exception:
            return
        if max(rgb) - min(rgb) < 0.12:
            return
        h, s, v = colorsys.rgb_to_hsv(*rgb)
        if s < 0.14 or v < 0.22:
            return
        if not any(min(abs(h - ch), 1.0 - abs(h - ch)) < (25.0 / 360.0) for ch in hue_clusters):
            hue_clusters.append(h)

    for idx, ax in enumerate(fig.axes, start=1):
        tag = f"子图{idx}" if len(fig.axes) > 1 else "图内"
        for ln in ax.lines:
            if _is_visible_artist(ln):
                add_color(ln.get_color())
        for col in ax.collections:
            if not _is_visible_artist(col):
                continue
            for getter in ("get_facecolor", "get_edgecolor"):
                if hasattr(col, getter):
                    for col_rgba in getattr(col, getter)():
                        if len(col_rgba) < 4 or col_rgba[3] > 0:
                            add_color(col_rgba[:3])
        for pt in ax.patches:
            if not _is_visible_artist(pt):
                continue
            for getter in ("get_edgecolor", "get_facecolor"):
                if hasattr(pt, getter):
                    col_rgba = getattr(pt, getter)()
                    if len(col_rgba) < 4 or col_rgba[3] > 0.05:
                        add_color(col_rgba[:3])
        if hasattr(ax, "zaxis"):
            continue

        ax_bb = ax.bbox
        in_texts = [t for t in ax.texts if not getattr(t, "_study_cell_text", False) and t.get_text().strip() and _is_visible_artist(t)]
        for t in in_texts:
            if (t_bp := t.get_bbox_patch()) is not None and _is_visible_artist(t_bp):
                for getter in ("get_edgecolor", "get_facecolor"):
                    col_rgba = getattr(t_bp, getter)()
                    if len(col_rgba) < 4 or col_rgba[3] > 0.05:
                        add_color(col_rgba[:3])
        all_texts = [*in_texts, *[t for t in (ax.title, ax.xaxis.label, ax.yaxis.label) if t.get_text().strip() and _is_visible_artist(t)]]
        t_boxes = [(t, _text_bbox_px(t, renderer, use_patch=True)) for t in all_texts]
        for i in range(len(t_boxes)):
            t1, b1 = t_boxes[i]
            s1 = (b1.x0 + 1.5, b1.y0 + 1.5, b1.x1 - 1.5, b1.y1 - 1.5)
            if s1[0] >= s1[2] or s1[1] >= s1[3]:
                continue
            for j in range(i + 1, len(t_boxes)):
                t2, b2 = t_boxes[j]
                s2 = (b2.x0 + 1.5, b2.y0 + 1.5, b2.x1 - 1.5, b2.y1 - 1.5)
                if s2[0] < s2[2] and s2[1] < s2[3] and _rect_overlap_area(s1, s2) > 4.0:
                    issues.append(f"{tag}文字重叠：{t1.get_text().splitlines()[0][:10]!r} 与 {t2.get_text().splitlines()[0][:10]!r}")

        line_px = _sample_lines_display(ax, step_px=3.0)
        for t in in_texts:
            tb = _text_bbox_px(t, renderer, use_patch=False)
            if line_px.size and tb.width > 4 and tb.height > 4:
                pts = line_px
                if hasattr(t, "xy") and getattr(t, "xycoords", "data") == "data":
                    ax_x, ax_y = ax.transData.transform(t.xy)
                    pts = pts[np.hypot(pts[:, 0] - ax_x, pts[:, 1] - ax_y) > 8.0]
                hits = int(((pts[:, 0] >= tb.x0 + 2.0) & (pts[:, 0] <= tb.x1 - 2.0) & (pts[:, 1] >= tb.y0 + 2.0) & (pts[:, 1] <= tb.y1 - 2.0)).sum())
                if hits >= 2:
                    issues.append(f"{tag}文字 {t.get_text().splitlines()[0][:12]!r} 压到曲线")
            bb = _text_bbox_px(t, renderer, use_patch=True)
            if (bp := getattr(t, "_study_box_patch", None)) is not None:
                pbb = bp.get_window_extent(renderer)
                if tb.x0 < pbb.x0 - 1.5 or tb.x1 > pbb.x1 + 1.5 or tb.y0 < pbb.y0 - 1.5 or tb.y1 > pbb.y1 + 1.5:
                    issues.append(f"{tag}文字 {t.get_text().splitlines()[0][:12]!r} 撑出固定框体")
            area = max(float(bb.width * bb.height), 1.0)
            in_ax = _rect_overlap_area((bb.x0, bb.y0, bb.x1, bb.y1), (ax_bb.x0, ax_bb.y0, ax_bb.x1, ax_bb.y1))
            if in_ax / area < 0.75:
                issues.append(f"{tag}文字 {t.get_text().splitlines()[0][:12]!r} 超出子图边界")

        for t, bb in t_boxes:
            if bb.x0 < fig_bb.x0 - 4 or bb.x1 > fig_bb.x1 + 4 or bb.y0 < fig_bb.y0 - 4 or bb.y1 > fig_bb.y1 + 4:
                issues.append(f"{tag}文字 {t.get_text().splitlines()[0][:12]!r} 超出画布边框")

        for lbb in _visible_legend_bboxes(ax, renderer):
            ls = (lbb[0] + 1.5, lbb[1] + 1.5, lbb[2] - 1.5, lbb[3] - 1.5)
            if ls[0] < ls[2] and ls[1] < ls[3]:
                for t, bb in t_boxes:
                    ts = (bb.x0 + 1.5, bb.y0 + 1.5, bb.x1 - 1.5, bb.y1 - 1.5)
                    if ts[0] < ts[2] and ts[1] < ts[3] and _rect_overlap_area(ls, ts) > 4.0:
                        issues.append(f"{tag}图例框与文字重叠：{t.get_text().splitlines()[0][:10]!r}")
            if line_px.size:
                l_hits = int(((line_px[:, 0] >= lbb[0] + 2.0) & (line_px[:, 0] <= lbb[2] - 2.0) & (line_px[:, 1] >= lbb[1] + 2.0) & (line_px[:, 1] <= lbb[3] - 2.0)).sum())
                if l_hits >= 2:
                    issues.append(f"{tag}图例框压到曲线")
            if lbb[0] < fig_bb.x0 - 4 or lbb[1] < fig_bb.y0 - 4 or lbb[2] > fig_bb.x1 + 4 or lbb[3] > fig_bb.y1 + 4:
                issues.append(f"{tag}图例框超出画布边框")

        dot_px = _collect_scatter_display(ax)
        if dot_px.shape[0] >= 2:
            dedup: list[np.ndarray] = []
            for p in dot_px:
                if not any(float(np.hypot(p[0] - q[0], p[1] - q[1])) < 1.5 for q in dedup):
                    dedup.append(p)
            if 2 <= len(dedup) <= 25:
                min_d = min(float(np.hypot(dedup[i][0] - dedup[j][0], dedup[i][1] - dedup[j][1])) for i in range(len(dedup)) for j in range(i + 1, len(dedup)))
                if min_d < 6.0:
                    issues.append(f"{tag}散点间距过近（{min_d:.1f}px < 6px）可能挤叠")

    if len(hue_clusters) > 3:
        issues.append(f"整图主色达 {len(hue_clusters)} 种，超过 3 种上限")
    return list(dict.fromkeys(issues))


_CACHED_SOURCE_REF_RE: re.Pattern[str] | None | bool = False


def _load_source_ref_re() -> re.Pattern[str] | None:
    global _CACHED_SOURCE_REF_RE
    if _CACHED_SOURCE_REF_RE is not False:
        return _CACHED_SOURCE_REF_RE
    chk = pathlib.Path(__file__).with_name("check_svg.py")
    if not chk.exists():
        _CACHED_SOURCE_REF_RE = None
        return None
    prev_dont_write = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec = importlib.util.spec_from_file_location("_study_check_svg_ref", chk)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _CACHED_SOURCE_REF_RE = getattr(mod, "_SOURCE_REF_RE", None)
            return _CACHED_SOURCE_REF_RE
    except Exception:
        pass
    finally:
        sys.dont_write_bytecode = prev_dont_write
    _CACHED_SOURCE_REF_RE = None
    return None


def _check_texts_and_sanitize(fig) -> None:
    src_ref_re = _load_source_ref_re()
    for t in fig.findobj(matplotlib.text.Text):
        txt = t.get_text()
        if not txt:
            continue
        for m_math in re.finditer(r"\$([^$]*)\$", txt):
            inner = m_math.group(1)
            if re.search(r"\\begin\s*\{", inner):
                plt.close(fig)
                raise ValueError("Matplotlib mathtext 不支持 \\begin{...} 环境，分块矩阵或分段式请改用矩形框分格或分行 $...$ 绘制")
            if re.search(r"[\u4e00-\u9fff]", inner):
                plt.close(fig)
                raise ValueError(f"$...$ 内含中文 {inner!r} 会变缺字方块，请将中文移到 $...$ 外面")
        if src_ref_re is not None and (m_ref := src_ref_re.search(txt)):
            plt.close(fig)
            raise ValueError(f"图内文字夹带原件式号或章节索引 {m_ref.group(0)!r}，请改写算式、符号或人话说明")
        plain = re.sub(r"\$[^$]*\$", "", txt)
        if m := _BARE_SUBSUP_RE.search(plain):
            plt.close(fig)
            raise ValueError(f"图内含裸 Unicode 上下标 {m.group(0)!r}，请改用 $...$ 公式写法")
        w = t.get_fontweight()
        is_bold = (isinstance(w, int) and w >= 600) or (isinstance(w, str) and w.lower() in {"bold", "semibold", "heavy", "demibold", "black"})
        if "$" in txt and is_bold:
            t.set_fontweight("normal")


def save_svg(fig, svg_path: str | pathlib.Path | None = None, html_path: str | pathlib.Path | None = None, preview_png: str | pathlib.Path | None = None) -> str:
    _check_texts_and_sanitize(fig)
    fig.canvas.draw()
    _resolve_flow_arrows(fig)
    _resolve_auto_notes(fig)
    _resolve_auto_annotations(fig)
    fig.canvas.draw()

    audit_issues = _audit_figure(fig)
    if audit_issues:
        print("[plot_helper 自检提示] " + "；".join(audit_issues), file=sys.stderr)

    if preview_png is not None:
        png_out = pathlib.Path(preview_png)
        png_out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(png_out, format="png", dpi=150, bbox_inches="tight", pad_inches=0.08)

    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)
    raw = buf.getvalue()
    if "STIXNonUnicode" in raw or any("\ue000" <= ch <= "\uf8ff" for ch in raw):
        raise ValueError("SVG contains STIXNonUnicode/PUA glyphs (e.g. \\mathcal); use plain letters like V_I instead")
    idx = raw.find("<svg")
    svg_str = raw[idx:].strip() if idx >= 0 else raw.strip()
    svg_str = re.sub(r"<metadata>.*?</metadata>", "", svg_str, flags=re.S)
    svg_str = re.sub(r"<!--.*?-->", "", svg_str, flags=re.S)
    svg_str = "\n".join(line.lstrip() for line in svg_str.splitlines() if line.strip())
    svg_str = re.sub(r"<svg\b", '<svg style="width:100%; height:auto; max-height:420px; display:block; margin:0 auto;"', svg_str, count=1)
    if svg_path is not None:
        out = pathlib.Path(svg_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(svg_str + "\n", encoding="utf-8")
    if html_path is not None:
        h_out = pathlib.Path(html_path)
        h_out.parent.mkdir(parents=True, exist_ok=True)
        html_str = (
            '<!DOCTYPE html><html><head><meta charset="utf-8"></head>'
            '<body style="margin:0;padding:8px;background:transparent;">\n'
            f"{svg_str}\n</body></html>\n"
        )
        h_out.write_text(html_str, encoding="utf-8")
    return svg_str


def _notify_update() -> None:
    try:
        import check_update
        check_update.maybe_notify(pathlib.Path(__file__).resolve().parents[1])
    except Exception:
        pass


atexit.register(_notify_update)
