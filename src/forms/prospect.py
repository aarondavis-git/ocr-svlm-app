# src/forms/prospect.py

"""Interessentenformular (prospective member registration form)."""

from pydantic import BaseModel, ConfigDict, Field

from forms.layout import Box


class ProspectForm(BaseModel):
    """Interessentenformular: registration of one prospective member."""

    model_config = ConfigDict(extra="forbid")

    last_name: str | None = Field(None, description="Label 'Name:'. Surname only.")
    first_name: str | None = Field(None, description="Label 'Vorname:'.")
    street_address: str | None = Field(
        None, description="Label 'Straße und Hausnummer:'. Street and house number."
    )
    postal_code_city: str | None = Field(
        None, description="Label 'PLZ und Ort:'. Postcode and city on one line."
    )
    date_of_birth: str | None = Field(None, description="Label 'Geburtsdatum:'.")
    phone: str | None = Field(
        None, description="Label 'Telefon (bitte unbedingt angeben!):'."
    )
    email: str | None = Field(None, description="Label 'E-Mail Adresse:'.")
    tour_date: str | None = Field(
        None, description="Label 'Datum der Führung:'. Date of the guided tour."
    )
    start_date: str | None = Field(
        None,
        description="Label 'ab wann möchte ich starten:'. Desired start; "
        "may be a date or text such as 'sofort'.",
    )
    referred_by: str | None = Field(
        None,
        description="Label 'empfohlen bzw. vermittelt von:'. "
        "Person or organisation that referred them.",
    )


PROSPECT_LAYOUT: dict[str, Box] = {
    "last_name": (0.425, 0.210, 0.905, 0.252),
    "first_name": (0.425, 0.260, 0.905, 0.298),
    "street_address": (0.425, 0.306, 0.905, 0.347),
    "postal_code_city": (0.425, 0.355, 0.905, 0.394),
    "date_of_birth": (0.425, 0.402, 0.905, 0.442),
    "phone": (0.425, 0.450, 0.905, 0.490),
    "email": (0.425, 0.498, 0.905, 0.531),
    "tour_date": (0.425, 0.539, 0.905, 0.581),
    "start_date": (0.425, 0.589, 0.905, 0.622),
    "referred_by": (0.425, 0.630, 0.905, 0.670),
}
