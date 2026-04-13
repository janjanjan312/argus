import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from agent.state import AgentState
from agent.prompts import SUPERVISOR_PROMPT

llm = ChatOpenAI(model="gemini-3-flash", temperature=0)

def parse_json_output(response_text: str) -> dict:
    """
    清洗大模型可能附带的 Markdown 标记（如 ```json ... ```），确保安全解析。
    """
    text = response_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]

    try:
        return json.loads(text.strip())
    except json.JSONDecodeError as e:
        print(f"❌ [Supervisor] JSON 解析失败. 原始输出: {response_text}")
        return {"execution_plan": ["解析失败，强制中断"], "next_worker": "Reviewer"}

def supervisor_node(state: AgentState) -> dict:
    """
    主控调度器
    负责根据用户问题和当前收集的数据，决定下一步由哪个 Worker 收集数据，或者转交审查。
    """
    rewritten_query = state.get("rewritten_query", "")
    collected_data = state.get("collected_data", [])
    verification_feedback = state.get("verification_feedback", "")
    if not rewritten_query:
        print("⚠️ [Supervisor] 未收到有效查询，暂停调度。")
        return {"next_worker": "Reviewer"}
    data_str = json.dumps(collected_data, ensure_ascii=False) if collected_data else "暂无收集到的数据"
    feedback_str = verification_feedback if verification_feedback else "无反馈（初次执行或上一轮通过）"
    prompt = ChatPromptTemplate.from_template(SUPERVISOR_PROMPT)
    chain = prompt | llm

    response = chain.invoke({
        "rewritten_query": rewritten_query,
        "collected_data": data_str,
        "verification_feedback": feedback_str
    })

    parsed_output = parse_json_output(response.content)

    plan = parsed_output.get("execution_plan", [])
    next_workers = parsed_output.get("next_workers", ["Reviewer"])

    return {
        "execution_plan": plan,
        "next_worker": next_workers,
        "verification_feedback": ""
    }