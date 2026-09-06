#!/usr/bin/env python3
"""Render compact, report-sized scaling charts for the uniform applications."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

# Keep the report figures on the same Computer Modern/LaTeX stack as the
# source scaling figures, while sizing all text for a 166 mm report column.
matplotlib.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Computer Modern Roman"],
        "font.size": 9,
        "axes.labelsize": 10,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "text.usetex": True,
        "text.latex.preamble": r"\usepackage{amsmath}",
        "pdf.fonttype": 42,
    }
)

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.ticker import FormatStrFormatter

import plot_uniform_apps as source_plot


REPO = Path(__file__).resolve().parents[1]
TIMING_CSV = REPO / "figures" / "uniform-app-timings.csv"
FIGURE_WIDTH_MM = 166.0
FIGURE_HEIGHT_MM = 63.0
FIGURE_SIZE = (FIGURE_WIDTH_MM / 25.4, FIGURE_HEIGHT_MM / 25.4)

# The case names and output names remain the canonical source-script order.
REPORT_CASES = tuple(
    (case, filename.replace(".pdf", "-report.pdf"))
    for case, filename, _title in source_plot.CASES
)
MULTILEVEL_CASES = source_plot.MULTILEVEL_CASES
NX_LEVELS = source_plot.NX_LEVELS
NX_NORM = source_plot.NX_NORM
NX_IDEAL_WINDOW = source_plot.NX_IDEAL_WINDOW
VIRIDIS = source_plot.VIRIDIS
MACHINE_STYLE = source_plot.MACHINE_STYLE


def load_rows(path: Path) -> list[dict[str, float | int | str]]:
    """Load the committed table using the source plotter's row semantics."""
    with path.open(newline="") as handle:
        raw_rows = list(csv.DictReader(handle))
    required = {
        "machine", "case", "level", "nx", "npe", "cells", "steps",
        "t", "real", "per_step", "speed",
    }
    if not raw_rows or not required.issubset(raw_rows[0]):
        raise SystemExit(f"{path} is missing one or more timing columns")

    rows: list[dict[str, float | int | str]] = []
    for raw in raw_rows:
        level = int(raw["level"])
        steps = int(raw["steps"])
        if steps < 1 or int(raw["nx"]) != 2**level:
            raise SystemExit(f"invalid mesh metadata in {path}: {raw}")
        real = float(raw["real"])
        # Recompute this field as parse_file() does in plot_uniform_apps.py;
        # the CSV is the committed compact representation of those rows.
        rows.append(
            {
                "machine": raw["machine"],
                "case": raw["case"],
                "level": level,
                "nx": 2**level,
                "npe": int(raw["npe"]),
                "cells": int(raw["cells"]),
                "steps": steps,
                "t": float(raw["t"]),
                "real": real,
                "per_step": real / steps,
                "speed": float(raw["speed"]),
            }
        )
    return rows


def _rank_axis_multilevel(
    picked: list[dict[str, float | int | str]],
) -> tuple[float, float, np.ndarray]:
    """Match plot_uniform_apps.plot_multilevel() exactly."""
    npe = np.array([int(row["npe"]) for row in picked], dtype=float)
    rank_min = float(npe.min())
    rank_max = max(float(npe.max()), 192.0)
    rank_lo = int(np.floor(np.log2(rank_min)))
    rank_hi = int(np.ceil(np.log2(rank_max)))
    rank_axis = np.array([2**k for k in range(rank_lo, rank_hi + 1)], dtype=float)
    if rank_axis[-1] < rank_max:
        rank_axis = np.append(rank_axis, rank_max)
    return rank_min, rank_max, rank_axis


def _rank_axis_single(
    picked: list[dict[str, float | int | str]],
) -> tuple[float, float, np.ndarray]:
    """Match plot_uniform_apps.plot_case() exactly."""
    npe = np.array([int(row["npe"]) for row in picked], dtype=float)
    rank_min = float(npe.min())
    rank_max = max(float(npe.max()), 192.0)
    rank_axis = np.array(
        [
            2**k
            for k in range(int(np.log2(rank_min)), int(np.log2(rank_max)) + 1)
        ],
        dtype=float,
    )
    if rank_axis[-1] < rank_max:
        rank_axis = np.append(rank_axis, rank_max)
    return rank_min, rank_max, rank_axis


