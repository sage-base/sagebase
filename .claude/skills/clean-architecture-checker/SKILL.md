---
name: clean-architecture-checker
description: Verifies code follows Clean Architecture principles in Polibase. Activates when creating or modifying src/domain, src/application, src/infrastructure, or src/interfaces files. Checks dependency rules, entity independence, repository patterns, DTO usage, and type safety.
---

# Clean Architecture Checker

## Purpose
Verify that new code follows Clean Architecture principles as defined in the Polibase project.

## When to Activate
This skill activates automatically when:
- Creating or modifying files in `src/domain/`, `src/application/`, `src/infrastructure/`, or `src/interfaces/`
- Reviewing code changes across multiple layers
- Adding entities, repositories, use cases, or services

## Quick Checklist

Before approving code, verify:

- [ ] **Dependency Rule**: Dependencies point inward (Domain ← Application ← Infrastructure ← Interfaces)
- [ ] **Entity Independence**: Domain entities have no framework dependencies (no SQLAlchemy, Streamlit, etc.)
- [ ] **Repository Pattern**: All repos inherit from `BaseRepository[T]` and use async/await
- [ ] **DTO Usage**: DTOs used for layer boundaries, not raw entities
- [ ] **DTO Placement**: DTOは`src/application/dtos/`に配置（UseCaseファイル内に混在させない）
- [ ] **DTO型変更時の全層追跡**: DTOのフィールド型を変更した場合、Presenter層だけでなくView層（`src/interfaces/web/streamlit/views/`）も確認。`WebResponseDTO.data: dict[str, Any]`境界でpyrightの型チェックが効かないため手動確認が必須
- [ ] **UseCase間依存**: Orchestratorパターンとして許容される場合のみ（抽出ログ統合等）
- [ ] **Type Safety**: Complete type hints with proper `Optional` handling
- [ ] **Tests**: Unit tests for domain services and use cases
- [ ] **ドメインロジックの配置**: UseCase内で文字列リテラル比較やドメイン定数の直接参照でフィルタリングしていないか → エンティティのプロパティ/メソッドに移す
- [ ] **リポジトリ実装のDRY**: Raw SQLリポジトリでSELECTカラムリストが重複していないか → 定数に抽出。Row→Dict変換が重複していないか → ヘルパーメソッドに抽出
- [ ] **BaseRepositoryImplのオーバーライド**: Raw SQLリポジトリで `count()` 等のORMベースメソッドが正しく動作するか確認

## Core Principles

### 1. Dependency Rule
**Dependencies must point inward: Domain ← Application ← Infrastructure ← Interfaces**

✅ Domain imports nothing from outer layers
✅ Application only imports Domain
✅ Infrastructure imports Domain and Application
✅ Interfaces imports all inner layers (but not other Interface modules)

### 2. Entity Independence
**Domain entities must not depend on external frameworks**

✅ Use `@dataclass` or Pydantic `BaseModel`
❌ No SQLAlchemy models in Domain
❌ No UI framework imports in Domain

### 3. Repository Pattern
**All repositories follow async/await with ISessionAdapter**

✅ Interfaces in Domain: `class IRepo(BaseRepository[T])`
✅ Implementations in Infrastructure: `class RepoImpl(BaseRepositoryImpl[T], IRepo)`
✅ All methods are `async def`
✅ `_to_entity` / `_to_model` / `_update_model` は具体的なモデル型を使用（`Any` ではなく `XxxModel`）
✅ `sqlalchemy_models.py` に新規モデル追加時は既存モデルと一貫した `__repr__` メソッドを定義

### 4. DTO Pattern
**Always use DTOs between layers**

✅ DTOs in `src/application/dtos/`（専用ファイルに配置）
✅ Input DTO → Use Case → Output DTO
❌ Never expose domain entities directly to outer layers
❌ **UseCaseファイル内にDTO定義を混在させない**（Issue #969）

### 5. UseCase間依存（Orchestratorパターン）
**UseCase間依存は条件付きで許容**

✅ Orchestrator UseCase が 子UseCase を呼び出すパターンは許容
✅ 抽出ログ統合（`UpdateEntityFromExtractionUseCase`）への依存は許容（ADR-0005）
❌ UseCase間で循環依存を作らない
❌ Bronze Layer / Gold Layer の保護機構をバイパスしない

### 6. ドメインロジックの配置
**ビジネス判定ロジックはドメイン層（エンティティ/ドメインサービス）に配置する**

エンティティが定数リスト（`VALID_RESULTS`等）を持つ場合、その定数を使った判定はエンティティのプロパティとして定義する。UseCase内で文字列リテラルを直接比較してはいけない。

❌ UseCase内で文字列リテラルによるフィルタ:
```python
# Application層 - ドメイン知識がUseCaseに漏洩
elected = [m for m in members if m.result == "当選"]
```

