# src/review/app.py

import hashlib
import logging
from datetime import date

import pandas as pd
import streamlit as st
from PIL import Image

from export.excel import export_rows, to_excel
from forms.registry import FORMS
from ingestion.ingestion import ENGINES, extract_form
from ingestion.loading import load_pages
from ingestion.results import PageResult

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

ENGINE_LABELS = {
    "tesseract": "Tesseract",
    "easyocr": "EasyOCR",
    "qwen3_vl": "Qwen3-VL",
}
SOURCE_COLUMNS = ["source_file", "page", "engine"]


@st.cache_data
def load_pages_cached(data: bytes, filename: str) -> list[Image.Image]:
    """Cache page loading per file, so PDFs aren't converted on every rerun."""
    return load_pages(data, filename)


st.set_page_config(page_title="Clubhouse Form Review", layout="wide")
st.title("Clubhouse Form Review")

# Extraction results survive reruns: {(files_id, form_key, engine): batch}
if "batches" not in st.session_state:
    st.session_state.batches = {}

# 1. Choose form and engine
form_key = st.segmented_control(
    "Form",
    options=list(FORMS),
    format_func=lambda key: FORMS[key].display_name,
    default="prospect",
)
engine = st.segmented_control(
    "Engine",
    options=ENGINES,
    format_func=lambda key: ENGINE_LABELS.get(key, key),
    default=ENGINES[0],
)
if form_key is None or engine is None:
    st.info("Choose a form and an engine.")
    st.stop()

spec = FORMS[form_key]

# 2. Upload one or more files

uploads = st.file_uploader(
    "Upload scanned forms (PDF or images)",
    type=["pdf", "png", "jpg", "jpeg"],
    accept_multiple_files=True,
)
if not uploads:
    st.info("Upload one or more scans to get started.")
    st.stop()

files = {upload.name: upload.getvalue() for upload in uploads}
files_id = hashlib.sha256(
    b"".join(hashlib.sha256(data).digest() for data in files.values())
).hexdigest()[:12]
batch_key = (files_id, form_key, engine)

total_pages = sum(len(load_pages_cached(data, name)) for name, data in files.items())
st.caption(f"{len(files)} file(s), {total_pages} page(s)")

# 3. Run extraction on every page

if st.button(f"Run on {total_pages} page(s)", type="primary"):
    results: list[PageResult] = []
    errors: list[str] = []
    progress = st.progress(0.0, text="Starting...")
    done = 0

    for name, data in files.items():
        for page_number, image in enumerate(load_pages_cached(data, name), start=1):
            progress.progress(done / total_pages, text=f"{name}, page {page_number}")
            try:
                form = extract_form(image, spec, engine)
                results.append(
                    PageResult(
                        source_file=name,
                        page=page_number,
                        form_key=form_key,
                        engine=engine,
                        data=form.model_dump(),
                    )
                )
            except RuntimeError as e:
                errors.append(f"{name}, page {page_number}: {e}")
            done += 1

    progress.progress(1.0, text="Done")
    st.session_state.batches[batch_key] = {"results": results, "errors": errors}

batch = st.session_state.batches.get(batch_key)
if batch is None:
    st.info("Press **Run** to extract all pages.")
    st.stop()

for error in batch["errors"]:
    st.error(error)
if not batch["results"]:
    st.warning("Nothing was extracted.")
    st.stop()

# 4. Review: scan on the left, editable table on the right

original = pd.DataFrame(export_rows(batch["results"], spec))
if original.empty:
    st.warning("No filled-in rows were found.")
    st.stop()

col_scan, col_table = st.columns([2, 3])

with col_scan:
    st.subheader("Scan")
    pages = [(r.source_file, r.page) for r in batch["results"]]
    name, page_number = st.selectbox(
        "Show page", pages, format_func=lambda p: f"{p[0]}, page {p[1]}"
    )
    st.image(load_pages_cached(files[name], name)[page_number - 1], width="stretch")

with col_table:
    st.subheader("Review (edit cells to correct them)")
    edited = st.data_editor(
        original,
        key=f"editor_{batch_key}",
        num_rows="fixed",
        disabled=SOURCE_COLUMNS,
        hide_index=True,
        width="stretch",
    )

    corrections = int(
        (original.fillna("").astype(str) != edited.fillna("").astype(str)).sum().sum()
    )
    st.caption(f"{len(edited)} row(s), {corrections} cell(s) corrected")

    # 5. Export
    st.download_button(
        "Download Excel",
        data=to_excel(edited, spec.display_name),
        file_name=f"{spec.key}_{date.today():%Y-%m-%d}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )
