#!/usr/bin/env python3
"""Render the Newtonian drop-impact velocity and streamline illustration."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
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
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = REPO / "figures" / "illustration-data" / "drop-impact"
DEFAULT_OUTPUT = REPO / "figures" / "drop-impact-simulation.pdf"
FIELD_FILE = DATA_DIR / "snapshot-0.4400-fields.npz"
INTERFACE_FILE = DATA_DIR / "snapshot-0.4400-interface.npz"
RAW_SHA256 = {
    "snapshot-0.4400": "7afe334e444183a244d348e456de945baaa0ad908b7c05ec6d3fe2475624f7df",
}
COMPACT_SHA256 = {
    FIELD_FILE.name: "7a51c4d463bf2642fba6c657550df84acf17a95d7ec487eab1f5ddb4a9c2379c",
    INTERFACE_FILE.name: "baf5dee1ca8cf28b06fcf75c77cb7d3426b65584e374b04edf776ecb1ce44515",
}

ZMIN = 0.0
ZMAX = 1.7
RMAX = 1.25
NR = 320
VMIN = 0.0
VMAX = 1.0
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


def compile_extractor(build_dir: Path) -> Path:
    qcc = shutil.which("qcc")
    if qcc is None:
        raise RuntimeError("qcc was not found; source the project .project_config")
    lock = REPO / "basilisk" / ".comphy-lock"
    expected_qcc = REPO / "basilisk" / "src" / "qcc"
    if (Path(qcc).resolve() != expected_qcc.resolve() or not lock.is_file()
            or "ref=v2026-07-20" not in lock.read_text().splitlines()):
        raise RuntimeError("raw extraction requires the project-pinned Basilisk v2026-07-20")
    source = SCRIPT_DIR / "extract_drop_image.c"
    local_source = build_dir / source.name
    shutil.copy2(source, local_source)
    executable = build_dir / "extract_drop_image"
    subprocess.run(
        [qcc, "-O2", "-Wall", "-disable-dimensions", source.name,
         "-o", executable.name, "-lm"],
        cwd=build_dir,
        check=True,
    )
    return executable


def parse_facets(text: str) -> np.ndarray:
    segments: list[list[tuple[float, float]]] = []
    pair: list[tuple[float, float]] = []
    for line in text.splitlines():
        values = line.split()
        if len(values) == 2:
            pair.append((float(values[0]), float(values[1])))
        elif pair:
            if len(pair) == 2:
                segments.append(pair)
            pair = []
    if len(pair) == 2:
        segments.append(pair)
    array = np.asarray(segments, dtype=float)
    if array.ndim != 3 or array.shape[1:] != (2, 2):
        raise ValueError("extractor returned malformed interface facets")
    return array


def parse_field(text: str) -> Field:
    data = np.loadtxt(text.splitlines())
    if data.ndim != 2 or data.shape[1] != 6:
        raise ValueError("extractor returned malformed field data")
    nz = data.shape[0] // NR
    if nz * NR != data.shape[0]:
        raise ValueError("field row count is not divisible by the radial resolution")
    arrays = [data[:, index].reshape(nz, NR) for index in range(6)]
    return Field(*arrays)


def atomic_npz(path: Path, **arrays: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.stem}.", suffix=".npz", dir=path.parent)
    os.close(descriptor)
    temporary = Path(name)
    try:
        np.savez_compressed(temporary, **arrays)
        os.replace(temporary, path)
        path.chmod(0o644)
    finally:
        temporary.unlink(missing_ok=True)


def refresh_data(raw_dir: Path) -> None:
    snapshot = raw_dir / "snapshot-0.4400"
    expected = RAW_SHA256[snapshot.name]
    if not snapshot.is_file() or sha256(snapshot) != expected:
        raise ValueError(f"missing or checksum-mismatched raw snapshot: {snapshot}")
    with tempfile.TemporaryDirectory(prefix="drop-impact-extract.") as name:
        executable = compile_extractor(Path(name))
        result = subprocess.run(
            [str(executable), str(snapshot), str(ZMIN), str(ZMAX), str(RMAX), str(NR)],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    field = parse_field(result.stdout)
    segments = parse_facets(result.stderr)
    atomic_npz(FIELD_FILE, **field.__dict__)
    atomic_npz(INTERFACE_FILE, segments_zr=segments)


def load_inputs() -> tuple[Field, np.ndarray]:
    for path in (FIELD_FILE, INTERFACE_FILE):
        if not path.is_file() or sha256(path) != COMPACT_SHA256[path.name]:
            raise ValueError(f"missing or checksum-mismatched illustration input: {path}")
    with np.load(FIELD_FILE) as payload:
        field = Field(**{name: payload[name] for name in Field.__dataclass_fields__})
    shape = field.z.shape
    if shape != (435, 320) or any(array.shape != shape for array in field.__dict__.values()):
        raise ValueError("field arrays do not match the archived 435 x 320 plotting grid")
    if not np.all(np.diff(field.z[:, 0]) > 0) or not np.all(np.diff(field.r[0, :]) > 0):
        raise ValueError("field coordinates are not strictly increasing")
    with np.load(INTERFACE_FILE) as payload:
        segments = np.asarray(payload["segments_zr"], dtype=float)
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


def mirrored_segments(segments_zr: np.ndarray) -> np.ndarray:
    z = segments_zr[:, :, 0]
    r = segments_zr[:, :, 1]
    visible = (
        (np.max(r, axis=1) <= 1.02 * RMAX)
        & (np.max(z, axis=1) >= ZMIN)
        & (np.min(z, axis=1) <= ZMAX)
    )
    right = np.stack((r[visible], z[visible]), axis=2)
    left = right.copy()
    left[:, :, 0] *= -1
    return np.concatenate((left, right), axis=0)


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
            fig.savefig(temp, format=target.suffix.lstrip("."), dpi=300,
                        facecolor="white", transparent=False)
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
    norm = Normalize(vmin=VMIN, vmax=VMAX, clip=True)
    cmap = plt.get_cmap("Purples").copy()
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
            color="#666666",
            density=0.72,
            linewidth=0.85,
            arrowsize=0.75,
            minlength=0.08,
            maxlength=2.0,
            zorder=2,
        )
    ax.add_collection(
        LineCollection(
            mirrored_segments(segments),
            colors=INTERFACE_COLOUR,
            linewidths=2.2,
            zorder=4,
        )
    )
    ax.axhline(0, color="black", linewidth=1.8, zorder=5)
    ax.axvline(0, color="0.72", linewidth=0.8, zorder=1)
    ax.set_xlim(-RMAX, RMAX)
    ax.set_ylim(ZMIN, ZMAX)
    ax.set_aspect("equal")
    ax.axis("off")

    cax = fig.add_axes([0.20, 0.12, 0.60, 0.045])
    colourbar = fig.colorbar(ScalarMappable(norm=norm, cmap=cmap), cax=cax,
                            orientation="horizontal", extend="max")
    colourbar.set_label(r"$|\mathbf{u}|/U_0$", fontsize=16, labelpad=4)
    colourbar.set_ticks(np.linspace(0, 1, 6))
    colourbar.ax.tick_params(labelsize=14, length=5, width=0.8, pad=3)
    colourbar.outline.set_linewidth(0.8)

    outputs = atomic_save(fig, output)
    plt.close(fig)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--refresh-data", action="store_true")
    parser.add_argument("--raw-dir", type=Path)
    parser.add_argument("--no-tex", action="store_true")
    args = parser.parse_args()
    if args.refresh_data:
        if args.raw_dir is None:
            raise SystemExit("--refresh-data requires --raw-dir")
        refresh_data(args.raw_dir)
    for path in render(args.output, use_tex=not args.no_tex):
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
