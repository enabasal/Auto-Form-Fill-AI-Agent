"""Carry out the fill plan in the browser and record what happened to each field."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from playwright.sync_api import Page

from .mapper import FillAction
from .scanner import FormField, Option

log = logging.getLogger(__name__)

FIELD_TIMEOUT_MS = 5000


@dataclass
class FieldResult:
    key: str
    label: str
    kind: str
    status: str  # "filled", "failed" or "skipped"
    value: str = ""
    detail: str = ""


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("*", "")).strip().lower()


def _has_word(text: str, part: str) -> bool:
    """True if `part` appears in `text` as a whole word ("c" is not in "javascript")."""
    return re.search(rf"(?<!\w){re.escape(part)}(?!\w)", text) is not None


def best_option(wanted: str, options: list[Option]) -> int | None:
    """Index of the option that best matches `wanted`, or None if nothing is close."""
    target = _norm(wanted)
    if not target:
        return None
    labels = [_norm(o.label) for o in options]
    values = [_norm(o.value) for o in options]
    for i in range(len(options)):
        if target in (labels[i], values[i]):
            return i
    partial = [
        i for i, label in enumerate(labels)
        if label and (label.startswith(target) or _has_word(label, target) or _has_word(target, label))
    ]
    if partial:
        return min(partial, key=lambda i: len(labels[i]))
    return None


def _fill_one(page: Page, field: FormField, value: str | list[str]) -> str:
    """Fill one field. Returns a short note; raises on failure."""
    locator = page.locator(field.selector)

    if field.kind == "select":
        index = best_option(str(value), field.options)
        if index is None:
            raise ValueError(f"no option matches {value!r}")
        locator.first.select_option(index=index, timeout=FIELD_TIMEOUT_MS)
        return field.options[index].label

    if field.kind in ("radio", "checkbox"):
        wanted = value if isinstance(value, list) else [value]
        picked, missing = [], []
        for item in wanted:
            index = best_option(item, field.options)
            if index is None:
                missing.append(item)
                continue
            page.locator(f'{field.selector}[data-aff-opt="{index}"]').check(timeout=FIELD_TIMEOUT_MS)
            picked.append(field.options[index].label)
            if field.kind == "radio":
                break
        if not picked:
            raise ValueError(f"no option matches {wanted!r}")
        return ", ".join(picked) + (f" (not found: {', '.join(missing)})" if missing else "")

    locator.first.fill(str(value), timeout=FIELD_TIMEOUT_MS)
    return str(value)


def apply_actions(page: Page, fields: list[FormField], actions: list[FillAction]) -> list[FieldResult]:
    """Apply every action; fields without an action are reported as skipped."""
    planned = {a.key: a.value for a in actions}
    results: list[FieldResult] = []
    for field in fields:
        label = field.label or field.placeholder or field.name or field.key
        if field.label and field.placeholder and field.placeholder != field.label:
            label = f"{field.label} ({field.placeholder})"
        if field.key not in planned:
            results.append(FieldResult(field.key, label, field.kind, "skipped"))
            continue
        try:
            shown = _fill_one(page, field, planned[field.key])
            results.append(FieldResult(field.key, label, field.kind, "filled", shown))
            log.info("Filled %-25s = %s", label[:25], shown)
        except Exception as exc:  # one bad field must not stop the rest
            results.append(FieldResult(field.key, label, field.kind, "failed",
                                       str(planned[field.key]), str(exc).splitlines()[0]))
            log.warning("Failed %-25s: %s", label[:25], exc)
    return results
