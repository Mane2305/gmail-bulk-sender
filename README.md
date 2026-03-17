# 📬 Gmail Bulk Sender — Selenium Automation

> Automate personalised bulk email outreach directly through Gmail's web UI — no SMTP limits, no API keys, no third-party services.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=flat-square&logo=python)
![Selenium](https://img.shields.io/badge/Selenium-Automation-green?style=flat-square&logo=selenium)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey?style=flat-square&logo=windows)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

---

## 🚀 What It Does

Send hundreds of personalised emails from your own Gmail account — using real browser automation instead of SMTP or API workarounds.

Each email is addressed individually (with the recipient's name/company auto-filled), sent with human-like typing delays to avoid spam detection, and the tool recovers from failures automatically.

---

## 🎯 Who Should Use This

| Use Case | Who |
|---|---|
| **Campus placement drives** | College TPOs, placement coordinators reaching out to recruiters |
| **Event invitations** | Organising teams sending bulk invites to companies or sponsors |
| **Cold outreach** | Freelancers, startups sending personalised B2B emails |
| **Marketing campaigns** | Small teams that want Gmail deliverability over Mailchimp |
| **NGOs / Non-profits** | Reaching donors or volunteers without paying for email tools |

If you have a Gmail account and a CSV of contacts — this tool works for you.

---

## ✨ Features

- **Chrome 145+ compatible** — uses CDP `Input.dispatchKeyEvent` to bypass Chrome's W3C interactability block (a fix most Selenium tutorials get wrong)
- **Anti-detection built-in** — randomised typing speed, human-like delays, `undetected_chromedriver` with navigator property spoofing
- **Session cookie caching** — logs in once, reuses the session on subsequent runs
- **Auto-retry per email** — retries up to 3 times on failure before moving on
- **Multi-selector fallback** — adapts to Gmail UI changes without breaking
- **Screenshot on failure** — saves a `.png` whenever an email fails, for easy debugging
- **Structured logging** — timestamped logs to both console and `gmail_send.log`
- **CSV-based contact list** — simple spreadsheet input, no database needed
- **Personalised body** — auto-fills `{company_name}` (or any field) per email

---

## 📁 Project Structure

```
gmail-bulk-sender/
├── selenium_email_sender.py   # Main script
├── companies.csv              # Your contact list (see format below)
├── gmail_send.log             # Auto-generated run log
├── gmail_session.pkl          # Auto-generated session cookies
└── README.md
```

---

## 🛠️ Setup

### 1. Prerequisites

- Python 3.8+
- Google Chrome installed
- Windows OS (Chrome version detection uses Windows Registry)

### 2. Install dependencies

```bash
pip install selenium undetected-chromedriver
```

### 3. Prepare your CSV

Your `companies.csv` should have at least 7 columns. The script reads:

| Column Index | Field |
|---|---|
| 2 | Company Name |
| 4 | Contact Person |
| 6 | Email Address |

Example:

```csv
id,type,company_name,industry,contact_person,designation,email
1,Recruiter,Acme Corp,IT,John Smith,HR Manager,hr@acmecorp.com
2,Recruiter,Bright Solutions,Finance,Jane Doe,Director,jane@brightsol.com
```

### 4. Configure the script

Open `selenium_email_sender.py` and update the config section at the top:

```python
CSV_FILE       = 'companies.csv'
EMAIL_ADDRESS  = "your_email@gmail.com"
EMAIL_PASSWORD = "your_password_here"   # Or leave as-is to be prompted at runtime
EMAIL_SUBJECT  = "Your Subject Here"
EMAIL_BODY     = """Your email body with {company_name} placeholder..."""
```

> **Tip:** Leave `EMAIL_PASSWORD = "your_password_here"` and the script will securely prompt you for the password at runtime instead of storing it in the file.

### 5. Run

```bash
python selenium_email_sender.py
```

A Chrome window will open, log into Gmail, and start sending. Watch the console for live progress.

---

## ⚙️ Configuration Options

| Variable | Default | Description |
|---|---|---|
| `HEADLESS_MODE` | `False` | Run browser invisibly (not recommended — causes login issues) |
| `DEBUG_MODE` | `True` | Keep browser open after run for inspection |
| `MIN_DELAY` | `12` | Minimum seconds to wait between emails |
| `MAX_DELAY` | `20` | Maximum seconds to wait between emails |

---

## 🔐 Security Notes

- **Never commit your password** to Git. Use the runtime prompt or environment variables:
  ```python
  import os
  EMAIL_PASSWORD = os.environ.get("GMAIL_PASSWORD", "your_password_here")
  ```
- Add `gmail_session.pkl` to your `.gitignore` — it contains your session cookies.
- Consider using a [Google App Password](https://support.google.com/accounts/answer/185833) if you have 2FA enabled.

**Recommended `.gitignore`:**
```
gmail_session.pkl
gmail_send.log
*.png
companies.csv
```

---

## 🧠 How It Works — The Technical Detail

Most Selenium tutorials fail on Chrome 131+ because Chrome's W3C input handler blocks synthetic `send_keys` events on `contenteditable` elements (like Gmail's compose body). This script solves that with **Chrome DevTools Protocol (CDP)**:

```
Standard Selenium send_keys  →  ChromeDriver W3C endpoint  →  Chrome InputHandler
                                                               ❌ Blocked on contenteditable (Chrome 131+)

CDP Input.dispatchKeyEvent   →  Chrome's raw input pipeline directly
                                ✅ No interactability check. Always works.
```

This is why the script uses `cdp_type()` for the To field and `js_set_body()` via `execCommand` for the message body.

---

## ⚠️ Responsible Use

- Respect email recipients — only send to people/organisations you have a legitimate reason to contact.
- Keep delays generous (`MIN_DELAY ≥ 10s`) to avoid triggering Gmail's spam detection.
- Gmail may flag the account for unusual activity if too many emails are sent in one session. For large lists (500+), split across multiple sessions or days.
- This tool automates the Gmail UI and is subject to [Google's Terms of Service](https://policies.google.com/terms). Use responsibly.

---

## 🗺️ Roadmap / Possible Improvements

- [ ] Resume tracking — skip already-sent emails across sessions
- [ ] Linux/macOS support (remove `winreg` dependency)
- [ ] HTML email support
- [ ] Attachment support
- [ ] Gmail API mode as an alternative backend
- [ ] GUI / web dashboard

PRs welcome!

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

> Built with Python + Selenium. Crafted to solve a real problem with a robust, production-aware approach.