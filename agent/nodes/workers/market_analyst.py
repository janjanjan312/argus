from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from agent.state import AgentState
from agent.prompts import MARKET_ANALYST_PROMPT
from data_tools.registry import TOOL_DEFINITIONS, TOOL_MAP
MARKET_TOOLS = [
    "get_stock_price",
    "get_stock_info",
    "get_company_news",
    "get_earnings_data",
    "get_market_overview",
    "get_sector_pe",
    "get_analyst_estimates"
]

market_tool_schemas = [
    tool for tool in TOOL_DEFINITIONS
    if tool.get("function", {}).get("name") in MARKET_TOOLS
]

llm = ChatOpenAI(model="gemini-3-flash", temperature=0)
llm_with_tools = llm.bind_tools(market_tool_schemas)

def market_analyst_node(state: AgentState) -> dict:
    """
    市场与情绪分析师
    负责解析关于股价、新闻、估值对比的查询，调用相应的 API，并将原始数据注入状态总线。
    """
    print("\n" + "-"*40)
    print("📈 [Market Analyst] 接收到任务，开始二级市场与情绪分析...")
    rewritten_query = state.get("rewritten_query", "")
    messages = [
        SystemMessage(content=MARKET_ANALYST_PROMPT),
        HumanMessage(content=rewritten_query)
    ]
    response = llm_with_tools.invoke(messages)
    new_collected_data = []
    if response.tool_calls:
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            print(f"🔧 [Market Analyst] 执行 L1 工具: {tool_name}")
            print(f"   参数: {tool_args}")

            if tool_name in TOOL_MAP:
                try:
                    raw_result = TOOL_MAP[tool_name](**tool_args)

                    new_collected_data.append({
                        "source": f"API_{tool_name}",
                        "worker": "Market_Analyst",
                        "parameters": tool_args,
                        "data": raw_result
                    })
                    print(f"✅ [Market Analyst] {tool_name} 执行成功，已获取市场数据。")
                except Exception as e:
                    print(f"❌ [Market Analyst] {tool_name} 执行抛出异常: {e}")
                    new_collected_data.append({
                        "source": f"API_{tool_name}",
                        "worker": "Market_Analyst",
                        "error": str(e)
                    })
            else:
                print(f"❌ [Market Analyst] 未知的工具名称: {tool_name}")
    else:
        print("⚠️ [Market Analyst] 模型未触发任何工具调用。")
        new_collected_data.append({
            "source": "Market_Analyst_Direct_Response",
            "worker": "Market_Analyst",
            "data": response.content
        })

    print("-" * 40 + "\n")
    return {"collected_data": new_collected_data}