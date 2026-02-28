import json
import os
from typing import Literal

from langchain_aws import ChatBedrockConverse
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from agent.state import AgentState
from agent.tools import ALL_TOOLS, set_workspace_root, set_is_running, set_iot_status

_llm = ChatBedrockConverse(
    model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
    region_name=os.environ.get("AWS_BEDROCK_REGION", os.environ.get("AWS_REGION", "us-east-1")),
)
_llm_with_tools = _llm.bind_tools(ALL_TOOLS)

# 走行状態のインメモリ記録（前回の状態を保持）
_prev_running: bool = False

_SENSOR_PROMPTS = {
    "heart_rate": (
        "あなたはApple Watchの心拍センサーデータを分析する専門AIです。"
        "必要に応じて save_record でデータを保存し、detect_anomaly で異常がないか確認してください。"
        "最終的にデータの状態を日本語で簡潔に説明してください。"
    ),
    "motion": (
        "あなたはESP32デバイスの活動センサーデータを分析する専門AIです。"
        "Status（Run/Walk/None）とbpm値から活動状態を把握し、"
        "必要に応じて save_record でデータを保存してください。"
        "最終的に活動状態を日本語で簡潔に説明してください。"
    ),
    "unknown": (
        "あなたはIoTデバイス（Apple Watch）のデータを分析するAIです。"
        "必要に応じて save_record でデータを保存してください。"
        "最終的にデータの意味を日本語で簡潔に説明してください。"
    ),
}


def classify(state: AgentState) -> dict:
    """センサー種別をStatusキーの存在で判定する"""
    msg = state["iot_message"]
    if "Status" in msg:
        return {"sensor_type": "motion"}
    return {"sensor_type": "unknown"}


def route_after_classify(state: AgentState) -> Literal["trigger_check", "agent"]:
    """motionのみtrigger_checkへ、それ以外はagentへ"""
    if state["sensor_type"] == "motion":
        return "trigger_check"
    return "agent"


def trigger_check(state: AgentState) -> dict:
    """Statusフィールドで走行状態を判定し、状態遷移でtriggerとmodel_tierを決定する"""
    global _prev_running
    msg = state["iot_message"]

    status = msg.get("Status", "None")  # "Run" | "Walk" | "None"
    is_running = status in ("Run", "Walk")

    if is_running and not _prev_running:
        trigger = "running_start"
    elif not is_running and _prev_running:
        trigger = "running_stop"
    else:
        trigger = "none"

    _prev_running = is_running

    # Run → sonnet (4.5), Walk → sonnet-3 (3.5), None → haiku
    if status == "Run":
        model_tier = "sonnet"
    elif status == "Walk":
        model_tier = "sonnet-3"
    else:
        model_tier = "haiku"

    device_id = msg.get("device_id", "motion_sensor")
    set_iot_status(device_id, {
        "status": status,
        "is_running": is_running,
        "trigger": trigger,
        "model_tier": model_tier,
        "timestamp": msg.get("timestamp"),
    })

    return {"trigger": trigger, "model_tier": model_tier}


def route_after_trigger(state: AgentState) -> Literal["notify_start", "notify_stop", "agent"]:
    trigger = state.get("trigger", "none")
    if trigger == "running_start":
        return "notify_start"
    elif trigger == "running_stop":
        return "notify_stop"
    return "agent"


async def notify_start(state: AgentState) -> dict:
    """走行開始トリガーを記録し、自律開発エージェントを起動する"""
    import asyncio
    set_is_running(True)
    workspace_root = state.get("workspace_root", "")
    model_tier = state.get("model_tier", "haiku")

    # 自律開発エージェントをバックグラウンドで起動
    if workspace_root:
        try:
            from agent.dev_graph import run_dev_agent
            asyncio.create_task(run_dev_agent(workspace_root, model_tier=model_tier))
            print(f"[notify_start] 自律開発エージェント起動: {workspace_root} (model_tier={model_tier})")
        except Exception as e:
            print(f"[notify_start] エージェント起動エラー: {e}")

    return {"agent_response": "🏃 走行開始を検知しました。AIエージェントを起動します。"}


def notify_stop(state: AgentState) -> dict:
    """走行終了トリガーを記録する（VS Code側への通知口）"""
    set_is_running(False)
    return {"agent_response": "🛑 走行終了を検知しました。AIエージェントを停止します。"}


async def agent_node(state: AgentState) -> dict:
    """センサー種別に応じたプロンプトでツール付きLLMを呼び出す"""
    sensor_type = state.get("sensor_type", "unknown")
    system_prompt = _SENSOR_PROMPTS.get(sensor_type, _SENSOR_PROMPTS["unknown"])
    msg = state["iot_message"]

    existing_messages = state.get("messages") or []

    if not existing_messages:
        user_content = (
            f"{system_prompt}\n\n"
            f"受信データ:\n{json.dumps(msg, ensure_ascii=False, indent=2)}"
        )
        initial_human = HumanMessage(content=user_content)
        messages = [initial_human]
    else:
        # ツール実行後の再呼び出し: 既存メッセージをそのまま使用
        messages = existing_messages

    response = await _llm_with_tools.ainvoke(messages)

    agent_response = state.get("agent_response", "")
    if not response.tool_calls:
        agent_response = response.content

    if not existing_messages:
        # 初回: HumanMessageとAIMessageを両方stateに保存
        return {"messages": [initial_human, response], "agent_response": agent_response}
    else:
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
_builder.add_node("trigger_check", trigger_check)
_builder.add_node("notify_start", notify_start)
_builder.add_node("notify_stop", notify_stop)
_builder.add_node("agent", agent_node)
_builder.add_node("tools", ToolNode(ALL_TOOLS))

_builder.add_edge(START, "classify")
_builder.add_conditional_edges("classify", route_after_classify)
_builder.add_conditional_edges("trigger_check", route_after_trigger)
_builder.add_edge("notify_start", END)
_builder.add_edge("notify_stop", END)
_builder.add_conditional_edges("agent", should_continue)
_builder.add_edge("tools", "agent")

graph = _builder.compile()


async def run_agent(iot_message: dict, workspace_root: str = "") -> str:
    if workspace_root:
        set_workspace_root(workspace_root)
    result = await graph.ainvoke({
        "iot_message": iot_message,
        "agent_response": "",
        "sensor_type": "",
        "trigger": "none",
        "model_tier": "haiku",
        "messages": [],
        "workspace_root": workspace_root,
    })
    return result["agent_response"]
