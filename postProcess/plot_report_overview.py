#!/usr/bin/env python3
"""Build report-sized overview figures from the committed timing tables."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import matplotlib

matplotlib.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Computer Modern Roman"],
        "font.size": 9,
        "axes.labelsize": 10,
        "axes.titlesize": 11,
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
from matplotlib.colors import LinearSegmentedColormap, LogNorm
from matplotlib.lines import Line2D
from matplotlib.ticker import FixedLocator, NullFormatter

REPO = Path(__file__).resolve().parents[1]
FIGURE_WIDTH_IN = 166.0 / 25.4
KERNEL_HEIGHT_IN = 112.0 / 25.4
APPLICATION_HEIGHT_IN = 118.0 / 25.4
KERNEL_CSV = REPO / "figures" / "kernel-timings.csv"
PTS_CSV = REPO / "figures" / "marangoni-uniform-per-iter-timings.csv"
DROPS_CSV = REPO / "figures" / "planar-ndrop-timings.csv"

MACHINE_STYLE = {
    "MareNostrum 5": {
        "wall": "#1A64B3",
        "mpi": "#C44E52",
        "wall_marker": "o",
        "mpi_marker": "s",
        "zorder": 4,
    },
    "Snellius": {
        "wall": "#4DAF4A",
        "mpi": "#984EA3",
        "wall_marker": "P",
        "mpi_marker": "X",
        "zorder": 3.5,
    },
}
REFERENCE_STYLE = {
    "wall": "#E76F51",
    "mpi": "#8C564B",
    "wall_marker": "D",
    "mpi_marker": "^",
}
REFERENCE_ROOT = {
    "mpi-laplacian-2d": REPO / "reference" / "curie",
    "mpi-laplacian": REPO / "reference" / "occigen-3D",
}
REFERENCE_LABEL = {"mpi-laplacian-2d": "Curie", "mpi-laplacian": "Occigen"}
OUT_RE = re.compile(r"^out-(\d+)-(\d+)$")

COMBINED_MARKERS = {"MareNostrum 5": "o", "Snellius": "D"}
PTS_LEVELS = (64, 128, 256, 512)
DROP_LEVELS = (1, 2, 4, 8, 16, 32)
PTS_NORM = LogNorm(vmin=64, vmax=512)
DROP_NORM = LogNorm(vmin=1, vmax=32)
VIRIDIS = matplotlib.colors.LinearSegmentedColormap.from_list(
    "viridis_readable", plt.cm.viridis(np.linspace(0.08, 0.82, 256))
)


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def select_kernel(
    rows: list[dict[str, str]], machine: str, test: str, level: int, kernel: str
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    picked = [
        row
        for row in rows
        if row["machine"] == machine
        and row["test"] == test
        and int(row["level"]) == level
        and row["name"] == kernel
    ]
    picked.sort(key=lambda row: int(row["npe"]))
    return (
        np.array([int(row["npe"]) for row in picked], dtype=float),
        np.array([float(row["real"]) for row in picked], dtype=float),
        np.array([float(row["comm_avg"]) for row in picked], dtype=float),
    )


def select_reference(
    test: str, level: int, kernel: str
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rows: list[tuple[int, float, float]] = []
    for path in sorted(REFERENCE_ROOT[test].glob(f"out-{level}-*")):
        match = OUT_RE.match(path.name)
        if match is None:
            continue
        npe_from_name = int(match.group(2))
        for raw in path.read_text(errors="replace").splitlines():
            parts = raw.split()
            if len(parts) < 11:
                continue
            try:
                npe, real, comm = int(parts[0]), float(parts[2]), float(parts[6])
            except ValueError:
                continue
            if npe == npe_from_name and parts[4].strip("[]") == kernel:
                rows.append((npe, real, comm))
    rows.sort()
    return tuple(np.array(values, dtype=float) for values in zip(*rows)) if rows else (
        np.array([]), np.array([]), np.array([])
    )


def sparse_rank_ticks(ax: plt.Axes, minimum: int, maximum: int) -> None:
    midpoint = 2 ** int(round((np.log2(minimum) + np.log2(maximum)) / 2))
    ticks = sorted(set((minimum, midpoint, maximum)))
    ax.xaxis.set_major_locator(FixedLocator(ticks))
    ax.set_xticklabels(["$" + f"{tick:,}".replace(",", "{,}") + "$" for tick in ticks])
    ax.xaxis.set_minor_formatter(NullFormatter())


def style_log_axes(ax: plt.Axes, xmin: int, xmax: int) -> None:
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xlim(xmin / 1.25, xmax * 1.25)
    sparse_rank_ticks(ax, xmin, xmax)
    ax.tick_params(which="major", direction="out", width=0.8, length=4, pad=3)
    ax.tick_params(which="minor", direction="out", width=0.55, length=2)
    for spine in ax.spines.values():
        spine.set_linewidth(0.8)
    ax.grid(which="major", color="0.9", linewidth=0.5, zorder=0)


def plot_kernel_report(
    rows: list[dict[str, str]], test: str, level: int, out: Path
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(FIGURE_WIDTH_IN, KERNEL_HEIGHT_IN))
    handles: list[Line2D] = []
    all_ranks: list[int] = []
    for ax, kernel, panel in zip(axes, ("poisson", "laplacian"), ("a", "b")):
        first_machine: tuple[np.ndarray, np.ndarray] | None = None
        for machine, spec in MACHINE_STYLE.items():
            npe, wall, mpi = select_kernel(rows, machine, test, level, kernel)
            if not npe.size:
                continue
            all_ranks.extend(npe.astype(int))
            if first_machine is None:
                first_machine = (npe, wall)
            wall_line, = ax.plot(
                npe, wall, "-", lw=1.25, marker=spec["wall_marker"], ms=4.2,
                mfc=spec["wall"], mec="k", mew=0.45, color=spec["wall"],
                zorder=spec["zorder"], label=f"{machine} wall",
            )
            mpi_line, = ax.plot(
                npe, mpi, "--", lw=1.05, marker=spec["mpi_marker"], ms=3.7,
                mfc=spec["mpi"], mec="k", mew=0.4, color=spec["mpi"],
                zorder=spec["zorder"] - 0.5, label=f"{machine} MPI",
            )
            if kernel == "poisson":
                handles.extend((wall_line, mpi_line))

        ref_npe, ref_wall, ref_mpi = select_reference(test, level, kernel)
        if not ref_npe.size:
            raise SystemExit(f"missing {REFERENCE_LABEL[test]} reference for {test} L={level}")
        all_ranks.extend(ref_npe.astype(int))
        ref_wall_line, = ax.plot(
            ref_npe, ref_wall, "-", lw=1.05, marker=REFERENCE_STYLE["wall_marker"],
            ms=3.8, mfc="none", mec=REFERENCE_STYLE["wall"], mew=0.9,
            color=REFERENCE_STYLE["wall"], zorder=2,
            label=f"{REFERENCE_LABEL[test]} wall",
        )
        ref_mpi_line, = ax.plot(
            ref_npe, ref_mpi, "--", lw=0.95, marker=REFERENCE_STYLE["mpi_marker"],
            ms=3.5, mfc="none", mec=REFERENCE_STYLE["mpi"], mew=0.8,
            color=REFERENCE_STYLE["mpi"], zorder=2,
            label=f"{REFERENCE_LABEL[test]} MPI",
        )
        if kernel == "poisson":
            handles.extend((ref_wall_line, ref_mpi_line))
        if first_machine is None:
            raise SystemExit(f"missing machine data for {test} L={level} {kernel}")
        ideal_npe, ideal_wall = first_machine
        ideal_line, = ax.plot(
            ideal_npe, ideal_wall[0] * ideal_npe[0] / ideal_npe, ":", lw=1.1,
            color="0.3", zorder=1, label="ideal (MareNostrum 5)",
        )
        if kernel == "poisson":
            handles.append(ideal_line)
        ax.set_title(rf"$({panel})$~{kernel.capitalize()}", pad=5)
        ax.set_xlabel("MPI ranks", labelpad=3)
        ax.set_ylabel("Time / iteration (s)", labelpad=3)

    xmin, xmax = min(all_ranks), max(all_ranks)
    for ax in axes:
        style_log_axes(ax, xmin, xmax)
    fig.legend(
        handles=handles, loc="lower center", ncol=4, frameon=False,
        bbox_to_anchor=(0.5, 0.015), handlelength=2.0, columnspacing=1.0,
        handletextpad=0.45, labelspacing=0.35,
    )
    fig.subplots_adjust(left=0.105, right=0.955, top=0.93, bottom=0.28, wspace=0.28)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=300, facecolor="white")
    plt.close(fig)


def ideal_prefactor(
    rows: list[dict[str, str]], key: str, value: int, npe_max: int | None
) -> float | None:
    values = [
        int(row["npe"]) * float(row["per_step"])
        for row in rows
        if int(row[key]) == value
        and (npe_max is None or int(row["npe"]) <= npe_max)
        and int(row["npe"]) > 0
        and float(row["per_step"]) > 0
    ]
    return float(np.exp(np.mean(np.log(values)))) if values else None


def draw_application_series(
    ax: plt.Axes,
    rows: list[dict[str, str]],
    key: str,
    levels: tuple[int, ...],
    norm: LogNorm,
    ideal_window: dict[int, int],
) -> None:
    rank_axis = np.array([2**k for k in range(1, 11)], dtype=float)
    for value in levels:
        prefactor = ideal_prefactor(rows, key, value, ideal_window.get(value))
        if prefactor is not None:
            ax.plot(rank_axis, prefactor / rank_axis, "--", lw=0.95,
                    color=VIRIDIS(norm(value)), zorder=1)
    for value in levels:
        colour = VIRIDIS(norm(value))
        for machine, marker in COMBINED_MARKERS.items():
            picked = sorted(
                (row for row in rows if int(row[key]) == value and row["machine"] == machine),
                key=lambda row: int(row["npe"]),
            )
            if picked:
                ax.plot(
                    [int(row["npe"]) for row in picked],
                    [float(row["per_step"]) for row in picked],
                    "-", lw=1.05, marker=marker, ms=3.8, mfc=colour,
                    mec="k", mew=0.4, color=colour,
                    zorder=4 if machine == "MareNostrum 5" else 3.5,
                )


def add_colourbar(
    fig: plt.Figure, ax: plt.Axes, norm: LogNorm, ticks: tuple[int, ...], label: str
) -> None:
    mappable = plt.cm.ScalarMappable(norm=norm, cmap=VIRIDIS)
    cbar = fig.colorbar(mappable, ax=ax, fraction=0.046, pad=0.025)
    cbar.set_label(label, fontsize=10, labelpad=3)
    cbar.set_ticks(ticks)
    cbar.set_ticklabels([rf"${tick}$" for tick in ticks])
    cbar.ax.tick_params(labelsize=9, width=0.7, length=3, pad=2)
    cbar.ax.minorticks_off()
    cbar.outline.set_linewidth(0.8)


def plot_application_report(
    pts_rows: list[dict[str, str]], drop_rows: list[dict[str, str]], out: Path
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(FIGURE_WIDTH_IN, APPLICATION_HEIGHT_IN))
    draw_application_series(axes[0], pts_rows, "pts", PTS_LEVELS, PTS_NORM, {64: 256})
    draw_application_series(
        axes[1], drop_rows, "ndrops", DROP_LEVELS, DROP_NORM,
        {1: 256, 2: 256, 4: 256, 8: 256, 16: 512, 32: 512},
    )
    for ax, rows, title in (
        (axes[0], pts_rows, r"$(a)$~axisymmetric, uniform mesh"),
        (axes[1], drop_rows, r"$(b)$~planar, $64$ pts$/R$"),
    ):
        values = np.array([float(row["per_step"]) for row in rows])
        ax.set_ylim(values.min() / 1.2, values.max() * 1.3)
        ax.set_title(title, pad=5)
        ax.set_xlabel("MPI ranks", labelpad=3)
        style_log_axes(ax, 2, 1024)
    axes[0].set_ylabel("Wall time / iteration (s)", labelpad=3)
    add_colourbar(fig, axes[0], PTS_NORM, PTS_LEVELS, r"$\mathrm{pts}/R$")
    add_colourbar(fig, axes[1], DROP_NORM, DROP_LEVELS, "drops")
    machine_handles = [
        Line2D([0], [0], ls="none", marker=marker, ms=5, mfc="white", mec="k",
               mew=0.6, label=machine)
        for machine, marker in COMBINED_MARKERS.items()
    ]
    machine_handles.append(Line2D([0], [0], ls="--", lw=1, color="0.25", label="ideal"))
    fig.legend(
        handles=machine_handles, loc="lower center", ncol=3, frameon=False,
        bbox_to_anchor=(0.5, 0.025), handlelength=1.8, columnspacing=1.4,
        handletextpad=0.5,
    )
    fig.subplots_adjust(left=0.1, right=0.94, top=0.93, bottom=0.24, wspace=0.34)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=300, facecolor="white")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, default=REPO / "figures")
    args = parser.parse_args()
    kernel_rows = load_csv(KERNEL_CSV)
    plot_kernel_report(
        kernel_rows, "mpi-laplacian-2d", 14, args.outdir / "circle-L14-report.pdf"
    )
    plot_kernel_report(
        kernel_rows, "mpi-laplacian", 9, args.outdir / "laplacian-L9-report.pdf"
    )
    plot_application_report(
        load_csv(PTS_CSV), load_csv(DROPS_CSV),
        args.outdir / "marangoni-uniform-ndrop-per-iter-report.pdf",
    )
    print(f"wrote three report figures at {FIGURE_WIDTH_IN * 25.4:.0f} mm width")


if __name__ == "__main__":
    main()
