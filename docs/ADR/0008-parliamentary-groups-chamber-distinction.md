# ADR 0008: 会派テーブルへの院（chamber）区別の導入

## Status

Accepted (2026-02-25)

## Context

### 背景

`parliamentary_groups` テーブルには `(name, governing_body_id)` のUNIQUE制約が存在します。衆議院と参議院はどちらも `governing_body_id=1`（国会）を共有しているため、同名の会派（「公明党」「日本共産党」等）を両院で登録できないという制約上の問題がありました。

### 課題

1. **UNIQUE制約の衝突**: 衆参で同名の会派が存在する場合（自由民主党、公明党、日本共産党、日本維新の会等）、片方しか登録できない
2. **LinkParliamentaryGroupUseCaseの誤動作**: `governing_body_id` でアクティブな会派を全取得するため、同じ `political_party_id` を持つ衆参の会派が両方存在すると `skipped_multiple_groups` が発生する
3. **Issue #1231の制限**: 会派マッピング調査（Issue #1231）で参議院の衆議院と同名会派が登録できなかった

### 検討した代替案

#### Option A: governing_body_idを衆議院/参議院で分ける

衆議院と参議院に別々の `governing_body_id` を割り当てる。

**利点**: 既存のUNIQUE制約を変更する必要がない
**欠点**: governing_bodiesマスターデータの大幅な変更が必要、既存の「国会」概念との整合性が崩れる、影響範囲が非常に大きい

#### Option B: chamberカラムを追加（採用）

`parliamentary_groups` テーブルに `chamber` カラムを追加し、衆議院/参議院/空文字で区別する。

**利点**: 最小限の変更で問題解決、既存のgoverning_bodiesマスターデータに影響なし、地方議会（chamber=''）との互換性を保持
**欠点**: 既存データのマイグレーションが必要、UNIQUE制約の変更が必要

#### Option C: start_date/end_dateカラムも同時追加

chamberに加えて、会派の有効期間を管理するカラムを追加する。

**利点**: 時代別会派の完全な管理が可能
**欠点**: 本Issueの範囲を超える、データ整備の工数が大きい

## Decision

### 決定1: chamberカラムの追加

`parliamentary_groups` テーブルに `chamber VARCHAR(10) NOT NULL DEFAULT ''` カラムを追加する。

| chamber値 | 用途 |
|-----------|------|
| `'衆議院'` | 衆議院の会派 |
| `'参議院'` | 参議院の会派 |
| `''`（空文字） | 地方議会の会派（院の区別不要） |

### 決定2: UNIQUE制約の変更

旧制約 `(name, governing_body_id)` を削除し、新制約 `(name, governing_body_id, chamber)` に変更する。これにより、同名会派を衆参で別々に登録できるようになる。

### 決定3: 将来の拡張

`start_date` / `end_date` カラムによる有効期間管理は将来の拡張として記録する。本Issueでは実装しない。

## Consequences

### 利点

- **衆参同名会派の登録**: 「公明党」「日本共産党」等を両院で登録可能に
- **LinkParliamentaryGroupUseCaseの精度向上**: chamber指定により衆参を区別してフィルタ可能
- **後方互換性**: 地方議会はchamber=''のままで既存の動作を維持
- **最小限の影響範囲**: governing_bodiesマスターデータの変更が不要

### トレードオフ

- **downgradeの制限**: 衆参同名会派が追加された後のdowngradeでは、参議院固有レコードの削除が必要（完全な可逆性はない）
- **UI変更**: 国会選択時に院の選択肢を表示する必要がある
- **シードデータの複雑化**: chamberカラムの管理が必要

## References

- Issue: #1232（本ADR策定・実装）
- 前提Issue: #1231（衆参の会派マッピング調査）
- [ADR 0007: リポジトリモデルパターンの標準化](0007-repository-model-pattern-standardization.md)
- `src/infrastructure/persistence/parliamentary_group_repository_impl.py` - リポジトリ実装
- `database/seed_parliamentary_groups_generated.sql` - 会派シードデータ
