@echo off
REM Run Streamlit UI for Stock Advisor AI Agent

echo ============================================
echo   Stock Advisor AI Agent - Streamlit UI
echo ============================================
echo.

REM Check if streamlit is installed
python -c "import streamlit" 2>NUL
if errorlevel 1 (
    echo ERROR: Streamlit is not installed!
    echo Please run: pip install -r src/streamlit_ui/requirements.txt
    echo.
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist .env (
    echo WARNING: .env file not found!
    echo Please create .env file with OPENAI_API_KEY
    echo You can copy from .env.example
    echo.
)

echo Starting Streamlit app with OpenAI...
echo App will open at: http://localhost:8501
echo.
echo Press Ctrl+C to stop the server
echo.

REM Run streamlit (OpenAI version)
streamlit run src\streamlit_ui\app_openai.py

pause
