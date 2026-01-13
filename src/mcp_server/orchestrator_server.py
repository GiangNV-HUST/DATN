"""
MCP Server Wrapper for Multi-Agent Orchestrator
Provides high-level orchestrator access via MCP protocol for Claude Desktop

ARCHITECTURE:
    Claude Desktop / Discord / Web
           ↓ (MCP Protocol)
    orchestrator_server.py  ← This file (single entry point: process_query)
           ↓
    HybridOrchestrator (main_orchestrator.py)
           ↓
    AI Router (decides AGENT vs DIRECT mode)
           ↓
    ┌─────────────────────────────────┐
    │  AGENT MODE (Complex)           │  DIRECT MODE (Fast)
    │  - AnalysisSpecialist           │  - Pattern matching
    │  - ScreenerSpecialist           │  - Direct tool call
    │  - InvestmentPlanner            │
    │  - DiscoverySpecialist          │
    │  - AlertManager                 │
    │  - SubscriptionManager          │
    └─────────────────────────────────┘
           ↓
    server.py (31 MCP tools)
           ↓
    Database / External APIs

This preserves the entire multi-agent system logic including routing, specialized agents, and state management.
All channels (Claude, Discord, Web) connect to the same orchestrator backend.
"""
import sys
import os
from pathlib import Path
import io

# IMPORTANT: Suppress stdout during imports to prevent vnstock welcome messages
# from breaking MCP JSON-RPC protocol
_original_stdout = sys.stdout
_original_stderr = sys.stderr
sys.stdout = io.StringIO()
sys.stderr = io.StringIO()

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent.parent

# Load environment variables from .env file
from dotenv import load_dotenv
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)
    # Restore temporarily to log
    sys.stdout = _original_stdout
    print(f"[OK] Loaded .env from {env_path}")
    sys.stdout = io.StringIO()
pythonpath_env = os.environ.get('PYTHONPATH', '')
if pythonpath_env and pythonpath_env not in sys.path:
    sys.path.insert(0, pythonpath_env)
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import asyncio
import logging
import json
from typing import Any, Optional, Literal, List
from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from pydantic import BaseModel, Field

# Import the Multi-Agent orchestrator (upgraded from HybridOrchestrator)
try:
    from src.ai_agent_hybrid.hybrid_system.orchestrator.multi_agent_orchestrator import MultiAgentOrchestrator
except ImportError as e:
    # Restore before logging error
    sys.stdout = _original_stdout
    sys.stderr = _original_stderr
    logging.error(f"Failed to import MultiAgentOrchestrator: {e}")
    raise

# Restore stdout/stderr after all imports are done
sys.stdout = _original_stdout
sys.stderr = _original_stderr

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create MCP server instance
app = Server("stock-market-orchestrator-server")

# Global orchestrator instance - NOW USES MultiAgentOrchestrator with 6 Specialists
orchestrator: Optional[MultiAgentOrchestrator] = None


async def get_orchestrator() -> MultiAgentOrchestrator:
    """Get or create the Multi-Agent orchestrator instance"""
    global orchestrator
    if orchestrator is None:
        logger.info("Initializing MultiAgentOrchestrator with 6 Specialists...")

        # Path to the actual MCP server with all stock tools
        mcp_server_path = os.path.join(
            project_root,
            "src", "mcp_server", "server.py"
        )
        logger.info(f"Using MCP server at: {mcp_server_path}")

        # Use DirectMCPClient when running inside Claude Desktop MCP server
        # This avoids subprocess creation issues (StringIO has no fileno())
        orchestrator = MultiAgentOrchestrator(
            server_script_path=mcp_server_path,
            use_direct_client=True  # Use in-process client, not subprocess
        )
        await orchestrator.initialize()
        logger.info(f"MultiAgentOrchestrator initialized with {len(orchestrator.specialists)} specialists!")
    return orchestrator


# ============================================================
# TOOL SCHEMAS - Single entry point for multi-agent system
# ============================================================

class ProcessQueryInput(BaseModel):
    """Input schema for process_query tool - THE MAIN AND ONLY ENTRY POINT"""
    user_query: str = Field(description="The user's query or request in natural language")
    user_id: str = Field(default="claude_desktop_user", description="User ID for session management")
    mode: Optional[Literal["auto", "agent", "direct"]] = Field(
        default="auto",
        description="Execution mode: 'auto' (AI decides - recommended), 'agent' (force complex reasoning), 'direct' (force fast execution)"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Optional session ID to maintain conversation context across multiple queries"
    )


