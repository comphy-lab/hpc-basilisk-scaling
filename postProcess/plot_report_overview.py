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

from scaling_guides import add_corner_guides, ideal_legend_handle

REPO = Path(__file__).resolve().parents[1]
FIGURE_WIDTH_MM = 166.0
KERNEL_HEIGHT_MM = 185.0
APPLICATION_HEIGHT_MM = 80.0
FIGURE_WIDTH_IN = FIGURE_WIDTH_MM / 25.4
KERNEL_HEIGHT_IN = KERNEL_HEIGHT_MM / 25.4
APPLICATION_HEIGHT_IN = APPLICATION_HEIGHT_MM / 25.4
KERNEL_AXES_SIDE_MM = 60.0
KERNEL_AXES_LEFT_MM = 16.0
KERNEL_AXES_BOTTOM_MM = 32.0
KERNEL_ROW_PITCH_MM = 82.0
KERNEL_AXES_GAP_MM = 14.0
APPLICATION_AXES_SIDE_MM = 50.0
APPLICATION_AXES_LEFT_MM = 17.0
APPLICATION_AXES_BOTTOM_MM = 20.0
COLOURBAR_WIDTH_MM = 2.5
COLOURBAR_PAD_MM = 4.0
APPLICATION_PANEL_GAP_MM = 23.0
KERNEL_CSV = REPO / "figures" / "kernel-timings.csv"
PTS_CSV = REPO / "figures" / "marangoni-uniform-per-iter-timings.csv"
DROPS_CSV = REPO / "figures" / "planar-ndrop-timings.csv"

MACHINE_STYLE = {
    "MareNostrum 5": {"marker": "o", "zorder": 4},
    "Snellius": {"marker": "D", "zorder": 3.5},
}
LEVEL_COLOURS = {
    14: {"wall": "#08519c", "mpi": "#4292c6"},
    9: {"wall": "#a50f15", "mpi": "#e57373"},
}
REFERENCE_MARKERS = {"Curie": "^", "Occigen": "s"}
KERNEL_ROWS = (("mpi-laplacian-2d", 14), ("mpi-laplacian", 9))
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


def add_square_axes(
    fig: plt.Figure,
    left_mm: float,
    bottom_mm: float,
    side_mm: float,
    figure_height_mm: float,
) -> plt.Axes:
    """Place a square plot box at fixed physical coordinates on the canvas."""
    ax = fig.add_axes(
        [
            left_mm / FIGURE_WIDTH_MM,
            bottom_mm / figure_height_mm,
            side_mm / FIGURE_WIDTH_MM,
            side_mm / figure_height_mm,
        ]
    )
    ax.set_box_aspect(1)
    return ax


def add_colourbar_axes(
    fig: plt.Figure,
    left_mm: float,
    bottom_mm: float,
    height_mm: float,
    figure_height_mm: float,
) -> plt.Axes:
    """Place a colourbar independently so it cannot resize a plot box."""
    return fig.add_axes(
        [
            left_mm / FIGURE_WIDTH_MM,
            bottom_mm / figure_height_mm,
            COLOURBAR_WIDTH_MM / FIGURE_WIDTH_MM,
            height_mm / figure_height_mm,
        ]
    )


