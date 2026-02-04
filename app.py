from __future__ import annotations

import streamlit as st
from typing import Dict, Any, List

from render_cv import render_and_compile, cleanup_workdir


st.set_page_config(page_title="LaTeX CV Builder", layout="wide")


def init_state() -> None:
    if "data" not in st.session_state:
        st.session_state.data = {
            "first_name": "Amaury",
            "last_name": "Gouverneur",
            "email": "",
            "phone": "",
            "website_text": "",
            "website_url": "",
            "linkedin_url": "",
            "scholar_url": "",
            "profile_text": "",
            "research_expertise": "",
            "education": [],
            "work": [],
            "selected_project": "",
            "skills_languages": "",
            "skills_libraries": "",
            "skills_tools": "",
            "spoken_languages": "",
            "other_interests": "",
        }
    if "last_pdf" not in st.session_state:
        st.session_state.last_pdf = None
    if "last_tex" not in st.session_state:
        st.session_state.last_tex = None
    if "last_workdir" not in st.session_state:
        st.session_state.last_workdir = None


def add_education():
    st.session_state.data["education"].append(
        {
            "variant": "full",
            "institution": "",
            "city": "",
            "country": "",
            "start": "",
            "end": "",
            "degree": "",
            "info1": "",
            "info2": "",
            "info3": "",
        }
    )


def add_work():
    st.session_state.data["work"].append(
        {
            "role": "",
            "company": "",
            "city": "",
            "country": "",
            "start": "",
            "end": "",
            "bullets": [],
        }
    )


def move_item(lst: List[Dict[str, Any]], idx: int, direction: int) -> None:
    j = idx + direction
    if j < 0 or j >= len(lst):
        return
    lst[idx], lst[j] = lst[j], lst[idx]


init_state()
data = st.session_state.data

st.title("LaTeX CV Builder (V1)")

left, right = st.columns([1.1, 1.0], gap="large")

