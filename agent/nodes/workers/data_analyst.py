from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from agent.state import AgentState
from agent.prompts import DATA_ANALYST_PROMPT
from data_tools.registry import TOOL_DEFINITIONS, TOOL_MAP

DATA_TOOLS = [
    "get_financial_statements",
    "get_key_metrics",
    "get_peer_comparison"
]

data_tool_schemas = [
    tool for tool in TOOL_DEFINITIONS
    if tool.get("function", {}).get("name") in DATA_TOOLS
]

llm = ChatOpenAI(model="gemini-3-flash", temperature=0)
llm_with_tools = llm.bind_tools(data_tool_schemas)

def data_analyst_node(state: AgentState) -> dict:
    """
    量化财务分析师
    负责解析用户的财务查询，调用相关 yfinance API，并将原始数据注入状态总线。
    """
    print("\n" + "-"*40)
    print("📊 [Data Analyst] 接收任务")

    rewritten_query = state.get("rewritten_query", "")
    messages = [
        SystemMessage(content=DATA_ANALYST_PROMPT),
        HumanMessage(content=rewritten_query)
    ]
    response = llm_with_tools.invoke(messages)
    new_collected_data = []
    if response.tool_calls:
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            print(f"🔧 [Data Analyst] 执行 L1 工具: {tool_name}")
            print(f"   参数: {tool_args}")

            if tool_name in TOOL_MAP:
                try:
                    raw_result = TOOL_MAP[tool_name](**tool_args)
                    new_collected_data.append({
                        "source": f"API_{tool_name}",
                        "worker": "Data_Analyst",
                        "parameters": tool_args,
                        "data": raw_result
                    })
                    print(f"✅ [Data Analyst] {tool_name} 执行成功，已获取底层数据。")
                except Exception as e:
                    print(f"❌ [Data Analyst] {tool_name} 执行抛出异常: {e}")
                    new_collected_data.append({
                        "source": f"API_{tool_name}",
                        "worker": "Data_Analyst",
                        "error": str(e)
                    })
            else:
                print(f"❌ [Data Analyst] 未知的工具名称: {tool_name}")
    else:
        print("⚠️ [Data Analyst] 模型未触发任何工具调用。")
        new_collected_data.append({
            "source": "Data_Analyst_Direct_Response",
            "worker": "Data_Analyst",
            "data": response.content
        })

    print("-"*40 + "\n")
    return {"collected_data": new_collected_data}