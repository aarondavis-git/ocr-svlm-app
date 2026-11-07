# tests/test_export.py

import io

import pandas as pd

from export.excel import prospect_rows, to_excel
from ingestion.results import PageResult


def _result(page: int, plz_city: str) -> PageResult:
    return PageResult(
        source_file="scan.pdf",
        page=page,
        form_key="prospect",
        engine="easyocr",
        data={"last_name": "Muster", "postal_code_city": plz_city},
    )


def test_one_row_per_form():
    rows = prospect_rows([_result(1, "81539 München"), _result(2, "80331 München")])
    assert len(rows) == 2
    assert rows[1]["page"] == 2


def test_excel_keeps_leading_zeros():
    rows = prospect_rows([_result(1, "01067 Dresden")])
    data = to_excel(pd.DataFrame(rows), "Interessenten")
    df = pd.read_excel(io.BytesIO(data), dtype=str)
    assert df.loc[0, "postal_code"] == "01067"
