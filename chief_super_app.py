from __future__ import annotations

import math
import json
import re
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st
from PIL import Image
from streamlit_cropper import st_cropper

from chief_render_cv import render_and_compile_chief, cleanup_workdir


st.set_page_config(page_title="Chief CV Builder", layout="wide")

USERS_DIR = Path("users")
USERS_DIR.mkdir(exist_ok=True)

TARGET_W = 1525
TARGET_H = 700
TARGET_RATIO = TARGET_W / TARGET_H

def safe_integer_ratio(
    img_w: int,
    img_h: int,
    base_w: int = TARGET_W,
    base_h: int = TARGET_H,
) -> tuple[int, int]:
    """
    Build an integer aspect ratio for st_cropper.

    Steps:
    1) height_ratio = img_h / 700, width_ratio = img_w / 1525
    2) If both > 1.1 -> return (1525, 700)
    3) Else smallest_ratio = min(height_ratio, width_ratio) / 1.1
       new_width_box  = int(1525 * smallest_ratio)
       new_height_box = int(700  * smallest_ratio)
    4) Reduce (w,h) by gcd, keep sane minimums.
    """
    if img_w <= 0 or img_h <= 0:
        return (base_w, base_h)

    height_ratio = img_h / base_h
    width_ratio = img_w / base_w

    margin_factor = 7.5

    if height_ratio > margin_factor and width_ratio > margin_factor:
        return (base_w, base_h)

    smallest_ratio = min(height_ratio, width_ratio) / margin_factor

    new_w = max(1, int(base_w * smallest_ratio))
    new_h = max(1, int(base_h * smallest_ratio))

    # Reduce to simplest integers (helps some cropper implementations)
    # g = math.gcd(new_w, new_h)
    # new_w //= g
    # new_h //= g

    # Safety: avoid degenerate ratios
    if new_w < 2 or new_h < 2:
        return (base_w, base_h)

    return (new_w, new_h)

# -----------------------------
# Profile storage helpers
# -----------------------------
def slugify_profile(first_name: str, last_name: str) -> str:
    base = f"{first_name}_{last_name}".strip().lower()
    base = re.sub(r"\s+", "_", base)
    base = re.sub(r"[^a-z0-9_]+", "", base)
    base = re.sub(r"_+", "_", base).strip("_")
    return base or "profile"


def list_profiles() -> List[str]:
    if not USERS_DIR.exists():
        return []
    return sorted([p.name for p in USERS_DIR.iterdir() if p.is_dir()])


def profile_paths(profile_id: str) -> Dict[str, Path]:
    pdir = USERS_DIR / profile_id
    return {
        "dir": pdir,
        "data": pdir / "data.txt",
        "banner": pdir / "photo_banner.png",
        "pdf": pdir / "chief_cv.pdf",
        "tex": pdir / "main.tex",
    }


def load_profile_into_state(profile_id: str) -> None:
    paths = profile_paths(profile_id)
    if not paths["dir"].exists():
        st.warning(f"Profile folder not found: {paths['dir']}")
        return

    # Load data.txt (JSON stored in txt)
    if paths["data"].exists():
        try:
            raw = paths["data"].read_text(encoding="utf-8")
            data = json.loads(raw)
        except Exception as e:
            st.error(f"Failed to load profile data.txt: {e}")
            return
    else:
        st.warning("Profile has no data.txt; using defaults.")
        data = {}

    # Ensure expected structure exists
    merged = default_data()
    merged.update(data)  # user overrides

    # Load banner if present (as bytes so renderer uses it)
    if paths["banner"].exists():
        merged["photo_banner_bytes"] = paths["banner"].read_bytes()
        merged["photo_banner_path"] = "photo_banner.png"
    else:
        merged.pop("photo_banner_bytes", None)
        merged["photo_banner_path"] = "photo_banner.png"

    st.session_state.data = merged
    st.session_state.selected_profile = profile_id
    st.session_state.profile_loaded_once = True


def save_profile_from_state(profile_id: str, result_pdf: bytes, result_tex: str) -> None:
    paths = profile_paths(profile_id)
    paths["dir"].mkdir(parents=True, exist_ok=True)

    data = dict(st.session_state.data)

    # Persist banner:
    #  - If user uploaded/cropped, it's in photo_banner_bytes
    #  - Otherwise, leave existing banner if present; or copy default is optional
    banner_bytes = data.get("photo_banner_bytes")
    if isinstance(banner_bytes, (bytes, bytearray)) and len(banner_bytes) > 0:
        paths["banner"].write_bytes(bytes(banner_bytes))

    # Save data.txt as JSON (but extension remains .txt as requested)
    # Remove large bytes from saved JSON
    data.pop("photo_banner_bytes", None)

    paths["data"].write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # Save outputs
    paths["pdf"].write_bytes(result_pdf)
    paths["tex"].write_text(result_tex, encoding="utf-8")


