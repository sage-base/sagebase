# ADR 0009: 会派の時代管理（start_date/end_date導入）

## Status

Accepted

## Context

`parliamentary_groups`テーブルには`is_active`（boolean）のみで有効期間を管理しており、
**選挙日時点で有効だった会派を特定できない**という問題がある。

具体的な問題:
- 同じ政党（例: 公明党）が時代で異なる会派名を持つ場合（公明党・改革クラブ → 公明党）、
  `LinkParliamentaryGroupUseCase`で`political_party_id`が衝突しスキップされる
- 歴史的会派と現行会派を区別するために`is_active`フラグを使っているが、
  「いつからいつまで有効だったか」の情報がなく、時点指定での検索ができない

ADR 0008では「将来の拡張」として先送りされていた`start_date`/`end_date`を、
本ADRで正式に導入する。

### 検討した選択肢

**Option A: `parliamentary_groups`に`start_date`/`end_date`を追加**（採用）
- プロジェクト内の既存パターン（`PartyMembershipHistory`, `ParliamentaryGroupMembership`）と一貫
- UseCaseの改修が最小限（`get_by_governing_body_id`に`as_of_date`パラメータを追加するだけ）
- 段階的移行が容易（NULL許容で後方互換）

**Option B: 別テーブル`parliamentary_group_history`を作成**
- 正規化は高いが、JOINが増えクエリが複雑化
- 既存の全呼び出し元の改修が必要

## Decision

**Option Aを採用**: `parliamentary_groups`テーブルに`start_date DATE NULL`と`end_date DATE NULL`を追加する。

### `is_active`との関係

- `start_date`/`end_date`は**日付ベースの有効期間**を表す
- `is_active`は**手動の有効フラグ**として残す（段階的移行のため）
- エンティティに`is_active_as_of(as_of_date)`メソッドを追加:
  - `start_date`/`end_date`が設定されている場合: 日付で判定
  - 未設定の場合: `is_active`フラグにフォールバック
- 将来的には`start_date`/`end_date`が全レコードに設定された時点で、
  `is_active`を計算フィールドに置き換えることを検討

### リポジトリでの優先順位

`get_by_governing_body_id()`メソッドに`as_of_date`パラメータを追加:
- `as_of_date`指定時: `(start_date IS NULL OR start_date <= as_of_date) AND (end_date IS NULL OR end_date >= as_of_date)` で絞り込み
- `as_of_date`未指定時: 従来の`is_active`フィルタ（後方互換）
- `as_of_date`が指定された場合は`active_only`より優先される

## Consequences

### Positive
- 選挙日時点での有効会派を正確に特定できる
- `LinkParliamentaryGroupUseCase`で`political_party_id`衝突が解消される
- 既存パターン（`PartyMembershipHistory`）と一貫した設計
- 後方互換性あり（`as_of_date`はオプショナル）

### Negative
- `is_active`との二重管理期間が発生する
- 歴史的会派の正確な日付データは別途調査が必要（後続Issue）

### Risks
- シードデータの日付は初期段階ではNULLのまま（段階的に追加）
