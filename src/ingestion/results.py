# src/ingestion/results.py

from typing import Any

from pydantic import BaseModel


class PageResult(BaseModel):
    source_file: str
    page: int  # 1-based, as in a PDF viewer
    form_key: str
    engine: str
    data: dict[str, Any]  # the form's fields, from form.model_dump()
