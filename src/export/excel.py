# src/export/excel.py

import io
from typing import Any

import pandas as pd

from forms.prospect import ProspectForm
from forms.registry import FormSpec
from forms.transform import prospect_to_row
from ingestion.results import PageResult


def _source(result: PageResult) -> dict[str, Any]:
    """Columns that trace a row back to its scan."""
    return {
        "source_file": result.source_file,
        "page": result.page,
        "engine": result.engine,
    }


def prospect_rows(results: list[PageResult]) -> list[dict[str, Any]]:
    """One export row per form 1: form fields first, then where it came from."""
    return [
        {**prospect_to_row(ProspectForm(**result.data)), **_source(result)}
        for result in results
    ]


def table_rows(results: list[PageResult]) -> list[dict[str, Any]]:
    """One export row per filled table line, across all pages."""
    return [
        {**row, **_source(result)} for result in results for row in result.data["rows"]
    ]


def export_rows(results: list[PageResult], spec: FormSpec) -> list[dict[str, Any]]:
    """Build export rows for any form."""
    if spec.is_table:
        return table_rows(results)
    if spec.key == "prospect":
        return prospect_rows(results)
    raise ValueError(f"No export defined for form {spec.key!r}.")


def to_excel(df: pd.DataFrame, sheet_name: str) -> bytes:
    """Write a table to an .xlsx file in memory, e.g. for st.download_button."""
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, sheet_name=sheet_name[:31])
    return buffer.getvalue()
