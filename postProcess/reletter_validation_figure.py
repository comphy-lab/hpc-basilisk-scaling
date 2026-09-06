#!/usr/bin/env python3
"""Recompose the fixed Marangoni validation artwork at a 166 mm width.

The source PDF is the scientific record. Ghostscript removes only its text
operators. Vector crops then retain the curves, markers, reference line,
slope triangle, axes, streamlines and interfaces; the four original field
rasters and colour-bar raster stay embedded at their native pixel counts.
LaTeX restores the same labels with report-readable Computer Modern type.

Source SHA-256:
4cb48ddc488ebc17518130352a371d881baaef6aae5c081a8136b3c11dccf914
Source page: 1146.875844 x 719.485328 bp. Crop boxes are recorded below in
the same top-origin source-page coordinate frame.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "figures" / "marangoni-validate-vt-fields.pdf"
DEFAULT_OUTPUT = ROOT / "figures" / "marangoni-validate-vt-fields-report.pdf"
EXPECTED_SOURCE_SHA256 = (
    "4cb48ddc488ebc17518130352a371d881baaef6aae5c081a8136b3c11dccf914"
)
SOURCE_WIDTH_BP = 1146.875844
SOURCE_HEIGHT_BP = 719.485328
OUTPUT_WIDTH_BP = 166.0 * 72.0 / 25.4
OUTPUT_HEIGHT_BP = 590.0


@dataclass(frozen=True)
class Crop:
    left: float
    top: float
    right: float
    bottom: float


@dataclass(frozen=True)
class Placement:
    crop: Crop
    x: float
    y: float
    width: float

    @property
    def scale(self) -> float:
        return self.width / (self.crop.right - self.crop.left)

    @property
    def height(self) -> float:
        return (self.crop.bottom - self.crop.top) * self.scale

    def map(self, source_x: float, source_y_from_top: float) -> tuple[float, float]:
        return (
            self.x + (source_x - self.crop.left) * self.scale,
            self.y + (self.crop.bottom - source_y_from_top) * self.scale,
        )


@dataclass(frozen=True)
class Label:
    x: float
    y: float
    text: str
    size: int
    rotation: int = 0
    align: str = ""


# Crops include every scientific graphical object within the corresponding
# axes, including the original legend handles, but exclude all neighbouring
# panels. The four field crops have identical dimensions and use one scale.
GRAPH_A = Placement(Crop(77.0, 47.0, 346.0, 315.0), 45.0, 397.0, 175.0)
GRAPH_B = Placement(Crop(77.0, 388.0, 346.0, 656.0), 280.0, 397.0, 175.0)
FIELD_TL = Placement(Crop(425.0, 48.0, 693.0, 315.0), 50.0, 190.0, 145.0)
FIELD_TR = Placement(Crop(760.0, 48.0, 1028.0, 315.0), 305.0, 190.0, 145.0)
FIELD_BL = Placement(Crop(425.0, 388.0, 693.0, 655.0), 50.0, 30.0, 145.0)
FIELD_BR = Placement(Crop(760.0, 388.0, 1028.0, 655.0), 305.0, 30.0, 145.0)
COLOURBAR_HEIGHT = 304.5
COLOURBAR = Placement(
    Crop(1058.0, 48.0, 1083.0, 655.0),
    225.0,
    30.0,
    25.0 * COLOURBAR_HEIGHT / 607.0,
)
PLACEMENTS = (GRAPH_A, GRAPH_B, FIELD_TL, FIELD_TR, FIELD_BL, FIELD_BR)


def mapped(
    placement: Placement,
    source_x: float,
    source_y: float,
    text: str,
    size: int,
    rotation: int = 0,
) -> Label:
    x, y = placement.map(source_x, source_y)
    return Label(x, y, text, size, rotation)


def labels() -> tuple[Label, ...]:
    result = [
        Label(15.0, 578.0, r"$(a)$", 11),
        Label(250.0, 578.0, r"$(b)$", 11),
        Label(15.0, 350.0, r"$(c)$", 11),
    ]

    # (a): terminal-speed history and resolution legend.
    result.extend(
        mapped(GRAPH_A, 49.77, sy, text, 9)
        for sy, text in (
            (55.16, r"$1.00$"),
            (107.36, r"$0.98$"),
            (211.72, r"$0.94$"),
            (316.09, r"$0.90$"),
        )
    )
    result.extend(
        mapped(GRAPH_A, sx, 336.62, text, 9)
        for sx, text in zip(
            (78.65, 167.37, 256.08, 344.80),
            (r"$0$", r"$1$", r"$2$", r"$3$"),
            strict=True,
        )
    )
    result.extend(
        (
            mapped(GRAPH_A, 211.75, 361.50, r"$t/t_0$", 10),
            Label(12.0, GRAPH_A.y + GRAPH_A.height / 2.0,
                  r"$u_{\mathrm{drop}}/U_{\mathrm{drop}}$", 10, 90),
            mapped(GRAPH_A, 297.77, 262.10, r"$\mathrm{pts}/R$", 9),
        )
    )
    for sx, sy, text in (
        (280.66, 275.65, r"$8$"),
        (325.29, 275.65, r"$64$"),
        (283.59, 288.54, r"$16$"),
        (328.21, 288.54, r"$128$"),
        (283.59, 301.42, r"$32$"),
        (328.21, 301.42, r"$256$"),
    ):
        result.append(mapped(GRAPH_A, sx, sy, text, 9))

    # (b): convergence data, retained slope marker and three-entry legend.
    result.extend(
        (
            mapped(GRAPH_B, 116.99, 426.20, r"$2$", 9),
            mapped(GRAPH_B, 287.75, 407.27, r"$N^{-2}$", 9),
            mapped(GRAPH_B, 303.62, 427.48, r"\textrm{basilisk.fr}", 9),
            mapped(GRAPH_B, 302.84, 446.99, r"\textrm{this work}", 9),
            mapped(GRAPH_B, 41.53, 539.86, r"$10^{-2}$", 9),
        )
    )
    result.extend(
        mapped(GRAPH_B, sx, 677.30, text, 9)
        for sx, text in zip(
            (97.90, 144.30, 190.70, 237.10, 283.50, 329.85),
            (r"$8$", r"$16$", r"$32$", r"$64$", r"$128$", r"$256$"),
            strict=True,
        )
    )
    result.extend(
        (
            mapped(GRAPH_B, 211.75, 701.35, r"$\mathrm{pts}/R$", 10),
            Label(235.0, GRAPH_B.y + GRAPH_B.height / 2.0,
                  r"\textrm{relative error}", 10, 90),
        )
    )

    # (c): four fields, all at one common spatial scale.
    for placement, title in zip(
        (FIELD_TL, FIELD_TR, FIELD_BL, FIELD_BR),
        (r"$t/t_0=0.5$", r"$t/t_0=1$", r"$t/t_0=2$", r"$t/t_0=3$"),
        strict=True,
    ):
        result.append(Label(
            placement.x + placement.width / 2.0,
            placement.y + placement.height + 8.0,
            title,
            10,
        ))
    for placement in (FIELD_TL, FIELD_BL):
        result.extend(
            Label(placement.x - 10.0, placement.y + frac * placement.height,
                  text, 9)
            for frac, text in ((1.0, r"$2$"), (0.5, r"$0$"), (0.0, r"$-2$"))
        )
        result.append(Label(
            placement.x - 29.0,
            placement.y + placement.height / 2.0,
            r"$y/R$",
            10,
            90,
        ))
    for placement in (FIELD_BL, FIELD_BR):
        result.extend(
            Label(placement.x + frac * placement.width, placement.y - 10.0,
                  text, 9)
            for frac, text in ((0.0, r"$-2$"), (0.5, r"$0$"), (1.0, r"$2$"))
        )
        result.append(Label(
            placement.x + placement.width / 2.0,
            placement.y - 24.0,
            r"$(x-x_b)/R$",
            10,
        ))

    # The source vertical colour bar is uniformly scaled to span both rows.
    bar_scale = COLOURBAR_HEIGHT / (COLOURBAR.crop.bottom - COLOURBAR.crop.top)
    bar_height = COLOURBAR_HEIGHT
    result.extend(
        Label(
            COLOURBAR.x + COLOURBAR.width + 7.0,
            COLOURBAR.y + (COLOURBAR.crop.bottom - sy) * bar_scale,
            text,
            9,
            align="l",
        )
        for sy, text in (
            (100.22, r"$1.0$"),
            (226.64, r"$0.5$"),
            (353.06, r"$0.0$"),
            (509.20, r"$-0.5$"),
            (660.90, r"$-1.0$"),
        )
    )
    result.append(Label(
        COLOURBAR.x + COLOURBAR.width + 39.0,
        COLOURBAR.y + bar_height / 2.0,
        r"$u_x^\prime/U_{\mathrm{drop}}$",
        10,
        90,
    ))
    return tuple(result)


def run(command: list[str], *, cwd: Path, env: dict[str, str]) -> None:
    subprocess.run(command, cwd=cwd, env=env, check=True)


def tex_include(placement: Placement, artwork: Path) -> str:
    crop = placement.crop
    bottom_trim = SOURCE_HEIGHT_BP - crop.bottom
    right_trim = SOURCE_WIDTH_BP - crop.right
    return (
        rf"\put({placement.x:.4f},{placement.y:.4f})"
        rf"{{\includegraphics[trim={crop.left:.4f}bp {bottom_trim:.4f}bp "
        rf"{right_trim:.4f}bp {crop.top:.4f}bp,clip,width={placement.width:.4f}bp]"
        rf"{{{artwork.as_posix()}}}}}"
    )


def tex_label(label: Label) -> str:
    content = (
        rf"\fontsize{{{label.size}}}{{{label.size + 1}}}\selectfont "
        + label.text
    )
    if label.rotation:
        content = rf"\rotatebox{{{label.rotation}}}{{{content}}}"
    align = f"[{label.align}]" if label.align else ""
    return rf"\put({label.x:.4f},{label.y:.4f}){{\makebox(0,0){align}{{{content}}}}}"


def make_tex(artwork: Path) -> str:
    artwork_commands = "\n".join(
        tex_include(placement, artwork) for placement in PLACEMENTS
    )
    # Colour-bar placement is height-driven so it spans both field rows.
    crop = COLOURBAR.crop
    bottom_trim = SOURCE_HEIGHT_BP - crop.bottom
    right_trim = SOURCE_WIDTH_BP - crop.right
    colourbar_command = (
        rf"\put({COLOURBAR.x:.4f},{COLOURBAR.y:.4f})"
        rf"{{\includegraphics[trim={crop.left:.4f}bp {bottom_trim:.4f}bp "
        rf"{right_trim:.4f}bp {crop.top:.4f}bp,clip,height={COLOURBAR_HEIGHT:.4f}bp]"
        rf"{{{artwork.as_posix()}}}}}"
    )
    label_commands = "\n".join(tex_label(label) for label in labels())
    return rf"""\RequirePackage{{fix-cm}}
