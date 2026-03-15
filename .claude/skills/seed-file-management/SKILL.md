---
name: dump-data-management
description: データベースのJSON DUMP管理に関するガイドライン。ダンプ・リストア・GCS共有・Alembic revision互換性チェックをカバー。データ投入・更新・共有時にアクティベートします。
---

# DUMP Data Management（データダンプ管理）

## 目的
データベースの全データをJSON DUMPで管理するためのガイドラインを提供します。
**旧SEED（SQLファイル）は廃止されました。** 詳細は [ADR 0010](../../../docs/ADR/0017-seed-dump-strategy.md) を参照。

## いつアクティベートするか
- データベースの初期データ投入について作業する時
- `just dump-gcs`, `just restore-latest` を実行する時
- ローカルエージェントがデータ拡充した後の共有方法について聞かれた時
- マイグレーション後のデータ更新について作業する時

## クイックリファレンス

### コマンド一覧

| コマンド | 説明 |
|---------|------|
| `just dump-gcs` | DBをJSONダンプしてGCSにアップロード |
| `just dump-gcs --description "説明"` | 説明付きでダンプ |
| `just restore-latest` | GCSから最新ダンプをリストア（truncate + insert） |
| `just list-dumps` | GCS上のダンプ一覧を表示 |
| `sagebase database dump` | ローカルのみにダンプ |
| `sagebase database dump --gcs` | GCSにもアップロード |
| `sagebase database restore-dump <dir>` | 指定ディレクトリからリストア |
| `sagebase database restore-dump <gs://...>` | GCS URIからリストア |
| `sagebase database restore-latest --force` | revision不一致でも強制リストア |

### 開発フロー

#### 初回セットアップ
```bash
just up                    # コンテナ起動 + マイグレーション
just restore-latest        # GCSから最新データを投入
```

#### データ拡充後の共有
```bash
# エージェントがDBにデータ追加・修正した後
just dump-gcs --description "衆議院議員465名のプロフィール追加"
```

#### 別の開発者が最新データを取得
```bash
just restore-latest
```

#### マイグレーション作成後
```bash
just migrate               # alembic upgrade head
# （必要なデータ修正）
just dump-gcs --description "カラム追加後のデータ更新"
```

#### DBリセット時
```bash
just clean                 # 自動でGCSにダンプ → ボリューム削除
just up                    # マイグレーション実行
just restore-latest        # 最新ダンプからリストア
```

## Alembic revision互換性チェック

DUMPの `_metadata.json` にはAlembic revisionが記録されています。
`restore-dump` / `restore-latest` 実行時に、DUMPのrevisionと現在のDBのrevisionを比較します。

- **一致**: そのままリストア
- **不一致**: 警告を表示して中断
  - `--force` オプションで強制リストア可能

### 典型的な不一致パターン

| 状況 | 対処 |
|------|------|
| DUMPが古い | `alembic upgrade head` を先に実行 |
| DUMPが新しい | マイグレーションファイルが不足。`git pull` してから `alembic upgrade head` |

## 注意事項

### 並行作業時のデータ衝突
複数人が同時にデータ拡充した場合、後から `dump-gcs` した方が最新になります。
- `restore-latest` でベースを揃えてから作業を開始する
- `list-dumps --gcs` で履歴を確認し、必要なら過去のDUMPに戻れる

### CI環境
CIではDUMPリストア不要です。テストはマイグレーション + テスト用フィクスチャで動作します。

### GCSが使えない場合
`--gcs` なしでローカルダンプ（`dumps/` ディレクトリ）は常に動作します。
GCSが使えない環境では、ローカルダンプを手動でコピーして共有できます。

## 旧SEEDからの移行

`database/seed_*_generated.sql` は全て削除されました。
`scripts/load-seeds.sh`, `scripts/load-seeds-internal.sh` も削除されました。
新規のSEEDファイルは作成しないでください。全データはDUMPで管理します。
