from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from jinja2 import Environment, FileSystemLoader, select_autoescape


@dataclass
class RenderResult:
    pdf_bytes: bytes
    tex_str: str
    workdir: str


def _run(cmd: list[str], cwd: str) -> None:
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "Command failed:\n"
            f"{' '.join(cmd)}\n\n"
            "---- Build output ----\n"
            f"{proc.stdout}"
        )


def latex_escape(value: Any) -> str:
    """
    Escape LaTeX special characters in user-provided text so arbitrary input
    (e.g. '50%', 'R&D', 'foo_bar', '$100') can't break compilation.
    """
    if value is None:
        return ""

    s = str(value)

    # Important: escape backslash first (otherwise later replacements can introduce \)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }

    return "".join(replacements.get(ch, ch) for ch in s)


def render_and_compile(data: Dict[str, Any], template_path: str = "templates") -> RenderResult:
    """
    Renders templates/main.tex.j2 into main.tex and compiles to main.pdf using latexmk.
    Returns PDF bytes and the rendered TeX.

    NOTE: Your template should use the filter |latex for any user-provided fields.
    Example: {{ first_name|latex }}
    """
    env = Environment(
        loader=FileSystemLoader(template_path),
        autoescape=select_autoescape(enabled_extensions=()),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # Register our LaTeX-escaping filter
    env.filters["latex"] = latex_escape
    print("Registered Jinja filter: latex")

    template = env.get_template("main.tex.j2")
    tex_str = template.render(**data)

    # Build in a temp directory
    workdir = tempfile.mkdtemp(prefix="cv_build_")
    wd = Path(workdir)

    # Write main.tex
    (wd / "main.tex").write_text(tex_str, encoding="utf-8")

    # Compile (LuaLaTeX)
    try:
        _run(
            [
                "latexmk",
                "-lualatex",
                "-interaction=nonstopmode",
                "-halt-on-error",
                "main.tex",
            ],
            cwd=workdir,
        )
    except Exception as ex:
        raise RuntimeError(f"{ex}\n\nTemp build folder: {workdir}") from ex

    pdf_path = wd / "main.pdf"
    if not pdf_path.exists():
        raise RuntimeError("Build succeeded but main.pdf was not created (unexpected).")

    pdf_bytes = pdf_path.read_bytes()
    return RenderResult(pdf_bytes=pdf_bytes, tex_str=tex_str, workdir=workdir)


def cleanup_workdir(workdir: str) -> None:
    """Optional: call to remove the temp build folder."""
    if workdir and os.path.isdir(workdir):
        shutil.rmtree(workdir, ignore_errors=True)
