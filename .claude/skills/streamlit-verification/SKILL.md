---
name: streamlit-verification
description: Streamlit UIの動作確認手順を提供します。Google認証スキップでの起動方法、ブラウザでの確認手順、Playwrightによる自動確認をカバー。UIの変更・修正後に動作確認する時にアクティベートします。
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

## Playwright MCP による自動確認

Claude Codeがブラウザ経由で動作確認する場合は、Playwright MCPツールを使用します。

### 基本的な確認手順

1. **ページを開く**: `browser_navigate` でStreamlit URLにアクセス
2. **スナップショット取得**: `browser_snapshot` でページのアクセシビリティツリーを確認
3. **スクリーンショット**: `browser_take_screenshot` で視覚的な確認
4. **要素の操作**: `browser_click`, `browser_type` でUI操作をテスト

### 確認例

```
1. browser_navigate → http://localhost:{PORT}
2. browser_snapshot → ページ構造を確認
3. browser_click → サイドバーのメニュー項目をクリック
4. browser_snapshot → 遷移先ページを確認
5. browser_take_screenshot → 視覚的にキャプチャ
```

## 注意事項

- **`just up-noauth`は開発・動作確認専用**です。本番環境では必ず認証を有効にしてください
- worktree環境ではポートが自動割り当てされるため、起動時のログでポート番号を確認してください
- Streamlitの変更をホットリロードで反映したい場合、ファイル保存後にブラウザをリロードしてください
