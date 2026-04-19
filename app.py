from dotenv import load_dotenv
from langgraph.errors import GraphRecursionError
load_dotenv()
import uuid
from agent.graph import app as agent_app
import os
import streamlit as st

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ARGUS · AI Equity Research",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
:root {
    --bg: #f7f8fa;
    --surface: #ffffff;
    --border: #e6eaf0;
    --text: #1f2937;
    --muted: #6b7280;
    --accent: #315efb;
    --shadow: 0 4px 18px rgba(15, 23, 42, 0.04);
}

html, body, [class*="css"] {
    font-family: 'Inter', 'SF Pro Display', 'Segoe UI', sans-serif;
    color: var(--text);
}

[data-testid="stAppViewContainer"] {
    background: var(--bg);
}

[data-testid="stHeader"] {
    background: rgba(255, 255, 255, 0.0);
}

[data-testid="stMainBlockContainer"] {
    max-width: 1180px;
    padding-top: 2rem;
    padding-bottom: 2.5rem;
}

.hero {
    padding: 0.25rem 0 1rem;
    color: var(--text);
}

.hero-badge {
    display: none;
}

.hero h1 {
    margin: 0;
    font-size: 2.15rem;
    font-weight: 700;
    letter-spacing: -0.04em;
}

.hero p {
    margin: 0.45rem 0 0;
    max-width: 760px;
    font-size: 0.98rem;
    line-height: 1.65;
    color: var(--muted);
}

.simple-block,
.report-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1rem 1.1rem;
    box-shadow: var(--shadow);
}

.report-card {
    margin-top: 0.75rem;
}

.report-card h3 {
    margin: 0 0 0.3rem;
    font-size: 1rem;
    font-weight: 700;
}

.report-card p,
.muted {
    margin: 0;
    color: var(--muted);
    line-height: 1.65;
}

[data-testid="stChatMessage"] {
    padding: 0.15rem 0;
    margin-bottom: 0.4rem;
}

[data-testid="stChatMessageContent"] {
    background: #ffffff;
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 0.9rem 1rem;
    box-shadow: var(--shadow);
}

[data-testid="stStatusWidget"],
[data-testid="stExpander"] {
    border-radius: 14px;
    border: 1px solid var(--border);
    box-shadow: var(--shadow);
}

[data-testid="stChatInput"] {
    margin-top: 0.4rem;
}

[data-testid="stChatInput"] textarea {
    border-radius: 12px !important;
    border: 1px solid var(--border) !important;
    background: #ffffff !important;
}

[data-testid="stSidebar"] > div:first-child {
    background: #fafbfc;
    border-left: 1px solid var(--border);
    padding-top: 1.2rem;
}

[data-testid="stSidebar"] [data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 0.7rem 0.8rem;
}

#MainMenu, footer {
    visibility: hidden;
}

