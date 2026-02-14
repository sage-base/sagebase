---
name: streamlit-verification
description: Streamlit UIの動作確認手順を提供します。Google認証スキップでの起動方法、ブラウザでの確認手順、Playwright CLIによる自動確認をカバー。UIの変更・修正後に動作確認する時にアクティベートします。
---

# Streamlit Verification（Streamlit動作確認）

## 目的
Streamlit UIの変更後に動作確認を行うための手順を提供します。特にClaude Codeなどの自動化エージェントがGoogle認証に阻まれずに動作確認を実施できるようにします。

## いつアクティベートするか
- Streamlit UIの変更・修正後に動作確認する時
- UIの表示や挙動をブラウザで確認したい時
- Claude CodeにStreamlitの動作確認を依頼する時

## クイックチェックリスト

### 起動
- [ ] `just up-noauth` で認証スキップ版Streamlitを起動している（`just up`ではなく）
- [ ] コンテナが正常に起動し、Streamlitがアクセス可能

### 確認
- [ ] 対象ページがエラーなく表示される
- [ ] 変更した箇所が期待通りに動作する
- [ ] コンソールにエラーが出ていない

### 終了
- [ ] 確認後、必要に応じて `just down` でコンテナを停止
- [ ] `playwright-cli close` でブラウザを閉じる

## 起動コマンド

### 認証スキップ版（動作確認用）

```bash
# Google認証をスキップしてStreamlitを起動（推奨）
just up-noauth
```

**仕組み**: `GOOGLE_OAUTH_DISABLED=true` 環境変数をコンテナに渡すことで、`app.py`のGoogle OAuth認証チェックと`@require_auth`デコレータを無効化します。`.env`ファイルの変更は不要です。

### 通常版（本番同等の認証あり）

```bash
# Google認証ありでStreamlitを起動
just up
```

## ポート確認

git worktreeを使用している場合、ポートがデフォルト（8501）と異なる場合があります。

```bash
# ポート確認
just ports

# または docker-compose.override.yml を確認
cat docker/docker-compose.override.yml
```

## Playwright CLI による自動確認

Claude Codeがブラウザ経由で動作確認する場合は、`playwright-cli` コマンドを使用します。

### 基本的な確認手順

```bash
# 1. ブラウザを開いてページにアクセス
playwright-cli open http://localhost:{PORT}

# 2. ページ状態をYAMLスナップショットで確認
playwright-cli snapshot

# 3. スクリーンショットで視覚的に確認
playwright-cli screenshot

# 4. 要素を操作（refはsnapshotの結果から取得）
playwright-cli click e21
playwright-cli fill e5 "テスト入力"

# 5. 操作後の状態を再確認
playwright-cli snapshot

# 6. ブラウザを閉じる
playwright-cli close
```

### 確認例（サイドバーナビゲーション）

```bash
playwright-cli open http://localhost:8501
playwright-cli snapshot
playwright-cli click e10          # サイドバーのメニュー項目をクリック
playwright-cli snapshot           # 遷移先ページの状態を確認
playwright-cli screenshot         # 視覚的にキャプチャ
playwright-cli close
```

### コンソール・ネットワーク確認

```bash
# コンソールエラーの確認
playwright-cli console

# ネットワークリクエストの確認
playwright-cli network
```

## 注意事項

- **`just up-noauth`は開発・動作確認専用**です。本番環境では必ず認証を有効にしてください
- worktree環境ではポートが自動割り当てされるため、起動時のログでポート番号を確認してください
- Streamlitの変更をホットリロードで反映したい場合、ファイル保存後にブラウザをリロードしてください
