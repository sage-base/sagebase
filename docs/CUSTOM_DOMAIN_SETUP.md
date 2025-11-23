# カスタムドメイン設定ガイド

このドキュメントでは、Sagebase (sage-base.com) のカスタムドメイン設定手順を説明します。

## 📋 前提条件

- [x] Cloudflareでsage-base.comドメインを購入済み
- [ ] Streamlit Cloudにアプリがデプロイ済み
- [ ] Google Analytics 4 プロパティを作成済み（アナリティクス使用時）
- [ ] Cloudflare Workers へのアクセス権限（セキュリティヘッダー設定時）

---

## 🌐 ステップ1: Cloudflare DNS設定

### 1.1 Cloudflareダッシュボードにアクセス

1. [Cloudflare Dashboard](https://dash.cloudflare.com/)にログイン
2. **sage-base.com** ドメインを選択
3. 左サイドバーから **DNS** > **Records** を選択

### 1.2 DNSレコードの追加

Streamlit Cloudが提供するIPアドレスまたはCNAMEを設定します。

#### パターンA: CNAMEレコード（推奨）

Streamlit CloudアプリのデフォルトURLを使用する場合：

```
Type: CNAME
Name: @ (またはsage-base.com)
Target: your-app-name.streamlit.app
TTL: Auto
Proxy status: Proxied (オレンジ色のアイコン)
```

#### パターンB: Aレコード

Streamlit CloudがIPアドレスを提供する場合：

```
Type: A
Name: @ (またはsage-base.com)
IPv4 address: xxx.xxx.xxx.xxx (Streamlit Cloudから提供されたIP)
TTL: Auto
Proxy status: Proxied (オレンジ色のアイコン)
```

### 1.3 wwwサブドメインの設定（オプション）

www.sage-base.comからのアクセスをリダイレクトする場合：

```
Type: CNAME
Name: www
Target: sage-base.com
TTL: Auto
Proxy status: Proxied
```

Cloudflare Page Rulesで301リダイレクトを設定：
- URL: `www.sage-base.com/*`
- Setting: Forwarding URL (301 Permanent Redirect)
- Destination: `https://sage-base.com/$1`

---

## ☁️ ステップ2: Streamlit Cloud設定

### 2.1 Streamlit Cloudダッシュボードにアクセス

1. [Streamlit Cloud](https://share.streamlit.io/)にログイン
2. デプロイ済みのアプリ（sagebase）を選択
3. アプリの **Settings** タブを開く

### 2.2 カスタムドメインの追加

1. **Settings** > **Custom Domain** セクションに移動
2. **Add domain** をクリック
3. ドメイン名を入力: `sage-base.com`
4. **Add domain** をクリック

### 2.3 SSL証明書の検証

- Streamlit Cloudが自動的にLet's EncryptのSSL証明書を発行します
- DNS設定が正しい場合、数分から数時間で証明書が有効になります
- ステータスが **Active** になるまで待ちます

### 2.4 環境変数の更新

Streamlit CloudのSettings > Secretsに以下の環境変数を追加：

```toml
# Google OAuth リダイレクトURIを本番ドメインに変更
GOOGLE_OAUTH_REDIRECT_URI = "https://sage-base.com/"

# Google Analytics測定IDを設定
GOOGLE_ANALYTICS_ID = "G-XXXXXXXXXX"

# その他の本番環境用設定
ENVIRONMENT = "production"
```

---

## 🔒 ステップ3: セキュリティ設定（Cloudflare Workers）

### 3.1 Cloudflare Workerの作成

1. Cloudflareダッシュボード > **Workers & Pages** を選択
2. **Create Worker** をクリック
3. Worker名を入力（例: `sagebase-security-headers`）

### 3.2 Workerスクリプトの設定

以下のコードをコピーして貼り付け：

```javascript
// Cloudflare Worker for adding security headers
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const response = await fetch(request)
  const newResponse = new Response(response.body, response)

  // Security Headers
  newResponse.headers.set('X-Frame-Options', 'DENY')
  newResponse.headers.set('X-Content-Type-Options', 'nosniff')
  newResponse.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin')
  newResponse.headers.set('Permissions-Policy', 'geolocation=(), microphone=(), camera=()')
  newResponse.headers.set('X-XSS-Protection', '1; mode=block')
  newResponse.headers.set('Strict-Transport-Security', 'max-age=31536000; includeSubDomains; preload')

  // Content Security Policy
  const csp = [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://www.googletagmanager.com https://www.google-analytics.com",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com",
    "img-src 'self' data: https: blob:",
    "connect-src 'self' https://www.google-analytics.com https://www.googletagmanager.com wss://*.streamlit.app wss://sage-base.com",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "upgrade-insecure-requests"
  ].join('; ')
  newResponse.headers.set('Content-Security-Policy', csp)

  // HTTPS redirect
  if (request.url.startsWith('http://')) {
    const httpsUrl = request.url.replace('http://', 'https://')
    return Response.redirect(httpsUrl, 301)
  }

  return newResponse
}
```

### 3.3 Workerのデプロイとルート設定

1. **Save and Deploy** をクリック
2. **Workers & Pages** > **sagebase-security-headers** を選択
3. **Triggers** タブを開く
4. **Add route** をクリック
5. Route: `sage-base.com/*`
6. Zone: `sage-base.com`
7. **Add route** をクリック

---

## 📊 ステップ4: Google Analytics設定

### 4.1 GA4プロパティの作成

1. [Google Analytics](https://analytics.google.com/)にアクセス
2. **Admin** > **Create Property** を選択
3. プロパティ名: `Sagebase`
4. タイムゾーン: `Japan`
5. 通貨: `Japanese Yen (¥)`

### 4.2 データストリームの設定

1. **Data Streams** > **Add stream** > **Web** を選択
2. Website URL: `https://sage-base.com`
3. Stream name: `Sagebase Production`
4. **Create stream** をクリック

### 4.3 測定IDのコピー

1. データストリームの詳細画面で **Measurement ID** をコピー
2. 形式: `G-XXXXXXXXXX`
3. Streamlit CloudのSecretsに `GOOGLE_ANALYTICS_ID` として追加

---

## 🔍 ステップ5: SEO設定

### 5.1 robots.txtとsitemap.xmlの配置

これらのファイルはすでにプロジェクトルートに作成済みです：
- `robots.txt`
- `sitemap.xml`

Streamlit Cloudにデプロイされると、自動的に以下のURLでアクセス可能になります：
- https://sage-base.com/robots.txt
- https://sage-base.com/sitemap.xml

### 5.2 Google Search Consoleへの登録

1. [Google Search Console](https://search.google.com/search-console)にアクセス
2. **Add property** をクリック
3. プロパティタイプ: **Domain**
4. ドメイン名: `sage-base.com` を入力
5. DNS認証用のTXTレコードをCloudflare DNSに追加
6. **Verify** をクリック

### 5.3 サイトマップの送信

1. Google Search Consoleの **Sitemaps** セクションに移動
2. サイトマップURL: `https://sage-base.com/sitemap.xml` を入力
3. **Submit** をクリック

---

## ✅ ステップ6: 動作確認

### 6.1 DNS伝播の確認

```bash
# nslookupでDNS設定を確認
nslookup sage-base.com

# digコマンドで詳細確認
dig sage-base.com
```

### 6.2 SSL証明書の確認

ブラウザでhttps://sage-base.comにアクセスし、アドレスバーの鍵アイコンをクリック：
- 証明書が有効か確認
- 発行者: Let's Encrypt

### 6.3 セキュリティヘッダーの確認

開発者ツールを開いて確認：
1. ブラウザで https://sage-base.com を開く
2. 開発者ツール（F12）> **Network** タブ
3. ページをリロード
4. レスポンスヘッダーに以下が含まれているか確認：
   - `X-Frame-Options: DENY`
   - `X-Content-Type-Options: nosniff`
   - `Content-Security-Policy: ...`
   - `Strict-Transport-Security: ...`

オンラインツールでも確認可能：
- [Security Headers](https://securityheaders.com/?q=sage-base.com)

### 6.4 Google Analyticsの確認

1. Google Analytics > **Realtime** レポートを開く
2. https://sage-base.com にアクセス
3. リアルタイムレポートにアクセスが表示されることを確認

### 6.5 全ページの動作確認

以下のページが正しく動作するか確認：
- [ ] https://sage-base.com/ (ホーム)
- [ ] https://sage-base.com/meetings (会議管理)
- [ ] https://sage-base.com/political_parties (政党管理)
- [ ] https://sage-base.com/politicians (政治家管理)
- [ ] https://sage-base.com/conversations (発言レコード)
- [ ] https://sage-base.com/processes (処理実行)

### 6.6 HTTPSリダイレクトの確認

```bash
# HTTPアクセスがHTTPSにリダイレクトされるか確認
curl -I http://sage-base.com
# 期待される結果: 301 Moved Permanently
# Location: https://sage-base.com
```

---

## 🐛 トラブルシューティング

### DNS設定が反映されない

**原因**: DNS伝播に時間がかかっている
**解決策**:
- 最大48時間待つ（通常は数時間で完了）
- Cloudflare DNSのTTLを確認
- `dig sage-base.com` で現在の設定を確認

### SSL証明書エラー

**原因**: Streamlit Cloudの証明書発行に失敗
**解決策**:
- DNS設定が正しいか確認
- Streamlit CloudのCustom Domainページでステータスを確認
- 証明書の再発行を試みる（Remove domain → Add domain）

### Cloudflare Workerが動作しない

**原因**: ルート設定が正しくない
**解決策**:
- Workers & Pages > Triggers でルート設定を確認
- `sage-base.com/*` が正しく設定されているか確認
- Cloudflare ProxyがON（オレンジ色）になっているか確認

### Google Analyticsでデータが取得できない

**原因**: 測定IDが正しく設定されていない
**解決策**:
- Streamlit CloudのSecretsで `GOOGLE_ANALYTICS_ID` を確認
- ブラウザの開発者ツールでgtagスクリプトが読み込まれているか確認
- アドブロッカーを無効にしてテスト

---

## 📚 参考リンク

- [Streamlit Cloud Custom Domains](https://docs.streamlit.io/streamlit-community-cloud/share-your-app/custom-domains)
- [Cloudflare DNS Documentation](https://developers.cloudflare.com/dns/)
- [Cloudflare Workers Documentation](https://developers.cloudflare.com/workers/)
- [Google Analytics 4 Documentation](https://support.google.com/analytics/answer/10089681)
- [Google Search Console Help](https://support.google.com/webmasters/)

---

## ✨ 完了後の確認項目

- [ ] https://sage-base.com でアプリにアクセスできる
- [ ] SSL証明書が有効（鍵アイコンが表示される）
- [ ] HTTPからHTTPSへ自動リダイレクトされる
- [ ] セキュリティヘッダーが正しく設定されている
- [ ] Google Analyticsでトラッキングが動作している
- [ ] robots.txt と sitemap.xml にアクセスできる
- [ ] Google Search Consoleでサイトが認証されている
- [ ] 全ページが正常に動作する
- [ ] OAuth認証が本番ドメインで動作する

すべてのチェック項目が完了したら、Issue #726を完了としてクローズできます！ 🎉
