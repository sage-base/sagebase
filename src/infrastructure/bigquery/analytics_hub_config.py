"""Analytics Hub デフォルト設定.

Exchange/Listing作成時のデフォルト値を一元管理する。
CLIコマンドとスタンドアロンスクリプトの両方から参照される。

3データセット（Source / Vault / Main）をそれぞれ個別のListingとして公開する。
"""

from dataclasses import dataclass


DEFAULT_EXCHANGE_ID = "sagebase_exchange"
DEFAULT_EXCHANGE_DISPLAY_NAME = "Sagebase 政治活動データ"
DEFAULT_EXCHANGE_DESCRIPTION = (
    "日本の政治活動追跡データを提供します。"
    "全1,966地方議会の議事録・発言・議案賛否等のデータを含みます。"
)


@dataclass(frozen=True)
class ListingConfig:
    """Analytics Hub Listing設定."""

    listing_id: str
    dataset_id: str
    display_name: str
    description: str
    documentation: str


LISTING_CONFIGS: list[ListingConfig] = [
    ListingConfig(
        listing_id="sagebase_source_listing",
        dataset_id="sagebase_source",
        display_name="Sagebase Source Layer - 政治活動データ",
        description=(
            "日本の地方議会・国会の政治活動データ（Source Layer）。\n\n"
            "23テーブル: 政治家、政党、選挙、会議体、議事録、発言、議案、賛否記録等。\n"
            "全1,966地方議会対応。PostgreSQL Gold Layerのミラーリング。\n\n"
            "データ更新頻度: 随時（新規議事録の処理後にエクスポート）"
        ),
        documentation=(
            "# Sagebase Source Layer データセット\n\n"
            "## 概要\n"
            "PostgreSQL Gold Layerのミラーリングデータセットです。\n"
            "日本の地方議会・国会の政治活動データを提供します。\n\n"
            "## 主なテーブル\n"
            "- politicians: 政治家\n"
            "- political_parties: 政党\n"
            "- governing_bodies: 開催主体（議会）\n"
            "- conferences: 会議体\n"
            "- meetings: 会議\n"
            "- minutes: 議事録\n"
            "- conversations: 発言\n"
            "- speakers: 発言者\n"
            "- proposals: 議案\n"
            "- proposal_judges: 議案賛否\n\n"
            "## データ更新頻度\n"
            "随時（export-to-bq実行後に反映）\n\n"
            "## ライセンス\n"
            "本データは公開情報（議会議事録等）を元に構造化したデータです。\n"
            "クエリ実行コストはサブスクライバー側で課金されます。\n"
        ),
    ),
    ListingConfig(
        listing_id="sagebase_vault_listing",
        dataset_id="sagebase_vault",
        display_name="Sagebase Vault Layer - Data Vault形式",
        description=(
            "Data Vault 2.0形式で構造化された政治活動データ（Vault Layer）。\n\n"
            "Hub/Link/Satelliteテーブルによる履歴管理。\n"
            "dbtによりSource Layerから変換・生成されます。\n\n"
            "データ更新頻度: dbt run実行時"
        ),
        documentation=(
            "# Sagebase Vault Layer データセット\n\n"
            "## 概要\n"
            "Data Vault 2.0形式で構造化されたデータセットです。\n"
            "Source Layerからdbtで変換・生成されます。\n\n"
            "## 構造\n"
            "- Hub: ビジネスキーの管理\n"
            "- Link: エンティティ間の関連\n"
            "- Satellite: 属性の履歴管理\n\n"
            "## データ更新頻度\n"
            "dbt run実行時に更新されます。\n"
        ),
    ),
    ListingConfig(
        listing_id="sagebase_main_listing",
        dataset_id="sagebase",
        display_name="Sagebase Main Layer - 分析用マート",
        description=(
            "分析用に最適化されたマートデータセット（Main Layer）。\n\n"
            "Vault Layerから生成されたVIEWで構成。\n"
            "ユーザー向けの最終的なデータアクセスポイントです。\n\n"
            "データ更新頻度: dbt run実行時（VIEW経由でリアルタイム反映）"
        ),
        documentation=(
            "# Sagebase Main Layer データセット\n\n"
            "## 概要\n"
            "ユーザー向けの分析用マートデータセットです。\n"
            "Vault Layerから生成されたVIEWで構成されています。\n\n"
            "## 特徴\n"
            "- VIEWベースのため、Vault更新が即座に反映\n"
            "- 分析しやすいスター/スノーフレークスキーマ\n\n"
            "## データ更新頻度\n"
            "VIEWのため、参照元のVault Layer更新時にリアルタイム反映されます。\n"
        ),
    ),
]

# 後方互換: 既存コードが参照している定数
DEFAULT_LISTING_ID = LISTING_CONFIGS[0].listing_id
DEFAULT_LISTING_DISPLAY_NAME = LISTING_CONFIGS[0].display_name
DEFAULT_LISTING_DESCRIPTION = LISTING_CONFIGS[0].description
DEFAULT_LISTING_DOCUMENTATION = LISTING_CONFIGS[0].documentation
