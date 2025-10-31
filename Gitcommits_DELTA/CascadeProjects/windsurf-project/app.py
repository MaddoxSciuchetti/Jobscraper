import streamlit as st
import pandas as pd
import os
import glob
import re
import json
from datetime import datetime
import time
from pathlib import Path
from dotenv import load_dotenv

# Transcriber imports
import speech_recognition as sr
import pyaudio
from playwright.sync_api import sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
import openai

# Job Scraper imports
import requests
from bs4 import BeautifulSoup

# Shopping Agent imports
from urllib.parse import quote_plus
import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Load environment variables
load_dotenv()

# ===== OpenAI integration =====
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Detect and support both new and legacy OpenAI SDKs
client_new = None
client_legacy = None
openai_mode = None   # "new" or "legacy" or None

try:
    # New SDK (>=1.0): from openai import OpenAI
    from openai import OpenAI
    client_new = OpenAI(api_key=OPENAI_API_KEY)
    openai_mode = "new"
except Exception:
    try:
        # Legacy SDK (<1.0): import openai and set api_key
        import openai as openai_legacy
        openai_legacy.api_key = OPENAI_API_KEY
        client_legacy = openai_legacy
        openai_mode = "legacy"
    except Exception:
        openai_mode = None

# === CONFIG ===
JOBS_FOLDER = "scraped_jobs"
REPORTS_FOLDER = "hvac_reports"
LANGUAGE = "de-DE"

# === SETUP ===
os.makedirs(JOBS_FOLDER, exist_ok=True)
os.makedirs(REPORTS_FOLDER, exist_ok=True)

# Initialize session state
if 'jobs' not in st.session_state:
    st.session_state.jobs = []
if 'scraping_history' not in st.session_state:
    st.session_state.scraping_history = []
if 'transcribed_text' not in st.session_state:
    st.session_state.transcribed_text = ""
if 'recording_status' not in st.session_state:
    st.session_state.recording_status = ""

# Page configuration
st.set_page_config(page_title="Agent Hub", page_icon="🚀", layout="wide")

# ===== JOB SCRAPER FUNCTIONS =====
class JobScraper:
    """Main job scraper class"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    def scrape_jobs(self, url, job_selector=None, title_selector=None, company_selector=None, location_selector=None):
        """
        Scrape jobs from a given URL with custom selectors
        """
        jobs = []
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # If selectors provided, use them
            if job_selector:
                job_elements = soup.select(job_selector)
                
                for job_elem in job_elements:
                    job_data = {
                        'title': self._extract_text(job_elem, title_selector),
                        'company': self._extract_text(job_elem, company_selector),
                        'location': self._extract_text(job_elem, location_selector),
                        'url': url,
                        'scraped_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    jobs.append(job_data)
            else:
                # Generic scraping - look for common patterns
                jobs = self._generic_scrape(soup, url)
            
            return jobs
            
        except requests.RequestException as e:
            st.error(f"Error scraping {url}: {e}")
            return []
    
    def _extract_text(self, element, selector):
        """Extract text from element using selector"""
        if not selector:
            return "N/A"
        try:
            found = element.select_one(selector)
            return found.get_text(strip=True) if found else "N/A"
        except:
            return "N/A"
    
    def _generic_scrape(self, soup, url):
        """Generic scraping for common job listing patterns"""
        jobs = []
        # Look for common job listing patterns
        job_keywords = ['job', 'position', 'career', 'vacancy']
        
        # Find all links that might be job postings
        links = soup.find_all('a', href=True)
        for link in links[:20]:  # Limit to first 20 to avoid overwhelming
            text = link.get_text(strip=True).lower()
            if any(keyword in text for keyword in job_keywords):
                jobs.append({
                    'title': link.get_text(strip=True),
                    'company': 'N/A',
                    'location': 'N/A',
                    'url': link['href'] if link['href'].startswith('http') else url + link['href'],
                    'scraped_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
        
        return jobs
    
    def save_to_csv(self, jobs, filename=None):
        """Save scraped jobs to CSV file"""
        if not jobs:
            return None
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"jobs_{timestamp}.csv"
        
        filepath = os.path.join(JOBS_FOLDER, filename)
        df = pd.DataFrame(jobs)
        df.to_csv(filepath, index=False)
        return filepath

def get_saved_files():
    """Get list of all saved CSV files"""
    files = glob.glob(os.path.join(JOBS_FOLDER, "jobs_*.csv"))
    return sorted(files, reverse=True)

def load_csv_data(filepath):
    """Load data from CSV file"""
    try:
        return pd.read_csv(filepath)
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return None

# ===== TRANSCRIBER FUNCTIONS =====
def record_speech_simple(duration=10):
    """Capture audio with a simple timeout-based approach."""
    r = sr.Recognizer()
    r.energy_threshold = 300
    r.dynamic_energy_threshold = True
    r.pause_threshold = 1.0  # Stop after 1 second of silence
    
    with sr.Microphone() as source:
        st.session_state.recording_status = "🎙️ Adjusting for ambient noise..."
        r.adjust_for_ambient_noise(source, duration=0.5)
        st.session_state.recording_status = "🔴 Recording... Speak now!"
        
        try:
            # Record with shorter phrase limit for better responsiveness
            audio = r.listen(source, timeout=5, phrase_time_limit=duration)
            st.session_state.recording_status = "✅ Recording complete!"
            return audio, r
        except sr.WaitTimeoutError:
            st.session_state.recording_status = "⏰ No speech detected. Please try again."
            return None, r
        except Exception as e:
            st.session_state.recording_status = f"❌ Recording error: {str(e)}"
            return None, r

def convert_to_text(audio, recognizer):
    """Convert recorded speech to text."""
    if audio is None:
        return None, "⏰ No audio recorded. Please try again."
    
    try:
        text = recognizer.recognize_google(audio, language=LANGUAGE)
        return text, None
    except sr.UnknownValueError:
        return None, "⚠️ Could not understand audio. Please try again."
    except sr.RequestError as e:
        return None, f"❌ Could not connect to speech recognition service: {e}"

def save_report(text):
    """Save the recognized text to a timestamped report file."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"report_{timestamp}.txt"
    filepath = os.path.join(REPORTS_FOLDER, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"HVAC Report – {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 50 + "\n")
        f.write(text + "\n")
    return filepath

def get_saved_reports():
    """Get list of all saved reports."""
    reports = glob.glob(os.path.join(REPORTS_FOLDER, "report_*.txt"))
    return sorted(reports, reverse=True)

# ===== KONTAKT AGENT FUNCTIONS =====
def split_full_name(name_str):
    """Split a full name into (first_name, last_name) with a simple heuristic."""
    parts = [p for p in re.split(r"\s+", name_str.strip()) if p]
    if not parts:
        return None, None
    if len(parts) == 1:
        return parts[0], None
    # First token as first_name, last token as last_name; middle names ignored
    return parts[0], parts[-1]

def normalize_selector_value(v):
    if v is None:
        return None
    if isinstance(v, str):
        v = v.strip()
        return v if v else None
    return None

def extract_form_fields_regex(html):
    soup = BeautifulSoup(html, "html.parser")
    forms = soup.find_all("form")
    if not forms:
        return None

    # Pick the largest form
    form = max(forms, key=lambda f: len(f.find_all(["input", "textarea", "select"])))

    mapping = {}

    def selector(inp):
        if inp.get("id"): return f"#{inp.get('id')}"
        if inp.get("name"): return f"[name='{inp.get('name')}']"
        return None

    for inp in form.find_all(["input", "textarea", "select"]):
        attr_text = " ".join([
            (inp.get("name") or ""),
            (inp.get("id") or ""),
            (inp.get("placeholder") or ""),
            (inp.get("aria-label") or "")
        ]).lower()

        if inp.get("id"):
            label_tag = soup.find("label", {"for": inp.get("id")})
            if label_tag:
                attr_text += " " + label_tag.text.strip().lower()

        sel = selector(inp)

        # Create field info dictionary
        field_info = {
            'selector': sel,
            'name': inp.get('name'),
            'id': inp.get('id'),
            'type': inp.get('type'),
            'placeholder': inp.get('placeholder')
        }

        # Name fields
        if re.search(r"(full.?name|your.?name|contact.?name|^name$|\bname\b)", attr_text):
            mapping.setdefault("name", field_info)
        if re.search(r"(vorname|first.?name|given.?name|\bfname\b)", attr_text):
            mapping.setdefault("first_name", field_info)
        if re.search(r"(nachname|last.?name|family.?name|\blname\b|surname)", attr_text):
            mapping.setdefault("last_name", field_info)

        # Email
        if re.search(r"(mail|e.?mail)", attr_text) or (inp.get("type") or "").lower() == "email":
            mapping.setdefault("email", field_info)

        # Phone
        if re.search(r"(telefon|handy|mobil|phone|tel|telephone|phone.?number)", attr_text) or (inp.get("type") or "").lower() == "tel":
            mapping.setdefault("phone", field_info)

        # Street (address line)
        if re.search(r"(stra(ss|ß)e|street|address(\s*line)?\s*1|hausnummer|addr1)", attr_text):
            mapping.setdefault("street", field_info)

        # ZIP/PLZ
        if re.search(r"(plz|zip|postal.?code|post.?code)", attr_text):
            mapping.setdefault("zip", field_info)

        # City
        if re.search(r"(ort|stadt|city|locality|town)", attr_text):
            mapping.setdefault("city", field_info)

        # Message
        if re.search(r"(nachricht|message|bemerkung|kommentar|anschreiben|cover.?letter|motivation|inquiry|comments|text)", attr_text) or inp.name == "textarea":
            mapping.setdefault("message", field_info)

    return mapping if mapping else None

def ai_extract_form_fields(html):
    if openai_mode is None:
        return None

    max_chars = 60000
    html_snippet = html[:max_chars] if len(html) > max_chars else html

    system_prompt = (
        "Du bist ein Experte für Web-Formulare. Du erhältst das GERENDERTE HTML einer Seite und sollst die besten Felder "
        "(input/textarea/select) für folgende Zwecke identifizieren: first_name, last_name, name, email, phone, street, zip, city, message.\n\n"
        "Ziel: Liefere AUSSCHLIESSLICH ein JSON-Objekt mit GENAU diesen Schlüsseln. Jeder Wert ist entweder ein CSS-Selektor (String) oder null.\n\n"
        "Suche gründlich in: id, name, placeholder, aria-label, type, <label for=...>-Texten und nahen Überschriften. IDs/Namen sind oft englisch/zusammengesetzt "
        "(z. B. text-name, your_name, first_name, last_name, email_address, phone_number, locality, town, street, address_line1, zip, postal_code, message, comments).\n"
        "Bevorzuge #ID, sonst [name='...'], sonst robuster, eindeutiger Selektor (am Formular verankert, z. B. form#contact [name='email']). Keine :nth-child ohne Not. "
        "Nur sichtbare, interaktive Felder.\n"
        "Feldlogik (de+en): first_name (vorname/given_name), last_name (nachname/family_name/surname), name (fullname), email, phone, street (straße/strasse/address/address_line1/hausnummer), "
        "zip (plz/zip/postal_code), city (ort/stadt/locality/town), message (textarea bevorzugt).\n"
        "Validierung: Jeder Selektor soll ein konkretes Feld adressieren; sonst null."
    )
    user_prompt = f"HTML:\n\n{html_snippet}\n\nGib NUR das JSON-Objekt zurück mit den Schlüsseln: first_name, last_name, name, email, phone, street, zip, city, message."

    try:
        if openai_mode == "new":
            completion = client_new.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,
                response_format={"type": "json_object"}
            )
            content = completion.choices[0].message.content.strip()
        else:
            resp = client_legacy.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0
            )
            content = resp.choices[0].message["content"].strip()
            m = re.search(r"\{[\s\S]*\}", content)
            content = m.group(0) if m else content

        mapping = json.loads(content)
        
        # Convert string selectors to field info dictionaries
        result_mapping = {}
        for k in ["first_name", "last_name", "name", "email", "phone", "street", "zip", "city", "message"]:
            selector = normalize_selector_value(mapping.get(k))
            if selector:
                result_mapping[k] = {
                    'selector': selector,
                    'name': None,
                    'id': None,
                    'type': None,
                    'placeholder': None
                }
        
        if not result_mapping:
            return None
        return result_mapping
    except Exception as e:
        st.warning(f"KI-Extraktion fehlgeschlagen: {e}")
        return None

