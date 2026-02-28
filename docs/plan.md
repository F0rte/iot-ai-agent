# AIエージェント 調整・改良設計書

## プロジェクト概要（現状把握）

Running Driven Development（RDD）: Apple Watchの走行を検知すると自律開発エージェントが起動し、
走行強度に応じてモデルを切り替えながらコードを自動実装する仕組み。

### 現在の全体フロー
```
Apple Watch（加速度センサー）
  → MQTT → subscriber.py → graph.py（IoTエージェント）
      ├── classify（センサー種別判定）
      ├── trigger_check（走行開始/終了判定・モデルティア決定）
      ├── notify_start → dev_graph.py（自律開発エージェント）非同期起動
      │     └── planner → coder → reviewer → loop
      └── agent（センサーデータ分析・ツール呼び出し）
  → SSE → VSCode Webview 表示
```

---

## 改良タスク一覧

### Task 1: workspace_root の自動設定【重要度: 高】

**問題:** `subscriber.py` から `run_agent()` を呼ぶ際に `workspace_root` が渡されていないため、
`notify_start` ノードで自律開発エージェントが起動できない（workspace_root が空文字になる）。

**対象ファイル:** `ai-agent/iot/subscriber.py`

**変更内容:**
- `_handle_message` の `run_agent()` 呼び出しに `workspace_root` を渡す
- `setup()` 実行時に `git rev-parse --show-toplevel` でリポジトリルートを自動取得して保持する

```python
# subscriber.py に追加
import subprocess

def _get_git_root() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    return result.stdout.strip() if result.returncode == 0 else ""

# run_agent 呼び出し時に workspace_root を渡す
response = await run_agent(message, workspace_root=_get_git_root())
```

---

### Task 2: dev_graph の planner が読む plan.md のパス統一【重要度: 高】

**問題:** `dev_graph.py` の `_PLAN_PATH = "docs/plan.md"` はリポジトリルートの `docs/plan.md` を参照するが、
実際の設計書は `.github/docs/tasks.md` にある。これを統一する必要がある。

**対象ファイル:** `ai-agent/agent/dev_graph.py`、`docs/plan.md`

**変更内容（2択）:**
- A案: `_PLAN_PATH = ".github/docs/tasks.md"` に変更する
- B案: `docs/plan.md` を実際の実装計画として活用し、`.github/docs/tasks.md` は設計書として分離する（推奨）

**B案の運用:**
- `.github/docs/tasks.md`（本ファイル）: 人間向けの設計・方針ドキュメント
- `docs/plan.md`: エージェントに渡す「次にやること」を自然言語で記述する実行計画

---

### Task 3: reviewer → coder フィードバックループ【重要度: 中】

**問題:** `dev_graph.py` の reviewer ノードはレビュー結果を `docs/review.md` に書くだけで、
問題を検知しても coder に修正を依頼しない。

**対象ファイル:** `ai-agent/agent/dev_graph.py`、`ai-agent/agent/state.py`

**変更内容:**
- `DevAgentState` に `review_result: str`、`needs_revision: bool` フィールドを追加
- reviewer ノードがレビュー結果を state に返す
- `running_check` の条件分岐を拡張し、`needs_revision=True` の場合は coder に戻る
- 無限ループ防止のため `revision_count: int` フィールドを追加し最大2回までとする

```
coder → reviewer → running_check
                       ├── (needs_revision=True, revision_count < 2) → coder
                       ├── (task_list残あり) → coder
                       └── (完了/上限) → END
```

---

### Task 4: dev_agent の進捗を SSE で VSCode に通知【重要度: 中】

**問題:** 自律開発エージェントの進捗（どのタスクを実行中か）が VSCode Webview に届かない。
ランニング中に何をしているか見えない。

**対象ファイル:** `ai-agent/agent/dev_graph.py`、`ai-agent/api/events.py`

**変更内容:**
- `planner_node`、`coder_node`、`reviewer_node` の各ノードで `broadcast()` を呼ぶ
- SSE イベント型に `"dev"` を追加する

