"""Find the fillable fields on a page and describe them for the LLM.

Every field the scanner finds is tagged in the DOM with a `data-aff-key` attribute,
so later steps target it with a selector that is guaranteed to exist and be unique.
The model never has to invent CSS selectors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from playwright.sync_api import Page

_SCAN_JS = r"""
() => {
  const SKIP = new Set(['hidden', 'submit', 'button', 'reset', 'image', 'file', 'password']);
  const clean = s => (s || '').replace(/\s+/g, ' ').trim().slice(0, 120);
  const visible = el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length)
      && getComputedStyle(el).visibility !== 'hidden';
  const controlsIn = node => node.querySelectorAll('input, select, textarea').length;

  // Text of a label that is not attached to any specific control (e.g. "Gender*").
  const groupLabel = el => {
    const legend = el.closest('fieldset')?.querySelector('legend');
    if (legend) return clean(legend.innerText);
    let node = el.parentElement;
    for (let depth = 0; depth < 4 && node; depth++, node = node.parentElement) {
      if (controlsIn(node) > 6) break;
      const free = [...node.querySelectorAll('label')].find(l => !l.control);
      if (free) return clean(free.innerText);
    }
    return '';
  };

  const ownLabel = el => {
    if (el.labels && el.labels.length) return clean([...el.labels].map(l => l.innerText).join(' '));
    if (el.getAttribute('aria-label')) return clean(el.getAttribute('aria-label'));
    const ids = el.getAttribute('aria-labelledby');
    if (ids) {
      const text = ids.split(/\s+/).map(id => document.getElementById(id)?.innerText || '').join(' ');
      if (clean(text)) return clean(text);
    }
    return '';
  };

  const fields = [];
  const groups = new Map();
  let n = 0;
  let containers = 0;

  // Checkboxes and radios without a name are grouped by the nearest element
  // that holds more than one of them (e.g. Cricket / Movies / Hockey).
  const groupKey = (el, type) => {
    if (el.name) return type + ':' + el.name;
    let node = el.parentElement;
    for (let depth = 0; depth < 4 && node; depth++, node = node.parentElement) {
      if (node.querySelectorAll(`input[type=${type}]`).length > 1) {
        if (!node.dataset.affGroup) node.dataset.affGroup = String(containers++);
        return type + ':box' + node.dataset.affGroup;
      }
    }
    return type + ':solo' + n;
  };

  // A dropdown with no real choices (only a "Select..." placeholder) is usually a
  // hidden duplicate of a styled dropdown, so it is not worth offering to the model.
  const hasRealOptions = sel => [...sel.options].some(o => o.value && !o.disabled);

  for (const el of document.querySelectorAll('input, select, textarea')) {
    const tag = el.tagName.toLowerCase();
    const type = (el.getAttribute('type') || (tag === 'input' ? 'text' : tag)).toLowerCase();
    if (SKIP.has(type) || el.disabled || el.readOnly || !visible(el)) continue;
    if (tag === 'select' && !hasRealOptions(el)) continue;

    if (type === 'radio' || type === 'checkbox') {
      const groupId = groupKey(el, type);
      let f = groups.get(groupId);
      if (!f) {
        f = { key: 'f' + n++, kind: type, label: groupLabel(el) || ownLabel(el), name: el.name || '',
              placeholder: '', required: el.required, multiple: type === 'checkbox', options: [] };
        groups.set(groupId, f);
        fields.push(f);
      }
      el.setAttribute('data-aff-key', f.key);
      el.setAttribute('data-aff-opt', String(f.options.length));
      f.options.push({ label: ownLabel(el) || el.value, value: el.value });
      continue;
    }

    const f = { key: 'f' + n++, kind: tag === 'input' ? type : tag,
                label: ownLabel(el) || groupLabel(el), name: el.name || el.id || '',
                placeholder: clean(el.getAttribute('placeholder')), required: el.required,
                multiple: !!el.multiple, options: [] };
    if (tag === 'select') {
      f.options = [...el.options].map(o => ({ label: clean(o.text), value: o.value }));
    }
    el.setAttribute('data-aff-key', f.key);
    fields.push(f);
  }
  return fields;
}
"""


@dataclass
class Option:
    label: str
    value: str


@dataclass
class FormField:
    key: str
    kind: str  # text, email, tel, textarea, select, radio, checkbox, date, ...
    label: str = ""
    name: str = ""
    placeholder: str = ""
    required: bool = False
    multiple: bool = False
    options: list[Option] = field(default_factory=list)

    @property
    def selector(self) -> str:
        return f'[data-aff-key="{self.key}"]'

    def describe(self, max_options: int = 60) -> dict[str, Any]:
        """Compact description sent to the LLM."""
        info: dict[str, Any] = {"key": self.key, "kind": self.kind}
        for attr in ("label", "name", "placeholder"):
            if getattr(self, attr):
                info[attr] = getattr(self, attr)
        if self.required:
            info["required"] = True
        if self.options:
            labels = [o.label for o in self.options if o.label]
            if len(labels) <= max_options:
                info["options"] = labels
            else:
                info["options_note"] = f"{len(labels)} options; give the plain value"
        return info


def scan_form(page: Page) -> list[FormField]:
    """Return every visible, fillable field on the page (passwords and files excluded)."""
    raw = page.evaluate(_SCAN_JS)
    return [
        FormField(**{**f, "options": [Option(**o) for o in f.get("options", [])]})
        for f in raw
    ]
