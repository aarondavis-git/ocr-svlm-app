# src/forms/attendance_times.py

"""Anwesenheitsliste (member attendance with arrival and departure times)."""

from pydantic import BaseModel, Field

from forms.layout import TableLayout


class TimeSheetRow(BaseModel):
    """One member's attendance on one day."""

    weekday_date: str | None = Field(
        None, description="Column 'Wochentag, Datum'. Weekday and date as written."
    )
    number: str | None = Field(
        None, description="Column 'Nr. (1, 2, 3, usw.)'. Running count for the day."
    )
    arrived: str | None = Field(
        None, description="Column 'gekommen um (Uhrzeit)'. Arrival time."
    )
    left: str | None = Field(
        None, description="Column 'gegangen um (Uhrzeit)'. Departure time."
    )
    member_name: str | None = Field(
        None, description="Column 'Mitglied Name'. Name of the member."
    )
    member_status: str | None = Field(
        None,
        description="Column 'MO?'. Either 'M' (member) or 'MO' "
        "(member in orientation).",
    )


class TimeSheetForm(BaseModel):
    """Anwesenheitsliste (Mitglieder): a table with one row per attendance."""

    rows: list[TimeSheetRow]


TIMESHEET_LAYOUT = TableLayout(
    columns={
        "weekday_date": (0.060, 0.216),
        "number": (0.216, 0.329),
        "arrived": (0.329, 0.471),
        "left": (0.471, 0.612),
        "member_name": (0.612, 0.806),
        "member_status": (0.806, 0.949),
    },
    top=0.136,
    bottom=0.892,
    n_rows=32,
)
