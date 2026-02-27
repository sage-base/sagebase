---
allowed-tools: Read, Glob, Grep, Edit, MultiEdit, Write, Bash, TodoWrite, ExitPlanMode, mcp__serena__check_onboarding_performed, mcp__serena__delete_memory, mcp__serena__find_file, mcp__serena__find_referencing_symbols, mcp__serena__find_symbol, mcp__serena__get_symbols_overview, mcp__serena__insert_after_symbol, mcp__serena__insert_before_symbol, mcp__serena__list_dir, mcp__serena__list_memories, mcp__serena__onboarding, mcp__serena__read_memory, mcp__serena__remove_project, mcp__serena__replace_regex, mcp__serena__replace_symbol_body, mcp__serena__restart_language_server, mcp__serena__search_for_pattern, mcp__serena__switch_modes, mcp__serena__think_about_collected_information, mcp__serena__think_about_task_adherence, mcp__serena__think_about_whether_you_are_done, mcp__serena__write_memory, mcp__context7__resolve-library-id, mcp__context7__get-library-docs
description: GitHub Issueを自動的に解決するコマンド
---
planmode
ultrathink
# Issue解決ワークフロー

Issue番号: $ARGUMENTS

## Phase 1: プランニング（Plan Mode）

このフェーズでは、実装計画を立ててユーザーに提示します。

### 1. Issue内容の確認

!gh issue view $ARGUMENTS

### 2. ブランチ状態の確認

現在のブランチ状態を確認します。

!git status

### 3. 実装計画の立案

上記のIssue内容を基に、以下の観点で実装計画を作成してください：

1. **問題の理解**
   - Issueで報告されている問題を正確に理解する
   - 受け入れ基準を確認する

2. **コードベースの調査**
   - serena MCPを使用して関連するコードを調査する
   - 必要なファイルの変更を特定する
   - 既存の実装パターンを確認する

3. **技術的な解決策**
   - 実装方法を検討する
   - 必要なファイルの変更を特定する
   - ユニットテストが必要な箇所を特定する
   - アーキテクチャへの影響を評価する

4. **実装計画の作成**
   - タスクを細分化する
   - 各タスクの説明と実装方針を明確にする
   - 実装の順序を決定する
   - リスクと注意点を洗い出す

**重要**: 計画が完成したら、必ず`ExitPlanMode`ツールを使用して、計画をユーザーに提示してください。
ユーザーの承認を得てから実装フェーズに進みます。

---

## Phase 2: 実装（Implementation Mode）

**注意**: このフェーズは、ユーザーが上記の計画を承認した後に実行されます。

### 4. ブランチの作成

必要に応じて新しいブランチを作成します（まだ作成していない場合）。

### 5. 実装

以下の手順で実装を進めてください：

1. **コードの実装**
   - 特定したファイルを修正する
     - serena MCPを使用して関連するコードを調査し、必要な変更を行います。
       - DRY原則に従い、重複コードを避けます
     - context7 MCPを使用してライブラリのドキュメントを確認し、適切なAPIとパッケージを使用します
   - 必要に応じて新しいファイルを作成する
   - コーディング規約に従う（Ruff、型チェック）

2. **ユニットテストの作成**
   - 新しい機能や修正した機能に対するテストを作成する
   - 既存のテストが壊れていないことを確認する

### 6. 動作確認

実装が完了したら、以下の動作確認を実行してください：

1. **機能の動作確認**
   - 実装した機能が期待通りに動作することを確認する
   - エッジケースも考慮する

2. **実データでの動作確認**（DB変更やクエリ変更がある場合）
   - `docker ps` でPostgreSQLコンテナが起動しているか確認する
   - 起動している場合は、実データを使った動作確認スクリプトを `tmp/` に作成して実行する
   - DB変更がある場合はマイグレーションSQLを直接適用し、リポジトリのクエリが実データに対して正しく動作するか確認する
   - テスト用に変更したデータは必ず元に戻す（スクリプト内で自動リセット）

3. **コード品質チェック**
   uv run --frozen ruff format .
   uv run --frozen ruff check . --fix
   uv run --frozen pyright

### 7. テストの実行

全てのテストが成功することを確認してください：

uv run pytest -xvs

テストが失敗した場合は、修正を行い再度テストを実行してください。

### 8. コミット

1. **変更内容の確認**
   !git status
   !git diff

2. **コミット**
   変更をコミットし、Issue番号を含むコミットメッセージを作成してください。

---

## Phase 3: プルリクエスト作成（必須）

**注意**: テストとコード品質チェックが全てパスしたら、**必ずPR作成まで完了させてください**。
ユーザーに「PRを作りますか？」と聞かずに、自動的にPR作成まで進めてください。

### 9. プッシュとPR作成

1. **リモートにプッシュ**
   !git push -u origin HEAD

2. **プルリクエストを `gh pr create` で作成**

   以下の形式で作成してください：

   ```bash
   gh pr create --title "<簡潔なタイトル>" --body "$(cat <<'EOF'
   ## 概要
   <実装内容の説明（1-3行）>

   ## 変更内容
   - <変更点1>
   - <変更点2>
   - ...

   ## テスト
   - <テスト内容の要約>

   Fixes #<Issue番号>

   🤖 Generated with [Claude Code](https://claude.com/claude-code)
   EOF
   )"
   ```

   - **タイトル**: 70文字以内で変更内容を簡潔に表現
   - **本文**: 概要、変更内容、テスト内容を含める
   - **Issue番号**: `$ARGUMENTS` からIssue番号を抽出して `Fixes #<番号>` を記載

3. **PR作成結果の報告**
   作成されたPRのURLをユーザーに報告してください。

## 注意事項

- 各ステップで問題が発生した場合は、その都度修正を行ってください
- テストが全て成功するまでプルリクエストは作成しないでください
  - Github Actionsの予算が少なくJob時間制限があるため不要なCIを実行させないためです。
- コーディング規約（Ruff、型チェック）を遵守してください
- **PR作成は必須です** - `/solve_issue` の完了条件にはPR作成が含まれます
