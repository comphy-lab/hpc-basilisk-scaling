#!/usr/bin/env python3
"""Drop-frame streamlines + VOF order parameter from Marangoni snapshots.

Follows the CoMPhy parallel snapshot pattern: compile get_* once, process
frames in batches of --cpus, isolate matplotlib caches per worker, assemble
the video only after every frame exists.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

SNAPSHOT_RE = re.compile(r"snapshot-([0-9]+\.[0-9]+)$")


def configure_worker_environment(cache_root: Path) -> None:
    pid = os.getpid()
    mpl = cache_root / f"mpl-{pid}"
    tex = cache_root / f"tex-{pid}"
    mpl.mkdir(parents=True, exist_ok=True)
    tex.mkdir(parents=True, exist_ok=True)
    os.environ["MPLCONFIGDIR"] = str(mpl)
    os.environ["TEXMFVAR"] = str(tex)
    os.environ["TEXMFCONFIG"] = str(tex)
    os.environ["OMP_NUM_THREADS"] = "1"


def precompile_get_helpers(src_dir: Path, build_dir: Path, qcc: str) -> dict[str, Path]:
    build_dir.mkdir(parents=True, exist_ok=True)
    bins = {}
    for name in ("get_facets", "get_fields"):
        src = src_dir / f"{name}.c"
        dest = build_dir / name
        cmd = [qcc, "-O2", "-Wall", "-disable-dimensions", str(src), "-o", str(dest), "-lm"]
        subprocess.run(cmd, check=True)
        bins[name] = dest
    return bins


def snapshot_time(path: Path) -> float:
    match = SNAPSHOT_RE.fullmatch(path.name)
    if not match:
        raise ValueError(f"unrecognised snapshot name {path.name}")
    return float(match.group(1))


def extract_ascii(snapshot: Path, helpers: dict[str, Path], work: Path, ny: int) -> tuple[Path, Path]:
    fields_txt = work / f"{snapshot.name}.fields"
    facets_txt = work / f"{snapshot.name}.facets"
    # Wide enough to contain the drop; Python recentres on xb from the header.
    fields = subprocess.run(
        [str(helpers["get_fields"]), str(snapshot), "-6", "6", "0", "5", str(ny)],
        check=True, capture_output=True, text=True,
    )
    fields_txt.write_text(fields.stdout)
    facets = subprocess.run(
        [str(helpers["get_facets"]), str(snapshot)],
        check=True, capture_output=True, text=True,
    )
    facets_txt.write_text(facets.stdout)
    return fields_txt, facets_txt


def read_facets(fname: Path) -> list:
    import numpy as np

    segments = []
    pts: list[tuple[float, float]] = []
    with fname.open() as handle:
        for line in handle:
            line = line.strip()
            if not line:
                if len(pts) == 2:
                    segments.append(np.array(pts))
                pts = []
                continue
            x, y = map(float, line.split()[:2])
            pts.append((x, y))
    if len(pts) == 2:
        segments.append(np.array(pts))
    return segments


def read_fields(fname: Path):
    import numpy as np

    with fname.open() as handle:
        header = handle.readline()
        extra = handle.readline()
    match = re.match(r"#\s*nx\s+(\d+)\s+ny\s+(\d+)", header)
    if not match:
        raise ValueError(f"{fname}: missing nx/ny header")
    nx, ny = int(match.group(1)), int(match.group(2))
    xb = vb = 0.0
    extra_match = re.match(r"\# xb\s+(\S+)\s+vb\s+(\S+)", extra)
    if extra_match:
        xb = float(extra_match.group(1))
        vb = float(extra_match.group(2))
    data = np.loadtxt(fname, comments="#")
    cols = [data[:, k].reshape(nx, ny) for k in range(7)]
    return nx, ny, xb, vb, cols


def render_one(task: dict) -> str:
    configure_worker_environment(Path(task["cache_root"]))
    import matplotlib

    matplotlib.use("Agg")
    matplotlib.rcParams["font.family"] = "serif"
    matplotlib.rcParams["mathtext.fontset"] = "cm"
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    import numpy as np

    snapshot = Path(task["snapshot"])
    helpers = {k: Path(v) for k, v in task["helpers"].items()}
    work = Path(task["ascii_dir"])
    fields_txt, facets_txt = extract_ascii(snapshot, helpers, work, task["ny"])
    nx, ny, xb, vb, cols = read_fields(fields_txt)
    x, y, f, _d, _sig, ux, uy = cols
    segments = read_facets(facets_txt)

    ux_rel = ux - vb
    x_shift = x - xb
    segs_shift = [seg - np.array([xb, 0.0]) for seg in segments]
    segs_mirror = [np.column_stack((seg[:, 0], -seg[:, 1])) for seg in segs_shift]
    all_segs = segs_shift + segs_mirror

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.set_facecolor("white")
    levels = np.linspace(0.0, 1.0, 21)
    cf = ax.contourf(
        x_shift, y, f, levels=levels, cmap="PuOr_r", vmin=0.0, vmax=1.0, zorder=1,
    )
    ax.contourf(
        x_shift, -y, f, levels=levels, cmap="PuOr_r", vmin=0.0, vmax=1.0, zorder=1,
    )
    skip = max(1, min(nx, ny) // 25)
    ax.streamplot(
        x_shift[::skip, 0], y[0, ::skip],
        ux_rel[::skip, ::skip].T, uy[::skip, ::skip].T,
        color="k", density=0.9, linewidth=0.8, arrowsize=0.8, zorder=2,
    )
    ax.streamplot(
        x_shift[::skip, 0], -y[0, ::skip],
        ux_rel[::skip, ::skip].T, -uy[::skip, ::skip].T,
        color="k", density=0.9, linewidth=0.8, arrowsize=0.8, zorder=2,
    )
    if all_segs:
        ax.add_collection(LineCollection(all_segs, colors="#FF00C8", linewidths=2.0, zorder=3))
    ax.set_aspect("equal")
    ax.set_xlim(-3, 3)
    ax.set_ylim(-3, 3)
    ax.set_xlabel(r"$(x - x_b)/R$")
    ax.set_ylabel(r"$y/R$")
    ax.set_title(rf"$t/t_0 = {task['tstar']:.2f}$")
    cbar = fig.colorbar(cf, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(r"$f$")
    out = Path(task["frame"])
    fig.savefig(out, dpi=160, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    return str(out)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-dir", type=Path, required=True)
    parser.add_argument("--cpus", "--CPUs", type=int, default=4)
    parser.add_argument("--max-frames", type=int, default=0)
    parser.add_argument("--skip-video", action="store_true")
    parser.add_argument("--ny", type=int, default=240)
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--qcc", default=os.environ.get("QCC", shutil.which("qcc") or "qcc"))
    args = parser.parse_args()
    if args.cpus <= 0:
        raise SystemExit("--cpus must be > 0")

    snapshots = sorted(
        (p for p in args.case_dir.glob("snapshot-*") if SNAPSHOT_RE.fullmatch(p.name)),
        key=snapshot_time,
    )
    if args.max_frames:
        snapshots = snapshots[: args.max_frames]
    if not snapshots:
        raise SystemExit(f"no snapshot-* in {args.case_dir}")

    src_dir = Path(__file__).resolve().parent
    build_dir = args.case_dir / "postprocess" / "bin"
    ascii_dir = args.case_dir / "postprocess" / "ascii"
    frame_dir = args.case_dir / "postprocess" / "frames"
    cache_root = args.case_dir / "postprocess" / "cache"
    for path in (ascii_dir, frame_dir, cache_root):
        path.mkdir(parents=True, exist_ok=True)
    helpers = precompile_get_helpers(src_dir, build_dir, args.qcc)

    tasks = []
    for index, snap in enumerate(snapshots):
        tasks.append({
            "snapshot": str(snap),
            "helpers": {k: str(v) for k, v in helpers.items()},
            "ascii_dir": str(ascii_dir),
            "cache_root": str(cache_root),
            "frame": str(frame_dir / f"frame_{index:06d}.png"),
            "tstar": snapshot_time(snap),
            "ny": args.ny,
        })

    for start in range(0, len(tasks), args.cpus):
        chunk = tasks[start:start + args.cpus]
        if args.cpus == 1:
            for task in chunk:
                render_one(task)
        else:
            with ProcessPoolExecutor(max_workers=args.cpus) as pool:
                list(pool.map(render_one, chunk))

    print(f"wrote {len(tasks)} frames in {frame_dir}")
    if args.skip_video:
        return
    video = args.case_dir / "postprocess" / "drop.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-framerate", str(args.fps),
            "-i", str(frame_dir / "frame_%06d.png"),
            "-pix_fmt", "yuv420p", "-crf", "18", str(video),
        ],
        check=True,
    )
    print(f"wrote {video}")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        sys.exit(exc.returncode)
