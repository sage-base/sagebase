---
allowed-tools: Read, Glob, Grep, Edit, Write, Bash, AskUserQuestion, mcp__serena__find_file, mcp__serena__find_symbol, mcp__serena__get_symbols_overview, mcp__serena__list_dir, mcp__serena__list_memories, mcp__serena__read_memory, mcp__serena__search_for_pattern
description: worktree+tmux環境でDockerを使った実データ動作確認を行うコマンド
---
ultrathink

# 実データ動作確認ワークフロー

このワークフローは、worktree + tmux 開発環境でDockerを使って実データ動作確認を行います。

## 前提

- 開発環境は **worktree + tmux** で構成されている
- 他のworktreeで起動中のsagebase Dockerサービスが存在する可能性がある
- **同一ホストで複数のsagebaseコンテナは共存できない**（ポート競合・DBボリューム共有のため）

---

## Step 1: 他のsagebase Dockerサービスを停止

他のworktreeやディレクトリで起動中のsagebaseサービスがあると、ポート競合やDB接続の問題が発生します。
まず既存のサービスを確認・停止してください。

```bash
# 起動中のsagebase関連コンテナを確認
docker ps --filter "name=sagebase" --filter "name=postgres"

# 他のworktreeで起動しているサービスがあれば停止
# （docker-compose.ymlの場所を確認して停止する）
docker ps --format '{{.Names}} {{.Labels}}' | grep -i sage
```

**重要**: `sagebase_db` ボリュームはすべてのworktreeで共有されています。他のサービスを停止しても**データは失われません**。

## Step 2: 現在のworktreeでDockerをビルド・起動

現在のworktreeのコードをDockerに反映するため、ビルドして起動します。

```bash
# 現在のworktreeパスを確認
pwd

# Dockerイメージをビルド（現worktreeのコードを反映）
docker compose -f docker/docker-compose.yml build sagebase

# サービスを起動
docker compose -f docker/docker-compose.yml up -d
```

### 起動確認

```bash
# コンテナが正常に起動しているか確認
docker compose -f docker/docker-compose.yml ps

# sagebaseコンテナのログを確認（エラーがないこと）
docker compose -f docker/docker-compose.yml logs sagebase --tail=20
```

## Step 3: 実データでの動作確認

### DB接続の確認

```bash
# PostgreSQLに接続できることを確認
docker compose -f docker/docker-compose.yml exec postgres \
    psql -U sagebase_user -d sagebase_db -c "SELECT 1"
```

### 動作確認の実行

実装した機能に応じて、以下のいずれかの方法で動作確認を行ってください：

#### A. CLIスクリプトの場合

```bash
# まずdry-runで実行（データを変更しない）
docker compose -f docker/docker-compose.yml exec sagebase \
    uv run python scripts/<script_name>.py --dry-run

# dry-run結果を確認し、問題なければ本実行
docker compose -f docker/docker-compose.yml exec sagebase \
    uv run python scripts/<script_name>.py
```

#### B. UseCaseや内部ロジックの場合

`tmp/` に検証スクリプトを作成して実行してください：

```bash
# 検証スクリプトを作成（tmp/配下）
# → tmp/verify_<feature_name>.py

# コンテナ内にコピーして実行
docker cp tmp/verify_<feature_name>.py <container_name>:/tmp/
docker compose -f docker/docker-compose.yml exec sagebase \
    uv run python /tmp/verify_<feature_name>.py
```

#### C. SQLクエリで結果確認

```bash
# 処理結果をSQLで直接確認
docker compose -f docker/docker-compose.yml exec postgres \
    psql -U sagebase_user -d sagebase_db -c "<確認クエリ>"
```

### 確認すべきポイント

- [ ] **件数の妥当性**: 処理対象・結果件数が期待通りか
- [ ] **データの正確性**: 主要フィールドの値が正しいか（日付、名前、ID等）
- [ ] **冪等性**: 2回実行して件数が変わらないか（upsert処理の場合）
- [ ] **エッジケース**: 0件データ、境界値等での動作

## Step 4: 後片付け

動作確認が完了したら：

```bash
# テスト用に変更したデータがあれば元に戻す

# 必要に応じてサービスを停止（他のworktreeに戻る場合）
docker compose -f docker/docker-compose.yml down
```

---

## トラブルシューティング

### コンテナ内にファイルが見えない

`scripts/` はDockerイメージにCOPYされるため、**ビルド時点のコード**が反映されます。
ファイルを変更した場合は再ビルドが必要です：

```bash
docker compose -f docker/docker-compose.yml build sagebase
docker compose -f docker/docker-compose.yml up -d
```

`src/` と `tests/` はバインドマウントされているため、再ビルド不要です。

### ポート競合エラー

他のworktreeのDockerサービスがまだ動いている可能性があります：

```bash
# 全sagebase関連コンテナを強制停止
docker ps -q --filter "name=sagebase" --filter "name=postgres" | xargs -r docker stop
```

### DB接続エラー

```bash
# 環境変数の確認
docker compose -f docker/docker-compose.yml exec sagebase env | grep DATABASE

# PostgreSQLコンテナの状態確認
docker compose -f docker/docker-compose.yml logs postgres --tail=10
```
