#!/usr/bin/env python3
"""Compose a chronological elastic Taylor--Culick simulation sequence.

Each snapshot combines the upper half of the velocity panel with the lower
half of the hoop-conformation panel from the same source frame.  The source
workflow renders identical physical windows on either side of the sheet
mid-plane, so this split retains the geometry and the pixels of both fields.
Colour bars reproduce the normalisations in ``VideoTC_vFinal_v2.py``; field
values are neither inferred nor recomputed.
"""

from __future__ import annotations

import argparse
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["font.family"] = "serif"
matplotlib.rcParams["font.serif"] = ["Computer Modern Roman"]
matplotlib.rcParams["axes.unicode_minus"] = False
if os.environ.get("MN5_PLOT_NO_LATEX") == "1":
    matplotlib.rcParams["mathtext.fontset"] = "cm"
else:
    matplotlib.rcParams["text.usetex"] = True
    matplotlib.rcParams["text.latex.preamble"] = r"\usepackage{amsmath}"

import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colorbar import ColorbarBase  # noqa: E402
from matplotlib.colors import Normalize  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "figures" / "illustration-data" / "taylorculick"
DEFAULT_OUTPUT = ROOT / "figures" / "taylorculick-simulation"

# Pixel bounds in every 2262 x 1356 source frame. These are matched 652 x 215
# interiors of the original plotting axes: the same tip-following physical
# window and pixel scale, with titles and spines excluded.
VELOCITY_CROP = (17, 253, 669, 468)
HOOP_CROP = (805, 693, 1457, 908)
SPLIT_ROW = 108


@dataclass(frozen=True)
class SourceFrame:
    path: str
    index: int
    time: float
    sha256: str


SOURCE_FRAMES = (
    SourceFrame(
        "source-frame-case3040-t17p30.png",
        30,
        17.30,
        "1c65153d84eaa49a1b82ea3455686438bc869ba60eb3bbef0f3ce25ed413b0d9",
    ),
    SourceFrame(
        "source-frame-case3040-t53p30.png",
        90,
        53.30,
        "8f5552477879d59a8e868859ef94ff5249a584a6d25dfe59cd7438649626b5f7",
    ),
    SourceFrame(
        "source-frame-case3040-t74p90.png",
        126,
        74.90,
        "2267cfafaec449d0787fddccdbe3c025e29cbc43972df95993884e0d59a842a8",
    ),
    SourceFrame(
        "source-frame-case3040-t119p30.png",
        200,
        119.30,
        "50ebe8591d50027bda6aea9098fbcf8669815bde8f0f3507ebd06d98347f39eb",
    ),
)


def crop(image, bounds: tuple[int, int, int, int]):
    """Return an exact array slice for ``(left, top, right, bottom)``."""
    left, top, right, bottom = bounds
    return image[top:bottom, left:right]


def load_snapshot(source_dir: Path, source: SourceFrame) -> np.ndarray:
    """Validate one source frame and make its upper/lower field split."""
    path = source_dir / source.path
    if hashlib.sha256(path.read_bytes()).hexdigest() != source.sha256:
        raise ValueError(f"{path}: source-frame checksum mismatch")

    frame = mpimg.imread(path)
    if frame.shape[:2] != (1356, 2262):
        raise ValueError(
            f"{path}: expected the verified 2262 x 1356 frame, "
            f"found {frame.shape[1]} x {frame.shape[0]}"
        )

    velocity = crop(frame, VELOCITY_CROP)
    hoop = crop(frame, HOOP_CROP)
    if velocity.shape != hoop.shape or velocity.shape[:2] != (215, 652):
        raise ValueError(f"{path}: field crops no longer share verified bounds")

    return np.concatenate((velocity[:SPLIT_ROW], hoop[SPLIT_ROW:]), axis=0)


def add_snapshot(fig, rect, pixels: np.ndarray, time: float) -> None:
    """Add one equal-aspect split-field snapshot and its physical time."""
    ax = fig.add_axes(rect)
    ax.imshow(pixels, interpolation="nearest", aspect="equal")
    ax.axhline(SPLIT_ROW - 0.5, color="black", linewidth=0.35)
    ax.set_title(rf"$t/t_\gamma={time:.2f}$", fontsize=10, pad=3)
    ax.set_axis_off()


def math_tick(value: float, _position: int) -> str:
    """Format signed decimal ticks inside math mode with a true minus glyph."""
    return rf"${value:.2f}$"


def add_colourbar(fig, rect, cmap: str, limits, ticks, label: str) -> None:
    ax = fig.add_axes(rect)
    bar = ColorbarBase(
        ax,
        cmap=matplotlib.colormaps[cmap],
        norm=Normalize(*limits),
        orientation="horizontal",
        ticks=ticks,
    )
    bar.ax.set_title(label, fontsize=10, pad=4)
    bar.ax.tick_params(labelsize=9, width=0.8, length=3, pad=2)
    bar.formatter = FuncFormatter(math_tick)
    bar.update_ticks()
    bar.outline.set_linewidth(0.8)


def compose(source_dir: Path, output_stem: Path) -> None:
    """Render the four verified times at the fixed 166 mm document width."""
    snapshots = [load_snapshot(source_dir, source) for source in SOURCE_FRAMES]

    width_in = 166.0 / 25.4
    height_in = 90.0 / 25.4
    fig = plt.figure(figsize=(width_in, height_in), facecolor="white")

    panel_width = 0.425
    panel_height = panel_width * width_in / (652.0 / 215.0) / height_in
    positions = (
        (0.050, 0.685),
        (0.525, 0.685),
        (0.050, 0.355),
        (0.525, 0.355),
    )
    for pixels, source, (left, bottom) in zip(
        snapshots, SOURCE_FRAMES, positions, strict=True
    ):
        add_snapshot(
            fig,
            [left, bottom, panel_width, panel_height],
            pixels,
            source.time,
        )

    add_colourbar(
        fig,
        [0.075, 0.165, 0.320, 0.030],
        "Purples",
        (0.0, 0.95),
        (0.0, 0.25, 0.50, 0.75, 0.95),
        r"upper half: $\|\boldsymbol{V}\|/V_{\mathrm{TC}}$",
    )
    add_colourbar(
        fig,
        [0.605, 0.165, 0.320, 0.030],
        "RdBu_r",
        (-0.1, 0.1),
        (-0.1, -0.05, 0.0, 0.05, 0.1),
        r"lower half: $\log(\mathcal{A})_{\theta\theta}$",
    )

    output_stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_stem.with_suffix(".pdf"), dpi=300, facecolor="white")
    fig.savefig(output_stem.with_suffix(".png"), dpi=300, facecolor="white")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=SOURCE_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    compose(args.source_dir, args.output)


if __name__ == "__main__":
    main()
