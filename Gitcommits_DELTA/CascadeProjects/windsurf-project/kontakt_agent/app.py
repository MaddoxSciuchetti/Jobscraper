import streamlit as st
from playwright.sync_api import sync_playwright, TimeoutError
from bs4 import BeautifulSoup
import requests, json, re, os
from dotenv import load_dotenv

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

st.set_page_config(page_title="Auto Bewerbungs Scanner", layout="centered")

st.title("🕵️‍♂️ Auto-Bewerbungs Scanner (Vorschau)")
st.write("Dieses Tool durchsucht Webseiten automatisch nach Kontaktformularen, erkennt deren Felder und zeigt an, was ausgefüllt werden könnte — ohne das Formular abzuschicken.")

# --- Input section
urls_input = st.text_area(
    "🔗 Geben Sie mehrere URLs ein (jeweils eine pro Zeile):",
    placeholder="https://www.arnovogel.de/unternehmen/shk/recruiting\nhttps://buchleither-bs.de/"
)

col1, col2 = st.columns(2)
with col1:
    full_name = st.text_input("👤 Vollständiger Name", "Maddox Sciuchetti")
    email = st.text_input("📧 E-Mail", "maddoxsciuchetti@icloud.com")
with col2:
    phone = st.text_input("📞 Telefonnummer", "01512")
    city = st.text_input("🏙️ Ort", "Berlin")

street = st.text_input("🏠 Straße, Hausnummer", "Musterstraße 1")
zip_code = st.text_input("📮 PLZ", "10115")

message = st.text_area(
    "💬 Nachricht",
    "Guten Tag – kann ich bei euch ein Praktikum in einer Länge von zwei Wochen?"
)

use_ai = st.checkbox("🤖 KI zur Felderkennung verwenden", value=True)
show_debug = st.checkbox("🛠️ Debug-Ausgaben anzeigen", value=True)
run = st.button("🔍 Webseiten analysieren (ohne Absenden)")

# --- Utilities
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

# --- Heuristic (Regex) extractor extended
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

        # Name fields
        if re.search(r"(full.?name|your.?name|contact.?name|^name$|\bname\b)", attr_text):
            mapping.setdefault("name", sel)
        if re.search(r"(vorname|first.?name|given.?name|\bfname\b)", attr_text):
            mapping.setdefault("first_name", sel)
        if re.search(r"(nachname|last.?name|family.?name|\blname\b|surname)", attr_text):
            mapping.setdefault("last_name", sel)

        # Email
        if re.search(r"(mail|e.?mail)", attr_text) or (inp.get("type") or "").lower() == "email":
            mapping.setdefault("email", sel)

        # Phone
        if re.search(r"(telefon|handy|mobil|phone|tel|telephone|phone.?number)", attr_text) or (inp.get("type") or "").lower() == "tel":
            mapping.setdefault("phone", sel)

        # Street (address line)
        if re.search(r"(stra(ss|ß)e|street|address(\s*line)?\s*1|hausnummer|addr1)", attr_text):
            mapping.setdefault("street", sel)

        # ZIP/PLZ
        if re.search(r"(plz|zip|postal.?code|post.?code)", attr_text):
            mapping.setdefault("zip", sel)

        # City
        if re.search(r"(ort|stadt|city|locality|town)", attr_text):
            mapping.setdefault("city", sel)

        # Message
        if re.search(r"(nachricht|message|bemerkung|kommentar|anschreiben|cover.?letter|motivation|inquiry|comments|text)", attr_text) or inp.name == "textarea":
            mapping.setdefault("message", sel)

    return mapping if mapping else None

# --- AI extractor (German system prompt, extended keys)
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
        for k in ["first_name", "last_name", "name", "email", "phone", "street", "zip", "city", "message"]:
            mapping[k] = normalize_selector_value(mapping.get(k))
        if not any(mapping.values()):
            return None
        return mapping
    except Exception as e:
        if show_debug:
            st.warning(f"KI-Extraktion fehlgeschlagen: {e}")
        return None

# --- Locator helpers
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

# --- Semantic fallbacks via label/placeholder
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

# --- Execution
if run:
    urls = [u.strip() for u in urls_input.split("\n") if u.strip()]
    if not urls:
        st.error("Bitte geben Sie mindestens eine gültige URL ein.")
    else:
        if use_ai:
            if openai_mode == "new":
                st.info("KI-Modus: Neuer OpenAI SDK erkannt.")
            elif openai_mode == "legacy":
                st.info("KI-Modus: Legacy OpenAI SDK erkannt.")
            else:
                st.warning("KI-Modus aktiviert, aber kein funktionierender OpenAI-Client gefunden. Es wird der Regex-Fallback verwendet.")

        st.info(f"{len(urls)} Webseiten werden überprüft...")
        results = []

        with st.spinner("Starte Browser und analysiere Webseiten..."):
            with sync_playwright() as p:
                browser = p.firefox.launch(headless=False, slow_mo=200)
                page = browser.new_page()

                for url in urls:
                    st.write(f"🌐 **{url}** wird analysiert...")
                    try:
                        page.goto(url, wait_until="load")
                        page.wait_for_timeout(1500)
                        rendered_html = page.content()

                        mapping = None
                        if use_ai and openai_mode is not None:
                            mapping = ai_extract_form_fields(rendered_html)

                        if not mapping:
                            if show_debug:
                                st.info("KI-Erkennung nicht verfügbar/fehlgeschlagen. Verwende Regex-Fallback.")
                            r = requests.get(url, timeout=15)
                            mapping = extract_form_fields_regex(r.text)

                        filled_any = False
                        if mapping:
                            st.code(json.dumps(mapping, indent=2, ensure_ascii=False))

                            # Prepare data, including split names
                            first_name_val, last_name_val = split_full_name(full_name)
                            data = {
                                "name": full_name,
                                "first_name": first_name_val or full_name,
                                "last_name": last_name_val or "",
                                "email": email,
                                "phone": phone,
                                "street": street,
                                "zip": zip_code,
                                "city": city,
                                "message": message
                            }

                            # Try mapping selectors first
                            for field_key, value in data.items():
                                sel = mapping.get(field_key)
                                ok = False
                                if sel:
                                    ok = try_fill_by_selector(page, sel, value, field_key, debug=show_debug)
                                # If selector path failed or missing, use semantic fallbacks
                                if not ok and value:
                                    ok = try_semantic_fill(page, field_key, value, debug=show_debug)
                                filled_any = filled_any or ok

                            if filled_any:
                                results.append({"url": url, "status": "✅ Formular erkannt und ausgefüllt (inkl. Nachname/Straße, falls vorhanden)"})
                            else:
                                results.append({"url": url, "status": "⚠️ Formular erkannt, aber keine Felder erfolgreich gefüllt"})
                        else:
                            results.append({"url": url, "status": "⚠️ Kein Formular gefunden"})

                    except Exception as e:
                        results.append({"url": url, "status": f"❌ Fehler: {e}"})
                        if show_debug:
                            st.error(f"Fehler bei {url}: {e}")
                        continue

                page.pause()
                browser.close()

        st.success("Analyse abgeschlossen.")
        st.json(results)
