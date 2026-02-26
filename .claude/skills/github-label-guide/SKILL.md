---
name: github-label-guide
description: GitHub Issueのラベル付けガイドライン。利用可能なラベル一覧と使い分けルールを提供。Issue作成時にアクティベートします。
---

# GitHub Label Guide（ラベル付けガイド）

## 目的
GitHub Issue作成時に正しいラベルを付与するためのクイックリファレンスを提供します。

## いつアクティベートするか
- `gh issue create` でIssueを作成する時
- ユーザーが「Issue作って」「ラベルつけて」と依頼した時

## ラベル一覧と使い分け

| ラベル名 | 用途 | Issueタイトル例 |
|---------|------|----------------|
| `ProductGoal` | プロダクトゴール（複数PBIの親） | `国会データ完全蓄積・公開（Goal 0011）` |
| `Epic` | エピック（複数PBIをまとめた機能群） | `和暦での日付入力対応` |
| `PBI` | Product Backlog Item（具体的な作業単位） | `[Goal 0013-2] 衆参両院の会派マスターデータ整備` |
| `bug` | バグ報告 | `MonitoringRepository の get_committee_type_coverage が存在しないカラムを参照` |
| `technical-debt` | 技術的負債の解消・リファクタリング | `[Tech Debt] political_party_id の段階的移行・削除計画` |
| `testing` | テスト関連（PBIと併用可） | `議案管理機能の統合テスト作成` |
| `ci-cd` | CI/CDパイプライン関連 | |
| `high-priority` | 緊急対応が必要 | |

## 判断フロー

```
Issueを作成する
↓
Q: プロダクト目標の定義？ → ProductGoal
Q: 複数PBIをまとめるエピック？ → Epic
Q: 具体的な機能実装・タスク？ → PBI
Q: バグ修正？ → bug
Q: リファクタリング・負債解消？ → technical-debt
Q: テスト追加が主目的？ → testing（PBIと併用可）
Q: CI/CD改善？ → ci-cd
```

## 複数ラベルの併用

- `PBI` + `technical-debt`: リファクタリングがプロダクトバックログの一部である場合
- `PBI` + `testing`: テスト作成がPBIとして管理されている場合

## 注意

- PRにはラベルを付けない（このプロジェクトの慣例）
- ラベル名は**正確に**指定すること（例: `tech-debt` ではなく `technical-debt`）
