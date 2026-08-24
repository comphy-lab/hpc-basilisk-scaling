#!/usr/bin/env python3
"""Wall time per iteration vs MPI ranks for uniform axi Marangoni."""

from __future__ import annotations

import argparse
import csv
import os
import re
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
from matplotlib.colors import LinearSegmentedColormap, LogNorm
from matplotlib.lines import Line2D
from mpl_toolkits.axes_grid1 import make_axes_locatable

TIMING_RE = re.compile(
    r"#TIMING npe=(?P<npe>\d+) level=(?P<level>\d+) cells=(?P<cells>\d+) "
    r"steps=(?P<steps>\d+) t=(?P<t>\S+) real=(?P<real>\S+) "
    r"speed=(?P<speed>\S+) u=(?P<u>\S+)(?: grid=(?P<grid>\S+))?"
)
MACHINE_STYLE = {
    "MareNostrum 5": {"color": "#1A64B3", "marker": "o", "z": 4},
    "Snellius": {"color": "#4DAF4A", "marker": "P", "z": 3.5},
}
COMBINED_MARKERS = {
    "MareNostrum 5": {"marker": "o", "z": 4},
    "Snellius": {"marker": "D", "z": 3.5},
}
PTS_LEVELS = (64, 128, 256, 512)
PTS_NORM = LogNorm(vmin=64, vmax=512)
PTS_CMAP = LinearSegmentedColormap.from_list(
    "viridis_readable",
    plt.cm.viridis(np.linspace(0.08, 0.82, 256)),
)


def pts_per_r(level: int) -> int:
    return 2 ** (level - 4)


def row_from_match(match: re.Match[str], source: str) -> dict[str, float | int] | None:
    if match.group("grid") != "uniform":
        return None
    t = float(match.group("t"))
    level = int(match.group("level"))
    npe = int(match.group("npe"))
    steps = int(match.group("steps"))
    if level < 10 or npe < 1 or npe > 1024:
        return None
    # t/t0=0.5 physics window, or short-window rank sweep (t>=0.02, enough steps).
    if t < 0.45 and (t < 0.02 or steps < 80):
        return None
    real = float(match.group("real"))
    return {
        "npe": npe,
        "level": level,
        "pts": pts_per_r(level),
        "cells": int(match.group("cells")),
        "steps": steps,
        "t": t,
        "real": real,
        "speed": float(match.group("speed")),
        "u": float(match.group("u")),
        "per_step": real / max(steps, 1),
        "source": source,
    }


def parse_file(path: Path) -> dict[str, float | int] | None:
    match = None
    for line in path.read_text(errors="replace").splitlines():
        found = TIMING_RE.search(line)
        if found:
            match = found
    if match is None:
        return None
    return row_from_match(match, str(path))


def load_tree(root: Path) -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    if not root.exists():
        return rows
    if root.is_file():
        for line in root.read_text(errors="replace").splitlines():
            found = TIMING_RE.search(line)
            if found:
                row = row_from_match(found, str(root))
                if row is not None:
                    rows.append(row)
        return rows
    for path in sorted(root.rglob("out-*")):
        row = parse_file(path)
        if row is not None:
            rows.append(row)
    return rows


def style(ax: plt.Axes) -> None:
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xlim(2**0 / 1.2, 2**10 * 1.2)
    ax.tick_params(which="both", direction="out", width=3, labelsize=28, pad=10)
    ax.tick_params(which="major", length=12)
    ax.tick_params(which="minor", length=6)
    for spine in ax.spines.values():
        spine.set_linewidth(3)
    ax.minorticks_on()
    ax.set_box_aspect(1)


