#!/usr/bin/env python3
"""One strong-scaling panel per uniform-grid application kernel."""

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
    r"speed=(?P<speed>\S+) grid=uniform"
)
OUT_RE = re.compile(r"^out-(\d+)-(\d+)$")
MACHINE_STYLE = {
    "Snellius": {
        "color": "#4DAF4A",
        "marker": "D",
        "z": 3.5,
        "label": "Snellius",
    },
}
MULTILEVEL_CASES = {
    "bursting-uniform",
    "taylorculick-uniform",
    "drop-impact-uniform",
}
NX_LEVELS = (512, 1024, 2048)
NX_NORM = LogNorm(vmin=512, vmax=2048)
# Coarse L=9 saturates earlier; keep the ideal window on the scaling branch.
# L=11 (2048) still scales at 1536 ranks; 2304 is on the floor.
NX_IDEAL_WINDOW = {512: 96, 1024: 384, 2048: 1536}
VIRIDIS = LinearSegmentedColormap.from_list(
    "viridis_readable",
    plt.cm.viridis(np.linspace(0.08, 0.82, 256)),
)
CASES = (
    ("bursting-uniform", "bursting-uniform.pdf", r"Bursting bubble"),
    ("taylorculick-uniform", "taylorculick-uniform.pdf",
     r"Elastic Taylor--Culick"),
    ("ve3d-impact-uniform", "ve3d-impact-uniform.pdf",
     r"Viscoelastic drop impact, $L=7$"),
    ("drop-impact-uniform", "drop-impact-uniform.pdf",
     r"Newtonian drop impact"),
    ("jumping-uniform", "jumping-uniform.pdf", r"Jumping drops, $L=7$"),
)
LABEL_FONT = 40
TICK_FONT = 30
LEGEND_FONT = 30
CBAR_FONT = 28
SERIES_MARKER_SIZE = 14
LEGEND_MARKER_SIZE = 16


def parse_file(path: Path, case: str) -> dict[str, float | int | str] | None:
    match = None
    for line in path.read_text(errors="replace").splitlines():
        found = TIMING_RE.search(line)
        if found:
            match = found
    if match is None:
        return None
    name = OUT_RE.match(path.name)
    if name is None:
        return None
    npe = int(match.group("npe"))
    level = int(match.group("level"))
    if npe != int(name.group(2)) or level != int(name.group(1)):
        return None
    steps = int(match.group("steps"))
    if steps < 1:
        return None
    real = float(match.group("real"))
    return {
        "case": case,
        "npe": npe,
        "level": level,
        "nx": 2 ** level,
        "cells": int(match.group("cells")),
        "steps": steps,
        "t": float(match.group("t")),
        "real": real,
        "speed": float(match.group("speed")),
        "per_step": real / steps,
        "source": str(path),
    }


def load_tree(root: Path) -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    if not root.exists():
        return rows
    known = {case for case, _pdf, _title in CASES}
    for path in sorted(root.rglob("out-*")):
        case = path.parent.name
        if case not in known:
            continue
        row = parse_file(path, case)
        if row is not None:
            rows.append(row)
    return rows


def style(ax: plt.Axes) -> None:
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.tick_params(which="both", direction="out", width=3, labelsize=TICK_FONT, pad=10)
    ax.tick_params(which="major", length=12)
    ax.tick_params(which="minor", length=6)
    for spine in ax.spines.values():
        spine.set_linewidth(3)
    ax.minorticks_on()
    ax.set_box_aspect(1)


def _ideal_prefactor(
    rows: list[dict[str, float | int | str]],
    nx: int,
    npe_max: int | None,
) -> float | None:
    values: list[float] = []
    for row in rows:
        if int(row["nx"]) != nx:
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


def _colorbar(fig: plt.Figure, ax: plt.Axes) -> None:
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="5%", pad=0.18)
    mappable = plt.cm.ScalarMappable(norm=NX_NORM, cmap=VIRIDIS)
    mappable.set_array([])
    cbar = fig.colorbar(mappable, cax=cax)
    cbar.set_label(r"$N_x = 2^{L}$", fontsize=CBAR_FONT, labelpad=10)
    cbar.set_ticks(list(NX_LEVELS))
    cbar.set_ticklabels([rf"${tick}$" for tick in NX_LEVELS])
    cbar.ax.tick_params(which="both", direction="out", width=2, labelsize=CBAR_FONT, pad=6)
    cbar.ax.tick_params(which="major", length=8)
    cbar.ax.minorticks_off()
    cbar.outline.set_linewidth(3)


