---
name: migration-helper
description: Assists in creating database migrations for Sagebase using Alembic. Activates when creating migration files, modifying database schema, or adding tables/columns/indexes. Ensures proper migration structure, rollback support, and Alembic best practices.
---

# Migration Helper (Alembic)

## Purpose
Alembicを使用したデータベースマイグレーションの作成を支援します。

## When to Activate
このスキルは以下の場合に自動的にアクティベートされます：
- 新しいマイグレーションファイルを作成する時
- データベーススキーマを変更する時
- テーブル、カラム、インデックス、制約を追加する時
- ユーザーが「migration」「schema」「database change」「マイグレーション」と言及した時
- ロールバックやマイグレーション履歴について質問された時

## 🚀 Quick Start

### 新しいマイグレーションを作成

```bash
# Docker環境内で作成（推奨）
just migrate-new "add_email_to_politicians"

# または直接Alembicコマンド
docker compose exec sagebase uv run alembic revision -m "add_email_to_politicians"
```

### マイグレーションを実行

```bash
# 未適用のマイグレーションを全て適用
just migrate

# 1つ前に戻す
just migrate-rollback
```

## ⚠️ CRITICAL: 必須チェックリスト

マイグレーション作成時に必ず確認：

- [ ] **upgrade() 実装**: スキーマ変更のSQLを記述
- [ ] **downgrade() 実装**: ロールバック用のSQLを記述（必須！）
- [ ] **冪等性確保**: `IF NOT EXISTS` / `IF EXISTS` を使用
- [ ] **テスト**: `just migrate` で適用確認
- [ ] **ロールバックテスト**: `just migrate-rollback` で戻せることを確認
- [ ] **シードファイル更新**: カラム追加・削除時はStreamlit UIのシード生成タブでシードファイルを再生成（既存シードが削除カラムを参照してDBリセットが失敗する原因になる）
  - ⚠️ **特にUPDATEでデータ移行する場合は要注意**: フレッシュDBではマイグレーションのUPDATEが空テーブルに対して実行される（0行更新）ため、シードファイルのINSERT文にも新カラムの値を含めること（[詳細](#-critical-マイグレーションupdateとシードの実行順序)）

## コマンドリファレンス

### justfile コマンド

| コマンド | 説明 |
|---------|------|
| `just migrate` | 未適用マイグレーションを全て適用 |
| `just migrate-rollback` | 1つ前の状態に戻す |
| `just migrate-current` | 現在適用されているバージョンを表示 |
| `just migrate-history` | マイグレーション履歴を表示 |
| `just migrate-new "説明"` | 新しいマイグレーションファイルを作成 |

### sagebase CLI コマンド

```bash
sagebase migrate              # マイグレーション実行
sagebase migrate-rollback     # ロールバック（-n オプションで複数可）
sagebase migrate-status       # 現在のバージョン確認
sagebase migrate-history      # 履歴確認
sagebase migrate-new "説明"   # 新規作成
```

### 直接 Alembic コマンド

```bash
# Docker内で実行
docker compose exec sagebase uv run alembic upgrade head
docker compose exec sagebase uv run alembic downgrade -1
docker compose exec sagebase uv run alembic current
docker compose exec sagebase uv run alembic history --verbose
docker compose exec sagebase uv run alembic revision -m "説明"
```

## マイグレーションファイル構造

```python
"""Add email column to politicians table.

Revision ID: 003
Revises: 002
Create Date: 2025-01-20
"""

from alembic import op


revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration: Add email column."""
    op.execute("""
        ALTER TABLE politicians
        ADD COLUMN IF NOT EXISTS email VARCHAR(255);

        COMMENT ON COLUMN politicians.email IS 'Politician email address';

        CREATE INDEX IF NOT EXISTS idx_politicians_email
        ON politicians(email);
    """)


def downgrade() -> None:
    """Rollback migration: Remove email column."""
    op.execute("""
        DROP INDEX IF EXISTS idx_politicians_email;

        ALTER TABLE politicians
        DROP COLUMN IF EXISTS email;
    """)
```

## 基本パターン

### カラム追加

```python
def upgrade() -> None:
    op.execute("""
        ALTER TABLE table_name
        ADD COLUMN IF NOT EXISTS column_name VARCHAR(255);
    """)

def downgrade() -> None:
    op.execute("""
        ALTER TABLE table_name
        DROP COLUMN IF EXISTS column_name;
    """)
```

### テーブル作成

```python
def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS new_table (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

def downgrade() -> None:
    op.execute("""
        DROP TABLE IF EXISTS new_table;
    """)
```

### インデックス追加

```python
def upgrade() -> None:
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_table_column
        ON table_name(column_name);
    """)

def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS idx_table_column;
    """)
```

### ジャンクションテーブル（多対多）

多対多関係のジャンクションテーブルを作成する際は、**DB レベルのUNIQUE制約**を必ず検討すること。アプリケーション層の重複チェックだけでは並行リクエスト時にレースコンディションで重複レコードが発生する。

```python
def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS entity_a_entity_b (
            id SERIAL PRIMARY KEY,
            entity_a_id INTEGER NOT NULL REFERENCES entity_a(id) ON DELETE CASCADE,
            entity_b_id INTEGER NOT NULL REFERENCES entity_b(id) ON DELETE RESTRICT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );

        -- 個別インデックス
        CREATE INDEX IF NOT EXISTS idx_entity_a_entity_b_a_id
            ON entity_a_entity_b(entity_a_id);
        CREATE INDEX IF NOT EXISTS idx_entity_a_entity_b_b_id
            ON entity_a_entity_b(entity_b_id);

        -- ❗ UNIQUE制約（レースコンディション防止）
        -- NULLableカラムがある場合は COALESCE でセンチネル値に変換
        CREATE UNIQUE INDEX IF NOT EXISTS uq_entity_a_entity_b_composite
            ON entity_a_entity_b(entity_a_id, entity_b_id);
    """)
```

**チェックリスト:**
- [ ] FK制約のON DELETE方針を決定（CASCADE / RESTRICT / SET NULL）
- [ ] 複合UNIQUE制約を追加（NULLableカラムがある場合は`COALESCE`で対応）
- [ ] downgradeでUNIQUEインデックスもDROPすること

## 詳細リファレンス

- [examples.md](examples.md) - 実践的なマイグレーション例
- [reference.md](reference.md) - 詳細なパターンとベストプラクティス

## ⚠️ CRITICAL: マイグレーションUPDATEとシードの実行順序

### 問題の概要（PR #1133 → #1135）

フレッシュDBでの初期化順序は「**Alembicマイグレーション → シードデータ投入**」です。
マイグレーションでカラム追加＋`UPDATE`によるデータ移行を行った場合、フレッシュDBではテーブルが空のため`UPDATE`は**0行**に対して実行されます。その後に投入されるシードデータにそのカラムが含まれていないと、全行NULLになります。

```
フレッシュDB初期化の流れ:
1. Alembic migration: ALTER TABLE ADD COLUMN + UPDATE → 空テーブルなので0行更新
2. load-seeds.sh: INSERT INTO ... (新カラムなし) → 全行NULL
```

### 対策

マイグレーションでカラム追加＋`UPDATE`（データ移行）を行った場合は、**必ずシードファイルも更新**して新カラムの値を含めること。

```sql
-- ❌ 悪い例: マイグレーションのUPDATEに頼り、シードにカラムがない
INSERT INTO governing_bodies (id, name, type, organization_code) VALUES ...

-- ✅ 良い例: シードファイルにも新カラムを含める
INSERT INTO governing_bodies (id, name, type, organization_code, prefecture) VALUES ...
```

## レガシーマイグレーションについて

**重要**: レガシーマイグレーション方式は廃止されました。

- `database/migrations/` 配下の48個のSQLファイルは**削除されました**（gitの履歴で参照可能）
- 全てのスキーマ定義は Alembic migration 001 (`alembic/versions/001_baseline.py`) に統合されました
- `database/init.sql` は最小限のブートストラップのみ（extensions + enum型）
- **Alembicが唯一のスキーマ定義源（Single Source of Truth）です**
- `just migrate-legacy` コマンドは削除されました

詳細は [ADR 0006: マイグレーションのAlembic完全統一](../../../docs/ADR/0006-alembic-migration-unification.md) を参照してください。