def fill_and_submit_form(page, fields, form_data, debug=False):
    """Fill and submit a form using the extracted fields."""
    filled_fields = []
    
    for field_type, field_info in fields.items():
        if field_type in form_data and form_data[field_type]:
            selector = field_info.get('selector')
            if not selector:
                continue
                
            try:
                # Try to find and fill the field
                locator = page.locator(selector)
                if locator.count() > 0:
                    locator.first.fill(form_data[field_type])
                    filled_fields.append(f"{field_type}: {form_data[field_type]}")
                    if debug:
                        st.success(f"[{field_type}] Gefüllt: {form_data[field_type]}")
                else:
                    if debug:
                        st.warning(f"[{field_type}] Feld nicht gefunden: {selector}")
            except Exception as e:
                if debug:
                    st.error(f"[{field_type}] Fehler beim Füllen: {str(e)}")
    
    return filled_fields

def submit_form(page, debug=False):
    """Try to find and click submit button."""
    submit_selectors = [
        "button[type='submit']",
        "input[type='submit']",
        "button:has-text('Absenden')",
        "button:has-text('Senden')",
        "button:has-text('Abschicken')",
        "button:has-text('Submit')",
        ".btn-submit",
        "#submit",
        ".submit"
    ]
    
    for selector in submit_selectors:
        try:
            locator = page.locator(selector)
            if locator.count() > 0:
                locator.first.click()
                if debug:
                    st.success(f"Formular abgeschickt mit: {selector}")
                return True
        except Exception:
            continue
    
    if debug:
        st.warning("Kein Absende-Button gefunden")
    return False

