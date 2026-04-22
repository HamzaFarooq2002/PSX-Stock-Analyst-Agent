import streamlit as st
import datetime
from google.genai.types import Content, Part
from google.adk.runners import InMemoryRunner
import sys
from dotenv import load_dotenv

# Reconfigure stdout to handle emojis in Windows terminal (if running locally)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables
load_dotenv()

# --- Config ---
MAX_MESSAGES_PER_DAY = 20
COOLDOWN_SECONDS = 5
APP_NAME = "psx_analyst"

st.set_page_config(
    page_title="PSX Stock Analyst",
    page_icon="📈",
    layout="wide",
)

# --- App Initialization ---
@st.cache_resource
def init_runner():
    """Cache runner + agent to avoid re-auth on every Streamlit rerun."""
    from agent import root_agent
    runner = InMemoryRunner(agent=root_agent, app_name=APP_NAME)
    return runner

# --- Session Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I am your AI stock analyst for the Pakistan Stock Exchange. Ask me about a stock's price, fundamentals, news, or comparison.", "tools": []}
    ]

if "session_id" not in st.session_state:
    import asyncio
    # Properly create the session in ADK database using asyncio sync wrapper
    runner = init_runner()
    sess = asyncio.run(runner.session_service.create_session(
        app_name=APP_NAME, user_id="streamlit_user"
    ))
    st.session_state.session_id = sess.id

if "rate_limit" not in st.session_state:
    st.session_state.rate_limit = {
        "last_request_time": None,
        "messages_today": 0,
        "last_reset": datetime.datetime.now().date()
    }

# --- Rate Limiter ---
def check_rate_limit() -> tuple[bool, str]:
    now = datetime.datetime.now()
    state = st.session_state.rate_limit
    
    # Reset daily counter at midnight
    if now.date() > state["last_reset"]:
        state["messages_today"] = 0
        state["last_reset"] = now.date()
    
    # Daily cap
    if state["messages_today"] >= MAX_MESSAGES_PER_DAY:
        return False, f"🚫 Daily limit ({MAX_MESSAGES_PER_DAY}) reached. Please come back tomorrow!"
    
    # Cooldown
    if state["last_request_time"]:
        elapsed = (now - state["last_request_time"]).total_seconds()
        if elapsed < COOLDOWN_SECONDS:
            remaining = int(COOLDOWN_SECONDS - elapsed)
            return False, f"⏳ Please wait {remaining}s before sending another message."
    
    # Allow
    state["last_request_time"] = now
    state["messages_today"] += 1
    return True, "OK"

# --- Main App Execution ---
runner = init_runner()

# Sidebar
with st.sidebar:
    st.title("📈 PSX Stock Analyst")
    st.markdown("An AI assistant specialized in the **Pakistan Stock Exchange**.")
    
    # Rate limit display
    st.subheader("Usage")
    msgs = st.session_state.rate_limit["messages_today"]
    st.progress(msgs / MAX_MESSAGES_PER_DAY)
    st.caption(f"{msgs} / {MAX_MESSAGES_PER_DAY} daily messages used.")
    
    st.subheader("Example Queries")
    examples = [
        "What is the current price of OGDC?",
        "Are the fundamentals for SYS looking good?",
        "Compare HUBC and KAPCO.",
        "Any recent news for Lucky Cement?"
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True):
            st.session_state.example_query = ex
            
    if st.button("Clear Chat", type="primary", use_container_width=True):
        st.session_state.messages = [
            {"role": "assistant", "content": "Chat cleared. What else can I help you with?", "tools": []}
        ]
        st.rerun()

# --- Chat Rendering ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "tools" in msg and msg["tools"]:
            with st.expander("🔧 Tools Used"):
                for tool in msg["tools"]:
                    st.write(f"- `{tool['name']}({tool['args']})`")

# --- User Input & Processing ---
# Use example query if clicked, otherwise get from chat input
if "example_query" in st.session_state:
    user_input = st.session_state.example_query
    del st.session_state.example_query
else:
    user_input = st.chat_input("Ask about a stock...")

if user_input:
    # 1. Add user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)
    
    # 2. Check Rate Limits
    allowed, message = check_rate_limit()
    if not allowed:
        st.error(message)
        st.stop()
    
    # 3. Agent Execution
    with st.chat_message("assistant"):
        with st.spinner("Analyzing data..."):
            response_text = ""
            tool_calls = []
            
            try:
                # Synchronous execution
                msg_content = Content(parts=[Part(text=user_input)], role="user")
                
                # Iterate through generator
                for event in runner.run(
                    user_id="streamlit_user", 
                    session_id=st.session_state.session_id, 
                    new_message=msg_content
                ):
                    if event.content and event.content.parts:
                        for part in event.content.parts:
                            if part.text:
                                response_text += part.text
                            if part.function_call:
                                tool_calls.append({
                                    "name": part.function_call.name,
                                    "args": part.function_call.args,
                                })
                                
                if response_text:
                    st.write(response_text)
                
                if tool_calls:
                    with st.expander("🔧 Tools Used"):
                        for tool in tool_calls:
                            st.write(f"- `{tool['name']}({tool['args']})`")
                            
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": response_text,
                    "tools": tool_calls
                })
                
            except Exception as e:
                error_msg = "An error occurred while fetching data. Please try again later."
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
                # Don't show stack traces to end users, log them natively instead
                pass
