@echo off
echo ==========================================
echo Starting Multi-Agent Streamlit UI
echo 6 Specialized AI Agents
echo ==========================================
echo.

cd /d "%~dp0"

echo Activating conda environment...
call conda activate stock_analysis

echo.
echo Starting Streamlit Multi-Agent App...
echo.

streamlit run src/streamlit_ui/app_multi_agent.py --server.port 8502

pause
