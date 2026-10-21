"""One agent run: open the page, scan it, plan with the LLM, fill, report.

The agent never submits the form. A person should review and submit it.
"""

from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

from .filler import FieldResult, apply_actions
from .llm import JSONLLM
from .mapper import plan_fill
from .profile import Profile
from .scanner import scan_form

log = logging.getLogger(__name__)


class AgentError(RuntimeError):
    """Raised when the page cannot be loaded or has no fillable fields."""


@dataclass
class RunReport:
    url: str
    started_at: str
    duration_s: float = 0.0
    results: list[FieldResult] = field(default_factory=list)
    invented_keys: list[str] = field(default_factory=list)
    screenshot: str | None = None

    def count(self, status: str) -> int:
        return sum(r.status == status for r in self.results)

    @property
    def attempted(self) -> int:
        return self.count("filled") + self.count("failed")

    @property
    def fill_rate(self) -> float:
        """Share of the fields the agent tried to fill that it actually filled."""
        return self.count("filled") / self.attempted if self.attempted else 0.0

    def to_dict(self) -> dict:
        data = asdict(self)
        data.update(
            fields_detected=len(self.results),
            filled=self.count("filled"),
            failed=self.count("failed"),
            skipped=self.count("skipped"),
            fill_rate=round(self.fill_rate, 3),
        )
        return data


def run_agent(
    url: str,
    profile: Profile,
    llm: JSONLLM,
    *,
    headless: bool = True,
    screenshot_path: str | Path | None = None,
    timeout_ms: int = 30_000,
    pause: Callable[[], None] | None = None,
) -> RunReport:
    """Fill the form at `url`. `pause`, if given, runs after filling and before the
    browser closes, so a person can look at the result in visible mode."""
    report = RunReport(url=url, started_at=datetime.now().isoformat(timespec="seconds"))
    start = time.perf_counter()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        try:
            page = browser.new_page()
            page.set_default_timeout(timeout_ms)
            try:
                page.goto(url, wait_until="domcontentloaded")
            except PlaywrightTimeout as exc:
                raise AgentError(f"Page did not load within {timeout_ms / 1000:.0f}s: {url}") from exc
            try:
                page.wait_for_load_state("networkidle", timeout=10_000)
            except PlaywrightTimeout:
                log.info("Page still busy after 10s; continuing with what has loaded.")

            fields = scan_form(page)
            log.info("Detected %d fillable fields", len(fields))
            if not fields:
                raise AgentError("No fillable form fields found on the page.")

            actions, report.invented_keys = plan_fill(fields, profile, llm)
            log.info("Model proposed values for %d fields", len(actions))
            report.results = apply_actions(page, fields, actions)

            if screenshot_path:
                Path(screenshot_path).parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(screenshot_path), full_page=True)
                report.screenshot = str(screenshot_path)

            if pause:
                pause()
        finally:
            browser.close()

    report.duration_s = round(time.perf_counter() - start, 2)
    return report
