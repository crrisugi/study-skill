"""study 伴学绘图底座与高频图元库（通过 uv run --project 调用；日常伴学期间只读不改）

速查接口（未覆盖的新图型，直接用返回的原生 fig, ax 配合 Matplotlib / SciPy 自由绘制）：
- COLORS: dict -> 语义高对比色盘 {'blue', 'green', 'orange', 'red', 'gray'}（单图主色 <= 3 种）
- BWR_CMAP -> 零值纯白对称红蓝双极色盘（蓝负 - 白零 - 红正）
- new_fig(figsize=(6.7, 3.0), **subplot_kw) -> (fig, ax): 白底网格/跨平台黑体/svg文本瘦身画布并去上右边框
- new_subplots(nrows=1, ncols=2, figsize=(6.8, 3.1), **kwargs) -> (fig, axes): 多子图对照画布
- new_3d_fig(figsize=(6.6, 3.3), elev=28, azim=38) -> (fig, ax): 偏开坐标轴防遮挡的三维画布
- vec2d(ax, vec, label="", color=COLORS['blue'], origin=(0,0)): 二维精确数据坐标落点箭头 + 自动扩轴防裁剪
- vec3d_drop(ax, vec, label="", color=COLORS['blue'], origin=(0,0,0)): 三维向量 + 底面竖直虚线直角三角形 + 防退化轴限位
- heatmap(ax, data, mask=None, fmt=".2g", vcenter_zero=True, cmap=None): 热力图 + 屏蔽格(-inf) 45°灰斜纹区分零值
- save_svg(fig, svg_path=None) -> str: 紧凑导出瘦身 .svg（自动建目录），并返回精简内联 <svg> 字符串
"""
from __future__ import annotations
import io
import pathlib
import re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import patches
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
import numpy as np

COLORS = {"blue": "#2563EB", "green": "#059669", "orange": "#D97706", "red": "#DC2626", "gray": "#64748B"}
BWR_CMAP = LinearSegmentedColormap.from_list("study_bwr", [COLORS["blue"], "#FFFFFF", COLORS["red"]])
SEQ_CMAP = LinearSegmentedColormap.from_list("study_seq", ["#FFFFFF", COLORS["blue"]])


def apply_rc() -> None:
    plt.rcParams.update({
        "font.sans-serif": ["PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Source Han Sans CN", "WenQuanYi Micro Hei", "DejaVu Sans", "sans-serif"],
        "mathtext.fontset": "dejavusans",
        "axes.unicode_minus": False,
        "svg.fonttype": "none",
        "font.size": 10,
        "axes.edgecolor": "#94A3B8",
        "grid.color": "#E2E8F0",
        "grid.linestyle": "--",
        "grid.alpha": 0.75,
    })


def _style_2d_ax(ax) -> None:
    if hasattr(ax, "zaxis") or getattr(ax, "name", "") == "polar":
        ax.grid(True)
        return
    for side in ("top", "right"):
        if side in ax.spines:
            ax.spines[side].set_visible(False)
    ax.grid(True)


def new_fig(figsize: tuple[float, float] = (6.7, 3.0), **subplot_kw):
    apply_rc()
    fig, ax = plt.subplots(figsize=figsize, subplot_kw=subplot_kw or None)
    fig.patch.set_facecolor("white")
    _style_2d_ax(ax)
    return fig, ax


def new_subplots(nrows: int = 1, ncols: int = 2, figsize: tuple[float, float] = (6.8, 3.1), **kwargs):
    apply_rc()
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


def vec2d(ax, vec, label: str = "", color: str = COLORS["blue"], origin=(0.0, 0.0)) -> None:
    ox, oy = map(float, origin)
    vx, vy = map(float, vec)
    ex, ey = ox + vx, oy + vy
    pad = 0.18 * max(abs(vx), abs(vy), 1.0)
    ax.plot([min(ox, ex) - pad, max(ox, ex) + pad], [min(oy, ey) - pad, max(oy, ey) + pad], alpha=0.0)
    ax.annotate("", xy=(ex, ey), xytext=(ox, oy), arrowprops=dict(arrowstyle="-|>", color=color, lw=2.1, shrinkA=0, shrinkB=0, mutation_scale=13))
    if label:
        ax.text(ex + 0.05 * (vx if abs(vx) > 1e-6 else pad), ey + 0.05 * (vy if abs(vy) > 1e-6 else pad), label, color=color, weight="bold")


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
        ax.text(ex + 0.05 * (vx or 1.0), ey + 0.05 * (vy or 1.0), ez + 0.06 * (vz or 1.0), label, color=color, weight="bold")


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
    nrows, ncols = arr.shape
    for r in range(nrows):
        for c in range(ncols):
            if mask_arr[r, c]:
                ax.add_patch(patches.Rectangle((c - 0.5, r - 0.5), 1, 1, facecolor="#E2E8F0", edgecolor="#94A3B8", hatch="///", lw=0.8))
                if nrows * ncols <= 36:
                    ax.text(c, r, "-∞" if np.isneginf(arr[r, c]) else "MASK", ha="center", va="center", color="#475569", fontsize=8.5)
            elif nrows * ncols <= 36:
                txt_c = "white" if abs(arr[r, c]) > 0.62 * vmax_abs else "#0F172A"
                ax.text(c, r, format(arr[r, c], fmt), ha="center", va="center", color=txt_c, fontsize=9.5)
    return im


def save_svg(fig, svg_path: str | pathlib.Path | None = None) -> str:
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)
    raw = buf.getvalue()
    if "STIXNonUnicode" in raw or any("\ue000" <= ch <= "\uf8ff" for ch in raw):
        raise ValueError("SVG contains STIXNonUnicode/PUA glyphs (e.g. \\mathcal); use plain letters like V_I instead")
    idx = raw.find("<svg")
    svg_str = raw[idx:].strip() if idx >= 0 else raw.strip()
    svg_str = re.sub(r"<svg\b", '<svg style="width:100%; height:auto; max-height:380px; display:block; margin:0 auto;"', svg_str, count=1)
    if svg_path is not None:
        out = pathlib.Path(svg_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(svg_str + "\n", encoding="utf-8")
    return svg_str
