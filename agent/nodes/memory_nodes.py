from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from agent.state import AgentState
from agent.prompts import QUERY_REWRITER_PROMPT, MEMORY_MANAGER_PROMPT

llm = ChatOpenAI(model="gemini-3-flash", temperature=0)

def query_rewriter_node(state: AgentState) -> dict:
    print("\n" + "="*40)
    raw_query = state.get("raw_query", "")
    full_chat_history = state.get("chat_history", [])
    recent_history = full_chat_history[-4:] if len(full_chat_history) > 4 else full_chat_history
    messages = [
        SystemMessage(content=QUERY_REWRITER_PROMPT),
        HumanMessage(content=f"Chat History: {recent_history}\n\nNew Query: {raw_query}")
    ]
    response = llm.invoke(messages)
    rewritten_query = response.content.strip()
    print(f"✅ [Query Rewriter] 重写结果: {rewritten_query}")
    print("="*40 + "\n")
    return {
        "rewritten_query": rewritten_query,
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

    if len(chat_history) > MAX_MESSAGES:
        oldest_user_msg = chat_history.pop(0)
        oldest_assistant_msg = chat_history.pop(0)
        prompt = ChatPromptTemplate.from_template(MEMORY_MANAGER_PROMPT)
        chain = prompt | llm

        response = chain.invoke({
            "memory_summary": memory_summary,
            "user_msg": oldest_user_msg["content"],
            "assistant_msg": oldest_assistant_msg["content"]
        })

        memory_summary = response.content.strip()
        print("✅ [Memory Manager] 旧对话已压缩至全局摘要")

    return {
        "chat_history": chat_history,
        "memory_summary": memory_summary
    }