def style_axes(ax: plt.Axes, ranks: list[int]) -> None:
    """Apply compact report styling while retaining source tick selection."""
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.tick_params(which="both", direction="out", width=0.8, labelsize=9, pad=3)
    ax.tick_params(which="major", length=4)
    ax.tick_params(which="minor", length=2)
    for spine in ax.spines.values():
        spine.set_linewidth(0.8)
    ax.minorticks_on()
    ax.set_xticks(source_plot._xticks_for_ranks(ranks))
    ax.xaxis.set_major_formatter(FormatStrFormatter(r"%d"))
    ax.tick_params(axis="x", which="minor", length=0)


def add_colourbar(fig: plt.Figure, cax: plt.Axes) -> None:
    """Add the thin level colourbar used by the multilevel charts."""
    mappable = plt.cm.ScalarMappable(norm=NX_NORM, cmap=VIRIDIS)
    mappable.set_array([])
    cbar = fig.colorbar(mappable, cax=cax)
    cbar.set_label(r"$N_x=2^L$", fontsize=10, labelpad=3)
    cbar.set_ticks(list(NX_LEVELS))
    cbar.set_ticklabels([rf"${tick}$" for tick in NX_LEVELS])
    cbar.ax.tick_params(which="both", direction="out", width=0.7, labelsize=9, pad=2)
    cbar.ax.tick_params(which="major", length=3)
    cbar.ax.minorticks_off()
    cbar.outline.set_linewidth(0.8)


def add_legend(ax: plt.Axes, measured: bool = True) -> None:
    handles: list[Line2D] = []
    if measured:
        spec = MACHINE_STYLE["Snellius"]
        handles.append(
            Line2D(
                [0],
                [0],
                linestyle="None",
                marker=spec["marker"],
                markersize=4.5,
                markerfacecolor="white",
                markeredgecolor="k",
                markeredgewidth=0.6,
                label=spec["label"],
            )
        )
    handles.append(
        Line2D(
            [0], [0], linestyle="--", linewidth=1.0, color="0.25", label="ideal"
        )
    )
    ax.legend(
        handles=handles,
        loc="lower left",
        frameon=False,
        fontsize=9,
        handlelength=1.8,
        handletextpad=0.45,
        borderaxespad=0.35,
        labelspacing=0.25,
    )


def configure_figure(with_colourbar: bool) -> tuple[plt.Figure, plt.Axes]:
    fig = plt.figure(figsize=FIGURE_SIZE, facecolor="white")
    # Manual axes keep the PDF canvas fixed: savefig deliberately does not use
    # bbox_inches="tight", so these dimensions survive LaTeX inclusion.
    if with_colourbar:
        ax = fig.add_axes([0.090, 0.275, 0.805, 0.655])
    else:
        ax = fig.add_axes([0.090, 0.275, 0.885, 0.655])
    return fig, ax


def finish_axes(
    ax: plt.Axes,
    picked: list[dict[str, float | int | str]],
    rank_min: float,
    rank_max: float,
) -> None:
    y = np.array([float(row["per_step"]) for row in picked], dtype=float)
    ax.set_xlim(rank_min / 1.2, rank_max * 1.2)
    ax.set_ylim(float(y.min()) / 1.15, float(y.max()) * 1.25)
    ax.set_xlabel("MPI ranks", fontsize=10, labelpad=3)
    ax.set_ylabel("Wall time / iteration (s)", fontsize=10, labelpad=3)
    style_axes(ax, sorted({int(row["npe"]) for row in picked}))


