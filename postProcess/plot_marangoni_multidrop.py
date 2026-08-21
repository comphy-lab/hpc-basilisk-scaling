#!/usr/bin/env python3
"""Plot planar multi-drop Marangoni strong scaling."""

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

TIMING_RE = re.compile(
    r"#TIMING npe=(?P<npe>\d+) ndrops=(?P<ndrops>\d+) level=(?P<level>\d+) "
    r"cells=(?P<cells>\d+) steps=(?P<steps>\d+) t=(?P<t>\S+) "
    r"real=(?P<real>\S+) speed=(?P<speed>\S+) u=(?P<u>\S+)"
)
DROP_COLORS = {
    2: "#1A64B3",
    4: "#C44E52",
    8: "#4DAF4A",
    16: "#984EA3",
    32: "#FF7F00",
}
MACHINE_MARKER = {"MareNostrum 5": "o", "Snellius": "P"}


def parse_file(path: Path) -> dict[str, float | int] | None:
    match = None
    for line in path.read_text(errors="replace").splitlines():
        found = TIMING_RE.search(line)
        if found:
            match = found
    if match is None:
        return None
    row = {key: match.group(key) for key in match.groupdict()}
    for key in ("npe", "ndrops", "level", "cells", "steps"):
        row[key] = int(row[key])
    for key in ("t", "real", "speed", "u"):
        row[key] = float(row[key])
    if row["t"] < 0.45:
        return None
    row["source"] = str(path)
    return row


def load_tree(root: Path) -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    for path in sorted(root.rglob("out-*")):
        row = parse_file(path)
        if row is not None:
            rows.append(row)
    return rows


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


def plot_all(rows: list[dict[str, float | int | str]], out: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(24, 10))
    fig.set_facecolor("white")
    ndrops_list = sorted({int(row["ndrops"]) for row in rows})
    machines = sorted({str(row["machine"]) for row in rows})
    for ax, key, ylabel in (
        (axes[0], "real", r"Wall time (s)"),
        (axes[1], "speed", r"Speed (cells/s)"),
    ):
        first_ideal = True
        for ndrops in ndrops_list:
            color = DROP_COLORS.get(ndrops, "0.2")
            for machine in machines:
                picked = [
                    row
                    for row in rows
                    if int(row["ndrops"]) == ndrops and str(row["machine"]) == machine
                ]
                picked.sort(key=lambda row: int(row["npe"]))
                if not picked:
                    continue
                npe = np.array([int(row["npe"]) for row in picked], dtype=float)
                y = np.array([float(row[key]) for row in picked], dtype=float)
                ax.plot(
                    npe,
                    y,
                    linestyle="-" if machine == "MareNostrum 5" else "--",
                    linewidth=3,
                    marker=MACHINE_MARKER[machine],
                    markersize=13,
                    markerfacecolor=color,
                    markeredgecolor="k",
                    color=color,
                    label=rf"{ndrops} drops, {machine}",
                    zorder=4,
                )
                if key == "real" and first_ideal and npe.size >= 2 and y[0] > 0:
                    ax.plot(
                        npe,
                        y[0] * npe[0] / npe,
                        linestyle=":",
                        linewidth=2.4,
                        color="0.35",
                        label=r"ideal",
                        zorder=1,
                    )
                    first_ideal = False
        ax.set_xlabel(r"MPI ranks", fontsize=34, labelpad=12)
        ax.set_ylabel(ylabel, fontsize=34, labelpad=12)
        ax.set_title(r"Planar multi-drop Marangoni, 64 pts$/R$", fontsize=22, pad=12)
        ax.legend(fontsize=13, frameon=False, loc="best", ncol=1)
        style(ax)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight", dpi=300, facecolor="white", pad_inches=0.1)
    plt.close(fig)


def write_csv(rows: list[dict[str, float | int | str]], path: Path) -> None:
    fieldnames = ["machine", "ndrops", "level", "npe", "cells", "steps", "t", "real", "speed", "u"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in sorted(
            rows,
            key=lambda item: (
                str(item.get("machine", "")),
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
    all_rows: list[dict[str, float | int | str]] = []
    mn5 = load_tree(args.results)
    if not mn5:
        raise SystemExit(f"no multi-drop #TIMING rows under {args.results}")
    for row in mn5:
        item = dict(row)
        item["machine"] = "MareNostrum 5"
        all_rows.append(item)
    if args.snellius is not None:
        snellius = load_tree(args.snellius)
        if not snellius:
            raise SystemExit(f"no multi-drop #TIMING rows under {args.snellius}")
        for row in snellius:
            item = dict(row)
            item["machine"] = "Snellius"
            all_rows.append(item)
    write_csv(all_rows, args.outdir / "marangoni-multidrop-timings.csv")
    plot_all(all_rows, args.outdir / "marangoni-multidrop.pdf")
    print(f"plotted {len(all_rows)} timing rows -> {args.outdir}")


if __name__ == "__main__":
    main()