def plot_multilevel(
    rows: list[dict[str, float | int | str]],
    case: str,
    title: str,
    out: Path,
) -> None:
    picked = [row for row in rows if str(row["case"]) == case]
    if not picked:
        raise SystemExit(f"no #TIMING rows for {case}")
    npe = np.array([int(row["npe"]) for row in picked], dtype=float)
    y = np.array([float(row["per_step"]) for row in picked], dtype=float)
    rank_min = float(npe.min())
    rank_max = max(float(npe.max()), 192.0)
    rank_lo = int(np.floor(np.log2(rank_min)))
    rank_hi = int(np.ceil(np.log2(rank_max)))
    rank_axis = np.array([2**k for k in range(rank_lo, rank_hi + 1)], dtype=float)
    if rank_axis[-1] < rank_max:
        rank_axis = np.append(rank_axis, rank_max)

    fig, ax = plt.subplots(figsize=(12, 12))
    fig.set_facecolor("white")
    present_nx = sorted({int(row["nx"]) for row in picked})
    for nx in present_nx:
        npe_max = NX_IDEAL_WINDOW.get(nx)
        prefactor = _ideal_prefactor(picked, nx, npe_max)
        if prefactor is None:
            continue
        ax.plot(
            rank_axis,
            prefactor / rank_axis,
            linestyle="--",
            linewidth=2.6,
            color=VIRIDIS(NX_NORM(nx)),
            zorder=1,
        )
    for nx in present_nx:
        color = VIRIDIS(NX_NORM(nx))
        for machine, spec in MACHINE_STYLE.items():
            series = [
                row
                for row in picked
                if int(row["nx"]) == nx and str(row["machine"]) == machine
            ]
            if not series:
                continue
            series.sort(key=lambda row: int(row["npe"]))
            ax.plot(
                np.array([int(row["npe"]) for row in series], dtype=float),
                np.array([float(row["per_step"]) for row in series], dtype=float),
                linestyle="-",
                linewidth=2.8,
                marker=spec["marker"],
                markersize=SERIES_MARKER_SIZE,
                markerfacecolor=color,
                markeredgecolor="k",
                markeredgewidth=1.1,
                color=color,
                zorder=spec["z"],
            )
    ax.set_xlim(rank_min / 1.2, rank_max * 1.2)
    ax.set_ylim(float(y.min()) / 1.15, float(y.max()) * 1.25)
    ax.set_xlabel(r"MPI ranks", fontsize=LABEL_FONT, labelpad=15)
    ax.set_ylabel(r"Wall time / iteration (s)", fontsize=LABEL_FONT, labelpad=15)
    ax.set_title(title, fontsize=28, pad=14)
    handles = [
        Line2D(
            [0],
            [0],
            linestyle="None",
            marker=spec["marker"],
            markersize=LEGEND_MARKER_SIZE,
            markerfacecolor="white",
            markeredgecolor="k",
            markeredgewidth=1.4,
            label=spec["label"],
        )
        for spec in MACHINE_STYLE.values()
        if any(str(row["machine"]) == spec["label"] for row in picked)
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
        fontsize=LEGEND_FONT,
        handlelength=1.8,
        handletextpad=0.55,
        borderaxespad=0.45,
        labelspacing=0.4,
    )
    style(ax)
    ranks = sorted({int(row["npe"]) for row in picked})
    ax.set_xticks(ranks)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter(r"%d"))
    ax.tick_params(axis="x", which="minor", length=0)
    if any(int(row["nx"]) in NX_LEVELS for row in picked):
        _colorbar(fig, ax)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight", dpi=300, facecolor="white", pad_inches=0.15)
    plt.close(fig)


