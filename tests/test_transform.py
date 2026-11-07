# tests/test_transform.py

import pytest

from forms.prospect import ProspectForm
from forms.transform import prospect_to_row, split_postal_code_city


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("81539 München", ("81539", "München")),
        ("81539München", ("81539", "München")),
        ("81539, München", ("81539", "München")),
        ("  81539   München  ", ("81539", "München")),
        ("8153 München", (None, "8153 München")),  # OCR misread: keep for review
        ("München", (None, "München")),
        ("", (None, None)),
        (None, (None, None)),
    ],
)
def test_split_postal_code_city(value, expected):
    assert split_postal_code_city(value) == expected


def test_prospect_to_row_splits_plz_and_city():
    form = ProspectForm(last_name="Muster", postal_code_city="81539 München")
    row = prospect_to_row(form)
    assert row["postal_code"] == "81539"
    assert row["city"] == "München"
    assert "postal_code_city" not in row
