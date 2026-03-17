#!/usr/bin/env python3
"""
Robust Gmail Bulk Sender — Selenium + undetected_chromedriver
Chrome 145 Fix: CDP Input.dispatchKeyEvent bypasses ElementNotInteractable entirely.
"""

import csv, time, logging, pickle, os, random, getpass, winreg
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException,
    WebDriverException, NoSuchWindowException,
    StaleElementReferenceException
)
import undetected_chromedriver as uc

# ===================== CONFIG =====================
CSV_FILE       = 'companies.csv'
EMAIL_ADDRESS  = "your_email@gmail.com"       # 👈 Replace with your Gmail address
EMAIL_PASSWORD = "your_password_here"          # 👈 Replace with your password, or leave as-is to be prompted at runtime
COOKIES_FILE   = "gmail_session.pkl"
HEADLESS_MODE  = False
DEBUG_MODE     = True
MIN_DELAY      = 12
MAX_DELAY      = 20

# 👇 Replace with your email subject
EMAIL_SUBJECT = "Your Email Subject Here"

# 👇 Replace this with your own email body.
#    Use {company_name} anywhere you want the recipient's company name to be auto-filled.
EMAIL_BODY = """To,
The Manager,
{company_name}

Dear Sir/Madam,

I hope this message finds you well.

I am reaching out to introduce myself and explore a potential opportunity to collaborate with {company_name}.

[Write your main message here. You can personalise it further by adding more
placeholders like {contact_person} if your CSV has that column, and passing
them into the .format() call in the main() function.]

Looking forward to hearing from you.

Warm regards,
[Your Name]
[Your Designation]
[Your Organisation]
[Your Contact Number]"""

# ===================== LOGGING =====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('gmail_send.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)


# ===================== WINDOW GUARD =====================

def switch_to_active_window(driver):
    try:
        handles = driver.window_handles
        if not handles:
            raise NoSuchWindowException("No open windows found")
        driver.switch_to.window(handles[-1])
    except Exception as e:
        log.error(f"switch_to_active_window failed: {e}")
        raise


def safe_screenshot(driver, filename):
    try:
        switch_to_active_window(driver)
        driver.save_screenshot(filename)
        log.info(f"Screenshot saved: {filename}")
    except Exception:
        log.warning(f"Could not save screenshot: {filename}")


# ===================== CHROME SETUP =====================

def get_chrome_major_version():
    paths = [
        r"SOFTWARE\Google\Chrome\BLBeacon",
        r"SOFTWARE\Wow6432Node\Google\Chrome\BLBeacon",
    ]
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for path in paths:
            try:
                key = winreg.OpenKey(hive, path)
                version, _ = winreg.QueryValueEx(key, "version")
                major = int(version.split('.')[0])
                log.info(f"Detected Chrome {version}  (major={major})")
                return major
            except Exception:
                continue
    log.warning("Could not detect Chrome version — letting uc decide")
    return None


