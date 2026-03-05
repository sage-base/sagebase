---
name: gemini-search
description: Google検索が必要な場面でgemini-cliを使って正確な情報を取得する。政治家名、所属組織、会議体など、正確性が重要な固有名詞の検索時にアクティベートします。
---

# Gemini Search（Google検索代行）

## 目的
Claude Codeの内部知識だけでは精度が不十分な検索（特に日本の政治家・組織に関する固有名詞）を、gemini-cliを経由してGoogle検索で補完します。

## いつアクティベートするか
- 政治家の正式名称・所属政党・役職を確認する時
- 会議体・地方自治体の組織名を正確に調べる時
- 現在の役職者（議長、知事など）を特定する時
- Webスクレイピング対象のURL・サイト構造を事前調査する時
- Claude Codeの内部知識では不確実な事実確認が必要な時

## 使い方

### 基本コマンド
```bash
./scripts/gemini_search.sh "検索クエリ"
```

### よくある検索パターン

#### 政治家の情報確認
```bash
./scripts/gemini_search.sh "高市早苗 所属政党 現在の役職"
./scripts/gemini_search.sh "東京都議会 議長 2026年"
```

#### 組織・会議体の正式名称
```bash
./scripts/gemini_search.sh "横浜市議会 公式サイト URL"
./scripts/gemini_search.sh "国会 常任委員会 一覧"
```

#### Webスクレイピング事前調査
```bash
./scripts/gemini_search.sh "○○市議会 議員名簿 ページ構造"
```

## チェックリスト
- [ ] 検索クエリは具体的か（「政治家」ではなく「高市早苗 所属政党」のように）
- [ ] 検索結果の情報が「未確認」とマークされていたら、追加検索で裏取りする
- [ ] 取得した情報をそのまま使わず、プロジェクトのデータと照合する

## 前提条件
- `@google/gemini-cli` がグローバルインストール済み（`npm install -g @google/gemini-cli`）
- `GOOGLE_API_KEY` が `.env` に設定済み

## 注意事項
- gemini-cliの応答にはGeminiモデルの推論が含まれるため、**事実として鵜呑みにせず裏取りすること**
- 大量の連続検索はAPIクォータを消費するため、必要最小限にする
- スクリプトのパス: `scripts/gemini_search.sh`
