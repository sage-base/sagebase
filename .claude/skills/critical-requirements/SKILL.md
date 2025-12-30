---
name: critical-requirements
description: Sagebase開発時に常に意識すべき重要なルールと制約を提供します。Pre-commit hooks遵守、API Key設定、処理順序、ファイル管理、テストのモックなど、違反するとエラーになる情報を含みます。コミット前、ファイル作成時、データ処理実行前、テスト作成時にアクティベートします。
---

# Critical Requirements（重要な要件と制約）

## 目的
Sagebaseプロジェクトの開発時に**絶対に守るべきルールと制約**を提供します。これらの要件を違反すると、ビルドエラー、テスト失敗、データ破損、セキュリティ問題などの深刻な問題が発生する可能性があります。

このスキルは、開発者が重要なルールを見落とさないよう、コミット前、ファイル作成時、データ処理実行前などの重要なタイミングで自動的にアクティベートされます。

## いつアクティベートするか
- **git commit**を実行する前（Pre-commit hooksの遵守確認）
- 新しいファイルを作成する時（ファイル配置ルールの確認）
- データ処理（議事録処理、話者マッチングなど）を実行する時（処理順序、API Keyの確認）
- テストを書く時（モック要件の確認）
- GCS（Google Cloud Storage）操作を行う時（認証、URI形式の確認）
- データベースマイグレーションを作成する時
- 一時ファイルや中間ファイルを作成する時

## クイックチェックリスト

### コミット前
- [ ] **Pre-commit hooksのエラーを修正**（`--no-verify`は**絶対に使用しない**）
- [ ] すべてのテストが成功している
- [ ] コードフォーマット（ruff format）が適用されている
- [ ] 型チェック（pyright）が通っている

### ファイル作成時
- [ ] 一時ファイルは`tmp/`ディレクトリに配置
- [ ] 知識蓄積ファイルは`_docs/`ディレクトリに配置
- [ ] プロダクションコードに一時ファイルのパスを含めていない

### データ処理実行前
- [ ] `GOOGLE_API_KEY`が`.env`に設定されている
- [ ] 処理順序を遵守（`process-minutes → extract-speakers → update-speakers`）
- [ ] GCS操作前に`gcloud auth application-default login`を実行

### テスト作成時
- [ ] 外部サービス（LLM、API）を**必ずモック**している
- [ ] 実際のAPI呼び出しを行っていない
- [ ] pytest-asyncioを使用した非同期テストになっている

### データベース操作時
- [ ] マイグレーションファイルを`database/02_run_migrations.sql`に追加
- [ ] マスターデータ（governing bodies、conferences）を変更していない
- [ ] マイグレーションの連番が正しい

## 詳細なガイドライン

### 1. Critical Requirements（必須要件）

#### API Key Required
**要件**: `GOOGLE_API_KEY`を`.env`に設定する必要があります。

**理由**: Gemini APIアクセスに必須です。

**確認方法**:
```bash
# .envファイルにGOOGLE_API_KEYが設定されているか確認
grep GOOGLE_API_KEY .env
```

**エラー例**:
```
Error: GOOGLE_API_KEY environment variable not set
```

#### Processing Order（処理順序）
**要件**: 議事録処理は必ず以下の順序で実行します。

```
process-minutes → extract-speakers → update-speakers
```

**理由**: データの依存関係により、順序を守らないとデータ不整合が発生します。

**コマンド例**:
```bash
# 正しい順序
just process-minutes
just extract-speakers
just update-speakers
```

#### GCS Authentication（GCS認証）
**要件**: GCS操作前に認証を行う必要があります。

**コマンド**:
```bash
gcloud auth application-default login
```

**理由**: Google Cloud Storage へのアクセスに必須です。

---

### 2. File Management（ファイル管理）

#### Intermediate Files（中間ファイル）
**要件**: **すべての一時ファイルは`tmp/`ディレクトリに作成**します。

**理由**:
- `tmp/`は`.gitignore`に含まれており、Gitにコミットされない
- プロジェクトのルートディレクトリを汚さない

**正しい例**:
```python
# ✅ 良い例
output_path = "tmp/intermediate_data.json"
with open(output_path, "w") as f:
    json.dump(data, f)
```

**悪い例**:
```python
# ❌ 悪い例
output_path = "intermediate_data.json"  # ルートディレクトリに作成される
with open(output_path, "w") as f:
    json.dump(data, f)
```

#### Knowledge Base（知識蓄積層）
**要件**: 重要な意思決定や知見は`_docs/`ディレクトリに記録します。

**理由**:
- `_docs/`は`.gitignore`に含まれており、Claudeのメモリとして機能
- プロジェクトの歴史や決定事項を記録

**使用例**:
```bash
# 重要な決定を記録
echo "## BAML採用の理由\n..." > _docs/decision-baml.md
```

---

### 3. Code Quality（コード品質）

#### Pre-commit Hooks（必須）
**要件**: **`--no-verify`は絶対に使用しない**。Pre-commit hooksのエラーは必ず修正してからコミットします。

**理由**:
- コード品質を保証するための最後の砦
- CI/CDで同じチェックが走るため、事前に修正することでCI時間を節約

**Pre-commit hooksの内容**:
- `ruff check`: Lintチェック
- `ruff format`: コードフォーマット
- `pyright`: 型チェック
- `pytest`: 単体テスト（ユニットテストのみ）

**正しい対応**:
```bash
# ✅ 良い例：エラーを修正してから再度コミット
git commit -m "fix: bug fix"
# → Pre-commit hooksでエラー発生
# → エラーを修正
git add .
git commit -m "fix: bug fix"
```

