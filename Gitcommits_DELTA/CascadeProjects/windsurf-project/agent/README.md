# Agent Tools - Streamlit Applications

This folder contains two Streamlit applications:

1. **OBI Shopping Agent** (`shopping_agent.py`) - Scrapes OBI.de for product information
2. **HTML Element Parser** (`main.py`) - Parse and search HTML files for specific elements

## Prerequisites

- Python 3.8 or higher
- Chrome or Chromium browser (only for Shopping Agent)
- ChromeDriver (will be managed by Selenium automatically)

## Installation

Install the required dependencies:
```bash
pip install -r requirements.txt
```

---

## 1. OBI Shopping Agent

### Features
- 🔍 Search for products on OBI.de
- 💶 Find the cheapest offers automatically
- 📊 View results in an interactive table
- 📥 Download results as CSV
- ⚙️ Configurable settings (headless mode, max results)

### Usage

```bash
streamlit run shopping_agent.py
```

The app will open at `http://localhost:8501`

### How to Use

1. Enter a search term in the text input field
2. Adjust settings in the sidebar:
   - **Headless mode**: Run browser in background (recommended)
   - **Maximum results**: Number of products to fetch (1-10)
3. Click the "🔎 Search" button
4. View the results:
   - Product cards with expandable details
   - Interactive data table
   - Cheapest offer highlighted
5. Download results as CSV if needed

### Example Search Terms

- entlüfterschlüssel (radiator key)
- Hammer (hammer)
- Bohrmaschine (drill)
- Schrauben (screws)
- LED Lampe (LED lamp)

---

## 2. HTML Element Parser

### Features
- 📤 Upload HTML files or paste HTML content
- 🔍 Search by Tag, Class, or ID
- 🔑 Keyword search within elements
- 📄 View full HTML, text content, and attributes
- 🎉 Highlights when keywords are found

### Usage

```bash
streamlit run main.py
```

The app will open at `http://localhost:8501`

### How to Use

1. Upload an HTML file or paste HTML content
2. Choose search method (Tag, Class, or ID)
3. Enter the search value
4. Optionally add a keyword to search within the element
5. Click Search to find the element
6. View results in organized tabs:
   - HTML code
   - Text content
   - Element attributes

### Example Searches

- **Tag:** `div`, `span`, `a`, `p`
- **Class:** `col-xs-6 col-sm-6 col-md-6 col-lg-6`
- **ID:** `main-content`, `header`
- **Keyword:** `Anlagenmechaniker` (will show "Yuhuu!" if found)

---

## Notes

- **Shopping Agent**: Uses Selenium WebDriver with Chrome. First run may take longer as it loads the website and handles cookies. Headless mode is recommended for faster performance.
- **HTML Parser**: Works entirely in-browser, no external dependencies needed beyond BeautifulSoup4.

## Troubleshooting

If you encounter issues:
1. Make sure all dependencies are installed: `pip install -r requirements.txt`
2. For Shopping Agent: Ensure Chrome/Chromium is installed
3. Check the error messages in the Streamlit interface
4. Try restarting the Streamlit server
