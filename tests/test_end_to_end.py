"""Runs the whole agent on a local HTML form with a rule-based stand-in for the LLM."""

from autoformfill.agent import run_agent
from tests.conftest import RuleBasedLLM


def test_agent_fills_local_form(form_url, profile, chromium_available, tmp_path):
    llm = RuleBasedLLM(profile)
    report = run_agent(form_url, profile, llm, screenshot_path=tmp_path / "shot.png")

    by_label = {r.label: r for r in report.results}
    kinds = {r.kind for r in report.results}

    # Passwords, file uploads and hidden inputs are never offered to the model.
    assert "password" not in kinds and "file" not in kinds
    assert '"Password"' not in llm.prompts[0]

    filled = {r.label: r.value for r in report.results if r.status == "filled"}
    assert filled["Email address*"] == profile.email
    assert filled["Skills"] == "Python"
    assert filled["Country"] == "India"
    assert filled["Preferred contact"] == "Email (not found: Fax)"
    assert filled["Full Name* (First Name)"] == profile.first_name
    assert filled["Full Name* (Last Name)"] == profile.last_name

    # Unnamed checkboxes are grouped into one question; an empty dropdown is ignored.
    assert by_label["Languages"].kind == "checkbox"
    assert "Region" not in by_label
    assert all(r.label not in ("English", "Hindi") for r in report.results)

    # Fields the model had no answer for are skipped, invented keys are dropped.
    assert by_label["Gender*"].status == "skipped"
    assert by_label["I accept the terms"].status == "skipped"
    assert report.invented_keys == ["f999"]
    assert report.count("failed") == 0
    assert report.fill_rate == 1.0
    assert (tmp_path / "shot.png").exists()
