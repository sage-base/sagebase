# ADR 0010: SEED廃止・DUMP一本化戦略

## Status

Accepted

## Context

従来、初期データ管理に2つの仕組みが混在していた:

- **SEED** (`database/seed_*_generated.sql`): Git管理のSQL INSERT文。11ファイル、約30MB
- **DUMP** (`dumps/`): gitignoredのJSON形式データスナップショット

### 問題点

1. SEEDの実態がDUMP（DBからエクスポートしたデータのSQL化）であり、区別が曖昧
2. テーブルごとに冪等性の実装が不統一（`WHERE NOT EXISTS`/`ON CONFLICT`/ID指定が混在）
3. SEEDの更新タイミングやルールが不明確
4. `load-seeds.sh` がエラーを `> /dev/null 2>&1` で握りつぶしており、サイレント失敗が発生
5. マイグレーションでスキーマが変わるとSEEDのSQL文がサイレントに壊れる
6. 新テーブル追加のたびに `COUNT(*) = 0` の個別チェックが増殖
7. ローカルエージェントがデータ拡充した結果をSEEDに反映するには手動でSQL再生成が必要

## Decision

**SEED（SQLファイル）を全廃し、JSON DUMPに一本化する。**

### 具体的な設計

- 全データをJSON形式でダンプ・リストアする
- DUMPメタデータにAlembic revisionを記録し、リストア時にスキーマ互換性をチェックする
- GCSに保存して開発者間でデータを共有する
- `--description` オプションでDUMPの目的を記録できる

### 開発フロー

```
初回:       just up → just restore-latest
データ拡充: エージェント作業 → just dump-gcs --description "..."
共有:       just restore-latest（他の開発者が最新データを取得）
リセット:   just clean → just up → just restore-latest
```

### コマンド

| コマンド | 説明 |
|---------|------|
| `just dump-gcs` | DBをJSONダンプしてGCSにアップロード |
| `just restore-latest` | GCSから最新のダンプをリストア |
| `just list-dumps` | GCS上のダンプ一覧を表示 |
| `sagebase database dump --gcs --description "..."` | CLI直接実行 |
| `sagebase database restore-dump <dir_or_gcs_uri>` | 指定ダンプからリストア |
| `sagebase database restore-latest` | 最新ダンプをリストア |

## Consequences

### メリット

- データ管理の一本化により、SEED/DUMPの衝突事故がなくなる
- Alembic revision紐付けにより、スキーマ不一致によるサイレント失敗を防止
- ローカルでのデータ拡充後、`just dump-gcs` するだけで共有可能
- JSON形式のため、カラム追加・削除に対して既存DUMPが壊れにくい（存在しないカラムは自動スキップ）

### デメリット

- GCS依存が増える（ただしGCSなしでもローカルダンプは動作する）
- 並行作業時のデータ衝突リスク（後勝ち）。運用ルールで対応
- Git上にデータのスナップショットがなくなる（GCSに移行）

### CI環境

- CIではDUMPリストア不要（テストはマイグレーション + テスト用フィクスチャで動作）
- `init_ci.sql` は変更なし
