"""Command-line interface.

    python main.py serve                      (web interface)
    python main.py parse resume.pdf -o profile.json
    python main.py fill --url https://example.com/apply --profile profile.json
    python main.py fill --url https://example.com/apply --resume resume.pdf --visible
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from .agent import AgentError, run_agent
from .config import ConfigError, Settings
from .llm import GroqLLM, LLMError
from .profile import ResumeError, extract_pdf_text, load_profile, parse_resume, save_profile

DEMO_URL = "https://demo.automationtesting.in/Register.html"

EXIT_OK, EXIT_ERROR, EXIT_PARTIAL = 0, 1, 2

log = logging.getLogger("autoformfill")


def _setup_logging(log_dir: Path, verbose: bool) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"run_{datetime.now():%Y%m%d_%H%M%S}.log"
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler()],
    )
    for noisy in ("httpx", "httpcore", "groq"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    return log_file


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="autoformfill", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--log-dir", type=Path, default=Path("logs"))
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    p_parse = sub.add_parser("parse", help="Parse a PDF resume into a profile JSON file.")
    p_parse.add_argument("resume", type=Path)
    p_parse.add_argument("-o", "--output", type=Path, default=Path("profile.json"))

    p_fill = sub.add_parser("fill", help="Fill a web form from a profile (never submits).")
    p_fill.add_argument("--url", default=DEMO_URL, help=f"Form URL (default: {DEMO_URL})")
    src = p_fill.add_mutually_exclusive_group()
    src.add_argument("--profile", type=Path, default=Path("profile.json"))
    src.add_argument("--resume", type=Path, help="Parse this PDF first (saved to profile.json).")
    p_fill.add_argument("--visible", action="store_true", help="Show the browser window.")
    p_fill.add_argument("--screenshot", type=Path, help="Save a full-page screenshot here.")
    p_fill.add_argument("--report", type=Path, help="Write a JSON run report here.")
    p_fill.add_argument("--timeout", type=int, default=30, help="Page load timeout in seconds.")

    p_serve = sub.add_parser("serve", help="Open the web interface on this computer.")
    p_serve.add_argument("--port", type=int, default=8000)
    p_serve.add_argument("--no-browser", action="store_true", help="Don't open a browser tab.")
    return parser


def _print_summary(report) -> None:
    print("\n" + "-" * 64)
    for r in report.results:
        mark = {"filled": "OK  ", "failed": "FAIL", "skipped": "--  "}[r.status]
        extra = r.value if r.status == "filled" else r.detail
        print(f"{mark} {r.label[:30]:<30} {extra[:28]}")
    print("-" * 64)
    print(f"Filled {report.count('filled')}/{report.attempted} attempted "
          f"({report.fill_rate:.0%}), {report.count('skipped')} skipped, "
          f"{report.duration_s:.1f}s. The form was NOT submitted.")


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    log_file = _setup_logging(args.log_dir, args.verbose)

    if args.command == "serve":
        from .web import serve

        serve(port=args.port, open_browser=not args.no_browser)
        return EXIT_OK

    try:
        llm = GroqLLM(Settings.from_env())

        if args.command == "parse":
            profile = parse_resume(extract_pdf_text(args.resume), llm)
            save_profile(profile, args.output)
            print(f"Saved profile for {profile.full_name or profile.email} to {args.output}")
            return EXIT_OK

        if args.resume:
            profile = parse_resume(extract_pdf_text(args.resume), llm)
            save_profile(profile, Path("profile.json"))
            log.info("Parsed %s and saved profile.json", args.resume)
        else:
            profile = load_profile(args.profile)

        pause = None
        if args.visible:
            def pause() -> None:
                input("\nCheck the form in the browser, then press Enter here to close it... ")
        report = run_agent(args.url, profile, llm, headless=not args.visible,
                           screenshot_path=args.screenshot, timeout_ms=args.timeout * 1000,
                           pause=pause)
        _print_summary(report)
        if args.report:
            args.report.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        log.info("Log file: %s", log_file)
        return EXIT_OK if report.attempted and report.count("failed") == 0 else EXIT_PARTIAL

    except (ConfigError, ResumeError, LLMError, AgentError) as exc:
        log.error("%s", exc)
        return EXIT_ERROR
    except KeyboardInterrupt:
        log.error("Interrupted.")
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
