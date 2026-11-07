# src/ingestion/loading.py

import io

from pdf2image import convert_from_bytes
from PIL import Image


def load_pages(data: bytes, filename: str, dpi: int = 300) -> list[Image.Image]:
    """Return one image per page. Images count as a single page."""
    if filename.lower().endswith(".pdf"):
        return convert_from_bytes(data, dpi=dpi)
    return [Image.open(io.BytesIO(data)).convert("RGB")]
