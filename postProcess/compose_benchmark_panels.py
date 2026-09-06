#!/usr/bin/env python3
"""Stack scaling plots and temporal sequences at their final 166 mm width.

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
    "bursting": ("bursting-uniform-report.pdf", "bursting-simulation.pdf",
                 "bursting-uniform-illustrated.pdf"),
    "taylorculick": ("taylorculick-uniform-report.pdf", "taylorculick-simulation.pdf",
                    "taylorculick-uniform-illustrated.pdf"),
    "drop-impact": ("drop-impact-uniform-report.pdf", "drop-impact-simulation.pdf",
                   "drop-impact-uniform-illustrated.pdf"),
    "ve3d": ("ve3d-impact-uniform-report.pdf", "three-dimensional-simulation.pdf",
             "ve3d-impact-uniform-illustrated.pdf"),
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
    scaling, snapshot, filename = PANELS[case]
    top = tex_path(FIGURES / scaling)
    bottom = tex_path(FIGURES / snapshot)
    document = r"""\documentclass[border=0pt]{standalone}
\usepackage{graphicx}
\usepackage{amsmath}
\setlength{\parindent}{0pt}
\begin{document}
\begin{minipage}{166mm}
  {\fontsize{11}{12}\selectfont $(a)$}\par
  \includegraphics[width=166mm]{TOP}\par\vspace{1mm}
  {\fontsize{11}{12}\selectfont $(b)$}\par
  \includegraphics[width=166mm]{BOTTOM}
\end{minipage}
\end{document}
""".replace("TOP", top).replace("BOTTOM", bottom)
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
