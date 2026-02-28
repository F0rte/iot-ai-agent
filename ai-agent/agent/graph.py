import json
import os

from langchain_aws import ChatBedrock
from langgraph.graph import StateGraph, START, END

from agent.state import AgentState

_llm = ChatBedrock(
    model_id="anthropic.claude-3-haiku-20240307-v1:0",
    region_name=os.environ.get("AWS_BEDROCK_REGION", os.environ.get("AWS_REGION", "us-east-1")),
)

_HEART_RATE_KEYS = {"heart_rate", "bpm", "heartRate", "heart_rate_variability", "hrv"}
_MOTION_KEYS = {"acceleration", "gyroscope", "steps", "motion", "accelerometer"}


def classify(state: AgentState) -> dict:
    """センサー種別をルールベースで判定する"""
    keys = set(state["iot_message"].keys())
    if keys & _HEART_RATE_KEYS:
        return {"sensor_type": "heart_rate"}
    elif keys & _MOTION_KEYS:
        return {"sensor_type": "motion"}
    else:
        return {"sensor_type": "unknown"}


def route_by_sensor(state: AgentState) -> str:
    return state["sensor_type"]


async def heart_rate_node(state: AgentState) -> dict:
    msg = state["iot_message"]
    prompt = (
        f"Apple Watchから心拍センサーのデータを受信しました。"
        f"心拍数や心拍変動の状態を日本語で簡潔に評価してください。\n\n"
        f"{json.dumps(msg, ensure_ascii=False, indent=2)}"
    )
    response = await _llm.ainvoke(prompt)
    return {"agent_response": response.content}


async def motion_node(state: AgentState) -> dict:
    msg = state["iot_message"]
    prompt = (
        f"Apple Watchから動作センサー（加速度・ジャイロスコープ）のデータを受信しました。"
        f"動作・姿勢の状態を日本語で簡潔に評価してください。\n\n"
        f"{json.dumps(msg, ensure_ascii=False, indent=2)}"
    )
    response = await _llm.ainvoke(prompt)
    return {"agent_response": response.content}


async def generic_node(state: AgentState) -> dict:
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
_builder.add_node("classify", classify)
_builder.add_node("heart_rate", heart_rate_node)
_builder.add_node("motion", motion_node)
_builder.add_node("unknown", generic_node)

_builder.add_edge(START, "classify")
_builder.add_conditional_edges(
    "classify",
    route_by_sensor,
    {"heart_rate": "heart_rate", "motion": "motion", "unknown": "unknown"},
)
_builder.add_edge("heart_rate", END)
_builder.add_edge("motion", END)
_builder.add_edge("unknown", END)

graph = _builder.compile()


async def run_agent(iot_message: dict) -> str:
    result = await graph.ainvoke({"iot_message": iot_message, "agent_response": "", "sensor_type": ""})
    return result["agent_response"]
