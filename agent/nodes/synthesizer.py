import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from agent.state import AgentState
from agent.prompts import SYNTHESIZER_PROMPT

llm = ChatOpenAI(model="gemini-3-flash", temperature=0.2)

def synthesizer_node(state: AgentState) -> dict:
    """
    最终研报生成器
    负责将所有通过核查的collected_data汇总，撰写成带有溯源引用的专业研报。
    """
    print("\n" + "="*40)
    print("✍️ [Synthesizer] 正在撰写最终研报...")

    rewritten_query = state.get("rewritten_query", "")
    collected_data = state.get("collected_data", [])

    data_str = json.dumps(collected_data, ensure_ascii=False)

    prompt = ChatPromptTemplate.from_template(SYNTHESIZER_PROMPT)
    chain = prompt | llm

    response = chain.invoke({
        "rewritten_query": rewritten_query,
        "collected_data": data_str
    })

    final_report_text = response.content.strip()

    print("✅ [Synthesizer] 研报撰写完成！")
    print("="*40 + "\n")

    return {"final_report": final_report_text}