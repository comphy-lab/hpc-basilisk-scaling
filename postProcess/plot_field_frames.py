#!/usr/bin/env python3
"""
# Planar snapshot movies

Interface facets over one scalar field from planar Basilisk dumps
(`activity-drop`, `marangoni-interact`). No streamlines. Mathtext (not
usetex) so workers can render in parallel.

Field modes:

- `speed` — $|u|$ on Blues
- `f` — VOF fraction
- `c` — activity concentration `cL`, masked by $(1-f)$, YlOrRd

Uses `get_fields_planar` / `get_facets_planar`. Compiles those helpers
once, then renders frames in batches of `--cpus`. Frame order is
numeric snapshot time, then a sequential `img_%06d.png` stitch (no
filename glob, no concat demuxer).

## Author
Vatsal Sanjay (vatsal.sanjay@comphy-lab.org)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

SNAPSHOT_RE = re.compile(r"snapshot-([0-9]+\.[0-9]+)$")
INTERFACE = "#FF00C8"


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
    for name in ("get_facets_planar", "get_fields_planar"):
        src = src_dir / f"{name}.c"
        local_src = build_dir / f"{name}.c"
        shutil.copy2(src, local_src)
        dest = build_dir / name
        if dest.exists() and dest.stat().st_mtime >= local_src.stat().st_mtime:
            bins[name] = dest
            continue
        cmd = [qcc, "-O2", "-Wall", "-disable-dimensions", str(local_src.name),
               "-o", str(dest.name), "-lm"]
        subprocess.run(cmd, check=True, cwd=str(build_dir))
        bins[name] = dest
    return bins


def param_slug(payload: dict) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()[:12]


def snapshot_time(path: Path) -> float:
    match = SNAPSHOT_RE.fullmatch(path.name)
    if not match:
        raise ValueError(f"unrecognised snapshot name {path.name}")
    return float(match.group(1))


def extract_ascii(snapshot: Path, helpers: dict[str, Path], work: Path,
                  xmin: float, xmax: float, ymin: float, ymax: float, ny: int) -> tuple[Path, Path]:
    fields_txt = work / f"{snapshot.name}.fields"
    facets_txt = work / f"{snapshot.name}.facets"
    if not fields_txt.exists():
        fields = subprocess.run(
            [str(helpers["get_fields_planar"]), str(snapshot),
             str(xmin), str(xmax), str(ymin), str(ymax), str(ny)],
            check=True, capture_output=True, text=True,
        )
        fields_txt.write_text(fields.stdout)
    if not facets_txt.exists():
        facets = subprocess.run(
            [str(helpers["get_facets_planar"]), str(snapshot)],
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
    match = re.match(r"#\s*nx\s+(\d+)\s+ny\s+(\d+)", header)
    if not match:
        raise ValueError(f"{fname}: missing nx/ny header")
    nx, ny = int(match.group(1)), int(match.group(2))
    data = np.loadtxt(fname, comments="#")
    ncols = data.shape[1]
    cols = [data[:, k].reshape(nx, ny) for k in range(ncols)]
    return nx, ny, cols


def style_axes(ax) -> None:
    ax.tick_params(which="both", direction="out", width=2.0, labelsize=14, pad=6)
    ax.tick_params(which="major", length=8)
    ax.tick_params(which="minor", length=4)
    for spine in ax.spines.values():
        spine.set_linewidth(2.0)


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
    fields_txt, facets_txt = extract_ascii(
        snapshot, helpers, work,
        task["xmin"], task["xmax"], task["ymin"], task["ymax"], task["ny"],
    )
    nx, ny, cols = read_fields(fields_txt)
    x, y, f, ux, uy = cols[0], cols[1], cols[2], cols[3], cols[4]
    cL = cols[5] if len(cols) > 5 else np.zeros_like(f)
    segments = read_facets(facets_txt)

    if task["field"] == "speed":
        z = np.hypot(ux, uy)
        cmap = "Blues"
        clabel = r"$|\boldsymbol{u}|$"
    elif task["field"] == "f":
        z = np.clip(f, 0.0, 1.0)
        cmap = "PuOr_r"
        clabel = r"$f$"
    elif task["field"] == "c":
        ff = np.clip(f, 0.0, 1.0)
        z = np.clip(cL, 0.0, None) * (1.0 - ff)
        cmap = "YlOrRd"
        clabel = r"$c$"
    else:
        raise ValueError(f"unknown field {task['field']}")

    fig, ax = plt.subplots(figsize=(8.2, 8.0))
    fig.set_facecolor("white")
    ax.set_facecolor("white")
    im = ax.pcolormesh(
        x, y, z, shading="nearest", cmap=cmap,
        vmin=task["vmin"], vmax=task["vmax"],
        rasterized=True, zorder=1,
    )
    if segments:
        ax.add_collection(LineCollection(
            segments, colors=INTERFACE, linewidths=1.6, zorder=3,
        ))
    ax.set_aspect("equal")
    ax.set_xlim(task["xmin"], task["xmax"])
    ax.set_ylim(task["ymin"], task["ymax"])
    ax.set_xlabel(r"$x/R$", fontsize=16, labelpad=6)
    ax.set_ylabel(r"$y/R$", fontsize=16, labelpad=6)
    ax.set_title(rf"${task['time_math']} = {task['tstar']:.2f}$", fontsize=16, pad=8)
    style_axes(ax)
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(clabel, fontsize=16, labelpad=8)
    cbar.ax.tick_params(labelsize=13, width=1.6, length=5)
    for spine in cbar.ax.spines.values():
        spine.set_linewidth(1.6)
    out = Path(task["frame"])
    fig.savefig(out, dpi=160, bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)
    return str(out)


def list_snapshots(case_dir: Path) -> list[Path]:
    return sorted(
        (p for p in case_dir.glob("snapshot-*") if SNAPSHOT_RE.fullmatch(p.name)),
        key=snapshot_time,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-dir", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument(
        "--src-dir", type=Path,
        default=Path(__file__).resolve().parent,
        help="directory containing get_fields_planar.c and get_facets_planar.c",
    )
    parser.add_argument("--field", choices=("speed", "f", "c"), required=True)
    parser.add_argument("--xmin", type=float, required=True)
    parser.add_argument("--xmax", type=float, required=True)
    parser.add_argument("--ymin", type=float, required=True)
    parser.add_argument("--ymax", type=float, required=True)
    parser.add_argument("--vmin", type=float, required=True)
    parser.add_argument("--vmax", type=float, required=True)
    parser.add_argument("--cpus", "--CPUs", dest="cpus", type=int, default=4)
    parser.add_argument("--ny", type=int, default=320)
    parser.add_argument("--fps", type=int, default=10)
    parser.add_argument("--video", type=Path, default=None)
    parser.add_argument("--ffmpeg", default="")
    parser.add_argument("--qcc", default=os.environ.get("QCC", shutil.which("qcc") or "qcc"))
    parser.add_argument("--max-frames", type=int, default=0)
    parser.add_argument("--skip-video", action="store_true")
    parser.add_argument("--time-math", default="t")
    parser.add_argument(
        "--exclude-times",
        default="",
        help="comma-separated snapshot times to drop from the movie",
    )
    args = parser.parse_args()
    if args.cpus <= 0:
        raise SystemExit("--cpus must be > 0")
    if not args.skip_video and args.video is None:
        raise SystemExit("--video is required unless --skip-video")

    snapshots = list_snapshots(args.case_dir)
    exclude = parse_exclude_times(args.exclude_times)
    if exclude:
        kept = [
            snap for snap in snapshots
            if not any(abs(snapshot_time(snap) - skipped) < 1e-9 for skipped in exclude)
        ]
        if len(kept) == len(snapshots):
            raise SystemExit(f"exclude-times matched nothing: {sorted(exclude)}")
        snapshots = kept
    if args.max_frames:
        snapshots = snapshots[: args.max_frames]
    if not snapshots:
        raise SystemExit(f"no snapshot-* in {args.case_dir}")

    ascii_dir = args.work_dir / "ascii" / param_slug({
        "xmin": args.xmin, "xmax": args.xmax,
        "ymin": args.ymin, "ymax": args.ymax, "ny": args.ny,
    })
    frame_dir = args.work_dir / "frames" / param_slug({
        "field": args.field, "xmin": args.xmin, "xmax": args.xmax,
        "ymin": args.ymin, "ymax": args.ymax, "ny": args.ny,
        "vmin": args.vmin, "vmax": args.vmax,
        "time_math": args.time_math,
    })
    cache_root = args.work_dir / "cache"
    build_dir = args.work_dir / "bin"
    for path in (ascii_dir, frame_dir, cache_root):
        path.mkdir(parents=True, exist_ok=True)
    helpers = precompile_get_helpers(args.src_dir, build_dir, args.qcc)

    tasks = []
    for snap in snapshots:
        tstar = snapshot_time(snap)
        tasks.append({
            "snapshot": str(snap),
            "helpers": {k: str(v) for k, v in helpers.items()},
            "ascii_dir": str(ascii_dir),
            "cache_root": str(cache_root),
            "frame": str(frame_dir / f"{snap.name}.png"),
            "tstar": tstar,
            "ny": args.ny,
            "xmin": args.xmin,
            "xmax": args.xmax,
            "ymin": args.ymin,
            "ymax": args.ymax,
            "vmin": args.vmin,
            "vmax": args.vmax,
            "field": args.field,
            "time_math": args.time_math,
        })

    for start in range(0, len(tasks), args.cpus):
        chunk = tasks[start:start + args.cpus]
        pending = [t for t in chunk if not Path(t["frame"]).exists()]
        if not pending:
            continue
        if args.cpus == 1:
            for task in pending:
                render_one(task)
        else:
            with ProcessPoolExecutor(max_workers=args.cpus) as pool:
                list(pool.map(render_one, pending))

    print(f"wrote {len(tasks)} frames in {frame_dir}")
    if args.skip_video:
        return
    ffmpeg = args.ffmpeg or shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg not found")
    args.video.parent.mkdir(parents=True, exist_ok=True)
    stitch_sorted_frames(ffmpeg, tasks, frame_dir, args.video, args.fps)
    print(f"wrote {args.video}")


def parse_exclude_times(raw: str) -> set[float]:
    times: set[float] = set()
    for part in raw.split(","):
        text = part.strip()
        if not text:
            continue
        times.add(float(text))
    return times


def stitch_sorted_frames(
    ffmpeg: str, tasks: list[dict], frame_dir: Path, video: Path, fps: int,
    exclude_times: set[float] | None = None,
) -> None:
    """Concat frames in numeric snapshot-time order. No B-frames, so decode
    order equals presentation order in every player."""
    exclude = exclude_times or set()
    kept = [
        task for task in tasks
        if not any(abs(float(task["tstar"]) - skipped) < 1e-9 for skipped in exclude)
    ]
    if exclude and len(kept) == len(tasks):
        raise SystemExit(f"exclude-times matched nothing: {sorted(exclude)}")
    ordered = sorted(kept, key=lambda t: (float(t["tstar"]), t["frame"]))
    times = [float(t["tstar"]) for t in ordered]
    if times != sorted(times):
        raise SystemExit("frame list is not monotonic in t")
    for i in range(1, len(times)):
        if times[i] < times[i - 1]:
            raise SystemExit(f"non-increasing time at {i}: {times[i-1]} -> {times[i]}")
    stitch_dir = frame_dir / "stitch"
    if stitch_dir.exists():
        shutil.rmtree(stitch_dir)
    stitch_dir.mkdir()
    manifest_lines = ["index\tt\tsource\n"]
    for i, task in enumerate(ordered):
        src = Path(task["frame"]).resolve()
        if not src.is_file():
            raise SystemExit(f"missing frame {src}")
        dest = stitch_dir / f"img_{i:06d}.png"
        try:
            dest.hardlink_to(src)
        except OSError:
            shutil.copy2(src, dest)
        manifest_lines.append(f"{i}\t{float(task['tstar']):.6f}\t{src.name}\n")
    (frame_dir / "frame-order.txt").write_text("".join(manifest_lines))
    # Sequential %06d image2 input. Do not glob, do not concat: both can
    # lexicographically put t=2 after t=19 or drop frames on bad DTS.
    subprocess.run(
        [
            ffmpeg, "-y",
            "-framerate", str(fps), "-start_number", "0",
            "-i", str(stitch_dir / "img_%06d.png"),
            "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-bf", "0", "-g", "1", "-fps_mode", "cfr", "-r", str(fps),
            "-crf", "18",
            str(video),
        ],
        check=True,
    )


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        sys.exit(exc.returncode)
