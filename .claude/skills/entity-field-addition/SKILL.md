---
name: entity-field-addition
description: エンティティに新しいフィールドを追加する際の全層横断チェックリスト。Clean Architectureの各層で必要な変更箇所を漏れなく対応するためのガイド。エンティティにフィールドを追加する時にアクティベートします。
---

# Entity Field Addition（エンティティフィールド追加ガイド）

## 目的

エンティティに新しいフィールド（カラム）を追加する際、Clean Architectureの全層にわたって必要な変更を漏れなく行うためのチェックリストとガイドラインを提供します。

フィールド追加は複数の層を横断するタスクであり、一部の層での変更漏れが実行時エラーやデータ不整合を引き起こします。特に、SEEDファイル生成やSQLAlchemyモデルの制約など、見落としやすい箇所に注意が必要です。

## いつアクティベートするか

- エンティティに新しいフィールド（カラム）を追加する時
- 既存フィールドの型を変更する時
- テーブルにカラムを追加するマイグレーションを作成する時

## クイックチェックリスト

### Domain層
- [ ] **エンティティ**: `__init__`にフィールドを追加
- [ ] **リポジトリIF**: 必要に応じてインターフェースメソッドのシグネチャを更新

### Infrastructure層
- [ ] **マイグレーション**: Alembicマイグレーションファイルを作成
- [ ] **SQLAlchemyモデル**: フィールドを追加（**FK制約がある場合は`ForeignKey`を忘れずに**）
- [ ] **リポジトリ実装**: 以下のすべてを更新
  - `create()` INSERT文
  - `update()` UPDATE文
  - `_row_to_entity()` マッピング
  - `_to_entity()` / `_to_model()` / `_update_model()`
  - 動的モデルクラスのフィールド定義

### Application層
- [ ] **DTO**: Create/Update InputDtoにフィールドを追加
- [ ] **UseCase**: エンティティ作成・更新時にフィールドを渡す
- [ ] **SEEDファイル生成**: `generate_seed_file()`等のSQL生成メソッドを更新

### Interface層
- [ ] **Presenter**: create/updateメソッドにパラメータを追加
- [ ] **View**: フォームに入力コンポーネントを追加
- [ ] **一覧表示**: DataFrameに列を追加

### テスト
- [ ] **エンティティテスト**: 新フィールドのアサーションを追加
- [ ] **ファクトリ**: `entity_factories.py`にデフォルト値を追加
- [ ] **リポジトリテスト**: CRUD操作でフィールドが正しく扱われるか確認
- [ ] **UseCaseテスト**: DTOからエンティティへフィールドが伝播するか確認
- [ ] **Presenterテスト**: UI層からUseCaseへフィールドが伝播するか確認

## 見落としやすいポイント

### 1. SQLAlchemyモデルのForeignKey制約

マイグレーションでFK制約を定義しても、SQLAlchemyモデルに`ForeignKey`を付けないとORMレベルでの整合性が取れません。

#### ✅ 良い例
```python
political_party_id: Mapped[int | None] = mapped_column(
    Integer, ForeignKey("political_parties.id", ondelete="SET NULL"), nullable=True
)
```

#### ❌ 悪い例
```python
# マイグレーションにFKがあるのにモデルにForeignKeyがない
political_party_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

### 2. SEEDファイル生成メソッド

`generate_seed_file()`のようなSQL生成メソッドは、エンティティの全フィールドをSQL文に含める必要があります。新フィールドを追加した際、以下の3箇所すべてを更新してください：

- INSERT文のカラムリスト
- VALUES句
- ON CONFLICT ... DO UPDATE SET句

#### ❌ 見落とし例
```python
# INSERT文に新カラムが含まれていない
seed_content += (
    "INSERT INTO parliamentary_groups "
    "(id, name, governing_body_id, url, description, is_active) VALUES\n"
    # ← political_party_id が漏れている
)
```

### 3. 動的モデルリポジトリのCRUDメソッド

Pydantic/動的モデル系リポジトリではraw SQLを使っているため、INSERT/UPDATE/SELECT文のカラムリストを手動で管理しています。新フィールドの追加時に**すべてのSQL文**を更新してください。

## 作業フロー

```
1. マイグレーション作成 → FK制約やインデックスの設計
2. ドメインエンティティ更新 → フィールド追加
3. SQLAlchemyモデル更新 → ForeignKey制約を含める
4. リポジトリ実装更新 → 全CRUD SQL + マッピングメソッド
5. DTO + UseCase更新 → フィールドの受け渡し
6. SEEDファイル生成更新 → SQL生成メソッド
7. UI層更新 → フォーム + 一覧表示
8. テスト追加・更新 → 全層でフィールドの伝播を確認
```

## 参考資料

- [clean-architecture-checker](./../clean-architecture-checker/): 各層の依存ルール
- [migration-helper](./../migration-helper/): マイグレーション作成ガイド
- [seed-file-management](./../seed-file-management/): SEEDファイルのルール
- [test-writer](./../test-writer/): テスト作成ガイド
