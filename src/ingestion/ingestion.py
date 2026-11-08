# src/ingestion/ingestion.py

import base64
import functools
import io
import json
import logging
import os
import time
import typing
from collections.abc import Callable
from typing import Any

import certifi
import easyocr
import httpx
import numpy as np
import pytesseract
from dotenv import load_dotenv
from PIL import Image
from pydantic import BaseModel, ValidationError

from forms.layout import Box, TableLayout
from forms.prompt import build_prompt
from forms.registry import FormSpec

logger = logging.getLogger(__name__)

load_dotenv()
# Python from python.org (macOS) ships without trusted certificates, which breaks
# EasyOCR's first-run model download. Use certifi's bundle unless one is set already.
os.environ.setdefault("SSL_CERT_FILE", certifi.where())

# Settings
LMSTUDIO_BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
DEFAULT_VLM_MODEL = os.getenv("DEFAULT_VLM_MODEL", "qwen/qwen3-vl-4b")
MAX_IMAGE_SIDE = 1600  # for Qwen3_VL
INK_THRESHOLD = 0.01  # for Tesseract and EasyOCR

## Optional: full path to the Tesseract binary, if it isn't on the PATH (Windows)
if tesseract_cmd := os.getenv("TESSERACT_CMD"):
    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd


class ExtractedField(BaseModel):
    text: str
    confidence: float | None = None


# LM Studio helpers
def _image_to_data_url(image: Image.Image) -> str:
    """Downscale large scans and encode them as a base64 PNG data URL."""
    image = image.copy()
    image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def _post_chat(payload: dict[str, Any]) -> str:
    """Send a chat request to LM Studio and return the reply text."""
    url = f"{LMSTUDIO_BASE_URL}/chat/completions"
    model = payload["model"]
    logger.info("Sending request to LM Studio (model=%s)...", model)
    start = time.monotonic()

    try:
        response = httpx.post(url, json=payload, timeout=300)
        response.raise_for_status()
    except httpx.ConnectError as e:
        logger.error("Could not reach LM Studio at %s", url)
        raise RuntimeError(
            "Could not reach LM Studio's local server. "
            "Make sure LM Studio is running with a vision model loaded "
            f"and serving at {LMSTUDIO_BASE_URL}."
        ) from e
    except httpx.TimeoutException as e:
        logger.error("LM Studio timed out at %s", url)
        raise RuntimeError("LM Studio took too long to answer. Try again.") from e
    except httpx.HTTPStatusError as e:
        logger.error(
            "LM Studio returned %s: %s", e.response.status_code, e.response.text
        )
        raise RuntimeError(
            f"LM Studio returned an error ({e.response.status_code}). "
            f"Check that the model '{model}' is loaded."
        ) from e

    logger.info("LM Studio responded in %.2fs", time.monotonic() - start)
    content: str = response.json()["choices"][0]["message"]["content"]
    return content


def _user_message(text: str, image: Image.Image) -> list[dict[str, Any]]:
    """A single chat message containing a text prompt and an image."""
    return [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": text},
                {"type": "image_url", "image_url": {"url": _image_to_data_url(image)}},
            ],
        }
    ]


# Form extraction for vision model
def extract_form_with_vlm(
    image: Image.Image, spec: FormSpec, model: str = DEFAULT_VLM_MODEL
) -> BaseModel:
    """Extract a whole form with a vision model, as a validated pydantic object."""
    payload = {
        "model": model,
        "messages": _user_message(build_prompt(spec), image),
        "temperature": 0,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": spec.key,
                "strict": True,
                "schema": spec.model.model_json_schema(),
            },
        },
    }

    content = _post_chat(payload)

    try:
        return spec.model.model_validate_json(content)
    except ValidationError as e:
        logger.error("Model output did not match the %s schema: %s", spec.key, content)
        raise RuntimeError(
            f"The model's answer did not match the '{spec.display_name}' form."
        ) from e


# Form extraction for OCR engines
@functools.cache
def _get_easyocr_reader() -> easyocr.Reader:
    """Load EasyOCR once (expensive); later calls return the same reader."""
    logger.info("Loading EasyOCR model (first use, this may take a moment)...")
    reader = easyocr.Reader(["de", "en"])
    logger.info("EasyOCR model loaded.")
    return reader


def _crop(image: Image.Image, box: Box) -> Image.Image:
    """Cut out one cell. The box is in fractions of the page size."""
    width, height = image.size
    x0, y0, x1, y1 = box
    return image.crop(
        (int(x0 * width), int(y0 * height), int(x1 * width), int(y1 * height))
    )


def _has_ink(cell: Image.Image) -> bool:
    """True if the cell contains enough dark pixels to be handwriting."""
    gray = np.array(cell.convert("L"))
    return bool((gray < 128).mean() > INK_THRESHOLD)


def _prepare_cell(cell: Image.Image) -> Image.Image:
    """Grayscale and enlarge a cell: OCR engines read larger text better."""
    cell = cell.convert("L")
    return cell.resize((cell.width * 2, cell.height * 2), Image.Resampling.LANCZOS)


def read_cell_tesseract(cell: Image.Image) -> str:
    """Read one cell with Tesseract, treating it as a single line of text."""
    text: str = pytesseract.image_to_string(cell, lang="deu", config="--psm 7")
    return text.strip()


