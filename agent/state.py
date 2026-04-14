# l3_agent/state.py

from typing import TypedDict, List, Dict, Any, Annotated
import operator

def manage_collected_data(existing_data: list, new_data: Any) -> list:
    if new_data == "CLEAR":
        return []
    if isinstance(new_data, list):
        return existing_data + new_data
    return existing_data + [new_data]
class AgentState(TypedDict):
    """
    ARGUS 系统 L3 Agent 的全局状态定义。
    所有的节点只能读取或修改这里定义的字段。
    """
    raw_query: str
    rewritten_query: str
    chat_history: List[Dict[str, str]]
    memory_summary: str
    execution_plan: List[str]
    next_worker: str
    revision_count: int
    collected_data: Annotated[list, manage_collected_data]
    worker_call_counts: dict
    verification_feedback: str
    final_report: str