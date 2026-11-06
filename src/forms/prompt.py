# src/forms/prompt.py

"""Build the extraction prompt for the vision model from a form's definition."""

from pydantic import BaseModel

from forms.registry import FormSpec

RULES = (
    "Copy all text exactly as written; do not correct or reformat it. "
    "Use null for empty or unreadable fields."
)


def describe_fields(model: type[BaseModel]) -> str:
    """One line per field: '- name: description'."""
    lines = [
        f"- {name}: {field.description or ''}"
        for name, field in model.model_fields.items()
    ]
    return "\n".join(lines)


def build_prompt(spec: FormSpec) -> str:
    """Prompt for one page of the given form."""
    intro = f"This is a scanned, handwritten form. {spec.model.__doc__ or ''}".strip()

    if spec.is_table and spec.row_model is not None:
        parts = [
            intro,
            "Each table row has these columns:\n" + describe_fields(spec.row_model),
            "Return one entry in 'rows' per filled-in row, top to bottom. "
            "Skip empty rows. If no rows are filled in, return an empty list.",
            RULES,
        ]
    else:
        parts = [
            intro,
            "Fill these fields:\n" + describe_fields(spec.model),
            RULES,
        ]

    return "\n\n".join(parts)
