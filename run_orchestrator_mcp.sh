#!/bin/bash
# Startup script for Orchestrator MCP Server
# This script runs the multi-agent orchestrator as an MCP server

echo "Starting Stock Market Orchestrator MCP Server..."
echo "This server provides access to the full multi-agent system"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Set environment variables
export PYTHONPATH="$SCRIPT_DIR"
export PYTHONIOENCODING=utf-8

# Activate virtual environment if it exists
if [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source "$SCRIPT_DIR/venv/bin/activate"
fi

# Run the orchestrator MCP server
python -m src.mcp_server.orchestrator_server