def setup_driver():
    options = ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
    )
    options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.notifications": 2,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
    })

    chrome_major = get_chrome_major_version()
    kwargs = dict(use_subprocess=True, suppress_welcome=True)
    if chrome_major:
        kwargs["version_main"] = int(chrome_major)  # type: ignore

    driver = uc.Chrome(options, **kwargs)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": """
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins',   {get: () => [1,2,3,4,5]});
        Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en']});
        window.chrome = { runtime: {} };
    """})
    driver.set_page_load_timeout(60)
    return driver


# ===================== CDP TYPING — THE ACTUAL FIX =====================
#
# WHY THIS WORKS:
#   Selenium send_keys   → ChromeDriver W3C endpoint → Chrome InputHandler
#                          Chrome 145 blocks synthetic events on contenteditable ✗
#   ActionChains Ctrl+V  → Same W3C path, same block ✗
#
#   CDP Input.dispatchKeyEvent → Chrome's raw input pipeline directly,
#                          NO interactability check. Always works. ✓
#
# The stacktrace is identical every attempt because it's crashing inside
# ChromeDriver's W3C input handler — not in your Python code or Gmail's JS.
# CDP bypasses ChromeDriver's W3C layer entirely.

def cdp_focus_element(driver, element):
    """Focus element via JS — positions cursor only, no typing."""
    driver.execute_script(
        "arguments[0].scrollIntoView({block:'center', behavior:'instant'});"
        "arguments[0].focus();"
        "arguments[0].click();",
        element
    )
    time.sleep(0.4)


def cdp_type(driver, text, char_delay=(0.04, 0.09)):
    """
    Type text via CDP Input.dispatchKeyEvent.
    Completely bypasses Chrome 145's W3C interactability gate.
    """
    for char in text:
        driver.execute_cdp_cmd("Input.dispatchKeyEvent", {
            "type": "keyDown",
            # NO "text" here — keyDown must not insert characters
            "key": char,
            "code": f"Key{char.upper()}" if char.isalpha() else "Unidentified",
            "windowsVirtualKeyCode": ord(char) if ord(char) < 256 else 0,
            "nativeVirtualKeyCode":  ord(char) if ord(char) < 256 else 0,
            "isSystemKey": False,
            "modifiers": 0,
        })
        # "char" is the ONLY event that should carry "text" — this is what inserts the char
        driver.execute_cdp_cmd("Input.dispatchKeyEvent", {
            "type": "char",
            "text": char,
            "key": char,
            "modifiers": 0,
        })
        driver.execute_cdp_cmd("Input.dispatchKeyEvent", {
            "type": "keyUp",
            # NO "text" here either
            "key": char,
            "code": f"Key{char.upper()}" if char.isalpha() else "Unidentified",
            "windowsVirtualKeyCode": ord(char) if ord(char) < 256 else 0,
            "nativeVirtualKeyCode":  ord(char) if ord(char) < 256 else 0,
            "modifiers": 0,
        })
        time.sleep(random.uniform(*char_delay))


def cdp_press_key(driver, key_name, modifiers=0):
    """Press a special key via CDP (Tab, Return, Escape, etc.)"""
    key_codes = {'Tab': 9, 'Return': 13, 'Escape': 27, 'Backspace': 8}
    vk = key_codes.get(key_name, 0)
    for event_type in ("keyDown", "keyUp"):
        driver.execute_cdp_cmd("Input.dispatchKeyEvent", {
            "type": event_type,
            "key": key_name,
            "code": key_name,
            "windowsVirtualKeyCode": vk,
            "nativeVirtualKeyCode": vk,
            "modifiers": modifiers,
        })
        time.sleep(0.1)


def js_set_body(driver, element, text):
    """
    Set body text via JS execCommand — fast for long text.
    execCommand('insertText') triggers Gmail's input listeners correctly.
    """
    driver.execute_script("""
        var el = arguments[0];
        el.focus();
        el.innerText = '';
        document.execCommand('selectAll', false, null);
        document.execCommand('insertText', false, arguments[1]);
        el.dispatchEvent(new Event('input', {bubbles: true}));
    """, element, text)


# ===================== STANDARD TYPING (plain <input> fields only) =====================

def human_type(element, text, delay=(0.07, 0.15)):
    for ch in text:
        element.send_keys(ch)
        time.sleep(random.uniform(*delay))


# ===================== COOKIE HELPERS =====================

def save_cookies(driver):
    try:
        switch_to_active_window(driver)
        with open(COOKIES_FILE, 'wb') as f:
            pickle.dump(driver.get_cookies(), f)
        log.info("Session cookies saved.")
    except Exception as e:
        log.warning(f"Could not save cookies: {e}")


def try_cookie_login(driver):
    if not os.path.exists(COOKIES_FILE):
        return False
    try:
        driver.get("https://mail.google.com")
        time.sleep(4)
        switch_to_active_window(driver)
        with open(COOKIES_FILE, 'rb') as f:
            for cookie in pickle.load(f):
                try:
                    driver.add_cookie(cookie)
                except Exception:
                    pass
        driver.refresh()
        time.sleep(5)
        switch_to_active_window(driver)
        if _is_inbox(driver):
            log.info("Logged in via saved cookies.")
            return True
    except Exception as e:
        log.warning(f"Cookie login failed: {e}")
    return False


def _is_inbox(driver):
    try:
        url = driver.current_url
        return "mail.google.com/mail" in url or "inbox" in url.lower()
    except Exception:
        return False


# ===================== LOGIN =====================

def login_to_gmail(driver, email, password, max_retries=3):
    if try_cookie_login(driver):
        return True

    EMAIL_SELECTORS = [
        "input[type='email'][name='identifier']",
        "input#identifierId",
        "input[type='email']",
    ]
    PW_SELECTORS = [
        "input[type='password'][name='Passwd']",
        "input[type='password'][name='password']",
        "input[type='password']",
    ]

    for attempt in range(1, max_retries + 1):
        log.info(f"Login attempt {attempt}/{max_retries}...")
        try:
            driver.get("https://accounts.google.com/signin/v2/identifier?service=mail")
            time.sleep(4)
            switch_to_active_window(driver)

            el = None
            for sel in EMAIL_SELECTORS:
                try:
                    el = WebDriverWait(driver, 20).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, sel))
                    )
                    WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                    )
                    break
                except TimeoutException:
                    continue
            if el is None:
                log.warning("Email field not found")
                safe_screenshot(driver, f"login_fail_email_{attempt}.png")
                continue

            el.click(); time.sleep(0.4); el.clear()
            human_type(el, email)
            el.send_keys(Keys.ENTER)
            time.sleep(4)
            switch_to_active_window(driver)

            pw_el = None
            for sel in PW_SELECTORS:
                try:
                    pw_el = WebDriverWait(driver, 20).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, sel))
                    )
                    WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                    )
                    break
                except TimeoutException:
                    continue
            if pw_el is None:
                log.warning("Password field not found")
                safe_screenshot(driver, f"login_fail_pw_{attempt}.png")
                continue

            pw_el.click(); time.sleep(0.4); pw_el.clear()
            human_type(pw_el, password)
            pw_el.send_keys(Keys.ENTER)
            time.sleep(8)
            switch_to_active_window(driver)

            if "managed-user-profile-notice" in driver.current_url:
                log.info("Managed profile notice — dismissing...")
                try:
                    driver.find_element(
                        By.XPATH,
                        "//*[contains(text(),'Continue to work in this profile')]"
                        "/ancestor::*[self::label or self::div][1]"
                    ).click()
                    time.sleep(1)
                except Exception:
                    pass
                try:
                    driver.find_element(
                        By.XPATH,
                        "//button[normalize-space(text())='Confirm'] | "
                        "//*[@id='confirm-button'] | "
                        "//cr-button[normalize-space(.)='Confirm']"
                    ).click()
                    time.sleep(4)
                    switch_to_active_window(driver)
                except Exception:
                    driver.get("https://mail.google.com/mail/u/0/#inbox")
                    time.sleep(5)
                    switch_to_active_window(driver)

            for txt in ["Skip", "Not now", "Remind me later", "No thanks"]:
                try:
                    driver.find_element(
                        By.XPATH,
                        f"//*[normalize-space(text())='{txt}' or "
                        f"contains(normalize-space(text()),'{txt}')]"
                    ).click()
                    time.sleep(2)
                except Exception:
                    pass

            time.sleep(3)
            switch_to_active_window(driver)

            if _is_inbox(driver):
                log.info("Login successful!")
                save_cookies(driver)
                return True

            log.warning(f"Attempt {attempt}: not in inbox. URL={driver.current_url}")
            safe_screenshot(driver, f"login_fail_final_{attempt}.png")

        except (WebDriverException, NoSuchWindowException) as e:
            log.error(f"WebDriver error on attempt {attempt}: {e}")
            if attempt < max_retries:
                time.sleep(5)

    log.error("All login attempts failed.")
    return False


# ===================== COMPOSE CLEANUP =====================

def close_all_compose_windows(driver):
    try:
        for sel in ["div[aria-label='Discard draft']", "button[aria-label='Discard draft']"]:
            for btn in driver.find_elements(By.CSS_SELECTOR, sel):
                try:
                    btn.click(); time.sleep(0.5)
                    for c in driver.find_elements(By.XPATH, "//button[contains(text(),'Discard')]"):
                        c.click(); time.sleep(0.3)
                except Exception:
                    pass
        for sel in ["img[aria-label='Close']", "div[aria-label='Close']"]:
            for btn in driver.find_elements(By.CSS_SELECTOR, sel):
                try:
                    btn.click(); time.sleep(0.3)
                except Exception:
                    pass
        time.sleep(1)
    except Exception as e:
        log.debug(f"close_all_compose_windows: {e}")


# ===================== TO FIELD =====================

def fill_to_field(driver, to_email):
    """Fill Gmail's To field using CDP typing — immune to Chrome 145 restriction."""
    SELECTORS = [
        (By.CSS_SELECTOR, "div[aria-label='To'][name='to']"),
        (By.CSS_SELECTOR, "div[aria-label='To']"),
        (By.XPATH,        "//div[@contenteditable='true' and @aria-label='To']"),
        (By.CSS_SELECTOR, "textarea[name='to']"),
    ]

    type_el = None
    for by, sel in SELECTORS:
        try:
            type_el = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((by, sel))
            )
            log.info(f"To field located: {sel}")
            break
        except Exception:
            type_el = None

    if type_el is None:
        try:
            compose = driver.find_element(By.CSS_SELECTOR, "div[role='dialog'], div.nH.Hd")
            elems = compose.find_elements(By.XPATH, ".//*[@aria-label or @contenteditable or @name]")
            info = [(e.tag_name, e.get_attribute('aria-label'),
                     e.get_attribute('name'), e.get_attribute('contenteditable'))
                    for e in elems[:30]]
            log.warning(f"To field not found. DOM dump: {info}")
        except Exception:
            pass
        raise NoSuchElementException("To field not found")

    cdp_focus_element(driver, type_el)
    cdp_type(driver, to_email, char_delay=(0.04, 0.09))
    time.sleep(0.6)
    cdp_press_key(driver, 'Tab')
    time.sleep(1.0)

    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((
                By.XPATH,
                f"//*[@data-hovercard-id='{to_email}' or contains(@aria-label,'{to_email}')]"
            ))
        )
        log.info(f"Recipient chip confirmed: {to_email}")
    except TimeoutException:
        log.info(f"Chip not confirmed via XPath for {to_email} — proceeding")


