#!/usr/bin/env python3
"""Compose four archived 3D coalescence states at the report's final width.

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
    (DATA / "state-t0p24.png", r"$t/\tau_\gamma = 0.24$"),
    (DATA / "state-t1p00.png", r"$t/\tau_\gamma = 1.00$"),
    (DATA / "state-t1p75.png", r"$t/\tau_\gamma = 1.75$"),
    (DATA / "state-t3p00.png", r"$t/\tau_\gamma = 3.00$"),
)
EXPECTED_SHA256 = {
    "state-t0p24.png": "c064582d51a7423d08552fb9f368d9e3b9983010c6145fa8529fde26285d9f35",
    "state-t1p00.png": "1ab8c0bceca7615ce2e0a74af2a30cdb7553fb8a8fb447dc760bf4b5b919f19f",
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
    fig, axes = plt.subplots(2, 2, figsize=(166 / 25.4, 116 / 25.4), facecolor="white")
    fig.subplots_adjust(left=0.02, right=0.98, bottom=0.025, top=0.95, hspace=0.13, wspace=0.04)

    for ax, (path, time_label) in zip(axes.flat, STATES, strict=True):
        ax.imshow(cropped_image(path), interpolation="none")
        ax.set_title(time_label, loc="left", fontsize=10, pad=3)
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
