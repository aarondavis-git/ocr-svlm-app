# src/forms/transform.py

import re
from typing import Any

from forms.prospect import ProspectForm

PLZ_CITY = re.compile(r"^\s*(\d{5})\s*,?\s*(.+?)\s*$")


def split_postal_code_city(value: str | None) -> tuple[str | None, str | None]:
    """'81539 München' → ('81539', 'München'). Unsplittable text goes to city."""
    if not value:
        return None, None
    match = PLZ_CITY.match(value)
    if match is None:
        return None, value
    return match.group(1), match.group(2)


def prospect_to_row(form: ProspectForm) -> dict[str, Any]:
    """One export row: all fields, with PLZ and Ort as separate columns."""
    row = form.model_dump()
    postal_code, city = split_postal_code_city(row.pop("postal_code_city"))
    row["postal_code"] = postal_code
    row["city"] = city
    return row
