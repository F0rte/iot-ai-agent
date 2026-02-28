from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    iot_message: dict
    agent_response: str
    sensor_type: str
    trigger: str  # "running_start" | "running_stop" | "none"
    messages: Annotated[list[BaseMessage], add_messages]
    workspace_root: str  # ファイル操作の基準ディレクトリ


class DevAgentState(TypedDict):
    """自律開発マルチエージェント用のstate"""
    workspace_root: str
    task_list: list[str]    # planner が生成したタスク一覧
    current_task: str       # 現在処理中のタスク
    is_running: bool        # 走行中フラグ
    messages: list[BaseMessage]  # ノードごとにリセットして使用
