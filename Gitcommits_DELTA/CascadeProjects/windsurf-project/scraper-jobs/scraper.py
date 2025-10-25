"""
Job Scraper - Streamlit Application
A web scraper for collecting job listings from various sources with a modern UI.
"""

import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import os
import glob
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

# === CONFIG ===
JOBS_FOLDER = "scraped_jobs"
os.makedirs(JOBS_FOLDER, exist_ok=True)

# Initialize session state
if 'jobs' not in st.session_state:
    st.session_state.jobs = []
if 'scraping_history' not in st.session_state:
    st.session_state.scraping_history = []


class JobScraper:
    """Main job scraper class"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    def scrape_jobs(self, url, job_selector=None, title_selector=None, company_selector=None, location_selector=None):
        """
        Scrape jobs from a given URL with custom selectors
        
        Args:
            url (str): The URL to scrape
            job_selector (str): CSS selector for job containers
            title_selector (str): CSS selector for job title
            company_selector (str): CSS selector for company name
            location_selector (str): CSS selector for location
            
        Returns:
            list: List of job dictionaries
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


def main():
    """Main Streamlit application"""
    st.set_page_config(
        page_title="Job Scraper",
        page_icon="🔍",
        layout="wide"
    )
    
    st.title("🔍 Job Scraper")
    st.markdown("Scrape job listings from various websites and manage your job search data.")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        
        st.subheader("Scraper Configuration")
        use_custom_selectors = st.checkbox("Use Custom CSS Selectors", value=False)
        
        st.divider()
        st.header("📊 Statistics")
        saved_files = get_saved_files()
        st.metric("Saved Files", len(saved_files))
        st.metric("Jobs in Current Session", len(st.session_state.jobs))
    
    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["🔍 Scrape Jobs", "📁 Saved Data", "📖 History"])
    
    with tab1:
        st.header("Scrape Job Listings")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            url_input = st.text_input(
                "Enter Job Board URL",
                placeholder="https://example.com/jobs",
                help="Enter the URL of the job board or company careers page"
            )
        
        with col2:
            st.write("")  # Spacing
            st.write("")  # Spacing
            scrape_button = st.button("🚀 Start Scraping", type="primary", use_container_width=True)
        
        # Custom selectors section
        if use_custom_selectors:
            st.subheader("Custom CSS Selectors")
            st.info("💡 Use browser DevTools to find CSS selectors for job elements")
            
            col1, col2 = st.columns(2)
            with col1:
                job_selector = st.text_input("Job Container Selector", placeholder=".job-card")
                title_selector = st.text_input("Title Selector", placeholder=".job-title")
            with col2:
                company_selector = st.text_input("Company Selector", placeholder=".company-name")
                location_selector = st.text_input("Location Selector", placeholder=".job-location")
        else:
            job_selector = title_selector = company_selector = location_selector = None
        
        # Scraping logic
        if scrape_button and url_input:
            with st.spinner("🔄 Scraping jobs..."):
                scraper = JobScraper()
                jobs = scraper.scrape_jobs(
                    url_input,
                    job_selector,
                    title_selector,
                    company_selector,
                    location_selector
                )
                
                if jobs:
                    st.session_state.jobs.extend(jobs)
                    st.session_state.scraping_history.append({
                        'url': url_input,
                        'jobs_found': len(jobs),
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    st.success(f"✅ Successfully scraped {len(jobs)} jobs!")
                else:
                    st.warning("⚠️ No jobs found. Try using custom selectors or check the URL.")
        
        # Display current session jobs
        if st.session_state.jobs:
            st.divider()
            st.subheader(f"📋 Current Session Jobs ({len(st.session_state.jobs)})")
            
            df = pd.DataFrame(st.session_state.jobs)
            st.dataframe(df, use_container_width=True, height=400)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("💾 Save to CSV", type="primary", use_container_width=True):
                    scraper = JobScraper()
                    filepath = scraper.save_to_csv(st.session_state.jobs)
                    if filepath:
                        st.success(f"✅ Saved to {os.path.basename(filepath)}")
            
            with col2:
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            with col3:
                if st.button("🗑️ Clear Session", use_container_width=True):
                    st.session_state.jobs = []
                    st.rerun()
    
    with tab2:
        st.header("📁 Saved Job Data")
        
        if saved_files:
            selected_file = st.selectbox(
                "Select a file to view",
                options=saved_files,
                format_func=lambda x: os.path.basename(x)
            )
            
            if selected_file:
                df = load_csv_data(selected_file)
                if df is not None:
                    st.subheader(f"📊 {os.path.basename(selected_file)}")
                    st.metric("Total Jobs", len(df))
                    
                    # Display data
                    st.dataframe(df, use_container_width=True, height=400)
                    
                    # Actions
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        csv = df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Download",
                            data=csv,
                            file_name=os.path.basename(selected_file),
                            mime="text/csv",
                            use_container_width=True
                        )
                    
                    with col2:
                        if st.button("🔄 Load to Session", use_container_width=True):
                            st.session_state.jobs = df.to_dict('records')
                            st.success("✅ Loaded to current session!")
                            st.rerun()
                    
                    with col3:
                        if st.button("🗑️ Delete File", use_container_width=True):
                            os.remove(selected_file)
                            st.success("✅ File deleted!")
                            st.rerun()
        else:
            st.info("📭 No saved files yet. Start scraping to create your first dataset!")
    
    with tab3:
        st.header("📖 Scraping History")
        
        if st.session_state.scraping_history:
            history_df = pd.DataFrame(st.session_state.scraping_history)
            st.dataframe(history_df, use_container_width=True)
            
            if st.button("🗑️ Clear History"):
                st.session_state.scraping_history = []
                st.rerun()
        else:
            st.info("📭 No scraping history yet. Start scraping to see your activity!")


if __name__ == "__main__":
    main()
