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
- [ ] **docstringのUsage例とargparse定義が一致している**（存在しないオプションを例に書いていないか）
- [ ] **外部データに依存する場合、取得方法（URL・コマンド）が記載されている**
- [ ] **外部JSON/CSVデータを解析する場合、実データの構造を事前に確認している**
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

### 4. docstringのUsage例とargparse定義を一致させる

docstringに書いたコマンド例で使っているオプションが、実際の`argparse`定義に存在するか確認してください。
他のスクリプトからUsage例をコピーして編集する際に、未実装のオプションが残りがちです。

**❌ 悪い例:**
```python
"""スクリプトの説明.

Usage:
    docker compose exec sagebase uv run python scripts/xxx.py --conference-name 参議院
"""
# argparseには --conference-name が未定義 → 実行時エラー
parser = argparse.ArgumentParser()
parser.add_argument("--dry-run", action="store_true")
```

**✅ 良い例:**
```python
"""スクリプトの説明.

Usage:
    docker compose exec sagebase uv run python scripts/xxx.py --dry-run
"""
parser = argparse.ArgumentParser()
parser.add_argument("--dry-run", action="store_true")
```

### 5. 外部データの構造を実データで事前検証する

外部JSONやCSVを解析するスクリプトを書く際は、**実データをダウンロードして構造を確認してから**パース処理を実装してください。
ドキュメントやコード内のコメントだけを頼りに実装すると、以下のような不一致が頻繁に発生します。

**よくある落とし穴:**
- ネスト構造の深さが想定と異なる（例: `data[10][14]` → 実際は `data[10][0][14]`）
- 区切り文字が想定と異なる（全角セミコロン `；` vs 半角セミコロン `;`）
- 数値フィールドが文字列として格納されている（例: 回次番号が `"143"` であり `143` ではない）
- ヘッダー行の有無やフィールド数が想定と異なる

**✅ 良いアプローチ:**
1. まず `curl` や `urllib` でデータをダウンロード
2. `json.load()` で読み込み、先頭数件の構造を `print` / `pprint` で確認
3. 確認した構造に基づいてパース処理を実装
4. エッジケース（空データ、不正行）のハンドリングを追加

**❌ 悪いアプローチ:**
- 既存のimporter等のインデックス定数を「多分こうだろう」と転用して、実データ確認せずにパース処理を書く

### 6. 実行前提条件を明記する

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
