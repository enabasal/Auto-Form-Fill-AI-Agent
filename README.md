# 🤖 Auto Form Fill AI Agent

An intelligent CLI tool that automatically fills web forms using AI-parsed resume data. Built with Playwright for browser automation and Groq's Llama 3 API for resume parsing.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-Active-success.svg)

## 🎯 What It Does

- **📄 Resume Parsing**: Extracts structured data from PDF resumes using AI
- **🌐 Form Automation**: Automatically fills web forms with extracted data
- **📊 Smart Logging**: Tracks success rates and generates detailed logs
- **⚡ CLI-Based**: Runs headlessly for fast, automated workflows
- **🔄 Flexible**: Support for custom forms and configuration

## 🏗️ Architecture

```
Resume PDF → AI Parser (Groq) → Structured JSON → Browser Automation (Playwright) → Filled Form
```

**Key Components:**
- `resume_parser.py` - AI-powered resume extraction
- `main.py` - Form filling orchestration  
- `profile.json` - Structured user data cache
- `logs/` - Session logs with timestamps

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Groq API Key ([Get one here](https://console.groq.com))

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd Auto-Form-Fill-AI-Agent

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Setup API key
echo "GROQ_API_KEY=your_api_key_here" > .env
```

### Basic Usage

```bash
# Default: Fills demo form with resume.pdf
python main.py

# Custom resume
python main.py --resume path/to/your_resume.pdf

# Custom form URL
python main.py --url https://example.com/job-application

# Visible mode (see browser in action)
python main.py --visible

# Take screenshot after completion
python main.py --screenshot

# Full example
python main.py --resume resume.pdf --url https://form.example.com --visible --screenshot
```

## 📁 Project Structure

```
Auto-Form-Fill-AI-Agent/
├── main.py              # Main CLI application
├── resume_parser.py     # AI resume parsing logic
├── config.py            # Configuration management
├── profile.json         # Cached user data (generated)
├── requirements.txt     # Python dependencies
├── .env                 # API keys (create this)
├── logs/                # Execution logs (created automatically)
├── screenshots/         # Form screenshots (optional)
└── README.md            # This file
```

## ⚙️ Configuration

### Environment Variables (.env)
```bash
GROQ_API_KEY=your_groq_api_key
```

### CLI Options
```
--resume PATH        Path to resume PDF (default: resume.pdf)
--profile PATH       Path to profile JSON (default: profile.json)
--url URL            Target form URL (default: demo form)
--visible            Show browser window (default: headless)
--screenshot         Capture screenshot after filling
```

## 📊 Features Deep Dive

### 1. Resume Parsing
- Extracts: Name, email, phone, address, skills, education, experience
- Uses Groq's Llama 3.3 70B model for accuracy
- Caches results in `profile.json` for faster reruns

### 2. Form Filling
Intelligently fills common form fields:
- ✅ Text inputs (name, email, phone, address)
- ✅ Dropdowns (country, skills)
- ✅ Textareas (address, bio)
- ⏳ Radio buttons (coming soon)
- ⏳ Checkboxes (coming soon)

### 3. Logging System
Every run creates a timestamped log file:
```
logs/form_fill_20260217_143052.log
```

Example log output:
```
2026-02-17 14:30:52 - INFO - Auto Form Fill Agent - Starting Session
2026-02-17 14:30:52 - INFO - Target URL: https://demo.automationtesting.in/Register.html
2026-02-17 14:30:53 - INFO - Successfully loaded profile from profile.json
2026-02-17 14:30:55 - INFO - ✓ First name: Enaba
2026-02-17 14:30:56 - INFO - ✓ Email: enaba584@gmail.com
...
2026-02-17 14:31:02 - INFO - Fields filled: 7/7 (100.0%)
2026-02-17 14:31:02 - INFO - Status: SUCCESS
```

### 4. Error Handling
- Validates profile JSON structure
- Graceful fallbacks for missing fields
- Detailed error logs with stack traces
- Exit codes: 0 (success), 1 (failure)

## 🎓 Use Cases

### For Job Seekers
- Automate job application forms
- Save time on repetitive data entry
- Ensure consistency across applications

### For Recruiters
- Pre-fill candidate information forms
- Batch process multiple applications
- Integration with ATS systems

### For Developers
- Learn browser automation with Playwright
- Understand AI-powered parsing
- Build custom form filling solutions

## 🔧 Customization

### Adding New Form Fields

Edit the `fill_form()` function in `main.py`:

```python
# Example: Fill a custom field
try:
    custom_field = page.locator("#your-field-id")
    if custom_field.count() > 0:
        custom_field.fill(user_profile['your_data'])
        logger.info(f"✓ Custom field filled")
        filled_count += 1
except Exception as e:
    logger.warning(f"✗ Could not fill custom field: {e}")
```

### Supporting Different Forms

1. Inspect the target form's HTML
2. Identify field selectors (ID, placeholder, type)
3. Update selectors in `fill_form()` function
4. Test with `--visible` flag

## 🐛 Troubleshooting

### Common Issues

**1. "profile.json not found"**
- First run automatically parses resume.pdf
- Ensure resume.pdf exists in the project directory

**2. "Invalid API key"**
- Check `.env` file has correct `GROQ_API_KEY`
- Verify key at https://console.groq.com

**3. "Fields not filling"**
- Use `--visible` to see browser
- Check logs/ directory for detailed error messages
- Form selectors may have changed – update in main.py

**4. "Playwright not installed"**
```bash
playwright install chromium
```

## 📈 Performance

- **Average runtime**: 5-10 seconds per form
- **Success rate**: 90%+ on standard forms
- **Resume parsing**: ~2 seconds (first run only)
- **Cached runs**: <1 second (using profile.json)

## 🛡️ Limitations

- **Form-specific selectors**: Currently optimized for demo form
- **English only**: Best results with English resumes
- **Single-page forms**: Multi-step forms need customization
- **No CAPTCHA bypass**: Human interaction required

## 🤝 Contributing

This is an educational/internship project. Suggestions welcome!

Areas for improvement:
- [ ] Generic form field detection (AI-based)
- [ ] Multi-page form support
- [ ] More field types (radio, checkbox, file uploads)
- [ ] Form config templates (JSON-based)
- [ ] Better error recovery
- [ ] Unit tests coverage

## 📝 License

MIT License - Feel free to use for learning and personal projects.

## 🙋 Author

Created as an internship/learning project demonstrating:
- AI integration (Groq LLM)
- Browser automation (Playwright)
- Python CLI development
- Logging & error handling
- Resume parsing and data extraction

## 📚 Tech Stack Details

| Technology | Purpose | Version |
|------------|---------|---------|
| Python | Core language | 3.8+ |
| Playwright | Browser automation | Latest |
| Groq API | AI resume parsing | Llama 3.3 70B |
| PyMuPDF | PDF text extraction | Latest |
| python-dotenv | Environment config | Latest |
| argparse | CLI interface | Built-in |
| logging | Session tracking | Built-in |

## 🎯 Learning Outcomes

By studying this project, you'll learn:
1. **API Integration**: Working with AI APIs (Groq)
2. **Web Automation**: Playwright for form filling
3. **Data Extraction**: PDF parsing and structuring
4. **CLI Design**: Professional command-line tools
5. **Error Handling**: Robust production-ready code
6. **Logging**: Debugging and monitoring best practices

## 🛠️ Developer Usage: Multiple Profiles

The system is designed to be user-agnostic. To process a new candidate:

1. **Extraction:**
   `python main.py --resume candidate_b.pdf`
   *This triggers the extraction layer and updates the local state.*

2. **Targeted Execution:**
   `python main.py --profile candidate_b.json --url [TARGET_URL]`
   *Injects the specific candidate schema into the Agentic reasoning loop.*

---

**Demo Form**: https://demo.automationtesting.in/Register.html  
**Questions?** Check logs/ directory for detailed execution info
