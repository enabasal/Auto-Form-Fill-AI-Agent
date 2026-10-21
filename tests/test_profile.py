import pytest

from autoformfill.profile import Profile, ResumeError, load_profile, parse_resume, save_profile


class FakeLLM:
    def __init__(self, reply):
        self.reply = reply

    def complete_json(self, system, user):
        return self.reply


def test_full_name_is_split_and_types_are_coerced():
    p = Profile.model_validate({
        "full_name": "Enaba Salman", "skills": "Python, SQL ,", "phone": 9000000000,
        "education": {"degree": "BCA", "institution": "Integral University"}, "extra": "ignored",
    })
    assert (p.first_name, p.last_name) == ("Enaba", "Salman")
    assert p.skills == ["Python", "SQL"]
    assert p.phone == "9000000000"
    assert p.education[0].degree == "BCA"


def test_parse_resume_validates(profile):
    parsed = parse_resume("resume text", FakeLLM(profile.model_dump()))
    assert parsed == profile


def test_parse_resume_rejects_empty_result():
    with pytest.raises(ResumeError):
        parse_resume("resume text", FakeLLM({"skills": ["Python"]}))


def test_round_trip(tmp_path, profile):
    path = tmp_path / "profile.json"
    save_profile(profile, path)
    assert load_profile(path) == profile


def test_load_missing_file(tmp_path):
    with pytest.raises(ResumeError):
        load_profile(tmp_path / "nope.json")
