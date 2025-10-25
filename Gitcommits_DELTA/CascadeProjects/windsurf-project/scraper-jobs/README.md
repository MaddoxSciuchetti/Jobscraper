# Job Scraper (Streamlit App)

A powerful web-based job scraping application for collecting and managing job listings from various sources. Built with Streamlit for an intuitive user interface.

## Features

- 🔍 **Web Scraping**: Scrape job listings from any job board or careers page
- 🎯 **Custom Selectors**: Use custom CSS selectors for precise data extraction
- 📊 **Data Management**: View, edit, and manage scraped job data
- 💾 **Export Options**: Save to CSV or download directly
- 📁 **File Management**: Browse and manage saved job datasets
- 📖 **History Tracking**: Keep track of all scraping activities
- 🎨 **Modern UI**: Clean, intuitive interface with tabs and real-time updates

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. (Optional) Create a `.env` file for environment variables:
```bash
# Add any API keys or configuration here
```

## Usage

### Option 1: Using the run script
```bash
./run.sh
```

### Option 2: Direct Streamlit command
```bash
streamlit run scraper.py
```

The application will open in your default web browser at `http://localhost:8501`

## How to Use

### Basic Scraping
1. Navigate to the **"🔍 Scrape Jobs"** tab
2. Enter the URL of a job board or careers page
3. Click **"🚀 Start Scraping"**
4. View results in the data table
5. Save or download the data

### Advanced Scraping with Custom Selectors
1. Enable **"Use Custom CSS Selectors"** in the sidebar
2. Use browser DevTools to find CSS selectors for:
   - Job container (e.g., `.job-card`)
   - Job title (e.g., `.job-title`)
   - Company name (e.g., `.company-name`)
   - Location (e.g., `.job-location`)
3. Enter the selectors and start scraping

### Managing Data
- **Saved Data Tab**: View and manage previously saved CSV files
- **History Tab**: Track all scraping activities
- **Export Options**: Download as CSV or save to local storage

## Features in Detail

### 🔍 Scrape Jobs Tab
- Enter any job board URL
- Toggle custom CSS selectors for precise extraction
- View scraped jobs in real-time
- Save to CSV or download immediately
- Clear session data when needed

### 📁 Saved Data Tab
- Browse all saved CSV files
- Preview data in interactive tables
- Download or reload data to current session
- Delete old files

### 📖 History Tab
- View all scraping activities
- Track URLs scraped and jobs found
- Clear history when needed

### ⚙️ Sidebar
- Toggle custom selector mode
- View statistics (saved files, session jobs)
- Quick access to settings

## Requirements

- Python 3.8+
- Modern web browser
- Internet connection for scraping

## Dependencies

See `requirements.txt` for full list:
- `streamlit` - Web application framework
- `requests` - HTTP library for web scraping
- `beautifulsoup4` - HTML parsing
- `pandas` - Data manipulation
- `selenium` - Browser automation (optional)
- `python-dotenv` - Environment variable management

## Tips for Best Results

1. **Use Custom Selectors**: For consistent results, use custom CSS selectors specific to your target website
2. **Inspect Elements**: Use browser DevTools (F12) to find the right selectors
3. **Test URLs**: Start with a single page to test your selectors before bulk scraping
4. **Respect Robots.txt**: Always check and respect website scraping policies
5. **Rate Limiting**: Avoid overwhelming servers with too many requests

## Troubleshooting

**No jobs found?**
- Verify the URL is correct
- Try using custom CSS selectors
- Check if the website requires JavaScript (may need Selenium)

**Scraping errors?**
- Check your internet connection
- Verify the website is accessible
- Some sites may block automated requests

## License

[Add license information]

## Contributing

[Add contribution guidelines]