# -----------------------------
# App data defaults
# -----------------------------
def default_data() -> Dict[str, Any]:
    return {
        "first_name": "Chief",
        "last_name": "Chiefsson",
        "title": "PROJECT MANAGER",
        "profile_text": (
            "Project manager, CAE engineer, and product manager with a strong foundation "
            "in mechanical design, simulation, and product development."
        ),
        "photo_banner_path": "photo_banner.png",

        "right_blocks": [
            {"heading": "Previous positions", "body": "Project Manager, CAE Engineer, Product Manager"},
            {"heading": "Key Competences", "body": "Leadership, Problem solving, Project Management, Analytics, Product development, FEM, CFD"},
            {"heading": "Skills", "body": "Python, Matlab, Microsoft Office, Hypermesh, Radioss, AcuSolve"},
            {"heading": "Keywords", "body": "Project management, engineering, leadership, finite element method, product development, R&D, CFD, Product management, simulation, CAE"},
        ],

        "experience": [],

        "summary_enabled": True,
        "employment_rows": [
            {"year": "2026", "org": "CHIEF CONSULTING AB"},
            {"year": "2025", "org": "MARSHALL GROUP"},
            {"year": "2022-2025", "org": "POC SPORTS"},
        ],
        "extracurricular_rows": [
            {"year": "2021-2022", "text": "SIGMA INDUSTRY STUDENT AMBASSADOR"},
            {"year": "2021", "text": "ABB SUSTAINABLE TALENT PROGRAM"},
        ],
        "about_me": (
            "Passionate about moving in nature, whether I’m walking, running or cycling. "
            "In my free time I like to travel, cook dinner with friends and read books."
        ),
        "education_rows": [
            {"years": "2020--2022", "text": "M.Sc. Mechanical Engineering: Solid Mechanics, KTH Royal Institute of Technology"},
            {"years": "2016--2020", "text": "B.Sc. Mechanical Engineering, KTH Royal Institute of Technology"},
            {"years": "2019--2020", "text": "French, general course, France Langue, Nice, France"},
        ],
        "languages_block": "Swedish -- Mother tongue\nEnglish -- Fluent\nFrench -- Fluent",
        "other_skills_block": "B driver’s license",

        "blank_last_page": True,
    }


def init_state() -> None:
    if "data" not in st.session_state:
        st.session_state.data = default_data()
    if "selected_profile" not in st.session_state:
        st.session_state.selected_profile = None  # profile_id string
    if "profile_loaded_once" not in st.session_state:
        st.session_state.profile_loaded_once = False

    if "last_pdf" not in st.session_state:
        st.session_state.last_pdf = None
    if "last_tex" not in st.session_state:
        st.session_state.last_tex = None
    if "last_workdir" not in st.session_state:
        st.session_state.last_workdir = None


# -----------------------------
# UI helpers you already had
# -----------------------------
def move_item(lst: List[Dict[str, Any]], idx: int, direction: int) -> None:
    j = idx + direction
    if j < 0 or j >= len(lst):
        return
    lst[idx], lst[j] = lst[j], lst[idx]


def add_right_block() -> None:
    st.session_state.data["right_blocks"].append({"heading": "", "body": ""})


def add_experience() -> None:
    st.session_state.data["experience"].append(
        {"dates_company": "", "role": "", "tasks": "", "contribution": "", "outcome": "", "keywords": ""}
    )


def add_employment_row() -> None:
    st.session_state.data["employment_rows"].append({"year": "", "org": ""})


def add_extracurricular_row() -> None:
    st.session_state.data["extracurricular_rows"].append({"year": "", "text": ""})


def add_education_row() -> None:
    st.session_state.data["education_rows"].append({"years": "", "text": ""})


# -----------------------------
# Start app
# -----------------------------
init_state()
data = st.session_state.data

# Sidebar: profile management
with st.sidebar:
    st.header("Profiles")

    profiles = list_profiles()
    choices = ["(New / unsaved)"] + profiles
    current = st.session_state.selected_profile
    idx = 0 if current is None else (profiles.index(current) + 1 if current in profiles else 0)

    picked = st.selectbox("Select a profile", choices, index=idx)

    if picked != "(New / unsaved)":
        # Load on click so we don't reload on every rerun
        if st.button("Load selected profile"):
            load_profile_into_state(picked)
            st.rerun()
    else:
        if st.button("Start a new profile"):
            st.session_state.data = default_data()
            st.session_state.selected_profile = None
            st.session_state.profile_loaded_once = True
            st.rerun()

    st.divider()
    st.caption("Profiles are stored under the local `users/` folder.")


