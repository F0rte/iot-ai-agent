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

**Task 3: reviewer → coder フィードバックループ【重要度: 高】**
- `ai-agent/agent/state.py` には `review_result: str`, `needs_revision: bool`, `revision_count: int` フィールドが既に追加済み
- `ai-agent/agent/dev_graph.py` の `reviewer_node` を修正して、レビュー結果（PASS/FAIL）と修正要否を state に返すようにする
- `running_check_node` の条件分岐を拡張し、`needs_revision=True` かつ `revision_count < 2` の場合は coder に戻る
- 無限ループを防ぐため最大2回までの修正とする

**Task 7: レビュー結果のタスク別ファイル出力【重要度: 高】**
- `ai-agent/agent/state.py` には `task_index: int` フィールドが既に追加済み
- `planner_node` で `task_index = 0` に初期化し、`run_dev_agent` の初期 state にも追加する
- `reviewer_node` のプロンプトを変更し、出力先を `docs/review_{task_index:02d}.md` に変更
- `running_check_node` で task_index をインクリメント
