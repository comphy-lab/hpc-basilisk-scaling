#!/usr/bin/env python3
"""Render the four-frame bursting-bubble velocity and streamline sequence."""

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

SNAPSHOTS = ("0.492500", "0.494219", "0.496719", "0.499844")
FIELD_FILES = {
    snapshot: DATA_DIR / f"snapshot-{snapshot}-fields.npz" for snapshot in SNAPSHOTS
}
INTERFACE_FILES = {
    snapshot: DATA_DIR / f"snapshot-{snapshot}-interface.npz" for snapshot in SNAPSHOTS
}
EXPECTED_SHA256 = {
    "snapshot-0.492500-fields.npz": "55fc4feca838c637bec35292a23ec0785ca88c373e0257fbad3bc2a1ef5cefd2",
    "snapshot-0.492500-interface.npz": "796accf1632ee96f043117d9d18d2a2732e278303efb1ec74084e5320bdafec3",
    "snapshot-0.494219-fields.npz": "b0ca4d5b97e69aa6efb6143c9d6c489616b5799160ae35a6389208c1186d1f2c",
    "snapshot-0.494219-interface.npz": "751283e98e1549b479275a6610467e385538f237b709dd9fe0eb7e02313dbb6b",
    "snapshot-0.496719-fields.npz": "0f15dacf8f1eae4d1732ccd725a3a19e78128f496723f0566e083934488ac361",
    "snapshot-0.496719-interface.npz": "abddfad52c25ca719c4e8866cea6ae8aecbf43f87505de64c6d327e0130d1839",
    "snapshot-0.499844-fields.npz": "c8c4efed9e2dda9aff7110bb9d970de110a65434adb89e1862dde053d326e4d0",
    "snapshot-0.499844-interface.npz": "5a27cb7b1bbb040092f4b2616df7940df074c0c0179e29ac94c977c06e165d7a",
}

RMAX = 0.58
ZMIN = -1.72
ZMAX = -0.82
VMAX = 50.0
FIGURE_WIDTH_MM = 166.0
FIGURE_HEIGHT_MM = 143.0
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
    for path in (*FIELD_FILES.values(), *INTERFACE_FILES.values()):
        expected = EXPECTED_SHA256[path.name]
        if not path.is_file() or sha256(path) != expected:
            raise ValueError(f"missing or checksum-mismatched illustration input: {path}")


def validate_field(field: Field) -> None:
    shape = field.z.shape
    if shape != (294, 190) or any(array.shape != shape for array in field.__dict__.values()):
        raise ValueError("field arrays do not match the archived 294 x 190 grid")
    if not np.all(np.isfinite(field.z)) or not np.all(np.isfinite(field.r)):
        raise ValueError("field coordinates contain non-finite values")
    if not np.all(np.diff(field.z[:, 0]) > 0) or not np.all(np.diff(field.r[0, :]) > 0):
        raise ValueError("field coordinates are not strictly increasing")
    if not np.any(np.isfinite(field.speed)):
        raise ValueError("field velocity contains no finite values")


def load_inputs() -> tuple[list[Field], list[np.ndarray]]:
    verify_inputs()
    fields: list[Field] = []
    interfaces: list[np.ndarray] = []
    for snapshot in SNAPSHOTS:
        with np.load(FIELD_FILES[snapshot]) as payload:
            field = Field(**{name: payload[name] for name in Field.__dataclass_fields__})
        validate_field(field)
        with np.load(INTERFACE_FILES[snapshot]) as payload:
            segments = np.asarray(payload["segments"], dtype=float)
        if segments.ndim != 3 or segments.shape[1:] != (2, 2) or not len(segments):
            raise ValueError(f"interface segments are malformed for {snapshot}")
        if not np.all(np.isfinite(segments)):
            raise ValueError(f"interface segments contain non-finite values for {snapshot}")
        fields.append(field)
        interfaces.append(segments)
    return fields, interfaces


def stream_arrays(field: Field, mirror: bool) -> tuple[np.ndarray, ...]:
    r = field.r[0, :]
    z = field.z[:, 0]
    ur = np.ma.masked_invalid(field.ur)
    uz = np.ma.masked_invalid(field.uz)
    if mirror:
        # x=-r reverses the radial velocity component as well as the coordinate.
        return -r[::-1], z, -ur[:, ::-1], uz[:, ::-1]
    return r, z, ur, uz


def visible_segments(segments: np.ndarray) -> np.ndarray:
    radius = np.max(np.abs(segments[:, :, 0]), axis=1)
    zlow = np.min(segments[:, :, 1], axis=1)
    zhigh = np.max(segments[:, :, 1], axis=1)
    return segments[(radius <= 1.02 * RMAX) & (zhigh >= ZMIN) & (zlow <= ZMAX)]


def draw_frame(
    ax: plt.Axes,
    field: Field,
    segments: np.ndarray,
    snapshot: str,
    norm: Normalize,
    cmap,
) -> None:
    speed = np.ma.masked_invalid(field.speed)
    mirrored_speed = np.ma.concatenate([speed[:, ::-1], speed], axis=1)
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
            linewidth=0.60,
            arrowsize=0.62,
            minlength=0.08,
            maxlength=2.0,
            zorder=2,
        )

    ax.add_collection(
        LineCollection(
            visible_segments(segments),
            colors=INTERFACE_COLOUR,
            linewidths=1.25,
            zorder=4,
        )
    )
    ax.axvline(0, color="0.72", linewidth=0.55, zorder=1)
    ax.set_xlim(-RMAX, RMAX)
    ax.set_ylim(ZMIN, ZMAX)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.text(
        0.04,
        0.94,
        rf"$t^*={snapshot}$",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=10,
        color="black",
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.72, "pad": 1.8},
        zorder=5,
    )


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
    fields, interfaces = load_inputs()
    norm = Normalize(vmin=0.0, vmax=VMAX)
    cmap = plt.get_cmap("Blues").copy()
    cmap.set_bad((1, 1, 1, 0))

    fig = plt.figure(
        figsize=(FIGURE_WIDTH_MM / 25.4, FIGURE_HEIGHT_MM / 25.4),
        facecolor="white",
    )
    panel_width = 0.4475
    panel_height = (
        panel_width
        * (ZMAX - ZMIN)
        / (2.0 * RMAX)
        * FIGURE_WIDTH_MM
        / FIGURE_HEIGHT_MM
    )
    lefts = (0.04, 0.5125)
    panel_bottom = 0.130
    bottoms = (panel_bottom, panel_bottom + panel_height + 0.020)
    for ax_left, ax_bottom, field, segments, snapshot in zip(
        (lefts[0], lefts[1], lefts[0], lefts[1]),
        (bottoms[1], bottoms[1], bottoms[0], bottoms[0]),
        fields,
        interfaces,
        SNAPSHOTS,
    ):
        ax = fig.add_axes([ax_left, ax_bottom, panel_width, panel_height])
        draw_frame(ax, field, segments, snapshot, norm, cmap)

    cax = fig.add_axes([0.22, 0.090, 0.56, 0.030])
    colourbar = fig.colorbar(
        ScalarMappable(norm=norm, cmap=cmap),
        cax=cax,
        orientation="horizontal",
        extend="max",
    )
    colourbar.set_label(r"$|\mathbf{u}|/V_c$", fontsize=10, labelpad=3)
    colourbar.set_ticks([0, 10, 20, 30, 40, 50])
    colourbar.ax.tick_params(labelsize=9, length=3, width=0.6, pad=2)
    colourbar.outline.set_linewidth(0.6)

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
