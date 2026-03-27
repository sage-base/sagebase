---
name: coverage-update
description: sage-base.comカバレッジページのデータをBQから更新するスキル。カバレッジページの数値更新、デプロイ時にアクティベートします。
---

# Coverage Update（カバレッジデータ更新）

## 目的

sage-base.com のカバレッジページ（/coverage/）に表示される数値を、BigQuery の最新データで更新する。
更新後に git commit & push すると、Cloudflare Pages で自動デプロイされる。

## いつアクティベートするか

- カバレッジページの数値を最新化したい時
- BQ のデータが更新された後
- 「カバレッジ更新」「coverage update」等のキーワードが出た時

## クイックチェックリスト

- [ ] GCP認証が有効（`gcloud auth application-default login`）
- [ ] `GOOGLE_CLOUD_PROJECT` 環境変数が設定されている
- [ ] BQ `sagebase_source` データセットにデータが存在する

## 実行手順

### 1. BQからデータを取得して coverage.json を更新

```bash
# Docker経由で実行
docker compose -f docker/docker-compose.yml exec sagebase \
    uv run python scripts/update_coverage_data.py

# ドライラン（ファイル書き込みなし、確認用）
docker compose -f docker/docker-compose.yml exec sagebase \
    uv run python scripts/update_coverage_data.py --dry-run
```

### 2. 変更を確認

```bash
git diff website/data/coverage.json
```

### 3. コミット & プッシュ

```bash
git add website/data/coverage.json
git commit -m "chore: カバレッジデータを更新"
git push
```

Cloudflare Pages が自動的にデプロイを実行する。

## アーキテクチャ

```
BigQuery (sagebase_source)
    ↓  scripts/update_coverage_data.py
website/data/coverage.json
    ↓  Hugo ビルド時
website/layouts/_default/coverage.html
    ↓  {{ .Site.Data.coverage }} で参照
sage-base.com/coverage/
```

### ファイル構成

| ファイル | 役割 |
|---------|------|
| `scripts/update_coverage_data.py` | BQクエリ実行 → JSON生成 |
| `website/data/coverage.json` | Hugo data file（テンプレートが参照） |
| `website/layouts/_default/coverage.html` | Hugoテンプレート |
| `src/infrastructure/bigquery/bq_data_coverage_repository_impl.py` | BQリポジトリ実装 |
| `src/domain/entities/bq_coverage_stats.py` | TypedDictエンティティ |

### coverage.json の主要フィールド

- `hero.national` / `hero.local`: ヒーローセクションの国会/地方数値
- `totals`: 合計値（発言数、会議数、政治家数、政党数）
- `quality.speaker_linkage`: 発言者紐付け率
- `quality.parliamentary_group_mapping`: 会派マッピング率
- `prefecture_ranking`: 都道府県別ランキング（タイムライン計算値含む）
- `updated_at` / `updated_date`: 更新タイムスタンプ

## トラブルシューティング

### BQ接続エラー
```
StorageError: BigQueryクエリの実行に失敗しました
```
→ `gcloud auth application-default login` を再実行

### GOOGLE_CLOUD_PROJECT 未設定
```
GOOGLE_CLOUD_PROJECT 環境変数が設定されていません
```
→ `.env` ファイルに `GOOGLE_CLOUD_PROJECT=your-project-id` を設定
