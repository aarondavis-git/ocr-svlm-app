# src/forms/attendance_signin.py

"""Anwesenheitsliste für Besucher von Tagesstätten (sign-in sheet)."""

from pydantic import BaseModel, Field

from forms.layout import TableLayout


class SignInRow(BaseModel):
    """One visitor signing in."""

    number: str | None = Field(None, description="Column 'Nr.'. Row number.")
    weekday: str | None = Field(None, description="Column 'Tag'. Day of the week.")
    date: str | None = Field(None, description="Column 'Datum'.")
    full_name: str | None = Field(
        None, description="Column 'Vor- und Zuname'. First name and surname."
    )
    signed: bool | None = Field(
        None,
        description="Column 'Unterschrift'. true if a signature is present, "
        "false if the cell is empty. Do not transcribe the signature.",
    )


class SignInSheetForm(BaseModel):
    """Anwesenheitsliste (Tagesstätte): a table with one row per visitor."""

    rows: list[SignInRow]


SIGNIN_LAYOUT = TableLayout(
    columns={
        "number": (0.032, 0.140),
        "weekday": (0.140, 0.285),
        "date": (0.285, 0.416),
        "full_name": (0.416, 0.726),
        "signed": (0.726, 0.984),
    },
    top=0.122,
    bottom=0.917,
    n_rows=34,
)