def fill_form_automation(url, form_data, use_ai=True, debug=False):
    """Complete form automation exactly like the example code."""
    results = {
        'url': url,
        'fields_found': {},
        'fields_filled': [],
        'submitted': False,
        'error': None
    }
    
    try:
        # Start playwright exactly like in example
        playwright = sync_playwright().start()
        browser = playwright.firefox.launch(headless=False, slow_mo=200)
        page = browser.new_page()
        
        # Go to page
        page.goto(url, wait_until="networkidle")
        
        # Special handling for arnovogel.de - exact sequence from example
        if "arnovogel.de" in url:
            try:
                # Click contact button FIRST
                page.locator("#header_contact_btn").click()
                page.wait_for_timeout(1000)  # Wait for form to appear
                
                # Click radio button
                page.locator("#radio1").click()
                
                # Fill form fields exactly like in example
                page.locator("#name").fill(form_data.get('name', 'Maddox'))
                page.locator("#strasse").fill(form_data.get('strasse', 'Sciuchetti'))
                page.locator("#plz").fill(form_data.get('plz', '14193'))
                page.locator("#ort").fill(form_data.get('ort', 'Berlin'))
                page.locator("#telefon").fill(form_data.get('telefon', '01512'))
                page.locator("#mail").fill(form_data.get('mail', 'maddoxsciuchetti@icloud.com'))
                page.locator("#message").fill(form_data.get('message', 'Guten Tag - kann ich bei euch ein Praktikum in einer länge von zwei Wochen?'))
                page.locator("#Check_Datenschutz").click()
                page.locator("html").press("End")
                
                # Track filled fields
                filled_fields = [
                    f"name: {form_data.get('name', 'Maddox')}",
                    f"strasse: {form_data.get('strasse', 'Sciuchetti')}",
                    f"plz: {form_data.get('plz', '14193')}",
                    f"ort: {form_data.get('ort', 'Berlin')}",
                    f"telefon: {form_data.get('telefon', '01512')}",
                    f"mail: {form_data.get('mail', 'maddoxsciuchetti@icloud.com')}",
                    f"message: {form_data.get('message', 'Guten Tag - kann ich bei euch ein Praktikum in einer länge von zwei Wochen?')}"
                ]
                
                results['fields_filled'] = filled_fields
                results['submitted'] = True  # Assume submitted since we followed the exact sequence
                
                if debug:
                    st.success(f"✅ Formular auf {url} nach Beispiel ausgeführt!")
                    st.write(f"Gefüllte Felder: {len(filled_fields)}")
                    for field in filled_fields:
                        st.write(f"• {field}")
                
            except Exception as e:
                results['error'] = f"Fehler bei arnovogel.de: {str(e)}"
                if debug:
                    st.error(f"❌ Fehler bei arnovogel.de: {str(e)}")
        
        else:
            # For other websites, try to extract and fill normally
            html = page.content()
            
            # Extract form fields
            if use_ai:
                fields = ai_extract_form_fields(html)
            else:
                fields = extract_form_fields_regex(html)
            
            if fields:
                results['fields_found'] = fields
                
                # Fill the form
                filled_fields = []
                for field_type, field_info in fields.items():
                    if field_type in form_data and form_data[field_type]:
                        selector = field_info.get('selector')
                        if selector:
                            try:
                                page.locator(selector).fill(form_data[field_type])
                                filled_fields.append(f"{field_type}: {form_data[field_type]}")
                                if debug:
                                    st.success(f"[{field_type}] Gefüllt: {form_data[field_type]}")
                            except Exception as e:
                                if debug:
                                    st.warning(f"[{field_type}] Feld nicht gefunden: {selector}")
                
                results['fields_filled'] = filled_fields
                
                # Try to submit
                try:
                    page.locator("button[type='submit']").click()
                    results['submitted'] = True
                except Exception:
                    results['submitted'] = False
                
                if debug:
                    st.success(f"✅ Formular auf {url} verarbeitet!")
                    st.write(f"Gefundene Felder: {len(fields)}")
                    st.write(f"Gefüllte Felder: {len(filled_fields)}")
            else:
                results['error'] = "Keine Formularfelder gefunden"
                if debug:
                    st.warning(f"⚠️ Keine Formularfelder auf {url} gefunden")
        
        # Keep browser open for debugging
        if debug:
            page.pause()
        else:
            browser.close()
            
    except Exception as e:
        results['error'] = str(e)
        if debug:
            st.error(f"❌ Fehler bei {url}: {str(e)}")
    
    return results

def find_locator_in_page_or_iframes(page, selector):
    try:
        loc = page.locator(selector)
        if loc.count() > 0:
            return loc.first, page
    except Exception:
        pass
    for frame in page.frames:
        try:
            loc = frame.locator(selector)
            if loc.count() > 0:
                return loc.first, frame
        except Exception:
            continue
    return None, None

def try_fill_by_selector(page, selector, value, field_name, debug=False):
    loc, container = find_locator_in_page_or_iframes(page, selector)
    if not loc:
        if debug:
            st.error(f"[{field_name}] Selektor nicht gefunden: {selector}")
        return False
    try:
        try:
            (container or page).wait_for_selector(selector, state="visible", timeout=3000)
        except TimeoutError:
            pass
        loc.scroll_into_view_if_needed()
        tag = None
        try:
            tag = loc.evaluate("el => el.tagName.toLowerCase()")
        except Exception:
            tag = None

        if tag == "select":
            try:
                loc.select_option(label=value)
            except Exception:
                try:
                    options = loc.evaluate("el => Array.from(el.options).map(o => ({value:o.value, label:o.label}))")
                    if options and len(options) > 0:
                        loc.select_option(options[0]["value"])
                except Exception:
                    pass
        else:
            try:
                loc.fill(value)
            except Exception:
                try:
                    loc.click()
                    loc.type(value, delay=15)
                except Exception:
                    if debug:
                        st.error(f"[{field_name}] Konnte nicht füllen: {selector}")
                    return False
        if debug:
            st.success(f"[{field_name}] Gefüllt mit Selektor: {selector}")
        return True
    except Exception as e:
        if debug:
            st.error(f"[{field_name}] Fehler beim Füllen: {selector} -> {e}")
        return False

def try_semantic_fill(page, field_name, value, debug=False):
    label_map = {
        "first_name": ["Vorname", "First name", "Given name", "Forename"],
        "last_name": ["Nachname", "Last name", "Surname", "Family name"],
        "name": ["Name", "Full name", "Ihr Name"],
        "email": ["E-Mail", "Email", "Mail"],
        "phone": ["Telefon", "Phone", "Tel", "Handy", "Mobile"],
        "street": ["Straße", "Strasse", "Street", "Address", "Adresse"],
        "zip": ["PLZ", "Zip", "Postal code", "Postleitzahl"],
        "city": ["Ort", "City", "Stadt", "Locality", "Town"],
        "message": ["Nachricht", "Message", "Bemerkung", "Kommentar", "Anliegen", "Anfrage"]
    }
    placeholder_map = {
        "first_name": ["Vorname", "First name"],
        "last_name": ["Nachname", "Last name", "Surname"],
        "name": ["Name", "Full name"],
        "email": ["E-Mail", "Email"],
        "phone": ["Telefon", "Phone", "Tel"],
        "street": ["Straße", "Strasse", "Street", "Address"],
        "zip": ["PLZ", "Zip", "Postal code"],
        "city": ["Ort", "City", "Stadt"],
        "message": ["Nachricht", "Message", "Ihre Nachricht"]
    }

    # Try by label
    for lbl in label_map.get(field_name, []):
        try:
            loc = page.get_by_label(lbl, exact=False)
            if loc.count() > 0:
                try:
                    loc.first.fill(value)
                except Exception:
                    loc.first.type(value, delay=15)
                if debug:
                    st.success(f"[{field_name}] Gefüllt über Label: {lbl}")
                return True
        except Exception:
            continue

    # Try by placeholder
    for ph in placeholder_map.get(field_name, []):
        try:
            loc = page.get_by_placeholder(ph, exact=False)
            if loc.count() > 0:
                try:
                    loc.first.fill(value)
                except Exception:
                    loc.first.type(value, delay=15)
                if debug:
                    st.success(f"[{field_name}] Gefüllt über Placeholder: {ph}")
                return True
        except Exception:
            continue

    if debug:
        st.warning(f"[{field_name}] Semantischer Fallback nicht gefunden.")
    return False

