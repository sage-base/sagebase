# Google認証セットアップガイド

このドキュメントでは、Polibaseでgit worktree環境におけるGoogle OAuth認証（Streamlit標準認証API使用）のセットアップ方法を説明します。

## ✅ 実装完了（Issue #706）

Streamlit 1.42.0の標準Google Sign-In認証が実装されています。
- 環境変数不要（`.streamlit/secrets.toml`で自動設定）
- git worktreeごとの動的ポート対応
- Docker環境での自動セットアップ

## 🎯 概要

Polibaseはgit worktreeごとに異なるポート番号を使用するため、各worktreeで異なるリダイレクトURIが必要になります。このガイドでは、この問題を解決する2つの方法を提供します。

## 📋 前提条件

- Googleアカウント
- Google Cloud Consoleへのアクセス権限
- Polibaseのgit worktree環境

## 🔧 セットアップ方法

### ステップ1: Google Cloud ConsoleでOAuth 2.0クライアントIDを作成

1. **Google Cloud Consoleにアクセス**
   ```
   https://console.cloud.google.com/apis/credentials
   ```

2. **プロジェクトを選択または作成**
   - 既存のプロジェクトを選択するか、新規作成

3. **OAuth同意画面の設定**（初回のみ）
   - 左メニューから「OAuth同意画面」を選択
   - User Type: 「外部」を選択
   - アプリ名: "Polibase" など任意の名前
   - ユーザーサポートメール: あなたのメールアドレス
   - 開発者の連絡先情報: あなたのメールアドレス
   - 「保存して次へ」をクリック

4. **OAuth 2.0 クライアントIDを作成**
   - 「認証情報」タブに戻る
   - 「認証情報を作成」→「OAuth クライアント ID」を選択
   - アプリケーションの種類: **ウェブアプリケーション**
   - 名前: "Polibase Development" など

5. **承認済みのリダイレクト URIを追加**

   **オプションA: 範囲を広く登録（推奨）**

   以下のURIをすべて追加してください：
   ```
   http://localhost:8501/oauth2callback
   http://localhost:8511/oauth2callback
   http://localhost:8521/oauth2callback
   http://localhost:8531/oauth2callback
   http://localhost:8541/oauth2callback
   http://localhost:8551/oauth2callback
   http://localhost:8561/oauth2callback
   http://localhost:8571/oauth2callback
   http://localhost:8581/oauth2callback
   http://localhost:8591/oauth2callback
   ```

   この方法では、一度設定すれば複数のworktreeで使い回せます。

   **オプションB: 個別に登録**

   各worktreeで使用されるポート番号のみを登録します。
   現在のworktreeのポート番号は以下のコマンドで確認できます：
   ```bash
   grep "STREAMLIT_PORT" docker/docker-compose.override.yml | awk '{print $2}' | cut -d: -f1
   ```

6. **認証情報をコピー**
   - クライアントIDとクライアントシークレットが表示されます
   - これらを安全な場所にコピーしてください

### ステップ2: 環境変数を設定

プロジェクトルートの`.env`ファイルに以下を追加：

```bash
# Google OAuth認証情報
GOOGLE_OAUTH_CLIENT_ID="YOUR_CLIENT_ID.apps.googleusercontent.com"
GOOGLE_OAUTH_CLIENT_SECRET="YOUR_CLIENT_SECRET"

# Cookie署名用のシークレット（以下のコマンドで生成）
# python -c "import secrets; print(secrets.token_urlsafe(32))"
STREAMLIT_COOKIE_SECRET="YOUR_RANDOM_SECRET"
```

**Cookie Secretの生成方法**:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### ステップ3: Streamlit認証設定ファイルを生成

以下のコマンドを実行すると、現在のworktreeのポート番号に合わせた`.streamlit/secrets.toml`が自動生成されます：

```bash
./scripts/setup-streamlit-secrets.sh
```

このスクリプトは以下を実行します：
- 現在のworktreeのポート番号を計算
- `.streamlit/secrets.toml`を生成または更新
- `.env`の環境変数を読み込んで設定

**または、`just up`を実行すると自動的に呼ばれます**：
```bash
just up
```

### ステップ4: 動作確認

1. Streamlitアプリを起動：
   ```bash
   just up
   ```

2. ブラウザで表示されたURLにアクセス（例: `http://localhost:8521`）

3. 「🔑 Googleでログイン」ボタンをクリック

4. Googleのログイン画面が表示される

5. ログイン成功後、ユーザー情報が表示される

## 🔍 トラブルシューティング

### エラー: "redirect_uri_mismatch"

**原因**: Google Cloud Consoleに登録されているリダイレクトURIと、実際のポート番号が一致していません。

**解決方法**:
1. 現在のポート番号を確認：
   ```bash
   grep ":8501" docker/docker-compose.override.yml | awk '{print $2}' | cut -d: -f1 | sed 's/"//g'
   ```

2. Google Cloud Consoleにそのポート番号のURIを追加：
   ```
   http://localhost:<ポート番号>/oauth2callback
   ```

3. `.streamlit/secrets.toml`を再生成：
   ```bash
   ./scripts/setup-streamlit-secrets.sh
   ```

### エラー: "To use authentication features you need to configure credentials"

**原因**: `.streamlit/secrets.toml`が存在しないか、正しく設定されていません。

**解決方法**:
1. `.env`ファイルに認証情報が正しく設定されているか確認
2. スクリプトを実行：
   ```bash
   ./scripts/setup-streamlit-secrets.sh
   ```

### 認証情報が反映されない

**原因**: 環境変数がコンテナに渡されていません。

**解決方法**:
1. Dockerコンテナを再起動：
   ```bash
   just down
   just up
   ```

## 🔐 セキュリティに関する注意

- ✅ `.streamlit/secrets.toml`は`.gitignore`に含まれています
- ⚠️ このファイルを絶対にGitにコミットしないでください
- ⚠️ `.env`ファイルも絶対にGitにコミットしないでください
- ⚠️ クライアントシークレットは他人と共有しないでください

## 📚 関連ファイル

- `.streamlit/secrets.toml.example`: 設定ファイルのサンプル
- `scripts/setup-streamlit-secrets.sh`: 自動生成スクリプト
- `scripts/setup-worktree-ports.sh`: ポート番号計算スクリプト
- `justfile`: ビルドタスク定義（自動セットアップを含む）

## 💡 ヒント

### 複数のworktreeで作業する場合

1回の設定で複数のworktreeに対応したい場合は、Google Cloud Consoleに広範囲のポート番号を登録しておくことをお勧めします（8501-8600など）。

### 本番環境への移行

本番環境では、以下のように設定を変更してください：

```toml
[auth.production]
redirect_uri = "https://your-app-domain.com/oauth2callback"
cookie_secret = "PRODUCTION_SECRET"
client_id = "PRODUCTION_CLIENT_ID"
client_secret = "PRODUCTION_CLIENT_SECRET"
```

## 🆘 サポート

問題が解決しない場合は、以下を確認してください：

1. Streamlitのバージョンが1.42.0以上であること
2. Google Cloud Consoleの設定が正しいこと
3. `.env`ファイルに正しい認証情報が設定されていること
4. `docker/docker-compose.override.yml`が存在すること
5. `.streamlit/secrets.toml`が正しく生成されていること

それでも解決しない場合は、GitHubのIssueを作成してください。
