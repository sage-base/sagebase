# 抽出ログ機能テストガイド

## 概要

このドキュメントでは、抽出層とGold Layer分離機能のテスト戦略とカバレッジについて説明します。

Issue #871（PBI-010）に基づき、全エンティティタイプでの品質を保証するテストスイートを提供します。

## テスト構成

### テストファイル一覧

```
tests/
├── integration/
│   ├── test_extraction_log_workflow.py      # 抽出ログワークフローテスト
│   ├── test_manual_verification_protection.py # 手動検証保護テスト
│   └── test_concurrent_updates.py           # 並行更新テスト
├── e2e/
│   ├── test_statement_extraction_e2e.py     # Statement E2Eテスト
│   ├── test_politician_extraction_e2e.py   # Politician E2Eテスト
│   ├── test_speaker_extraction_e2e.py      # Speaker E2Eテスト
│   ├── test_conference_member_extraction_e2e.py  # ConferenceMember E2Eテスト
│   └── test_parliamentary_group_member_extraction_e2e.py  # ParliamentaryGroupMember E2Eテスト
└── performance/
    └── test_extraction_log_performance.py   # パフォーマンステスト
```

## 対象エンティティタイプ

| EntityType | エンティティ | 説明 |
|------------|--------------|------|
| STATEMENT | Conversation | 議事録からの発言 |
| POLITICIAN | Politician | 政治家情報 |
| SPEAKER | Speaker | 発言者情報 |
| CONFERENCE_MEMBER | ExtractedConferenceMember | 会議体メンバー |
| PARLIAMENTARY_GROUP_MEMBER | ExtractedParliamentaryGroupMember | 議員団メンバー |

## 統合テスト

### test_extraction_log_workflow.py

全エンティティタイプで抽出ログワークフローが正しく動作することを検証します。

**テストケース：**
- `TestExtractionLogWorkflowForStatement` - STATEMENT抽出ログワークフロー
- `TestExtractionLogWorkflowForPolitician` - POLITICIAN抽出ログワークフロー
- `TestExtractionLogWorkflowForSpeaker` - SPEAKER抽出ログワークフロー
- `TestExtractionLogWorkflowForConferenceMember` - CONFERENCE_MEMBER抽出ログワークフロー
- `TestExtractionLogWorkflowForParliamentaryGroupMember` - PARLIAMENTARY_GROUP_MEMBER抽出ログワークフロー
- `TestExtractionLogWorkflowEdgeCases` - エッジケーステスト

**検証項目：**
1. 抽出実行後にログが保存される
2. エンティティが正しく更新される
3. `latest_extraction_log_id`が更新される

### test_manual_verification_protection.py

手動検証済みエンティティがAI更新から保護されることを検証します。

**テストケース：**
- 各エンティティタイプの手動検証保護
- 手動検証ライフサイクル（検証前→検証後→再抽出）

**検証項目：**
1. `is_manually_verified=True`のエンティティは更新されない
2. 更新がスキップされても抽出ログは保存される
3. `reason="manually_verified"`が返される

### test_concurrent_updates.py

並行した抽出更新でもデータ整合性が保たれることを検証します。

**テストケース：**
- 同一エンティティへの並行更新
- 異なるエンティティへの並行更新
- 異なるエンティティタイプへの並行更新
- レース条件（手動検証フラグ変更時）
- 一括抽出

**検証項目：**
1. 全ての抽出ログが保存される
2. ログIDの重複がない
3. エンティティの整合性が保たれる

## E2Eテスト

### 共通フロー

全エンティティタイプで以下のフローをテストします：

1. **初回抽出** - 新規エンティティに対するAI抽出
2. **ログ確認** - 抽出ログが正しく保存されていることを確認
3. **手動修正** - ユーザーによる修正と検証済みマーク
4. **再抽出** - AIによる再抽出の試行
5. **保護確認** - 手動修正が保護されていることを確認

### 各エンティティのE2Eテスト

#### Statement (Conversation)
- 議事録処理フロー
- 同一議事録内の複数発言
- 発言者紐付け保持
- 抽出履歴蓄積

#### Politician
- 政党ページからのスクレイピング
- マッチング処理（ログのみ記録）
- 一括抽出

#### Speaker
- 発言者抽出と政治家紐付け
- ルールベース→LLMマッチング遷移
- 発言者タイプ分類

#### ConferenceMember
- 会議体ページからの抽出
- 一括メンバー抽出
- 政治家マッチング

#### ParliamentaryGroupMember
- 議員団ページからの抽出
- 一括メンバー抽出
- 複数議員団にまたがる抽出

## パフォーマンステスト

### test_extraction_log_performance.py

**テストケース：**

| テスト | 目標 |
|--------|------|
| 1000件挿入 | 10秒以内 |
| 100件並行挿入 | 5秒以内 |
| 平均クエリ時間 | 5ms以内 |
| フィルタクエリ時間 | 10ms以内 |
| 500件エンティティ更新 | 5秒以内 |
| P99レスポンスタイム | 50ms以内 |

## テスト実行方法

### 統合テスト
```bash
# 全統合テスト
uv run pytest tests/integration/test_extraction_log_workflow.py tests/integration/test_manual_verification_protection.py tests/integration/test_concurrent_updates.py -v

# 特定のテストクラス
uv run pytest tests/integration/test_extraction_log_workflow.py::TestExtractionLogWorkflowForStatement -v
```

### E2Eテスト
```bash
# 全E2Eテスト
uv run pytest tests/e2e/ -v -m e2e

# 特定のエンティティタイプ
uv run pytest tests/e2e/test_statement_extraction_e2e.py -v
```

### パフォーマンステスト
```bash
# 全パフォーマンステスト
uv run pytest tests/performance/test_extraction_log_performance.py -v -m performance

# 特定のテスト
uv run pytest tests/performance/test_extraction_log_performance.py::TestExtractionLogInsertionPerformance -v
```

### 全テスト
```bash
uv run pytest -xvs
```

## CI/CD統合

統合テストは既存の`ci.yml`パイプラインで自動実行されます：

- **integration-other**ジョブ: 統合テストを実行
- **unit-tests**ジョブ: 単体テストを実行

## マーカー

テストには以下のマーカーが使用されています：

- `@pytest.mark.integration` - 統合テスト
- `@pytest.mark.e2e` - E2Eテスト
- `@pytest.mark.performance` - パフォーマンステスト
- `@pytest.mark.asyncio` - 非同期テスト

## モックの使用

全てのテストでLLM APIは呼び出されません：

1. `conftest.py`の`assert_no_real_llm_call`フィクスチャー
2. `mock_extraction_log_repo`によるリポジトリモック
3. `mock_session_adapter`によるセッションモック

## カバレッジ目標

- 統合テスト: 90%以上
- E2Eテスト: 主要フローの100%カバレッジ
- パフォーマンステスト: 全パフォーマンス要件のカバレッジ

## 注意事項

1. **テスト環境変数**: `TESTING=true`が自動設定されます
2. **データベース**: 統合テストはPostgreSQLサービスが必要です
3. **並行テスト**: 並行更新テストは実行順序に依存しません
4. **パフォーマンステスト**: CI環境では実行時間が長くなる可能性があります

## 関連ドキュメント

- [ARCHITECTURE.md](./ARCHITECTURE.md) - システムアーキテクチャ
- [TESTING_GUIDE.md](./TESTING_GUIDE.md) - テスト戦略全般
- [data-layer-architecture](./../.claude/skills/data-layer-architecture/SKILL.md) - Bronze/Gold Layer設計
