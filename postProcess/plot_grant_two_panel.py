#!/usr/bin/env python3
"""Two-panel grant figure: pts/R (left) and drop count at 64 pts/R (right)."""

from __future__ import annotations

import argparse
import csv
import os
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

COMBINED_MARKERS = {
    "MareNostrum 5": {"marker": "o", "z": 4},
    "Snellius": {"marker": "D", "z": 3.5},
}
PTS_LEVELS = (64, 128, 256, 512)
PTS_NORM = LogNorm(vmin=64, vmax=512)
DROP_LEVELS = (1, 2, 4, 8, 16, 32)
DROP_NORM = LogNorm(vmin=1, vmax=32)
VIRIDIS = LinearSegmentedColormap.from_list(
    "viridis_readable",
    plt.cm.viridis(np.linspace(0.08, 0.82, 256)),
)
LABEL_FONT = 34
TICK_FONT = 28
LEGEND_FONT = 26
CBAR_FONT = 28
PANEL_FONT = 30


def _load_csv(path: Path) -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    with path.open(newline="") as handle:
        for raw in csv.DictReader(handle):
            item: dict[str, float | int | str] = dict(raw)
            item["npe"] = int(raw["npe"])
            item["per_step"] = float(raw["per_step"])
            if "pts" in raw and raw["pts"] != "":
                item["pts"] = int(raw["pts"])
            if "ndrops" in raw and raw["ndrops"] != "":
                item["ndrops"] = int(raw["ndrops"])
            rows.append(item)
    return rows


def _ideal_prefactor(
    rows: list[dict[str, float | int | str]],
    key: str,
    value: int,
    npe_max: int | None,
) -> float | None:
    values: list[float] = []
    for row in rows:
        if int(row[key]) != value:
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


def _style(ax: plt.Axes) -> None:
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xlim(2**1 / 1.2, 2**10 * 1.2)
    ax.tick_params(which="both", direction="out", width=3, labelsize=TICK_FONT, pad=8)
    ax.tick_params(which="major", length=12)
    ax.tick_params(which="minor", length=6)
    for spine in ax.spines.values():
        spine.set_linewidth(3)
    ax.minorticks_on()
    ax.set_box_aspect(1)


def _machine_legend(ax: plt.Axes) -> None:
    handles = [
        Line2D(
            [0],
            [0],
            linestyle="None",
            marker=COMBINED_MARKERS[name]["marker"],
            markersize=16,
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
        fontsize=LEGEND_FONT,
        handlelength=1.8,
        handletextpad=0.5,
        borderaxespad=0.35,
        labelspacing=0.35,
    )


def _colorbar(fig: plt.Figure, ax: plt.Axes, norm, ticks, label: str) -> None:
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="5%", pad=0.18)
    mappable = plt.cm.ScalarMappable(norm=norm, cmap=VIRIDIS)
    mappable.set_array([])
    cbar = fig.colorbar(mappable, cax=cax)
    cbar.set_label(label, fontsize=CBAR_FONT, labelpad=10)
    cbar.set_ticks(list(ticks))
    cbar.set_ticklabels([rf"${tick}$" for tick in ticks])
    cbar.ax.tick_params(which="both", direction="out", width=2, labelsize=CBAR_FONT, pad=6)
    cbar.ax.tick_params(which="major", length=8)
    cbar.ax.minorticks_off()
    cbar.outline.set_linewidth(3)


def _draw_series(
    ax: plt.Axes,
    rows: list[dict[str, float | int | str]],
    key: str,
    levels: tuple[int, ...],
    norm,
    ideal_window: dict[int, int],
    rank_axis: np.ndarray,
) -> None:
    for value in levels:
        npe_max = ideal_window.get(value)
        prefactor = _ideal_prefactor(rows, key, value, npe_max)
        if prefactor is None:
            continue
        ax.plot(
            rank_axis,
            prefactor / rank_axis,
            linestyle="--",
            linewidth=2.6,
            color=VIRIDIS(norm(value)),
            zorder=1,
        )
        print(f"ideal {key}={value} A={prefactor:.4g} s·rank (npe<={npe_max or 'all'})")
    for value in levels:
        color = VIRIDIS(norm(value))
        for machine, spec in COMBINED_MARKERS.items():
            picked = [
                row
                for row in rows
                if int(row[key]) == value and str(row["machine"]) == machine
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
                linewidth=2.8,
                marker=spec["marker"],
                markersize=14,
                markerfacecolor=color,
                markeredgecolor="k",
                markeredgewidth=1.1,
                color=color,
                zorder=spec["z"],
            )


def plot_two_panel(
    pts_rows: list[dict[str, float | int | str]],
    drop_rows: list[dict[str, float | int | str]],
    out: Path,
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(24, 11))
    fig.set_facecolor("white")
    rank_axis = np.array([2**k for k in range(1, 11)], dtype=float)

    ax_pts, ax_drops = axes
    _draw_series(
        ax_pts,
        pts_rows,
        "pts",
        PTS_LEVELS,
        PTS_NORM,
        {64: 256},
        rank_axis,
    )
    _draw_series(
        ax_drops,
        drop_rows,
        "ndrops",
        DROP_LEVELS,
        DROP_NORM,
        {1: 256, 2: 256, 4: 256, 8: 256, 16: 512, 32: 512},
        rank_axis,
    )

    for ax, rows in ((ax_pts, pts_rows), (ax_drops, drop_rows)):
        data_y = np.array([float(row["per_step"]) for row in rows], dtype=float)
        ymin = float(data_y.min()) / 1.15
        ymax = float(data_y.max()) * 1.25
        ax.set_ylim(ymin, ymax)
        ax.set_xlabel(r"MPI ranks", fontsize=LABEL_FONT, labelpad=12)
        ax.set_ylabel(r"Wall time / iteration (s)", fontsize=LABEL_FONT, labelpad=12)
        _style(ax)

    ax_pts.set_title(r"$(a)$~axisymmetric, uniform mesh", fontsize=PANEL_FONT, pad=10)
    ax_drops.set_title(r"$(b)$~planar, $64$ pts$/R$", fontsize=PANEL_FONT, pad=10)
    _machine_legend(ax_pts)
    _machine_legend(ax_drops)
    _colorbar(fig, ax_pts, PTS_NORM, PTS_LEVELS, r"$\mathrm{pts}/R$")
    _colorbar(fig, ax_drops, DROP_NORM, DROP_LEVELS, r"drops")

    fig.tight_layout(w_pad=2.2)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight", dpi=300, facecolor="white", pad_inches=0.12)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pts-csv", type=Path, required=True)
    parser.add_argument("--drops-csv", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    pts_rows = _load_csv(args.pts_csv)
    drop_rows = _load_csv(args.drops_csv)
    if not pts_rows or not drop_rows:
        raise SystemExit("missing pts/R or drop-count timings")
    plot_two_panel(pts_rows, drop_rows, args.out)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
