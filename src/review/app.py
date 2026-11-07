# src/review/app.py

import hashlib
import logging

import streamlit as st
from PIL import Image

from forms.registry import FORMS
from ingestion.ingestion import ENGINES, ExtractedField, extract_fields
from ingestion.loading import load_pages

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

ENGINE_LABELS = {
    "tesseract": "Tesseract",
    "easyocr": "EasyOCR",
    "qwen3_vl": "Qwen3-VL",
}


@st.cache_data
def load_pages_cached(data: bytes, filename: str) -> list[Image.Image]:
    """Cache page loading per file, so PDFs aren't converted on every rerun."""
    return load_pages(data, filename)


st.set_page_config(page_title="Clubhouse Form Review", layout="wide")
st.title("Clubhouse Form Review")

# Results survive reruns: {(file_id, form_key, engine): [ExtractedField, ...]}
if "results" not in st.session_state:
    st.session_state.results = {}

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
    help=(
        "Tesseract: fast, classical OCR, weak on handwriting. "
        "EasyOCR: local deep-learning OCR, decent on handwriting. "
        "Qwen3-VL: local vision-language model via LM Studio. Requires "
        "LM Studio running with a vision model loaded."
    ),
)

if form_key is None or engine is None:
    st.info("Choose a form and an engine.")
    st.stop()

# 2. Upload
uploaded_file = st.file_uploader(
    "Upload a scanned form (PDF or image)", type=["pdf", "png", "jpg", "jpeg"]
)

if uploaded_file is None:
    st.info("Upload a scan to get started.")
    st.stop()

data = uploaded_file.getvalue()
file_id = hashlib.sha256(data).hexdigest()[:12]
pages = load_pages_cached(data, uploaded_file.name)

if len(pages) > 1:
    st.warning(f"This PDF has {len(pages)} pages. Only the first page is processed.")
image = pages[0]

run_key = (file_id, form_key, engine)

# 3. Run
if st.button("Run", type="primary"):
    label = ENGINE_LABELS.get(engine, engine)
    try:
        with st.spinner(f"Running {label} on {FORMS[form_key].display_name}..."):
            st.session_state.results[run_key] = extract_fields(image, engine=engine)
    except RuntimeError as e:
        st.error(str(e))

# 4. Show scan and results
col1, col2 = st.columns(2)

with col1:
    st.subheader("Scan")
    st.image(image, width="stretch")

with col2:
    st.subheader("Extracted text (edit as needed)")
    results: list[ExtractedField] | None = st.session_state.results.get(run_key)

    if results is None:
        st.info("Press **Run** to extract this scan.")
    elif not results:
        st.warning("No text found.")
    else:
        for i, field in enumerate(results):
            label = f"Field {i + 1}"
            if field.confidence is not None:
                label += f" (confidence: {field.confidence:.2f})"
            st.text_input(label, value=field.text, key=f"{run_key}_{i}")
