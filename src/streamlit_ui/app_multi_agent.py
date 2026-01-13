"""
Streamlit UI for Multi-Agent System

Uses MultiAgentOrchestrator with 6 Specialized Agents:
1. AnalysisSpecialist - Stock analysis
2. ScreenerSpecialist - Stock screening
3. AlertManager - Price alerts
4. InvestmentPlanner - Investment planning
5. DiscoverySpecialist - Stock discovery
6. SubscriptionManager - Subscriptions

Features:
- Intelligent routing to appropriate specialist
- Real-time streaming responses
- Specialist usage metrics
- Conversation memory
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

from src.ai_agent_hybrid.hybrid_system.orchestrator.multi_agent_orchestrator import MultiAgentOrchestrator


# ==================== PAGE CONFIG ====================

st.set_page_config(
    page_title="AI Stock Advisor - Multi-Agent System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ==================== SESSION STATE ====================

def initialize_session_state():
    """Initialize session state variables"""

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "session_id" not in st.session_state:
        st.session_state.session_id = f"streamlit_multi_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    if "user_id" not in st.session_state:
        st.session_state.user_id = "streamlit_user"

    if "orchestrator" not in st.session_state:
        st.session_state.orchestrator = None

    if "mcp_client" not in st.session_state:
        st.session_state.mcp_client = None

    if "metrics_history" not in st.session_state:
        st.session_state.metrics_history = []


# ==================== ORCHESTRATOR INITIALIZATION ====================

async def initialize_orchestrator():
    """Initialize MCP client and Multi-Agent orchestrator"""

    if st.session_state.orchestrator is None:
        with st.spinner("Dang khoi tao he thong Multi-Agent..."):
            try:
                # Create orchestrator with DirectMCPClient mode
                orchestrator = MultiAgentOrchestrator(use_direct_client=True)
                await orchestrator.initialize()

                st.session_state.orchestrator = orchestrator
                st.session_state.mcp_client = orchestrator.mcp_client

                # Get number of available tools
                num_tools = len(orchestrator.mcp_client.available_tools) if hasattr(orchestrator.mcp_client, 'available_tools') else 0
                num_specialists = len(orchestrator.specialists)

                st.info(f"Multi-Agent System: {num_specialists} specialists, {num_tools} tools")
                st.success("He thong Multi-Agent da san sang!")
                return True

            except Exception as e:
                st.error(f"Loi khoi tao Multi-Agent: {e}")
                import traceback
                st.code(traceback.format_exc())
                return False

    return True


# ==================== QUERY PROCESSING ====================

async def process_query_async(user_query: str):
    """Process user query through multi-agent system"""

    if st.session_state.orchestrator is None:
        success = await initialize_orchestrator()
        if not success:
            return None

    try:
        # Process through orchestrator - collect streaming results
        full_response = []
        metadata = {}

        async for event in st.session_state.orchestrator.process_query(
            user_query=user_query,
            user_id=st.session_state.user_id,
            session_id=st.session_state.session_id
        ):
            event_type = event.get("type", "")

            if event_type == "routing_decision":
                metadata["specialist"] = event["data"].get("specialist", "unknown")
                metadata["method"] = event["data"].get("method", "unknown")
                metadata["routing_time"] = event["data"].get("routing_time", 0)

            elif event_type == "chunk":
                chunk_data = event.get("data", "")
                if isinstance(chunk_data, dict):
                    full_response.append(chunk_data.get("response", str(chunk_data)))
                    if "tools_used" in chunk_data:
                        metadata["tools_used"] = chunk_data.get("tools_used", [])
                else:
                    full_response.append(str(chunk_data))

            elif event_type == "complete":
                data = event.get("data", {})
                if isinstance(data, dict):
                    if "response" in data:
                        full_response = [data.get("response", "")]
                    metadata["elapsed_time"] = data.get("elapsed_time", 0)
                    metadata["quality_score"] = data.get("quality_score", 0)
                    metadata["tools_used"] = data.get("tools_used", [])
                    metadata["specialist_used"] = data.get("specialist_used", "")
                    metadata["method_used"] = data.get("method_used", "")

            elif event_type == "error":
                error_data = event.get("data", {})
                if isinstance(error_data, dict):
                    full_response.append(f"Loi: {error_data.get('error', 'Unknown error')}")
                else:
                    full_response.append(f"Loi: {error_data}")

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
        st.title("Multi-Agent System")

        # Specialist info
        st.subheader("6 Chuyen gia")
        st.markdown("""
        1. **AnalysisSpecialist** - Phan tich co phieu
        2. **ScreenerSpecialist** - Sang loc co phieu
        3. **AlertManager** - Quan ly canh bao
        4. **InvestmentPlanner** - Ke hoach dau tu
        5. **DiscoverySpecialist** - Tim co phieu tiem nang
        6. **SubscriptionManager** - Quan ly goi
        """)

        st.divider()

        # Session info
        st.subheader("Session Info")
        st.text(f"Session: {st.session_state.session_id[-12:]}")
        st.text(f"User: {st.session_state.user_id}")
        st.text(f"Messages: {len(st.session_state.messages)}")

        st.divider()

        # Metrics
        if st.session_state.orchestrator:
            st.subheader("Specialist Usage")

            metrics = st.session_state.orchestrator.get_metrics()
            specialist_usage = metrics.get("specialist_usage", {})

            for name, count in specialist_usage.items():
                short_name = name.replace("Specialist", "").replace("Manager", "")
                st.metric(short_name, count)

            st.divider()

            # Total queries
            st.metric("Total Queries", metrics.get("total_queries", 0))

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

            with st.expander("Chi tiet xu ly", expanded=False):
                col1, col2, col3 = st.columns(3)

                with col1:
                    specialist = metadata.get("specialist_used", "unknown")
                    st.text(f"Specialist: {specialist}")

                with col2:
                    method = metadata.get("method_used", "unknown")
                    st.text(f"Method: {method}")

                with col3:
                    elapsed = metadata.get("elapsed_time", 0)
                    st.text(f"Time: {elapsed:.2f}s")

                # Quality score
                quality = metadata.get("quality_score", 0)
                if quality > 0:
                    st.text(f"Quality: {quality}/10")

                # Tools used
                if metadata.get("tools_used"):
                    st.text(f"Tools: {', '.join(metadata['tools_used'])}")


def render_chat_interface():
    """Render main chat interface"""

    st.title("AI Stock Advisor - Multi-Agent System")
    st.caption("6 chuyen gia AI san sang ho tro ban")

    # Display chat messages
    for message in st.session_state.messages:
        render_chat_message(message)

    # Chat input
    if prompt := st.chat_input("Hoi ve co phieu, phan tich, tu van dau tu..."):

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
            with st.spinner("Dang xu ly..."):
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
                            "specialist_used": result.get("specialist_used") or result.get("specialist"),
                            "method_used": result.get("method_used") or result.get("method"),
                            "elapsed_time": result.get("elapsed_time"),
                            "routing_time": result.get("routing_time"),
                            "quality_score": result.get("quality_score"),
                            "tools_used": result.get("tools_used", [])
                        }
                    })

                    # Store metrics
                    st.session_state.metrics_history.append({
                        "timestamp": datetime.now(),
                        "specialist": result.get("specialist_used") or result.get("specialist"),
                        "elapsed_time": result.get("elapsed_time")
                    })

                    # Rerun to show metadata expander
                    st.rerun()

                else:
                    st.error("Khong the xu ly yeu cau")


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
        **Vi du cau hoi:**

        **Phan tich (AnalysisSpecialist):**
        - Phan tich ky thuat co phieu VCB
        - Gia FPT hom nay?
        - So sanh VCB va TCB

        **Sang loc (ScreenerSpecialist):**
        - Top 10 co phieu thanh khoan cao
        - Tim co phieu P/E < 15 va ROE > 15%

        **Tu van dau tu (InvestmentPlanner):**
        - Toi co 500 trieu muon dau tu
        - Tao ke hoach DCA cho VNM

        **Tim kiem (DiscoverySpecialist):**
        - Tim co phieu tiem nang nganh cong nghe
        - Co phieu nao dang duoc khuyen nghi?
        """)


if __name__ == "__main__":
    main()
