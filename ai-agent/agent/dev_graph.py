import json
import os
import re
import asyncio
from typing import Literal

from langchain_aws import ChatBedrockConverse
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from agent.state import DevAgentState
from agent.tools import FILE_TOOLS, get_is_running, set_workspace_root, get_iot_status
from api.events import broadcast

_REGION = os.environ.get("AWS_BEDROCK_REGION", os.environ.get("AWS_REGION", "us-east-1"))

# モデルティアとモデルIDのマッピング
_MODEL_IDS = {
    "haiku":  "us.anthropic.claude-haiku-4-5-20251001-v1:0",
    "sonnet": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "opus":   "us.anthropic.claude-opus-4-5-20251101-v1:0",
    # 旧世代（フォールバック用）
    "haiku-3":  "anthropic.claude-3-haiku-20240307-v1:0",
    "sonnet-3": "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "opus-3":   "anthropic.claude-3-7-sonnet-20250219-v1:0",
}
_TIER_ORDER = ["haiku", "sonnet", "opus"]

# 実行計画専用ファイルパス
# 注: .github/docs/tasks.md は人間向けの設計・方針ドキュメント
# docs/plan.md はエージェントに渡す「次にやること」を自然言語で記述する実行計画専用
_PLAN_PATH = "docs/plan.md"


def _get_llm(tier: str) -> ChatBedrockConverse:
    model_id = _MODEL_IDS.get(tier, _MODEL_IDS["haiku"])
    return ChatBedrockConverse(model=model_id, region_name=_REGION)


def _lower_tier(tier: str) -> str:
    """1段階下のティアを返す（haiku の場合はそのまま）"""
    idx = _TIER_ORDER.index(tier) if tier in _TIER_ORDER else 0
    return _TIER_ORDER[max(0, idx - 1)]


async def _invoke_agent(prompt: str, tier: str, max_iterations: int = 20) -> str:
    """単一ターンのエージェント呼び出し（ツールループ付き）"""
    llm_with_tools = _get_llm(tier).bind_tools(FILE_TOOLS)
    messages = [HumanMessage(content=prompt)]
    for i in range(max_iterations):
        response = await llm_with_tools.ainvoke(messages)
        messages.append(response)
        if not response.tool_calls:
            return response.content or ""
        tool_node = ToolNode(FILE_TOOLS)
        tool_result = await tool_node.ainvoke({"messages": messages})
        messages = messages + tool_result["messages"]
    print(f"[agent] 最大イテレーション数({max_iterations})に達しました")
    return messages[-1].content if messages else ""


