"""Consistent, arbitrarily positioned T proportional to N^-1 corner guides."""

from __future__ import annotations

import numpy as np
from matplotlib.axes import Axes
from matplotlib.lines import Line2D


GUIDE_STYLE = {"color": "0.3", "linestyle": "--", "linewidth": 1.1}
CORNER_MARGIN = 0.08
GUIDE_LENGTH = 0.28


def ideal_legend_handle() -> Line2D:
    """Return one shared legend key for both corner guides."""
    return Line2D([], [], label="ideal", **GUIDE_STYLE)


def add_corner_guides(ax: Axes) -> tuple[Line2D, Line2D]:
    """Add matching lower-left and upper-right guides without changing limits.

    Margins and segment length are fractions of the square plot box. The
    coordinate increments account for both logarithmic ranges, so each
    segment has slope -1 in log(T) versus log(N), rather than a fixed visual
    angle. Only the final axis limits determine placement; no curve is fitted.
    """
    if ax.get_xscale() != "log" or ax.get_yscale() != "log":
        raise ValueError("ideal corner guides require logarithmic x and y axes")
    limits = np.array([ax.get_xlim(), ax.get_ylim()], dtype=float)
    if not np.isfinite(limits).all() or (limits <= 0).any():
        raise ValueError("ideal corner guides require finite positive limits")
    log_limits = np.log(limits)
    spans = log_limits[:, 1] - log_limits[:, 0]
    if (spans <= 0).any():
        raise ValueError("ideal corner guides require increasing axis limits")

    ratio = spans[0] / spans[1]
    dx = GUIDE_LENGTH / np.hypot(1.0, ratio)
    dy = ratio * dx
    margin = CORNER_MARGIN
    segments = (
        ("lower-left", [margin, margin + dx], [margin + dy, margin]),
        ("upper-right", [1 - margin - dx, 1 - margin],
         [1 - margin, 1 - margin - dy]),
    )
    artists = []
    for corner, x_fraction, y_fraction in segments:
        x = np.exp(log_limits[0, 0] + np.asarray(x_fraction) * spans[0])
        y = np.exp(log_limits[1, 0] + np.asarray(y_fraction) * spans[1])
        line, = ax.plot(
            x, y, scalex=False, scaley=False, zorder=1,
            label="_nolegend_", gid=f"ideal-{corner}", **GUIDE_STYLE,
        )
        artists.append(line)
    return artists[0], artists[1]
