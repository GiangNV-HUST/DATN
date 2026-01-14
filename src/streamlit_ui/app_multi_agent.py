"""
Streamlit UI for Multi-Agent System

Uses MultiAgentOrchestrator with 8 Specialized Agents:
1. AnalysisSpecialist - Stock analysis
2. ScreenerSpecialist - Stock screening
3. AlertManager - Price alerts
4. InvestmentPlanner - Investment planning
5. DiscoverySpecialist - Stock discovery
6. SubscriptionManager - Subscriptions
7. MarketContextSpecialist - Market overview (VN-Index, sectors)
8. ComparisonSpecialist - Stock comparison

Features:
- AI-Powered routing (OpenAI GPT-4o-mini)
- OpenAI post-processing for beautiful responses (like Claude Desktop)
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
from openai import OpenAI

# Load environment
load_dotenv()

# Add project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.ai_agent_hybrid.hybrid_system.orchestrator.multi_agent_orchestrator import MultiAgentOrchestrator

# Initialize OpenAI client for post-processing
openai_client = OpenAI()


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

    if "use_openai_formatting" not in st.session_state:
        st.session_state.use_openai_formatting = True  # Enable by default

    if "openai_model" not in st.session_state:
        st.session_state.openai_model = "gpt-4o-mini"  # Fast and cheap

    if "quick_query" not in st.session_state:
        st.session_state.quick_query = None


# ==================== OPENAI POST-PROCESSING ====================

def format_response_with_openai(user_query: str, raw_response: str, specialist: str) -> str:
    """
    Use OpenAI to format and enhance the raw agent response.
    Similar to how Claude Desktop uses Claude AI to post-process MCP results.

    Args:
        user_query: Original user question
        raw_response: Raw output from specialist agent
        specialist: Name of the specialist that generated the response

    Returns:
        Formatted, user-friendly response
    """
    if not raw_response or len(raw_response.strip()) < 10:
        return raw_response

    system_prompt = """Ban la tro ly AI chuyen ve co phieu Viet Nam. Nhiem vu cua ban la format lai ket qua tu he thong Multi-Agent thanh cau tra loi tu nhien, de hieu cho nguoi dung.

QUY TAC QUAN TRONG:
1. GIU NGUYEN tat ca so lieu, ma co phieu, gia ca - KHONG duoc thay doi bat ky data nao
2. Format thanh markdown de hien thi dep (dung headers, bold, tables, lists)
3. Them phan tich/nhan xet ngan gon neu phu hop
4. Tra loi bang tieng Viet, tu nhien nhu dang noi chuyen
5. Neu data cho thay diem tot/xau, hay highlight ra
6. Neu co nhieu co phieu, co the dung bang de so sanh
7. Ket thuc bang 1-2 cau khuyen nghi hoac luu y neu phu hop
8. KHONG them thong tin khong co trong data goc
9. KHONG noi "Dua tren du lieu" hoac "Theo he thong" - tra loi truc tiep

VERIFY CALCULATIONS (RAT QUAN TRONG):
- Neu la ke hoach DCA: Tong dau tu = So tien moi thang x So thang
  Vi du: 5 trieu/thang x 12 thang = 60 trieu (KHONG PHAI 127 trieu)
- Neu so lieu trong raw_response SAI so voi phep tinh don gian, hay SUA LAI cho dung
- Tinh toan lai neu can thiet va hien thi so lieu DUNG

FORMAT OUTPUT:
- Su dung ## cho headers chinh
- Su dung **bold** cho ten co phieu va so lieu quan trong
- Su dung tables cho so sanh nhieu co phieu
- Su dung bullet points cho danh sach
- Giu response ngan gon, tap trung vao thong tin chinh"""

    user_prompt = f"""Cau hoi nguoi dung: "{user_query}"

Ket qua tu {specialist}:
{raw_response}

Hay format lai thanh cau tra loi tu nhien, de hieu.

