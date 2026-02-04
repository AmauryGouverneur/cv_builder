from __future__ import annotations

from pathlib import Path
import sys

from render_cv import render_and_compile


def main() -> int:
    # Adjust if your folder is actually named "template" not "templates"
    template_path = "templates"

    data = {
        "first_name": "Amaury",
        "last_name": "Gouverneur",
        "email": "amauryg@kth.se",
        "phone": "+46 70 123 45 67",
        "website_text": "homepage",
        "website_url": "https://example.com/~amaury_g?x=1&y=2",
        "linkedin_url": "https://www.linkedin.com/in/example_profile",
        "scholar_url": "https://scholar.google.com/citations?user=XXXX",

        "profile_text": "PhD student in ML. I like 50% theory & 50% practice. R&D, foo_bar, $100.",
        "research_expertise": "Bandits, information theory, reinforcement learning.",

        "education": [
            {
                "variant": "full",
                "institution": "KTH Royal Institute of Technology",
                "city": "Stockholm",
                "country": "Sweden",
                "start": "Sep 2020",
                "end": "Present",
                "degree": "PhD in Machine Learning",
                "info1": "Advisor: Someone & Someoneelse",
                "info2": "Thesis: Information-theoretic analysis of Thompson sampling",
                "info3": "GPA: N/A",
            },
            {
                "variant": "small",
                "institution": "Some University",
                "city": "Paris",
                "country": "France",
                "start": "Sep 2018",
                "end": "Jun 2020",
                "degree": "MSc in Mathematics",
                "info1": "Graduated with honors",
                "info2": "",
                "info3": "",
            },
        ],

        "work": [
            {
                "role": "Research Intern",
                "company": "Example Labs",
                "city": "Zurich",
                "country": "Switzerland",
                "start": "Jun 2024",
                "end": "Aug 2024",
                "bullets": [
                    "Built a Streamlit app to generate LaTeX CVs.",
                    "Handled edge cases: %, &, _, $, #, {, }, ~, ^ and backslashes (\\).",
                ],
            }
        ],

        "selected_project": "Selected project text with special chars: 100% improvement & robust pipeline.",
        "skills_languages": "Python, C++, LaTeX",
        "skills_libraries": "NumPy, PyTorch, JAX",
        "skills_tools": "Git, Linux, Docker, Streamlit",
        "spoken_languages": "French (native), English (fluent), Swedish (basic)",
        "other_interests": "Climbing, chess, travel.",
    }

    result = render_and_compile(data, template_path=template_path)

    tex = result.tex_str

    # 1) Make sure template tags didn't leak through (common when delimiters mismatch)
    # If you switched to ((* ... *)), keep both checks.
    suspicious = ["{% ", "%}", "{# ", "#}", "((*", "*))", "((#", "#))"]
    leaked = [t for t in suspicious if t in tex]
    if leaked:
        print("ERROR: Rendered TeX still contains template syntax:", leaked)
        print("This usually means your Jinja delimiters in render_cv.py don't match the template.")
        return 2

    # 2) Basic PDF signature check
    if not result.pdf_bytes.startswith(b"%PDF"):
        print("ERROR: Output does not look like a PDF (missing %PDF header).")
        return 3

    outdir = Path("out")
    outdir.mkdir(exist_ok=True)
    (outdir / "main.tex").write_text(tex, encoding="utf-8")
    (outdir / "main.pdf").write_bytes(result.pdf_bytes)

    print("OK: Render + compile succeeded.")
    print("Wrote:")
    print(" - out/main.tex")
    print(" - out/main.pdf")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