def read_cell_easyocr(cell: Image.Image) -> str:
    """Read one cell with EasyOCR, joining all text it finds."""
    parts = _get_easyocr_reader().readtext(np.array(cell), detail=0, paragraph=True)
    return " ".join(str(part) for part in parts).strip()


CELL_READERS: dict[str, Callable[[Image.Image], str]] = {
    "tesseract": read_cell_tesseract,
    "easyocr": read_cell_easyocr,
}


def _is_bool_field(model: type[BaseModel], name: str) -> bool:
    """True for fields like `signed: bool | None`: ink checks, not text."""
    return bool in typing.get_args(model.model_fields[name].annotation)


def _read_field(
    image: Image.Image,
    box: Box,
    model: type[BaseModel],
    name: str,
    reader: Callable[[Image.Image], str],
) -> str | bool | None:
    """Read one field: ink check for yes/no fields, OCR for text fields."""
    cell = _crop(image, box)
    if _is_bool_field(model, name):
        return _has_ink(cell)
    if not _has_ink(cell):
        return None
    return reader(_prepare_cell(cell)) or None


def extract_form_with_ocr(image: Image.Image, spec: FormSpec, engine: str) -> BaseModel:
    """Extract a form by cropping each cell and reading it with an OCR engine."""
    if engine not in CELL_READERS:
        raise ValueError(
            f"Unknown OCR engine: {engine!r}. Choose from {list(CELL_READERS)}."
        )
    reader = CELL_READERS[engine]
    start = time.monotonic()

    if isinstance(spec.layout, TableLayout):
        if spec.row_model is None:
            raise ValueError(f"Table form {spec.key!r} has no row model.")
        layout = spec.layout
        row_model = spec.row_model
        rows = []
        for r in range(layout.n_rows):
            cells = {
                column: _read_field(
                    image, layout.cell(r, column), row_model, column, reader
                )
                for column in layout.columns
            }
            if any(isinstance(value, str) for value in cells.values()):
                rows.append(row_model(**cells))
        result = spec.model(rows=rows)
    else:
        values = {
            name: _read_field(image, box, spec.model, name, reader)
            for name, box in spec.layout.items()
        }
        result = spec.model(**values)

    logger.info("%s read %s in %.2fs", engine, spec.key, time.monotonic() - start)
    return result


# Form extraction, one entry point for all engines
def extract_form(image: Image.Image, spec: FormSpec, engine: str) -> BaseModel:
    """Extract a form with any engine. Every engine returns the same model type."""
    if engine == "qwen3_vl":
        return extract_form_with_vlm(image, spec)
    return extract_form_with_ocr(image, spec, engine)


# Free-text extraction
def extract_with_tesseract(image: Image.Image) -> list[ExtractedField]:
    """Extract text using Tesseract OCR. Fast, but weak on handwriting."""
    start = time.monotonic()
    text = pytesseract.image_to_string(image, lang="deu")
    elapsed = time.monotonic() - start
    lines = [line for line in text.splitlines() if line.strip()]
    logger.info("Tesseract extracted %d lines in %.2fs", len(lines), elapsed)
    return [ExtractedField(text=line, confidence=None) for line in lines]


def extract_with_easyocr(image: Image.Image) -> list[ExtractedField]:
    """Extract text using EasyOCR. Slower, but better on handwriting."""
    reader = _get_easyocr_reader()
    start = time.monotonic()
    results = reader.readtext(np.array(image))
    elapsed = time.monotonic() - start
    logger.info("EasyOCR extracted %d fields in %.2fs", len(results), elapsed)
    return [
        ExtractedField(text=str(text), confidence=float(confidence))
        for (_bbox, text, confidence) in results
    ]


def extract_with_qwen3_vl(image: Image.Image) -> list[ExtractedField]:
    """Extract free text using a vision model via LM Studio."""
    prompt = (
        "Extract the fields from this handwritten form. "
        "Return ONLY a JSON list of objects like "
        '{"text": "...", "confidence": null} '
        "for each field you find. "
        "No explanation, just the JSON."
    )
    payload = {
        "model": DEFAULT_VLM_MODEL,
        "messages": _user_message(prompt, image),
        "temperature": 0,
    }

    content = _post_chat(payload)

    try:
        raw = json.loads(content)
        return [ExtractedField(**item) for item in raw]
    except json.JSONDecodeError, ValidationError, TypeError:
        logger.warning("Model did not return valid JSON; returning raw text instead.")
        return [ExtractedField(text=content, confidence=None)]


_ENGINE_FUNCTIONS: dict[str, Callable[[Image.Image], list[ExtractedField]]] = {
    "tesseract": extract_with_tesseract,
    "easyocr": extract_with_easyocr,
    "qwen3_vl": extract_with_qwen3_vl,
}

ENGINES: tuple[str, ...] = tuple(_ENGINE_FUNCTIONS)


def extract_fields(image: Image.Image, engine: str = "easyocr") -> list[ExtractedField]:
    """Extract text from a scan using the chosen engine."""
    if engine not in _ENGINE_FUNCTIONS:
        logger.error("Unknown engine requested: %r", engine)
        raise ValueError(f"Unknown engine: {engine!r}. Choose from {list(ENGINES)}.")

    logger.info("Starting extraction with engine=%s", engine)
    return _ENGINE_FUNCTIONS[engine](image)