\documentclass{{article}}
\usepackage{{amsmath}}
\usepackage{{graphicx}}
\usepackage[paperwidth={OUTPUT_WIDTH_BP:.6f}bp,paperheight={OUTPUT_HEIGHT_BP:.6f}bp,margin=0bp]{{geometry}}
\pagestyle{{empty}}
\setlength{{\parindent}}{{0pt}}
\setlength{{\topskip}}{{0pt}}
\setlength{{\unitlength}}{{1bp}}
\begin{{document}}
\noindent\begin{{picture}}({OUTPUT_WIDTH_BP:.6f},{OUTPUT_HEIGHT_BP:.6f})
{artwork_commands}
{colourbar_command}
{label_commands}
\end{{picture}}
\end{{document}}
"""


def compose(source: Path, output: Path) -> None:
    if output.suffix.lower() != ".pdf":
        raise ValueError("the output path must have a .pdf suffix")
    output = output.expanduser().resolve()
    actual = hashlib.sha256(source.read_bytes()).hexdigest()
    if actual != EXPECTED_SOURCE_SHA256:
        raise ValueError(f"{source}: expected source SHA-256 {EXPECTED_SOURCE_SHA256}")

    output.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["SOURCE_DATE_EPOCH"] = "0"
    env["FORCE_SOURCE_DATE"] = "1"
    with tempfile.TemporaryDirectory(prefix="marangoni-reletter-") as tmp:
        work = Path(tmp)
        artwork = work / "artwork-no-text.pdf"
        run(
            [
                "gs", "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER",
                "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4",
                "-dDeterministicID", "-dOmitInfoDate",
                "-dFILTERTEXT", "-dAutoRotatePages=/None",
                f"-sOutputFile={artwork}", str(source.resolve()),
            ],
            cwd=work,
            env=env,
        )
        tex = work / "reletter.tex"
        tex.write_text(make_tex(artwork))
        run(
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex.name],
            cwd=work,
            env=env,
        )
        shutil.copyfile(work / "reletter.pdf", output)

    png_stem = output.with_suffix("")
    run(
        [
            "pdftoppm", "-png", "-r", "300", "-singlefile",
            str(output), str(png_stem),
        ],
        cwd=output.parent,
        env=env,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    compose(args.source, args.output)


if __name__ == "__main__":
    main()
