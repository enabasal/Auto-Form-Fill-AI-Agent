"""Thin wrapper around the Groq chat API that always returns a JSON object."""

from __future__ import annotations

import json
import re
from typing import Any, Protocol

from .config import Settings


class LLMError(RuntimeError):
    """Raised when the model call fails or returns unusable output."""


class JSONLLM(Protocol):
    """Anything that can answer a prompt with a JSON object (real or fake)."""

    def complete_json(self, system: str, user: str) -> dict[str, Any]: ...


def parse_json_object(text: str) -> dict[str, Any]:
    """Parse a JSON object from model output, tolerating code fences or stray text."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end <= start:
        raise LLMError(f"Model did not return a JSON object: {text[:200]!r}")
    try:
        data = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise LLMError(f"Model returned invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise LLMError("Model returned JSON that is not an object.")
    return data


class GroqLLM:
    """JSON-mode client for Groq. Retries and timeouts are handled by the SDK."""

    def __init__(self, settings: Settings):
        from groq import Groq  # imported here so tests don't need the network

        self.model = settings.model
        self._client = Groq(
            api_key=settings.groq_api_key,
            timeout=settings.timeout_s,
            max_retries=settings.max_retries,
        )

    def complete_json(self, system: str, user: str) -> dict[str, Any]:
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0,
                response_format={"type": "json_object"},
            )
        except Exception as exc:  # network, auth, rate limit...
            raise LLMError(f"Groq API call failed: {exc}") from exc
        return parse_json_object(response.choices[0].message.content or "")
