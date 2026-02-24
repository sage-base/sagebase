"""BigQuery Gold Layerテーブルスキーマ定義.

PostgreSQLのGold Layerテーブル構造をBigQuery用に定義する。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from google.cloud.bigquery import SchemaField

# PostgreSQL → BigQuery 型マッピング
PG_TO_BQ_TYPE_MAP: dict[str, str] = {
    "SERIAL": "INT64",
    "INTEGER": "INT64",
    "INT": "INT64",
    "VARCHAR": "STRING",
    "TEXT": "STRING",
    "CHAR": "STRING",
    "BOOLEAN": "BOOL",
    "DATE": "DATE",
    "TIMESTAMP": "TIMESTAMP",
    "TIMESTAMP WITH TIME ZONE": "TIMESTAMP",
    "JSONB": "JSON",
    "JSON": "JSON",
    "DECIMAL": "NUMERIC",
    "NUMERIC": "NUMERIC",
    "FLOAT": "FLOAT64",
    "UUID": "STRING",
}


@dataclass(frozen=True)
class BQColumnDef:
    """BigQueryカラム定義."""

    name: str
    bq_type: str
    mode: str = "NULLABLE"
    description: str = ""


@dataclass(frozen=True)
class BQTableDef:
    """BigQueryテーブル定義."""

    table_id: str
    description: str
    columns: tuple[BQColumnDef, ...]


def to_bigquery_schema(table_def: BQTableDef) -> list[SchemaField]:
    """BQTableDefをBigQuery SchemaFieldリストに変換する."""
    from google.cloud.bigquery import SchemaField

    return [
        SchemaField(
            name=col.name,
            field_type=col.bq_type,
            mode=col.mode,
            description=col.description,
        )
        for col in table_def.columns
    ]


# ==========================================================================
# Gold Layerテーブル定義（全20テーブル）
# ==========================================================================

_POLITICIANS = BQTableDef(
    table_id="politicians",
    description="政治家",
    columns=(
        BQColumnDef("id", "INT64", "REQUIRED", "政治家ID"),
        BQColumnDef("name", "STRING", "REQUIRED", "氏名"),
        BQColumnDef("prefecture", "STRING", description="都道府県"),
        BQColumnDef("furigana", "STRING", description="ふりがな"),
        BQColumnDef("district", "STRING", description="選挙区"),
        BQColumnDef("profile_page_url", "STRING", description="プロフィールページURL"),
        BQColumnDef("created_at", "TIMESTAMP", description="作成日時"),
        BQColumnDef("updated_at", "TIMESTAMP", description="更新日時"),
    ),
)

_POLITICAL_PARTIES = BQTableDef(
    table_id="political_parties",
    description="政党",
    columns=(
        BQColumnDef("id", "INT64", "REQUIRED", "政党ID"),
        BQColumnDef("name", "STRING", "REQUIRED", "政党名"),
        BQColumnDef("members_list_url", "STRING", description="所属議員一覧URL"),
        BQColumnDef("created_at", "TIMESTAMP", description="作成日時"),
        BQColumnDef("updated_at", "TIMESTAMP", description="更新日時"),
    ),
)

_ELECTIONS = BQTableDef(
    table_id="elections",
    description="選挙",
    columns=(
        BQColumnDef("id", "INT64", "REQUIRED", "選挙ID"),
        BQColumnDef("governing_body_id", "INT64", "REQUIRED", "開催主体ID"),
        BQColumnDef("term_number", "INT64", "REQUIRED", "期番号"),
        BQColumnDef("election_date", "DATE", "REQUIRED", "選挙実施日"),
        BQColumnDef("election_type", "STRING", description="選挙種別"),
        BQColumnDef("created_at", "TIMESTAMP", description="作成日時"),
        BQColumnDef("updated_at", "TIMESTAMP", description="更新日時"),
    ),
)

_ELECTION_MEMBERS = BQTableDef(
    table_id="election_members",
    description="選挙結果メンバー",
    columns=(
        BQColumnDef("id", "INT64", "REQUIRED", "選挙結果メンバーID"),
        BQColumnDef("election_id", "INT64", "REQUIRED", "選挙ID"),
        BQColumnDef("politician_id", "INT64", "REQUIRED", "政治家ID"),
        BQColumnDef("result", "STRING", "REQUIRED", "選挙結果"),
        BQColumnDef("votes", "INT64", description="得票数"),
        BQColumnDef("rank", "INT64", description="順位"),
        BQColumnDef("created_at", "TIMESTAMP", description="作成日時"),
        BQColumnDef("updated_at", "TIMESTAMP", description="更新日時"),
    ),
)

_GOVERNING_BODIES = BQTableDef(
    table_id="governing_bodies",
    description="開催主体",
    columns=(
        BQColumnDef("id", "INT64", "REQUIRED", "開催主体ID"),
        BQColumnDef("name", "STRING", "REQUIRED", "名称"),
        BQColumnDef("organization_code", "STRING", description="総務省6桁自治体コード"),
        BQColumnDef("organization_type", "STRING", description="組織種別"),
        BQColumnDef("prefecture", "STRING", description="都道府県"),
        BQColumnDef("created_at", "TIMESTAMP", description="作成日時"),
        BQColumnDef("updated_at", "TIMESTAMP", description="更新日時"),
    ),
)

_CONFERENCES = BQTableDef(
    table_id="conferences",
    description="会議体",
    columns=(
        BQColumnDef("id", "INT64", "REQUIRED", "会議体ID"),
        BQColumnDef("name", "STRING", "REQUIRED", "会議体名"),
        BQColumnDef("governing_body_id", "INT64", description="開催主体ID"),
        BQColumnDef("term", "STRING", description="任期"),
        BQColumnDef("election_id", "INT64", description="選挙ID"),
        BQColumnDef("created_at", "TIMESTAMP", description="作成日時"),
        BQColumnDef("updated_at", "TIMESTAMP", description="更新日時"),
    ),
)

_CONFERENCE_MEMBERS = BQTableDef(
    table_id="conference_members",
    description="会議体メンバー（議員の議会所属）",
    columns=(
        BQColumnDef("id", "INT64", "REQUIRED", "所属ID"),
        BQColumnDef("politician_id", "INT64", "REQUIRED", "政治家ID"),
        BQColumnDef("conference_id", "INT64", "REQUIRED", "会議体ID"),
        BQColumnDef("start_date", "DATE", "REQUIRED", "開始日"),
        BQColumnDef("end_date", "DATE", description="終了日"),
        BQColumnDef("role", "STRING", description="役割"),
        BQColumnDef("is_manually_verified", "BOOL", description="手動検証済みフラグ"),
        BQColumnDef("created_at", "TIMESTAMP", description="作成日時"),
        BQColumnDef("updated_at", "TIMESTAMP", description="更新日時"),
    ),
)

_PARLIAMENTARY_GROUPS = BQTableDef(
    table_id="parliamentary_groups",
    description="議員団（会派）",
    columns=(
        BQColumnDef("id", "INT64", "REQUIRED", "議員団ID"),
        BQColumnDef("name", "STRING", "REQUIRED", "議員団名"),
        BQColumnDef("governing_body_id", "INT64", "REQUIRED", "開催主体ID"),
        BQColumnDef("political_party_id", "INT64", description="政党ID"),
        BQColumnDef("url", "STRING", description="URL"),
        BQColumnDef("description", "STRING", description="説明"),
        BQColumnDef("is_active", "BOOL", description="有効フラグ"),
        BQColumnDef("created_at", "TIMESTAMP", description="作成日時"),
        BQColumnDef("updated_at", "TIMESTAMP", description="更新日時"),
    ),
)

_PARLIAMENTARY_GROUP_MEMBERSHIPS = BQTableDef(
    table_id="parliamentary_group_memberships",
    description="議員団所属履歴",
    columns=(
        BQColumnDef("id", "INT64", "REQUIRED", "所属ID"),
        BQColumnDef("politician_id", "INT64", "REQUIRED", "政治家ID"),
        BQColumnDef("parliamentary_group_id", "INT64", "REQUIRED", "議員団ID"),
        BQColumnDef("start_date", "DATE", "REQUIRED", "開始日"),
        BQColumnDef("end_date", "DATE", description="終了日"),
        BQColumnDef("role", "STRING", description="役割"),
        BQColumnDef("is_manually_verified", "BOOL", description="手動検証済みフラグ"),
        BQColumnDef("created_at", "TIMESTAMP", description="作成日時"),
        BQColumnDef("updated_at", "TIMESTAMP", description="更新日時"),
    ),
)

_MEETINGS = BQTableDef(
    table_id="meetings",
    description="会議（開催インスタンス）",
    columns=(
        BQColumnDef("id", "INT64", "REQUIRED", "会議ID"),
        BQColumnDef("conference_id", "INT64", "REQUIRED", "会議体ID"),
        BQColumnDef("date", "DATE", description="開催日"),
        BQColumnDef("url", "STRING", description="URL"),
        BQColumnDef("name", "STRING", description="会議名"),
        BQColumnDef("created_at", "TIMESTAMP", description="作成日時"),
        BQColumnDef("updated_at", "TIMESTAMP", description="更新日時"),
    ),
)

_MINUTES = BQTableDef(
    table_id="minutes",
    description="議事録",
    columns=(
        BQColumnDef("id", "INT64", "REQUIRED", "議事録ID"),
        BQColumnDef("meeting_id", "INT64", "REQUIRED", "会議ID"),
        BQColumnDef("url", "STRING", description="URL"),
        BQColumnDef("processed_at", "TIMESTAMP", description="処理日時"),
        BQColumnDef("created_at", "TIMESTAMP", description="作成日時"),
        BQColumnDef("updated_at", "TIMESTAMP", description="更新日時"),
    ),
)

_CONVERSATIONS = BQTableDef(
    table_id="conversations",
    description="発言",
    columns=(
        BQColumnDef("id", "INT64", "REQUIRED", "発言ID"),
        BQColumnDef("minutes_id", "INT64", description="議事録ID"),
        BQColumnDef("speaker_id", "INT64", description="発言者ID"),
        BQColumnDef("speaker_name", "STRING", description="発言者名"),
        BQColumnDef("comment", "STRING", "REQUIRED", "発言内容"),
        BQColumnDef("sequence_number", "INT64", "REQUIRED", "発言順序"),
        BQColumnDef("chapter_number", "INT64", description="章番号"),
        BQColumnDef("sub_chapter_number", "INT64", description="節番号"),
        BQColumnDef("is_manually_verified", "BOOL", description="手動検証済みフラグ"),
        BQColumnDef("created_at", "TIMESTAMP", description="作成日時"),
        BQColumnDef("updated_at", "TIMESTAMP", description="更新日時"),
    ),
)

_SPEAKERS = BQTableDef(
    table_id="speakers",
    description="発言者",
    columns=(
        BQColumnDef("id", "INT64", "REQUIRED", "発言者ID"),
        BQColumnDef("name", "STRING", "REQUIRED", "氏名"),
        BQColumnDef("type", "STRING", description="種別"),
        BQColumnDef("political_party_name", "STRING", description="政党名"),
        BQColumnDef("position", "STRING", description="役職"),
        BQColumnDef("is_politician", "BOOL", description="政治家フラグ"),
        BQColumnDef("politician_id", "INT64", description="政治家ID"),
        BQColumnDef("matching_confidence", "NUMERIC", description="マッチング信頼度"),
        BQColumnDef("matching_reason", "STRING", description="マッチング理由"),
        BQColumnDef("is_manually_verified", "BOOL", description="手動検証済みフラグ"),
        BQColumnDef("name_yomi", "STRING", description="氏名よみ"),
        BQColumnDef("created_at", "TIMESTAMP", description="作成日時"),
        BQColumnDef("updated_at", "TIMESTAMP", description="更新日時"),
    ),
)

_PROPOSALS = BQTableDef(
    table_id="proposals",
    description="議案",
    columns=(
        BQColumnDef("id", "INT64", "REQUIRED", "議案ID"),
        BQColumnDef("title", "STRING", "REQUIRED", "議案名"),
        BQColumnDef("detail_url", "STRING", description="詳細URL"),
        BQColumnDef("status_url", "STRING", description="審議状況URL"),
        BQColumnDef("meeting_id", "INT64", description="会議ID"),
        BQColumnDef("votes_url", "STRING", description="投票結果URL"),
        BQColumnDef("conference_id", "INT64", description="会議体ID"),
        BQColumnDef("proposal_category", "STRING", description="議案大分類"),
        BQColumnDef("proposal_type", "STRING", description="議案小分類"),
        BQColumnDef("governing_body_id", "INT64", description="開催主体ID"),
        BQColumnDef("session_number", "INT64", description="回次"),
        BQColumnDef("proposal_number", "INT64", description="議案番号"),
        BQColumnDef("external_id", "STRING", description="外部データソースID"),
        BQColumnDef("deliberation_status", "STRING", description="審議状況"),
        BQColumnDef("deliberation_result", "STRING", description="最終結果"),
        BQColumnDef("submitted_date", "DATE", description="提出日"),
        BQColumnDef("voted_date", "DATE", description="採決日"),
        BQColumnDef("created_at", "TIMESTAMP", description="作成日時"),
        BQColumnDef("updated_at", "TIMESTAMP", description="更新日時"),
    ),
)

_PROPOSAL_SUBMITTERS = BQTableDef(
    table_id="proposal_submitters",
    description="議案提出者",
    columns=(
        BQColumnDef("id", "INT64", "REQUIRED", "提出者ID"),
        BQColumnDef("proposal_id", "INT64", "REQUIRED", "議案ID"),
        BQColumnDef("submitter_type", "STRING", "REQUIRED", "提出者種別"),
        BQColumnDef("politician_id", "INT64", description="政治家ID"),
        BQColumnDef("parliamentary_group_id", "INT64", description="議員団ID"),
        BQColumnDef("conference_id", "INT64", description="会議体ID"),
        BQColumnDef("raw_name", "STRING", description="元データの名前"),
        BQColumnDef("is_representative", "BOOL", description="代表者フラグ"),
        BQColumnDef("display_order", "INT64", description="表示順"),
        BQColumnDef("created_at", "TIMESTAMP", description="作成日時"),
        BQColumnDef("updated_at", "TIMESTAMP", description="更新日時"),
    ),
)

_PROPOSAL_DELIBERATIONS = BQTableDef(
    table_id="proposal_deliberations",
    description="議案審議",
    columns=(
        BQColumnDef("id", "INT64", "REQUIRED", "審議ID"),
        BQColumnDef("proposal_id", "INT64", "REQUIRED", "議案ID"),
        BQColumnDef("conference_id", "INT64", "REQUIRED", "会議体ID"),
        BQColumnDef("meeting_id", "INT64", description="会議ID"),
        BQColumnDef("stage", "STRING", description="審議段階"),
        BQColumnDef("created_at", "TIMESTAMP", description="作成日時"),
        BQColumnDef("updated_at", "TIMESTAMP", description="更新日時"),
    ),
)

_PROPOSAL_JUDGES = BQTableDef(
    table_id="proposal_judges",
    description="議案賛否（個人）",
    columns=(
        BQColumnDef("id", "INT64", "REQUIRED", "賛否ID"),
        BQColumnDef("proposal_id", "INT64", "REQUIRED", "議案ID"),
        BQColumnDef("politician_id", "INT64", "REQUIRED", "政治家ID"),
        BQColumnDef("approve", "STRING", description="賛否"),
        BQColumnDef("parliamentary_group_id", "INT64", description="議員団ID"),
        BQColumnDef("source_type", "STRING", description="データソース種別"),
        BQColumnDef("source_group_judge_id", "INT64", description="会派賛否展開元ID"),
        BQColumnDef("is_defection", "BOOL", description="造反フラグ"),
        BQColumnDef("created_at", "TIMESTAMP", description="作成日時"),
        BQColumnDef("updated_at", "TIMESTAMP", description="更新日時"),
    ),
)

_PROPOSAL_PARLIAMENTARY_GROUP_JUDGES = BQTableDef(
    table_id="proposal_parliamentary_group_judges",
    description="議案賛否（会派）",
    columns=(
        BQColumnDef("id", "INT64", "REQUIRED", "会派賛否ID"),
        BQColumnDef("proposal_id", "INT64", "REQUIRED", "議案ID"),
        BQColumnDef("judgment", "STRING", "REQUIRED", "賛否"),
        BQColumnDef("member_count", "INT64", description="メンバー数"),
        BQColumnDef("note", "STRING", description="備考"),
        BQColumnDef("judge_type", "STRING", description="賛否種別"),
        BQColumnDef("created_at", "TIMESTAMP", description="作成日時"),
        BQColumnDef("updated_at", "TIMESTAMP", description="更新日時"),
    ),
)

_PROPOSAL_JUDGE_PARLIAMENTARY_GROUPS = BQTableDef(
    table_id="proposal_judge_parliamentary_groups",
    description="賛否レコードと会派の中間テーブル",
    columns=(
        BQColumnDef("id", "INT64", "REQUIRED", "中間テーブルID"),
        BQColumnDef("judge_id", "INT64", "REQUIRED", "会派賛否ID"),
        BQColumnDef("parliamentary_group_id", "INT64", "REQUIRED", "議員団ID"),
        BQColumnDef("created_at", "TIMESTAMP", description="作成日時"),
    ),
)

_PROPOSAL_JUDGE_POLITICIANS = BQTableDef(
    table_id="proposal_judge_politicians",
    description="賛否レコードと政治家の中間テーブル",
    columns=(
        BQColumnDef("id", "INT64", "REQUIRED", "中間テーブルID"),
        BQColumnDef("judge_id", "INT64", "REQUIRED", "会派賛否ID"),
        BQColumnDef("politician_id", "INT64", "REQUIRED", "政治家ID"),
        BQColumnDef("created_at", "TIMESTAMP", description="作成日時"),
    ),
)

# 全20テーブルのリスト
GOLD_LAYER_TABLES: list[BQTableDef] = [
    _POLITICIANS,
    _POLITICAL_PARTIES,
    _ELECTIONS,
    _ELECTION_MEMBERS,
    _GOVERNING_BODIES,
    _CONFERENCES,
    _CONFERENCE_MEMBERS,
    _PARLIAMENTARY_GROUPS,
    _PARLIAMENTARY_GROUP_MEMBERSHIPS,
    _MEETINGS,
    _MINUTES,
    _CONVERSATIONS,
    _SPEAKERS,
    _PROPOSALS,
    _PROPOSAL_SUBMITTERS,
    _PROPOSAL_DELIBERATIONS,
    _PROPOSAL_JUDGES,
    _PROPOSAL_PARLIAMENTARY_GROUP_JUDGES,
    _PROPOSAL_JUDGE_PARLIAMENTARY_GROUPS,
    _PROPOSAL_JUDGE_POLITICIANS,
]