def plot_pair(
    rows: list[dict[str, float | int | str]],
    pts_left: int,
    pts_right: int,
    out: Path,
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(24, 10))
    fig.set_facecolor("white")
    rank_axis = np.array([2**k for k in range(0, 11)], dtype=float)
    for ax, pts in ((axes[0], pts_left), (axes[1], pts_right)):
        series = []
        for machine, spec in MACHINE_STYLE.items():
            picked = [
                row
                for row in rows
                if int(row["pts"]) == pts and str(row["machine"]) == machine
            ]
            picked.sort(key=lambda row: int(row["npe"]))
            if picked:
                series.append((machine, spec, picked))
        if series:
            first = series[0][2]
            n0 = float(first[0]["npe"])
            y0 = float(first[0]["real"]) / max(int(first[0]["steps"]), 1)
            if y0 > 0 and n0 > 0:
                ax.plot(
                    rank_axis,
                    y0 * n0 / rank_axis,
                    linestyle="--",
                    linewidth=3,
                    color="0.25",
                    label=r"ideal",
                    zorder=1,
                )
        for machine, spec, picked in series:
            npe = np.array([int(row["npe"]) for row in picked], dtype=float)
            y = np.array(
                [
                    float(row["real"]) / max(int(row["steps"]), 1)
                    for row in picked
                ],
                dtype=float,
            )
            ax.plot(
                npe,
                y,
                linestyle="-",
                linewidth=3,
                marker=spec["marker"],
                markersize=13,
                markerfacecolor=spec["color"],
                markeredgecolor="k",
                color=spec["color"],
                label=machine,
                zorder=spec["z"],
            )
        ax.set_xlabel(r"MPI ranks", fontsize=34, labelpad=12)
        ax.set_ylabel(r"Wall time / iteration (s)", fontsize=34, labelpad=12)
        ax.set_title(rf"Uniform mesh, ${pts}$ pts$/R$", fontsize=22, pad=12)
        if ax.get_legend_handles_labels()[0]:
            ax.legend(fontsize=18, frameon=False, loc="best")
        style(ax)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight", dpi=300, facecolor="white", pad_inches=0.1)
    plt.close(fig)


def _ideal_prefactor(
    rows: list[dict[str, float | int | str]],
    pts: int,
    npe_max: int | None = None,
) -> float | None:
    """Prefactor A in T = A / n with slope fixed at -1.

    Log-space least squares: log T = log A - log n, so A is the
    geometric mean of n T. Both machines, ranks up to npe_max.
    """
    values: list[float] = []
    for row in rows:
        if int(row["pts"]) != pts:
            continue
        npe = int(row["npe"])
        if npe_max is not None and npe > npe_max:
            continue
        per_step = float(row["per_step"])
        if npe > 0 and per_step > 0:
            values.append(npe * per_step)
    if not values:
        return None
    return float(np.exp(np.mean(np.log(np.array(values, dtype=float)))))


