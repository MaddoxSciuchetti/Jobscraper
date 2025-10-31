# Auto Bewerbungs Scanner

A Streamlit-based web application that automatically scans websites for contact forms, identifies their fields, and demonstrates how they could be filled out - without actually submitting the form.

## Features

- Scans multiple URLs for contact forms
- Uses AI (OpenAI GPT-4) or regex-based field detection
- Automatically identifies common form fields (name, email, phone, address, message)
- Visual preview of form filling using Playwright browser automation
- Supports both German and English form fields

## Requirements

- Python 3.x
- Streamlit
- Playwright
- BeautifulSoup4
- OpenAI API (optional, for AI-powered field detection)

## Usage

Run the application with:
```bash
streamlit run app.py
```

Enter URLs and your contact information to see how the tool identifies and fills contact forms.