✅ エンティティにプロパティを定義:
```python
# Domain層 - エンティティが判定ロジックを持つ
class ElectionMember(BaseEntity):
    ELECTED_RESULTS = ["当選", "繰上当選", "無投票当選"]

    @property
    def is_elected(self) -> bool:
        return self.result in self.ELECTED_RESULTS

# Application層 - エンティティのプロパティを使う
elected = [m for m in members if m.is_elected]
```

**なぜ重要か**: 定数リストに複数の関連値がある場合（「当選」「繰上当選」「無投票当選」等）、文字列リテラル比較では一部の値を見落とすリスクがある。エンティティに判定ロジックを集約することで、漏れを防ぎテストも容易になる。

### 7. Type Safety
**Leverage Python 3.11+ type hints**

✅ All public methods have type hints
✅ Use `T | None` for nullable types
✅ Explicit `None` checks for Optional values

### 8. リポジトリ実装のDRY原則
**Raw SQLリポジトリ実装で繰り返しコードを避ける**

#### SELECTカラムリストの定数化
複数メソッドで同じカラムリストを使うSQLリポジトリでは、モジュールレベル定数に抽出する。

```python
# ✅ 定数に抽出（1箇所で管理）
_SELECT_COLUMNS = """
    id, title, detail_url, status_url, meeting_id,
    created_at, updated_at
"""

async def get_all(self, ...) -> list[Entity]:
    query = text(f"SELECT {_SELECT_COLUMNS} FROM table_name ...")

async def get_by_id(self, id: int) -> Entity | None:
    query = text(f"SELECT {_SELECT_COLUMNS} FROM table_name WHERE id = :id")
```

```python
# ❌ 各メソッドにカラムリストをコピー（変更漏れの原因）
async def get_all(self, ...) -> list[Entity]:
    query = text("SELECT id, title, detail_url, ... FROM table_name ...")

async def get_by_id(self, id: int) -> Entity | None:
    query = text("SELECT id, title, detail_url, ... FROM table_name WHERE id = :id")
```

#### Row→Dict変換のヘルパーメソッド化
SQLAlchemyの `Row` オブジェクトをdictに変換するロジックが複数箇所にある場合、ヘルパーメソッドに抽出する。

```python
# ✅ ヘルパーメソッド
def _row_to_dict(self, row: Any) -> dict[str, Any]:
    if hasattr(row, "_asdict"):
        return row._asdict()
    elif hasattr(row, "_mapping"):
        return dict(row._mapping)
    return dict(row)
```

#### BaseRepositoryImplのcount()オーバーライド
`BaseRepositoryImpl.count()` はORMモデルに依存している。Raw SQLリポジトリでは `count()` をオーバーライドすること。

```python
# ✅ Raw SQLでオーバーライド
async def count(self) -> int:
    query = text("SELECT COUNT(*) FROM table_name")
    result = await self.session.execute(query)
    count = result.scalar()
    return count if count is not None else 0
```

## 既知の技術的負債

以下はプロジェクト全体に存在する技術的負債です。新規実装で同じパターンに遭遇した場合の判断材料としてください。

### 1. ドメインエンティティのView層への漏洩
**現状**: `Politician`エンティティがPresenter/View層で直接使用されている（`ElectionPresenter`、`ElectionMemberPresenter`、`GoverningBodyPresenter`等）。
**理想**: DTOを経由して外部層に公開すべき。
**方針**: 新規Presenterでは可能な限りDTOを使用するが、既存パターンとの一貫性も考慮する。プロジェクト全体のリファクタリングは別Issue対応。

### 2. Presenter→Repository直接利用
**現状**: 一部のPresenterがUseCaseを経由せずRepositoryを直接利用している（例: `politician_repo.get_all()`）。
**理想**: Presenterは常にUseCaseを経由すべき。
**方針**: 単純な読み取り操作（get_all等）についてはPresenterからの直接利用が慣例化している。ビジネスロジックを含む操作は必ずUseCaseを経由すること。

## Common Violations

See [examples.md](examples.md) for detailed good/bad code examples.

## Detailed Reference

For comprehensive architecture guidelines, see [reference.md](reference.md).

## Templates

Use templates in `templates/` directory for creating new:
- Domain entities
- Repository interfaces and implementations
- Use cases with DTOs
- Domain services

## References

- [CLEAN_ARCHITECTURE_MIGRATION.md](../../../docs/CLEAN_ARCHITECTURE_MIGRATION.md)
- [ARCHITECTURE.md](../../../docs/ARCHITECTURE.md)
- [tmp/clean_architecture_analysis_2025.md](../../../tmp/clean_architecture_analysis_2025.md)