```python
# 例: coder_node 内
await broadcast({"type": "dev", "node": "coder", "task": task, "status": "start"})
# 実装後
await broadcast({"type": "dev", "node": "coder", "task": task, "status": "done"})
```

- VSCode の `panel.ts` 側で `type: "dev"` を処理してタスク進捗を表示する（UI班対応）

---

### Task 5: git commit ツールの追加【重要度: 低】

**問題:** coder がファイルを書き込んでもコミットしない。実装結果が git 履歴に残らない。

**対象ファイル:** `ai-agent/agent/tools.py`

**変更内容:** `git_commit(message: str)` ツールを追加する

```python
@tool
def git_commit(message: str) -> str:
    """ワークスペースの変更をgitにコミットする。
    Args:
        message: コミットメッセージ（英語）
    """
    result = subprocess.run(
        ["git", "add", "-A"],
        cwd=_workspace_root, capture_output=True, text=True
    )
    result = subprocess.run(
        ["git", "commit", "-m", message],
        cwd=_workspace_root, capture_output=True, text=True
    )
    return result.stdout or result.stderr
```

- `FILE_TOOLS` に追加し、coder がレビュー通過後に自動コミットできるようにする

---

### Task 6: タスクキューの永続化【重要度: 中】

**問題:** `task_list` はメモリ上にのみ存在するため、途中でプロセスが終了するとどこまで完了したか失われる。

**対象ファイル:** `ai-agent/agent/dev_graph.py`

**変更内容:**
- `planner_node` がタスク分解直後に `docs/tasks_queue.md` へタスク一覧を書き出す
- `running_check_node` でタスク完了のたびにステータスを更新する
- 再起動時に `tasks_queue.md` に未完了タスクが残っていれば planner をスキップして再開できる

**`docs/tasks_queue.md` のフォーマット例:**
```markdown
## タスクキュー

- [x] src/hello.py を作成する
- [ ] tests/test_hello.py を作成する
- [ ] README.md にセットアップ手順を追記する
```

**再開ロジック（将来対応）:**
- 起動時に `tasks_queue.md` が存在し未完了タスク（`- [ ]`）があれば、planner をスキップして残タスクから再開する

### Task 7: レビュー結果のタスク別ファイル出力【重要度: 中】

**問題:** reviewer のプロンプトは「追記形式で」と指示しているが、`write_file` ツールは上書き（`"w"`モード）のため、
ループが回るたびに `docs/review.md` が上書きされ、前のタスクのレビュー結果が失われる。

**対象ファイル:** `ai-agent/agent/dev_graph.py`

**変更内容:**
- reviewer プロンプトの出力先を `docs/review_{task番号}.md` に変更する
- タスク番号は `DevAgentState` に `task_index: int` フィールドを追加して管理する
- `planner_node` で `task_index = 0` に初期化し、`running_check_node` でインクリメントする

```python
# reviewer_node のプロンプト変更
task_index = state.get("task_index", 0)
f"レビュー結果を write_file で `docs/review_{task_index:02d}.md` に書き出してください。"

# 出力例: docs/review_00.md, docs/review_01.md, docs/review_02.md ...
```

---

```python
class DevAgentState(TypedDict):
    workspace_root: str
    model_tier: str
    task_list: list[str]
    current_task: str
    is_running: bool
    messages: list[BaseMessage]
    review_result: str      # Task 3 で追加
    needs_revision: bool    # Task 3 で追加
    revision_count: int     # Task 3 で追加
    task_index: int         # Task 7 で追加（レビューファイルの番号管理）
```

---

## 優先実装順

1. Task 1（workspace_root 渡し）← run_dev_agent が動作する前提条件
2. Task 2（plan.md パス統一）← エージェントが正しい計画を読む前提条件
3. Task 3（フィードバックループ）← 自律性の向上
4. Task 4（SSE通知）← VSCode表示との連携
5. Task 6（タスクキュー永続化）← 途中終了への耐性
6. Task 7（レビューファイルのタスク別出力）← レビュー結果の上書き防止
7. Task 5（git commit）← 最後の仕上げ
