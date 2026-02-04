from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

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
    """Escape LaTeX special characters in user-provided text."""
    if value is None:
        return ""
    s = str(value)

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


def _copy_asset_to_workdir(
    asset_path: Path,
    workdir: Path,
) -> str:
    """
    Copy asset into build folder and return the basename (so LaTeX can load it).
    """
    dest = workdir / asset_path.name
    shutil.copyfile(asset_path, dest)
    return dest.name


def _resolve_asset_path(
    maybe_path: Optional[str],
    template_dir: Path,
    project_root: Path,
    default_name: str,
) -> Optional[Path]:
    """
    Resolve an asset path by trying:
    - explicit data path (absolute or relative)
    - template_dir/default_name
    - project_root/default_name
    """
    if maybe_path:
        p = Path(maybe_path)
        if p.is_absolute() and p.exists():
            return p
        # relative: try relative to project root first
        p1 = (project_root / p).resolve()
        if p1.exists():
            return p1
        # or relative to templates dir
        p2 = (template_dir / p).resolve()
        if p2.exists():
            return p2

    # fallback default
    p3 = (template_dir / default_name).resolve()
    if p3.exists():
        return p3
    p4 = (project_root / default_name).resolve()
    if p4.exists():
        return p4

    return None


def render_and_compile_chief(
    data: Dict[str, Any],
    template_path: str = "templates",
    template_name: str = "main_chief.tex.j2",
) -> RenderResult:
    """
    Render + compile the Chief template with LuaLaTeX via latexmk.
    Also copies required images into temp build dir so \\includegraphics works.
    """
    template_dir = Path(template_path).resolve()
    project_root = Path.cwd().resolve()

    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(enabled_extensions=()),
        trim_blocks=True,
        lstrip_blocks=True,
        block_start_string="((*",
        block_end_string="*))",
        comment_start_string="((#",
        comment_end_string="#))",
    )
    env.filters["latex"] = latex_escape

    template = env.get_template(template_name)

    # Build in a temp directory
    workdir = Path(tempfile.mkdtemp(prefix="cv_build_"))

    # Resolve + copy assets into workdir, and force template to use basenames
    # so LaTeX finds them relative to workdir.
    banner_src = _resolve_asset_path(
        data.get("photo_banner_path"),
        template_dir=template_dir,
        project_root=project_root,
        default_name="photo_banner.png",
    )
    highlight_src = _resolve_asset_path(
        data.get("highlight_path"),
        template_dir=template_dir,
        project_root=project_root,
        default_name="highlight.png",
    )

    data = dict(data)  # copy
    if banner_src:
        data["photo_banner_path"] = _copy_asset_to_workdir(banner_src, workdir)
    if highlight_src:
        data["highlight_path"] = _copy_asset_to_workdir(highlight_src, workdir)

    tex_str = template.render(**data)

    # Write main.tex
    (workdir / "main.tex").write_text(tex_str, encoding="utf-8")

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
            cwd=str(workdir),
        )
    except Exception as ex:
        raise RuntimeError(f"{ex}\n\nTemp build folder: {workdir}") from ex

    pdf_path = workdir / "main.pdf"
    if not pdf_path.exists():
        raise RuntimeError("Build succeeded but main.pdf was not created (unexpected).")

    return RenderResult(pdf_bytes=pdf_path.read_bytes(), tex_str=tex_str, workdir=str(workdir))


def cleanup_workdir(workdir: str) -> None:
    if workdir and os.path.isdir(workdir):
        shutil.rmtree(workdir, ignore_errors=True)
