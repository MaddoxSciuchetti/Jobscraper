# Agent Hub - Multi-Purpose Automation Platform

A comprehensive Streamlit application featuring job scraping, voice transcription, shopping comparison, and automated job applications.

## Features

- **💼 Job Scraper** - Find and analyze Anlagenmechaniker job postings
- **🎙️ Transcriber** - Voice-to-text transcription for HVAC reports
- **🛒 Shopping Agent** - AI-powered multi-shop product search (OBI, Würth, Bauhaus)
- **🕵️‍♂️ Auto-Bewerbung** - Automated job application system

## Local Development

### Prerequisites
- Python 3.9+
- PortAudio (for voice recording)

### Installation

```bash
# Install system dependencies (macOS)
brew install portaudio

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Create .env file
echo "OPENAI_API_KEY=your-key-here" > .env

# Run the app
streamlit run app.py
```

## Deployment to Streamlit Cloud

### Step 1: Push to GitHub
Your code is already on GitHub at: `MaddoxSciuchetti/Jobscraper`

### Step 2: Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io/)
2. Sign in with GitHub
3. Click "New app"
4. Select:
   - **Repository:** MaddoxSciuchetti/Jobscraper
   - **Branch:** main
   - **Main file:** app.py
5. Click "Deploy"

### Step 3: Add Secrets

In Streamlit Cloud dashboard, go to **Settings → Secrets** and add:

```toml
OPENAI_API_KEY = "your-actual-openai-key-here"
```

### Step 4: Advanced Settings (Optional)

- **Python version:** 3.9
- **Custom domain:** Configure in Settings → General

## Environment Variables

Required environment variables:
- `OPENAI_API_KEY` - Your OpenAI API key for AI-enhanced search

## Files Structure

```
.
├── app.py                 # Main application
├── requirements.txt       # Python dependencies
├── packages.txt          # System dependencies for Streamlit Cloud
├── .streamlit/
│   └── config.toml       # Streamlit configuration
├── agent/                # Shopping agent module
├── kontakt_agent/        # Contact agent module
├── transcriber/          # Voice transcription module
└── scraper-jobs/         # Job scraping utilities
```

## Known Limitations on Streamlit Cloud

- **Voice recording** may not work (requires microphone access)
- **Selenium/Playwright** features may be limited
- **File uploads** are temporary and reset on rerun

## License

MIT License
