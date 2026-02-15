# ADR 0007: リポジトリモデルパターンの標準化

## Status

Accepted (2026-02-15)

## Context

### 背景

Sagebaseのリポジトリ実装には、歴史的経緯から3種類のモデルパターンが混在しています：

| パターン | モデル基盤 | 該当リポジトリ例 |
|---------|-----------|----------------|
| **SQLAlchemy ORM** | `registry.mapped` / `DeclarativeBase` | Speaker, Minutes, Conversation等 |
| **Pydantic** | `PydanticBaseModel` | Conference, GoverningBody等 |
| **動的モデル** | 動的`__init__` / ランタイム属性 | Politician, ParliamentaryGroup, Meeting等 |

`BaseRepositoryImpl`は`select(model_class)`を前提としたORMベースの汎用メソッド（`count()`, `get_by_ids()`等）を提供していますが、Pydantic/動的モデル系のリポジトリではこれらが**正しく動作しません**。

### 課題: 繰り返し発生するバグ

この不整合が原因で、同種のバグが繰り返し発生しています：

- **#1127**: `count()`が動的モデルリポジトリで失敗
- **#1143**: `get_by_ids()`がPydanticモデルリポジトリで失敗
- **#1147**: 新規リポジトリ追加時にオーバーライド漏れ
- **#1149**: `_to_entity`と`_dict_to_entity`の不整合

これらのバグはすべて「どのパターンで実装すべきか」「何をオーバーライドすべきか」が明文化されていないことに起因します。

### 追加の問題点

1. **変換メソッドの不統一**: `_to_entity()`, `_dict_to_entity()`, `_row_to_entity()`など複数の変換メソッドが混在し、どれを実装すべきか不明確
2. **新規リポジトリ作成の指針不足**: 新しいエンティティを追加する際、3パターンのどれを選択すべきか判断基準がない
3. **`BaseRepositoryImpl`の暗黙的前提**: ORMモデル前提のコードが基底クラスに含まれており、非ORMリポジトリでの落とし穴が多い

### 検討した代替案

#### Option A: 全リポジトリをSQLAlchemy ORMに統一

すべてのリポジトリをSQLAlchemy ORMモデルベースに移行する。

**利点**: パターンが完全に統一される、`BaseRepositoryImpl`がそのまま動作する
**欠点**: 大規模なリファクタリングが必要（推定20+ファイル）、既存テスト全面修正、動的モデルの柔軟性を失う

#### Option B: 新規リポジトリのみORMに統一（既存は維持）

新規作成分のみORM統一し、既存のPydantic/動的モデルリポジトリは現状維持。

**利点**: 段階的に改善可能
**欠点**: 2つのパターンが永続的に共存、開発者の混乱は残る

#### Option C: BaseRepositoryImplにテキストSQLフォールバックを追加（採用）

`BaseRepositoryImpl`を改善し、非ORMモデルでも汎用メソッドが動作するようにする。新規リポジトリの作成方針も明確化。

**利点**: 既存コードの大規模変更なし、全パターンで`BaseRepositoryImpl`が安全に動作、新規は推奨パターンに誘導
**欠点**: `BaseRepositoryImpl`の複雑さが若干増加、3パターンの共存は継続

## Decision

### 決定1: BaseRepositoryImplの改善（実装は別Issue）

`BaseRepositoryImpl`に以下の仕組みを追加し、非ORMモデルでも汎用メソッドが安全に動作するようにする：

- **`_is_orm`フラグ**: コンストラクタでモデルクラスがORMマッピング済みか自動判定
- **`table_name`プロパティ**: 非ORMモデル用にテーブル名を明示的に指定可能に
- **テキストSQLフォールバック**: `_is_orm=False`の場合、`count()`/`get_by_ids()`等がテキストSQLで実行

```python
# 改善後のBaseRepositoryImplイメージ
class BaseRepositoryImpl[T: BaseEntity](BaseRepository[T]):
    def __init__(self, session, entity_class, model_class):
        self._is_orm = self._check_is_orm(model_class)
        # ...

    async def count(self) -> int:
        if self._is_orm:
            result = await self.session.execute(
                select(func.count()).select_from(self.model_class)
            )
        else:
            result = await self.session.execute(
                text(f"SELECT COUNT(*) FROM {self.table_name}")
            )
        return result.scalar() or 0
```

> **注意**: 具体的な実装は別Issueで行います。本ADRでは方針のみ決定します。

### 決定2: 新規リポジトリ作成方針

新規リポジトリ作成時のモデルパターン選択ルールを以下のとおり定めます：

| 優先度 | パターン | 条件 | 理由 |
|-------|---------|------|------|
| **第1選択** | SQLAlchemy ORM | デフォルト | `BaseRepositoryImpl`と完全互換、`select()`が使える |
| **条件付き許容** | Pydantic | 既存Pydanticモデルの拡張時のみ | 既存パターンとの一貫性 |
| **新規禁止** | 動的モデル | 新規作成不可 | バグの温床、IDE補完が効かない |

### 決定3: 変換メソッドの統一（実装は別Issue）

Entity ↔ Model 変換メソッドを`_to_entity()`に一本化します：

- **統一メソッド**: `_to_entity(model) -> Entity` を唯一の変換メソッドとする
- **廃止対象**: `_dict_to_entity()`, `_row_to_entity()` は段階的に`_to_entity()`に統合
- **移行方針**: 新規リポジトリでは`_to_entity()`のみ使用、既存リポジトリは順次移行

### 実装順序

1. **決定2**（本ADR / 本Issue）: 方針を文書化し、CLAUDE.md・Skillsに反映
2. **決定3**: 変換メソッド統一の実装（別Issue）
3. **決定1**: `BaseRepositoryImpl`改善の実装（別Issue）

## Consequences

### 利点

- **バグの再発防止**: `BaseRepositoryImpl`のフォールバックにより、オーバーライド漏れによるランタイムエラーを防止
- **開発者ガイダンスの明確化**: 新規リポジトリ作成時の迷いを解消
- **段階的改善**: 既存コードの大規模リファクタリングなしで改善可能
- **コードベースの一貫性向上**: 変換メソッドの統一により、リポジトリ間のパターンが整理される

### トレードオフ

- **3パターンの共存は継続**: 既存リポジトリの完全統一は行わないため、複数パターンが残る
- **`BaseRepositoryImpl`の複雑さ増加**: `_is_orm`フラグによる分岐が追加される
- **移行コスト**: 変換メソッド統一には既存リポジトリの段階的修正が必要

## References

- [ADR 0003: リポジトリパターン + ISessionAdapter の採用](0003-repository-pattern.md)
- Issue: #1174（本ADR策定）
- 関連バグ: #1127, #1143, #1147, #1149
- `src/infrastructure/persistence/base_repository_impl.py` - BaseRepositoryImpl実装

## Notes

- 本ADRは「方針の文書化」が主目的。コード変更（決定1・決定3の実装）は別Issueで実施する
- 決定2（新規リポジトリ作成方針）は本ADR承認と同時に即時適用
- `BaseRepositoryImpl`改善（決定1）の実装Issueは本ADR承認後に起票予定
