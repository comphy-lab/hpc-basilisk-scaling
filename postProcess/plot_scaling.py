#!/usr/bin/env python3
"""Plot stock Basilisk kernel timings from MN5 out-LEVEL-NRANKS tables."""

from __future__ import annotations

import argparse
import glob
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

KERNELS = ("refine", "cos", "laplacian", "sum", "restriction", "poisson")


def parse_table(path: Path) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    for raw in path.read_text(errors="replace").splitlines():
        parts = raw.split()
        if len(parts) < 11:
            continue
        try:
            npe = int(parts[0])
            cpu = float(parts[1])
            real = float(parts[2])
            speed = float(parts[3])
        except ValueError:
            continue
        name = parts[4].strip("[]")
        if name not in KERNELS:
            continue
        try:
            comm_min = float(parts[5])
            comm_avg = float(parts[6])
            comm_max = float(parts[7])
            mem = float(parts[9])
        except ValueError:
            continue
        rows.append(
            {
                "npe": npe,
                "cpu": cpu,
                "real": real,
                "speed": speed,
                "name": name,
                "comm_min": comm_min,
                "comm_avg": comm_avg,
                "comm_max": comm_max,
                "mem": mem,
                "source": str(path),
            }
        )
    return rows


def load_results(root: Path) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    for path in sorted(root.rglob("out-*")):
        rows.extend(parse_table(path))
    return rows


def select(rows: list[dict[str, float | str]], kernel: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    picked = [row for row in rows if row["name"] == kernel]
    picked.sort(key=lambda row: int(row["npe"]))
    npe = np.array([int(row["npe"]) for row in picked], dtype=float)
    real = np.array([float(row["real"]) for row in picked], dtype=float)
    comm = np.array([float(row["comm_avg"]) for row in picked], dtype=float)
    return npe, real, comm


def style(ax: plt.Axes) -> None:
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.tick_params(which="both", direction="out", width=3, labelsize=30, pad=10)
    ax.tick_params(which="major", length=12)
    ax.tick_params(which="minor", length=6)
    for spine in ax.spines.values():
        spine.set_linewidth(3)
    ax.minorticks_on()
    ax.set_box_aspect(1)


def plot_kernel(rows: list[dict[str, float | str]], kernel: str, out: Path, title: str) -> None:
    npe, real, comm = select(rows, kernel)
    if npe.size == 0:
        raise SystemExit(f"no rows for kernel {kernel}")
    fig, ax = plt.subplots(figsize=(12, 12))
    ax.plot(npe, real, "o-", lw=3, ms=14, color="C0", label="wall time")
    ax.plot(npe, comm, "s--", lw=3, ms=12, color="C3", label="MPI time")
    if npe.size >= 2 and real[0] > 0:
        ideal = real[0] * npe[0] / npe
        ax.plot(npe, ideal, "k:", lw=2, label="ideal strong scaling")
    ax.set_xlabel(r"MPI ranks", fontsize=40, labelpad=15)
    ax.set_ylabel(r"Time / iteration (s)", fontsize=40, labelpad=15)
    ax.set_title(title, fontsize=28, pad=16)
    ax.legend(fontsize=24, frameon=False)
    style(ax)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight", dpi=300)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()
    rows = load_results(args.results)
    if not rows:
        raise SystemExit(f"no timer rows under {args.results}")
    plot_kernel(rows, "poisson", args.outdir / "poisson-scaling.pdf", "Poisson (stock Basilisk)")
    plot_kernel(rows, "laplacian", args.outdir / "laplacian-scaling.pdf", "Laplacian (stock Basilisk)")
    plot_kernel(
        rows, "restriction", args.outdir / "restriction-scaling.pdf", "Restriction (stock Basilisk)"
    )
    print(f"plotted {len(rows)} timer rows from {args.results} -> {args.outdir}")


if __name__ == "__main__":
    main()
