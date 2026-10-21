"""Local web interface: `python main.py serve`, then open http://127.0.0.1:8000.

The server only listens on this computer. It reuses the same agent as the CLI.
"""

from __future__ import annotations

import logging
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, ValidationError

from .agent import AgentError, run_agent
from .config import ConfigError, Settings
from .llm import JSONLLM, GroqLLM, LLMError
from .profile import Profile, ResumeError, extract_pdf_text, load_profile, parse_resume, save_profile

log = logging.getLogger(__name__)

STATIC = Path(__file__).parent / "static"
DEMO_URL = "https://demo.automationtesting.in/Register.html"
SHOW_BROWSER_SECONDS = 12
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


class FillRequest(BaseModel):
    url: str = DEMO_URL
    show_browser: bool = False


def create_app(
    llm_factory: Callable[[], JSONLLM] | None = None,
    profile_path: Path = Path("profile.json"),
    screenshot_dir: Path = Path("screenshots"),
) -> FastAPI:
    app = FastAPI(title="Auto-Form-Fill AI Agent", docs_url=None, redoc_url=None)
    run_lock = threading.Lock()
    llm_holder: dict[str, JSONLLM] = {}

    def get_llm() -> JSONLLM:
        if "llm" not in llm_holder:
            try:
                llm_holder["llm"] = (llm_factory or (lambda: GroqLLM(Settings.from_env())))()
            except ConfigError as exc:
                raise HTTPException(503, str(exc)) from exc
        return llm_holder["llm"]

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC / "index.html")

    @app.get("/api/profile")
    def get_profile() -> dict:
        if not profile_path.exists():
            return {"profile": None}
        try:
            return {"profile": load_profile(profile_path).model_dump()}
        except ResumeError as exc:
            raise HTTPException(500, str(exc)) from exc

    @app.put("/api/profile")
    def put_profile(data: dict) -> dict:
        try:
            profile = Profile.model_validate(data)
        except ValidationError as exc:
            raise HTTPException(422, f"These details aren't valid: {exc.errors()[0]['msg']}") from exc
        if not profile.is_usable():
            raise HTTPException(422, "Add at least a name or an email address.")
        save_profile(profile, profile_path)
        return {"profile": profile.model_dump()}

    @app.post("/api/resume")
    def upload_resume(file: UploadFile = File(...)) -> dict:
        if not (file.filename or "").lower().endswith(".pdf"):
            raise HTTPException(415, "Choose a PDF file.")
        content = file.file.read(MAX_UPLOAD_BYTES + 1)
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "That PDF is larger than 10 MB.")
        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / "resume.pdf"
            pdf.write_bytes(content)
            try:
                profile = parse_resume(extract_pdf_text(pdf), get_llm())
            except (ResumeError, LLMError) as exc:
                raise HTTPException(422, str(exc)) from exc
        save_profile(profile, profile_path)
        return {"profile": profile.model_dump()}

    @app.post("/api/fill")
    def fill(req: FillRequest) -> dict:
        if urlparse(req.url).scheme not in ("http", "https", "file"):
            raise HTTPException(422, "Enter a full web address starting with http:// or https://.")
        if not profile_path.exists():
            raise HTTPException(409, "Add your details first: upload a resume or fill them in.")
        if not run_lock.acquire(blocking=False):
            raise HTTPException(409, "A form is already being filled. Wait for it to finish.")
        try:
            profile = load_profile(profile_path)
            shot = screenshot_dir / f"run_{datetime.now():%Y%m%d_%H%M%S_%f}.png"
            pause = (lambda: time.sleep(SHOW_BROWSER_SECONDS)) if req.show_browser else None
            report = run_agent(req.url, profile, get_llm(), headless=not req.show_browser,
                               screenshot_path=shot, pause=pause)
        except (AgentError, LLMError, ResumeError) as exc:
            raise HTTPException(422, str(exc)) from exc
        except Exception as exc:  # Playwright errors, e.g. browser not installed
            log.exception("Fill failed")
            raise HTTPException(500, str(exc).splitlines()[0]) from exc
        finally:
            run_lock.release()
        data = report.to_dict()
        data["screenshot_url"] = f"/api/screenshots/{shot.name}" if report.screenshot else None
        return data

    @app.get("/api/screenshots/{name}", include_in_schema=False)
    def screenshot(name: str) -> FileResponse:
        path = (screenshot_dir / name).resolve()
        if path.parent != screenshot_dir.resolve() or not path.is_file():
            raise HTTPException(404, "Screenshot not found.")
        return FileResponse(path)

    return app


def serve(port: int = 8000, open_browser: bool = True) -> None:
    import uvicorn
    import webbrowser

    url = f"http://127.0.0.1:{port}"
    print(f"Auto-Form-Fill is running at {url}  (press Ctrl+C to stop)")
    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    uvicorn.run(create_app(), host="127.0.0.1", port=port, log_level="warning")
