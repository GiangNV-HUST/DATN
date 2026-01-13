"""
Streamlit UI for Full Agent System (OpenAI Version)

Uses complete HybridOrchestratorOpenAI with:
- Intelligent routing (AGENT vs DIRECT mode)
- Access to 25 MCP tools
- All specialized agents
- Performance metrics
"""

import streamlit as st
import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# Load environment
load_dotenv()

# Add project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.ai_agent_hybrid.hybrid_system.orchestrator.main_orchestrator import HybridOrchestrator


# ==================== PAGE CONFIG ====================

st.set_page_config(
    page_title="AI Stock Advisor - Full Agent System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ==================== SESSION STATE ====================

def initialize_session_state():
    """Initialize session state variables"""

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "session_id" not in st.session_state:
        st.session_state.session_id = f"streamlit_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    if "user_id" not in st.session_state:
        st.session_state.user_id = "streamlit_user"

    if "orchestrator" not in st.session_state:
        st.session_state.orchestrator = None

    if "mcp_client" not in st.session_state:
        st.session_state.mcp_client = None

    if "metrics_history" not in st.session_state:
        st.session_state.metrics_history = []

    if "routing_enabled" not in st.session_state:
        st.session_state.routing_enabled = True


# ==================== ORCHESTRATOR INITIALIZATION ====================

async def initialize_orchestrator():
    """Initialize MCP client and orchestrator"""

    if st.session_state.orchestrator is None:
        with st.spinner("Đang khởi tạo hệ thống AI Agent..."):
            try:
                # Create orchestrator with DirectMCPClient mode (in-process, no subprocess)
                orchestrator = HybridOrchestrator(use_direct_client=True)
                await orchestrator.initialize()

                st.session_state.orchestrator = orchestrator
                st.session_state.mcp_client = orchestrator.mcp_client

                # Get number of available tools
                num_tools = len(orchestrator.mcp_client.available_tools) if hasattr(orchestrator.mcp_client, 'available_tools') else 0
                st.info(f"✅ HybridOrchestrator initialized with {num_tools} tools")

                st.success("✅ Agent system initialized successfully!")
                return True

            except Exception as e:
                st.error(f"❌ Failed to initialize agent system: {e}")
                import traceback
                st.code(traceback.format_exc())
                return False

    return True


# ==================== QUERY PROCESSING ====================

async def process_query_async(user_query: str):
    """Process user query through full agent system"""

    if st.session_state.orchestrator is None:
        success = await initialize_orchestrator()
        if not success:
            return None

    try:
        # Determine mode based on routing setting
        mode = "auto" if st.session_state.routing_enabled else "agent"

        # Process through orchestrator - collect streaming results
        full_response = []
        metadata = {}

        async for event in st.session_state.orchestrator.process_query(
            user_query=user_query,
            user_id=st.session_state.user_id,
            mode=mode,
            session_id=st.session_state.session_id
        ):
            event_type = event.get("type", "")

            if event_type == "routing_decision":
                metadata["mode"] = event["data"].get("mode", "unknown")
                metadata["routing_time"] = event["data"].get("routing_time", 0)
                metadata["confidence"] = event["data"].get("confidence", 0)

            elif event_type == "chunk":
                chunk_data = event.get("data", "")
                # Handle both string chunks (from agent mode) and dict results (from direct mode)
                if isinstance(chunk_data, dict):
                    # Direct mode returns dict with 'response' key
                    full_response.append(chunk_data.get("response", str(chunk_data)))
                    # Also capture tools_used from direct mode
                    if "tools_used" in chunk_data:
                        metadata["tools_used"] = chunk_data.get("tools_used", [])
                else:
                    full_response.append(str(chunk_data))

            elif event_type == "complete":
                metadata["execution_time"] = event["data"].get("execution_time", 0)
                metadata["total_time"] = event["data"].get("total_time", 0)
                metadata["tools_used"] = event["data"].get("tools_used", [])

        return {
            "response": "".join(full_response),
            **metadata
        }

    except Exception as e:
        st.error(f"Error processing query: {e}")
        import traceback
        traceback.print_exc()
        return None


def process_query(user_query: str):
    """Sync wrapper for async query processing"""
    return asyncio.run(process_query_async(user_query))


# ==================== UI COMPONENTS ====================

def render_sidebar():
    """Render sidebar with settings and metrics"""

    with st.sidebar:
        st.title("⚙️ Settings")

        # Routing toggle
        st.session_state.routing_enabled = st.checkbox(
            "Enable AI Routing",
            value=st.session_state.routing_enabled,
            help="Use AI to decide between AGENT and DIRECT modes"
        )

        st.divider()

        # Session info
        st.subheader("Session Info")
        st.text(f"Session: {st.session_state.session_id[-12:]}")
        st.text(f"User: {st.session_state.user_id}")
        st.text(f"Messages: {len(st.session_state.messages)}")

        st.divider()

        # Metrics
        if st.session_state.orchestrator:
            st.subheader("📊 System Metrics")

            metrics = st.session_state.orchestrator.get_metrics()

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Queries", metrics.get("total_queries", 0))
                st.metric("Agent Mode", metrics.get("agent_mode_count", 0))

            with col2:
                agent_pct = metrics.get("agent_mode_percentage", 0)
                st.metric("Agent %", f"{agent_pct:.1f}%")
                st.metric("Direct Mode", metrics.get("direct_mode_count", 0))

            # Average times
            avg_agent = metrics.get("avg_agent_time", 0)
            avg_direct = metrics.get("avg_direct_time", 0)
            avg_routing = metrics.get("avg_routing_time", 0)

            st.text(f"Avg Agent: {avg_agent:.2f}s")
            st.text(f"Avg Direct: {avg_direct:.2f}s")
            st.text(f"Avg Routing: {avg_routing:.2f}s")

            # Time saved
            time_saved = metrics.get("total_time_saved", 0)
            if time_saved > 0:
                st.success(f"Time saved: {time_saved:.1f}s")

            # Reset button
            if st.button("Reset Metrics"):
                st.session_state.orchestrator.reset_metrics()
                st.rerun()

        st.divider()

        # Clear conversation
        if st.button("Clear Conversation"):
            st.session_state.messages = []
            st.rerun()


def render_chat_message(message: dict):
    """Render a chat message with metadata"""

    role = message.get("role")
    content = message.get("content", "")

    with st.chat_message(role):
        st.markdown(content)

        # Show metadata for assistant messages
        if role == "assistant" and "metadata" in message:
            metadata = message["metadata"]

            with st.expander("🔍 Query Details", expanded=False):
                col1, col2, col3 = st.columns(3)

                with col1:
                    mode = metadata.get("mode", "unknown")
                    st.text(f"Mode: {mode.upper()}")

                with col2:
                    exec_time = metadata.get("execution_time", 0)
                    st.text(f"Execution: {exec_time:.2f}s")

                with col3:
                    total_time = metadata.get("total_time", 0)
                    st.text(f"Total: {total_time:.2f}s")

                # Routing decision
                if "routing_decision" in metadata:
                    st.text(f"Routing: {metadata['routing_decision']}")

                # Tools used
                if metadata.get("tools_used"):
                    st.text(f"Tools: {', '.join(metadata['tools_used'])}")


def render_chat_interface():
    """Render main chat interface"""

    st.title("📊 AI Stock Advisor - Full Agent System")
    st.caption("Powered by OpenAI with 25 MCP Tools")

    # Display chat messages
    for message in st.session_state.messages:
        render_chat_message(message)

    # Chat input
    if prompt := st.chat_input("Ask about stocks, analysis, portfolio planning..."):

        # Add user message
        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })

        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Process query
        with st.chat_message("assistant"):
            with st.spinner("Processing..."):
                result = process_query(prompt)

                if result:
                    response = result.get("response", "")

                    # Display response
                    st.markdown(response)

                    # Store assistant message with metadata
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response,
                        "metadata": {
                            "mode": result.get("mode"),
                            "execution_time": result.get("execution_time"),
                            "routing_time": result.get("routing_time"),
                            "total_time": result.get("total_time"),
                            "routing_decision": result.get("routing_decision"),
                            "tools_used": result.get("tools_used", [])
                        }
                    })

                    # Store metrics
                    st.session_state.metrics_history.append({
                        "timestamp": datetime.now(),
                        "mode": result.get("mode"),
                        "execution_time": result.get("execution_time"),
                        "total_time": result.get("total_time")
                    })

                    # Rerun to show metadata expander
                    st.rerun()

                else:
                    st.error("Failed to process query")


# ==================== MAIN ====================

def main():
    """Main application"""

    # Initialize session state
    initialize_session_state()

    # Render sidebar
    render_sidebar()

    # Render chat interface
    render_chat_interface()

    # Show example queries
    if len(st.session_state.messages) == 0:
        st.info("""
        **Example queries:**

        Simple queries (DIRECT mode):
        - Gia VCB?
        - VCB hom nay?
        - Tao canh bao VCB > 100000

        Complex queries (AGENT mode):
        - Phan tich VCB chi tiet
        - Tim co phieu tiem nang
        - Tu van dau tu 100 trieu
        - Loc co phieu P/E < 15 va ROE > 15%
        - Tao danh muc dau tu nganh ngan hang
        """)


if __name__ == "__main__":
    main()
