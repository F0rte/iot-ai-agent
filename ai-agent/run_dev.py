#!/usr/bin/env python3
"""
自律開発エージェント 実行スクリプト

docs/plan.md に記載された要件を読み込み、自律的に実装・レビューを行います。

使い方:
    uv run python run_dev.py [--tier haiku|sonnet|opus]

オプション:
    --tier    使用するモデルティア（デフォルト: haiku）
"""

import asyncio
import os
import subprocess
import sys

from dotenv import load_dotenv

load_dotenv()


def get_git_root() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )
    if result.returncode != 0:
        raise RuntimeError("Gitリポジトリが見つかりません")
    return result.stdout.strip()


def parse_tier() -> str:
    if "--tier" in sys.argv:
        idx = sys.argv.index("--tier")
        if idx + 1 < len(sys.argv):
            return sys.argv[idx + 1]
    return "sonnet"


async def main():
    from agent.dev_graph import run_dev_agent

    tier = parse_tier()
    workspace_root = get_git_root()

    print("\n" + "=" * 60)
    print("🤖 自律開発エージェント 起動")
    print("=" * 60)
    print(f"  workspace : {workspace_root}")
    print(f"  model tier: {tier}")
    print(f"  plan file : docs/plan.md")
    print("=" * 60 + "\n")

    result = await run_dev_agent(workspace_root=workspace_root, model_tier=tier)
    print(f"\n{result}\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  中断されました")
