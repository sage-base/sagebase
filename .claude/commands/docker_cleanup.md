---
allowed-tools: Bash, Read, AskUserQuestion
description: Dockerディスク不足時に安全にディスクを解放するコマンド。DBボリュームを保護しつつビルドキャッシュ・不要イメージを削除。
---
ultrathink

# Docker安全クリーンアップ

Dockerのディスク不足でコンテナが起動できない場合に、**DBボリュームを保護しながら**段階的にディスクを解放します。

## 重要: 絶対に実行してはいけないコマンド

以下のコマンドはDBデータを含む全ボリュームを削除するため、**絶対に実行しない**:
- `docker system prune -a --volumes`
- `docker volume prune -a`

## 手順

### Step 1: 現状のディスク使用量を確認

!docker system df
!docker system df -v | head -50

ユーザーに現状を報告し、どの項目がディスクを圧迫しているか説明してください。

### Step 2: ビルドキャッシュの削除（最も安全、効果大）

ビルドキャッシュは再ビルド時に自動的に再作成されるため、安全に削除できます。

```bash
docker builder prune -a -f
```

これだけで数十GBの解放が見込めます。解放されたサイズを報告してください。

### Step 3: 不要なイメージの削除

```bash
# dangling（タグなし中間）イメージのみ削除（安全）
docker image prune -f

# 未使用イメージも含めて削除（より多くの容量解放）
docker image prune -a -f
```

### Step 4: 停止済みコンテナの削除

```bash
docker container prune -f
```

### Step 5: 効果確認

!docker system df

Step 1 の結果と比較して、解放されたディスク容量を報告してください。

### Step 6: まだ不足している場合のみ - 不要ボリュームの選択的削除

**注意**: このステップはStep 2-4で十分な容量が確保できなかった場合のみ実行します。

```bash
# 現在のボリューム一覧を確認
docker volume ls
```

以下のボリュームは**絶対に削除しない**（DBデータ）:
- `docker_postgres_data`
- `polibase_postgres_data`
- 名前に `postgres` を含むボリューム

匿名ボリューム（ハッシュ値のみの名前）は削除候補です。
ユーザーに削除対象を確認してから、個別に `docker volume rm <name>` で削除してください。

## 容量解放の目安

| 対象 | 解放量の目安 | 安全性 | 再構築コスト |
|------|------------|--------|------------|
| ビルドキャッシュ | 数十GB | 完全に安全 | 次回ビルドが遅くなる程度 |
| danglingイメージ | 数GB | 完全に安全 | なし |
| 未使用イメージ | 数GB~数十GB | 安全 | `docker pull` で再取得 |
| 停止済みコンテナ | 数百MB | 安全 | `just up` で再作成 |
| 匿名ボリューム | 数百MB~数GB | 要確認 | 内容による |
| **DBボリューム** | - | **削除禁止** | **データ喪失** |
