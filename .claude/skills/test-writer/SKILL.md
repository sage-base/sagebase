---
name: test-writer
description: Guides test creation for Polibase following strict testing standards. Activates when writing tests or creating test files. Enforces external service mocking (no real API calls), async/await patterns, test independence, and proper use of pytest-asyncio to prevent CI failures and API costs.
---

# Test Writer

## Purpose
Guide test creation following Polibase testing standards with proper mocking, async/await patterns, and independence from external services.

## When to Activate
This skill activates automatically when:
- Writing new tests
- Creating test files in `tests/` directory
- User mentions "test", "pytest", or "testing"
- Reviewing existing test code

## ⚡ TDD Workflow (Test-First Development)

**ALWAYS write tests BEFORE implementation!**

### Red-Green-Refactor Cycle

1. **🔴 Red**: Write a failing test
   ```python
   # Write test first - it will fail (no implementation yet)
   @pytest.mark.asyncio
   async def test_create_politician_saves_to_repository():
       mock_repo = AsyncMock(spec=IPoliticianRepository)
       mock_repo.create.return_value = Politician(id=1, name="山田太郎")

       usecase = CreatePoliticianUseCase(mock_repo)
       result = await usecase.execute(CreatePoliticianInputDTO(name="山田太郎"))

       mock_repo.create.assert_awaited_once()
   ```

2. **🟢 Green**: Write minimal code to pass
   ```python
   # Now implement just enough to make test pass
   class CreatePoliticianUseCase:
       async def execute(self, input_dto):
           politician = Politician(name=input_dto.name)
           await self.repository.create(politician)
   ```

3. **♻️ Refactor**: Improve code while keeping tests green
   ```python
   # Refactor with confidence - tests verify behavior
   class CreatePoliticianUseCase:
       async def execute(self, input_dto):
           # Add validation
           if not input_dto.name:
               raise ValueError("Name required")
           # Extract to method
           politician = self._create_entity(input_dto)
           return await self.repository.create(politician)
   ```

### TDD Benefits
- ✅ Forces you to think about API design before implementation
- ✅ Tests serve as documentation
- ✅ Refactoring is safe (tests catch regressions)
- ✅ Code is naturally testable (designed for testing)

**Remember**: If you write implementation first, you're not doing TDD!

## 🚫 CRITICAL: Never Call External Services

**ABSOLUTELY FORBIDDEN in tests:**
- ❌ Real API calls to Google Gemini or any LLM
- ❌ Actual HTTP requests to external websites
- ❌ Real database connections (except integration tests)
- ❌ File system operations outside temp directories
- ❌ Network connections of any kind

**Why?**
- Tests must run in CI/CD without API keys
- Tests must be fast (< 1 second per test)
- Tests must be deterministic (same result every time)
- Tests must not incur API costs

## Quick Checklist

Before committing tests:

- [ ] **No External Calls**: All external services mocked
- [ ] **Fast Execution**: Each test runs in < 1 second
- [ ] **Isolated**: Tests don't depend on each other
- [ ] **Deterministic**: Same result every time
- [ ] **Clear Names**: Test name describes what it tests
- [ ] **Arrange-Act-Assert**: Clear test structure
- [ ] **Async Properly**: Uses `@pytest.mark.asyncio` and `AsyncMock`
- [ ] **Mock Verification**: Asserts mock calls when relevant
- [ ] **Type Hints**: Complete type annotations
- [ ] **Nullable Fields**: `T | None` フィールドは `None` ケースもテスト
- [ ] **List Results**: リスト返却メソッドは 0件・1件・複数件 をテスト
- [ ] **Private Method Calls**: `_to_entity` 等のプライベートメソッド呼び出しには `# type: ignore[reportPrivateUsage]` を付与
- [ ] **Entity Constructor**: テストデータ作成時、ドメインエンティティのコンストラクタ引数を実際のクラス定義で確認済み
- [ ] **Guard Clause Coverage**: `if x:` / `if x is None` 等のガードクローズは、`None`や空を返すケースもテスト
- [ ] **int | None の truthiness 罠**: `int | None` 型の変数を `if x:` で判定しない。`0` は有効値だが falsy と評価される → `if x is not None:` を使う
- [ ] **Domain Constant Coverage**: エンティティの定数リスト（`VALID_RESULTS`等）でフィルタする場合、全値パターンをテスト（特に類似値: 「当選」と「繰上当選」「無投票当選」等）
- [ ] **テストデータの順序**: ソートやグループ化を検証する場合、テストデータは意図的に期待順序と異なる並びで提供し、実装のソート処理が実際に機能することを検証する
- [ ] **述語関数のパラメタライズドテスト**: 判定ロジック（`_is_retryable`等）の純粋関数は `@pytest.mark.parametrize` で全分岐パターン（True/False両方）を網羅する
- [ ] **コードパス到達確認**: テスト名が示す検証対象のコードパスに実際に到達するか確認する。モックのセットアップにより早期リターンされ、検証対象のコードが実行されないテストは無意味（下記アンチパターン12参照）

