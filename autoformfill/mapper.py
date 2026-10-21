"""Ask the LLM which profile value belongs in which form field."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from .llm import JSONLLM
from .profile import Profile
from .scanner import FormField

log = logging.getLogger(__name__)

MAPPER_SYSTEM = "You fill in web forms for a job candidate. Reply with one JSON object only."

MAPPER_PROMPT = """CANDIDATE PROFILE (JSON):
{profile}

FORM FIELDS (JSON):
{fields}

Decide what to enter in each form field and reply as:
{{"fields": {{"<key>": <value>, ...}}}}

Rules:
- Only include a field when the profile clearly contains the answer. Never invent data.
- Text-like fields: a string. If the form splits the name, use first_name and last_name.
- Address fields: use address; if it is empty, join city, state and country.
- A select or checkbox about skills: pick options that match the candidate's skills.
- select and radio: a string copied exactly from that field's options. If a select lists no
  options, give the plain value (for example the country name).
- checkbox: a list of option labels to tick.
- Leave out passwords, CAPTCHAs, terms/consent boxes and anything you are unsure about.
"""


@dataclass
class FillAction:
    key: str
    value: str | list[str]


def _normalise(field: FormField, value: object) -> str | list[str] | None:
    if value is None or value == "" or value == []:
        return None
    if field.kind == "checkbox":
        if isinstance(value, bool):
            # A lone checkbox answered with true/false.
            return [field.options[0].label] if value and len(field.options) == 1 else None
        items = value if isinstance(value, list) else [value]
        items = [str(v).strip() for v in items if str(v).strip()]
        return items or None
    if isinstance(value, list):
        value = value[0] if value else ""
    text = str(value).strip()
    return text or None


def plan_fill(
    fields: list[FormField], profile: Profile, llm: JSONLLM
) -> tuple[list[FillAction], list[str]]:
    """Return the actions to perform and any keys the model invented (which are dropped)."""
    prompt = MAPPER_PROMPT.format(
        profile=profile.model_dump_json(indent=2),
        fields=json.dumps([f.describe() for f in fields], indent=2),
    )
    data = llm.complete_json(MAPPER_SYSTEM, prompt)
    mapping = data.get("fields", data) if isinstance(data.get("fields", data), dict) else {}

    by_key = {f.key: f for f in fields}
    actions: list[FillAction] = []
    unknown: list[str] = []
    for key, value in mapping.items():
        field = by_key.get(key)
        if field is None:
            unknown.append(key)
            continue
        normalised = _normalise(field, value)
        if normalised is not None:
            actions.append(FillAction(key, normalised))
    if unknown:
        log.warning("Ignoring %d field keys the model made up: %s", len(unknown), unknown)
    return actions, unknown