class GetSessionStateInput(BaseModel):
    """Input schema for get_session_state tool"""
    session_id: str = Field(description="Session ID to retrieve state for")


class ClearSessionInput(BaseModel):
    """Input schema for clear_session tool"""
    session_id: str = Field(description="Session ID to clear")


class GetSystemStatusInput(BaseModel):
    """Input schema for get_system_status tool"""
    include_metrics: bool = Field(default=True, description="Include execution metrics")


class ListAvailableCapabilitiesInput(BaseModel):
    """Input schema for list_available_capabilities tool"""
    category: Optional[str] = Field(default=None, description="Filter by category: analysis, screening, planning, discovery, alerts, subscriptions, data")


# ============================================================
# TOOL REGISTRATION - Only expose orchestrator-level tools
# ============================================================

@app.list_tools()
async def list_tools() -> list[Tool]:
    """
    List all available tools for Claude Desktop.

    IMPORTANT: We only expose high-level orchestrator tools here.
    The multi-agent system internally uses 31+ tools from server.py.
    This ensures all queries go through the proper AI routing and agent delegation.
    """
    return [
        Tool(
            name="process_query",
            description="""
THE MAIN ENTRY POINT for the multi-agent stock market system.

**IMPORTANT**: This tool handles ALL stock market operations internally. DO NOT attempt to:
- Create charts yourself using Python/matplotlib
- Query databases directly
- Generate visualizations manually

The tool AUTOMATICALLY handles chart generation, data retrieval, and analysis.

USE THIS TOOL FOR ALL STOCK MARKET QUERIES. The system will automatically:
1. Analyze query complexity using AI Router
2. Route to appropriate mode (AGENT for complex, DIRECT for simple)
3. Delegate to specialized agents if needed
4. Execute multi-step workflows
5. Return comprehensive responses with data/charts

CAPABILITIES (accessed via natural language queries):
- **Charts**: "Vẽ biểu đồ VCB 30 ngày", "Chart for FPT 7 days" → Interactive HTML charts auto-generated and opened in browser
- Stock Analysis: "Phân tích cổ phiếu VCB", "Analyze FPT stock"
- Stock Screening: "Tìm cổ phiếu ROE > 15%, PE < 20", "Find banking stocks"
- Investment Planning: "Tư vấn đầu tư 100 triệu", "Plan portfolio for growth"
- Stock Discovery: "Tìm cổ phiếu tiềm năng ngành công nghệ"
- Price Data: "Giá VCB hiện tại", "VCB price history"
- Predictions: "Dự đoán giá VCB 7 ngày tới"
- Alerts: "Tạo cảnh báo VCB > 90000", "Xem cảnh báo của tôi"
- Subscriptions: "Theo dõi HPG", "Danh sách cổ phiếu đang theo dõi"
- Financial Data: "Báo cáo tài chính VCB", "Balance sheet FPT"

**CHART GENERATION**: When user asks for charts, this tool:
1. Fetches historical stock data
2. Generates interactive HTML chart with Plotly
3. Saves to Downloads folder
4. Auto-opens in browser
5. Returns confirmation message

SPECIALIZED AGENTS (auto-selected based on query):
- AnalysisSpecialist: Deep stock analysis with technicals & fundamentals
- ScreenerSpecialist: Filter stocks by 80+ criteria
- InvestmentPlanner: Multi-step investment planning workflow
- DiscoverySpecialist: Find stocks matching investment profile
- AlertManager: Price alerts and notifications
- SubscriptionManager: Stock watchlist management

MODES:
- auto (default): AI decides between agent/direct - RECOMMENDED
- agent: Force complex multi-step reasoning
- direct: Force fast pattern-matching execution

**TRUST THE TOOL OUTPUT**: If the tool says a chart was created successfully, it was. Do not attempt to recreate it.
            """.strip(),
            inputSchema=ProcessQueryInput.model_json_schema()
        ),
        Tool(
            name="get_session_state",
            description="Get current session state including conversation history and execution metrics",
            inputSchema=GetSessionStateInput.model_json_schema()
        ),
        Tool(
            name="clear_session",
            description="Clear session to start fresh (clears conversation history and shared state)",
            inputSchema=ClearSessionInput.model_json_schema()
        ),
        Tool(
            name="get_system_status",
            description="Get system status: active sessions, queries processed, routing statistics, performance metrics",
            inputSchema=GetSystemStatusInput.model_json_schema()
        ),
        Tool(
            name="list_available_capabilities",
            description="List all capabilities the system can handle. Useful to understand what queries are supported.",
            inputSchema=ListAvailableCapabilitiesInput.model_json_schema()
        ),
    ]


