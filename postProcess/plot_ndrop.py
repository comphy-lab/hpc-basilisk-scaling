#!/usr/bin/env python3
"""Wall time / iteration vs MPI ranks for planar uniform Marangoni.

One combined figure: colour by drop count, markers by machine.
"""

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
    r"#TIMING npe=(?P<npe>\d+) ndrops=(?P<ndrops>\d+) level=(?P<level>\d+) "
    r"cells=(?P<cells>\d+) steps=(?P<steps>\d+) t=(?P<t>\S+) "
    r"real=(?P<real>\S+) speed=(?P<speed>\S+) u=(?P<u>\S+)"
    r"(?: grid=(?P<grid>\S+))?"
)
COMBINED_MARKERS = {
    "MareNostrum 5": {"marker": "o", "z": 4},
    "Snellius": {"marker": "D", "z": 3.5},
}
DROP_LEVELS = (1, 2, 4, 8, 16, 32)
DROP_NORM = LogNorm(vmin=1, vmax=32)
DROP_CMAP = LinearSegmentedColormap.from_list(
    "viridis_readable",
    plt.cm.viridis(np.linspace(0.08, 0.82, 256)),
)


def row_from_match(match: re.Match[str], source: str) -> dict[str, float | int] | None:
    if match.group("grid") not in (None, "uniform"):
        return None
    ndrops = int(match.group("ndrops"))
    if ndrops not in DROP_LEVELS:
        return None
    t = float(match.group("t"))
    npe = int(match.group("npe"))
    steps = int(match.group("steps"))
    if npe < 2 or npe > 1024:
        return None
    if t < 0.45 and (t < 0.02 or steps < 80):
        return None
    real = float(match.group("real"))
    return {
        "npe": npe,
        "ndrops": ndrops,
        "level": int(match.group("level")),
        "cells": int(match.group("cells")),
        "steps": steps,
        "t": t,
        "real": real,
        "speed": float(match.group("speed")),
        "u": float(match.group("u")),
        "per_step": real / max(steps, 1),
        "source": source,
    }


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
        text = path.read_text(errors="replace")
        match = None
        for line in text.splitlines():
            found = TIMING_RE.search(line)
            if found:
                match = found
        if match is None:
            continue
        row = row_from_match(match, str(path))
        if row is not None:
            rows.append(row)
    return rows


def _ideal_prefactor(
    rows: list[dict[str, float | int | str]],
    ndrops: int,
    npe_max: int | None = None,
) -> float | None:
    """Prefactor A in T = A / n with slope fixed at -1.

    Log-space least squares: log T = log A - log n, so A is the
    geometric mean of n T. Both machines, ranks up to npe_max.
    """
    values: list[float] = []
    for row in rows:
        if int(row["ndrops"]) != ndrops:
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
    rank_axis = np.array([2**k for k in range(1, 11)], dtype=float)
    data_y = np.array([float(row["per_step"]) for row in rows], dtype=float)
    # 1/2/4/8 drops share the LEVEL 10 1M-cell mesh and are
    # communication-limited above 256 ranks. 16/32 drops grow the
    # box to LEVEL 11 (4.19e6 cells); 512 is still in the window.
    ideal_window = {1: 256, 2: 256, 4: 256, 8: 256, 16: 512, 32: 512}
    ideal_A: dict[int, float] = {}
    for ndrops in DROP_LEVELS:
        npe_max = ideal_window.get(ndrops)
        prefactor = _ideal_prefactor(rows, ndrops, npe_max=npe_max)
        if prefactor is None:
            continue
        ideal_A[ndrops] = prefactor
        ax.plot(
            rank_axis,
            prefactor / rank_axis,
            linestyle="--",
            linewidth=2.8,
            color=DROP_CMAP(DROP_NORM(ndrops)),
            zorder=1,
        )
        print(
            f"ideal ndrops={ndrops} A={prefactor:.4g} s·rank "
            f"(npe<={npe_max or 'all'})"
        )

    for ndrops in DROP_LEVELS:
        color = DROP_CMAP(DROP_NORM(ndrops))
        for machine, spec in COMBINED_MARKERS.items():
            picked = [
                row
                for row in rows
                if int(row["ndrops"]) == ndrops and str(row["machine"]) == machine
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
    ax.set_xlim(2**1 / 1.2, 2**10 * 1.2)
    ymin = float(data_y.min())
    ymax = float(data_y.max()) * 1.25
    if 1 in ideal_A:
        ymin = min(ymin, ideal_A[1] / rank_axis[-1])
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
    mappable = plt.cm.ScalarMappable(norm=DROP_NORM, cmap=DROP_CMAP)
    mappable.set_array([])
    cbar = fig.colorbar(mappable, cax=cax)
    cbar.set_label(r"drops", fontsize=30, labelpad=12)
    cbar.set_ticks(list(DROP_LEVELS))
    cbar.set_ticklabels([rf"${ndrops}$" for ndrops in DROP_LEVELS])
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
        "ndrops",
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
            key=lambda item: (
                str(item["machine"]),
                int(item["ndrops"]),
                int(item["npe"]),
            ),
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
        raise SystemExit("no planar ndrop #TIMING rows")
    write_csv(rows, args.outdir / "planar-ndrop-timings.csv")
    plot_combined(rows, args.outdir / "planar-ndrop-per-iter.pdf")
    print(f"plotted {len(rows)} rows -> {args.outdir}")


if __name__ == "__main__":
    main()
