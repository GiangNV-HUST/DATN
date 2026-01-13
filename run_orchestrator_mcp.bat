@echo off
REM Startup script for Orchestrator MCP Server
REM This script runs the multi-agent orchestrator as an MCP server

echo Starting Stock Market Orchestrator MCP Server...
echo This server provides access to the full multi-agent system

REM Set environment variables
set PYTHONPATH=%~dp0
set PYTHONIOENCODING=utf-8

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Run the orchestrator MCP server
python -m src.mcp_server.orchestrator_server

pause
