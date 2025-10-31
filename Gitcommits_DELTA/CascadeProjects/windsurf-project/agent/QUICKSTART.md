# Quick Start Guide

## Setup (One-time)

```bash
cd /Users/maddoxsciuchetti/webpage.handwerk/Gitcommits_DELTA/CascadeProjects/windsurf-project/agent
pip install -r requirements.txt
```

## Run Applications

### Option 1: HTML Element Parser
```bash
streamlit run main.py
```

### Option 2: OBI Shopping Agent
```bash
streamlit run shopping_agent.py
```

## What Each App Does

### `main.py` - HTML Element Parser
- Upload or paste HTML content
- Search for elements by Tag, Class, or ID
- Find keywords within elements
- View HTML structure, text, and attributes

### `shopping_agent.py` - OBI Shopping Agent
- Search OBI.de for products
- Compare prices
- Find cheapest offers
- Download results as CSV

---

**Note:** Both apps will open automatically in your browser at `http://localhost:8501`
