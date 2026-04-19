from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from agent.state import AgentState
from agent.prompts import QUERY_REWRITER_PROMPT, MEMORY_MANAGER_PROMPT

llm = ChatOpenAI(model="gemini-3-flash", temperature=0)

def query_rewriter_node(state: AgentState) -> dict:
    print("\n" + "="*40)
    raw_query = state.get("raw_query", "")
    full_chat_history = state.get("chat_history", [])
    memory_summary = state.get("memory_summary", "")

    # 改进：构建更完整的上下文提示
    recent_history = full_chat_history[-4:] if len(full_chat_history) > 4 else full_chat_history

    # 使用 ChatPromptTemplate 正确处理提示模板
    prompt = ChatPromptTemplate.from_template(QUERY_REWRITER_PROMPT)
    chain = prompt | llm

    try:
        response = chain.invoke({
            "memory_summary": memory_summary or "暂无历史记忆",
            "chat_history": str(recent_history) if recent_history else "暂无",
            "raw_query": raw_query
        })
        rewritten_query = response.content.strip()
        print(f"✅ [Query Rewriter] 重写结果: {rewritten_query}")
        print("="*40 + "\n")
        return {
            "rewritten_query": rewritten_query,
            "collected_data": "CLEAR",
            "revision_count": 0,
            "worker_call_counts": {}
        }
    except Exception as e:
        print(f"❌ [Query Rewriter] 执行失败: {e}")
        print("="*40 + "\n")
        # 降级处理：直接使用原始查询
        return {
            "rewritten_query": raw_query,
            "collected_data": "CLEAR",
            "revision_count": 0,
            "worker_call_counts": {}
        }
def memory_manager_node(state: AgentState) -> dict:
    """
    记忆管理（系统的出口）
    负责在生成最终报告后，更新滑动窗口（chat_history）和全局摘要（memory_summary）。
    """
    raw_query = state.get("raw_query", "")
    final_report = state.get("final_report", "")
    chat_history = state.get("chat_history", [])
    memory_summary = state.get("memory_summary", "")

    chat_history.append({"role": "user", "content": raw_query})
    chat_history.append({"role": "assistant", "content": final_report})

    MAX_MESSAGES = 4

    # 修复：添加边界检查，确保 chat_history 有足够的消息对
    if len(chat_history) > MAX_MESSAGES and len(chat_history) >= 2:
        oldest_user_msg = chat_history.pop(0)
        oldest_assistant_msg = chat_history.pop(0)

        # 验证是否确实是 user/assistant 对
        if oldest_user_msg.get("role") == "user" and oldest_assistant_msg.get("role") == "assistant":
            prompt = ChatPromptTemplate.from_template(MEMORY_MANAGER_PROMPT)
            chain = prompt | llm

            response = chain.invoke({
                "memory_summary": memory_summary,
                "user_msg": oldest_user_msg["content"],
                "assistant_msg": oldest_assistant_msg["content"]
            })

            memory_summary = response.content.strip()
            print("✅ [Memory Manager] 旧对话已压缩至全局摘要")
        else:
            # 恢复消息，防止状态不一致
            chat_history.insert(0, oldest_user_msg)
            chat_history.insert(0, oldest_assistant_msg)
            print("⚠️ [Memory Manager] 消息对不匹配，跳过压缩")

    return {
        "chat_history": chat_history,
        "memory_summary": memory_summary
    }