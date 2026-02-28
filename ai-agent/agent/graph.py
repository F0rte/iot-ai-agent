import json
import asyncio
import os

from langchain_aws import ChatBedrock
from langgraph.graph import StateGraph, START, END

from agent.state import AgentState

_llm = ChatBedrock(
    model_id="anthropic.claude-3-haiku-20240307-v1:0",
    region_name=os.environ.get("AWS_BEDROCK_REGION", os.environ.get("AWS_REGION", "us-east-1")),
)


async def call_llm(state: AgentState) -> dict:
    msg = state["iot_message"]
    prompt = (
        f"IoTデバイス（Apple Watch）から以下のデータを受信しました。"
        f"データの意味を日本語で簡潔に説明してください。\n\n"
        f"{json.dumps(msg, ensure_ascii=False, indent=2)}"
    )
    response = await _llm.ainvoke(prompt)
    return {"agent_response": response.content}


# グラフ構築
_builder = StateGraph(AgentState)
_builder.add_node("call_llm", call_llm)
_builder.add_edge(START, "call_llm")
_builder.add_edge("call_llm", END)
graph = _builder.compile()


async def run_agent(iot_message: dict) -> str:
    result = await graph.ainvoke({"iot_message": iot_message, "agent_response": ""})
    return result["agent_response"]
