import json
import os
from typing import Literal

from langchain_aws import ChatBedrockConverse
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from agent.state import DevAgentState
from agent.tools import FILE_TOOLS, get_is_running, set_workspace_root

_llm = ChatBedrockConverse(
    model="anthropic.claude-3-haiku-20240307-v1:0",
    region_name=os.environ.get("AWS_BEDROCK_REGION", os.environ.get("AWS_REGION", "us-east-1")),
)
_llm_with_file_tools = _llm.bind_tools(FILE_TOOLS)

_PLAN_PATH = "docs/plan.md"


async def _invoke_agent(prompt: str) -> str:
    """単一ターンのエージェント呼び出し（ツールループ付き）"""
    messages = [HumanMessage(content=prompt)]
    while True:
        response = await _llm_with_file_tools.ainvoke(messages)
        messages.append(response)
        if not response.tool_calls:
            return response.content or ""
        # ツール呼び出しを実行
        tool_node = ToolNode(FILE_TOOLS)
        tool_result = await tool_node.ainvoke({"messages": messages})
        messages = tool_result["messages"]


async def planner_node(state: DevAgentState) -> dict:
    """plan.md を読み込み、タスクリストを生成する（1回だけ実行）"""
    workspace_root = state.get("workspace_root", "")
    plan_path = _PLAN_PATH

    prompt = (
        f"あなたは自律開発エージェントのプランナーです。\n"
        f"ワークスペース: {workspace_root}\n\n"
        f"まず `{plan_path}` を read_file で読み込み、実装すべきタスクをリストアップしてください。\n"
        f"最終的な出力は以下のJSON形式のみで返してください（余分な説明不要）:\n"
        f'[\"タスク1\", \"タスク2\", \"タスク3\"]'
    )

    response = await _invoke_agent(prompt)

    # JSONリストをパース
    try:
        start = response.find("[")
        end = response.rfind("]") + 1
        task_list = json.loads(response[start:end])
    except Exception:
        task_list = [response.strip()]

    return {
        "task_list": task_list,
        "current_task": task_list[0] if task_list else "",
        "messages": [],
    }


async def coder_node(state: DevAgentState) -> dict:
    """current_task を実装しファイルに書き込む"""
    task = state.get("current_task", "")
    workspace_root = state.get("workspace_root", "")

    prompt = (
        f"あなたは自律開発エージェントのコーダーです。\n"
        f"ワークスペース: {workspace_root}\n\n"
        f"以下のタスクを実装してください:\n{task}\n\n"
        f"必要に応じて list_files でプロジェクト構造を確認し、"
        f"read_file で既存コードを読み込んだ上で、"
        f"write_file で実装コードをファイルに書き込んでください。"
    )

    response = await _invoke_agent(prompt)
    return {"messages": []}


async def reviewer_node(state: DevAgentState) -> dict:
    """実装コードをレビューし結果をファイルに書き出す"""
    task = state.get("current_task", "")
    workspace_root = state.get("workspace_root", "")

    prompt = (
        f"あなたは自律開発エージェントのレビュアーです。\n"
        f"ワークスペース: {workspace_root}\n\n"
        f"以下のタスクについて実装されたコードをレビューしてください:\n{task}\n\n"
        f"list_files でファイル一覧を確認し、read_file で実装ファイルを読み込んでレビューしてください。\n"
        f"レビュー結果を write_file で `docs/review.md` に追記形式で書き出してください。"
    )

    response = await _invoke_agent(prompt)
    return {"messages": []}


def running_check_node(state: DevAgentState) -> dict:
    """走行中フラグを確認してstateを更新する"""
    is_running = get_is_running()
    task_list = list(state.get("task_list", []))

    # 完了したタスクをリストから除去
    if task_list:
        task_list.pop(0)

    next_task = task_list[0] if task_list else ""
    return {
        "task_list": task_list,
        "current_task": next_task,
        "is_running": is_running,
    }


def should_continue_dev(state: DevAgentState) -> Literal["coder", "__end__"]:
    """タスクが残っていて走行中なら次のサイクルへ、それ以外は終了"""
    if state.get("task_list") and state.get("is_running", True):
        return "coder"
    return "__end__"


# グラフ構築
_builder = StateGraph(DevAgentState)
_builder.add_node("planner", planner_node)
_builder.add_node("coder", coder_node)
_builder.add_node("reviewer", reviewer_node)
_builder.add_node("running_check", running_check_node)

_builder.add_edge(START, "planner")
_builder.add_edge("planner", "coder")
_builder.add_edge("coder", "reviewer")
_builder.add_edge("reviewer", "running_check")
_builder.add_conditional_edges("running_check", should_continue_dev)

dev_graph = _builder.compile()


async def run_dev_agent(workspace_root: str, plan_path: str = _PLAN_PATH) -> str:
    """走行開始トリガーで呼び出す自律開発エージェントのエントリーポイント"""
    set_workspace_root(workspace_root)
    result = await dev_graph.ainvoke({
        "workspace_root": workspace_root,
        "task_list": [],
        "current_task": "",
        "is_running": True,
        "messages": [],
    })
    completed = len(result.get("task_list", []))
    return f"✅ 自律開発完了（残タスク: {completed} 件）"
