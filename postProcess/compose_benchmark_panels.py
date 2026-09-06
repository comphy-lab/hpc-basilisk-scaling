#!/usr/bin/env python3
"""Pair the existing vector scaling plots with representative simulation images.

Requires pdflatex and its standalone, graphicx and amsmath packages. The input
scaling PDFs are embedded unchanged; this step never reads simulation timings.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "figures"
PANELS = {
    "bursting": ("bursting-uniform.pdf", "bursting-simulation.pdf",
                 "bursting-uniform-illustrated.pdf", "Representative simulation"),
    "taylorculick": ("taylorculick-uniform.pdf", "taylorculick-simulation.pdf",
                    "taylorculick-uniform-illustrated.pdf", "Representative simulation"),
    "drop-impact": ("drop-impact-uniform.pdf", "drop-impact-simulation.pdf",
                   "drop-impact-uniform-illustrated.pdf", "Representative simulation"),
    "ve3d": ("ve3d-impact-uniform.pdf", "three-dimensional-simulation.pdf",
             "ve3d-impact-uniform-illustrated.pdf", "3D coalescence illustration"),
}


def tex_path(path: Path) -> str:
    """Represent an existing PDF path without allowing TeX control syntax."""
    if not path.is_file():
        raise FileNotFoundError(path)
    value = str(path.resolve())
    if any(char in value for char in "{}%\\\r\n"):
        raise ValueError(f"unsupported TeX path characters: {path}")
    return r"\detokenize{" + value + "}"


def compose(case: str, output_dir: Path) -> Path:
    scaling, snapshot, filename, heading = PANELS[case]
    left = tex_path(FIGURES / scaling)
    right = tex_path(FIGURES / snapshot)
    document = r"""\documentclass[border=2mm]{standalone}
\usepackage{graphicx}
\usepackage{amsmath}
\setlength{\parindent}{0pt}
\begin{document}
\begin{tabular}{@{}c@{\hspace{5mm}}c@{}}
\begin{minipage}[t]{170mm}
  {\fontsize{24}{28}\selectfont $(a)$}\par\vspace{2mm}
  \makebox[170mm][c]{\includegraphics[width=168mm,height=160mm,keepaspectratio]{LEFT}}
\end{minipage}&
\begin{minipage}[t]{170mm}
  {\fontsize{24}{28}\selectfont $(b)$\hfill
   \fontsize{18}{22}\selectfont HEADING\hfill}\par\vspace{2mm}
  \makebox[170mm][c]{\includegraphics[width=168mm,height=160mm,keepaspectratio]{RIGHT}}
\end{minipage}
\end{tabular}
\end{document}
""".replace("LEFT", left).replace("RIGHT", right).replace("HEADING", heading)
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / filename
    with tempfile.TemporaryDirectory(prefix="benchmark-panels-") as temporary:
        build = Path(temporary)
        tex = build / "panels.tex"
        tex.write_text(document)
        result = subprocess.run(
            ["pdflatex", "-halt-on-error", "-interaction=nonstopmode", tex.name],
            cwd=build, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        if result.returncode:
            raise RuntimeError(result.stdout)
        built = build / "panels.pdf"
        if not built.is_file() or not built.stat().st_size:
            raise RuntimeError("pdflatex produced no composite PDF")
        shutil.copyfile(built, output)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=PANELS, action="append")
    parser.add_argument("--output-dir", type=Path, default=FIGURES)
    args = parser.parse_args()
    for case in args.case or PANELS:
        print(compose(case, args.output_dir))


if __name__ == "__main__":
    main()
