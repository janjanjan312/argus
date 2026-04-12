"""
Quick end-to-end test: user query → LLM tool selection → data retrieval → final answer.

Usage:
    python test_query.py "What is NVDA's P/E ratio compared to the tech sector?"
    python test_query.py                       # runs built-in sample queries
"""

import json
import sys
import os

from openai import OpenAI
from data_tools.registry import TOOL_DEFINITIONS, TOOL_MAP

SYSTEM_PROMPT = (
    "You are ARGUS, an AI equity research assistant specializing in the AI/Technology sector. "
    "Use the provided tools to retrieve real-time financial data, then synthesize a clear, "
    "analyst-quality answer with specific numbers. Always cite the data source."
)

SAMPLE_QUERIES = [
    "What is NVDA's current P/E ratio compared to the Technology sector average?",
    "How has AAPL's stock price performed over the past 6 months?",
    "What recent news events have impacted META's stock?",
    "How is the overall market performing today?",
    "What are the latest quarterly earnings for MSFT — did they beat estimates?",
]


def run_query(client: OpenAI, model: str, query: str) -> str:
    print(f"\n{'='*70}")
    print(f"Query: {query}")
    print('='*70)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": query},
    ]

    MAX_ROUNDS = 5
    for round_num in range(MAX_ROUNDS):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_DEFINITIONS,
        )

        msg = response.choices[0].message

        if not msg.tool_calls:
            print(f"\n--- Final Answer ---\n{msg.content}")
            return msg.content

        messages.append(msg)

        for tc in msg.tool_calls:
            func_name = tc.function.name
            args = json.loads(tc.function.arguments)
            print(f"  [Round {round_num+1}] Calling {func_name}({args})")

            try:
                result = TOOL_MAP[func_name](**args)
                result_str = json.dumps(result, ensure_ascii=False, default=str)
                if len(result_str) > 4000:
                    result_str = result_str[:4000] + "...(truncated)"
            except Exception as e:
                result_str = json.dumps({"error": str(e)})

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result_str,
            })

    return msg.content or "(max rounds reached)"


def main():
    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL", None)
    model = os.getenv("OPENAI_MODEL", "gpt-4o")

    if not api_key:
        print("Error: set OPENAI_API_KEY in .env or environment")
        print("For other providers, also set OPENAI_BASE_URL and OPENAI_MODEL")
        print("\nExamples:")
        print("  # OpenAI")
        print('  OPENAI_API_KEY="sk-..." python test_query.py')
        print("  # DeepSeek")
        print('  OPENAI_API_KEY="sk-..." OPENAI_BASE_URL="https://api.deepseek.com" OPENAI_MODEL="deepseek-chat" python test_query.py')
        sys.exit(1)

    client = OpenAI(api_key=api_key, base_url=base_url)
    print(f"Model: {model}")
    if base_url:
        print(f"Base URL: {base_url}")

    if len(sys.argv) > 1:
        queries = [" ".join(sys.argv[1:])]
    else:
        queries = SAMPLE_QUERIES

    for q in queries:
        run_query(client, model, q)
        print()


if __name__ == "__main__":
    main()
