---
name: cli-script-creation
description: scripts/配下にCLIスクリプトを新規作成・修正する際のガイドライン。Docker実行コマンドの記載、外部データ依存の明示、使い方のドキュメントをカバー。CLIスクリプトを作成・修正する時にアクティベートします。
---

# CLI Script Creation（CLIスクリプト作成ガイド）

## 目的

`scripts/` 配下に作成するCLIスクリプトが、利用者にとって迷わず実行できるようにするためのガイドラインを提供します。
Docker-first環境であること、外部データへの依存があること等を、スクリプト自身に明記するルールを定めます。

## いつアクティベートするか

- `scripts/` 配下にCLIスクリプト（Python/Shell）を新規作成する時
- 既存のCLIスクリプトの使い方やインターフェースを修正する時

## クイックチェックリスト

- [ ] **docstringにDocker経由の実行コマンド例が記載されている**
- [ ] **外部データに依存する場合、取得方法（URL・コマンド）が記載されている**
- [ ] **argparseのhelpが充実している**（引数の意味、デフォルト値、具体例）
- [ ] **実行前提条件が明記されている**（必要なマスターデータ、環境変数など）

## 詳細なガイドライン

### 1. Docker実行コマンドをdocstringに書く

このプロジェクトはDocker-first環境のため、ローカルPythonでは依存パッケージが入っていません。
利用者がローカルで直接 `python scripts/xxx.py` を実行して `ModuleNotFoundError` になるのを防ぐため、
スクリプト冒頭のdocstringにDocker経由の実行方法を必ず記載してください。

**✅ 良い例:**
```python
"""smartnews-smri gian_summary.json インポートスクリプト.

Usage (Docker経由で実行):
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/import_smartnews_smri.py /tmp/gian_summary.json

    # バッチサイズを指定する場合
    docker compose -f docker/docker-compose.yml exec sagebase \
        uv run python scripts/import_smartnews_smri.py /tmp/gian_summary.json --batch-size 200
"""
```

**❌ 悪い例:**
```python
"""smartnews-smri gian_summary.json インポートスクリプト."""
```

用途は書いてあるが、どうやって実行するかが不明。

### 2. 外部データの取得方法を明記する

外部リポジトリやAPIからデータをダウンロードして使うスクリプトの場合、
データの取得方法をdocstringまたはargparseのdescriptionに記載してください。

**✅ 良い例:**
```python
"""smartnews-smri gian_summary.json インポートスクリプト.

データ取得:
    curl -sL https://raw.githubusercontent.com/smartnews-smri/house-of-representatives/master/data/gian_summary.json \
        -o /tmp/gian_summary.json

    # コンテナ内にコピー
    docker cp /tmp/gian_summary.json docker-sagebase-1:/tmp/gian_summary.json
"""
```

**❌ 悪い例:**
- データの出典URLがスクリプト内のどこにも書かれていない
- 「gian_summary.jsonを用意してください」とだけ書いてある（どこから？）

### 3. argparseのヘルプを充実させる

`--help` を実行するだけで使い方が分かるようにしてください。

**✅ 良い例:**
```python
parser = argparse.ArgumentParser(
    description="smartnews-smri gian_summary.json をProposalテーブルにインポート",
    epilog="例: docker compose exec sagebase uv run python scripts/import_smartnews_smri.py /tmp/gian_summary.json",
)
parser.add_argument(
    "file_path",
    type=Path,
    help="gian_summary.json ファイルのパス（コンテナ内のパス）",
)
```

**❌ 悪い例:**
```python
parser = argparse.ArgumentParser()
parser.add_argument("file_path")
```

### 4. 実行前提条件を明記する

マスターデータの存在、環境変数、DB接続など、スクリプト実行に必要な前提条件がある場合は明記してください。

**✅ 良い例:**
```python
"""
前提条件:
    - Docker環境が起動済み（just up-detached）
    - マスターデータ（開催主体「日本国」）がロード済み
    - Alembicマイグレーション適用済み
"""
```
