@echo off
echo ==========================================
echo Starting Multi-Agent Discord Bot
echo 6 Specialized AI Agents
echo ==========================================
echo.

cd /d "%~dp0"

echo Activating conda environment...
call conda activate stock_analysis

echo.
echo Starting Discord Multi-Agent Bot...
echo.

python src/ai_agent_hybrid/discord_bot_multi_agent.py

pause
