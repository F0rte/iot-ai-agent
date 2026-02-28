import json
import os
from typing import Literal

from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from agent.state import AgentState
from agent.tools import TOOLS

_llm = ChatBedrock(
    model_id="anthropic.claude-3-haiku-20240307-v1:0",
    region_name=os.environ.get("AWS_BEDROCK_REGION", os.environ.get("AWS_REGION", "us-east-1")),
)
_llm_with_tools = _llm.bind_tools(TOOLS)

_HEART_RATE_KEYS = {"heart_rate", "bpm", "heartRate", "heart_rate_variability", "hrv"}
_MOTION_KEYS = {"acceleration", "gyroscope", "steps", "motion", "accelerometer"}

_SENSOR_PROMPTS = {
    "heart_rate": (
        "あなたはApple Watchの心拍センサーデータを分析する専門AIです。"
        "必要に応じて save_record でデータを保存し、detect_anomaly で異常がないか確認してください。"
        "最終的にデータの状態を日本語で簡潔に説明してください。"
    ),
    "motion": (
        "あなたはApple Watchの動作センサー（加速度・ジャイロスコープ）データを分析する専門AIです。"
        "必要に応じて save_record でデータを保存してください。"
        "最終的に動作・姿勢の状態を日本語で簡潔に説明してください。"
    ),
    "unknown": (
        "あなたはIoTデバイス（Apple Watch）のデータを分析するAIです。"
        "必要に応じて save_record でデータを保存してください。"
        "最終的にデータの意味を日本語で簡潔に説明してください。"
    ),
}


def classify(state: AgentState) -> dict:
    """センサー種別をルールベースで判定する"""
    keys = set(state["iot_message"].keys())
    if keys & _HEART_RATE_KEYS:
        return {"sensor_type": "heart_rate"}
    elif keys & _MOTION_KEYS:
        return {"sensor_type": "motion"}
    else:
        return {"sensor_type": "unknown"}


async def agent_node(state: AgentState) -> dict:
    """センサー種別に応じたプロンプトでツール付きLLMを呼び出す"""
    sensor_type = state.get("sensor_type", "unknown")
    system_prompt = _SENSOR_PROMPTS.get(sensor_type, _SENSOR_PROMPTS["unknown"])
    msg = state["iot_message"]

    messages = state.get("messages") or []
    # 最初のメッセージのみユーザープロンプトを追加
    if not messages:
        user_content = (
            f"{system_prompt}\n\n"
            f"受信データ:\n{json.dumps(msg, ensure_ascii=False, indent=2)}"
        )
        messages = [HumanMessage(content=user_content)]

    response = await _llm_with_tools.ainvoke(messages)

    # ツール呼び出しがない場合は最終応答として確定
    agent_response = state.get("agent_response", "")
    if not response.tool_calls:
        agent_response = response.content

    return {"messages": [response], "agent_response": agent_response}


def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    """ツール呼び出しがあれば継続、なければ終了"""
    messages = state.get("messages", [])
    if messages and hasattr(messages[-1], "tool_calls") and messages[-1].tool_calls:
        return "tools"
    return "__end__"


# グラフ構築
_builder = StateGraph(AgentState)
_builder.add_node("classify", classify)
_builder.add_node("agent", agent_node)
_builder.add_node("tools", ToolNode(TOOLS))

_builder.add_edge(START, "classify")
_builder.add_edge("classify", "agent")
_builder.add_conditional_edges("agent", should_continue)
_builder.add_edge("tools", "agent")

graph = _builder.compile()


async def run_agent(iot_message: dict) -> str:
    result = await graph.ainvoke({
        "iot_message": iot_message,
        "agent_response": "",
        "sensor_type": "",
        "messages": [],
    })
    return result["agent_response"]
