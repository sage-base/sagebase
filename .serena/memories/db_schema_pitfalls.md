# DBスキーマの落とし穴

## elections テーブル
- `chamber` カラムは**存在しない**
- `Election` エンティティの `chamber` は `election_type` から導出される Python プロパティ
- `election_type = '衆議院議員総選挙'` → `chamber = '衆議院'`
- `election_type = '参議院議員通常選挙'` → `chamber = '参議院'`
- raw SQL で院名が必要な場合は `CASE WHEN e.election_type = '...' THEN '...' END` を使う

## parliamentary_groups テーブル
- `chamber` カラムは**存在する**（varchar(10)）
- `pg.chamber` はSQLで直接参照可能

## 注意
- エンティティのプロパティが全てDBカラムに対応するわけではない
- raw SQL を書く前に必ず `\d tablename` でスキーマを確認すること
