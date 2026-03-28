---
title: "使い方ガイド"
date: 2025-01-16
draft: false
ShowBreadCrumbs: false
description: "BigQuery Analytics Hubを通じてSagebaseのデータにアクセスする方法をご案内します。"
---

Sagebase（政治ベース）のデータは、Google CloudのBigQuery Analytics Hubを通じて公開データセットとして提供しています。本ページでは、ご自身のBigQuery環境からデータを参照できるようにするまでの手順をご案内します。

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
  speaker_name,
  speech_content,
  meeting_date,
  conference_name
FROM `your-project.sagebase.speeches`
WHERE speaker_name LIKE '%山田%'
ORDER BY meeting_date DESC
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