def plot_multilevel(
    rows: list[dict[str, float | int | str]], case: str, out: Path
) -> None:
    picked = [row for row in rows if str(row["case"]) == case]
    if not picked:
        raise SystemExit(f"no timing rows for {case}")
    rank_min, rank_max, rank_axis = _rank_axis_multilevel(picked)
    fig, ax = configure_figure(with_colourbar=True)
    present_nx = sorted({int(row["nx"]) for row in picked})

    for nx in present_nx:
        prefactor = source_plot._ideal_prefactor(
            picked, nx, NX_IDEAL_WINDOW.get(nx)
        )
        if prefactor is not None:
            ax.plot(
                rank_axis,
                prefactor / rank_axis,
                linestyle="--",
                linewidth=1.0,
                color=VIRIDIS(NX_NORM(nx)),
                zorder=1,
            )

    for nx in present_nx:
        colour = VIRIDIS(NX_NORM(nx))
        for machine, spec in MACHINE_STYLE.items():
            series = sorted(
                (
                    row
                    for row in picked
                    if int(row["nx"]) == nx
                    and str(row["machine"]) == machine
                ),
                key=lambda row: int(row["npe"]),
            )
            if not series:
                continue
            ax.plot(
                [int(row["npe"]) for row in series],
                [float(row["per_step"]) for row in series],
                linestyle="-",
                linewidth=1.2,
                marker=spec["marker"],
                markersize=4,
                markerfacecolor=colour,
                markeredgecolor="k",
                markeredgewidth=0.4,
                color=colour,
                zorder=spec["z"],
            )

    finish_axes(ax, picked, rank_min, rank_max)
    add_legend(ax)
    cax = fig.add_axes([0.905, 0.275, 0.014, 0.655])
    add_colourbar(fig, cax)
    save_figure(fig, out)


def plot_single_level(
    rows: list[dict[str, float | int | str]], case: str, out: Path
) -> None:
    picked = [row for row in rows if str(row["case"]) == case]
    picked.sort(key=lambda row: (str(row["machine"]), int(row["npe"])))
    if not picked:
        raise SystemExit(f"no timing rows for {case}")
    rank_min, rank_max, rank_axis = _rank_axis_single(picked)
    fig, ax = configure_figure(with_colourbar=False)

    y0 = float(picked[0]["per_step"])
    n0 = float(picked[0]["npe"])
    if y0 > 0 and n0 > 0:
        ax.plot(
            rank_axis,
            y0 * n0 / rank_axis,
            linestyle="--",
            linewidth=1.0,
            color="0.25",
            zorder=1,
        )
    for machine, spec in MACHINE_STYLE.items():
        series = sorted(
            (row for row in picked if str(row["machine"]) == machine),
            key=lambda row: int(row["npe"]),
        )
        if not series:
            continue
        ax.plot(
            [int(row["npe"]) for row in series],
            [float(row["per_step"]) for row in series],
            linestyle="-",
            linewidth=1.2,
            marker=spec["marker"],
            markersize=4,
            markerfacecolor=spec["color"],
            markeredgecolor="k",
            markeredgewidth=0.4,
            color=spec["color"],
            zorder=spec["z"],
        )

    finish_axes(ax, picked, rank_min, rank_max)
    add_legend(ax)
    save_figure(fig, out)


def save_figure(fig: plt.Figure, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "Creator": "postProcess/plot_report_apps.py",
        "CreationDate": None,
        "ModDate": None,
    }
    fig.savefig(out, dpi=300, facecolor="white", metadata=metadata)
    # PNGs are ignored by the component repository and make exact-output
    # inspection convenient without changing the tracked report assets.
    fig.savefig(out.with_suffix(".png"), dpi=300, facecolor="white")
    plt.close(fig)


def validate_source_rows(rows: list[dict[str, float | int | str]]) -> None:
    known_cases = {case for case, _filename in REPORT_CASES}
    if {str(row["case"]) for row in rows} != known_cases:
        raise SystemExit("uniform-app-timings.csv does not contain exactly the four report cases")
    for case in known_cases:
        picked = [row for row in rows if str(row["case"]) == case]
        machines = {str(row["machine"]) for row in picked}
        if machines != {"Snellius"}:
            raise SystemExit(f"unexpected machine selection for {case}: {machines}")
    ve3d_levels = {int(row["level"]) for row in rows if row["case"] == "ve3d-impact-uniform"}
    if ve3d_levels != {7}:
        raise SystemExit(f"VE3D source selection changed: expected L=7, found {ve3d_levels}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=TIMING_CSV)
    parser.add_argument("--outdir", type=Path, default=REPO / "figures")
    args = parser.parse_args()
    rows = load_rows(args.csv)
    validate_source_rows(rows)
    for case, filename in REPORT_CASES:
        out = args.outdir / filename
        if case in MULTILEVEL_CASES:
            plot_multilevel(rows, case, out)
        else:
            plot_single_level(rows, case, out)
    print(
        f"wrote {len(REPORT_CASES)} report application figures "
        f"({FIGURE_WIDTH_MM:.0f} x {FIGURE_HEIGHT_MM:.0f} mm) from {len(rows)} timing rows"
    )


if __name__ == "__main__":
    main()