async def planner_node(state: DevAgentState) -> dict:
    """plan.md を読み込み、タスクリストを生成する（1回だけ実行）"""
    workspace_root = state.get("workspace_root", "")
    tier = state.get("model_tier", "haiku")

    prompt = (
        f"あなたは自律開発エージェントのプランナーです。\n"
        f"ワークスペース: {workspace_root}\n\n"
        f"手順:\n"
        f"1. `{_PLAN_PATH}` を read_file で読み込む（ユーザーが自然言語で書いた要件・やりたいことが記載されている）\n"
        f"   注: このファイルは実行計画専用で、エージェントが実装すべき次のタスクが記述されています\n"
        f"2. list_files でプロジェクト構造を把握し、必要に応じて既存コードを read_file で確認する\n"
        f"3. 要件を実装可能な具体的タスクに分解する。各タスクは独立して実装できる単位にすること\n\n"
        f"最終的な出力は以下のJSON形式のみで返してください（余分な説明不要）:\n"
        f'[{{"task": "タスク1の具体的な実装内容", "read_files": ["読む必要があるファイルパス"], "write_files": ["編集・作成するファイルパス"]}}, ...]'
    )

    print(f"[planner] model_tier={tier} ({_MODEL_IDS.get(tier)})")
    response = await _invoke_agent(prompt, tier)

    try:
        start = response.find("[")
        if start == -1:
            raise ValueError("No JSON array found in response")
        end = response.rfind("]") + 1
        raw_list = json.loads(response[start:end])
        # 旧形式（文字列）と新形式（dict）両対応
        task_list = []
        for item in raw_list:
            if isinstance(item, str):
                task_list.append({"task": item, "read_files": [], "write_files": []})
            else:
                task_list.append(item)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[planner] JSONパースエラー: {e}")
        print(f"[planner] 生レスポンス: {response[:200]}...")
        task_list = [{"task": response.strip(), "read_files": [], "write_files": []}]

    # タスク一覧をブロードキャスト
    if task_list:
        print(f"[planner] タスク一覧をブロードキャストします（{len(task_list)} 件）")
        await broadcast({
            "type": "tasks",
            "tasks": [
                {"index": i, "task": t["task"] if isinstance(t, dict) else t, "status": "pending"}
                for i, t in enumerate(task_list)
            ],
            "total_count": len(task_list),
            "message": f"タスク分解完了: {len(task_list)} 件のタスクを生成しました"
        })
    else:
        print("[planner] タスクリストが空です。終了します。")
        await broadcast({
            "type": "task_list",
            "tasks": [],
            "total_count": 0,
            "message": "タスクが見つかりませんでした"
        })

    first = task_list[0] if task_list else {}
    if not task_list:
        return {
            "task_list": [],
            "current_task": "",
            "current_read_files": [],
            "current_write_files": [],
            "messages": [],
            "revision_count": 0,
            "needs_revision": False,
            "review_result": "",
            "is_running": False,  # タスクなしで終了
            "task_index": 0,
        }
    return {
        "task_list": task_list,
        "current_task": first.get("task", ""),
        "current_read_files": first.get("read_files", []),
        "current_write_files": first.get("write_files", []),
        "messages": [],
        "revision_count": 0,
        "needs_revision": False,
        "review_result": "",
        "task_index": 0,
    }


async def coder_node(state: DevAgentState) -> dict:
    """current_task を実装しファイルに書き込む"""
    task = state.get("current_task", "")
    workspace_root = state.get("workspace_root", "")
    tier = state.get("model_tier", "haiku")
    read_files = state.get("current_read_files", [])
    write_files = state.get("current_write_files", [])
    revision_count = state.get("revision_count", 0)
    review_result = state.get("review_result", "")
    task_index = state.get("task_index", 0)

    await broadcast({"type": "task_status", "task_index": task_index, "status": "coding"})

    file_hint = ""
    if read_files or write_files:
        file_hint = (
            f"\n\n【ファイルヒント（plannerが特定済み）】\n"
            f"読み込むファイル: {read_files}\n"
            f"編集・作成するファイル: {write_files}\n"
            f"list_files による探索は不要です。上記ファイルを直接 read_file してください。"
        )

    revision_hint = ""
    if revision_count > 0 and review_result:
        revision_hint = (
            f"\n\n【修正依頼（{revision_count}回目）】\n"
            f"前回のレビュー結果:\n{review_result}\n\n"
            f"上記の指摘事項を反映して修正してください。"
        )

    print(f"[coder] model_tier={tier} ({_MODEL_IDS.get(tier)}), revision_count={revision_count}")
    prompt = (
        f"あなたは自律開発エージェントのコーダーです。\n"
        f"ワークスペース: {workspace_root}\n\n"
        f"以下のタスクを実装してください:\n{task}"
        f"{file_hint}"
        f"{revision_hint}\n\n"
        f"read_file で対象ファイルを読み込んだ上で、"
        f"write_file で実装コードをファイルに書き込んでください。\n"
        f"実装後は run_shell でテストやビルドを実行して動作確認してください。\n"
        f"一時的なテストファイルは `agent_test_` で始まる名前にしてください。\n"
        f"一時的なドキュメント・レポートファイルは `agent_` で始まる名前にしてください。"
    )

    await _invoke_agent(prompt, tier)
    return {"messages": []}


