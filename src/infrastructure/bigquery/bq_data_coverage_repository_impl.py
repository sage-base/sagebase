"""BQカバレッジ集計リポジトリ実装.

sagebase（Main Layer）データセットから、カバレッジページに必要な全指標を集計する。
国会と地方議会を分離し、都道府県別の内訳も提供する。
"""

import asyncio
import logging

from typing import Any

from src.domain.entities.bq_coverage_stats import (
    BQCoverageSummary,
    ConversationMeetingStats,
    DataPeriod,
    ParliamentaryGroupMappingStats,
    PartyGroupCounts,
    PoliticianStats,
    PrefectureCoverageStats,
    ProposalStats,
    SpeakerLinkageStats,
)
from src.domain.repositories.bq_data_coverage_repository import (
    IBQDataCoverageRepository,
)


try:
    from google.cloud import bigquery
    from google.cloud.exceptions import GoogleCloudError

    HAS_BIGQUERY = True
except ImportError:
    HAS_BIGQUERY = False
    bigquery = None  # type: ignore[assignment]
    GoogleCloudError = Exception  # type: ignore[assignment, misc]

from src.infrastructure.exceptions import StorageError


logger = logging.getLogger(__name__)

# 国会の組織種別
_NATIONAL_TYPE = "国"


class BQDataCoverageRepositoryImpl(IBQDataCoverageRepository):
    """BigQueryからカバレッジ指標を取得するリポジトリ実装."""

    def __init__(
        self,
        project_id: str,
        dataset_id: str = "sagebase",
    ) -> None:
        if not HAS_BIGQUERY:
            raise StorageError(
                "Google Cloud BigQuery library not installed. "
                "Install with: uv add google-cloud-bigquery"
            )
        self._project_id = project_id
        self._dataset_id = dataset_id
        self._client: Any = bigquery.Client(project=project_id) if bigquery else None

    @property
    def _dataset_ref(self) -> str:
        return f"{self._project_id}.{self._dataset_id}"

    def _table(self, name: str) -> str:
        return f"`{self._dataset_ref}.{name}`"

    def _run_query(self, sql: str) -> list[dict[str, Any]]:
        """BQクエリを同期実行し、結果をdictリストで返す."""
        try:
            query_job = self._client.query(sql)
            rows = query_job.result()
            return [dict(row) for row in rows]
        except GoogleCloudError as e:
            logger.error(f"BQクエリ実行エラー: {e}")
            raise StorageError(
                "BigQueryクエリの実行に失敗しました",
                {"error": str(e)},
            ) from e

    # ------------------------------------------------------------------
    # 発言数・会議数（国会 / 地方）
    # ------------------------------------------------------------------
    _CONVERSATION_MEETING_SQL = """
    SELECT
        CASE
            WHEN gb.organization_type = '{national_type}' THEN 'national'
            ELSE 'local'
        END AS scope,
        COUNT(DISTINCT conv.id) AS conversation_count,
        COUNT(DISTINCT m.id) AS meeting_count
    FROM {conversations} conv
    JOIN {minutes} mi ON conv.minutes_id = mi.id
    JOIN {meetings} m ON mi.meeting_id = m.id
    JOIN {conferences} c ON m.conference_id = c.id
    JOIN {governing_bodies} gb ON c.governing_body_id = gb.id
    GROUP BY scope
    """

    def _query_conversation_meeting_stats(
        self,
    ) -> tuple[ConversationMeetingStats, ConversationMeetingStats]:
        """発言数・会議数を国会/地方で集計."""
        sql = self._CONVERSATION_MEETING_SQL.format(
            national_type=_NATIONAL_TYPE,
            conversations=self._table("conversations"),
            minutes=self._table("minutes"),
            meetings=self._table("meetings"),
            conferences=self._table("conferences"),
            governing_bodies=self._table("governing_bodies"),
        )
        rows = self._run_query(sql)

        national: ConversationMeetingStats = {
            "conversation_count": 0,
            "meeting_count": 0,
        }
        local: ConversationMeetingStats = {
            "conversation_count": 0,
            "meeting_count": 0,
        }
        for row in rows:
            stats: ConversationMeetingStats = {
                "conversation_count": row["conversation_count"],
                "meeting_count": row["meeting_count"],
            }
            if row["scope"] == "national":
                national = stats
            else:
                local = stats
        return national, local

    # ------------------------------------------------------------------
    # 政治家数（国会議員 / 地方議員）
    # ------------------------------------------------------------------
    _POLITICIAN_SQL = """
    SELECT
        COUNT(DISTINCT CASE
            WHEN gb.organization_type = '{national_type}' THEN cm.politician_id
        END) AS national_count,
        COUNT(DISTINCT CASE
            WHEN gb.organization_type != '{national_type}' THEN cm.politician_id
        END) AS local_count
    FROM {conference_members} cm
    JOIN {conferences} c ON cm.conference_id = c.id
    JOIN {governing_bodies} gb ON c.governing_body_id = gb.id
    """

    def _query_politician_stats(self) -> PoliticianStats:
        """政治家数を国会/地方で集計."""
        sql = self._POLITICIAN_SQL.format(
            national_type=_NATIONAL_TYPE,
            conference_members=self._table("conference_members"),
            conferences=self._table("conferences"),
            governing_bodies=self._table("governing_bodies"),
        )
        rows = self._run_query(sql)
        if not rows:
            return {"national_politician_count": 0, "local_politician_count": 0}
        row = rows[0]
        return {
            "national_politician_count": row["national_count"],
            "local_politician_count": row["local_count"],
        }

    # ------------------------------------------------------------------
    # 議案数（国会）
    # ------------------------------------------------------------------
    _PROPOSAL_SQL = """
    SELECT COUNT(*) AS cnt
    FROM {proposals} p
    JOIN {governing_bodies} gb ON p.governing_body_id = gb.id
    WHERE gb.organization_type = '{national_type}'
    """

    def _query_proposal_stats(self) -> ProposalStats:
        """国会議案数を集計."""
        sql = self._PROPOSAL_SQL.format(
            national_type=_NATIONAL_TYPE,
            proposals=self._table("proposals"),
            governing_bodies=self._table("governing_bodies"),
        )
        rows = self._run_query(sql)
        cnt = rows[0]["cnt"] if rows else 0
        return {"national_proposal_count": cnt}

    # ------------------------------------------------------------------
    # データ収録期間（国会 / 地方）
    # ------------------------------------------------------------------
    _DATA_PERIOD_SQL = """
    SELECT
        CASE
            WHEN gb.organization_type = '{national_type}' THEN 'national'
            ELSE 'local'
        END AS scope,
        MIN(m.date) AS earliest_date,
        MAX(m.date) AS latest_date
    FROM {meetings} m
    JOIN {conferences} c ON m.conference_id = c.id
    JOIN {governing_bodies} gb ON c.governing_body_id = gb.id
    WHERE m.date IS NOT NULL
    GROUP BY scope
    """

    def _query_data_periods(self) -> tuple[DataPeriod, DataPeriod]:
        """データ収録期間を国会/地方で取得."""
        sql = self._DATA_PERIOD_SQL.format(
            national_type=_NATIONAL_TYPE,
            meetings=self._table("meetings"),
            conferences=self._table("conferences"),
            governing_bodies=self._table("governing_bodies"),
        )
        rows = self._run_query(sql)

        national: DataPeriod = {"earliest_date": None, "latest_date": None}
        local: DataPeriod = {"earliest_date": None, "latest_date": None}

        for row in rows:
            period: DataPeriod = {
                "earliest_date": (
                    str(row["earliest_date"]) if row["earliest_date"] else None
                ),
                "latest_date": (
                    str(row["latest_date"]) if row["latest_date"] else None
                ),
            }
            if row["scope"] == "national":
                national = period
            else:
                local = period
        return national, local

    # ------------------------------------------------------------------
    # 発言者→政治家紐付け
    # ------------------------------------------------------------------
    _SPEAKER_LINKAGE_SQL = """
    SELECT
        COUNT(*) AS total_speakers,
        COUNTIF(s.politician_id IS NOT NULL) AS matched_speakers,
        COUNTIF(s.government_official_id IS NOT NULL) AS government_official_count
    FROM {speakers} s
    """

    def _query_speaker_linkage(self) -> SpeakerLinkageStats:
        """発言者紐付け統計を取得."""
        sql = self._SPEAKER_LINKAGE_SQL.format(
            speakers=self._table("speakers"),
        )
        rows = self._run_query(sql)
        if not rows:
            return {
                "total_speakers": 0,
                "matched_speakers": 0,
                "government_official_count": 0,
                "linkage_rate": 0.0,
            }
        row = rows[0]
        total = row["total_speakers"]
        matched = row["matched_speakers"]
        rate = round(matched / total * 100, 2) if total > 0 else 0.0
        return {
            "total_speakers": total,
            "matched_speakers": matched,
            "government_official_count": row["government_official_count"],
            "linkage_rate": rate,
        }

    # ------------------------------------------------------------------
    # 会派マッピング率
    # ------------------------------------------------------------------
    _PG_MAPPING_SQL = """
    SELECT
        COUNT(DISTINCT pg.id) AS total_groups,
        COUNT(DISTINCT pgp.parliamentary_group_id) AS mapped_groups
    FROM {parliamentary_groups} pg
    LEFT JOIN {parliamentary_group_parties} pgp
        ON pg.id = pgp.parliamentary_group_id
    """

    def _query_parliamentary_group_mapping(self) -> ParliamentaryGroupMappingStats:
        """会派マッピング率を取得."""
        sql = self._PG_MAPPING_SQL.format(
            parliamentary_groups=self._table("parliamentary_groups"),
            parliamentary_group_parties=self._table("parliamentary_group_parties"),
        )
        rows = self._run_query(sql)
        if not rows:
            return {
                "total_parliamentary_groups": 0,
                "mapped_parliamentary_groups": 0,
                "mapping_rate": 0.0,
            }
        row = rows[0]
        total = row["total_groups"]
        mapped = row["mapped_groups"]
        rate = round(mapped / total * 100, 2) if total > 0 else 0.0
        return {
            "total_parliamentary_groups": total,
            "mapped_parliamentary_groups": mapped,
            "mapping_rate": rate,
        }

    # ------------------------------------------------------------------
    # 政党・会派登録数
    # ------------------------------------------------------------------
    _PARTY_GROUP_COUNTS_SQL = """
    SELECT
        (SELECT COUNT(*) FROM {political_parties}) AS party_count,
        (SELECT COUNT(*) FROM {parliamentary_groups}) AS group_count
    """

    def _query_party_group_counts(self) -> PartyGroupCounts:
        """政党・会派の登録数を取得."""
        sql = self._PARTY_GROUP_COUNTS_SQL.format(
            political_parties=self._table("political_parties"),
            parliamentary_groups=self._table("parliamentary_groups"),
        )
        rows = self._run_query(sql)
        if not rows:
            return {"political_party_count": 0, "parliamentary_group_count": 0}
        row = rows[0]
        return {
            "political_party_count": row["party_count"],
            "parliamentary_group_count": row["group_count"],
        }

    # ------------------------------------------------------------------
    # 都道府県別カバレッジ
    # ------------------------------------------------------------------
    _PREFECTURE_SQL = """
    WITH pref_conversations AS (
        SELECT
            gb.prefecture,
            COUNT(DISTINCT conv.id) AS conversation_count,
            COUNT(DISTINCT m.id) AS meeting_count,
            MIN(m.date) AS earliest_date,
            MAX(m.date) AS latest_date
        FROM {governing_bodies} gb
        JOIN {conferences} c ON gb.id = c.governing_body_id
        JOIN {meetings} m ON c.id = m.conference_id
        JOIN {minutes} mi ON m.id = mi.meeting_id
        JOIN {conversations} conv ON mi.id = conv.minutes_id
        WHERE gb.organization_type != '{national_type}'
          AND gb.prefecture IS NOT NULL
        GROUP BY gb.prefecture
    ),
    pref_gb AS (
        SELECT
            gb.prefecture,
            COUNT(DISTINCT gb.id) AS governing_body_count
        FROM {governing_bodies} gb
        WHERE gb.organization_type != '{national_type}'
          AND gb.prefecture IS NOT NULL
        GROUP BY gb.prefecture
    ),
    pref_politicians AS (
        SELECT
            gb.prefecture,
            COUNT(DISTINCT cm.politician_id) AS politician_count
        FROM {conference_members} cm
        JOIN {conferences} c ON cm.conference_id = c.id
        JOIN {governing_bodies} gb ON c.governing_body_id = gb.id
        WHERE gb.organization_type != '{national_type}'
          AND gb.prefecture IS NOT NULL
        GROUP BY gb.prefecture
    ),
    pref_speakers AS (
        SELECT
            gb.prefecture,
            COUNT(DISTINCT s.id) AS speaker_count,
            COUNTIF(s.politician_id IS NOT NULL) AS matched_speaker_count
        FROM {speakers} s
        JOIN {conversations} conv ON s.id = conv.speaker_id
        JOIN {minutes} mi ON conv.minutes_id = mi.id
        JOIN {meetings} m ON mi.meeting_id = m.id
        JOIN {conferences} c ON m.conference_id = c.id
        JOIN {governing_bodies} gb ON c.governing_body_id = gb.id
        WHERE gb.organization_type != '{national_type}'
          AND gb.prefecture IS NOT NULL
        GROUP BY gb.prefecture
    ),
    pref_proposals AS (
        SELECT
            gb.prefecture,
            COUNT(DISTINCT p.id) AS proposal_count
        FROM {proposals} p
        JOIN {governing_bodies} gb ON p.governing_body_id = gb.id
        WHERE gb.organization_type != '{national_type}'
          AND gb.prefecture IS NOT NULL
        GROUP BY gb.prefecture
    )
    SELECT
        g.prefecture,
        g.governing_body_count,
        COALESCE(pc.conversation_count, 0) AS conversation_count,
        COALESCE(pc.meeting_count, 0) AS meeting_count,
        COALESCE(pp.politician_count, 0) AS politician_count,
        COALESCE(ps.speaker_count, 0) AS speaker_count,
        COALESCE(ps.matched_speaker_count, 0) AS matched_speaker_count,
        COALESCE(pr.proposal_count, 0) AS proposal_count,
        pc.earliest_date,
        pc.latest_date
    FROM pref_gb g
    LEFT JOIN pref_conversations pc ON g.prefecture = pc.prefecture
    LEFT JOIN pref_politicians pp ON g.prefecture = pp.prefecture
    LEFT JOIN pref_speakers ps ON g.prefecture = ps.prefecture
    LEFT JOIN pref_proposals pr ON g.prefecture = pr.prefecture
    ORDER BY g.prefecture
    """

    def _query_prefecture_stats(self) -> list[PrefectureCoverageStats]:
        """都道府県別カバレッジを集計."""
        sql = self._PREFECTURE_SQL.format(
            national_type=_NATIONAL_TYPE,
            governing_bodies=self._table("governing_bodies"),
            conferences=self._table("conferences"),
            meetings=self._table("meetings"),
            minutes=self._table("minutes"),
            conversations=self._table("conversations"),
            conference_members=self._table("conference_members"),
            speakers=self._table("speakers"),
            proposals=self._table("proposals"),
        )
        rows = self._run_query(sql)
        result: list[PrefectureCoverageStats] = []
        for row in rows:
            speaker_count = row["speaker_count"]
            matched = row["matched_speaker_count"]
            linkage_rate = (
                round(matched / speaker_count * 100, 2) if speaker_count > 0 else 0.0
            )
            result.append(
                {
                    "prefecture": row["prefecture"],
                    "governing_body_count": row["governing_body_count"],
                    "conversation_count": row["conversation_count"],
                    "meeting_count": row["meeting_count"],
                    "politician_count": row["politician_count"],
                    "speaker_count": speaker_count,
                    "matched_speaker_count": matched,
                    "linkage_rate": linkage_rate,
                    "proposal_count": row["proposal_count"],
                    "earliest_date": (
                        str(row["earliest_date"]) if row["earliest_date"] else None
                    ),
                    "latest_date": (
                        str(row["latest_date"]) if row["latest_date"] else None
                    ),
                }
            )
        return result

    # ------------------------------------------------------------------
    # 公開API
    # ------------------------------------------------------------------
    async def get_coverage_summary(self) -> BQCoverageSummary:
        """カバレッジページに必要な全指標を取得する.

        各クエリを並列実行し、結果を統合して返す。
        """
        loop = asyncio.get_event_loop()

        # BQクエリを並列実行（同期関数をスレッドプールで実行）
        cm_future = loop.run_in_executor(None, self._query_conversation_meeting_stats)
        politician_future = loop.run_in_executor(None, self._query_politician_stats)
        proposal_future = loop.run_in_executor(None, self._query_proposal_stats)
        period_future = loop.run_in_executor(None, self._query_data_periods)
        speaker_future = loop.run_in_executor(None, self._query_speaker_linkage)
        pg_future = loop.run_in_executor(None, self._query_parliamentary_group_mapping)
        party_future = loop.run_in_executor(None, self._query_party_group_counts)
        pref_future = loop.run_in_executor(None, self._query_prefecture_stats)

        national_cm, local_cm = await cm_future
        politician_stats = await politician_future
        proposal_stats = await proposal_future
        national_period, local_period = await period_future
        speaker_linkage = await speaker_future
        pg_mapping = await pg_future
        party_group_counts = await party_future
        prefecture_stats = await pref_future

        return {
            "national": national_cm,
            "local_total": local_cm,
            "politician_stats": politician_stats,
            "proposal_stats": proposal_stats,
            "speaker_linkage": speaker_linkage,
            "parliamentary_group_mapping": pg_mapping,
            "party_group_counts": party_group_counts,
            "national_period": national_period,
            "local_period": local_period,
            "prefecture_stats": prefecture_stats,
        }

    async def get_prefecture_stats(self) -> list[PrefectureCoverageStats]:
        """都道府県別のカバレッジ統計を取得する."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._query_prefecture_stats)