**悪い例**:
```bash
# ❌ 悪い例：--no-verifyでスキップ
git commit -m "fix: bug fix" --no-verify
```

#### Testing（テストのモック要件）
**要件**: **外部サービス（LLM、API）は必ずモック**します。

**理由**:
- テスト実行のたびにAPIコストが発生することを防ぐ
- CI/CDでの実行時間短縮
- テストの再現性とスピードを保証

**正しい例**:
```python
# ✅ 良い例：LLMサービスをモック
@pytest.fixture
def mock_llm_service():
    mock = AsyncMock(spec=ILLMService)
    mock.generate_text.return_value = "モックされた応答"
    return mock

async def test_process_minutes(mock_llm_service):
    processor = MinutesProcessor(llm_service=mock_llm_service)
    result = await processor.process(...)
    assert result is not None
```

**悪い例**:
```python
# ❌ 悪い例：実際のAPIを呼び出し
async def test_process_minutes():
    llm_service = GeminiLLMService()  # 実際のAPI呼び出し
    processor = MinutesProcessor(llm_service=llm_service)
    result = await processor.process(...)
    assert result is not None
```

#### CI/CD
**要件**: スキップしたテストには**必ずIssueを作成**します。

**理由**: `continue-on-error: true`を使用したテストは、失敗が見過ごされる可能性があるため、Issueで追跡します。

**対応例**:
```yaml
# CI設定で continue-on-error: true を使った場合
- name: Run flaky test
  run: pytest tests/flaky_test.py
  continue-on-error: true
```

その後、GitHubでIssueを作成：
```markdown
# Issueタイトル
CI: flaky_testが不安定なため修正が必要

# Issue本文
`tests/flaky_test.py`が不安定で、CI/CDで`continue-on-error: true`を設定しています。
原因を特定して修正する必要があります。
```

---

### 4. Database（データベース）

#### Master Data（マスターデータ）
**要件**: Governing bodies（統治機構）とconferences（会議体）は**固定のマスターデータ**です。変更しないでください。

**理由**: システム全体で共通して使用されるデータであり、変更すると既存データとの不整合が発生します。

**マスターデータの例**:
- 統治機構：国、都道府県、市区町村
- 会議体：衆議院、参議院、都道府県議会、市区町村議会

#### Coverage（カバレッジ）
**情報**: 全国1,966の自治体が組織コードで追跡されています。

#### Migrations（マイグレーション）
**要件**: 新しいマイグレーションは**必ず**`database/02_run_migrations.sql`に追加します。

**理由**: データベーススキーマの一貫性を保証するため。

**手順**:
1. 新しいマイグレーションファイルを作成（例：`013_create_new_table.sql`）
2. `database/02_run_migrations.sql`に追加

```sql
-- 02_run_migrations.sql
\i 001_initial_schema.sql
\i 002_add_indexes.sql
...
\i 013_create_new_table.sql  -- 新しいマイグレーションを追加
```

---

### 5. Development（開発）

#### Docker-first
**要件**: **すべてのコマンドはDockerコンテナ経由で実行**します。

**理由**: 環境の一貫性を保証し、「手元では動くがCIで動かない」を防ぎます。

**正しい例**:
```bash
# ✅ 良い例：Dockerコンテナ経由
just test
just format
just lint
```

**悪い例**:
```bash
# ❌ 悪い例：ローカル環境で直接実行
pytest
ruff check .
```

#### Unified CLI
**要件**: `sagebase`コマンドを統一エントリーポイントとして使用します。

**例**:
```bash
# Sagebase CLIを使用
sagebase process-minutes
sagebase extract-speakers
```

#### GCS URI Format
**要件**: GCS URIは**必ず`gs://`形式**を使用します。HTTPS URLは使用しません。

**正しい例**:
```python
# ✅ 良い例
gcs_uri = "gs://my-bucket/path/to/file.pdf"
```

**悪い例**:
```python
# ❌ 悪い例
gcs_uri = "https://storage.googleapis.com/my-bucket/path/to/file.pdf"
```

---

## リファレンス

詳細な技術情報は以下のドキュメントを参照してください：
- [project-conventions](../project-conventions/): プロジェクト全体の規約
- [development-workflows](../development-workflows/): 開発ワークフロー
- [test-writer](../test-writer/): テスト作成ガイド
- [migration-helper](../migration-helper/): データベースマイグレーション

## 違反時の対処法

### Pre-commit hooksでエラーが出た場合
1. エラーメッセージを確認
2. 該当ファイルを修正
3. `git add .`で変更をステージング
4. 再度`git commit`

### API Keyエラーが出た場合
1. `.env.example`をコピーして`.env`を作成
2. `GOOGLE_API_KEY`を設定
3. アプリケーションを再起動

### GCS認証エラーが出た場合
```bash
# 認証を実行
gcloud auth application-default login

# 認証状態を確認
gcloud auth list
```

### テストでモックし忘れた場合
1. テストファイルを開く
2. 外部サービスを`AsyncMock`でモック
3. fixtureとして定義
4. テスト関数で使用

---

## まとめ

このスキルで提供される要件は、**Sagebaseプロジェクトの品質と一貫性を保証するための最低限のルール**です。これらを守ることで：

✅ ビルドエラーを防ぐ
✅ テスト失敗を防ぐ
✅ データ不整合を防ぐ
✅ セキュリティ問題を防ぐ
✅ APIコストを抑える
✅ CI/CD時間を短縮する

**違反すると重大な問題が発生する可能性があるため、必ずこのスキルのチェックリストを確認してください。**
