# src/forms/call_log.py

"""Telefon-Doku der MG-Anrufe (phone call log)."""

from pydantic import BaseModel, Field

from forms.layout import TableLayout


class CallLogRow(BaseModel):
    """One phone call."""

    date: str | None = Field(None, description="Column 'Datum'. Date of the call.")
    member: str | None = Field(
        None, description="Column 'Mitglied'. Name of the member."
    )
    caller: str | None = Field(
        None,
        description="Column 'Wer telefoniert? (MG, MA)'. Either 'MG' or 'MA'.",
    )
    duration_min: str | None = Field(
        None, description="Column 'Dauer in min.'. A number of minutes."
    )
    concern_code: str | None = Field(
        None, description="Column 'Anliegen (Nr.)'. A single number from 1 to 5."
    )
    note: str | None = Field(None, description="Column 'Notiz'. Free text.")


class CallLogForm(BaseModel):
    """Telefon-Doku der MG-Anrufe: a table with one row per phone call."""

    rows: list[CallLogRow]


CONCERN_CODES = {
    "1": "Anmeldung zu einer Schicht",
    "2": "Clubhausbelange",
    "3": "Beratungsgespräch",
    "4": "Krisenintervention",
    "5": "Entlastungsgespräch",
}

CALL_LOG_LAYOUT = TableLayout(
    columns={
        "date": (0.115, 0.199),
        "member": (0.199, 0.328),
        "caller": (0.328, 0.439),
        "duration_min": (0.439, 0.528),
        "concern_code": (0.528, 0.622),
        "note": (0.622, 0.898),
    },
    top=0.195,
    bottom=0.775,
    n_rows=12,
)
