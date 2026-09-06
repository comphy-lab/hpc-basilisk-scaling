#!/usr/bin/env python3
"""Render the bursting-bubble velocity and streamline illustration."""

from __future__ import annotations

import argparse
import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.cm import ScalarMappable
from matplotlib.collections import LineCollection
from matplotlib.colors import Normalize


REPO = Path(__file__).resolve().parents[1]
DATA_DIR = REPO / "figures" / "illustration-data" / "bursting"
DEFAULT_OUTPUT = REPO / "figures" / "bursting-simulation.pdf"
FIELD_FILE = DATA_DIR / "snapshot-0.496719-fields.npz"
INTERFACE_FILE = DATA_DIR / "snapshot-0.496719-interface.npz"

EXPECTED_SHA256 = {
    FIELD_FILE.name: "0f15dacf8f1eae4d1732ccd725a3a19e78128f496723f0566e083934488ac361",
    INTERFACE_FILE.name: "abddfad52c25ca719c4e8866cea6ae8aecbf43f87505de64c6d327e0130d1839",
}

RMAX = 0.58
ZMIN = -1.72
ZMAX = -0.82
VMAX = 50.0
INTERFACE_COLOUR = "#D55E00"


@dataclass(frozen=True)
class Field:
    z: np.ndarray
    r: np.ndarray
    f: np.ndarray
    uz: np.ndarray
    ur: np.ndarray
    speed: np.ndarray


def configure_matplotlib(use_tex: bool) -> None:
    matplotlib.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Computer Modern Roman", "DejaVu Serif"],
            "mathtext.fontset": "cm",
            "text.usetex": use_tex,
            "text.latex.preamble": r"\usepackage{amsmath}",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "axes.unicode_minus": False,
        }
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_inputs() -> None:
    for path in (FIELD_FILE, INTERFACE_FILE):
        expected = EXPECTED_SHA256[path.name]
        if not path.is_file() or sha256(path) != expected:
            raise ValueError(f"missing or checksum-mismatched illustration input: {path}")


def load_inputs() -> tuple[Field, np.ndarray]:
    verify_inputs()
    with np.load(FIELD_FILE) as payload:
        field = Field(**{name: payload[name] for name in Field.__dataclass_fields__})
    shape = field.z.shape
    if shape != (294, 190) or any(array.shape != shape for array in field.__dict__.values()):
        raise ValueError("field arrays do not match the archived 294 x 190 grid")
    if not np.all(np.diff(field.z[:, 0]) > 0) or not np.all(np.diff(field.r[0, :]) > 0):
        raise ValueError("field coordinates are not strictly increasing")
    with np.load(INTERFACE_FILE) as payload:
        segments = np.asarray(payload["segments"], dtype=float)
    if segments.ndim != 3 or segments.shape[1:] != (2, 2) or not np.all(np.isfinite(segments)):
        raise ValueError("interface segments are malformed")
    return field, segments


def stream_arrays(field: Field, mirror: bool) -> tuple[np.ndarray, ...]:
    r = field.r[0, :]
    z = field.z[:, 0]
    ur = np.ma.masked_invalid(field.ur)
    uz = np.ma.masked_invalid(field.uz)
    if mirror:
        return -r[::-1], z, -ur[:, ::-1], uz[:, ::-1]
    return r, z, ur, uz


def visible_segments(segments: np.ndarray) -> np.ndarray:
    radius = np.max(np.abs(segments[:, :, 0]), axis=1)
    zlow = np.min(segments[:, :, 1], axis=1)
    zhigh = np.max(segments[:, :, 1], axis=1)
    return segments[(radius <= 1.02 * RMAX) & (zhigh >= ZMIN) & (zlow <= ZMAX)]


def atomic_save(fig: plt.Figure, output: Path) -> tuple[Path, Path]:
    output = output.resolve()
    png = output.with_suffix(".png")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary: list[tuple[Path, Path]] = []
    try:
        for target in (output, png):
            descriptor, name = tempfile.mkstemp(
                prefix=f".{target.stem}.", suffix=target.suffix, dir=target.parent
            )
            os.close(descriptor)
            temp = Path(name)
            fig.savefig(
                temp,
                format=target.suffix.lstrip("."),
                dpi=300,
                facecolor="white",
                transparent=False,
            )
            if temp.stat().st_size == 0:
                raise RuntimeError(f"empty render: {target}")
            temporary.append((temp, target))
        for temp, target in temporary:
            os.replace(temp, target)
            target.chmod(0o644)
    finally:
        for temp, _target in temporary:
            temp.unlink(missing_ok=True)
    return output, png


def render(output: Path, use_tex: bool) -> tuple[Path, Path]:
    configure_matplotlib(use_tex)
    field, segments = load_inputs()

    speed = np.ma.masked_invalid(field.speed)
    mirrored_speed = np.ma.concatenate([speed[:, ::-1], speed], axis=1)
    norm = Normalize(vmin=0.0, vmax=VMAX)
    cmap = plt.get_cmap("Blues").copy()
    cmap.set_bad((1, 1, 1, 0))

    fig = plt.figure(figsize=(6.0, 6.0), facecolor="white")
    ax = fig.add_axes([0.03, 0.19, 0.94, 0.75])
    ax.imshow(
        mirrored_speed,
        origin="lower",
        extent=[-RMAX, RMAX, ZMIN, ZMAX],
        cmap=cmap,
        norm=norm,
        interpolation="bilinear",
        rasterized=True,
        zorder=0,
    )

    for mirror in (True, False):
        radial, axial, u_radial, u_axial = stream_arrays(field, mirror)
        ax.streamplot(
            radial,
            axial,
            u_radial,
            u_axial,
            color="#6f6f6f",
            density=0.62,
            linewidth=0.9,
            arrowsize=0.75,
            minlength=0.08,
            maxlength=2.0,
            zorder=2,
        )

    ax.add_collection(
        LineCollection(
            visible_segments(segments),
            colors=INTERFACE_COLOUR,
            linewidths=2.2,
            zorder=4,
        )
    )
    ax.axvline(0, color="0.72", linewidth=0.8, zorder=1)
    ax.set_xlim(-RMAX, RMAX)
    ax.set_ylim(ZMIN, ZMAX)
    ax.set_aspect("equal")
    ax.axis("off")

    cax = fig.add_axes([0.20, 0.12, 0.60, 0.045])
    colourbar = fig.colorbar(ScalarMappable(norm=norm, cmap=cmap), cax=cax,
                            orientation="horizontal", extend="max")
    colourbar.set_label(r"$|\mathbf{u}|/V_c$", fontsize=16, labelpad=4)
    colourbar.set_ticks([0, 10, 20, 30, 40, 50])
    colourbar.ax.tick_params(labelsize=14, length=5, width=0.8, pad=3)
    colourbar.outline.set_linewidth(0.8)

    outputs = atomic_save(fig, output)
    plt.close(fig)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--no-tex", action="store_true")
    args = parser.parse_args()
    for path in render(args.output, use_tex=not args.no_tex):
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
