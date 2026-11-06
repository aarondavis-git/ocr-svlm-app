# src/forms/registry.py

from dataclasses import dataclass

from pydantic import BaseModel

from forms.attendance_signin import SIGNIN_LAYOUT, SignInRow, SignInSheetForm
from forms.attendance_times import TIMESHEET_LAYOUT, TimeSheetForm, TimeSheetRow
from forms.call_log import CALL_LOG_LAYOUT, CallLogForm, CallLogRow
from forms.layout import Box, TableLayout
from forms.prospect import PROSPECT_LAYOUT, ProspectForm


@dataclass(frozen=True)
class FormSpec:
    key: str
    display_name: str
    model: type[BaseModel]
    layout: dict[str, Box] | TableLayout
    row_model: type[BaseModel] | None = None

    @property
    def is_table(self) -> bool:
        return isinstance(self.layout, TableLayout)


FORMS: dict[str, FormSpec] = {
    spec.key: spec
    for spec in [
        FormSpec("prospect", "Interessentenformular", ProspectForm, PROSPECT_LAYOUT),
        FormSpec("call_log", "Telefon-Doku", CallLogForm, CALL_LOG_LAYOUT, CallLogRow),
        FormSpec(
            "attendance_signin",
            "Anwesenheitsliste",
            SignInSheetForm,
            SIGNIN_LAYOUT,
            SignInRow,
        ),
        FormSpec(
            "attendance_times",
            "Anwesenheitszeiten",
            TimeSheetForm,
            TIMESHEET_LAYOUT,
            TimeSheetRow,
        ),
    ]
}


def get_form(key: str) -> FormSpec:
    if key not in FORMS:
        raise ValueError(f"Unknown form {key!r}. Choose from {list(FORMS)}.")
    return FORMS[key]
