# src/ingestion/ingestion.py

import base64
import functools
import io
import json
import logging
import os
import time
from collections.abc import Callable

import easyocr
import httpx
import numpy as np
import pytesseract
from dotenv import load_dotenv
from PIL import Image
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

load_dotenv()

LMSTUDIO_BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
DEFAULT_VLM_MODEL = os.getenv("DEFAULT_VLM_MODEL", "qwen/qwen3-vl-8b")

if tesseract_cmd := os.getenv("TESSERACT_CMD"):
    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd


class ExtractedField(BaseModel):
    text: str
    confidence: float | None = None


@functools.cache
def _get_easyocr_reader() -> easyocr.Reader:
    """Load EasyOCR once (expensive); later calls return the same reader."""
    logger.info("Loading EasyOCR model (first use, this may take a moment)...")
    reader = easyocr.Reader(["de", "en"])
    logger.info("EasyOCR model loaded.")
    return reader


def extract_with_easyocr(image: Image.Image) -> list[ExtractedField]:
    """Extract text using EasyOCR. Slower, but better on handwriting."""
    reader = _get_easyocr_reader()
    img_array = np.array(image)

    start = time.monotonic()
    results = reader.readtext(img_array)
    elapsed = time.monotonic() - start
    logger.info("EasyOCR extracted %d fields in %.2fs", len(results), elapsed)

    return [
        ExtractedField(text=str(text), confidence=float(confidence))
        for (_bbox, text, confidence) in results
    ]


def extract_with_tesseract(image: Image.Image) -> list[ExtractedField]:
    """Extract text using Tesseract OCR. Fast, but weak on handwriting."""
    start = time.monotonic()
    text = pytesseract.image_to_string(image, lang="deu")
    elapsed = time.monotonic() - start
    lines = [line for line in text.splitlines() if line.strip()]
    logger.info("Tesseract extracted %d lines in %.2fs", len(lines), elapsed)
    return [ExtractedField(text=line, confidence=None) for line in lines]


def extract_with_qwen3_vl(image: Image.Image) -> list[ExtractedField]:
    """Extract text using a local vision model via LM Studio's server."""
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    image_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    payload = {
        "model": DEFAULT_VLM_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Extract the fields from this handwritten form. "
                            "Return ONLY a JSON list of objects like "
                            '{"text": "...", "confidence": null} '
                            "for each field you find. "
                            "No explanation, just the JSON."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                    },
                ],
            }
        ],
        "temperature": 0,
    }

    url = f"{LMSTUDIO_BASE_URL}/chat/completions"
    logger.info("Sending request to LM Studio (model=%s)...", DEFAULT_VLM_MODEL)
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
            f"Check that the model '{DEFAULT_VLM_MODEL}' is loaded."
        ) from e

    elapsed = time.monotonic() - start
    logger.info("LM Studio responded in %.2fs", elapsed)

    content = response.json()["choices"][0]["message"]["content"]

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
