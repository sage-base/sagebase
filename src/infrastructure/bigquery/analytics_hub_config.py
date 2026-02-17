"""Analytics Hub デフォルト設定.

Exchange/Listing作成時のデフォルト値を一元管理する。
CLIコマンドとスタンドアロンスクリプトの両方から参照される。
"""

DEFAULT_EXCHANGE_ID = "sagebase_exchange"
DEFAULT_LISTING_ID = "sagebase_gold_listing"
DEFAULT_EXCHANGE_DISPLAY_NAME = "Sagebase 政治活動データ"
DEFAULT_EXCHANGE_DESCRIPTION = (
    "日本の政治活動追跡データを提供します。"
    "全1,966地方議会の議事録・発言・議案賛否等のデータを含みます。"
)
DEFAULT_LISTING_DISPLAY_NAME = "Sagebase Gold Layer - 政治活動データ"
DEFAULT_LISTING_DESCRIPTION = (
    "日本の地方議会・国会の政治活動データ（Gold Layer）。\n\n"
    "20テーブル: 政治家、政党、選挙、会議体、議事録、発言、議案、賛否記録等。\n"
    "全1,966地方議会対応。\n\n"
    "データ更新頻度: 随時（新規議事録の処理後にエクスポート）"
)
DEFAULT_LISTING_DOCUMENTATION = (
    "# Sagebase Gold Layer データセット\n\n"
    "## 概要\n"
    "日本の地方議会・国会の政治活動データを提供するデータセットです。\n\n"
    "## テーブル一覧（20テーブル）\n"
    "- politicians: 政治家\n"
    "- political_parties: 政党\n"
    "- elections: 選挙\n"
    "- election_members: 選挙結果メンバー\n"
    "- governing_bodies: 開催主体（議会）\n"
    "- conferences: 会議体\n"
    "- conference_members: 会議体メンバー\n"
    "- parliamentary_groups: 議員団（会派）\n"
    "- parliamentary_group_memberships: 議員団所属履歴\n"
    "- meetings: 会議\n"
    "- minutes: 議事録\n"
    "- conversations: 発言\n"
    "- speakers: 発言者\n"
    "- proposals: 議案\n"
    "- proposal_submitters: 議案提出者\n"
    "- proposal_deliberations: 議案審議\n"
    "- proposal_judges: 議案賛否（個人）\n"
    "- proposal_parliamentary_group_judges: 議案賛否（会派）\n"
    "- proposal_judge_parliamentary_groups: 賛否と会派の中間テーブル\n"
    "- proposal_judge_politicians: 賛否と政治家の中間テーブル\n\n"
    "## データ更新頻度\n"
    "随時（新規議事録の処理・エクスポート後に反映されます）\n\n"
    "## ライセンス\n"
    "本データは公開情報（議会議事録等）を元に構造化したデータです。\n"
    "クエリ実行コストはサブスクライバー側で課金されます。\n"
)
