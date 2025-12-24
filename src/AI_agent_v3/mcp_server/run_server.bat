@echo off
echo ============================================================
echo STOCK MCP SERVER V3
echo ============================================================
echo.

REM Activate venv if exists
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

echo Starting MCP Server...
echo.

cd src\AI_agent_v3\mcp_server

python stock_mcp_server.py --host 0.0.0.0 --port 5000

pause
