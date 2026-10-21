# Auto-Form-Fill AI Agent

A command-line agent that reads a PDF resume and fills in web forms with it. It uses Playwright to drive Chromium and an LLM on the Groq API to understand the resume and decide which value goes in which field. The default model is `openai/gpt-oss-120b`; the internship version used Llama 3.3 (70B), which Groq has since retired. Set `GROQ_MODEL` in `.env` to use another model.

I first built this during my AI engineering internship at Ascezen Consulting (Jan–Mar 2026), and later restructured it into a tested package.

## How it works

```
resume.pdf ──PyMuPDF──▶ text ──LLM──▶ profile.json (validated with Pydantic)
                                            │
form URL ──Playwright──▶ scan visible fields ─┴─▶ LLM decides value per field ──▶ fill ──▶ report
```

1. **Parse.** PyMuPDF extracts the resume text. The LLM turns it into a fixed JSON schema (name, contact details, address, skills, education, experience), which Pydantic validates. The result is saved as `profile.json` so later runs don't call the API again.
2. **Scan.** The agent finds every visible text field, text area, dropdown, radio group and checkbox group, along with its label. It tags each one in the page with a `data-aff-key` attribute. Password, file-upload and hidden fields are never touched.
3. **Plan.** The LLM gets the profile and the list of fields (with dropdown options) and answers with a value per field key. It only refers to keys the scanner created, so it never has to guess CSS selectors. Any key it makes up is dropped and logged.
4. **Fill.** Playwright fills text fields, picks the closest matching dropdown or radio option, and ticks checkboxes. If one field fails, the rest still continue.
5. **Report.** Every field is marked filled, failed or skipped. You get a summary in the terminal, a log file and, optionally, a JSON report and a screenshot.

**The agent never submits the form.** You review it and submit it yourself.

## Setup

Requires Python 3.10+ and a [Groq API key](https://console.groq.com).

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env              # then add your GROQ_API_KEY
```

## Usage

### Web interface

```bash
python main.py serve
```

This opens http://127.0.0.1:8000, a small page for managing your details. Upload your resume and the agent reads it, or type and correct the details yourself, then save. They're stored in `profile.json`, which the `fill` command uses. The server only listens on your own computer.

### Command line

```bash
# Parse a resume once
python main.py parse resume.pdf -o profile.json

# Fill a form from the saved profile (defaults to a public demo form)
python main.py fill --profile profile.json

# Any form, browser visible, with a screenshot and a JSON report
python main.py fill --url https://example.com/apply --visible \
    --screenshot screenshots/run.png --report reports/run.json

# Parse and fill in one go
python main.py fill --resume resume.pdf --url https://example.com/apply
```

Exit codes: `0` every attempted field was filled, `2` some fields failed, `1` error (missing key, unreadable resume, page not loading).

Example summary (from a run on the local test form):

```
OK   Full Name* (First Name)        Enaba
OK   Full Name* (Last Name)         Salman
OK   Address                        Lucknow, Uttar Pradesh
OK   Email address*                 enaba@example.com
OK   Phone                          +91 90000 00000
--   Gender*
OK   Preferred contact              Email (not found: Fax)
--   Languages
OK   Skills                         Python
OK   Country                        India
--   I accept the terms
----------------------------------------------------------------
Filled 8/8 attempted (100%), 3 skipped, 2.7s. The form was NOT submitted.
```

## Project structure

```
autoformfill/
  config.py     settings from .env
  llm.py        Groq client in JSON mode, tolerant JSON parsing
  profile.py    Pydantic profile model, PDF text extraction, resume parsing
  scanner.py    finds and tags form fields in the page
  mapper.py     asks the LLM which value goes where, drops invented keys
  filler.py     fills fields with Playwright, fuzzy option matching
  agent.py      runs one session and builds the report
  cli.py        command-line interface
  web.py        local web interface for your details (FastAPI)
  static/       the web page (plain HTML, CSS and JavaScript)
tests/          unit tests and an end-to-end test on a local HTML form
main.py         entry point
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

The tests don't need an API key or internet access. The end-to-end tests run the real agent in headless Chromium on `tests/fixtures/form.html`, from both the Python API and the web API, using a rule-based stand-in for the LLM.

## Limitations

- Single-page forms only. No multi-step wizards, iframes or CAPTCHAs.
- Text-based PDFs only. Scanned resumes would need OCR.
- Quality depends on how clearly the form labels its fields.
- File uploads (e.g. attaching the CV) and date pickers that aren't plain inputs are not handled.
- Tested on a demo registration form and the local test form, not on a large set of real application sites.
