"""Candidate profile: data model, resume parsing and JSON storage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from .llm import JSONLLM


class ResumeError(RuntimeError):
    """Raised when a resume cannot be read or parsed."""


class Education(BaseModel):
    model_config = ConfigDict(extra="ignore")
    degree: str = ""
    institution: str = ""
    year: str = ""
    grade: str = ""


class Experience(BaseModel):
    model_config = ConfigDict(extra="ignore")
    role: str = ""
    company: str = ""
    duration: str = ""
    description: str = ""


class Profile(BaseModel):
    """Everything the agent may use to fill a form. Missing values stay empty."""

    model_config = ConfigDict(extra="ignore")

    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    country: str = ""
    postal_code: str = ""
    linkedin_url: str = ""
    github_url: str = ""
    skills: list[str] = []
    languages: list[str] = []
    education: list[Education] = []
    experience: list[Experience] = []

    @model_validator(mode="before")
    @classmethod
    def _split_full_name(cls, data: Any) -> Any:
        if isinstance(data, dict) and data.get("full_name") and not data.get("first_name"):
            first, _, last = str(data["full_name"]).strip().partition(" ")
            data = {**data, "first_name": first, "last_name": data.get("last_name") or last}
        return data

    @field_validator("skills", "languages", mode="before")
    @classmethod
    def _coerce_list(cls, value: Any) -> Any:
        if value is None:
            return []
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value

    @field_validator("education", "experience", mode="before")
    @classmethod
    def _coerce_records(cls, value: Any) -> Any:
        if value is None:
            return []
        if isinstance(value, dict):
            return [value]
        return value

    @field_validator(
        "first_name", "last_name", "email", "phone", "address", "city", "state",
        "country", "postal_code", "linkedin_url", "github_url", mode="before",
    )
    @classmethod
    def _coerce_str(cls, value: Any) -> Any:
        return "" if value is None else str(value).strip()

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def is_usable(self) -> bool:
        return bool(self.full_name or self.email)


RESUME_SYSTEM = "You extract structured data from resumes. Reply with one JSON object only."

RESUME_PROMPT = """Extract the candidate's details from the resume text below.
Return a JSON object with exactly these keys (use "" or [] when something is not stated;
never guess):
first_name, last_name, email, phone, address, city, state, country, postal_code,
linkedin_url, github_url, skills (list of strings), languages (list of strings),
education (list of {{degree, institution, year, grade}}),
experience (list of {{role, company, duration, description}}).

RESUME TEXT:
{text}
"""


def extract_pdf_text(pdf_path: str | Path) -> str:
    """Return the text of a PDF. Raises ResumeError for missing or image-only files."""
    import pymupdf as fitz

    path = Path(pdf_path)
    if not path.is_file():
        raise ResumeError(f"Resume not found: {path}")
    with fitz.open(path) as doc:
        text = "\n".join(page.get_text() for page in doc).strip()
    if not text:
        raise ResumeError(f"No text found in {path}. Scanned (image-only) PDFs are not supported.")
    return text


def parse_resume(text: str, llm: JSONLLM) -> Profile:
    """Turn resume text into a validated Profile using the LLM."""
    data = llm.complete_json(RESUME_SYSTEM, RESUME_PROMPT.format(text=text[:20000]))
    try:
        profile = Profile.model_validate(data)
    except ValidationError as exc:
        raise ResumeError(f"Model output did not match the profile schema: {exc}") from exc
    if not profile.is_usable():
        raise ResumeError("Could not find a name or email in the resume.")
    return profile


def load_profile(path: str | Path) -> Profile:
    try:
        return Profile.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise ResumeError(f"Could not load profile from {path}: {exc}") from exc


def save_profile(profile: Profile, path: str | Path) -> None:
    Path(path).write_text(profile.model_dump_json(indent=2), encoding="utf-8")
