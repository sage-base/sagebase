---
title: "使い方ガイド"
date: 2025-01-16
draft: false
ShowBreadCrumbs: false
description: "BigQuery Analytics Hubを通じてSagebaseのデータにアクセスする方法をご案内します。"
---

Sagebase（政治ベース）のデータは、Google CloudのBigQuery Analytics Hubを通じて公開データセットとして提供しています。本ページでは、ご自身のBigQuery環境からデータを参照できるようにするまでの手順をご案内します。

### 公開データセット

用途に応じて3つのデータセットを提供しています。

| データセット | 内容 | 用途 |
|---|---|---|
| **sagebase** | ユーザー向け最新状態VIEW | 通常のデータ分析・アプリケーション開発にはこちらを利用 |
| **sagebase_vault** | 変更履歴（Data Vault形式） | データの変更履歴を追跡したい場合 |
| **sagebase_source** | 生データ（PostgreSQLミラー） | 内部構造を直接参照したい場合 |

通常の利用では **sagebase** データセットのみで十分です。

<nav class="nav-cards" aria-label="セクションナビゲーション">
  <div class="nav-cards-grid">
    <a href="#前提条件" class="nav-card">
      <span class="nav-card-number">00</span>
      <h3 class="nav-card-title">前提条件</h3>
      <p class="nav-card-desc">必要なアカウントとプロジェクト</p>
    </a>
    <a href="#ステップ1analytics-hubでリスティングを検索" class="nav-card">
      <span class="nav-card-number">01</span>
      <h3 class="nav-card-title">リスティング検索</h3>
      <p class="nav-card-desc">Analytics Hubでデータを見つける</p>
    </a>
    <a href="#ステップ2データセットをサブスクライブ" class="nav-card">
      <span class="nav-card-number">02</span>
      <h3 class="nav-card-title">サブスクライブ</h3>
      <p class="nav-card-desc">自分のプロジェクトにデータを追加</p>
    </a>
    <a href="#ステップ3bigqueryでデータを参照" class="nav-card">
      <span class="nav-card-number">03</span>
      <h3 class="nav-card-title">データ参照</h3>
      <p class="nav-card-desc">SQLでデータを分析</p>
    </a>
    <a href="#料金について" class="nav-card">
      <span class="nav-card-number">04</span>
      <h3 class="nav-card-title">料金</h3>
      <p class="nav-card-desc">無料枠と課金の仕組み</p>
    </a>
  </div>
</nav>

---

## 前提条件

- Google Cloudアカウントをお持ちであること
- BigQueryが有効なGoogle Cloudプロジェクトがあること（[無料枠](https://cloud.google.com/bigquery/pricing?hl=ja)で利用可能です）

---

## ステップ1：Analytics Hubでリスティングを検索

1. [Google Cloud Console](https://console.cloud.google.com/) にログイン
2. 左メニューから **「BigQuery」** → **「Analytics Hub」** を選択
3. 検索バーで **「Sagebase」** または **「政治ベース」** と検索
4. 表示された **Sagebaseのリスティング** をクリック

---

## ステップ2：データセットをサブスクライブ

Sagebaseでは3つのリスティング（sagebase、sagebase_vault、sagebase_source）を公開しています。通常の利用では **sagebase** のみサブスクライブすれば十分です。

各リスティングについて以下の手順でサブスクライブします：

1. リスティングの詳細ページで **「データセットに追加」** ボタンをクリック
2. データを追加するGoogle Cloudプロジェクトを選択
3. 必要に応じて、リンクされたデータセットの名前を変更（デフォルトのままでもOK）
4. **「保存」** をクリック

これで、ご自身のBigQueryプロジェクトにSagebaseのデータセットがリンクされます。

---

## ステップ3：BigQueryでデータを参照

1. BigQueryコンソールの左ペインで、ご自身のプロジェクト配下に追加されたデータセットを確認
2. テーブル一覧から参照したいテーブルを選択
3. **「プレビュー」** でデータの内容を確認、または **「クエリ」** をクリックしてSQLで分析

### クエリ例

```sql
-- 特定の政治家の発言を検索
SELECT
  s.name AS speaker_name,
  c.content AS speech_content,
  m.date AS meeting_date,
  conf.name AS conference_name
FROM `your-project.sagebase.conversations` c
JOIN `your-project.sagebase.speakers` s ON c.speaker_id = s.id
JOIN `your-project.sagebase.minutes` mi ON c.minutes_id = mi.id
JOIN `your-project.sagebase.meetings` m ON mi.meeting_id = m.id
JOIN `your-project.sagebase.conferences` conf ON m.conference_id = conf.id
WHERE s.name LIKE '%山田%'
ORDER BY m.date DESC
LIMIT 100;
```

---

## 料金について

- **データセットのサブスクライブ**: 無料
- **クエリ実行**: BigQueryの通常料金が適用されます（毎月1TBまで無料）
- 詳しくは [BigQueryの料金ページ](https://cloud.google.com/bigquery/pricing?hl=ja) をご参照ください

---

## 今後の提供予定

### Snowflake Marketplace

Snowflake Marketplaceでも公開データセットとして提供を予定しています。

- SQLで直接クエリ可能
- Snowflakeユーザーは即座にアクセス可能
- データのコピー不要（Zero-Copy Cloning）

公開開始時期については、本ページで順次お知らせいたします。

---

## お問い合わせ

データの利用方法や詳細については、[お問い合わせページ](/contact)からご連絡ください。