# ===================== COMPOSE & SEND =====================

def _wait_for_compose_dialog(driver, timeout=15):
    for sel in ["div[role='dialog']", "div.nH.Hd", "div[aria-label='New Message']"]:
        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, sel))
            )
            log.info(f"Compose dialog: {sel}")
            return True
        except TimeoutException:
            continue
    return False


def compose_and_send(driver, to_email, subject, body, retries=3):
    COMPOSE_CSS = ["div[gh='cm']", "div.T-I.T-I-KE.L3", "div[aria-label='Compose']"]
    SUBJ_CSS    = ["input[name='subjectbox']", "input[aria-label='Subject']"]
    BODY_CSS    = [
        "div[aria-label='Message Body']",
        "div[role='textbox'][aria-label='Message Body']",
        "div.Am.Al.editable",
        "div[role='textbox']",
    ]
    SEND_CSS = [
        "div[aria-label='Send \u202a(Ctrl-Enter)\u202c']",
        "div[aria-label='Send']",
        "div[data-tooltip='Send']",
        "button[aria-label='Send']",
    ]

    for attempt in range(1, retries + 1):
        try:
            switch_to_active_window(driver)
            close_all_compose_windows(driver)
            time.sleep(1.5)

            log.info(f"Composing to {to_email} (attempt {attempt}/{retries})")

            # ── Compose button ──
            composed = False
            for sel in COMPOSE_CSS:
                try:
                    btn = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                    )
                    btn.click(); composed = True
                    log.info(f"Compose clicked: {sel}"); break
                except Exception:
                    continue
            if not composed:
                WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//div[contains(@class,'T-I') and contains(.,'Compose')]")
                    )
                ).click()

            if not _wait_for_compose_dialog(driver):
                log.warning(f"Compose dialog did not appear — attempt {attempt}")
                time.sleep(3); continue

            time.sleep(2)
            switch_to_active_window(driver)

            # ── To (CDP) ──
            fill_to_field(driver, to_email)
            time.sleep(0.5)

            # ── Subject (standard input — send_keys fine) ──
            subj_filled = False
            for sel in SUBJ_CSS:
                try:
                    el = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                    )
                    el.click(); time.sleep(0.3)
                    human_type(el, subject)
                    subj_filled = True
                    log.info(f"Subject filled: {sel}"); break
                except Exception as e:
                    log.debug(f"Subject '{sel}': {e}")
            if not subj_filled:
                raise NoSuchElementException("Subject field not found")

            time.sleep(0.5)

            # ── Body (JS execCommand — fast for long text) ──
            body_el = None
            for sel in BODY_CSS:
                try:
                    body_el = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                    )
                    log.info(f"Body field located: {sel}"); break
                except Exception as e:
                    log.debug(f"Body '{sel}': {e}")
            if body_el is None:
                raise NoSuchElementException("Message body not found")

            cdp_focus_element(driver, body_el)
            js_set_body(driver, body_el, body)
            time.sleep(1)

            # ── Send ──
            sent = False
            for sel in SEND_CSS:
                try:
                    send_btn = WebDriverWait(driver, 8).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                    )
                    send_btn.click(); sent = True
                    log.info(f"Send clicked: {sel}"); break
                except Exception as e:
                    log.debug(f"Send '{sel}': {e}")
            if not sent:
                log.info("Send button not found — CDP Ctrl+Enter")
                driver.execute_cdp_cmd("Input.dispatchKeyEvent", {
                    "type": "keyDown", "key": "Return", "code": "Enter",
                    "windowsVirtualKeyCode": 13, "modifiers": 2,
                })
                driver.execute_cdp_cmd("Input.dispatchKeyEvent", {
                    "type": "keyUp", "key": "Return", "code": "Enter",
                    "windowsVirtualKeyCode": 13, "modifiers": 2,
                })

            time.sleep(3)

            try:
                WebDriverWait(driver, 8).until(
                    EC.presence_of_element_located(
                        (By.XPATH,
                         "//*[contains(text(),'Message sent') or contains(text(),'Sent')]")
                    )
                )
                log.info(f"✓ Confirmed sent → {to_email}")
            except TimeoutException:
                log.info(f"✓ Sent → {to_email} (no snackbar)")

            return True

        except StaleElementReferenceException as e:
            log.warning(f"Stale element attempt {attempt}: {e}")
            try:
                switch_to_active_window(driver)
                close_all_compose_windows(driver)
            except Exception:
                pass
            time.sleep(5)

        except (NoSuchWindowException, WebDriverException) as e:
            log.warning(f"Window/Driver error attempt {attempt}: {e}")
            try:
                switch_to_active_window(driver)
            except Exception:
                log.error("Browser crashed — cannot recover")
                return False
            time.sleep(5)

        except Exception as e:
            log.warning(f"Compose attempt {attempt} failed: {e}")
            try:
                safe_screenshot(driver, f"attempt_{attempt}_{to_email.split('@')[0]}.png")
                switch_to_active_window(driver)
                close_all_compose_windows(driver)
            except Exception:
                pass
            time.sleep(5)

    log.error(f"✗ Failed → {to_email} after {retries} attempts")
    safe_screenshot(driver, f"fail_{to_email.split('@')[0]}.png")
    return False


