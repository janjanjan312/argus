import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from agent.state import AgentState
from agent.prompts import REVIEWER_PROMPT


llm = ChatOpenAI(model="gemini-3-flash", temperature=0)
def reviewer_node(state: AgentState) -> dict:
    """
    事实核查与防幻觉审查员
    负责校验底层的 collected_data 是否能充分且无矛盾地回答用户的 rewritten_query。
    """
    print("\n" + "="*40)
    print("🕵️ [Reviewer] 开始执行事实核查...")

    rewritten_query = state.get("rewritten_query", "")
    collected_data = state.get("collected_data", [])
    current_revision = state.get("revision_count", 0)

    if not collected_data:
        print("❌ [Reviewer] 拦截：未收集到任何底层数据。")
        return {
            "verification_feedback": "No data collected. Please assign a worker to fetch data.",
            "revision_count": current_revision + 1
        }

    data_str = json.dumps(collected_data, ensure_ascii=False)
    prompt = ChatPromptTemplate.from_template(REVIEWER_PROMPT)
    chain = prompt | llm

    response = chain.invoke({
        "rewritten_query": rewritten_query,
        "collected_data": data_str
    })

    feedback = response.content.strip()
    # 清理反馈，移除引号和空白字符
    clean_feedback = feedback.strip(' "\'\n.').upper()

    if "UNDERSTOOD" in clean_feedback or "PLEASE PROVIDE" in clean_feedback:
        print("⚠️ [Reviewer] 模型未进入执行模式...")
        return {
            "verification_feedback": "The reviewer failed to analyze. Retrying with stricter instructions.",
            "revision_count": current_revision + 1
        }

    # 修复：检查 PASS 应该在清理后进行，且只检查一次
    if clean_feedback == "PASS":
        print("🟢 [Reviewer] 核查通过！数据无冲突。")
        return {"verification_feedback": "PASS"}
    else:
        print(f"🔴 [Reviewer] 发现问题，打回重做。意见：\n   {feedback}")
        return {
            "verification_feedback": feedback,
            "revision_count": current_revision + 1
        }