hr {
    border-color: rgba(128, 146, 176, 0.16);
}
</style>
""", unsafe_allow_html=True)

# ── API Key guard ─────────────────────────────────────────────────────────────
if not os.environ.get("OPENAI_API_KEY"):
    st.error("⚠️ OPENAI_API_KEY not found. Please check your .env configuration.")
    st.stop()

# ── Hero banner ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>📈 ARGUS</h1>
  <p>AI-powered equity research for comparing filings, market signals, and verified insights.</p>
</div>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if not st.session_state.messages:
    st.markdown('<div class="simple-block"><p class="muted">Try a focused prompt such as comparing two companies, summarizing a recent filing, or reviewing valuation and risk changes.</p></div>', unsafe_allow_html=True)
    st.markdown("- Compare NVDA and MSFT on revenue growth, margins, and valuation.")
    st.markdown("- Summarize the latest 10-K for META and highlight the key business risks.")
# ── Chat history ──────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Chat input ────────────────────────────────────────────────────────────────
if prompt := st.chat_input("Ask about a stock or request an equity report  (e.g. Compare NVDA and MSFT latest revenue and P/E ratio)"):

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.status("🤖 ARGUS Agents are thinking and executing...", expanded=True) as status_box:

            inputs = {"raw_query": prompt}
            config = {
                "configurable": {"thread_id": st.session_state.thread_id},
                "recursion_limit": 15,
            }
            try:
                for output in agent_app.stream(inputs, config=config, stream_mode="updates"):
                    for node_name, state_update in output.items():
                        st.write(f"✅ **{node_name}** node completed")
                        if node_name == "Query_Rewriter":
                            st.info(f"📝 Rewritten query: {state_update.get('rewritten_query', '')}")
                        elif node_name == "Supervisor":
                            st.write(f"👉 Supervisor routed next step to: `{state_update.get('next_worker', '')}`")
                        elif node_name == "Reviewer":
                            feedback = state_update.get("verification_feedback", "")
                            if feedback == "PASS":
                                st.success("🟢 Fact-check passed — no data conflicts detected.")
                            else:
                                st.error(f"🔴 Issues found, sending back for revision: {feedback}")

                status_box.update(label="✅ Report generation complete", state="complete", expanded=False)

            except GraphRecursionError:
                status_box.update(label="🚨 Recursion limit reached — circuit breaker triggered", state="error", expanded=True)
                st.error("**System Warning:** The agent entered a retry loop due to conflicting or unavailable data. Execution was forcibly halted to protect resources.")
                st.info("A degraded report based on partially collected data is shown below.")

            except Exception as e:
                status_box.update(label="❌ An error occurred during execution", state="error", expanded=True)
                st.error(f"System error: {str(e)}")
                st.stop()

        final_state = agent_app.get_state(config).values

        if "final_report" in final_state:
            report_content = final_state["final_report"]
            st.markdown('<div class="report-card"><h3>Research report</h3><p>The verified synthesis from the agent workflow is shown below.</p></div>', unsafe_allow_html=True)
            st.markdown(report_content)
            st.session_state.messages.append({"role": "assistant", "content": report_content})
        else:
            st.warning("⚠️ No final report was generated. Please review the debug panel in the sidebar.")

# ── Sidebar debug panel ───────────────────────────────────────────────────────
current_state = agent_app.get_state({"configurable": {"thread_id": st.session_state.thread_id}})

with st.sidebar:
    st.markdown("## 🛠️ Debug Panel")
    st.caption(f"Session Thread ID:\n`{st.session_state.thread_id}`")
    st.divider()

    if current_state and current_state.values:
        state_data = current_state.values
        collected = state_data.get("collected_data", [])
        verification_feedback = state_data.get("verification_feedback", "—")
        revision = state_data.get("revision_count", 0)

        metric_col1, metric_col2 = st.columns(2)
        with metric_col1:
            st.metric("Data chunks", len(collected))
        with metric_col2:
            st.metric("Revisions", revision)
        if verification_feedback == "PASS":
            st.success("Fact-check status: PASS")
        else:
            st.info(f"Latest reviewer feedback: {verification_feedback}")

        with st.expander("🧠 Memory & Query Rewriting", expanded=False):
            st.markdown("**Rewritten Query:**")
            st.write(state_data.get("rewritten_query", "—"))
            st.markdown("**Long-term Global Summary:**")
            st.info(state_data.get("memory_summary", "No summary yet."))
            st.markdown("**Short-term Chat Window:**")
            st.json(state_data.get("chat_history", []))

        with st.expander("🚦 Scheduling & Verification", expanded=False):
            st.markdown("**Execution Plan:**")
            st.json(state_data.get("execution_plan", []))
            st.markdown(f"**Revision Count:** `{revision}`")
            st.markdown("**Verification Feedback:**")
            st.write(verification_feedback)

        with st.expander("📊 Collected Raw Data", expanded=True):
            st.write(f"**{len(collected)}** data chunk(s) collected.")
            st.json(collected)

    else:
        st.info("No active runtime state yet. Submit a research query to populate details here.")