# ===================== CSV =====================

def read_companies():
    companies = []
    try:
        with open(CSV_FILE, encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)
            for i, row in enumerate(reader, 2):
                if len(row) < 7:
                    continue
                name   = row[2].strip()
                person = row[4].strip() or "Sir/Madam"
                email  = row[6].strip()
                if name and email and '@' in email and '.' in email.split('@')[-1]:
                    companies.append({
                        'company_name':   name,
                        'contact_person': person,
                        'email':          email
                    })
        log.info(f"Loaded {len(companies)} valid companies")
        return companies
    except FileNotFoundError:
        log.error(f"'{CSV_FILE}' not found.")
        return []
    except Exception as e:
        log.error(f"CSV read error: {e}")
        return []


# ===================== MAIN =====================

def main():
    log.info("=" * 58)
    log.info("  Gmail Bulk Sender — Sathaye Career Conclave 2026")
    log.info("=" * 58)

    pw = (EMAIL_PASSWORD if EMAIL_PASSWORD != "your_password_here"
          else getpass.getpass(f"Password for {EMAIL_ADDRESS}: "))

    companies = read_companies()
    if not companies:
        log.error("No companies loaded. Exiting.")
        return

    driver = None
    try:
        driver = setup_driver()

        if not login_to_gmail(driver, EMAIL_ADDRESS, pw):
            log.error("Login failed.")
            return

        switch_to_active_window(driver)
        if not _is_inbox(driver):
            driver.get("https://mail.google.com/mail/u/0/#inbox")
            time.sleep(5)
            switch_to_active_window(driver)

        sent_ok = sent_fail = 0

        for idx, co in enumerate(companies, 1):
            log.info(f"[{idx:>3}/{len(companies)}] {co['company_name']}  →  {co['email']}")

            body = EMAIL_BODY.format(
                company_name=co['company_name']
            )

            if compose_and_send(driver, co['email'], EMAIL_SUBJECT, body):
                sent_ok += 1
            else:
                sent_fail += 1

            if idx < len(companies):
                delay = random.uniform(MIN_DELAY, MAX_DELAY)
                log.info(f"Waiting {delay:.1f}s...")
                time.sleep(delay)

        log.info("=" * 58)
        log.info(f"  Done.  ✓ Sent: {sent_ok}  |  ✗ Failed: {sent_fail}  |  Total: {len(companies)}")
        log.info("=" * 58)

    except KeyboardInterrupt:
        log.info("Interrupted by user.")
    except Exception as e:
        log.critical(f"Fatal error: {e}", exc_info=True)
    finally:
        if driver:
            if not HEADLESS_MODE and DEBUG_MODE:
                input("\nPress Enter to close browser...")
            try:
                driver.quit()
            except Exception:
                pass


if __name__ == "__main__":
    main()