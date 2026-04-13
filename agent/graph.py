from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from .state import AgentState
from .nodes.memory_nodes import query_rewriter_node, memory_manager_node
from .nodes.supervisor import supervisor_node
from .nodes.reviewer import reviewer_node
from .nodes.synthesizer import synthesizer_node
from .nodes.workers.data_analyst import data_analyst_node
from .nodes.workers.market_analyst import market_analyst_node
from .nodes.workers.compliance_analyst import compliance_analyst_node

workflow = StateGraph(AgentState)
workflow.add_node("Query_Rewriter", query_rewriter_node)
workflow.add_node("Supervisor", supervisor_node)
workflow.add_node("Data_Analyst", data_analyst_node)
workflow.add_node("Market_Analyst", market_analyst_node)
workflow.add_node("Compliance_Analyst", compliance_analyst_node)
workflow.add_node("Reviewer", reviewer_node)
workflow.add_node("Synthesizer", synthesizer_node)
workflow.add_node("Memory_Manager", memory_manager_node)

def supervisor_router(state: AgentState) -> list[str]:
    """
    根据 Supervisor 写入的列表，触发 LangGraph 的并行执行。
    包含基于 Worker 身份的智能防死循环机制。
    """
    next_nodes = state.get("next_worker", ["Reviewer"])
    if isinstance(next_nodes, str):
        next_nodes = [next_nodes]

    if "Reviewer" in next_nodes:
        return ["Reviewer"]

    collected_data = state.get("collected_data", [])
    worked_agents = set()
    for item in collected_data:
        if isinstance(item, dict) and "worker" in item:
            worked_agents.add(item["worker"])

    valid_nodes = []
    for node in next_nodes:
        if node in ["Data_Analyst", "Market_Analyst", "Compliance_Analyst"]:
            if node in worked_agents:
                print(f"🚨 [Graph Router] 防死循环拦截：{node} 已经提交过数据，踢出本次任务队列！")
            else:
                valid_nodes.append(node)

    if not valid_nodes:
        print("🚨 [Graph Router] 所有派发路径均已执行或被拦截，强行收口流转至 Reviewer！")
        return ["Reviewer"]

    return valid_nodes
def reviewer_router(state: AgentState) -> str:
    """
    根据 Reviewer 的核查结果，决定是生成报告还是打回重做。
    """
    feedback = state.get("verification_feedback", "")
    revision_count = state.get("revision_count", 0)

    if feedback == "PASS":
        return "Synthesizer"
    elif revision_count >= 3:
        return "Synthesizer"
    else:
        return "Supervisor"

workflow.set_entry_point("Query_Rewriter")

workflow.add_edge("Query_Rewriter", "Supervisor")

workflow.add_conditional_edges(
    "Supervisor",
    supervisor_router,
    {
        "Data_Analyst": "Data_Analyst",
        "Market_Analyst": "Market_Analyst",
        "Compliance_Analyst": "Compliance_Analyst",
        "Reviewer": "Reviewer"
    }
)

workflow.add_edge("Data_Analyst", "Supervisor")
workflow.add_edge("Market_Analyst", "Supervisor")
workflow.add_edge("Compliance_Analyst", "Supervisor")

workflow.add_conditional_edges(
    "Reviewer",
    reviewer_router,
    {
        "Synthesizer": "Synthesizer",
        "Supervisor": "Supervisor"
    }
)

workflow.add_edge("Synthesizer", "Memory_Manager")

workflow.add_edge("Memory_Manager", END)

memory_saver = MemorySaver()

app = workflow.compile(checkpointer=memory_saver)