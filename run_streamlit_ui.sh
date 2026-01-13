#!/bin/bash
# Run Streamlit UI for Stock Advisor AI Agent

echo "============================================"
echo "  Stock Advisor AI Agent - Streamlit UI"
echo "============================================"
echo ""

# Check if streamlit is installed
if ! python -c "import streamlit" 2>/dev/null; then
    echo "ERROR: Streamlit is not installed!"
    echo "Please run: pip install -r src/streamlit_ui/requirements.txt"
    echo ""
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "WARNING: .env file not found!"
    echo "Please create .env file with GOOGLE_API_KEY"
    echo ""
fi

echo "Starting Streamlit app..."
echo "App will open at: http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run streamlit
streamlit run src/streamlit_ui/app.py
