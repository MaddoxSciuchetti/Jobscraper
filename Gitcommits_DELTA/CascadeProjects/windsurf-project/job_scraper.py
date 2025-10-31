import streamlit as st
import requests
from pathlib import Path
import re
import time

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

st.title("Anlagenmechaniker Job Finder")

urls = st.text_area("Enter website URLs (one per line):")
keyword = "Anlagenmechaniker"

if st.button("Check Websites"):
    if urls.strip():
        url_list = [u.strip() for u in urls.splitlines() if u.strip()]
        progress = st.progress(0)
        status_placeholder = st.empty()
        for i, url in enumerate(url_list):
            status_placeholder.info(f"Processing {url} ...")
            time.sleep(1)  # Simulate loading time
            if url not in st.session_state.storage_websites:
                try:
                    filename, downloaded = save_website(url)
                    found, phone = analyze_file(filename, keyword)

                    if found:
                        st.session_state.job_count += 1
                        st.session_state.storage_websites.append(url)
                        st.success(f"Job found on: {url}")
                        st.write(f"Phone number: {phone if phone else 'None found'}")
                    else:
                        st.info(f"No Anlagenmechaniker job found on: {url}")
                except Exception as e:
                    st.error(f"Error on {url}: {e}")
            else:
                st.warning(f"Website already saved: {url}")
            progress.progress((i + 1) / len(url_list))
        status_placeholder.success("Done! All websites have been checked.")
    else:
        st.warning("Please enter at least one URL.")

st.write(f"**Number of Anlagenmechaniker jobs found:** {st.session_state.job_count}")
st.write(f"**Saved websites:**")
for site in st.session_state.storage_websites:
    st.write(site)
