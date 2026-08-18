#!/usr/bin/env python3
"""Plot MN5 stock Basilisk timings with official Curie/Occigen overlays."""

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

KERNELS = ("refine", "cos", "laplacian", "sum", "restriction", "poisson")
OUT_RE = re.compile(r"^out-(\d+)-(\d+)$")
REPO = Path(__file__).resolve().parents[1]
OFFICIAL_ROOTS = {
    "mpi-circle": REPO / "reference" / "curie",
    "mpi-laplacian": REPO / "reference" / "occigen-3D",
    "mpi-laplacian-2d": REPO / "reference" / "curie",
}
OFFICIAL_LABEL = {
    "mpi-circle": "Curie",
    "mpi-laplacian": "Occigen",
    "mpi-laplacian-2d": "Curie",
}


def parse_table(path: Path, test: str) -> list[dict[str, float | str | int]]:
    match = OUT_RE.match(path.name)
    if match is None:
        return []
    level = int(match.group(1))
    npe_from_name = int(match.group(2))
    rows: list[dict[str, float | str | int]] = []
    for raw in path.read_text(errors="replace").splitlines():
        parts = raw.split()
        if len(parts) < 11:
            continue
        try:
            npe = int(parts[0])
            real = float(parts[2])
            speed = float(parts[3])
        except ValueError:
            continue
        name = parts[4].strip("[]")
        if name not in KERNELS:
            continue
        try:
            comm_avg = float(parts[6])
        except ValueError:
            continue
        if npe != npe_from_name:
            continue
        rows.append(
            {
                "test": test,
                "level": level,
                "npe": npe,
                "real": real,
                "speed": speed,
                "name": name,
                "comm_avg": comm_avg,
                "source": str(path),
            }
        )
    return rows


def load_results(root: Path, test: str | None = None) -> list[dict[str, float | str | int]]:
    rows: list[dict[str, float | str | int]] = []
    for path in sorted(root.rglob("out-*")):
        inferred = test
        if inferred is None:
            parent = path.parent.name
            inferred = parent if parent in OFFICIAL_ROOTS else parent
        rows.extend(parse_table(path, inferred))
    return rows