with left:
    st.subheader("Basics")
    c1, c2 = st.columns(2)
    data["first_name"] = c1.text_input("First name", data["first_name"])
    data["last_name"] = c2.text_input("Last name", data["last_name"])

    data["email"] = st.text_input("Email", data["email"])
    data["phone"] = st.text_input("Phone", data["phone"])

    c3, c4 = st.columns(2)
    data["website_text"] = c3.text_input("Website text (shown)", data["website_text"])
    data["website_url"] = c4.text_input("Website URL (link)", data["website_url"])

    c5, c6 = st.columns(2)
    data["linkedin_url"] = c5.text_input("LinkedIn URL", data["linkedin_url"])
    data["scholar_url"] = c6.text_input("Scholar URL", data["scholar_url"])

    st.divider()

    st.subheader("Profile (optional)")
    data["profile_text"] = st.text_area("Profile text", data["profile_text"], height=120)

    st.subheader("Research Expertise (optional)")
    data["research_expertise"] = st.text_area("Research expertise", data["research_expertise"], height=80)

    st.divider()

    st.subheader("Education (optional)")
    st.caption("Add entries. If none are added, the section is removed from the PDF.")
    if st.button("➕ Add education entry"):
        add_education()

    for i, edu in enumerate(data["education"]):
        with st.expander(f"Education #{i+1}: {edu.get('institution','').strip() or '(new)'}", expanded=False):
            cols = st.columns([1, 1, 1])
            edu["variant"] = cols[0].selectbox("Variant", ["full", "small"], index=0 if edu["variant"] == "full" else 1)
            if cols[1].button("⬆️ Move up", key=f"edu_up_{i}"):
                move_item(data["education"], i, -1)
                st.rerun()
            if cols[2].button("⬇️ Move down", key=f"edu_down_{i}"):
                move_item(data["education"], i, +1)
                st.rerun()

            edu["institution"] = st.text_input("Institution", edu["institution"], key=f"edu_inst_{i}")
            cA, cB = st.columns(2)
            edu["city"] = cA.text_input("City", edu["city"], key=f"edu_city_{i}")
            edu["country"] = cB.text_input("Country", edu["country"], key=f"edu_country_{i}")

            cC, cD = st.columns(2)
            edu["start"] = cC.text_input("From (e.g., Sep 2018)", edu["start"], key=f"edu_start_{i}")
            edu["end"] = cD.text_input("To (e.g., Jun 2020 / Present)", edu["end"], key=f"edu_end_{i}")

            edu["degree"] = st.text_input("Degree / title", edu["degree"], key=f"edu_degree_{i}")

            edu["info1"] = st.text_input("Other info line 1 (optional)", edu.get("info1",""), key=f"edu_info1_{i}")

            if edu["variant"] == "full":
                edu["info2"] = st.text_input("Other info line 2 (optional)", edu.get("info2",""), key=f"edu_info2_{i}")
                edu["info3"] = st.text_input("Other info line 3 (optional)", edu.get("info3",""), key=f"edu_info3_{i}")
            else:
                edu["info2"] = ""
                edu["info3"] = ""

            if st.button("🗑️ Delete this education entry", key=f"edu_del_{i}"):
                data["education"].pop(i)
                st.rerun()

    st.divider()

    st.subheader("Work Experience (optional)")
    st.caption("Add roles and bullet points. If empty, section is removed.")
    if st.button("➕ Add work entry"):
        add_work()

    for i, job in enumerate(data["work"]):
        with st.expander(f"Work #{i+1}: {job.get('company','').strip() or '(new)'}", expanded=False):
            cols = st.columns([1, 1, 1])
            if cols[1].button("⬆️ Move up", key=f"job_up_{i}"):
                move_item(data["work"], i, -1)
                st.rerun()
            if cols[2].button("⬇️ Move down", key=f"job_down_{i}"):
                move_item(data["work"], i, +1)
                st.rerun()

            job["role"] = st.text_input("Role", job["role"], key=f"job_role_{i}")
            job["company"] = st.text_input("Company", job["company"], key=f"job_company_{i}")

            cA, cB = st.columns(2)
            job["city"] = cA.text_input("City", job["city"], key=f"job_city_{i}")
            job["country"] = cB.text_input("Country", job["country"], key=f"job_country_{i}")

            cC, cD = st.columns(2)
            job["start"] = cC.text_input("From (e.g., Mar 2025)", job["start"], key=f"job_start_{i}")
            job["end"] = cD.text_input("To (e.g., Jul 2025 / Present)", job["end"], key=f"job_end_{i}")

            st.markdown("**Bullets**")
            if "bullets" not in job or job["bullets"] is None:
                job["bullets"] = []

            if st.button("➕ Add bullet", key=f"job_add_bullet_{i}"):
                job["bullets"].append("")
                st.rerun()

            for j, b in enumerate(job["bullets"]):
                c1, c2 = st.columns([0.92, 0.08])
                job["bullets"][j] = c1.text_input(f"Bullet {j+1}", b, key=f"job_{i}_b_{j}")
                if c2.button("🗑️", key=f"job_{i}_b_del_{j}"):
                    job["bullets"].pop(j)
                    st.rerun()

            if st.button("🗑️ Delete this work entry", key=f"job_del_{i}"):
                data["work"].pop(i)
                st.rerun()

    st.divider()

    st.subheader("Selected Project (optional)")
    data["selected_project"] = st.text_area("Project description", data["selected_project"], height=100)

    st.subheader("Programming skills (optional)")
    data["skills_languages"] = st.text_input("Languages (comma-separated)", data["skills_languages"])
    data["skills_libraries"] = st.text_input("Libraries (comma-separated)", data["skills_libraries"])
    data["skills_tools"] = st.text_input("Tools & Environment (comma-separated)", data["skills_tools"])

    st.subheader("Languages (optional)")
    data["spoken_languages"] = st.text_area("Spoken languages", data["spoken_languages"], height=70)

    st.subheader("Other Interests (optional)")
    data["other_interests"] = st.text_input("Other interests", data["other_interests"])

    st.divider()

    st.subheader("Export")
    render_btn = st.button("🚀 Generate PDF", type="primary")

    if render_btn:
        # Clean previous temp dir (optional)
        if st.session_state.last_workdir:
            cleanup_workdir(st.session_state.last_workdir)
            st.session_state.last_workdir = None

        try:
            result = render_and_compile(data)
            st.session_state.last_pdf = result.pdf_bytes
            st.session_state.last_tex = result.tex_str
            st.session_state.last_workdir = result.workdir
            st.success("PDF generated successfully.")
        except Exception as e:
            st.error("Failed to compile LaTeX.")
            st.text_area("Build log", str(e), height=350)
            if st.session_state.last_workdir:
                st.info(f"Temp build folder: {st.session_state.last_workdir}")

    if st.session_state.last_pdf:
        st.download_button(
            "⬇️ Download PDF",
            data=st.session_state.last_pdf,
            file_name="cv.pdf",
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
        st.pdf(st.session_state.last_pdf) if hasattr(st, "pdf") else st.info(
            "Preview not supported in this Streamlit version. Download the PDF to view it."
        )
    else:
        st.info("Click **Generate PDF** to build and preview your CV.")
