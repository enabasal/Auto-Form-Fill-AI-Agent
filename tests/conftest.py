import json
import re
from pathlib import Path

import pytest

from autoformfill.profile import Profile

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def profile() -> Profile:
    return Profile(
        first_name="Enaba", last_name="Salman", email="enaba@example.com",
        phone="+91 90000 00000", address="Lucknow, Uttar Pradesh", city="Lucknow",
        country="India", skills=["Python", "SQL"],
    )


@pytest.fixture
def form_url() -> str:
    return (FIXTURES / "form.html").resolve().as_uri()


class RuleBasedLLM:
    """Stands in for the model: maps fields by simple keyword rules, plus one made-up key."""

    def __init__(self, profile: Profile):
        self.profile = profile
        self.prompts: list[str] = []

    def complete_json(self, system: str, user: str) -> dict:
        self.prompts.append(user)
        fields = json.loads(re.search(r"FORM FIELDS \(JSON\):\n(.*?)\n\nDecide", user, re.S).group(1))
        p, out = self.profile, {}
        for f in fields:
            text = " ".join(str(f.get(k, "")) for k in ("label", "placeholder", "name")).lower()
            if "first" in text:
                out[f["key"]] = p.first_name
            elif "last" in text:
                out[f["key"]] = p.last_name
            elif "email" in text:
                out[f["key"]] = p.email
            elif "phone" in text and f["kind"] != "checkbox":
                out[f["key"]] = p.phone
            elif "address" in text:
                out[f["key"]] = p.address
            elif "skill" in text:
                out[f["key"]] = "Python"
            elif "country" in text:
                out[f["key"]] = p.country
            elif "contact" in text:
                out[f["key"]] = ["Email", "Fax"]  # Fax is not an option
        out["f999"] = "made up"
        return {"fields": out}


@pytest.fixture
def chromium_available() -> None:
    from playwright.sync_api import Error, sync_playwright

    try:
        with sync_playwright() as pw:
            pw.chromium.launch().close()
    except Error:
        pytest.skip("Chromium is not installed (run: playwright install chromium)")