st.title("Chief CV Builder")

left, right = st.columns([1.15, 1.0], gap="large")

with left:
    st.subheader("Page 1")
    c1, c2 = st.columns(2)
    data["first_name"] = c1.text_input("First name (big)", data["first_name"])
    data["last_name"] = c2.text_input("Last name (big)", data["last_name"])
    data["title"] = st.text_input("Title (on highlight)", data["title"])
    data["profile_text"] = st.text_area("Profile text", data["profile_text"], height=140)

    # -------- Banner uploader + cropper (keeps your current logic) --------
    st.markdown("### Photo banner")
    uploaded = st.file_uploader(
        "Upload banner image",
        type=["png", "jpg", "jpeg"],
        key="banner_uploader",
    )

    # If a profile is loaded and has a saved banner, show it as "current"
    if uploaded is None and isinstance(data.get("photo_banner_bytes"), (bytes, bytearray)):
        st.image(Image.open(BytesIO(data["photo_banner_bytes"])), caption="Current saved banner", width="stretch")

    if uploaded is not None:
        raw = uploaded.getvalue()
        try:
            img = Image.open(BytesIO(raw)).convert("RGB")

            st.caption("Crop (ratio fixed near 1525×700). You can move + resize the box.")

            # Use integer ratio pair (you wanted integer enforcement)
            # (keeps ratio exact)
            rw, rh = 1525, 700

            cropped_img = st_cropper(
                img,
                aspect_ratio=(rw, rh),
                box_color="#000000",
                return_type="image",
                realtime_update=True,
            )

            # Normalize output size for LaTeX stability
            cropped_img = cropped_img.resize((1525, 700), Image.LANCZOS)

            st.image(cropped_img, caption="Cropped banner preview", width="stretch")

            out = BytesIO()
            cropped_img.save(out, format="PNG", optimize=True)

            data["photo_banner_bytes"] = out.getvalue()
            data["photo_banner_path"] = "photo_banner.png"

        except Exception as e:
            st.error(f"Could not load/crop the uploaded image: {e}")

    st.divider()

    # -------- Right blocks --------
    st.subheader("Right column blocks")
    if st.button("➕ Add right-column block"):
        add_right_block()

    for i, blk in enumerate(data["right_blocks"]):
        with st.expander(f"Block #{i+1}: {blk.get('heading','').strip() or '(new)'}", expanded=False):
            cols = st.columns([1, 1, 1])
            if cols[1].button("⬆️ Move up", key=f"rb_up_{i}"):
                move_item(data["right_blocks"], i, -1)
                st.rerun()
            if cols[2].button("⬇️ Move down", key=f"rb_dn_{i}"):
                move_item(data["right_blocks"], i, +1)
                st.rerun()

            blk["heading"] = st.text_input("Heading", blk["heading"], key=f"rb_h_{i}")
            blk["body"] = st.text_area("Body (plain text)", blk["body"], height=90, key=f"rb_b_{i}")

            if st.button("🗑️ Delete this block", key=f"rb_del_{i}"):
                data["right_blocks"].pop(i)
                st.rerun()

    st.divider()

    # -------- Experience --------
    st.subheader("Experience")
    st.caption("Entries will flow across pages automatically.")
    if st.button("➕ Add experience entry"):
        add_experience()

    for i, e in enumerate(data["experience"]):
        with st.expander(f"Experience #{i+1}: {e.get('dates_company','').strip() or '(new)'}", expanded=False):
            cols = st.columns([1, 1, 1])
            if cols[1].button("⬆️ Move up", key=f"exp_up_{i}"):
                move_item(data["experience"], i, -1)
                st.rerun()
            if cols[2].button("⬇️ Move down", key=f"exp_dn_{i}"):
                move_item(data["experience"], i, +1)
                st.rerun()

            e["dates_company"] = st.text_input("Dates + Company", e["dates_company"], key=f"exp_dc_{i}")
            e["role"] = st.text_input("Role", e["role"], key=f"exp_role_{i}")
            e["tasks"] = st.text_area("Tasks (paragraphs)", e["tasks"], height=120, key=f"exp_tasks_{i}")
            e["contribution"] = st.text_area("Contribution (paragraphs)", e["contribution"], height=120, key=f"exp_contrib_{i}")
            e["outcome"] = st.text_area("Outcome (paragraphs)", e["outcome"], height=120, key=f"exp_outcome_{i}")
            e["keywords"] = st.text_area("Keywords", e["keywords"], height=70, key=f"exp_kw_{i}")

            if st.button("🗑️ Delete this experience entry", key=f"exp_del_{i}"):
                data["experience"].pop(i)
                st.rerun()

    st.divider()

    # -------- Summary --------
    st.subheader("Summary page (page 4)")
    data["summary_enabled"] = st.checkbox("Enable summary page", value=bool(data.get("summary_enabled", True)))
    data["blank_last_page"] = st.checkbox("Add blank last page", value=bool(data.get("blank_last_page", True)))

    st.markdown("**Employment rows**")
    if st.button("➕ Add employment row"):
        add_employment_row()
    for i, row in enumerate(data["employment_rows"]):
        c1, c2, c3 = st.columns([0.25, 0.65, 0.10])
        row["year"] = c1.text_input("Year", row["year"], key=f"emp_y_{i}")
        row["org"] = c2.text_input("Organization", row["org"], key=f"emp_o_{i}")
        if c3.button("🗑️", key=f"emp_del_{i}"):
            data["employment_rows"].pop(i)
            st.rerun()

    st.markdown("**Extracurricular rows**")
    if st.button("➕ Add extracurricular row"):
        add_extracurricular_row()
    for i, row in enumerate(data["extracurricular_rows"]):
        c1, c2, c3 = st.columns([0.25, 0.65, 0.10])
        row["year"] = c1.text_input("Year", row["year"], key=f"ext_y_{i}")
        row["text"] = c2.text_input("Text", row["text"], key=f"ext_t_{i}")
        if c3.button("🗑️", key=f"ext_del_{i}"):
            data["extracurricular_rows"].pop(i)
            st.rerun()

    data["about_me"] = st.text_area("About me", data.get("about_me", ""), height=100)

    st.markdown("**Education rows**")
    if st.button("➕ Add education row"):
        add_education_row()
    for i, row in enumerate(data["education_rows"]):
        c1, c2, c3 = st.columns([0.30, 0.60, 0.10])
        row["years"] = c1.text_input("Years", row["years"], key=f"edu_y_{i}")
        row["text"] = c2.text_input("Text", row["text"], key=f"edu_t_{i}")
        if c3.button("🗑️", key=f"edu_del_{i}"):
            data["education_rows"].pop(i)
            st.rerun()

    cL, cR = st.columns(2)
    data["languages_block"] = cL.text_area("Languages (one per line)", data.get("languages_block", ""), height=110)
    data["other_skills_block"] = cR.text_area("Other skills (one per line)", data.get("other_skills_block", ""), height=110)

    st.divider()

    # -------- Export + Save profile --------
    st.subheader("Export")
    render_btn = st.button("🚀 Generate PDF", type="primary")

    if render_btn:
        if st.session_state.last_workdir:
            cleanup_workdir(st.session_state.last_workdir)
            st.session_state.last_workdir = None

        try:
            result = render_and_compile_chief(data, template_path="templates", template_name="main_chief.tex.j2")
            st.session_state.last_pdf = result.pdf_bytes
            st.session_state.last_tex = result.tex_str
            st.session_state.last_workdir = result.workdir

            # Decide profile id:
            # - if selected -> overwrite/update
            # - if none -> create from first/last
            profile_id = st.session_state.selected_profile
            if not profile_id:
                profile_id = slugify_profile(data.get("first_name", ""), data.get("last_name", ""))
                st.session_state.selected_profile = profile_id

            save_profile_from_state(profile_id, result_pdf=result.pdf_bytes, result_tex=result.tex_str)

            st.success(f"PDF generated and saved under users/{profile_id}/")

        except Exception as e:
            st.error("Failed to compile LaTeX.")
            st.text_area("Build log", str(e), height=350)
            if st.session_state.last_workdir:
                st.info(f"Temp build folder: {st.session_state.last_workdir}")

    if st.session_state.last_pdf:
        st.download_button(
            "⬇️ Download PDF",
            data=st.session_state.last_pdf,
            file_name="chief_cv.pdf",
            mime="application/pdf",
        )
        st.download_button(
            "⬇️ Download LaTeX (main.tex)",
            data=st.session_state.last_tex or "",
            file_name="main.tex",
            mime="text/plain",
        )

with right:
    st.subheader("Preview")
    if st.session_state.last_pdf:
        try:
            st.pdf(st.session_state.last_pdf)
        except Exception:
            st.info("PDF preview is unavailable here. Download the PDF to view it.")
    else:
        st.info("Click **Generate PDF** to build and preview your CV.")