# ============================================================
# TOOL HANDLERS
# ============================================================

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent | ImageContent | EmbeddedResource]:
    """Handle tool execution - routes everything through the multi-agent system"""
    logger.info(f"Tool called: {name} with arguments: {arguments}")

    try:
        if name == "process_query":
            # Main orchestrator entry point - THE CORE OF THE SYSTEM
            orch = await get_orchestrator()

            user_query = arguments.get("user_query")
            user_id = arguments.get("user_id", "claude_desktop_user")
            mode = arguments.get("mode", "auto")
            session_id = arguments.get("session_id")

            logger.info(f"Processing query: {user_query[:100]}... (mode: {mode}, user: {user_id})")

            # Collect all streaming events from the orchestrator
            full_response = []
            routing_info = None
            error_info = None
            chart_paths = {}  # Collect chart paths for ImageContent

            async for event in orch.process_query(
                user_query=user_query,
                user_id=user_id,
                mode=mode,
                session_id=session_id
            ):
                event_type = event.get("type")

                if event_type == "routing_decision":
                    routing_info = event.get("data", {})
                    logger.info(f"Routing decision: {routing_info}")

                elif event_type == "chunk":
                    chunk_data = event.get("data", "")
                    # Handle both string (from agent mode) and dict (from direct mode)
                    if isinstance(chunk_data, str):
                        full_response.append(chunk_data)
                    elif isinstance(chunk_data, dict):
                        # Direct mode returns dict - format it nicely
                        if "response" in chunk_data:
                            full_response.append(chunk_data["response"])
                        elif "text" in chunk_data:
                            full_response.append(chunk_data["text"])
                        else:
                            # Fallback: convert dict to readable format
                            full_response.append(json.dumps(chunk_data, ensure_ascii=False, indent=2))

                        # Extract html_paths if present (from chart requests)
                        if "html_paths" in chunk_data and chunk_data["html_paths"]:
                            chart_paths.update(chunk_data["html_paths"])
                            logger.info(f"HTML chart paths received: {chart_paths}")
                    else:
                        full_response.append(str(chunk_data))

                elif event_type == "complete":
                    final_data = event.get("data", {})
                    logger.info(f"Query completed: {final_data.get('status')}")

                elif event_type == "error":
                    error_info = event.get("data", {})
                    logger.error(f"Error during execution: {error_info}")

            # Format the response
            response_text = "".join(full_response)

            # Build final response for Claude Desktop
            final_response_parts = []

            # Add routing info if available (debug info)
            if routing_info and mode == "auto":
                final_response_parts.append(
                    f"🤖 **Routing Decision**: {routing_info.get('mode')} mode "
                    f"(confidence: {routing_info.get('confidence', 0):.2f})\n"
                )

            # Add main response
            final_response_parts.append(response_text)

            # Add chart info if generated
            if chart_paths:
                final_response_parts.append(
                    f"\n\n📊 **Charts Generated**: {len(chart_paths)} file(s) created and opened in browser"
                )

            # Add error info if any
            if error_info:
                final_response_parts.append(f"\n\n⚠️ **Error**: {error_info.get('error', 'Unknown error')}")

            # Join all parts into final text
            final_text = "\n".join(final_response_parts)

            # Return as simple text content (no JSON wrapper to avoid confusion)
            return [TextContent(type="text", text=final_text)]

        elif name == "get_session_state":
            session_id = arguments.get("session_id")

            orch = await get_orchestrator()

            # Get metrics if available
            metrics = {}
            if orch:
                try:
                    metrics = orch.get_metrics()
                except:
                    pass

            return [TextContent(type="text", text=json.dumps({
                "session_id": session_id,
                "orchestrator_initialized": orchestrator is not None,
                "metrics": metrics,
                "note": "Use process_query with session_id to maintain conversation context"
            }, ensure_ascii=False, indent=2))]

        elif name == "clear_session":
            session_id = arguments.get("session_id")

            # Clear agent history if available
            if orchestrator and orchestrator.agent:
                orchestrator.clear_agent_history(session_id)
                return [TextContent(type="text", text=json.dumps({
                    "status": "success",
                    "message": f"Session {session_id} history cleared"
                }))]
            else:
                return [TextContent(type="text", text=json.dumps({
                    "status": "info",
                    "message": "No active session to clear (agent not initialized yet)"
                }))]

        elif name == "get_system_status":
            include_metrics = arguments.get("include_metrics", True)

            status = {
                "status": "operational",
                "orchestrator_initialized": orchestrator is not None,
                "architecture": {
                    "type": "multi-agent",
                    "components": [
                        "AI Router (complexity analysis)",
                        "OrchestratorAgent (reasoning)",
                        "DirectExecutor (fast path)",
                        "6 Specialized Agents",
                        "31 MCP Tools"
                    ],
                    "supported_channels": ["Claude Desktop", "Discord", "Web UI"]
                }
            }

            if orchestrator and include_metrics:
                try:
                    status["metrics"] = orchestrator.get_metrics()
                    status["routing_analysis"] = orchestrator.get_routing_analysis()
                except Exception as e:
                    status["metrics_error"] = str(e)

            return [TextContent(type="text", text=json.dumps(status, ensure_ascii=False, indent=2))]

        elif name == "list_available_capabilities":
            category = arguments.get("category")

            capabilities = {
                "analysis": {
                    "description": "Deep stock analysis with technical and fundamental data",
                    "examples": [
                        "Phân tích cổ phiếu VCB",
                        "Analyze FPT stock with charts",
                        "Technical analysis HPG"
                    ],
                    "agent": "AnalysisSpecialist"
                },
                "screening": {
                    "description": "Filter stocks by 80+ criteria",
                    "examples": [
                        "Tìm cổ phiếu ROE > 15%, PE < 20",
                        "Find banking stocks with high dividend",
                        "Screen stocks by market cap > 10000B"
                    ],
                    "agent": "ScreenerSpecialist"
                },
                "planning": {
                    "description": "Investment planning with portfolio allocation",
                    "examples": [
                        "Tư vấn đầu tư 100 triệu vào ngành ngân hàng",
                        "Plan growth portfolio with moderate risk",
                        "Investment strategy for retirement"
                    ],
                    "agent": "InvestmentPlanner"
                },
                "discovery": {
                    "description": "Find potential stocks matching profile",
                    "examples": [
                        "Tìm cổ phiếu tiềm năng ngành công nghệ",
                        "Discover undervalued stocks",
                        "Find growth stocks with strong momentum"
                    ],
                    "agent": "DiscoverySpecialist"
                },
                "alerts": {
                    "description": "Price alerts and notifications",
                    "examples": [
                        "Tạo cảnh báo VCB > 90000",
                        "Alert me when HPG RSI > 70",
                        "List my alerts"
                    ],
                    "agent": "AlertManager / DirectExecutor"
                },
                "subscriptions": {
                    "description": "Stock watchlist management",
                    "examples": [
                        "Theo dõi cổ phiếu FPT",
                        "Unsubscribe from VCB",
                        "Show my watchlist"
                    ],
                    "agent": "SubscriptionManager / DirectExecutor"
                },
                "data": {
                    "description": "Stock data, financials, and predictions",
                    "examples": [
                        "Giá VCB hiện tại",
                        "Báo cáo tài chính FPT Q3/2025",
                        "Dự đoán giá VCB 7 ngày",
                        "Vẽ biểu đồ HPG 30 ngày"
                    ],
                    "agent": "DirectExecutor / AnalysisSpecialist"
                }
            }

            if category and category in capabilities:
                result = {category: capabilities[category]}
            else:
                result = capabilities

            return [TextContent(type="text", text=json.dumps({
                "capabilities": result,
                "total_tools": 31,
                "total_agents": 6,
                "note": "All capabilities are accessed through the process_query tool using natural language"
            }, ensure_ascii=False, indent=2))]

        else:
            raise ValueError(f"Unknown tool: {name}. Use 'process_query' for all stock market queries.")

    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}", exc_info=True)
        error_response = {
            "error": str(e),
            "tool": name,
            "type": type(e).__name__,
            "hint": "Use 'process_query' tool with natural language queries for all stock market operations"
        }
        return [TextContent(type="text", text=json.dumps(error_response, ensure_ascii=False, indent=2))]


async def main():
    """Run the MCP server"""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        logger.info("Stock Market Orchestrator MCP Server starting...")
        logger.info("This server provides access to the full multi-agent system")
        logger.info("Architecture: Claude Desktop -> orchestrator_server.py -> HybridOrchestrator -> 6 Agents -> 31 Tools")

        # Pre-initialize orchestrator at startup to avoid timeout on first query
        logger.info("Pre-initializing HybridOrchestrator...")
        try:
            await get_orchestrator()
            logger.info("Orchestrator pre-initialized successfully!")
        except Exception as e:
            logger.warning(f"Failed to pre-initialize orchestrator: {e}")

        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
