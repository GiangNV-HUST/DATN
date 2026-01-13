#!/bin/bash

echo "========================================"
echo "AI Stock Advisor - Full Agent System"
echo "========================================"
echo ""
echo "Starting Streamlit UI with Full Agent System..."
echo "Access at: http://localhost:8501"
echo ""

cd "$(dirname "$0")"
streamlit run src/streamlit_ui/app_full_agent.py