## リポジトリテストの網羅性

リポジトリ実装のテストでは、**全publicメソッド**に対してテストを作成すること。新しいメソッドだけでなく、既存メソッドのテスト漏れも確認する。

### チェックリスト
- [ ] **全publicメソッドにテストがあるか**: リポジトリインターフェースの全メソッド + `count()` 等の `BaseRepositoryImpl` メソッド
- [ ] **正常系**: 成功パス（データあり）
- [ ] **空結果**: データなし・0件の場合
- [ ] **エラー系**: `DatabaseError` 発生時
- [ ] **境界値**: limit=0, limit=None 等

### よくあるテスト漏れパターン

```python
# ❌ 新メソッドのテストのみ追加し、既存メソッドを放置
class TestNewRepo:
    def test_new_method(self): ...  # 新メソッドだけテスト

# ✅ 既存メソッドも含めて全publicメソッドをテスト
class TestNewRepo:
    def test_get_all_with_limit(self): ...
    def test_get_all_without_limit(self): ...
    def test_get_all_empty(self): ...
    def test_get_by_id_found(self): ...
    def test_get_by_id_not_found(self): ...
    def test_count_success(self): ...
    def test_count_empty(self): ...
    def test_new_method(self): ...
```

## Test Structure

```
tests/
├── unit/              # Fast, isolated tests
│   ├── domain/       # Domain entities and services
│   ├── application/  # Use cases (with mocks)
│   └── infrastructure/  # External services (with mocks)
├── integration/       # Tests with real database
├── evaluation/       # LLM evaluation (manual only, not in CI)
└── conftest.py       # Shared fixtures
```

## Core Testing Patterns

### 1. Mocking External Services

**Always use `AsyncMock` with `spec=` parameter:**
```python
from unittest.mock import AsyncMock

@pytest.fixture
def mock_llm_service():
    # ALWAYS use spec= to catch typos and wrong method calls
    mock = AsyncMock(spec=ILLMService)
    mock.generate_text.return_value = "Mocked response"
    return mock
```

**⚠️ Why `spec=` is CRITICAL:**
```python
# ❌ WITHOUT spec= - typos go undetected
mock = AsyncMock()
await mock.genrate_text("prompt")  # Typo! Test still passes!

# ✅ WITH spec= - typos caught immediately
mock = AsyncMock(spec=ILLMService)
await mock.genrate_text("prompt")  # AttributeError!
```

**Use `AsyncMock` for async methods, never `MagicMock`:**
```python
# ❌ WRONG - MagicMock for async function
mock_repo = MagicMock(spec=IPoliticianRepository)
result = await mock_repo.create(politician)  # Error!

# ✅ CORRECT - AsyncMock for async function
mock_repo = AsyncMock(spec=IPoliticianRepository)
result = await mock_repo.create(politician)  # Works!
```

### 2. Async Tests

**Use pytest-asyncio:**
```python
@pytest.mark.asyncio
async def test_async_function(mock_repo):
    result = await usecase.execute(input_dto)
    assert result.success
```

### 3. Test Independence

**Each test is self-contained:**
```python
def test_create_politician(mock_repo):
    # Setup mock
    mock_repo.save.return_value = Politician(id=1, name="Test")

    # Execute
    result = usecase.execute(input_dto)

    # Assert
    assert result.success
```

## Templates

Use templates in `templates/` directory for:
- Domain service tests
- Use case tests with mocks
- Repository integration tests
- External service tests with mocks

## Detailed Reference

For comprehensive testing patterns, mocking strategies, and best practices, see [reference.md](reference.md).

## Examples

See [examples.md](examples.md) for concrete test examples at each layer.

## Running Tests

```bash
# Run all tests
docker compose -f docker/docker-compose.yml [-f docker/docker-compose.override.yml] exec sagebase uv run pytest

# Run specific test file
docker compose -f docker/docker-compose.yml [-f docker/docker-compose.override.yml] exec sagebase uv run pytest tests/unit/domain/test_speaker_domain_service.py

# Run with coverage
docker compose -f docker/docker-compose.yml [-f docker/docker-compose.override.yml] exec sagebase uv run pytest --cov=src

# Run only unit tests
docker compose -f docker/docker-compose.yml [-f docker/docker-compose.override.yml] exec sagebase uv run pytest tests/unit/
```

