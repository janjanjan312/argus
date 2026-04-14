from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from agent.state import AgentState
from agent.prompts import COMPLIANCE_ANALYST_PROMPT
from data_tools.registry import TOOL_DEFINITIONS, TOOL_MAP
from rag import RAG_TOOL_DEFINITIONS, RAG_TOOL_MAP

COMPLIANCE_TOOLS = ["download_filing"]

compliance_tool_schemas = [
    tool for tool in TOOL_DEFINITIONS
    if tool.get("function", {}).get("name") in COMPLIANCE_TOOLS
]

compliance_tool_schemas.extend(RAG_TOOL_DEFINITIONS)

LOCAL_TOOL_MAP = TOOL_MAP.copy()
LOCAL_TOOL_MAP.update(RAG_TOOL_MAP)

llm = ChatOpenAI(model="gemini-3-flash", temperature=0)
llm_with_tools = llm.bind_tools(compliance_tool_schemas)

def compliance_analyst_node(state: AgentState) -> dict:
    """
    合规与风险分析师
    负责调用L1基础API和 L2 RAG 向量检索，提取SEC官方文件中的风险与合规文本。
    """
    print("\n" + "-"*40)
    print("⚖️ [Compliance Analyst] 接收任务")

    rewritten_query = state.get("rewritten_query", "")

    messages = [
        SystemMessage(content=COMPLIANCE_ANALYST_PROMPT),
        HumanMessage(content=rewritten_query)
    ]
    response = llm_with_tools.invoke(messages)

    new_collected_data = []

    if response.tool_calls:
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            print(f"🔧 [Compliance Analyst] 执行工具: {tool_name}")
            print(f"   参数: {tool_args}")

            if tool_name in LOCAL_TOOL_MAP:
                try:
                    # 调用真实的 Python 工具函数执行
                    raw_result = LOCAL_TOOL_MAP[tool_name](**tool_args)

                    new_collected_data.append({
                        "source": f"API/RAG_{tool_name}",
                        "worker": "Compliance_Analyst",
                        "parameters": tool_args,
                        "data": raw_result
                    })
                    print(f"✅ [Compliance Analyst] {tool_name} 执行成功，已获取真实文本块。")
                except Exception as e:
                    print(f"❌ [Compliance Analyst] {tool_name} 执行抛出异常: {e}")
                    new_collected_data.append({
                        "source": f"API/RAG_{tool_name}",
                        "worker": "Compliance_Analyst",
                        "error": str(e)
                    })
            else:
                print(f"❌ [Compliance Analyst] 未知的工具名称: {tool_name}")
    else:
        print("⚠️ [Compliance Analyst] 模型未触发任何工具调用。")
        new_collected_data.append({
            "source": "Compliance_Analyst_Direct_Response",
            "worker": "Compliance_Analyst",
            "data": response.content
        })

    print("-" * 40 + "\n")
    return {"collected_data": new_collected_data}