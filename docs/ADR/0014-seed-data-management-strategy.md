# ADR 0014: SEEDデータ管理戦略

## Status

Accepted (2026-03-13)

## Context

### 背景

Polibaseでは、開催主体（governing_bodies）、会議体（conferences）、政党（political_parties）、議員団（parliamentary_groups）、会議（meetings）、政治家（politicians）、選挙（elections）、選挙結果メンバー（election_members）、議員団所属（parliamentary_group_memberships）、議案（proposals）、発言者（speakers）など、多数のマスタデータ・初期データをデータベースに投入する必要があります。

現在、`src/seed_generator.py` の `SeedGenerator` クラスがデータベースの既存データを読み取り、INSERT文を含むSQL（`.sql`ファイル）を直接生成する方式を採用しています。生成されたSQLは `database/` ディレクトリに `seed_*_generated.sql` として出力されます。

Alembicマイグレーション（[ADR 0006](0006-alembic-migration-unification.md)）はスキーマ変更の管理に使用していますが、初期データ投入にはこのSQL生成器による独立したアプローチを取っています。

### 課題と設計判断

1. **冪等性の確保**: 各テーブルのINSERT文に `ON CONFLICT DO NOTHING` または `ON CONFLICT ... DO UPDATE SET` を使用し、同じSEEDを何度実行しても安全に動作するようにしています。例えば:
   - `governing_bodies`: `ON CONFLICT (name, type) DO NOTHING`
   - `conferences`: `ON CONFLICT (name, governing_body_id, term) DO NOTHING`
   - `political_parties`: `ON CONFLICT (name) DO NOTHING`
   - `elections`: `ON CONFLICT (governing_body_id, term_number) DO UPDATE SET ...`
   - `proposals`: `ON CONFLICT (id) DO UPDATE SET ...`

2. **テーブル生成順序の管理**: `generate_all_seeds()` 関数で、ForeignKey制約を考慮した順序でSEEDファイルを生成しています。例えば `governing_bodies` → `elections` → `conferences` → `political_parties` → `parliamentary_groups` → `meetings` → `politicians` → `election_members` → `parliamentary_group_memberships` → `proposals` → `speakers` の順に生成されます。

3. **グループ化による識別可能性**: 各テーブルのSEEDファイルにはコメントヘッダ（生成日時、テーブル名、レコード件数）が含まれ、さらにデータはタイプ別にグループ化されています（例: `governing_bodies` は「国」「都道府県」「市町村」でグルーピング）。これにより、どのSEEDバッチでどのデータが投入されたか追跡可能です。

4. **SQLインジェクション対策**: `_escape_sql()` メソッドでシングルクォートのエスケープ処理を行い、データベースから取得した値をSQL文に埋め込む際の安全性を担保しています。また `_sql_str_or_null()` でNULL値の適切な処理も行っています。

5. **Streamlit UIからのトリガー**: `SeedGeneratorServiceImpl`（`src/infrastructure/external/seed_generator_service.py`）を通じて、Streamlit UIからSEEDファイルの生成を実行できます。選挙SEED・選挙結果メンバーSEEDの生成がユースケース経由で呼び出されます。

### 検討した代替案

#### Option A: FixtureファイルベースのJSON/YAML管理

マスタデータをJSON/YAMLファイルとして管理し、ローダースクリプトでデータベースに投入する方式。

**利点**: データが構造化されて読みやすい、バージョン管理しやすい
**欠点**: ForeignKey参照の解決が複雑になる（IDの事前確定が必要）、大量データ（1,966市町村等）の管理が煩雑、冪等な投入ロジックを自前で実装する必要がある

#### Option B: Alembicのdata migration

Alembicマイグレーションファイル内に初期データ投入のINSERTを含める方式。

**利点**: スキーマ変更とデータ投入が一元管理される、マイグレーション順序が保証される
**欠点**: データ量が多いマイグレーションファイルが可読性を損なう、データの追加・修正のたびにマイグレーションファイルが増加する、再実行（冪等な追加投入）が困難

#### Option C: Django的なfixtures

テストデータのフィクスチャ機構を独自に実装する方式。

**利点**: フレームワーク的なアプローチで統一性がある
**欠点**: 独自のフィクスチャフレームワークの開発・保守コストが高い、SQLAlchemy/PostgreSQLの機能（ON CONFLICT等）を活かしにくい

## Decision

`SeedGenerator` クラスによるSQL直接生成方式を採用します。

### 主な理由

1. **ON CONFLICTによる宣言的な冪等性**: PostgreSQLの `ON CONFLICT DO NOTHING / DO UPDATE SET` 構文を活用することで、冪等性をSQL文レベルで宣言的に実現できます。独自のUPSERTロジックを実装する必要がありません。

2. **ForeignKey制約順の自動管理**: `generate_all_seeds()` で生成順序を明示的に管理し、外部キー制約違反を防止しています。

3. **現行データベースからの生成**: 本番データベースの現在の状態をそのままSEEDとして保存できるため、データの正確性が担保されます。データベースに手動投入・修正したデータも含めてSEED化できます。

4. **可読性とデバッグ容易性**: 生成されるSQLファイルは人間が直接読んで内容を確認できます。問題が発生した場合もSQL文を直接デバッグできます。

5. **Streamlit UI統合**: `SeedGeneratorServiceImpl` を通じたUIからの生成トリガーにより、開発者以外でもSEED更新が可能です。

## Consequences

### Positive

- **冪等性**: `ON CONFLICT` により、SEEDの重複実行が安全
- **順序保証**: ForeignKey制約順の生成順序管理により、依存関係を自動解決
- **追跡可能性**: コメントヘッダとグループ化により、SEEDの内容と投入履歴を把握可能
- **可搬性**: 生成されたSQLファイルは任意のPostgreSQL環境で実行可能
- **UI統合**: Streamlit UIからの生成トリガーにより運用の利便性を確保

### Negative

- **SQL文字列の手動組み立て**: `_escape_sql()` によるエスケープに依存しており、SQLAlchemy ORMのパラメータバインドと比較するとSQLインジェクションリスクのカバー範囲が限定的（ただし、入力はすべてデータベースから取得した値であり、外部ユーザー入力ではないためリスクは低い）
- **スキーマ変更への追従**: テーブルのカラム追加・変更時にSeedGeneratorの対応メソッドも修正が必要
- **生成ファイルのサイズ**: 大量データ（例: 1,966市町村のgoverning_bodies）の場合、生成されるSQLファイルが大きくなる

## References

- [ADR 0006: Alembic統一マイグレーション](0006-alembic-migration-unification.md)
- `src/seed_generator.py` - SeedGeneratorクラス実装
- `src/infrastructure/external/seed_generator_service.py` - SeedGeneratorServiceImpl実装
- `src/domain/services/interfaces/seed_generator_service.py` - サービスインターフェース
