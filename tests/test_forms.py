# tests/test_forms.py

from forms.layout import TableLayout
from forms.registry import FORMS


def test_every_layout_matches_its_fields():
    for spec in FORMS.values():
        if isinstance(spec.layout, TableLayout):
            assert spec.row_model is not None, spec.key
            assert set(spec.layout.columns) == set(
                spec.row_model.model_fields
            ), spec.key
        else:
            assert set(spec.layout) == set(spec.model.model_fields), spec.key