def select(
    rows: list[dict[str, float | str | int]],
    *,
    test: str,
    level: int,
    kernel: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    picked = [
        row
        for row in rows
        if row["test"] == test and int(row["level"]) == level and row["name"] == kernel
    ]
    picked.sort(key=lambda row: int(row["npe"]))
    npe = np.array([int(row["npe"]) for row in picked], dtype=float)
    real = np.array([float(row["real"]) for row in picked], dtype=float)
    comm = np.array([float(row["comm_avg"]) for row in picked], dtype=float)
    return npe, real, comm


def style(ax: plt.Axes) -> None:
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.tick_params(which="both", direction="out", width=3, labelsize=28, pad=10)
    ax.tick_params(which="major", length=12)
    ax.tick_params(which="minor", length=6)
    for spine in ax.spines.values():
        spine.set_linewidth(3)
    ax.minorticks_on()
    ax.set_box_aspect(1)


def draw_kernel(
    ax: plt.Axes,
    npe: np.ndarray,
    real: np.ndarray,
    comm: np.ndarray,
    title: str,
    official: tuple[str, int, np.ndarray, np.ndarray, np.ndarray] | None,
) -> None:
    ax.plot(
        npe,
        real,
        linestyle="-",
        linewidth=3,
        marker="o",
        markersize=13,
        markerfacecolor="#1A64B3",
        markeredgecolor="k",
        color="#1A64B3",
        label="MareNostrum 5 wall",
        zorder=4,
    )
    ax.plot(
        npe,
        comm,
        linestyle="--",
        linewidth=2.5,
        marker="s",
        markersize=9,
        markerfacecolor="#C44E52",
        markeredgecolor="k",
        color="#C44E52",
        label="MareNostrum 5 MPI",
        zorder=3,
    )
    if official is not None:
        olabel, _olevel, onpe, oreal, ocomm = official
        if onpe.size:
            ax.plot(
                onpe,
                oreal,
                linestyle="-",
                linewidth=2.2,
                marker="D",
                markersize=8,
                markerfacecolor="none",
                markeredgecolor="#FC8D59",
                markeredgewidth=2,
                color="#FC8D59",
                label=rf"{olabel} wall",
                zorder=2,
            )
            ax.plot(
                onpe,
                ocomm,
                linestyle="--",
                linewidth=2,
                marker="^",
                markersize=7,
                markerfacecolor="none",
                markeredgecolor="#8C564B",
                markeredgewidth=1.6,
                color="#8C564B",
                label=rf"{olabel} MPI",
                zorder=2,
            )
    if npe.size >= 2 and real[0] > 0:
        ax.plot(
            npe,
            real[0] * npe[0] / npe,
            linestyle=":",
            linewidth=2.4,
            color="0.35",
            label="ideal (MareNostrum 5)",
            zorder=1,
        )
    ax.set_xlabel(r"MPI ranks", fontsize=34, labelpad=12)
    ax.set_ylabel(r"Time / iteration (s)", fontsize=34, labelpad=12)
    ax.set_title(title, fontsize=22, pad=12)
    ax.legend(fontsize=15, frameon=False, loc="best")
    style(ax)


def official_series(
    test: str,
    mn5_level: int,
    kernel: str,
) -> tuple[str, int, np.ndarray, np.ndarray, np.ndarray] | None:
    root = OFFICIAL_ROOTS.get(test)
    if root is None or not root.is_dir():
        return None
    level = mn5_level
    rows = load_results(root, test=test)
    npe, real, comm = select(rows, test=test, level=level, kernel=kernel)
    if npe.size == 0:
        return None
    return OFFICIAL_LABEL[test], level, npe, real, comm


def plot_pair(
    rows: list[dict[str, float | str | int]],
    *,
    test: str,
    level: int,
    out: Path,
    heading: str,
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(24, 10))
    fig.set_facecolor("white")
    for ax, kernel, label in (
        (axes[0], "poisson", "Poisson"),
        (axes[1], "laplacian", "Laplacian"),
    ):
        npe, real, comm = select(rows, test=test, level=level, kernel=kernel)
        if npe.size == 0:
            raise SystemExit(f"no rows for {test} level {level} {kernel}")
        draw_kernel(
            ax,
            npe,
            real,
            comm,
            rf"{label}, {heading}",
            official_series(test, level, kernel),
        )
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight", dpi=300, facecolor="white")
    plt.close(fig)


def write_csv(rows: list[dict[str, float | str | int]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["test", "level", "name", "npe", "real", "comm_avg", "speed"]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in sorted(
            rows,
            key=lambda item: (
                str(item["test"]),
                int(item["level"]),
                str(item["name"]),
                int(item["npe"]),
            ),
        ):
            writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()
    rows = load_results(args.results)
    if not rows:
        raise SystemExit(f"no timer rows under {args.results}")
    write_csv(rows, args.outdir / "mn5-kernel-timings.csv")
    series = (
        ("mpi-laplacian", 9, "laplacian-L9.pdf", r"stock mpi-laplacian, octree $L=9$"),
        ("mpi-laplacian-2d", 14, "circle-L14.pdf", r"2D full quadtree $L=14$ (Curie comparison)"),
        ("mpi-laplacian-2d", 12, "circle-L12.pdf", r"2D full quadtree $L=12$ (Curie comparison)"),
        ("mpi-laplacian", 8, "laplacian-L8.pdf", r"stock mpi-laplacian, octree $L=8$"),
    )
    for test, level, filename, heading in series:
        npe, _, _ = select(rows, test=test, level=level, kernel="poisson")
        if npe.size == 0:
            continue
        plot_pair(rows, test=test, level=level, out=args.outdir / filename, heading=heading)
    print(f"plotted {len(rows)} timer rows from {args.results} -> {args.outdir}")


if __name__ == "__main__":
    main()
