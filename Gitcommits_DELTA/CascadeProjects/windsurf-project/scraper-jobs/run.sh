#!/bin/bash
# Run the Job Scraper Streamlit application

cd "$(dirname "$0")"
source ../venv/bin/activate
streamlit run scraper.py
