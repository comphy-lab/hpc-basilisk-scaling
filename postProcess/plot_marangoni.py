#!/usr/bin/env python3
"""Plot stock Marangoni-migration strong scaling on MareNostrum 5 and Snellius."""

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
    r"#TIMING npe=(?P<npe>\d+) level=(?P<level>\d+) cells=(?P<cells>\d+) "
    r"steps=(?P<steps>\d+) t=(?P<t>\S+) real=(?P<real>\S+) "
    r"speed=(?P<speed>\S+) u=(?P<u>\S+)"
)
OUT_RE = re.compile(r"^out-(\d+)-(\d+)$")
MACHINE_STYLE = {
    "MareNostrum 5": {"color": "#1A64B3", "marker": "o", "z": 4},
    "Snellius": {"color": "#4DAF4A", "marker": "P", "z": 3.5},
}


def parse_file(path: Path) -> dict[str, float | int] | None:
    text = path.read_text(errors="replace")
    match = None
    for line in text.splitlines():
        found = TIMING_RE.search(line)
        if found:
            match = found
    if match is None:
        name = OUT_RE.match(path.name)
        if name is None:
            return None
        return None
    return {
        "npe": int(match.group("npe")),
        "level": int(match.group("level")),
        "cells": int(match.group("cells")),
        "steps": int(match.group("steps")),
        "t": float(match.group("t")),
        "real": float(match.group("real")),
        "speed": float(match.group("speed")),
        "u": float(match.group("u")),
        "source": str(path),
    }


def load_tree(root: Path) -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    for path in sorted(root.rglob("out-*")):
        row = parse_file(path)
        if row is not None:
            rows.append(row)
    return rows


def select(rows: list[dict[str, float | int | str]], level: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    picked = [row for row in rows if int(row["level"]) == level]
    picked.sort(key=lambda row: int(row["npe"]))
    npe = np.array([int(row["npe"]) for row in picked], dtype=float)
    real = np.array([float(row["real"]) for row in picked], dtype=float)
    speed = np.array([float(row["speed"]) for row in picked], dtype=float)
    return npe, real, speed


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


def plot_level(
    machines: list[tuple[str, list[dict[str, float | int | str]]]],
    level: int,
    out: Path,
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(24, 10))
    fig.set_facecolor("white")
    pts = 2 ** (level - 4)
    for ax, key, ylabel in (
        (axes[0], "real", r"Wall time (s)"),
        (axes[1], "speed", r"Speed (cells/s)"),
    ):
        drawn = False
        for label, rows in machines:
            npe, real, speed = select(rows, level)
            if npe.size == 0:
                continue
            y = real if key == "real" else speed
            machine_style = MACHINE_STYLE[label]
            ax.plot(
                npe,
                y,
                linestyle="-",
                linewidth=3,
                marker=machine_style["marker"],
                markersize=13,
                markerfacecolor=machine_style["color"],
                markeredgecolor="k",
                color=machine_style["color"],
                label=label,
                zorder=machine_style["z"],
            )
            if key == "real" and npe.size >= 2 and real[0] > 0:
                ax.plot(
                    npe,
                    real[0] * npe[0] / npe,
                    linestyle=":",
                    linewidth=2.4,
                    color="0.35",
                    label=rf"ideal ({label})" if not drawn else None,
                    zorder=1,
                )
                drawn = True
        ax.set_xlabel(r"MPI ranks", fontsize=34, labelpad=12)
        ax.set_ylabel(ylabel, fontsize=34, labelpad=12)
        ax.set_title(
            rf"Marangoni migration, $L={level}$ (${pts}$ pts$/R$)",
            fontsize=22,
            pad=12,
        )
        ax.legend(fontsize=18, frameon=False, loc="best")
        style(ax)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight", dpi=300, facecolor="white", pad_inches=0.1)
    plt.close(fig)


def write_csv(rows: list[dict[str, float | int | str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["machine", "level", "npe", "cells", "steps", "t", "real", "speed", "u"]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in sorted(
            rows,
            key=lambda item: (str(item.get("machine", "")), int(item["level"]), int(item["npe"])),
        ):
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True, help="MareNostrum 5 run tree")
    parser.add_argument("--snellius", type=Path, default=None)
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()
    mn5 = load_tree(args.results)
    if not mn5:
        raise SystemExit(f"no #TIMING rows under {args.results}")
    machines: list[tuple[str, list[dict[str, float | int | str]]]] = [("MareNostrum 5", mn5)]
    all_rows: list[dict[str, float | int | str]] = []
    for row in mn5:
        item = dict(row)
        item["machine"] = "MareNostrum 5"
        all_rows.append(item)
    if args.snellius is not None:
        snellius = load_tree(args.snellius)
        if not snellius:
            raise SystemExit(f"no #TIMING rows under {args.snellius}")
        machines.append(("Snellius", snellius))
        for row in snellius:
            item = dict(row)
            item["machine"] = "Snellius"
            all_rows.append(item)
    write_csv(all_rows, args.outdir / "marangoni-timings.csv")
    levels = sorted({int(row["level"]) for row in all_rows})
    for level in levels:
        plot_level(machines, level, args.outdir / f"marangoni-L{level}.pdf")
    print(f"plotted {len(all_rows)} timing rows -> {args.outdir}")


if __name__ == "__main__":
    main()
