import streamlit as st
import requests
import bs4
import re
from pathlib import Path

import storage_utils as su  # NEW: shared storage utils

# Keep counters similar to your code (in-memory)
counting_websites = []

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
HTML_PATH = DATA_DIR / "text.html"


class Suche:
    def __init__(self):
        self.question = ""  # website URL
        self._html_path = HTML_PATH

    def ask_user_file(self):
        # Clean Streamlit input for website
        self.question = st.text_input("Wie lautet die Website?", placeholder="https://example.com")
        return self.question

    def website_scraper(self):
        # Minimal change: relies on self.question set by ask_user_file
        if not self.question:
            st.warning("Bitte gib zuerst eine Website ein.")
            return False
        try:
            # Ensure URL scheme
            url = self.question.strip()
            if not url.startswith("http://") and not url.startswith("https://"):
                url = "https://" + url

            r = requests.get(url, timeout=10)
            r.raise_for_status()
            with open(self._html_path, "wb") as play_file:
                for chunk in r.iter_content(100000):
                    play_file.write(chunk)
            return True
        except Exception as e:
            st.error(f"Fehler beim Laden der Website: {e}")
            return False

    def analyze_filename(self):
        # Keeps your logic, prints to Streamlit
        count = 0
        value = False

        if not self._html_path.exists():
            st.warning("Keine Datei gefunden. Bitte zuerst scrapen.")
            return

        contents = self._html_path.read_text(encoding="utf-8", errors="ignore")
        lines = contents.splitlines()
        for line in lines:
            if "Anlagenmechaniker" in line:
                value = True
                st.write(line)

        if value:
            st.success("Anlagenmechaniker: Check ✅ ")
            count += 1
            counting_websites.append(count)
            st.info(f"Anzahl von Stellenangeboten total: {len(counting_websites)}")
            st.write(f"Website: {self.question}")
            st.write("Website wird gespeichert (keine Duplikate)")
            su.add_website(self.question)  # NEW: store via helper

            st.write(su.load_storage())

    def match_telefonnummer(self, text: str):
        """
        New clean method:
        - Matches common phone formats (e.g., +49 ..., 0..., with spaces, parentheses)
        - Returns the first match or None
        """
        if not text:
            return None

        pattern = re.compile(
            r"""
            (?:
                (\+?\d{2,3})      # country code, optional
                [\s\-]?
            )?
            (?:\(?\d{2,5}\)?)     # area code
            [\s\/\-]?
            (?:\d{3,})            # subscriber number
            """,
            re.VERBOSE
        )

        for m in pattern.finditer(text):
            candidate = m.group().strip()
            digits = re.sub(r"\D", "", candidate)
            if len(digits) >= 7:
                return candidate
        return None

    def find_number(self):
        """
        Entry point similar to your original name,
        but uses match_telefonnummer for the actual work.
        """
        if not self._html_path.exists():
            st.warning("Keine Datei gefunden. Bitte zuerst scrapen.")
            return

        contents = self._html_path.read_text(encoding="utf-8", errors="ignore")
        phone = self.match_telefonnummer(contents)
        if phone:
            st.success(f"Telefonnummer gefunden: {phone}")
        else:
            st.warning("Keine Nummer gefunden.")

    def extract_betrieb_info(self):
        """
        Outputs simple info about the 'Betrieb' (company):
        - title
        - meta description
        - first h1/h2
        """
        info = {"title": None, "description": None, "headline": None}
        if not self._html_path.exists():
            return info

        html = self._html_path.read_text(encoding="utf-8", errors="ignore")
        soup = bs4.BeautifulSoup(html, "html.parser")

        if soup.title and soup.title.string:
            info["title"] = soup.title.string.strip()

        meta_desc = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        if meta_desc and meta_desc.get("content"):
            info["description"] = meta_desc.get("content").strip()

        h1 = soup.find("h1")
        h2 = soup.find("h2")
        if h1 and h1.get_text(strip=True):
            info["headline"] = h1.get_text(strip=True)
        elif h2 and h2.get_text(strip=True):
            info["headline"] = h2.get_text(strip=True)

        return info


def render_suche_page():
    st.title("Suche: Webseiten prüfen und Telefonnummer finden")
    ha = Suche()

    ha.ask_user_file()

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Website scrapen"):
            ok = ha.website_scraper()
            if ok:
                st.success("Website erfolgreich gespeichert.")
    with col2:
        if st.button("Analysieren (Anlagenmechaniker + Telefonnummer)"):
            ha.analyze_filename()
            ha.find_number()

    st.markdown("---")
    st.subheader("Betrieb-Informationen")
    info_btn = st.button("Betrieb-Infos anzeigen")
    if info_btn:
        info = ha.extract_betrieb_info()
        st.write(f"- Titel: {info.get('title') or 'Nicht gefunden'}")
        st.write(f"- Beschreibung: {info.get('description') or 'Nicht gefunden'}")
        st.write(f"- Überschrift: {info.get('headline') or 'Nicht gefunden'}")

    st.markdown("---")
    st.subheader("Gespeicherte Webseiten (keine Duplikate)")
    websites = su.load_storage()
    if websites:
        for i, w in enumerate(websites, 1):
            st.write(f"{i}. {w}")
    else:
        st.write("Keine gespeicherten Webseiten.")


def render_ad_studio_page():
    # Import the other page module safely (no circular import now)
    import ads_page
    ads_page.AdStudioPage().render()


def main():
    st.set_page_config(page_title="Handwerker Lead Tool", layout="centered")
    st.sidebar.title("Navigation")
    choice = st.sidebar.radio("Seite auswählen:", ["Suche", "Ad Studio"])

    if choice == "Suche":
        render_suche_page()
    else:
        render_ad_studio_page()


if __name__ == "__main__":
    main()
