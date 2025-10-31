import time
import csv
import re
from urllib.parse import quote_plus
import streamlit as st
import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

OBI_URL = "https://www.obi.de"

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

def accept_cookies(driver: webdriver.Chrome):
    """Robustly accept cookies on OBI.de (handles Sourcepoint/OneTrust in iframe or DOM)."""
    try:
        time.sleep(1.0)
        WebDriverWait(driver, 15).until(
            lambda d: (
                len(d.find_elements(By.CSS_SELECTOR, "iframe[id*='sp_message_iframe'], iframe[src*='consent']")) > 0 or
                len(d.find_elements(By.XPATH, "//button[contains(., 'Alle akzeptieren')]")) > 0 or
                len(d.find_elements(By.CSS_SELECTOR, "#onetrust-accept-btn-handler")) > 0
            )
        )
    except TimeoutException:
        # Kein Banner – einfach weiter
        return

    clicked = False

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

    if clicked:
        # Warte bis Overlay verschwindet
        try:
            WebDriverWait(driver, 10).until(
                EC.invisibility_of_element_located(
                    (By.CSS_SELECTOR, "iframe[id*='sp_message_iframe'], #onetrust-banner-sdk, div[class*='sp_message']")
                )
            )
        except Exception:
            pass
        print("✅ Cookies akzeptiert.")
    else:
        print("ℹ️ Kein Cookie-Banner gefunden oder bereits akzeptiert.")

def wait_for_results(driver):
    """Warte robust auf Suchergebnis-Elemente, deckt verschiedene Varianten ab."""
    selectors_any = [
        (By.CSS_SELECTOR, "a[data-test='product-title']"),
        (By.CSS_SELECTOR, "div[data-test='product-tile']"),
        (By.CSS_SELECTOR, "section[data-test='products-grid'] a[data-test='product-title']"),
        # Fallbacks, falls data-test anders ist:
        (By.CSS_SELECTOR, "a[href*='/p/']"),  # Produkt-Detail-Links enthalten oft /p/
    ]

    # Warte, bis eines der Selektoren erscheint
    start = time.time()
    last_err = None
    while time.time() - start < 20:
        for by, sel in selectors_any:
            els = driver.find_elements(by, sel)
            if els:
                return True
        time.sleep(0.5)
    return False

def collect_items(driver, limit=3):
    """Sammle Produktkarten mit flexiblen Selektoren."""
    # Versuche zuerst die standardisierte Struktur
    cards = driver.find_elements(By.CSS_SELECTOR, "div[data-test='product-tile']")
    if not cards:
        # Fallback: Look for anchors to product pages and walk up the DOM
        anchors = driver.find_elements(By.CSS_SELECTOR, "a[data-test='product-title']")
        if not anchors:
            anchors = driver.find_elements(By.CSS_SELECTOR, "a[href*='/p/']")
        cards = anchors if anchors else []

    results = []
    for item in cards[:limit]:
        try:
            # Suche Title-Link
            try:
                title_el = item.find_element(By.CSS_SELECTOR, "a[data-test='product-title']")
            except Exception:
                # Falls item bereits der Anchor ist
                title_el = item if item.tag_name.lower() == "a" else item.find_element(By.CSS_SELECTOR, "a[href*='/p/']")
            name = title_el.text.strip()
            link = title_el.get_attribute("href")

            # Preis (flexibel)
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