async def reviewer_node(state: DevAgentState) -> dict:
    """実装コードをレビューし、PASS/FAIL判定と修正要否をstateに返す"""
    task = state.get("current_task", "")
    workspace_root = state.get("workspace_root", "")
    tier = _lower_tier(state.get("model_tier", "haiku"))  # レビューは1段階下
    write_files = state.get("current_write_files", [])
    revision_count = state.get("revision_count", 0)
    task_index = state.get("task_index", 0)

    file_hint = ""
    if write_files:
        file_hint = (
            f"\n\n【ファイルヒント（plannerが特定済み）】\n"
            f"レビュー対象ファイル: {write_files}\n"
            f"list_files による探索は不要です。上記ファイルを直接 read_file してください。"
        )

    print(f"[reviewer] model_tier={tier} ({_MODEL_IDS.get(tier)}), revision_count={revision_count}")
    await broadcast({"type": "task_status", "task_index": task_index, "status": "reviewing"})
    prompt = (
        f"あなたは自律開発エージェントのレビュアーです。\n"
        f"ワークスペース: {workspace_root}\n\n"
        f"以下のタスクについて実装されたコードをレビューしてください:\n{task}"
        f"{file_hint}\n\n"
        f"read_file で実装ファイルを読み込んでレビューしてください。\n"
        f"必要に応じて run_shell でテストを実行し、動作を確認してください。\n\n"
        f"レビュー基準:\n"
        f"- コードがタスクの要件を満たしているか\n"
        f"- 構文エラーや明らかなバグがないか\n"
        f"- テストが通るか（該当する場合）\n\n"
        f"レビューコメントを自由に書いた後、必ず最後に以下の形式で判定を出力してください:\n"
        f"<review_result>\n"
        f'{{"result": "PASS", "needs_revision": false, "comment": "コメント"}}\n'
        f"</review_result>\n\n"
        f"※ 問題がある場合は result を FAIL、needs_revision を true にしてください。\n"
        f"※ <review_result> タグの中身は必ず有効なJSONにしてください。"
    )

    response = await _invoke_agent(prompt, tier)

    # <review_result>タグ内のJSONを抽出
    tag_match = re.search(r"<review_result>\s*(.*?)\s*</review_result>", response, re.DOTALL)
    try:
        json_str = tag_match.group(1) if tag_match else None
        if not json_str:
            raise ValueError("No <review_result> tag found in response")
        review_data = json.loads(json_str)

        result = review_data.get("result", "FAIL")
        needs_revision = review_data.get("needs_revision", True)
        comment = review_data.get("comment", response)

        print(f"[reviewer] result={result}, needs_revision={needs_revision}")

    except (json.JSONDecodeError, ValueError) as e:
        print(f"[reviewer] JSONパースエラー: {e}")
        print(f"[reviewer] 生レスポンス: {response[:200]}...")
        # パース失敗時はPASSとして扱う（誤ったFAILによる無駄ループを防ぐ）
        result = "PASS"
        needs_revision = False
        comment = response

    # レビュー結果をタスクごとの個別ファイルに出力
    review_summary = (
        f"# レビュー結果 - タスク {task_index}\n\n"
        f"## タスク内容\n{task}\n\n"
        f"## レビュー結果\n"
        f"- **判定**: {result}\n"
        f"- **修正要否**: {'必要' if needs_revision else '不要'}\n"
        f"- **修正回数**: {revision_count}\n\n"
        f"## コメント\n{comment}\n"
    )
    review_path = os.path.join(workspace_root, f"docs/review_{task_index:02d}.md")
    os.makedirs(os.path.dirname(review_path), exist_ok=True)
    with open(review_path, "w", encoding="utf-8") as f:
        f.write(review_summary)

    final_needs_revision = needs_revision and revision_count < 2
    await broadcast({
        "type": "task_status",
        "task_index": task_index,
        "status": "done" if not final_needs_revision else "revision",
        "result": result,
    })

    return {
        "review_result": comment,
        "needs_revision": final_needs_revision,
        "messages": [],
    }


