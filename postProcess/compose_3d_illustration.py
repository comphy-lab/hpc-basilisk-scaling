#!/usr/bin/env python3
"""Compose two archived 3D coalescence renders for the scaling report.

The source images are embedded raster objects extracted from the
jumping-drops phenomenology figure.  This script crops only the unused white
header and outer margins; it does not alter the rendered simulation geometry.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Computer Modern Roman"],
    "text.usetex": True,
    "text.latex.preamble": r"\usepackage{amsmath}",
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})

import matplotlib.image as mpimg
import matplotlib.pyplot as plt


REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "figures" / "illustration-data" / "coalescence-3d"
OUTPUT = REPO / "figures" / "three-dimensional-simulation"

# Pixel coordinates in the untouched 1024 x 768 source objects.  The source
# time label lies in the discarded white header and is redrawn legibly below.
CROP = (120, 1020, 150, 735)  # left, right, top, bottom
STATES = (
    (DATA / "state-t1p75.png", r"$t/\tau_\gamma = 1.75$"),
    (DATA / "state-t3p00.png", r"$t/\tau_\gamma = 3.00$"),
)
EXPECTED_SHA256 = {
    "state-t1p75.png": "26d7e3ed32f26b9077cc7cf2f9d960ded3bd626953bcdd69489fd30f82084fe6",
    "state-t3p00.png": "d3330ee16a6c36ef2c91451897c1003e52b62dd362051351d845da023110578d",
}


def cropped_image(path: Path):
    """Load one source object and return its fixed, geometry-preserving crop."""
    if hashlib.sha256(path.read_bytes()).hexdigest() != EXPECTED_SHA256[path.name]:
        raise ValueError(f"source image does not match its labelled state: {path}")
    image = mpimg.imread(path)
    left, right, top, bottom = CROP
    if image.shape[:2] != (768, 1024):
        raise ValueError(f"{path}: expected 1024 x 768 source image, got {image.shape[1]} x {image.shape[0]}")
    return image[top:bottom, left:right]


def main() -> None:
    fig, axes = plt.subplots(2, 1, figsize=(6, 6), facecolor="white")
    fig.subplots_adjust(left=0.025, right=0.975, bottom=0.025, top=0.975, hspace=0.035)

    for ax, (path, time_label) in zip(axes, STATES, strict=True):
        ax.imshow(cropped_image(path), interpolation="none")
        ax.text(
            0.025,
            0.955,
            time_label,
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=13,
            color="black",
        )
        ax.set_axis_off()

    for suffix in ("pdf", "png"):
        fig.savefig(
            OUTPUT.with_suffix(f".{suffix}"),
            dpi=300,
            facecolor="white",
            bbox_inches=None,
        )
    plt.close(fig)


if __name__ == "__main__":
    main()