def plot_case(
    rows: list[dict[str, float | int | str]],
    case: str,
    title: str,
    out: Path,
) -> None:
    picked = [row for row in rows if str(row["case"]) == case]
    picked.sort(key=lambda row: (str(row["machine"]), int(row["npe"])))
    if not picked:
        raise SystemExit(f"no #TIMING rows for {case}")
    fig, ax = plt.subplots(figsize=(12, 12))
    fig.set_facecolor("white")
    npe = np.array([int(row["npe"]) for row in picked], dtype=float)
    y = np.array([float(row["per_step"]) for row in picked], dtype=float)
    rank_min = float(npe.min())
    rank_max = max(float(npe.max()), 192.0)
    rank_axis = np.array(
        [2**k for k in range(int(np.log2(rank_min)), int(np.log2(rank_max)) + 1)],
        dtype=float,
    )
    if rank_axis[-1] < rank_max:
        rank_axis = np.append(rank_axis, rank_max)
    y0 = float(picked[0]["per_step"])
    n0 = float(picked[0]["npe"])
    if y0 > 0 and n0 > 0:
        ax.plot(
            rank_axis,
            y0 * n0 / rank_axis,
            linestyle="--",
            linewidth=2.8,
            color="0.25",
            zorder=1,
        )
    for machine, spec in MACHINE_STYLE.items():
        series = [row for row in picked if str(row["machine"]) == machine]
        if not series:
            continue
        series.sort(key=lambda row: int(row["npe"]))
        ax.plot(
            np.array([int(row["npe"]) for row in series], dtype=float),
            np.array([float(row["per_step"]) for row in series], dtype=float),
            linestyle="-",
            linewidth=3,
            marker=spec["marker"],
            markersize=16,
            markerfacecolor=spec["color"],
            markeredgecolor="k",
            markeredgewidth=1.15,
            color=spec["color"],
            zorder=spec["z"],
        )
    ax.set_xlim(rank_min / 1.2, rank_max * 1.2)
    ax.set_ylim(float(y.min()) / 1.15, float(y.max()) * 1.25)
    ax.set_xlabel(r"MPI ranks", fontsize=LABEL_FONT, labelpad=15)
    ax.set_ylabel(r"Wall time / iteration (s)", fontsize=LABEL_FONT, labelpad=15)
    ax.set_title(title, fontsize=28, pad=14)
    handles = [
        Line2D(
            [0],
            [0],
            linestyle="None",
            marker=spec["marker"],
            markersize=17,
            markerfacecolor=spec["color"],
            markeredgecolor="k",
            markeredgewidth=1.4,
            label=spec["label"],
        )
        for spec in MACHINE_STYLE.values()
        if any(str(row["machine"]) == spec["label"] for row in picked)
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
        fontsize=LEGEND_FONT,
        handlelength=1.8,
        handletextpad=0.55,
        borderaxespad=0.45,
        labelspacing=0.4,
    )
    style(ax)
    ranks = sorted({int(row["npe"]) for row in picked})
    ax.set_xticks(ranks)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter(r"%d"))
    ax.tick_params(axis="x", which="minor", length=0)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight", dpi=300, facecolor="white", pad_inches=0.1)
    plt.close(fig)


def write_csv(rows: list[dict[str, float | int | str]], path: Path) -> None:
    fieldnames = [
        "machine",
        "case",
        "level",
        "nx",
        "npe",
        "cells",
        "steps",
        "t",
        "real",
        "per_step",
        "speed",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in sorted(
            rows,
            key=lambda item: (
                str(item["machine"]),
                str(item["case"]),
                int(item["level"]),
                int(item["npe"]),
            ),
        ):
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snellius", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()
    rows: list[dict[str, float | int | str]] = []
    for row in load_tree(args.snellius):
        item = dict(row)
        item["machine"] = "Snellius"
        rows.append(item)
    if not rows:
        raise SystemExit(f"no uniform-app #TIMING rows under {args.snellius}")
    write_csv(rows, args.outdir / "uniform-app-timings.csv")
    for case, filename, title in CASES:
        if case in MULTILEVEL_CASES:
            plot_multilevel(rows, case, title, args.outdir / filename)
        else:
            plot_case(rows, case, title, args.outdir / filename)
    print(f"plotted {len(rows)} rows -> {args.outdir}")


if __name__ == "__main__":
    main()
