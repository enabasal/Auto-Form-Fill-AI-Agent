# Quick Start Guide

## First Time Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 2. Add your API key to .env
echo "GROQ_API_KEY=your_api_key_here" > .env

# 3. Place your resume.pdf in the project folder
```

## Usage Examples

### Basic Usage (Headless Mode)
```bash
python main.py
```
- Runs in background (no browser window)
- Uses resume.pdf and profile.json
- Fills default demo form
- Logs saved to logs/ folder

### See It Working (Visible Mode)
```bash
python main.py --visible
```
- Opens browser window
- Watch form being filled
- Great for debugging

### With Screenshot
```bash
python main.py --screenshot
```
- Takes screenshot after filling
- Saved to screenshots/ folder
- Proof of completion

### Custom Resume
```bash
python main.py --resume myresume.pdf
```
- Parse a different resume
- Updates profile.json automatically

### Custom Form URL
```bash
python main.py --url "https://example.com/application"
```
- Fill a different form
- Note: May need to update field selectors in main.py

### Full Example
```bash
python main.py --resume myresume.pdf --url "https://form.example.com" --visible --screenshot
```

## Understanding the Output

### Console Output
```
2026-02-17 14:30:52,123 - INFO - ============================================================
2026-02-17 14:30:52,124 - INFO - Auto Form Fill Agent - Starting Session
2026-02-17 14:30:52,125 - INFO - ============================================================
2026-02-17 14:30:52,126 - INFO - Target URL: https://demo.automationtesting.in/Register.html
2026-02-17 14:30:52,127 - INFO - Mode: Headless
2026-02-17 14:30:52,128 - INFO - Log file: logs\form_fill_20260217_143052.log
2026-02-17 14:30:53,456 - INFO - Successfully loaded profile from profile.json
2026-02-17 14:30:55,234 - INFO - Navigating to: https://demo.automationtesting.in/Register.html
2026-02-17 14:30:57,891 - INFO - Page loaded successfully
2026-02-17 14:30:58,123 - INFO - Starting form field filling...
2026-02-17 14:30:58,456 - INFO - ✓ First name: Enaba
2026-02-17 14:30:58,789 - INFO - ✓ Last name: Salman
2026-02-17 14:30:59,123 - INFO - ✓ Email: enaba584@gmail.com
2026-02-17 14:30:59,456 - INFO - ✓ Phone: +91 9219476008
2026-02-17 14:30:59,789 - INFO - ✓ Address: Lucknow, Lucknow
2026-02-17 14:31:00,456 - INFO - ✓ Country: India
2026-02-17 14:31:01,234 - INFO - ✓ Skills: Python
2026-02-17 14:31:02,456 - INFO - ============================================================
2026-02-17 14:31:02,457 - INFO - Session Summary
2026-02-17 14:31:02,458 - INFO - ============================================================
2026-02-17 14:31:02,459 - INFO - Fields filled: 7/7 (100.0%)
2026-02-17 14:31:02,460 - INFO - Duration: 10.33 seconds
2026-02-17 14:31:02,461 - INFO - Status: SUCCESS
2026-02-17 14:31:02,462 - INFO - ============================================================
2026-02-17 14:31:02,789 - INFO - Browser closed
```

### Exit Codes
- `0` - All fields filled successfully
- `1` - Some fields failed or error occurred

### Check Logs
```bash
# View latest log
cat logs/form_fill_*.log | tail -20

# List all logs
ls logs/
```

## Troubleshooting

### Profile.json Not Found (First Run)
```
2026-02-17 14:30:52,128 - WARNING - profile.json not found
2026-02-17 14:30:52,129 - INFO - Parsing resume from resume.pdf...
```
**Normal behavior**: First run parses PDF and creates profile.json

### Fields Not Filling
```bash
# Run in visible mode to see what's happening
python main.py --visible

# Check the log file for detailed errors
cat logs/form_fill_*.log
```

### API Key Error
```
Error loading profile: ...
```
**Fix**: Check `.env` file has correct `GROQ_API_KEY`

## Customizing for Your Form

1. **Identify field selectors** using browser DevTools:
   - Right-click field → Inspect
   - Note the `id`, `placeholder`, or `name` attribute

2. **Update main.py** in the `fill_form()` function:
   ```python
   # Example: Add a new field
   try:
       linkedin = page.locator("input[name='linkedin']")
       if linkedin.count() > 0:
           linkedin.fill(user_profile['social']['linkedin'])
           logger.info(f"✓ LinkedIn filled")
           filled_count += 1
   except Exception as e:
       logger.warning(f"✗ Could not fill LinkedIn: {e}")
       failed_fields.append("linkedin")
   ```

3. **Test**:
   ```bash
   python main.py --visible
   ```

## Tips & Best Practices

1. **Always test with --visible first** for new forms
2. **Check logs/** after each run for debugging
3. **Keep profile.json** - saves API calls on reruns
4. **Use --screenshot** for record-keeping
5. **Update field selectors** if form changes

## Next Steps

- Read [README.md](README.md) for full documentation
- Check `main.py` to understand the code
- Explore `resume_parser.py` for AI parsing logic
- Customize for your specific forms
