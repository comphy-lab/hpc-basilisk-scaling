#!/usr/bin/env python3
"""Render a four-state Newtonian drop-impact velocity sequence."""

from __future__ import annotations

import argparse
import hashlib
import io
import os
import shutil
import subprocess
import tempfile
import zipfile
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
TIMES = ("0.0500", "0.2200", "0.4400", "4.1900")
RAW_SHA256 = {
    "snapshot-0.0500": "1916f5c15501342890ef20968839b4cd5c4aa84def48c9871756f596b176dc3a",
    "snapshot-0.2200": "7766174bdddcab03379554663201b91ced2075b0dfc206521b7c97f5ee03455a",
    "snapshot-0.4400": "7afe334e444183a244d348e456de945baaa0ad908b7c05ec6d3fe2475624f7df",
    "snapshot-4.1900": "85104a67eb4a83c3d68e599a368f0df0015a461787c137dde1b02c89a850c965",
}
COMPACT_SHA256 = {
    "snapshot-0.0500-fields.npz": "07568225afae5a73f94129d2a792fe0cd4ec9f2be5b871fcfc47b2bcf46a878a",
    "snapshot-0.0500-interface.npz": "1a741529d52acbfa3175d787fcff14aa4b3170545a8a856cb53ddd45b9f823d2",
    "snapshot-0.2200-fields.npz": "935067fe9f6cf272c0960605f4eb4974bb2e8915596c32e6fbf70606d3f4b4cf",
    "snapshot-0.2200-interface.npz": "4e8a5fd3be5f07b1052070e4d16c9e07a519f0ed8e93cd7bf6da1a03d88b4c1b",
    "snapshot-0.4400-fields.npz": "2aa64b863820e7b58a24538f250047785ec80eff0c1dc30c47bfdcc60a92e2b3",
    "snapshot-0.4400-interface.npz": "db2bc24a81a4a8458667cf2eb566f703ba9d834ff03dc934408fbe15251eb99a",
    "snapshot-4.1900-fields.npz": "34d6fb167243e41ff83652cbf35b82cdc76c77ce090ab31afb05c6ca04d2e7e9",
    "snapshot-4.1900-interface.npz": "c37c7ffb4a05c6322dbadd56b88dfa426b2ce1eb8f5ca5c017552886c71041d7",
}

ZMIN = 0.0
ZMAX = 2.05
RMAX = 3.25
NR = 480
VMIN = 0.0
VMAX = 1.0
INVALID_LIMIT = 1.0e20
INTERFACE_COLOUR = "#D55E00"
MM_PER_INCH = 25.4


@dataclass(frozen=True)
class Field:
    z: np.ndarray
    r: np.ndarray
    f: np.ndarray
    uz: np.ndarray
    ur: np.ndarray
    speed: np.ndarray


def field_file(time: str) -> Path:
    return DATA_DIR / f"snapshot-{time}-fields.npz"


def interface_file(time: str) -> Path:
    return DATA_DIR / f"snapshot-{time}-interface.npz"


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
    if (
        Path(qcc).resolve() != expected_qcc.resolve()
        or not lock.is_file()
        or "ref=v2026-07-20" not in lock.read_text().splitlines()
    ):
        raise RuntimeError("raw extraction requires the project-pinned Basilisk v2026-07-20")
    source = SCRIPT_DIR / "extract_drop_image.c"
    shutil.copy2(source, build_dir / source.name)
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
    return Field(*(data[:, i].reshape(nz, NR) for i in range(6)))


