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
- [ ] **Type Safety**: Complete type hints with proper `Optional` handling. `**kwargs`展開ではなく明示的引数渡しを使用
- [ ] **UseCase内N+1クエリ回避**: UseCaseのメソッド間でIDリストだけ渡して`get_by_id`で再取得していないか → メモリ上で必要な情報を受け渡す
- [ ] **Tests**: Unit tests for domain services and use cases
- [ ] **ドメインロジックの配置**: UseCase内で文字列リテラル比較やドメイン定数の直接参照でフィルタリングしていないか → エンティティのプロパティ/メソッドに移す
- [ ] **リポジトリ実装のDRY**: Raw SQLリポジトリでSELECTカラムリストが重複していないか → 定数に抽出。Row→Dict変換が重複していないか → ヘルパーメソッドに抽出
- [ ] **BaseRepositoryImplのオーバーライド**: Raw SQLリポジトリで `count()`, `get_by_ids()` 等のORMベースメソッドが正しく動作するか確認（Pydanticモデル系では必ずraw SQLでオーバーライド）
- [ ] **新規リポジトリ作成方針（ADR 0007）**: 新規リポジトリはSQLAlchemy ORM第一選択、Pydanticは既存拡張時のみ許容、動的モデルは新規禁止。変換メソッドは`_to_entity()`のみ使用
- [ ] **オーバーライドのシグネチャ一致**: BaseRepository IFのデフォルト値（`offset: int | None = None`等）と実装のシグネチャが一致しているか
- [ ] **`_to_entity`/`_dict_to_entity`の一貫性**: 両メソッドで`created_at`/`updated_at`の設定が一致しているか

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

### 7. UseCase内のN+1クエリ回避
**UseCaseのメソッド間でデータを受け渡す際、DBに再クエリしない**

UseCaseの`execute`メソッドで取得・計算済みのデータを、プライベートメソッドに渡す際はIDリストだけでなく必要な情報をメモリ上で受け渡す。IDだけ渡して`get_by_id`で再取得するN+1クエリパターンは避ける。

❌ IDリストだけ渡して再取得（N+1クエリ）:
```python
async def execute(self, input_dto):
    matched_ids = []
    for judge in pending:
        group_id = name_to_id.get(judge.name)
        if group_id:
            matched_ids.append(judge.id)  # IDだけ蓄積
    await self._create_gold(matched_ids)

async def _create_gold(self, ids: list[int]):
    for id in ids:
        judge = await self._repo.get_by_id(id)  # N回のDB呼び出し！
```

✅ 必要な情報をメモリ上で受け渡す:
```python
@dataclass
class _MatchedInfo:
    judge_id: int
    proposal_id: int
    judgment: str
    group_id: int

async def execute(self, input_dto):
    matched_infos = []
    for judge in pending:
        group_id = name_to_id.get(judge.name)
        if group_id:
            matched_infos.append(_MatchedInfo(...))  # 全情報を蓄積
    await self._create_gold(matched_infos)

async def _create_gold(self, infos: list[_MatchedInfo]):
    for info in infos:  # DB再取得不要
        grouped[key].append(info.group_id)
```

### 8. Type Safety
**Leverage Python 3.11+ type hints**

✅ All public methods have type hints
✅ Use `T | None` for nullable types
✅ Explicit `None` checks for Optional values
✅ `**kwargs`展開ではなく明示的引数渡しを使用

#### `**kwargs`展開の禁止

UseCaseからリポジトリメソッドを呼び出す際、辞書にフィルター条件を溜めて`**kwargs`で展開するパターンは型安全性を損なうため避ける。

```python
# ❌ BAD: dict展開で型情報が失われる（`Any`が必要になる）
filter_kwargs: dict[str, Any] = {}
if meeting_id:
    filter_kwargs["meeting_id"] = meeting_id
if deliberation_status:
    filter_kwargs["deliberation_status"] = deliberation_status

proposals = await repo.get_filtered_paginated(**filter_kwargs)
total = await repo.count_filtered(**filter_kwargs)
```

```python
# ✅ GOOD: 明示的引数渡し（pyrightが各引数の型を検証できる）
meeting_id_filter: int | None = None
if filter_type == "by_meeting" and input_dto.meeting_id:
    meeting_id_filter = input_dto.meeting_id

proposals = await repo.get_filtered_paginated(
    meeting_id=meeting_id_filter,
    deliberation_status=input_dto.deliberation_status,
    limit=input_dto.limit,
    offset=input_dto.offset,
)
total = await repo.count_filtered(
    meeting_id=meeting_id_filter,
    deliberation_status=input_dto.deliberation_status,
)
```

**なぜ重要か**: `dict[str, int | str | None]`のような共用体型の辞書を`**`展開すると、pyrightは各パラメータの型を個別に検証できず型エラーになる。`dict[str, Any]`に逃げると型チェックが無効化される。明示的引数渡しならpyrightが各引数の型を正確に検証できる。

### 9. リポジトリ実装のDRY原則
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

#### BaseRepositoryImplのORMベースメソッドのオーバーライド
`BaseRepositoryImpl` の以下のメソッドはORMモデル（`select(model_class)`）に依存しているため、Pydantic/動的モデル系のリポジトリではraw SQLでオーバーライドが**必須**。

| メソッド | 内部で使用するAPI | Pydanticモデルでの問題 |
|---------|-----------------|---------------------|
| `count()` | `select(func.count()).select_from(model_class)` | model_classにテーブルマッピングがない |
| `get_by_ids()` | `select(model_class).where(model_class.id.in_(...))` | model_classに`id`カラム属性がない |

```python
# ✅ Raw SQLでオーバーライド
async def count(self) -> int:
    query = text("SELECT COUNT(*) FROM table_name")
    result = await self.session.execute(query)
    count = result.scalar()
    return count if count is not None else 0

async def get_by_ids(self, entity_ids: list[int]) -> list[Entity]:
    if not entity_ids:
        return []
    placeholders = ", ".join(f":id_{i}" for i in range(len(entity_ids)))
    query = text(f"SELECT {_SELECT_COLUMNS} FROM table_name WHERE id IN ({placeholders})")
    params = {f"id_{i}": eid for i, eid in enumerate(entity_ids)}
    result = await self.session.execute(query, params)
    return self._rows_to_entities(result.fetchall())
```

#### オーバーライド時の注意点

**シグネチャの一致**: BaseRepository IFのメソッドをオーバーライドする際、デフォルト値を含むシグネチャを正確に一致させること。

```python
# ❌ デフォルト値が不一致（IFは offset: int | None = None）
async def get_all(
    self, limit: int | None = None, offset: int | None = 0
) -> list[Entity]:

# ✅ IFのシグネチャと一致
async def get_all(
    self, limit: int | None = None, offset: int | None = None
) -> list[Entity]:
```

**`_to_entity`と`_dict_to_entity`の一貫性**: Pydantic系リポジトリでは主に`_dict_to_entity`が使われるが、`_to_entity`も`BaseRepositoryImpl`経由で呼ばれる可能性がある。両メソッドで`created_at`/`updated_at`の設定を一致させること。

```python
# ❌ _to_entity で timestamps が欠落
def _to_entity(self, model: XxxModel) -> Xxx:
    return Xxx(id=model.id, name=model.name)

# ✅ _dict_to_entity と同じく timestamps も設定
def _to_entity(self, model: XxxModel) -> Xxx:
    entity = Xxx(id=model.id, name=model.name)
    entity.created_at = model.created_at
    entity.updated_at = model.updated_at
    return entity
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
