from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    iot_message: dict
    agent_response: str
    sensor_type: str
    trigger: str        # "running_start" | "running_stop" | "none"
    model_tier: str     # "haiku" | "sonnet" | "opus"（走行強度で決定）
    messages: Annotated[list[BaseMessage], add_messages]
    workspace_root: str  # ファイル操作の基準ディレクトリ


class DevAgentState(TypedDict):
    """自律開発マルチエージェント用のstate"""
    workspace_root: str
    model_tier: str         # "haiku" | "sonnet" | "opus"
    task_list: list[dict]   # planner が生成したタスク一覧 {"task": str, "read_files": list[str], "write_files": list[str]}
    current_task: str       # 現在処理中のタスク
    current_read_files: list[str]   # 現在タスクで読むべきファイル一覧（plannerが特定）
    current_write_files: list[str]  # 現在タスクで書くべきファイル一覧（plannerが特定）
    is_running: bool        # 走行中フラグ
    messages: list[BaseMessage]  # ノードごとにリセットして使用
    review_result: str      # レビュー結果
    needs_revision: bool    # 修正が必要かどうか
    revision_count: int     # 修正回数
    task_index: int         # 現在のタスクのインデックス
