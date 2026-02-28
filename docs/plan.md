# AIエージェント実行計画

このファイルは自律開発エージェントが読み込む実行計画専用ファイルです。
人間向けの詳細な設計書は `.github/docs/tasks.md` を参照してください。

## 運用ルール

1. **目的**: エージェントに次に実装してほしいタスクを自然言語で記述する
2. **フォーマット**: 自由記述（箇条書き推奨）
3. **更新タイミング**: 
   - 人間が新しい機能を追加したい時
   - エージェントが全タスクを完了した後、次のイテレーションを開始する時

## 現在の実行計画

以下のタスクを優先的に実装してください：

### Task 2完了の確認
- dev_graph.py の _PLAN_PATH が正しく運用されているか確認
- このファイル（docs/plan.md）が実行計画専用として機能しているか検証

### 次の優先タスク

**Task 3: reviewer → coder フィードバックループ【重要度: 高】**
- `ai-agent/agent/state.py` に以下のフィールドを追加：
  - `review_result: str`
  - `needs_revision: bool`
  - `revision_count: int`
- `ai-agent/agent/dev_graph.py` の `reviewer_node` を修正して、レビュー結果を state に返すようにする
- `running_check_node` の条件分岐を拡張し、`needs_revision=True` かつ `revision_count < 2` の場合は coder に戻る
- 無限ループを防ぐため最大2回までの修正とする

**Task 7: レビュー結果のタスク別ファイル出力【重要度: 高】**
- `DevAgentState` に `task_index: int` フィールドを追加
- `planner_node` で `task_index = 0` に初期化
- `reviewer_node` のプロンプトを変更し、出力先を `docs/review_{task_index:02d}.md` に変更
- `running_check_node` で task_index をインクリメント

---

## 実装済みタスク

- ✅ Task 2: dev_graph の planner が読む plan.md のパス統一
  - B案採用: docs/plan.md を実行計画専用ファイルとして運用
  - .github/docs/tasks.md は人間向けの設計・方針ドキュメント
  - _PLAN_PATH = "docs/plan.md" を維持し、コメントで運用方針を明記