LUU Y QUAN TRONG:
- Kiem tra lai cac phep tinh (dac biet la DCA: tong dau tu = so tien/thang x so thang)
- Neu so lieu SAI, hay tinh lai va hien thi so DUNG
- Giu nguyen cac so lieu khac neu chinh xac"""

    try:
        response = openai_client.chat.completions.create(
            model=st.session_state.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        return response.choices[0].message.content
    except Exception as e:
        # If OpenAI fails, return raw response
        print(f"OpenAI formatting error: {e}")
        return raw_response


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

async def process_query_async(user_query: str, status_placeholder=None):
    """Process user query through multi-agent system with streaming status updates"""

    if st.session_state.orchestrator is None:
        success = await initialize_orchestrator()
        if not success:
            return None

    try:
        # Process through orchestrator - collect streaming results
        full_response = []
        metadata = {
            "is_multi_agent": False,
            "execution_mode": "single",
            "tasks": [],
            "specialist_responses": {}
        }
        current_specialist = None
        current_task_id = None

        async for event in st.session_state.orchestrator.process_query(
            user_query=user_query,
            user_id=st.session_state.user_id,
            session_id=st.session_state.session_id
        ):
            event_type = event.get("type", "")

            if event_type == "routing_decision":
                data = event.get("data", {})
                metadata["specialist"] = data.get("specialist", "unknown")
                metadata["method"] = data.get("method", "unknown")
                metadata["routing_time"] = data.get("routing_time", 0)
                metadata["is_multi_agent"] = data.get("is_multi_agent", False)
                metadata["execution_mode"] = data.get("execution_mode", "single")
                metadata["tasks"] = data.get("tasks", [])
                metadata["reasoning"] = data.get("reasoning", "")

                # Update status for multi-agent
                if status_placeholder and metadata["is_multi_agent"]:
                    tasks_info = metadata["tasks"]
                    mode = metadata["execution_mode"]
                    mode_icon = "🔄" if mode == "sequential" else "⚡" if mode == "parallel" else "📌"
                    status_placeholder.info(f"{mode_icon} **Multi-Agent Mode**: {mode.upper()} - {len(tasks_info)} specialists")

            elif event_type == "task_start":
                # New task starting
                data = event.get("data", {})
                current_specialist = data.get("specialist", "unknown")
                current_task_id = data.get("task_id", "")

                if status_placeholder:
                    status_placeholder.info(f"🔄 **{current_specialist}** đang xử lý...")

            elif event_type == "task_complete":
                # Task finished
                data = event.get("data", {})
                task_id = data.get("task_id", current_task_id)
                specialist = data.get("specialist", current_specialist)

                if specialist and task_id:
                    metadata["specialist_responses"][task_id] = {
                        "specialist": specialist,
                        "status": "completed"
                    }

                if status_placeholder:
                    status_placeholder.success(f"✅ **{specialist}** hoàn thành")

            elif event_type == "chunk":
                chunk_data = event.get("data", "")
                task_id = event.get("task_id", current_task_id)
                specialist = event.get("specialist", current_specialist)

                if isinstance(chunk_data, dict):
                    chunk_text = chunk_data.get("response", str(chunk_data))
                    full_response.append(chunk_text)
                    if "tools_used" in chunk_data:
                        metadata["tools_used"] = chunk_data.get("tools_used", [])
                else:
                    full_response.append(str(chunk_data))

                # Track per-specialist responses for multi-agent
                if task_id and specialist:
                    if task_id not in metadata["specialist_responses"]:
                        metadata["specialist_responses"][task_id] = {
                            "specialist": specialist,
                            "chunks": []
                        }
                    if "chunks" in metadata["specialist_responses"][task_id]:
                        metadata["specialist_responses"][task_id]["chunks"].append(str(chunk_data))

            elif event_type == "status":
                # Status update from orchestrator
                if status_placeholder:
                    status_placeholder.info(event.get("data", "Processing..."))

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
                    full_response.append(f"⚠️ Loi: {error_data.get('error', 'Unknown error')}")
                else:
                    full_response.append(f"⚠️ Loi: {error_data}")

                if status_placeholder:
                    status_placeholder.error(f"❌ Error: {error_data}")

        return {
            "response": "".join(full_response),
            **metadata
        }

    except Exception as e:
        st.error(f"Error processing query: {e}")
        import traceback
        traceback.print_exc()
        return None


def process_query(user_query: str, status_placeholder=None):
    """Sync wrapper for async query processing"""
    return asyncio.run(process_query_async(user_query, status_placeholder))


# ==================== UI COMPONENTS ====================

def render_sidebar():
    """Render sidebar with settings and metrics"""

    with st.sidebar:
        st.title("Multi-Agent System")

        # OpenAI Formatting Settings
        st.subheader("AI Formatting")
        st.session_state.use_openai_formatting = st.toggle(
            "OpenAI Post-Processing",
            value=st.session_state.use_openai_formatting,
            help="Su dung OpenAI de format response dep hon (giong Claude Desktop)"
        )

        if st.session_state.use_openai_formatting:
            st.session_state.openai_model = st.selectbox(
                "Model",
                ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
                index=0,
                help="gpt-4o-mini: Nhanh, re. gpt-4o: Chat luong cao hon."
            )
            st.caption("OpenAI se format lai response tu Agent")
        else:
            st.caption("Hien thi raw output tu Agent")

        st.divider()

        # Specialist info
        st.subheader("8 Chuyen gia AI")
        st.markdown("""
        1. **AnalysisSpecialist** - Phan tich co phieu
        2. **ScreenerSpecialist** - Sang loc co phieu
        3. **AlertManager** - Quan ly canh bao
        4. **InvestmentPlanner** - Ke hoach dau tu
        5. **DiscoverySpecialist** - Tim co phieu tiem nang
        6. **SubscriptionManager** - Quan ly goi
        7. **MarketContextSpecialist** - Tong quan thi truong
        8. **ComparisonSpecialist** - So sanh co phieu
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
            is_multi_agent = metadata.get("is_multi_agent", False)

            with st.expander("Chi tiet xu ly", expanded=False):
                # Multi-agent badge
                if is_multi_agent:
                    mode = metadata.get("execution_mode", "single")
                    mode_icon = "🔄" if mode == "sequential" else "⚡" if mode == "parallel" else "📌"
                    st.success(f"{mode_icon} **Multi-Agent Mode**: {mode.upper()}")

                    # Show tasks/specialists involved
                    tasks = metadata.get("tasks", [])
                    if tasks:
                        specialists_list = [t.get("specialist", "unknown") if isinstance(t, dict) else str(t) for t in tasks]
                        st.info(f"🤖 Specialists: {' → '.join(specialists_list)}")

                    # Show reasoning
                    if metadata.get("reasoning"):
                        st.caption(f"💡 Routing: {metadata['reasoning']}")

                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    specialist = metadata.get("specialist_used") or metadata.get("specialist") or "unknown"
                    st.text(f"Specialist: {specialist}")

                with col2:
                    method = metadata.get("method_used") or metadata.get("method") or "unknown"
                    st.text(f"Method: {method}")

                with col3:
                    elapsed = metadata.get("elapsed_time") or 0
                    st.text(f"Time: {elapsed:.2f}s" if elapsed else "Time: N/A")

                with col4:
                    if metadata.get("formatted_by_openai"):
                        st.text("Format: OpenAI")
                    else:
                        st.text("Format: Raw")

                # Quality score
                quality = metadata.get("quality_score") or 0
                if quality and quality > 0:
                    st.text(f"Quality: {quality}/10")

                # Tools used
                if metadata.get("tools_used"):
                    # Convert any non-string items to strings
                    tools_list = [str(t) if not isinstance(t, str) else t for t in metadata['tools_used']]
                    st.text(f"Tools: {', '.join(tools_list)}")

                # Per-specialist responses for multi-agent
                specialist_responses = metadata.get("specialist_responses", {})
                if specialist_responses and len(specialist_responses) > 1:
                    st.divider()
                    st.caption("**Per-Specialist Results:**")
                    for task_id, resp_info in specialist_responses.items():
                        if isinstance(resp_info, dict):
                            sp_name = resp_info.get("specialist", task_id)
                            status = resp_info.get("status", "completed")
                            status_icon = "✅" if status == "completed" else "⏳"
                            st.text(f"{status_icon} {sp_name}")

            # Show raw response if formatted by OpenAI (separate expander, not nested)
            if metadata.get("formatted_by_openai") and metadata.get("raw_response"):
                with st.expander("Xem Raw Response (truoc khi format)", expanded=False):
                    st.code(metadata["raw_response"], language="markdown")