def plot_combined(rows: list[dict[str, float | int | str]], out: Path) -> None:
    fig, ax = plt.subplots(figsize=(12, 12))
    fig.set_facecolor("white")
    rank_axis = np.array([2**k for k in range(0, 11)], dtype=float)
    data_y = np.array([float(row["per_step"]) for row in rows], dtype=float)
    # 64 pts/R is communication-limited above 256 ranks. The finer
    # meshes stay in the scaling window over the measured range.
    ideal_window = {64: 256}
    ideal_A: dict[int, float] = {}
    for pts in PTS_LEVELS:
        npe_max = ideal_window.get(pts)
        prefactor = _ideal_prefactor(rows, pts, npe_max=npe_max)
        if prefactor is None:
            continue
        ideal_A[pts] = prefactor
        ax.plot(
            rank_axis,
            prefactor / rank_axis,
            linestyle="--",
            linewidth=2.8,
            color=PTS_CMAP(PTS_NORM(pts)),
            zorder=1,
        )
        print(f"ideal pts/R={pts} A={prefactor:.4g} s·rank (npe<={npe_max or 'all'})")

    for pts in PTS_LEVELS:
        color = PTS_CMAP(PTS_NORM(pts))
        for machine, spec in COMBINED_MARKERS.items():
            picked = [
                row
                for row in rows
                if int(row["pts"]) == pts and str(row["machine"]) == machine
            ]
            picked.sort(key=lambda row: int(row["npe"]))
            if not picked:
                continue
            npe = np.array([int(row["npe"]) for row in picked], dtype=float)
            y = np.array([float(row["per_step"]) for row in picked], dtype=float)
            ax.plot(
                npe,
                y,
                linestyle="-",
                linewidth=3,
                marker=spec["marker"],
                markersize=16,
                markerfacecolor=color,
                markeredgecolor="k",
                markeredgewidth=1.15,
                color=color,
                zorder=spec["z"],
            )

    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xlim(2**0 / 1.2, 2**10 * 1.2)
    ymin = float(data_y.min())
    ymax = float(data_y.max()) * 1.25
    if 64 in ideal_A:
        ymin = min(ymin, ideal_A[64] / rank_axis[-1])
    ax.set_ylim(ymin / 1.15, ymax)
    ax.set_xlabel(r"MPI ranks", fontsize=40, labelpad=15)
    ax.set_ylabel(r"Wall time / iteration (s)", fontsize=40, labelpad=15)
    ax.tick_params(which="both", direction="out", width=3, labelsize=30, pad=10)
    ax.tick_params(which="major", length=12)
    ax.tick_params(which="minor", length=6)
    for spine in ax.spines.values():
        spine.set_linewidth(3)
    ax.minorticks_on()
    ax.set_box_aspect(1)

    handles = [
        Line2D(
            [0],
            [0],
            linestyle="None",
            marker=COMBINED_MARKERS[name]["marker"],
            markersize=17,
            markerfacecolor="white",
            markeredgecolor="k",
            markeredgewidth=1.4,
            label=name,
        )
        for name in COMBINED_MARKERS
    ]
    handles.append(
        Line2D(
            [0],
            [0],
            linestyle="--",
            linewidth=2.8,
            color="0.2",
            label=r"ideal",
        )
    )
    ax.legend(
        handles=handles,
        loc="lower left",
        frameon=False,
        fontsize=30,
        handlelength=1.8,
        handletextpad=0.55,
        borderaxespad=0.45,
        labelspacing=0.4,
    )

    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="5%", pad=0.22)
    mappable = plt.cm.ScalarMappable(norm=PTS_NORM, cmap=PTS_CMAP)
    mappable.set_array([])
    cbar = fig.colorbar(mappable, cax=cax)
    cbar.set_label(r"$\mathrm{pts}/R$", fontsize=30, labelpad=12)
    cbar.set_ticks(list(PTS_LEVELS))
    cbar.set_ticklabels([rf"${pts}$" for pts in PTS_LEVELS])
    cbar.ax.tick_params(which="both", direction="out", width=2, labelsize=30, pad=8)
    cbar.ax.tick_params(which="major", length=8)
    cbar.ax.minorticks_off()
    cbar.outline.set_linewidth(3)

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight", dpi=300, facecolor="white", pad_inches=0.1)
    plt.close(fig)


def write_csv(rows: list[dict[str, float | int | str]], path: Path) -> None:
    fieldnames = [
        "machine",
        "pts",
        "level",
        "npe",
        "cells",
        "steps",
        "t",
        "real",
        "per_step",
        "speed",
        "u",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in sorted(
            rows,
            key=lambda item: (str(item["machine"]), int(item["pts"]), int(item["npe"])),
        ):
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--snellius", type=Path, default=None)
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()
    rows: list[dict[str, float | int | str]] = []
    for row in load_tree(args.results):
        item = dict(row)
        item["machine"] = "MareNostrum 5"
        rows.append(item)
    if args.snellius is not None:
        for row in load_tree(args.snellius):
            item = dict(row)
            item["machine"] = "Snellius"
            rows.append(item)
    if not rows:
        raise SystemExit("no uniform #TIMING rows")
    for row in rows:
        row["per_step"] = float(row["real"]) / max(int(row["steps"]), 1)
    write_csv(rows, args.outdir / "marangoni-uniform-per-iter-timings.csv")
    plot_pair(rows, 64, 128, args.outdir / "marangoni-uniform-per-iter-64-128.pdf")
    plot_pair(rows, 256, 512, args.outdir / "marangoni-uniform-per-iter-256-512.pdf")
    plot_combined(rows, args.outdir / "marangoni-uniform-per-iter.pdf")
    print(f"plotted {len(rows)} rows -> {args.outdir}")


if __name__ == "__main__":
    main()