def atomic_npz(path: Path, **arrays: np.ndarray) -> None:
    """Write a byte-reproducible compressed NumPy archive."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        prefix=f".{path.stem}.", suffix=".npz", dir=path.parent
    )
    os.close(descriptor)
    temporary = Path(name)
    try:
        with zipfile.ZipFile(temporary, "w") as archive:
            for key, array in arrays.items():
                payload = io.BytesIO()
                np.lib.format.write_array(payload, np.asarray(array), allow_pickle=False)
                info = zipfile.ZipInfo(f"{key}.npy", date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o600 << 16
                archive.writestr(info, payload.getvalue(), compresslevel=9)
        os.replace(temporary, path)
        path.chmod(0o644)
    finally:
        temporary.unlink(missing_ok=True)


def refresh_data(raw_dir: Path) -> None:
    snapshots = [raw_dir / f"snapshot-{time}" for time in TIMES]
    for snapshot in snapshots:
        if not snapshot.is_file() or sha256(snapshot) != RAW_SHA256[snapshot.name]:
            raise ValueError(f"missing or checksum-mismatched raw snapshot: {snapshot}")
    with tempfile.TemporaryDirectory(prefix="drop-impact-extract.") as name:
        executable = compile_extractor(Path(name))
        for time, snapshot in zip(TIMES, snapshots, strict=True):
            result = subprocess.run(
                [str(executable), str(snapshot), str(ZMIN), str(ZMAX), str(RMAX), str(NR)],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            field = parse_field(result.stdout)
            atomic_npz(field_file(time), **field.__dict__)
            atomic_npz(interface_file(time), segments_zr=parse_facets(result.stderr))


def load_inputs(time: str, verify_hashes: bool = True) -> tuple[Field, np.ndarray]:
    paths = (field_file(time), interface_file(time))
    for path in paths:
        if not path.is_file():
            raise ValueError(f"missing illustration input: {path}")
        if verify_hashes and sha256(path) != COMPACT_SHA256.get(path.name):
            raise ValueError(f"checksum-mismatched illustration input: {path}")
    with np.load(paths[0]) as payload:
        field = Field(**{name: payload[name] for name in Field.__dataclass_fields__})
    nz = int((ZMAX - ZMIN) / (RMAX / NR))
    shape = (nz, NR)
    if any(array.shape != shape for array in field.__dict__.values()):
        raise ValueError(f"field arrays do not match the archived {nz} x {NR} plotting grid")
    if not np.all(np.diff(field.z[:, 0]) > 0) or not np.all(np.diff(field.r[0, :]) > 0):
        raise ValueError("field coordinates are not strictly increasing")
    with np.load(paths[1]) as payload:
        segments = np.asarray(payload["segments_zr"], dtype=float)
    if segments.ndim != 3 or segments.shape[1:] != (2, 2) or not np.all(np.isfinite(segments)):
        raise ValueError("interface segments are malformed")
    return field, segments


def stream_arrays(field: Field, mirror: bool) -> tuple[np.ndarray, ...]:
    invalid = (
        ~np.isfinite(field.ur)
        | ~np.isfinite(field.uz)
        | (np.abs(field.ur) >= INVALID_LIMIT)
        | (np.abs(field.uz) >= INVALID_LIMIT)
    )
    ur = np.ma.masked_where(invalid, field.ur)
    uz = np.ma.masked_where(invalid, field.uz)
    r, z = field.r[0, :], field.z[:, 0]
    if mirror:
        return -r[::-1], z, -ur[:, ::-1], uz[:, ::-1]
    return r, z, ur, uz


def mirrored_segments(segments_zr: np.ndarray) -> np.ndarray:
    z, r = segments_zr[:, :, 0], segments_zr[:, :, 1]
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


def draw_frame(
    ax: plt.Axes,
    time: str,
    norm: Normalize,
    cmap: matplotlib.colors.Colormap,
    verify_hashes: bool,
) -> None:
    field, segments = load_inputs(time, verify_hashes=verify_hashes)
    speed = np.ma.masked_where(
        ~np.isfinite(field.speed) | (np.abs(field.speed) >= INVALID_LIMIT), field.speed
    )
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
            color="#666666",
            density=(1.05, 0.58),
            linewidth=0.38,
            arrowsize=0.45,
            minlength=0.10,
            maxlength=2.4,
            zorder=2,
        )
    ax.add_collection(
        LineCollection(
            mirrored_segments(segments),
            colors=INTERFACE_COLOUR,
            linewidths=0.85,
            zorder=4,
        )
    )
    ax.axhline(0, color="black", linewidth=0.8, zorder=5)
    ax.axvline(0, color="0.72", linewidth=0.35, zorder=1)
    ax.text(
        0.025,
        0.91,
        rf"$tU_0/R={float(time):.2f}$",
        transform=ax.transAxes,
        fontsize=10,
        ha="left",
        va="top",
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.82, "pad": 1.2},
        zorder=6,
    )
    ax.set_xlim(-RMAX, RMAX)
    ax.set_ylim(ZMIN, ZMAX)
    ax.set_aspect("equal")
    ax.axis("off")


def render(output: Path, use_tex: bool, verify_hashes: bool = True) -> tuple[Path, Path]:
    configure_matplotlib(use_tex)
    norm = Normalize(vmin=VMIN, vmax=VMAX, clip=True)
    cmap = plt.get_cmap("Purples").copy()
    cmap.set_bad((1, 1, 1, 0))
    fig, axes = plt.subplots(
        2, 2, figsize=(166.0 / MM_PER_INCH, 74.0 / MM_PER_INCH), facecolor="white"
    )
    fig.subplots_adjust(
        left=0.008, right=0.992, top=0.985, bottom=0.205, wspace=0.025, hspace=0.095
    )
    for ax, time in zip(axes.flat, TIMES, strict=True):
        draw_frame(ax, time, norm, cmap, verify_hashes)
    cax = fig.add_axes([0.30, 0.130, 0.40, 0.035])
    colourbar = fig.colorbar(
        ScalarMappable(norm=norm, cmap=cmap),
        cax=cax,
        orientation="horizontal",
        extend="max",
    )
    colourbar.set_label(r"$|\mathbf{u}|/U_0$", fontsize=10, labelpad=2)
    colourbar.set_ticks([0.0, 0.5, 1.0])
    colourbar.ax.tick_params(labelsize=9, length=3, width=0.6, pad=2)
    colourbar.outline.set_linewidth(0.6)
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
    for path in render(
        args.output, use_tex=not args.no_tex, verify_hashes=not args.refresh_data
    ):
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
