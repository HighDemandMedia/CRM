"""Presentation for form mail; submitted values stay out of visitor confirmations."""

from django.template.loader import render_to_string

from common.links import frontend_url
from webforms.constants import (
    CONTACT_FIELD_CHOICES,
    LEAD_FIELD_CHOICE_SOURCES,
    LEAD_FIELD_CHOICES,
)
from webforms.models import WebFormSubmission
from webforms.notifications import record_link


def _display_value(value, choices, language):
    if isinstance(value, bool):
        return (
            ("Sí" if value else "No")
            if language == "es"
            else ("Yes" if value else "No")
        )
    if isinstance(value, list):
        return ", ".join(_display_value(item, choices, language) for item in value)
    if isinstance(value, dict):
        return "\n".join(
            f"{key}: {_display_value(item, {}, language)}"
            for key, item in value.items()
        )
    return str(choices.get(str(value), value))


def submission_rows(submission, language="en"):
    """Configured labels/order, choice labels and readable values, never raw dict repr."""
    form = submission.form
    payload = submission.payload
    custom = payload.get("custom_fields") or {}
    defaults = dict(
        CONTACT_FIELD_CHOICES if form.target_model == "Contact" else LEAD_FIELD_CHOICES
    )
    rows, seen = [], set()

    def append(key, value, label, choices, is_custom=False):
        seen.add((is_custom, key))
        if value is None or value == "" or value == []:
            return
        rows.append({"label": label, "value": _display_value(value, choices, language)})

    for field in form.fields.select_related("custom_field").all():
        if field.custom_field_id:
            definition = field.custom_field
            key = definition.key
            if key in custom:
                choices = {
                    option["value"]: option["label"]
                    for option in definition.options or []
                }
                append(key, custom[key], field.label, choices, is_custom=True)
        elif field.lead_field in payload:
            key = field.lead_field
            append(
                key,
                payload[key],
                field.label,
                dict(LEAD_FIELD_CHOICE_SOURCES.get(key, [])),
            )

    # A form can be edited between accepting a submission and sending its mail.
    # Preserve those accepted values, even if their question was removed.
    for key, value in payload.items():
        if key != "custom_fields" and (False, key) not in seen:
            append(
                key, value, defaults.get(key, key.replace("_", " ").capitalize()), {}
            )
    for key, value in custom.items():
        if (True, key) not in seen:
            append(key, value, key.replace("_", " ").capitalize(), {}, is_custom=True)
    return rows


def internal_email(submission, profile):
    language = "es" if (profile.language or profile.user.ui_language) == "es" else "en"
    spanish = language == "es"
    form = submission.form
    form_name = " ".join(form.name.split())
    heading = "Nueva solicitud recibida" if spanish else "New website submission"
    introduction = (
        f"Nueva solicitud a través de {form_name}."
        if spanish
        else f"A new submission arrived through {form_name}."
    )
    duplicate_note = ""
    if submission.status == WebFormSubmission.ACCEPTED_DUPLICATE:
        if form.target_model == "Contact":
            duplicate_note = (
                "Vinculada a un contacto existente. Sus datos y responsable no han cambiado."
                if spanish
                else "Linked to an existing contact. Its details and owner were left unchanged."
            )
        else:
            duplicate_note = (
                "Vinculada a un registro existente. Solo se completaron campos vacíos."
                if spanish
                else "Linked to an existing record. New details were merged into blank fields only."
            )
    record = submission.contact or submission.lead
    record_url = frontend_url(record_link(submission)) if record else ""
    rows = submission_rows(submission, language)
    button_label = (
        ("Abrir contacto" if form.target_model == "Contact" else "Abrir lead")
        if spanish
        else f"Open {form.target_model.lower()}"
    )
    context = {
        "email_language": language,
        "heading": heading,
        "introduction": introduction,
        "duplicate_note": duplicate_note,
        "submission_rows": rows,
        "record_url": record_url,
        "button_label": button_label,
    }
    text = [heading, introduction, duplicate_note]
    text.extend(f"{row['label']}: {row['value']}" for row in rows)
    if record_url:
        text.append(f"{button_label}: {record_url}")
    return {
        "subject": f"{'Nueva solicitud' if spanish else 'New submission'}: {form_name}",
        "html_content": render_to_string("webforms/submission_email.html", context),
        "text_content": "\n\n".join(part for part in text if part),
    }


def confirmation_email(submission):
    """Only organization-controlled identity; no submitted message or CRM links."""
    language = submission.submission_language
    spanish = language == "es"
    organization = " ".join(submission.form.org.name.split())
    heading = "Recibimos tu solicitud" if spanish else "We've received your request"
    introduction = (
        f"Gracias por contactar a {organization}."
        if spanish
        else f"Thank you for contacting {organization}."
    )
    next_step = (
        "Nuestro equipo revisará tu solicitud y se pondrá en contacto contigo para hablar de los siguientes pasos."
        if spanish
        else "Our team will review your request and contact you to discuss the next steps."
    )
    return {
        "subject": f"{heading} · {organization}",
        "html_content": render_to_string(
            "webforms/confirmation_email.html",
            {
                "email_language": language,
                "heading": heading,
                "introduction": introduction,
                "next_step": next_step,
            },
        ),
        "text_content": f"{heading}\n\n{introduction}\n\n{next_step}",
    }