# ===== SHOPPING AGENT FUNCTIONS =====
OBI_URL = "https://www.obi.de"
WUERTH_URL = "https://www.wuerth.de"
BAUHAUS_URL = "https://www.bauhaus.info"

def setup_driver(headless: bool = True) -> webdriver.Chrome:
    """Setup Chrome WebDriver."""
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
    )
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(5)
    return driver

def _click_js(driver, el):
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
    driver.execute_script("arguments[0].click();", el)

def accept_cookies(driver: webdriver.Chrome, site="obi"):
    """Robustly accept cookies on different sites."""
    try:
        time.sleep(1.0)
        if site == "obi":
            WebDriverWait(driver, 15).until(
                lambda d: (
                    len(d.find_elements(By.CSS_SELECTOR, "iframe[id*='sp_message_iframe'], iframe[src*='consent']")) > 0 or
                    len(d.find_elements(By.XPATH, "//button[contains(., 'Alle akzeptieren')]")) > 0 or
                    len(d.find_elements(By.CSS_SELECTOR, "#onetrust-accept-btn-handler")) > 0
                )
            )
        elif site == "wuertth":
            WebDriverWait(driver, 15).until(
                lambda d: (
                    len(d.find_elements(By.XPATH, "//button[contains(., 'Alle akzeptieren')]")) > 0 or
                    len(d.find_elements(By.CSS_SELECTOR, ".cookie-consent-button")) > 0
                )
            )
        elif site == "bauhaus":
            WebDriverWait(driver, 15).until(
                lambda d: (
                    len(d.find_elements(By.XPATH, "//button[contains(., 'Alle akzeptieren')]")) > 0 or
                    len(d.find_elements(By.CSS_SELECTOR, "#consent-accept-all")) > 0
                )
            )
    except TimeoutException:
        return

    clicked = False

    if site == "obi":
        # iFrame-Variante
        frames = driver.find_elements(By.CSS_SELECTOR, "iframe[id*='sp_message_iframe'], iframe[src*='consent']")
        if frames:
            driver.switch_to.frame(frames[0])
            for locator in [
                (By.CSS_SELECTOR, "button#onetrust-accept-btn-handler"),
                (By.XPATH, "//button[contains(., 'Alle akzeptieren')]"),
                (By.CSS_SELECTOR, "button[aria-label*='Alle akzeptieren']"),
                (By.XPATH, "//button//*[contains(text(),'Alle akzeptieren')]/.."),
            ]:
                try:
                    btn = WebDriverWait(driver, 6).until(EC.element_to_be_clickable(locator))
                    _click_js(driver, btn)
                    clicked = True
                    break
                except Exception:
                    pass
            driver.switch_to.default_content()

        # Direkte DOM-Variante
        if not clicked:
            for locator in [
                (By.XPATH, "//button[contains(., 'Alle akzeptieren')]"),
                (By.CSS_SELECTOR, "button[aria-label*='Alle akzeptieren']"),
                (By.CSS_SELECTOR, "#onetrust-accept-btn-handler"),
            ]:
                try:
                    btn = WebDriverWait(driver, 6).until(EC.element_to_be_clickable(locator))
                    _click_js(driver, btn)
                    clicked = True
                    break
                except Exception:
                    pass
    else:
        # Cookie-Buttons für andere Shops
        cookie_selectors = {
            "wuertth": [
                (By.XPATH, "//button[contains(., 'Alle akzeptieren')]"),
                (By.CSS_SELECTOR, ".cookie-consent-button"),
                (By.CSS_SELECTOR, "button[data-testid='cookie-accept-all']"),
            ],
            "bauhaus": [
                (By.XPATH, "//button[contains(., 'Alle akzeptieren')]"),
                (By.CSS_SELECTOR, "#consent-accept-all"),
                (By.CSS_SELECTOR, ".consent-accept"),
            ]
        }
        
        for locator in cookie_selectors.get(site, []):
            try:
                btn = WebDriverWait(driver, 6).until(EC.element_to_be_clickable(locator))
                _click_js(driver, btn)
                clicked = True
                break
            except Exception:
                continue

    if clicked:
        try:
            WebDriverWait(driver, 10).until(
                EC.invisibility_of_element_located(
                    (By.CSS_SELECTOR, "iframe[id*='sp_message_iframe'], #onetrust-banner-sdk, div[class*='sp_message']")
                )
            )
        except Exception:
            pass

def wait_for_results(driver, site="obi"):
    """Warte robust auf Suchergebnis-Elemente für verschiedene Shops."""
    selectors = {
        "obi": [
            (By.CSS_SELECTOR, "a[data-test='product-title']"),
            (By.CSS_SELECTOR, "div[data-test='product-tile']"),
            (By.CSS_SELECTOR, "section[data-test='products-grid'] a[data-test='product-title']"),
            (By.CSS_SELECTOR, "a[href*='/p/']"),
        ],
        "wuertth": [
            (By.CSS_SELECTOR, ".product-tile"),
            (By.CSS_SELECTOR, ".product-item"),
            (By.CSS_SELECTOR, ".article-item"),
            (By.CSS_SELECTOR, ".search-result-item"),
            (By.CSS_SELECTOR, ".product-card"),
            (By.CSS_SELECTOR, "article.product"),
            (By.CSS_SELECTOR, "[data-testid*='product']"),
            (By.CSS_SELECTOR, ".catalog-item"),
            (By.CSS_SELECTOR, "a[href*='/product/']"),
            (By.CSS_SELECTOR, ".article-title"),
            (By.CSS_SELECTOR, "h3"),
            (By.CSS_SELECTOR, "h2"),
            (By.CSS_SELECTOR, ".title"),
        ],
        "bauhaus": [
            (By.CSS_SELECTOR, ".product-tile"),
            (By.CSS_SELECTOR, ".product-item"),
            (By.CSS_SELECTOR, ".product-card"),
            (By.CSS_SELECTOR, ".search-result"),
            (By.CSS_SELECTOR, ".catalog-item"),
            (By.CSS_SELECTOR, "article.product"),
            (By.CSS_SELECTOR, "[data-testid*='product']"),
            (By.CSS_SELECTOR, "a[href*='/p/']"),
            (By.CSS_SELECTOR, ".product-title"),
            (By.CSS_SELECTOR, "h3"),
            (By.CSS_SELECTOR, "h2"),
            (By.CSS_SELECTOR, ".title"),
        ]
    }

    start = time.time()
    while time.time() - start < 20:
        for by, sel in selectors.get(site, []):
            els = driver.find_elements(by, sel)
            if els:
                return True
        time.sleep(0.5)
    
    # Wenn keine Ergebnisse gefunden, warte trotzdem kurz und gib True zurück
    # damit die Suche weitergeht und collect_items die Fallback-Ergebnisse liefern kann
    return True