def assert_square_axes(fig: plt.Figure, axes: list[plt.Axes]) -> None:
    """Check the rendered plot boxes, excluding separately placed colourbars."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    for index, ax in enumerate(axes):
        bbox = ax.get_window_extent(renderer=renderer)
        ratio = bbox.width / bbox.height
        if abs(ratio - 1.0) > 1e-6:
            raise AssertionError(
                f"plot axis {index} is not square: {bbox.width:.12g} / "
                f"{bbox.height:.12g} = {ratio:.12g}"
            )


def save_report_figure(fig: plt.Figure, axes: list[plt.Axes], out: Path) -> None:
    """Validate and save a fixed-size PDF plus an ignored inspection PNG."""
    assert_square_axes(fig, axes)
    out.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "Creator": "postProcess/plot_report_overview.py",
        "CreationDate": None,
        "ModDate": None,
    }
    fig.savefig(out, dpi=300, facecolor="white", metadata=metadata)
    fig.savefig(out.with_suffix(".png"), dpi=300, facecolor="white")
    plt.close(fig)


def draw_kernel_series(
    ax: plt.Axes,
    npe: np.ndarray,
    wall: np.ndarray,
    mpi: np.ndarray,
    *,
    level: int,
    machine: str,
    marker: str,
    filled: bool,
    zorder: float,
) -> None:
    """Keep machine symbols fixed while colour encodes level and timing type."""
    for metric, time in (("wall", wall), ("mpi", mpi)):
        colour = LEVEL_COLOURS[level][metric]
        ax.plot(
            npe, time, "-", lw=1.1, marker=marker, ms=4.0,
            mfc=colour if filled else "none",
            mec="k" if filled else colour, mew=0.45 if filled else 0.85,
            color=colour, zorder=zorder if metric == "wall" else zorder - 0.25,
            label=f"{machine} {metric}",
        )


def kernel_legend(fig: plt.Figure) -> None:
    """One shared legend: level/timing shades above the machine symbols."""
    colour_handles = [
        Line2D([0], [0], color=LEVEL_COLOURS[level][metric], lw=1.4,
               label=rf"$L={level}$, {label}")
        for level in (14, 9)
        for metric, label in (("wall", "wall"), ("mpi", "MPI"))
    ]
    machine_handles = [
        Line2D([0], [0], ls="none", marker=marker, ms=5,
               mfc="0.6" if filled else "none", mec="k", mew=0.7, label=machine)
        for machine, marker, filled in (
            ("MareNostrum 5", "o", True), ("Snellius", "D", True),
            ("Curie", "^", False), ("Occigen", "s", False),
        )
    ]
    # Matplotlib fills legend columns from top to bottom. Interleaving creates
    # a colour row and a symbol row without repeating a legend in each panel.
    handles = [handle for pair in zip(colour_handles, machine_handles) for handle in pair]
    handles.extend((
        Line2D([], [], ls="none", label=""),
        ideal_legend_handle(),
    ))
    fig.legend(
        handles=handles, loc="lower center", ncol=5, frameon=False,
        bbox_to_anchor=(0.5, 0.025), handlelength=1.6, columnspacing=1.0,
        handletextpad=0.5, labelspacing=0.6,
    )


def plot_kernel_comparison(rows: list[dict[str, str]], out: Path) -> None:
    """Compare both dimensions and operators on four square plot boxes."""
    fig = plt.figure(figsize=(FIGURE_WIDTH_IN, KERNEL_HEIGHT_IN), facecolor="white")
    axes = []
    for row_index, (test, level) in enumerate(KERNEL_ROWS):
        for column, kernel in enumerate(("poisson", "laplacian")):
            ax = add_square_axes(
                fig,
                KERNEL_AXES_LEFT_MM + column * (KERNEL_AXES_SIDE_MM + KERNEL_AXES_GAP_MM),
                KERNEL_AXES_BOTTOM_MM + (1 - row_index) * KERNEL_ROW_PITCH_MM,
                KERNEL_AXES_SIDE_MM, KERNEL_HEIGHT_MM,
            )
            axes.append(ax)
            ranks = []
            for machine, spec in MACHINE_STYLE.items():
                npe, wall, mpi = select_kernel(rows, machine, test, level, kernel)
                if not npe.size:
                    raise ValueError(f"missing {machine} {test} L={level} {kernel}")
                ranks.extend(npe.astype(int))
                draw_kernel_series(
                    ax, npe, wall, mpi, level=level, machine=machine,
                    marker=spec["marker"], filled=True, zorder=spec["zorder"],
                )
            reference = REFERENCE_LABEL[test]
            npe, wall, mpi = select_reference(test, level, kernel)
            if not npe.size:
                raise ValueError(f"missing {reference} {test} L={level} {kernel}")
            ranks.extend(npe.astype(int))
            draw_kernel_series(
                ax, npe, wall, mpi, level=level, machine=reference,
                marker=REFERENCE_MARKERS[reference], filled=False, zorder=2,
            )
            panel = "abcd"[2 * row_index + column]
            ax.set_title(rf"$({panel})$ {kernel.capitalize()}, $L={level}$", pad=5)
            ax.set_xlabel("MPI ranks", labelpad=3)
            ax.set_ylabel("Time / iteration (s)", labelpad=3)
            style_log_axes(ax, min(ranks), max(ranks))
            add_corner_guides(ax)
    kernel_legend(fig)
    save_report_figure(fig, axes, out)


def draw_application_series(
    ax: plt.Axes,
    rows: list[dict[str, str]],
    key: str,
    levels: tuple[int, ...],
    norm: LogNorm,
) -> None:
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
    fig: plt.Figure, cax: plt.Axes, norm: LogNorm, ticks: tuple[int, ...], label: str
) -> None:
    mappable = plt.cm.ScalarMappable(norm=norm, cmap=VIRIDIS)
    mappable.set_array([])
    cbar = fig.colorbar(mappable, cax=cax)
    cbar.set_label(label, fontsize=10, labelpad=3)
    cbar.set_ticks(ticks)
    cbar.set_ticklabels([rf"${tick}$" for tick in ticks])
    cbar.ax.tick_params(labelsize=9, width=0.7, length=3, pad=2)
    cbar.ax.minorticks_off()
    cbar.outline.set_linewidth(0.8)


def plot_application_report(
    pts_rows: list[dict[str, str]], drop_rows: list[dict[str, str]], out: Path
) -> None:
    fig = plt.figure(
        figsize=(FIGURE_WIDTH_IN, APPLICATION_HEIGHT_IN), facecolor="white"
    )
    axes = [
        add_square_axes(
            fig,
            APPLICATION_AXES_LEFT_MM,
            APPLICATION_AXES_BOTTOM_MM,
            APPLICATION_AXES_SIDE_MM,
            APPLICATION_HEIGHT_MM,
        ),
        add_square_axes(
            fig,
            APPLICATION_AXES_LEFT_MM
            + APPLICATION_AXES_SIDE_MM
            + COLOURBAR_PAD_MM
            + COLOURBAR_WIDTH_MM
            + APPLICATION_PANEL_GAP_MM,
            APPLICATION_AXES_BOTTOM_MM,
            APPLICATION_AXES_SIDE_MM,
            APPLICATION_HEIGHT_MM,
        ),
    ]
    draw_application_series(axes[0], pts_rows, "pts", PTS_LEVELS, PTS_NORM)
    draw_application_series(
        axes[1], drop_rows, "ndrops", DROP_LEVELS, DROP_NORM,
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
        add_corner_guides(ax)
    axes[0].set_ylabel("Wall time / iteration (s)", labelpad=3)
    colourbar0 = add_colourbar_axes(
        fig,
        APPLICATION_AXES_LEFT_MM + APPLICATION_AXES_SIDE_MM + COLOURBAR_PAD_MM,
        APPLICATION_AXES_BOTTOM_MM,
        APPLICATION_AXES_SIDE_MM,
        APPLICATION_HEIGHT_MM,
    )
    colourbar1 = add_colourbar_axes(
        fig,
        APPLICATION_AXES_LEFT_MM
        + APPLICATION_AXES_SIDE_MM
        + COLOURBAR_PAD_MM
        + COLOURBAR_WIDTH_MM
        + APPLICATION_PANEL_GAP_MM
        + APPLICATION_AXES_SIDE_MM
        + COLOURBAR_PAD_MM,
        APPLICATION_AXES_BOTTOM_MM,
        APPLICATION_AXES_SIDE_MM,
        APPLICATION_HEIGHT_MM,
    )
    add_colourbar(fig, colourbar0, PTS_NORM, PTS_LEVELS, r"$\mathrm{pts}/R$")
    add_colourbar(fig, colourbar1, DROP_NORM, DROP_LEVELS, "drops")
    machine_handles = [
        Line2D([0], [0], ls="none", marker=marker, ms=5, mfc="white", mec="k",
               mew=0.6, label=machine)
        for machine, marker in COMBINED_MARKERS.items()
    ]
    machine_handles.append(ideal_legend_handle())
    fig.legend(
        handles=machine_handles, loc="lower center", ncol=3, frameon=False,
        bbox_to_anchor=(0.5, 0.025), handlelength=1.8, columnspacing=1.4,
        handletextpad=0.5,
    )
    save_report_figure(fig, axes, out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, default=REPO / "figures")
    args = parser.parse_args()
    kernel_rows = load_csv(KERNEL_CSV)
    plot_kernel_comparison(kernel_rows, args.outdir / "kernel-scaling-combined-report.pdf")
    plot_application_report(
        load_csv(PTS_CSV), load_csv(DROPS_CSV),
        args.outdir / "marangoni-uniform-ndrop-per-iter-report.pdf",
    )
    print(f"wrote two report figures at {FIGURE_WIDTH_IN * 25.4:.0f} mm width")


if __name__ == "__main__":
    main()
