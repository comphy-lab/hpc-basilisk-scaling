#!/usr/bin/env python3
"""Validation figure: (a) u_drop(t), (b) error vs pts/R, (c) drop-frame sequence."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
from pathlib import Path

import matplotlib

matplotlib.rcParams["font.family"] = "serif"
matplotlib.rcParams["font.serif"] = ["Computer Modern Roman"]
if os.environ.get("MN5_PLOT_NO_LATEX") == "1":
    matplotlib.rcParams["mathtext.fontset"] = "cm"
else:
    matplotlib.rcParams["text.usetex"] = True
    matplotlib.rcParams["text.latex.preamble"] = r"\usepackage{amsmath}"

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap, LogNorm, TwoSlopeNorm
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D
from matplotlib.ticker import LogLocator, NullFormatter

PTS_CMAP = LinearSegmentedColormap.from_list(
    "viridis_readable",
    plt.cm.viridis(np.linspace(0.08, 0.82, 256)),
)
INTERFACE = "#FF00C8"
LABEL_FONT = 22
TICK_FONT = 16
LEGEND_FONT = 14
CBAR_FONT = 16
PANEL_FONT = 20
# Young–Wilson–Goldstein U_drop for equal properties: (2/15) Gamma_T R |∇T|/μ.
U_DROP = (2.0 / 15.0) * 0.066
U_DROP_SIGNED = -U_DROP
TIMING_RE = re.compile(r"#TIMING\b.*\bu=(?P<u>\S+)")
VIEW = 2.05
PTS_LEGEND = (8, 16, 32, 64, 128, 256)


def pts_per_r(level: int) -> int:
    return 2 ** (level - 4)


def load_series(path: Path) -> np.ndarray:
    rows = []
    with path.open() as handle:
        for line in handle:
            if not line.strip() or line.startswith("#") or line.startswith("t "):
                continue
            parts = line.split()
            if len(parts) < 6:
                continue
            try:
                rows.append((float(parts[4]), float(parts[5])))
            except ValueError:
                continue
    return np.asarray(rows, dtype=float)


def load_terminal_u(path: Path) -> float | None:
    last = None
    with path.open() as handle:
        for line in handle:
            match = TIMING_RE.search(line)
            if match:
                last = float(match.group("u"))
    return last


def load_ref(path: Path) -> np.ndarray:
    data = np.loadtxt(path)
    return np.column_stack((data[:, 0], data[:, 1] / data[:, 2]))


def style_axes(ax, labelsize: int = TICK_FONT) -> None:
    ax.tick_params(which="both", direction="out", width=2.4, labelsize=labelsize, pad=6)
    ax.tick_params(which="major", length=9)
    ax.tick_params(which="minor", length=4)
    for spine in ax.spines.values():
        spine.set_linewidth(2.4)


def read_facets(fname: Path) -> list[np.ndarray]:
    segments = []
    pts: list[tuple[float, float]] = []
    with fname.open() as handle:
        for line in handle:
            line = line.strip()
            if not line:
                if len(pts) == 2:
                    segments.append(np.array(pts))
                pts = []
                continue
            x, y = map(float, line.split()[:2])
            pts.append((x, y))
    if len(pts) == 2:
        segments.append(np.array(pts))
    return segments


def read_fields(fname: Path):
    with fname.open() as handle:
        header = handle.readline()
        extra = handle.readline()
    match = re.match(r"#\s*nx\s+(\d+)\s+ny\s+(\d+)", header)
    if not match:
        raise ValueError(f"{fname}: missing nx/ny header")
    nx, ny = int(match.group(1)), int(match.group(2))
    xb = vb = 0.0
    extra_match = re.match(r"# xb\s+(\S+)\s+vb\s+(\S+)", extra)
    if extra_match:
        xb = float(extra_match.group(1))
        vb = float(extra_match.group(2))
    data = np.loadtxt(fname, comments="#")
    cols = [data[:, k].reshape(nx, ny) for k in range(7)]
    return nx, ny, xb, vb, cols


def extract_frame(snapshot: Path, helpers: dict[str, Path], work: Path, ny: int):
    fields_txt = work / f"{snapshot.name}.fields"
    facets_txt = work / f"{snapshot.name}.facets"
    if not fields_txt.exists():
        proc = subprocess.run(
            [str(helpers["get_fields"]), str(snapshot), "-8", "8", "0", "4", str(ny)],
            check=True, capture_output=True, text=True,
        )
        fields_txt.write_text(proc.stdout)
    if not facets_txt.exists():
        proc = subprocess.run(
            [str(helpers["get_facets"]), str(snapshot)],
            check=True, capture_output=True, text=True,
        )
        facets_txt.write_text(proc.stdout)
    return read_fields(fields_txt), read_facets(facets_txt)


def u_ratio_at(series: np.ndarray, tstar: float) -> float:
    if series.size == 0:
        return 1.0
    idx = int(np.argmin(np.abs(series[:, 0] - tstar)))
    return float(series[idx, 1])


def slope_triangle(ax, x0, y0, *, decade=0.28, slope=-2.0, label=r"$2$"):
    x1 = x0 * 10 ** decade
    y1 = y0 * (x1 / x0) ** slope
    ax.plot([x0, x1], [y0, y0], color="0.15", linewidth=1.5, zorder=5)
    ax.plot([x1, x1], [y0, y1], color="0.15", linewidth=1.5, zorder=5)
    ax.plot([x0, x1], [y0, y1], color="0.15", linewidth=1.5, zorder=5)
    ax.text(
        x1 * 1.08, 10 ** (0.5 * (np.log10(y0) + np.log10(y1))),
        label, ha="left", va="center", fontsize=LEGEND_FONT, color="0.15",
    )


def draw_drop(ax, fields, segments, speed_norm, vb_use):
    nx, ny, xb, _vb, cols = fields
    x, y, _f, _d, _sig, ux, uy = cols
    u_rel_full = (ux - vb_use) / U_DROP
    v_rel_full = uy / U_DROP
    x_shift = x - xb
    segs = [seg - np.array([xb, 0.0]) for seg in segments]
    segs_m = [np.column_stack((seg[:, 0], -seg[:, 1])) for seg in segs]
    x1d = x_shift[:, 0]
    y1d = y[0, :]
    field = u_rel_full.T
    dx = float(np.median(np.diff(x1d)))
    dy = float(np.median(np.diff(y1d)))
    xlo, xhi = x1d[0] - dx / 2.0, x1d[-1] + dx / 2.0
    ylo, yhi = max(0.0, y1d[0] - dy / 2.0), y1d[-1] + dy / 2.0

    im = ax.imshow(
        field,
        extent=(xlo, xhi, ylo, yhi),
        origin="lower", interpolation="nearest", cmap="RdBu_r",
        norm=speed_norm, aspect="auto", zorder=1,
    )
    ax.imshow(
        field[::-1, :],
        extent=(xlo, xhi, -yhi, -ylo),
        origin="lower", interpolation="nearest", cmap="RdBu_r",
        norm=speed_norm, aspect="auto", zorder=1,
    )

    ix = np.where((x1d >= -VIEW) & (x1d <= VIEW))[0]
    iy = np.where(y1d <= VIEW)[0]
    skipx = max(1, len(ix) // 18)
    skipy = max(1, len(iy) // 18)
    ixs = ix[::skipx]
    iys = iy[::skipy]
    xs = np.linspace(float(x1d[ixs[0]]), float(x1d[ixs[-1]]), len(ixs))
    ys = np.linspace(float(y1d[iys[0]]), float(y1d[iys[-1]]), len(iys))
    u_win = u_rel_full[np.ix_(ixs, iys)].T
    v_win = v_rel_full[np.ix_(ixs, iys)].T
    ax.streamplot(
        xs, ys, u_win, v_win,
        color="0.55", density=0.55, linewidth=0.65, arrowsize=0.65, zorder=2,
    )
    ax.streamplot(
        xs, -ys[::-1], u_win[::-1, :], -v_win[::-1, :],
        color="0.55", density=0.55, linewidth=0.65, arrowsize=0.65, zorder=2,
    )
    if segs + segs_m:
        ax.add_collection(LineCollection(
            segs + segs_m, colors=INTERFACE, linewidths=2.0, zorder=4,
        ))
    ax.set_aspect("equal")
    ax.set_xlim(-VIEW, VIEW)
    ax.set_ylim(-VIEW, VIEW)
    ax.set_xticks([-2, 0, 2])
    ax.set_yticks([-2, 0, 2])
    style_axes(ax, labelsize=13)
    return im


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--ref", type=Path, required=True)
    parser.add_argument("--snaps", type=Path, required=True)
    parser.add_argument("--helpers", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--ny", type=int, default=180)
    args = parser.parse_args()

    levels = sorted(
        int(p.name[1:])
        for p in args.root.glob("L*")
        if p.is_dir() and (p / "out").is_file()
    )
    times = ("00.500", "01.000", "02.000", "03.000")
    helpers = {
        "get_fields": args.helpers / "get_fields",
        "get_facets": args.helpers / "get_facets",
    }
    work = args.snaps / "ascii"
    work.mkdir(parents=True, exist_ok=True)

    series_l10 = load_series(args.root / "L10" / "out")
    frames = []
    for stamp in times:
        snap = args.snaps / f"snapshot-{stamp}"
        fields, segs = extract_frame(snap, helpers, work, args.ny)
        tstar = float(stamp)
        vb_use = u_ratio_at(series_l10, tstar) * U_DROP_SIGNED
        frames.append((tstar, fields, segs, vb_use))
    speed_norm = TwoSlopeNorm(vmin=-1.0, vcenter=0.0, vmax=1.2)

    pts_list = []
    err_list = []
    for level in levels:
        u_end = load_terminal_u(args.root / f"L{level}" / "out")
        if u_end is None:
            continue
        pts_list.append(pts_per_r(level))
        err_list.append(abs(1.0 - u_end))
    pts_arr = np.array(pts_list, dtype=float)
    err_arr = np.array(err_list, dtype=float)
    fit = pts_arr <= 32
    prefactor = float(np.exp(np.mean(np.log(err_arr[fit] * pts_arr[fit] ** 2))))
    ref = load_ref(args.ref)
    ref_err = np.abs(1.0 - ref[:, 1])

    fig = plt.figure(figsize=(16.4, 9.8))
    fig.set_facecolor("white")
    gs = GridSpec(
        2, 3, figure=fig,
        width_ratios=[1.08, 1.0, 1.0], height_ratios=[1.0, 1.0],
        hspace=0.28, wspace=0.18,
        left=0.07, right=0.90, top=0.94, bottom=0.08,
    )

    ax_vt = fig.add_subplot(gs[0, 0])
    pts_norm = LogNorm(vmin=8, vmax=256)
    for level in levels:
        series = load_series(args.root / f"L{level}" / "out")
        if series.size == 0:
            continue
        mask = series[:, 0] <= 3.0 + 1e-9
        pr = pts_per_r(level)
        ax_vt.plot(
            series[mask, 0], series[mask, 1],
            color=PTS_CMAP(pts_norm(pr)), linewidth=2.4, zorder=2,
        )
    ax_vt.axhline(1.0, color="0.45", linewidth=1.1, linestyle=":", zorder=1)
    ax_vt.set_xlim(0.0, 3.0)
    ax_vt.set_ylim(0.90, 1.002)
    ax_vt.set_xlabel(r"$t/t_0$", fontsize=LABEL_FONT, labelpad=6)
    ax_vt.set_ylabel(r"$u_\mathrm{drop}/U_\mathrm{drop}$", fontsize=LABEL_FONT, labelpad=6)
    ax_vt.set_xticks([0, 1, 2, 3])
    ax_vt.set_yticks([0.90, 0.94, 0.98, 1.00])
    style_axes(ax_vt)
    ax_vt.minorticks_on()
    ax_vt.set_box_aspect(1)
    ax_vt.legend(
        handles=[
            Line2D([0], [0], color=PTS_CMAP(pts_norm(p)), linewidth=2.4,
                   label=rf"${p}$")
            for p in PTS_LEGEND
        ],
        title=r"$\mathrm{pts}/R$",
        loc="lower right", frameon=False, fontsize=12, title_fontsize=12,
        handlelength=1.2, labelspacing=0.18, borderpad=0.15, ncol=2,
        columnspacing=0.9, handletextpad=0.4,
    )
    ax_vt.text(-0.18, 1.03, r"$(a)$", transform=ax_vt.transAxes,
               fontsize=PANEL_FONT, va="bottom")

    ax_err = fig.add_subplot(gs[1, 0])
    x_fit = np.logspace(np.log10(7), np.log10(45), 40)
    ax_err.plot(
        x_fit, prefactor * x_fit ** (-2), linestyle="--",
        linewidth=2.2, color="0.35", zorder=1,
    )
    ax_err.plot(
        ref[:, 0], ref_err, linestyle="None", marker="s", markersize=8,
        markerfacecolor="white", markeredgecolor="k", markeredgewidth=1.3,
        zorder=3,
    )
    ax_err.scatter(
        pts_arr, err_arr, s=78, c=pts_arr, cmap=PTS_CMAP, norm=pts_norm,
        edgecolors="k", linewidths=0.8, zorder=4,
    )
    slope_triangle(ax_err, 7.1, 6.6e-2, decade=0.14, slope=-2.0, label=r"$2$")
    ax_err.legend(
        handles=[
            Line2D([0], [0], linestyle="--", color="0.35", linewidth=2.2,
                   label=r"$N^{-2}$"),
            Line2D([0], [0], linestyle="None", marker="s", markersize=8,
                   markerfacecolor="white", markeredgecolor="k",
                   markeredgewidth=1.3, label=r"basilisk.fr"),
            Line2D([0], [0], linestyle="None", marker="o", markersize=8,
                   markerfacecolor="white", markeredgecolor="k",
                   markeredgewidth=0.8, label=r"this work"),
        ],
        loc="upper right", frameon=False, fontsize=LEGEND_FONT,
        handletextpad=0.4,
    )
    ax_err.set_xscale("log")
    ax_err.set_yscale("log")
    ax_err.set_xlim(6, 320)
    ax_err.set_ylim(2.0e-3, 8.0e-2)
    ax_err.set_xticks([8, 16, 32, 64, 128, 256])
    ax_err.set_xticklabels(["8", "16", "32", "64", "128", "256"])
    ax_err.xaxis.set_minor_locator(LogLocator(base=10, subs=[]))
    ax_err.xaxis.set_minor_formatter(NullFormatter())
    ax_err.set_xlabel(r"$\mathrm{pts}/R$", fontsize=LABEL_FONT, labelpad=6)
    ax_err.set_ylabel(r"relative error", fontsize=LABEL_FONT, labelpad=6)
    style_axes(ax_err)
    ax_err.set_box_aspect(1)
    ax_err.text(-0.18, 1.03, r"$(b)$", transform=ax_err.transAxes,
                fontsize=PANEL_FONT, va="bottom")

    axes_f = [
        fig.add_subplot(gs[0, 1]),
        fig.add_subplot(gs[0, 2]),
        fig.add_subplot(gs[1, 1]),
        fig.add_subplot(gs[1, 2]),
    ]
    im = None
    for i, (ax, (tstar, fields, segs, vb_use)) in enumerate(zip(axes_f, frames)):
        im = draw_drop(ax, fields, segs, speed_norm, vb_use)
        ax.set_title(rf"$t/t_0={tstar:g}$", fontsize=16, pad=4)
        if i >= 2:
            ax.set_xlabel(r"$(x-x_b)/R$", fontsize=15, labelpad=3)
        else:
            ax.tick_params(axis="x", which="both", labelbottom=False)
            plt.setp(ax.get_xticklabels(), visible=False)
        if i % 2 == 0:
            ax.set_ylabel(r"$y/R$", fontsize=15, labelpad=3)
        else:
            ax.tick_params(axis="y", which="both", labelleft=False)
            plt.setp(ax.get_yticklabels(), visible=False)
    axes_f[0].text(-0.22, 1.08, r"$(c)$", transform=axes_f[0].transAxes,
                   fontsize=PANEL_FONT, va="bottom")
    cax = fig.add_axes([0.92, 0.08, 0.016, 0.86])
    cbar = fig.colorbar(im, cax=cax)
    cbar.set_label(
        r"$u_x'/U_{\mathrm{drop}}$",
        fontsize=CBAR_FONT, labelpad=8,
    )
    cbar.set_ticks([-1.0, -0.5, 0.0, 0.5, 1.0])
    cbar.ax.tick_params(labelsize=13, width=1.6, length=5)
    for spine in cbar.ax.spines.values():
        spine.set_linewidth(1.6)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, bbox_inches="tight", dpi=300, pad_inches=0.10)
    plt.close(fig)
    print(f"wrote {args.out}")
    print(f"N^{-2} prefactor={prefactor:.4g}")
    for p, e in zip(pts_arr, err_arr):
        print(f"  pts/R={p:.0f}  err={e:.5f}")


if __name__ == "__main__":
    main()