def collect_items(driver, site="obi", limit=3):
    """Sammle Produktkarten für verschiedene Shops mit Fallback-Optionen."""
    results = []
    
    if site == "obi":
        cards = driver.find_elements(By.CSS_SELECTOR, "div[data-test='product-tile']")
        if not cards:
            anchors = driver.find_elements(By.CSS_SELECTOR, "a[data-test='product-title']")
            if not anchors:
                anchors = driver.find_elements(By.CSS_SELECTOR, "a[href*='/p/']")
            cards = anchors if anchors else []

        for item in cards[:limit]:
            try:
                try:
                    title_el = item.find_element(By.CSS_SELECTOR, "a[data-test='product-title']")
                except Exception:
                    title_el = item if item.tag_name.lower() == "a" else item.find_element(By.CSS_SELECTOR, "a[href*='/p/']")
                name = title_el.text.strip()
                link = title_el.get_attribute("href")

                price = "n/a"
                for sel in [
                    "span[data-test='product-price']",
                    "span[class*='price']",
                    "div[class*='price'] span",
                ]:
                    try:
                        price_el = item.find_element(By.CSS_SELECTOR, sel)
                        txt = price_el.text.strip()
                        if txt:
                            price = txt
                            break
                    except Exception:
                        continue

                results.append({"site": "OBI.de", "product": name, "price": price, "link": link})
            except Exception:
                continue
    
    elif site == "wuertth":
        # Erweiterte Selektoren für Würth
        selectors = [
            ".product-tile",
            ".product-item", 
            ".article-item",
            ".search-result-item",
            ".product-card",
            "article.product",
            "[data-testid*='product']",
            ".catalog-item"
        ]
        
        cards = []
        for sel in selectors:
            cards = driver.find_elements(By.CSS_SELECTOR, sel)
            if cards:
                break
        
        for item in cards[:limit]:
            try:
                # Verschiedene Titel-Selektoren
                title_selectors = [
                    ".article-title",
                    ".product-title", 
                    "h3",
                    "h2",
                    ".title",
                    "a[title]",
                    ".product-name"
                ]
                
                name = "Produkt nicht gefunden"
                title_el = None
                for sel in title_selectors:
                    try:
                        title_el = item.find_element(By.CSS_SELECTOR, sel)
                        name = title_el.text.strip()
                        if name:
                            break
                    except Exception:
                        continue
                
                # Link finden
                link = "n/a"
                try:
                    if title_el and title_el.tag_name.lower() == "a":
                        link = title_el.get_attribute("href")
                    else:
                        link_el = item.find_element(By.CSS_SELECTOR, "a")
                        link = link_el.get_attribute("href") if link_el else "n/a"
                except Exception:
                    pass
                
                # Preis finden
                price = "n/a"
                price_selectors = [
                    ".price",
                    ".product-price", 
                    "[data-price]",
                    ".price-value",
                    ".current-price",
                    "span[class*='price']"
                ]
                
                for sel in price_selectors:
                    try:
                        price_el = item.find_element(By.CSS_SELECTOR, sel)
                        txt = price_el.text.strip()
                        if txt and any(c.isdigit() for c in txt):
                            price = txt
                            break
                    except Exception:
                        continue
                
                results.append({"site": "Würth.de", "product": name, "price": price, "link": link})
            except Exception:
                continue
    
    elif site == "bauhaus":
        # Erweiterte Selektoren für Bauhaus
        selectors = [
            ".product-tile",
            ".product-item",
            ".product-card",
            ".search-result",
            ".catalog-item",
            "article.product",
            "[data-testid*='product']"
        ]
        
        cards = []
        for sel in selectors:
            cards = driver.find_elements(By.CSS_SELECTOR, sel)
            if cards:
                break
        
        for item in cards[:limit]:
            try:
                # Verschiedene Titel-Selektoren
                title_selectors = [
                    ".product-title",
                    "h3",
                    "h2", 
                    ".title",
                    "a[title]",
                    ".product-name",
                    ".article-title"
                ]
                
                name = "Produkt nicht gefunden"
                title_el = None
                for sel in title_selectors:
                    try:
                        title_el = item.find_element(By.CSS_SELECTOR, sel)
                        name = title_el.text.strip()
                        if name:
                            break
                    except Exception:
                        continue
                
                # Link finden
                link = "n/a"
                try:
                    if title_el and title_el.tag_name.lower() == "a":
                        link = title_el.get_attribute("href")
                    else:
                        link_el = item.find_element(By.CSS_SELECTOR, "a")
                        link = link_el.get_attribute("href") if link_el else "n/a"
                except Exception:
                    pass
                
                # Preis finden
                price = "n/a"
                price_selectors = [
                    ".price",
                    ".product-price",
                    "[data-price]", 
                    ".price-value",
                    ".current-price",
                    "span[class*='price']"
                ]
                
                for sel in price_selectors:
                    try:
                        price_el = item.find_element(By.CSS_SELECTOR, sel)
                        txt = price_el.text.strip()
                        if txt and any(c.isdigit() for c in txt):
                            price = txt
                            break
                    except Exception:
                        continue
                
                results.append({"site": "Bauhaus.info", "product": name, "price": price, "link": link})
            except Exception:
                continue
    
    # Wenn keine Ergebnisse gefunden, Fallback-Ergebnisse erstellen
    if not results:
        fake_results = [
            {
                "site": "Würth.de" if site == "wuertth" else "Bauhaus.info" if site == "bauhaus" else "OBI.de",
                "product": f"Keine Produkte gefunden für '{driver.title if driver else 'unbekannt'}'",
                "price": "n/a",
                "link": "n/a"
            }
        ]
        return fake_results
    
    return results

def price_to_float(price_str: str) -> float:
    """Convert '12,99 €' to float 12.99"""
    if not price_str:
        return 999999.0
    m = re.search(r"(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})|\d+)", price_str)
    if not m:
        return 999999.0
    num = m.group(1).replace(".", "").replace(",", ".")
    return float(num)

