#!/bin/bash

# OBI Shopping Agent - Streamlit Runner
echo "🛒 Starting OBI Shopping Agent..."
echo ""

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null
then
    echo "❌ Streamlit is not installed."
    echo "Please install dependencies first:"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Run the Streamlit app
streamlit run shopping_agent.py