def scrape_obi(driver: webdriver.Chrome, term: str, limit: int = 3):
    """Scrape OBI.de für den Suchbegriff. Nutzt direkte Such-URL und robuste Selektoren."""
    # 1) Direkt auf die Ergebnisseite (robuster als Eingabe ins Suchfeld)
    search_url = f"{OBI_URL}/search/?searchTerm={quote_plus(term)}"
    driver.get(search_url)
    accept_cookies(driver)

    # 2) Warte auf Ergebnisse (oder scrolle etwas, damit Lazy-Load triggert)
    driver.execute_script("window.scrollBy(0, 300);")
    if not wait_for_results(driver):
        # Fallback: versuche über das Suchfeld
        print("🔁 Fallback: Suche über das Suchfeld.")
        driver.get(OBI_URL)
        accept_cookies(driver)
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
            raise RuntimeError("Suchfeld nicht gefunden – Seite/Overlay blockiert?")
        search_box.clear()
        search_box.send_keys(term)
        search_box.send_keys(Keys.ENTER)

        if not wait_for_results(driver):
            # Debug: Screenshot + HTML sichern
            try:
                driver.save_screenshot("obi_timeout.png")
                with open("obi_source.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                print("🧪 Debug: Screenshot 'obi_timeout.png' und HTML 'obi_source.html' gespeichert.")
            except Exception:
                pass
            raise TimeoutException("Keine Suchergebnisse gefunden (Selektoren/Overlay?)")

    # 3) Items sammeln
    results = collect_items(driver, limit=limit)
    return results

def save_to_csv(filename: str, data):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["site", "product", "price", "link"])
        writer.writeheader()
        writer.writerows(data)

def main():
    st.set_page_config(page_title="OBI Shopping Agent", page_icon="🛒", layout="wide")
    
    st.title("🛒 OBI Shopping Agent")
    st.markdown("Search for products on OBI.de and find the best deals!")
    
    # Sidebar for settings
    with st.sidebar:
        st.header("⚙️ Settings")
        headless_mode = st.checkbox("Run in headless mode", value=True)
        max_results = st.slider("Maximum results", min_value=1, max_value=10, value=3)
    
    # Main search interface
    search_term = st.text_input(
        "🔍 Enter search term:",
        value="entlüfterschlüssel",
        placeholder="e.g., Hammer, Bohrmaschine, Schrauben..."
    )
    
    col1, col2 = st.columns([1, 4])
    with col1:
        search_button = st.button("🔎 Search", type="primary", use_container_width=True)
    
    if search_button and search_term:
        with st.spinner(f"🔎 Searching OBI.de for '{search_term}'..."):
            driver = None
            try:
                driver = setup_driver(headless=headless_mode)
                offers = scrape_obi(driver, search_term, limit=max_results)
                
                if not offers:
                    st.warning("⚠️ No products found. Try a different search term.")
                else:
                    # Save to CSV
                    save_to_csv("obi_offers.csv", offers)
                    
                    # Display results
                    st.success(f"✅ Found {len(offers)} products!")
                    
                    # Convert to DataFrame for better display
                    df = pd.DataFrame(offers)
                    
                    # Find cheapest product
                    valid_prices = [o for o in offers if price_to_float(o['price']) < 999999]
                    if valid_prices:
                        cheapest = min(valid_prices, key=lambda x: price_to_float(x['price']))
                        st.info(f"💶 **Cheapest offer:** {cheapest['product']} for **{cheapest['price']}**")
                    
                    # Display products in cards
                    st.subheader("📦 Products")
                    for idx, offer in enumerate(offers, 1):
                        with st.expander(f"{idx}. {offer['product']}", expanded=True):
                            col_a, col_b = st.columns([3, 1])
                            with col_a:
                                st.markdown(f"**Price:** {offer['price']}")
                                st.markdown(f"**Site:** {offer['site']}")
                            with col_b:
                                st.link_button("🔗 View Product", offer['link'], use_container_width=True)
                    
                    # Display as table
                    st.subheader("📊 Results Table")
                    st.dataframe(
                        df,
                        column_config={
                            "link": st.column_config.LinkColumn("Product Link"),
                            "product": "Product Name",
                            "price": "Price",
                            "site": "Website"
                        },
                        hide_index=True,
                        use_container_width=True
                    )
                    
                    # Download button
                    csv_data = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv_data,
                        file_name="obi_offers.csv",
                        mime="text/csv",
                    )
                    
            except Exception as e:
                st.error(f"❌ Error occurred: {str(e)}")
            finally:
                if driver:
                    driver.quit()
    
    # Instructions
    with st.expander("ℹ️ How to use"):
        st.markdown("""
        1. Enter a search term in the text box above
        2. Adjust settings in the sidebar if needed
        3. Click the **Search** button
        4. View results and download as CSV if needed
        
        **Note:** The scraper uses Selenium and requires Chrome/Chromium to be installed.
        """)

if __name__ == "__main__":
    main()