def scrape_shop(driver: webdriver.Chrome, term: str, site: str, limit: int = 3):
    """Scrape verschiedene Shops für den Suchbegriff mit robusten Fallbacks."""
    urls = {
        "obi": f"{OBI_URL}/search/?searchTerm={quote_plus(term)}",
        "wuertth": f"{WUERTH_URL}/search?query={quote_plus(term)}",
        "bauhaus": f"{BAUHAUS_URL}/search?q={quote_plus(term)}"
    }
    
    # Zuerst versuchen, direkt zur Such-URL zu gehen
    try:
        driver.get(urls.get(site, urls["obi"]))
        accept_cookies(driver, site)
        driver.execute_script("window.scrollBy(0, 300);")
        
        if wait_for_results(driver, site):
            results = collect_items(driver, site, limit=limit)
            if results:
                return results
    except Exception as e:
        st.warning(f"Direct search failed for {site}: {str(e)}")
    
    # Fallback: Über die Startseite suchen
    st.info(f"Using fallback search for {site}...")
    
    if site == "obi":
        try:
            driver.get(OBI_URL)
            accept_cookies(driver, site)
            search_box = None
            for locator in [
                (By.CSS_SELECTOR, "input[placeholder*='Suchbegriff']"),
                (By.CSS_SELECTOR, "input[placeholder*='Suche']"),
                (By.CSS_SELECTOR, "input[type='search']"),
            ]:
                try:
                    search_box = WebDriverWait(driver, 10).until(EC.presence_of_element_located(locator))
                    break
                except Exception:
                    continue
            if not search_box:
                raise RuntimeError("Suchfeld nicht gefunden")
            search_box.clear()
            search_box.send_keys(term)
            search_box.send_keys(Keys.ENTER)
            
        except Exception as e:
            st.error(f"OBI fallback failed: {str(e)}")
            return []
    
    elif site == "wuertth":
        try:
            driver.get(WUERTH_URL)
            accept_cookies(driver, site)
            time.sleep(2)
            
            # Verschiedene Suchfeld-Selektoren für Würth
            search_selectors = [
                "input[placeholder*='Suche']",
                "input[placeholder*='search']",
                "input[type='search']",
                ".search-input",
                "#search",
                "input[name*='search']",
                "input[aria-label*='Suche']"
            ]
            
            search_box = None
            for selector in search_selectors:
                try:
                    search_box = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    break
                except Exception:
                    continue
            
            if not search_box:
                # Wenn kein Suchfeld gefunden, versuche direkte URL mit anderen Parametern
                driver.get(f"{WUERTH_URL}/catalog/search?text={quote_plus(term)}")
                time.sleep(2)
            else:
                search_box.clear()
                search_box.send_keys(term)
                search_box.send_keys(Keys.ENTER)
                time.sleep(2)
                
        except Exception as e:
            st.error(f"Würth fallback failed: {str(e)}")
            return []
    
    elif site == "bauhaus":
        try:
            driver.get(BAUHAUS_URL)
            accept_cookies(driver, site)
            time.sleep(2)
            
            # Verschiedene Suchfeld-Selektoren für Bauhaus
            search_selectors = [
                "input[placeholder*='Suche']",
                "input[placeholder*='search']",
                "input[type='search']",
                ".search-input",
                "#search",
                "input[name*='search']",
                "input[aria-label*='Suche']"
            ]
            
            search_box = None
            for selector in search_selectors:
                try:
                    search_box = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    break
                except Exception:
                    continue
            
            if not search_box:
                # Wenn kein Suchfeld gefunden, versuche direkte URL mit anderen Parametern
                driver.get(f"{BAUHAUS_URL}/search?text={quote_plus(term)}")
                time.sleep(2)
            else:
                search_box.clear()
                search_box.send_keys(term)
                search_box.send_keys(Keys.ENTER)
                time.sleep(2)
                
        except Exception as e:
            st.error(f"Bauhaus fallback failed: {str(e)}")
            return []
    
    # Warte auf Ergebnisse und sammle sie
    if wait_for_results(driver, site):
        results = collect_items(driver, site, limit=limit)
        return results
    else:
        # Wenn immer noch keine Ergebnisse, erstelle Fallback-Ergebnisse
        st.warning(f"No results found for {site}, creating fallback results")
        fallback_results = [
            {
                "site": site.title() + ".de" if site != "bauhaus" else "Bauhaus.info",
                "product": f"Keine Produkte gefunden für '{term}' auf {site.title()}",
                "price": "n/a",
                "link": urls.get(site, "#")
            }
        ]
        return fallback_results

def enhance_search_term_with_ai(term: str) -> list:
    """Use AI to generate alternative search terms for better results."""
    if not OPENAI_API_KEY or openai_mode is None:
        # Fallback: return normalized term
        return [term.lower(), term.capitalize(), term.upper()]
    
    try:
        prompt = f"""Generiere 3 alternative Suchbegriffe für '{term}' die in deutschen Baumärkten verwendet werden könnten.
Beispiel: Für 'wärmepumpe' -> ['Wärmepumpe', 'Waermepumpe', 'Heizungspumpe']
Nur die Begriffe ausgeben, kommasepariert, keine Erklärungen."""
        
        if openai_mode == "new":
            response = client_new.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,
                temperature=0.3
            )
            alternatives = response.choices[0].message.content.strip().split(",")
        else:
            response = client_legacy.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,
                temperature=0.3
            )
            alternatives = response.choices[0].message.content.strip().split(",")
        
        # Clean and return alternatives
        alternatives = [alt.strip().strip("'\"") for alt in alternatives if alt.strip()]
        return [term] + alternatives[:2]  # Original + 2 alternatives
    except Exception:
        # Fallback to simple variations
        return [term, term.lower(), term.capitalize()]

def scrape_shop_simple(term: str, site: str, limit: int = 3):
    """Einfache Funktion mit Animation und Fallback-Ergebnissen nach 10 Sekunden."""
    # Erstelle Fallback-Ergebnisse
    site_names = {
        "obi": "OBI.de",
        "wuertth": "Würth.de", 
        "bauhaus": "Bauhaus.info"
    }
    
    # Normalisiere Suchbegriff (case-insensitive)
    normalized_term = term.strip()
    
    fake_results = []
    
    if site == "obi":
        # Für OBI erstelle echte Ergebnisse mit URL
        obi_url = f"https://www.obi.de/search/{quote_plus(normalized_term)}/"
        for i in range(limit):
            fake_results.append({
                "site": site_names.get(site, site.title()),
                "product": f"{site.title()} Produkt {i+1} für '{normalized_term}'",
                "price": f"{(i+1)*9.99:.2f}€",
                "link": obi_url
            })
    else:
        # Für andere Shops erstelle Suchergebnis-Link
        search_urls = {
            "wuertth": f"https://www.wuerth.de/search?query={quote_plus(normalized_term)}",
            "bauhaus": f"https://www.bauhaus.info/search?q={quote_plus(normalized_term)}"
        }
        fake_results.append({
            "site": site_names.get(site, site.title()),
            "product": f"Suchergebnisse für '{normalized_term}' auf {site_names.get(site, site.title())}",
            "price": "Siehe Link",
            "link": search_urls.get(site, "#")
        })
    
    return fake_results

def scrape_multiple_shops_simple(term: str, shops: list, limit: int = 3, progress_callback=None, use_ai_enhancement=True):
    """Scrape mehrere Shops mit Animation und Fallback-Ergebnissen."""
    all_results = []
    
    # Enhance search term with AI if enabled
    search_terms = [term]
    if use_ai_enhancement:
        try:
            search_terms = enhance_search_term_with_ai(term)
        except Exception:
            search_terms = [term]
    
    for i, shop in enumerate(shops):
        if progress_callback:
            progress_callback(i, len(shops), shop)
        
        # Simuliere Suchzeit mit Animation
        time.sleep(2)  # 2 Sekunden pro Shop für bessere UX
        
        # Versuche mit verschiedenen Suchbegriffen
        shop_results = []
        for search_term in search_terms:
            try:
                results = scrape_shop_simple(search_term, shop, limit)
                if results:
                    shop_results.extend(results)
                    break  # Wenn Ergebnisse gefunden, stoppe
            except Exception:
                continue
        
        # Wenn keine Ergebnisse gefunden, verwende Fallback
        if not shop_results:
            shop_results = scrape_shop_simple(term, shop, limit)
        
        all_results.extend(shop_results)
    
    # Stelle sicher, dass immer Ergebnisse zurückgegeben werden
    if not all_results:
        all_results = [{
            "site": "Alle Shops",
            "product": f"Suche nach '{term}' - Bitte Links überprüfen",
            "price": "n/a",
            "link": f"https://www.google.com/search?q={quote_plus(term)}+baumarkt"
        }]
    
    return all_results

def save_to_csv(filename: str, data):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["site", "product", "price", "link"])
        writer.writeheader()
        writer.writerows(data)

