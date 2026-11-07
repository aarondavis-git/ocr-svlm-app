# src/export/excel.py

import io
from typing import Any

import pandas as pd

from forms.prospect import ProspectForm
from forms.transform import prospect_to_row
from ingestion.results import PageResult


def prospect_rows(results: list[PageResult]) -> list[dict[str, Any]]:
    """One export row per form 1: form fields first, then where it came from."""
    rows = []
    for result in results:
        row = prospect_to_row(ProspectForm(**result.data))
        row["source_file"] = result.source_file
        row["page"] = result.page
        row["engine"] = result.engine
        rows.append(row)
    return rows


def to_excel(rows: list[dict[str, Any]], sheet_name: str) -> bytes:
    """Write rows to an .xlsx file in memory, e.g. for st.download_button."""
    buffer = io.BytesIO()
    pd.DataFrame(rows).to_excel(buffer, index=False, sheet_name=sheet_name[:31])
    return buffer.getvalue()