## テストヘルパーの配置ルール

複数のテストファイルで使うヘルパー関数（レコードファクトリ等）は、**最初から`tests/fixtures/`に配置する**こと。
ローカルヘルパーとして書いた後にコピペで別ファイルに持ち込むと重複が生まれる。

```python
# ❌ 悪い例 - 同じヘルパーを複数テストファイルにコピペ
# tests/infrastructure/test_importer.py
def _make_record_with_judges(...): ...

# tests/application/test_usecase.py
def _make_record_with_judges(...): ...  # 重複！

# ✅ 良い例 - 共通ファクトリに配置してインポート
# tests/fixtures/smri_record_factories.py
def make_smri_record_with_judges(...): ...

# tests/infrastructure/test_importer.py
from tests.fixtures.smri_record_factories import make_smri_record_with_judges
```

**判断基準**: ヘルパーが2つ以上のテストファイルで必要になると分かっている場合は、最初から`tests/fixtures/`に作成する。

## CLI→UseCase引数のマッピング検証

CLIコマンドのテストでは、**CLIオプションがUseCaseの入力DTOに正しくマッピングされたか**を検証すること。
出力文字列のチェックだけでは、オプション値がDTOに反映されているかわからない。

```python
# ❌ 悪い例 - 出力文字列のみチェック（DTOマッピングは未検証）
result = runner.invoke(cmd, ["--session-from", "1", "--name-of-house", "衆議院"])
assert "衆議院" in result.output  # 出力に表示されてるだけ

# ✅ 良い例 - DTOの中身まで検証
result = runner.invoke(cmd, ["--session-from", "1", "--name-of-house", "衆議院"])
input_dto = mock_usecase.execute.call_args[0][0]
assert isinstance(input_dto, BatchImportInputDTO)
assert input_dto.session_from == 1
assert input_dto.name_of_house == "衆議院"
```

## bulk操作テストの検証ルール

`bulk_create`や`bulk_update`等のバルク操作を呼ぶUseCaseをテストする場合、**呼ばれたことだけでなく、渡された引数の中身も検証する**こと。

```python
# ❌ 悪い例 - 呼ばれたかだけ確認
mock_repo.bulk_create.assert_called_once()

# ✅ 良い例 - 引数の中身まで検証
mock_repo.bulk_create.assert_called_once()
entities = mock_repo.bulk_create.call_args[0][0]
assert len(entities) == 2
sansei = [e for e in entities if e.judgment == "賛成"][0]
assert sorted(sansei.parliamentary_group_ids) == [8, 18]
```

また、bulk操作後の副作用（`mark_processed`等）も漏れなく検証すること。

```python
# ✅ 副作用の検証
assert mock_repo.mark_processed.call_count == 3
processed_ids = sorted(
    call.args[0] for call in mock_repo.mark_processed.call_args_list
)
assert processed_ids == [1, 2, 3]
```

## Common Anti-Patterns

1. **❌ Real API Calls**: Most common mistake!
2. **❌ Testing Implementation Details**: Test public interfaces
3. **❌ Test Dependencies**: Each test must be independent
4. **❌ Missing Async/Await**: Forget `@pytest.mark.asyncio`
5. **❌ No Mock Verification**: Don't check if mocks were called
6. **❌ `return` in `patch` fixture**: `with patch(...)` 内で `return` するとpatchスコープが切れる → `yield` を使う
7. **❌ 内部メソッドのモック上書き**: `presenter._run_async = MagicMock(...)` はプロダクションコードの検証をバイパスする
8. **❌ ドメインエンティティのコンストラクタ引数ミス**: テストデータ作成時に存在しないキーワード引数を使用 → 必ず`find_symbol`等でコンストラクタを確認する
9. **❌ bulk操作の引数未検証**: `bulk_create.assert_called_once()` だけで、渡されたエンティティの中身を検証していない
10. **❌ ローカルインポートのパッチパス誤り**: 関数内でローカルインポートされたシンボルは、モジュール属性にならないため `patch("module.symbol")` でパッチできない → インポート元モジュールでパッチする
11. **❌ `spec=` なしの `AsyncMock`/`MagicMock`**: 存在しないメソッド名のタイプミスが検出されず偽陽性テストになる → **常に `spec=` を付ける**
12. **❌ 検証対象コードパスに到達しないテスト**: モックのセットアップ（例: 空リスト返却）で早期リターンされ、テスト名が示す対象コード（例: `as_of_date`がリポジトリに渡される）に実際には到達しない → テストデータをセットアップして対象コードパスまで到達させること

See [reference.md](reference.md) for detailed explanations and fixes.