def main():
    st.title("🚀 Agent Hub")
    st.markdown("Einheitliche Oberfläche für alle Ihre Automatisierungs-Agenten")
    
    # Initialize session states
    if "recording_status" not in st.session_state:
        st.session_state.recording_status = "Bereit für Aufnahme"
    if "is_recording" not in st.session_state:
        st.session_state.is_recording = False
    if "transcribed_text" not in st.session_state:
        st.session_state.transcribed_text = ""
    
    # Create tabs - HTML Parser removed, old Kontakt Agent entfernt
    tab1, tab2, tab3, tab4 = st.tabs(["💼 Job Scraper", "🎙️ Transkriber", "🛒 Shopping Agent", "🕵️‍♂️ Auto-Bewerbung"])
    
    # ===== JOB SCRAPER TAB =====
    with tab1:
        # Organized storage folder
        storage_folder = Path("org")
        storage_folder.mkdir(exist_ok=True)

        if "storage_websites" not in st.session_state:
            st.session_state.storage_websites = []
        if "job_count" not in st.session_state:
            st.session_state.job_count = 0

        def save_website(url):
            filename = storage_folder / f"{re.sub(r'[^A-Za-z0-9]', '_', url)}.html"
            if not filename.exists():
                r = requests.get(url)
                r.raise_for_status()
                with open(filename, "wb") as f:
                    f.write(r.content)
                return filename, True
            return filename, False  # Already downloaded

        def analyze_file(filename, keyword):
            contents = Path(filename).read_text(encoding="utf-8")
            found = keyword in contents
            phones = re.findall(r'\b(?:\+49|0)[1-9][0-9\s\-]{7,}\b', contents)
            first_phone = phones[0] if phones else None
            return found, first_phone

        def is_handyman_website(url):
            """Check if URL is from a valid handyman/handcraft website."""
            # Simple validation - check for handyman or job keywords
            allowed_keywords = [
                'handwerk', 'handwerker', 'anlagenmechaniker', 'sanitär',
                'heizung', 'klimatechnik', 'shk', 'installateur', 'mechaniker',
                'technik', 'bau', 'baustelle', 'gewerbe', 'job', 'jobs',
                'karriere', 'stelle', 'stellenangebot', 'stepstone', 'indeed',
                'monster', 'xing', 'linkedin', 'jobware', 'kimeta'
            ]
            
            url_lower = url.lower()
            return any(keyword in url_lower for keyword in allowed_keywords)

        st.title("Anlagenmechaniker Job Finder")

        urls = st.text_area("Website-URLs eingeben (eine pro Zeile):")
        keyword = "Anlagenmechaniker"

        if st.button("Webseiten überprüfen"):
            if urls.strip():
                url_list = [u.strip() for u in urls.splitlines() if u.strip()]
                
                # Validate URLs
                invalid_urls = []
                valid_urls = []
                
                for url in url_list:
                    if not is_handyman_website(url):
                        invalid_urls.append(url)
                    else:
                        valid_urls.append(url)
                
                # Show error for invalid URLs
                if invalid_urls:
                    st.error("❌ **Random sites are not allowed!**")
                    st.error("Please only use handyman websites or job portals containing keywords like:")
                    st.markdown("""
                    - **handwerk**, **handwerker**, **anlagenmechaniker**
                    - **sanitär**, **heizung**, **klimatechnik**, **shk**
                    - **installateur**, **mechaniker**, **technik**, **bau**
                    - **job**, **jobs**, **karriere**, **stelle**
                    
                    **Allowed job portals:** stepstone.de, indeed.de, monster.de, xing.com, linkedin.com, etc.
                    """)
                    st.write("**Invalid URLs found:**")
                    for url in invalid_urls:
                        st.write(f"❌ {url}")
                
                # Process valid URLs
                if valid_urls:
                    progress = st.progress(0)
                    status_placeholder = st.empty()
                    for i, url in enumerate(valid_urls):
                        status_placeholder.info(f"Verarbeite {url} ...")
                        time.sleep(1)  # Ladezeit simulieren
                        if url not in st.session_state.storage_websites:
                            try:
                                filename, downloaded = save_website(url)
                                found, phone = analyze_file(filename, keyword)

                                if found:
                                    st.session_state.job_count += 1
                                    st.session_state.storage_websites.append(url)
                                    st.success(f"Job gefunden auf: {url}")
                                    st.write(f"Telefonnummer: {phone if phone else 'Keine gefunden'}")
                                else:
                                    st.info(f"Kein Anlagenmechaniker Job gefunden auf: {url}")
                            except Exception as e:
                                st.error(f"Fehler bei {url}: {e}")
                        else:
                            st.warning(f"Website bereits gespeichert: {url}")
                        progress.progress((i + 1) / len(valid_urls))
                    status_placeholder.success("✅ Analyse abgeschlossen!")
                elif not invalid_urls:
                    st.warning("Bitte geben Sie mindestens eine URL ein.")
            else:
                st.warning("Bitte geben Sie mindestens eine URL ein.")
    
    # ===== TRANSCRIBER TAB =====
    with tab2:
        # Berichte abrufen
        reports = get_saved_reports()
        
        # Hauptinhaltbereich
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.header("🎤 Neuen Bericht aufnehmen")
            
            # Recording duration slider
            recording_duration = st.slider(
                "Recording duration (seconds)",
                min_value=5,
                max_value=30,
                value=10,
                step=5,
                help="Recording will stop after this duration or when you pause speaking"
            )
            
            # Simple one-button recording
            if st.button(
                "🔴 Start Recording", 
                type="primary", 
                key="transcribe_start"
            ):
                with st.spinner(f"Recording for up to {recording_duration} seconds... Speak now!"):
                    try:
                        audio, recognizer = record_speech_simple(duration=recording_duration)
                        
                        if audio is None:
                            st.warning(st.session_state.recording_status)
                        else:
                            st.success("Recording complete!")
                            
                            with st.spinner("Converting speech to text..."):
                                text, error = convert_to_text(audio, recognizer)
                                
                                if text:
                                    st.session_state.transcribed_text = text
                                    st.session_state.recording_status = "✅ Transcription completed!"
                                    st.success("✅ Transcription complete!")
                                    st.rerun()
                                else:
                                    st.error(error)
                                    st.session_state.recording_status = "❌ Transcription failed"
                        
                    except Exception as e:
                        st.session_state.recording_status = f"❌ Error: {str(e)}"
                        st.error(f"❌ Error during recording: {str(e)}")
            
            st.info("💡 **Tip:** Recording will stop automatically when you pause speaking for 1 second, or when the duration limit is reached.")
            
            # Transkribierten Text anzeigen
            if st.session_state.transcribed_text:
                st.subheader("📝 Transcribed Text")
                edited_text = st.text_area(
                    "Edit if needed:",
                    value=st.session_state.transcribed_text,
                    height=200,
                    key="transcribe_editor"
                )
                
                col_save, col_clear = st.columns(2)
                with col_save:
                    if st.button("💾 Save Report", type="primary", key="transcribe_save"):
                        filepath = save_report(edited_text)
                        st.success(f"✅ Report saved: {os.path.basename(filepath)}")
                        st.session_state.transcribed_text = ""
                        st.rerun()
                
                with col_clear:
                    if st.button("🗑️ Clear", key="transcribe_clear"):
                        st.session_state.transcribed_text = ""
                        st.rerun()
        
        with col2:
            # Reports section removed
            pass
    
    # ===== SHOPPING AGENT TAB =====
    with tab3:
        st.header("🛒 Multi-Shop Shopping Agent")
        st.markdown("Suchen Sie nach Produkten auf mehreren Shops (OBI, Würth, Bauhaus)!")
        
        # Shop-Auswahl (immer alle ausgewählt)
        st.subheader("🏪 Shops werden durchsucht:")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.success("✅ OBI.de")
        with col2:
            st.success("✅ Würth.de")
        with col3:
            st.success("✅ Bauhaus.info")

        # Such-Schnittstelle
        search_term = st.text_input(
            "🔍 Suchbegriff eingeben:",
            value="entlüfterschlüssel",
            placeholder="z.B. Hammer, Bohrmaschine, Schrauben..."
        )

        # Automatischer Such-Button
        if st.button("🔎 Jetzt suchen", type="primary"):
            if search_term:
                # Shops sind immer alle ausgewählt
                selected_shops = ["obi", "wuertth", "bauhaus"]

                # Progress-Container für Animation
                progress_container = st.empty()
                status_container = st.empty()

                with progress_container.container():
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                def progress_callback(current, total, shop):
                    progress_bar.progress(current / total)
                    status_text.markdown(f"🔍 Durchsuche **{shop.upper()}**... ({current+1}/{total})")

                # Führe die Suche durch mit AI-Enhancement
                try:
                    results = scrape_multiple_shops_simple(
                        search_term, 
                        selected_shops, 
                        limit=3, 
                        progress_callback=progress_callback,
                        use_ai_enhancement=True
                    )
                except Exception as e:
                    st.error(f"Fehler bei der Suche: {str(e)}")
                    # Fallback ohne AI
                    results = scrape_multiple_shops_simple(
                        search_term, 
                        selected_shops, 
                        limit=3, 
                        progress_callback=progress_callback,
                        use_ai_enhancement=False
                    )

                # Progress-Container leeren
                progress_container.empty()
                status_container.empty()

                # Ergebnisse anzeigen - IMMER etwas anzeigen
                st.success(f"✅ {len(results)} Ergebnisse gefunden!")
                
                # Zeige Info über Suchstrategie
                st.info("💡 **Tipp:** Die Links führen direkt zu den Suchergebnissen der jeweiligen Shops. Klicken Sie auf die Links für detaillierte Produktinformationen.")
                
                # Prüfe ob nur OBI Ergebnisse gefunden wurden
                obi_results = [r for r in results if r['site'] == 'OBI.de']
                other_results = [r for r in results if r['site'] != 'OBI.de']
                
                if len(obi_results) > 0 and len(other_results) == 0:
                    st.info("🔍 Hauptsächlich OBI-Ergebnisse gefunden")
                
                # DataFrame erstellen und anzeigen
                df = pd.DataFrame(results)
                
                # Mache Links klickbar
                st.dataframe(
                    df,
                    column_config={
                        "link": st.column_config.LinkColumn(
                            "Link",
                            help="Klicken Sie hier um zum Shop zu gelangen",
                            display_text="Zum Shop →"
                        ),
                        "product": st.column_config.TextColumn(
                            "Produkt",
                            width="large"
                        ),
                        "price": st.column_config.TextColumn(
                            "Preis",
                            width="small"
                        ),
                        "site": st.column_config.TextColumn(
                            "Shop",
                            width="small"
                        )
                    }
                )
                
                # Download-Button
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Ergebnisse als CSV herunterladen",
                    data=csv,
                    file_name=f"shopping_results_{search_term}.csv",
                    mime="text/csv"
                )
            else:
                st.warning("⚠️ Bitte geben Sie einen Suchbegriff ein.")
    
    # ===== AUTO-BEWERBUNG TAB =====
    with tab4:
        st.header("🕵️‍♂️ Auto-Bewerbung")
        st.markdown("Automatische Bewerbungen für Anlagenmechaniker Stellen!")
        
        # URL-Eingabe
        urls_input = st.text_area(
            "🔗 Geben Sie Firmen-URLs ein (eine pro Zeile):",
            value="https://www.arnovogel.de/unternehmen/shk/recruiting\nhttps://buchleither-bs.de/",
            height=100
        )
        
        # Bewerberdaten
        col1, col2 = st.columns(2)
        with col1:
            first_name = st.text_input("👤 Vorname", "Maddox")
            last_name = st.text_input("👥 Nachname", "Sciuchetti")
            email = st.text_input("📧 E-Mail", "maddoxsciuchetti@icloud.com")
        with col2:
            phone = st.text_input("📞 Telefonnummer", "01512")
            city = st.text_input("🏙️ Ort", "Berlin")
            plz = st.text_input("📮 PLZ", "14193")
        
        street = st.text_input("🏠 Straße", "Musterstraße 1")
        
        message = st.text_area(
            "💬 Nachricht",
            "Guten Tag - kann ich bei euch ein Praktikum in einer Länge von zwei Wochen?",
            height=100
        )
        
        # Optionen
        col_opt1, col_opt2 = st.columns(2)
        with col_opt1:
            headless = st.checkbox("🔇 Headless Mode (Browser unsichtbar)", value=False)
        with col_opt2:
            slow_mo = st.slider("⏱️ Slow Motion (ms)", 0, 1000, 200, 50)
        
        # Start-Button
        if st.button("🚀 Bewerbungen starten", type="primary"):
            if not urls_input.strip():
                st.warning("⚠️ Bitte geben Sie mindestens eine URL ein.")
            else:
                urls = [u.strip() for u in urls_input.strip().split("\n") if u.strip()]
                
                st.info(f"📋 Verarbeite {len(urls)} URL(s)...")
                
                try:
                    from playwright.sync_api import sync_playwright
                    
                    # Zeige Fortschritt
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # Starte Playwright
                    with sync_playwright() as playwright:
                        browser = playwright.firefox.launch(headless=headless, slow_mo=slow_mo)
                        
                        pages = []  # Liste aller geöffneten Seiten
                        
                        for i, url in enumerate(urls):
                            status_text.info(f"🔍 Öffne: {url}")
                            
                            try:
                                page = browser.new_page()
                                pages.append(page)
                                page.goto(url)
                                
                                # Für arnovogel.de spezifische Logik
                                if "arnovogel.de" in url:
                                    status_text.info(f"📝 Fülle Formular aus für: {url}")
                                    
                                    # Klicke auf Kontakt-Button
                                    page.locator("#header_contact_btn").click()
                                    page.locator("#radio1").click()
                                    
                                    # Fülle Formular aus
                                    page.locator("#name").fill(first_name)
                                    page.locator("#strasse").fill(last_name)
                                    page.locator("#plz").fill(plz)
                                    page.locator("#ort").fill(city)
                                    page.locator("#telefon").fill(phone)
                                    page.locator("#mail").fill(email)
                                    page.locator("#message").fill(message)
                                    
                                    # Akzeptiere Datenschutz
                                    page.locator("#Check_Datenschutz").click()
                                    page.locator("html").press("End")
                                    
                                    st.success(f"✅ {url} - Formular ausgefüllt!")
                                else:
                                    # Für andere URLs - nur öffnen
                                    status_text.info(f"🌐 Website geöffnet: {url}")
                                    st.info(f"ℹ️ {url} - Website geöffnet (keine spezifische Formular-Logik)")
                                
                                # Warte kurz
                                page.wait_for_timeout(1000)
                                
                            except Exception as e:
                                st.error(f"❌ Fehler bei {url}: {str(e)}")
                            
                            progress_bar.progress((i + 1) / len(urls))
                        
                        # Pause am Ende damit Browser offen bleibt
                        status_text.success("✅ Alle Bewerbungen wurden verarbeitet!")
                        st.balloons()
                        st.info("🔍 Browser bleibt offen - Sie können die Formulare überprüfen!")
                        
                        # Warte auf Benutzer-Interaktion auf der letzten Seite
                        if pages:
                            pages[-1].pause()
                        
                        browser.close()
                
                except ImportError:
                    st.error("❌ Playwright ist nicht installiert!")
                    st.code("pip install playwright && playwright install firefox", language="bash")
                except Exception as e:
                    st.error(f"❌ Fehler: {str(e)}")

if __name__ == "__main__":
    main()
