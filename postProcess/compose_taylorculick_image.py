#!/usr/bin/env python3
"""Compose the representative elastic Taylor--Culick simulation image.

The stored source frame is an unmodified frame from the established
axisymmetric Taylor--Culick rendering workflow.  This script crops its
velocity and hoop-conformation panels, then restores the colour bars from the
normalisations in ``VideoTC_vFinal_v2.py``.  It does not infer or recompute any
field values.
"""

from __future__ import annotations

import argparse
import hashlib
import os
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
from matplotlib.colorbar import ColorbarBase  # noqa: E402
from matplotlib.colors import Normalize  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = (
    ROOT
    / "figures"
    / "illustration-data"
    / "taylorculick"
    / "source-frame-case3040-t74p90.png"
)
DEFAULT_OUTPUT = ROOT / "figures" / "taylorculick-simulation"

# Pixel bounds in the 2262 x 1356 source frame.  These are matched 652 x 215
# interiors of the original plotting axes: the same tip-following physical
# window and the same pixel scale for both fields, with titles and spines
# excluded.
VELOCITY_CROP = (17, 253, 669, 468)
HOOP_CROP = (805, 693, 1457, 908)


def crop(image, bounds: tuple[int, int, int, int]):
    """Return an exact array slice for ``(left, top, right, bottom)``."""
    left, top, right, bottom = bounds
    return image[top:bottom, left:right]


def add_field_panel(fig, rect, pixels, title: str) -> None:
    ax = fig.add_axes(rect)
    ax.imshow(pixels, interpolation="nearest", aspect="equal")
    ax.set_title(title, fontsize=18, pad=6)
    ax.set_axis_off()


def add_colourbar(fig, rect, cmap: str, limits, ticks) -> None:
    ax = fig.add_axes(rect)
    bar = ColorbarBase(
        ax,
        cmap=matplotlib.colormaps[cmap],
        norm=Normalize(*limits),
        orientation="horizontal",
        ticks=ticks,
    )
    bar.ax.tick_params(labelsize=12, width=1.2, length=5, pad=3)
    bar.formatter = matplotlib.ticker.FormatStrFormatter(r"$%.2f$")
    bar.update_ticks()
    bar.outline.set_linewidth(1.2)


def compose(source: Path, output_stem: Path) -> None:
    expected = "2267cfafaec449d0787fddccdbe3c025e29cbc43972df95993884e0d59a842a8"
    if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
        raise ValueError("source frame does not match case 3040 at t/t_gamma=74.90")
    frame = mpimg.imread(source)
    if frame.shape[:2] != (1356, 2262):
        raise ValueError(
            f"{source}: expected the verified 2262 x 1356 frame, "
            f"found {frame.shape[1]} x {frame.shape[0]}"
        )

    velocity = crop(frame, VELOCITY_CROP)
    hoop = crop(frame, HOOP_CROP)

    fig = plt.figure(figsize=(6.0, 6.0), facecolor="white")
    fig.text(0.92, 0.955, r"$t/t_\gamma=74.90$", ha="right", va="top", fontsize=15)

    add_field_panel(fig, [0.07, 0.620, 0.86, 0.284], velocity,
                    r"$\|\boldsymbol{V}\|/V_{\mathrm{TC}}$")
    add_colourbar(
        fig,
        [0.12, 0.585, 0.76, 0.030],
        "Purples",
        (0.0, 0.95),
        (0.0, 0.25, 0.50, 0.75, 0.95),
    )

    add_field_panel(fig, [0.07, 0.170, 0.86, 0.284], hoop,
                    r"$\log(\mathcal{A})_{\theta\theta}$")
    add_colourbar(
        fig,
        [0.12, 0.080, 0.76, 0.030],
        "RdBu_r",
        (-0.1, 0.1),
        (-0.1, -0.05, 0.0, 0.05, 0.1),
    )

    output_stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_stem.with_suffix(".pdf"), dpi=300, facecolor="white")
    fig.savefig(output_stem.with_suffix(".png"), dpi=300, facecolor="white")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    compose(args.source, args.output)


if __name__ == "__main__":
    main()
