from dotenv import load_dotenv
from langgraph.errors import GraphRecursionError
load_dotenv()
import uuid
from agent.graph import app as agent_app
import os
import streamlit as st
if not os.environ.get("OPENAI_API_KEY"):
    st.error("未找到 OPENAI_API_KEY，请检查 .env 文件配置！")
    st.stop()

st.set_page_config(page_title="ARGUS 智能研报系统", page_icon="📈", layout="wide")
st.title("📈 ARGUS AI-Powered Equity Research")
st.caption("基于 LangGraph 多智能体架构的金融研报生成系统 (带防幻觉事实核查)")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("请输入你要查询的股票或研报需求 (例如: 对比 NVDA 和 MSFT 的最新财报营收和市盈率)"):

    # 记录并显示用户输入
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 准备调用 Agent
    with st.chat_message("assistant"):
        with st.status("🤖 ARGUS Agents 正在思考和执行...", expanded=True) as status_box:

            inputs = {"raw_query": prompt}
            config = {
                "configurable": {"thread_id": st.session_state.thread_id},
                "recursion_limit": 15
            }
            try:
                for output in agent_app.stream(inputs, config=config, stream_mode="updates"):
                    for node_name, state_update in output.items():
                        st.write(f"✅ **{node_name}** 节点执行完毕")
                        if node_name == "Query_Rewriter":
                            st.info(f"📝 重写后的查询: {state_update.get('rewritten_query', '')}")
                        elif node_name == "Supervisor":
                            st.write(f"👉 主管路由下一步至: `{state_update.get('next_worker', '')}`")
                        elif node_name == "Reviewer":
                            feedback = state_update.get("verification_feedback", "")
                            if feedback == "PASS":
                                st.success("🟢 事实核查通过！数据无冲突。")
                            else:
                                st.error(f"🔴 发现问题，打回重做: {feedback}")

                status_box.update(label="研报生成完毕", state="complete", expanded=False)

            except GraphRecursionError:
                status_box.update(label="触发系统级死循环熔断保护", state="error", expanded=True)
                st.error("🚨 系统警告：由于目标数据过于难找或数据源冲突，Agent 陷入了反复重试。系统已强行切断以保护资源。")
                st.info("已生成基于目前收集到的部分残缺数据的降级报告，请在下方查看。")

            except Exception as e:
                status_box.update(label="执行过程中出现异常", state="error", expanded=True)
                st.error(f"系统异常: {str(e)}")
                st.stop()

        final_state = agent_app.get_state(config).values

        if "final_report" in final_state:
            report_content = final_state["final_report"]
            st.markdown(report_content)
            st.session_state.messages.append({"role": "assistant", "content": report_content})
        else:
            st.warning("未能生成最终报告，请检查右侧侧边栏的状态总线数据。")

current_state = agent_app.get_state({"configurable": {"thread_id": st.session_state.thread_id}})

with st.sidebar:
    st.header("🛠️ 调试面板：状态总线 (AgentState)")
    st.caption(f"当前 Session Thread ID:\n`{st.session_state.thread_id}`")

    if current_state and current_state.values:
        state_data = current_state.values

        with st.expander("🧠 记忆与重写 (Memory)", expanded=False):
            st.markdown("**重写后的 Query:**")
            st.write(state_data.get("rewritten_query", "暂无"))
            st.markdown("**长期全局摘要 (Summary):**")
            st.info(state_data.get("memory_summary", "暂无"))
            st.markdown("**短期对话窗口 (Chat History):**")
            st.json(state_data.get("chat_history", []))

        with st.expander("🚦 调度与核查 (Control)", expanded=False):
            st.markdown("**执行计划 (Execution Plan):**")
            st.json(state_data.get("execution_plan", []))
            st.markdown(f"**打回重试次数 (Revision Count):** `{state_data.get('revision_count', 0)}`")
            st.markdown("**审核意见 (Verification Feedback):**")
            st.write(state_data.get("verification_feedback", "暂无"))

        with st.expander("📊 底层收集的数据 (Raw Data)", expanded=True):
            collected = state_data.get("collected_data", [])
            st.write(f"共收集到 {len(collected)} 条数据块。")
            st.json(collected)

    else:
        st.write("暂无运行状态数据，请在左侧发起查询。")