def should_revise(state: DevAgentState) -> Literal["coder", "running_check"]:
    """修正が必要かつ修正回数が2回未満ならcoderに戻る、それ以外はrunning_checkへ"""
    needs_revision = state.get("needs_revision", False)
    revision_count = state.get("revision_count", 0)
    
    if needs_revision and revision_count < 2:
        print(f"[should_revise] 修正ループへ (revision_count={revision_count})")
        return "coder"
    else:
        if revision_count >= 2:
            print(f"[should_revise] 最大修正回数到達、次のタスクへ")
        else:
            print(f"[should_revise] レビューPASS、次のタスクへ")
        return "running_check"


def revision_counter_node(state: DevAgentState) -> dict:
    """修正カウンターをインクリメント"""
    revision_count = state.get("revision_count", 0)
    return {"revision_count": revision_count + 1}


async def running_check_node(state: DevAgentState) -> dict:
    """IoTステータスを確認してから、走行中フラグを確認してstateを更新し、task_indexをインクリメントして返す"""
    
    # IoTステータスの確認（Noneの場合は5秒ごとに確認する無限ループ）
    print("[running_check] IoTステータスの確認を開始...")
    while True:
        # 全デバイスのステータスを取得
        iot_status = get_iot_status()
        
        if iot_status is None or len(iot_status) == 0:
            print("[running_check] IoTステータスがNoneまたは空です。5秒待機してから再確認します...")
            await broadcast({"type": "task_status", "status": "waiting"})
            await asyncio.sleep(5)
            continue
        
        # ステータスが取得できた場合
        print(f"[running_check] IoTステータスを確認しました: {iot_status}")
        break
    
    # 走行中フラグの確認
    is_running = state.get("is_running", True)
    task_list = list(state.get("task_list", []))
    task_index = state.get("task_index", 0)

    # 現在のタスクを削除
    if task_list:
        task_list.pop(0)

    # 次のタスクを取得
    next_item = task_list[0] if task_list else {}
    
    # task_indexをインクリメント
    next_task_index = task_index + 1
    
    return {
        "task_list": task_list,
        "current_task": next_item.get("task", "") if isinstance(next_item, dict) else next_item,
        "current_read_files": next_item.get("read_files", []) if isinstance(next_item, dict) else [],
        "current_write_files": next_item.get("write_files", []) if isinstance(next_item, dict) else [],
        "is_running": is_running,
        "revision_count": 0,  # 次のタスクのためにリセット
        "needs_revision": False,
        "review_result": "",
        "task_index": next_task_index,  # インクリメントされたインデックスを返す
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
_builder.add_node("revision_counter", revision_counter_node)
_builder.add_node("running_check", running_check_node)

_builder.add_edge(START, "planner")
_builder.add_edge("planner", "coder")
_builder.add_edge("coder", "reviewer")
_builder.add_conditional_edges("reviewer", should_revise, {
    "coder": "revision_counter",
    "running_check": "running_check"
})
_builder.add_edge("revision_counter", "coder")
_builder.add_conditional_edges("running_check", should_continue_dev)

dev_graph = _builder.compile()


async def run_dev_agent(workspace_root: str, model_tier: str = "haiku", plan_path: str = _PLAN_PATH) -> str:
    """走行開始トリガーで呼び出す自律開発エージェントのエントリーポイント"""
    set_workspace_root(workspace_root)
    result = await dev_graph.ainvoke({
        "workspace_root": workspace_root,
        "model_tier": model_tier,
        "task_list": [],
        "current_task": "",
        "current_read_files": [],
        "current_write_files": [],
        "is_running": True,
        "messages": [],
        "revision_count": 0,
        "needs_revision": False,
        "review_result": "",
        "task_index": 0,
    })
    remaining = len(result.get("task_list", []))
    return f"✅ 自律開発完了（残タスク: {remaining} 件、使用ティア: {model_tier}）"