def render_chat_interface():
    """Render main chat interface"""

    st.title("AI Stock Advisor - Multi-Agent System")
    st.caption("8 chuyen gia AI san sang ho tro ban")

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
            # Status placeholder for streaming updates
            status_placeholder = st.empty()
            status_placeholder.info("🔍 Đang phân tích yêu cầu...")

            result = process_query(prompt, status_placeholder)

            if result:
                # Clear status placeholder
                status_placeholder.empty()

                raw_response = result.get("response", "")
                specialist = result.get("specialist_used") or result.get("specialist") or "unknown"
                is_multi_agent = result.get("is_multi_agent", False)

                # Apply OpenAI post-processing if enabled
                if st.session_state.use_openai_formatting and raw_response:
                    with st.spinner("OpenAI dang format response..."):
                        response = format_response_with_openai(prompt, raw_response, specialist)
                        formatted_by_openai = True
                else:
                    response = raw_response
                    formatted_by_openai = False

                # Display response
                st.markdown(response)

                # Store assistant message with metadata
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response,
                    "metadata": {
                        "specialist_used": specialist,
                        "method_used": result.get("method_used") or result.get("method"),
                        "elapsed_time": result.get("elapsed_time"),
                        "routing_time": result.get("routing_time"),
                        "quality_score": result.get("quality_score"),
                        "tools_used": result.get("tools_used", []),
                        "formatted_by_openai": formatted_by_openai,
                        "raw_response": raw_response if formatted_by_openai else None,
                        # Multi-agent metadata
                        "is_multi_agent": is_multi_agent,
                        "execution_mode": result.get("execution_mode", "single"),
                        "tasks": result.get("tasks", []),
                        "reasoning": result.get("reasoning", ""),
                        "specialist_responses": result.get("specialist_responses", {})
                    }
                })

                # Store metrics
                st.session_state.metrics_history.append({
                    "timestamp": datetime.now(),
                    "specialist": specialist,
                    "elapsed_time": result.get("elapsed_time"),
                    "is_multi_agent": is_multi_agent
                })

                # Rerun to show metadata expander
                st.rerun()

            else:
                status_placeholder.empty()
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
        **📌 SINGLE AGENT - 1 Chuyen gia:**

        **Phan tich (AnalysisSpecialist):**
        - Phan tich ky thuat co phieu VCB
        - Gia FPT hom nay?

        **Sang loc (ScreenerSpecialist):**
        - Top 10 co phieu thanh khoan cao
        - Tim co phieu P/E < 15

        **Tu van dau tu (InvestmentPlanner):**
        - Toi co 500 trieu muon dau tu
        - Lap ke hoach DCA cho FPT voi 5 trieu/thang trong 12 thang

        ---

        **🔄 MULTI-AGENT SEQUENTIAL - Nhieu chuyen gia lien tiep:**

        **Screen → Analysis:**
        - Top 5 co phieu ngan hang, phan tich chi tiet

        **Screen → Invest:**
        - Loc co phieu P/E < 15 sau do tu van dau tu 100 trieu

        **Analysis → Compare:**
        - Phan tich VCB va TCB roi so sanh xem cai nao tot hon

        ---

        **⚡ MULTI-AGENT PARALLEL - Nhieu chuyen gia dong thoi:**

        **Market || Discovery:**
        - Tong quan VN-Index va khuyen nghi co phieu tiem nang
        """)

        # Quick action buttons
        st.subheader("🚀 Thu nhanh:")
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("📊 Phan tich VCB", key="quick_vcb"):
                st.session_state.quick_query = "Phan tich co phieu VCB"
                st.rerun()

        with col2:
            if st.button("🔄 Screen + Analysis", key="quick_multi"):
                st.session_state.quick_query = "Top 5 co phieu ngan hang, phan tich chi tiet"
                st.rerun()

        with col3:
            if st.button("⚡ Market + Discovery", key="quick_parallel"):
                st.session_state.quick_query = "Tong quan VN-Index va khuyen nghi co phieu tiem nang"
                st.rerun()

    # Handle quick query from buttons
    if "quick_query" in st.session_state and st.session_state.quick_query:
        quick_query = st.session_state.quick_query
        st.session_state.quick_query = None  # Clear it

        # Add as user message and process
        st.session_state.messages.append({
            "role": "user",
            "content": quick_query
        })
        st.rerun()


if __name__ == "__main__":
    main()
