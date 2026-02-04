---
allowed-tools: Read, Glob, Grep, Bash, EnterPlanMode, ExitPlanMode, AskUserQuestion, mcp__serena__check_onboarding_performed, mcp__serena__delete_memory, mcp__serena__find_file, mcp__serena__find_referencing_symbols, mcp__serena__find_symbol, mcp__serena__get_symbols_overview, mcp__serena__list_dir, mcp__serena__list_memories, mcp__serena__onboarding, mcp__serena__read_memory, mcp__serena__search_for_pattern, mcp__serena__think_about_collected_information, mcp__serena__think_about_task_adherence, mcp__serena__think_about_whether_you_are_done, mcp__serena__write_memory, mcp__context7__resolve-library-id, mcp__context7__get-library-docs
description: GitHub Issueの解決方法をplanモードで相談するコマンド
---
planmode
ultrathink
# Issue解決相談ワークフロー

Issue番号: $ARGUMENTS

## 目的

このコマンドは、GitHub Issueの解決方法をユーザーと相談しながら計画するためのものです。
実装は行わず、**計画の立案と合意形成**に焦点を当てます。

---

## Phase 1: Issue内容の理解

### 1.1 Issue情報の取得

!gh issue view $ARGUMENTS

### 1.2 Issue内容の要約

上記のIssue内容を基に、以下をユーザーに提示してください：

1. **問題の概要**: Issueで報告されている問題を簡潔に説明
2. **期待される成果**: Issueが解決した状態とは何か
3. **受け入れ基準**: 明示されている場合は列挙

---

## Phase 2: コードベースの調査

serena MCPを使用して、関連するコードベースを調査します。

### 2.1 関連コードの特定

以下の観点で調査を行い、結果をユーザーに共有してください：

1. **関連ファイル/モジュールの特定**
   - Issueに関連するコード領域を特定
   - 既存の実装パターンを確認

2. **影響範囲の分析**
   - 変更が影響するファイル一覧
   - 依存関係の確認
   - テストへの影響

3. **既存の類似実装**
   - 参考になる既存コードがあれば提示
   - プロジェクトの規約やパターンを確認

### 2.2 調査結果の共有

調査結果をユーザーに分かりやすく提示し、認識を合わせてください。

---

## Phase 3: 解決方法の相談（対話形式）

ユーザーとの対話を通じて、最適な解決方法を検討します。

### 3.1 解決アプローチの提案

調査結果に基づいて、以下を提案してください：

1. **アプローチ案の提示**（複数ある場合は比較）
   - アプローチA: [概要]
     - メリット: [...]
     - デメリット: [...]
   - アプローチB: [概要]
     - メリット: [...]
     - デメリット: [...]

2. **推奨アプローチとその理由**
   - なぜこのアプローチを推奨するか
   - プロジェクトの既存パターンとの整合性

### 3.2 ユーザーへの確認事項

以下のような質問をユーザーに投げかけ、認識を合わせてください：

**質問例:**
- この解決方法で問題ないでしょうか？
- 追加で考慮すべき要件はありますか？
- 実装の優先度や制約はありますか？
- テストの範囲についてご要望はありますか？

### 3.3 懸念事項やリスクの共有

- 技術的な懸念点
- 実装上の注意点
- 既存機能への影響

---

## Phase 4: 実装計画の合意

ユーザーとの対話を経て、実装計画を固めます。

### 4.1 実装計画の作成

以下の形式で実装計画をまとめてください：

```markdown
# 実装計画: Issue #$ARGUMENTS

## 1. 概要
[解決する問題と採用するアプローチの要約]

## 2. 実装ステップ
1. [ステップ1]: [説明]
2. [ステップ2]: [説明]
3. [ステップ3]: [説明]

## 3. 変更予定ファイル
- `path/to/file1.py`: [変更内容の概要]
- `path/to/file2.py`: [変更内容の概要]

## 4. テスト計画
- [ ] [テスト項目1]
- [ ] [テスト項目2]

## 5. 注意事項
- [注意点1]
- [注意点2]
```

### 4.2 計画の承認依頼

**重要**: 計画が完成したら、`ExitPlanMode` ツールを使用してユーザーに計画を提示し、承認を求めてください。

---

## 完了後のアクション

計画が承認されたら、以下のいずれかを案内してください：

1. **すぐに実装を開始する場合**
   - `/solve_issue $ARGUMENTS` コマンドの使用を案内

2. **計画をIssueに記録する場合**
   - 計画内容をIssueにコメントとして追加

3. **別のタイミングで実装する場合**
   - 計画を `tmp/implementation_plan_$ARGUMENTS.md` に保存

---

## 注意事項

- このコマンドは**計画と相談のみ**を行います。コードの編集は行いません
- ユーザーとの対話を重視し、一方的に計画を進めないでください
- 不明点がある場合は、必ずユーザーに確認してください
- 複数のアプローチがある場合は、比較検討の材料を提示してください
