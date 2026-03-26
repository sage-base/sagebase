"""BQカバレッジ集計リポジトリ実装のテスト."""

from datetime import date
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.domain.entities.bq_coverage_stats import (
    BQCoverageSummary,
    PrefectureCoverageStats,
)
from src.infrastructure.exceptions import StorageError


MODULE_PATH = "src.infrastructure.bigquery.bq_data_coverage_repository_impl"


@pytest.fixture
def mock_bq_client() -> MagicMock:
    return MagicMock()


def _make_repo(mock_bigquery: MagicMock) -> Any:
    """テスト用リポジトリインスタンスを作成."""
    from src.infrastructure.bigquery.bq_data_coverage_repository_impl import (
        BQDataCoverageRepositoryImpl,
    )

    return BQDataCoverageRepositoryImpl(
        project_id="test-project",
        dataset_id="test_dataset",
    )


class TestInit:
    """初期化テスト."""

    @patch(f"{MODULE_PATH}.bigquery")
    def test_init_success(self, mock_bigquery: MagicMock) -> None:
        repo = _make_repo(mock_bigquery)
        assert repo._project_id == "test-project"
        assert repo._dataset_id == "test_dataset"
        mock_bigquery.Client.assert_called_once_with(project="test-project")

    @patch(f"{MODULE_PATH}.HAS_BIGQUERY", False)
    def test_init_raises_when_library_not_installed(self) -> None:
        from src.infrastructure.bigquery.bq_data_coverage_repository_impl import (
            BQDataCoverageRepositoryImpl,
        )

        with pytest.raises(StorageError, match="not installed"):
            BQDataCoverageRepositoryImpl(project_id="test-project")


class TestRunQuery:
    """_run_query テスト."""

    @patch(f"{MODULE_PATH}.bigquery")
    def test_run_query_returns_dict_list(self, mock_bigquery: MagicMock) -> None:
        repo = _make_repo(mock_bigquery)

        mock_row = {"scope": "national", "count": 42}
        mock_job = MagicMock()
        mock_job.result.return_value = [mock_row]
        repo._client.query.return_value = mock_job

        result = repo._run_query("SELECT 1")  # type: ignore[reportPrivateUsage]
        assert result == [mock_row]

    @patch(f"{MODULE_PATH}.bigquery")
    def test_run_query_raises_storage_error_on_bq_error(
        self, mock_bigquery: MagicMock
    ) -> None:
        from google.cloud.exceptions import GoogleCloudError

        repo = _make_repo(mock_bigquery)
        repo._client.query.side_effect = GoogleCloudError("BQ error")

        with pytest.raises(StorageError, match="BigQueryクエリの実行に失敗"):
            repo._run_query("SELECT 1")  # type: ignore[reportPrivateUsage]


class TestConversationMeetingStats:
    """発言数・会議数の集計テスト."""

    @patch(f"{MODULE_PATH}.bigquery")
    def test_returns_national_and_local_stats(self, mock_bigquery: MagicMock) -> None:
        repo = _make_repo(mock_bigquery)

        mock_job = MagicMock()
        mock_job.result.return_value = [
            {
                "scope": "national",
                "conversation_count": 100,
                "meeting_count": 10,
            },
            {
                "scope": "local",
                "conversation_count": 500,
                "meeting_count": 50,
            },
        ]
        repo._client.query.return_value = mock_job

        national, local = repo._query_conversation_meeting_stats()  # type: ignore[reportPrivateUsage]

        assert national["conversation_count"] == 100
        assert national["meeting_count"] == 10
        assert local["conversation_count"] == 500
        assert local["meeting_count"] == 50

    @patch(f"{MODULE_PATH}.bigquery")
    def test_returns_zeros_when_empty(self, mock_bigquery: MagicMock) -> None:
        repo = _make_repo(mock_bigquery)

        mock_job = MagicMock()
        mock_job.result.return_value = []
        repo._client.query.return_value = mock_job

        national, local = repo._query_conversation_meeting_stats()  # type: ignore[reportPrivateUsage]

        assert national["conversation_count"] == 0
        assert local["conversation_count"] == 0


class TestPoliticianStats:
    """政治家数の集計テスト."""

    @patch(f"{MODULE_PATH}.bigquery")
    def test_returns_national_and_local_counts(self, mock_bigquery: MagicMock) -> None:
        repo = _make_repo(mock_bigquery)

        mock_job = MagicMock()
        mock_job.result.return_value = [
            {"national_count": 700, "local_count": 3000},
        ]
        repo._client.query.return_value = mock_job

        result = repo._query_politician_stats()  # type: ignore[reportPrivateUsage]

        assert result["national_politician_count"] == 700
        assert result["local_politician_count"] == 3000

    @patch(f"{MODULE_PATH}.bigquery")
    def test_returns_zeros_when_empty(self, mock_bigquery: MagicMock) -> None:
        repo = _make_repo(mock_bigquery)

        mock_job = MagicMock()
        mock_job.result.return_value = []
        repo._client.query.return_value = mock_job

        result = repo._query_politician_stats()  # type: ignore[reportPrivateUsage]

        assert result["national_politician_count"] == 0
        assert result["local_politician_count"] == 0


class TestProposalStats:
    """議案数の集計テスト."""

    @patch(f"{MODULE_PATH}.bigquery")
    def test_returns_proposal_count(self, mock_bigquery: MagicMock) -> None:
        repo = _make_repo(mock_bigquery)

        mock_job = MagicMock()
        mock_job.result.return_value = [{"cnt": 1500}]
        repo._client.query.return_value = mock_job

        result = repo._query_proposal_stats()  # type: ignore[reportPrivateUsage]
        assert result["national_proposal_count"] == 1500

    @patch(f"{MODULE_PATH}.bigquery")
    def test_returns_zero_when_empty(self, mock_bigquery: MagicMock) -> None:
        repo = _make_repo(mock_bigquery)

        mock_job = MagicMock()
        mock_job.result.return_value = []
        repo._client.query.return_value = mock_job

        result = repo._query_proposal_stats()  # type: ignore[reportPrivateUsage]
        assert result["national_proposal_count"] == 0


class TestDataPeriods:
    """データ収録期間の集計テスト."""

    @patch(f"{MODULE_PATH}.bigquery")
    def test_returns_national_and_local_periods(self, mock_bigquery: MagicMock) -> None:
        repo = _make_repo(mock_bigquery)

        mock_job = MagicMock()
        mock_job.result.return_value = [
            {
                "scope": "national",
                "earliest_date": date(2000, 1, 1),
                "latest_date": date(2025, 12, 31),
            },
            {
                "scope": "local",
                "earliest_date": date(2010, 4, 1),
                "latest_date": date(2025, 6, 30),
            },
        ]
        repo._client.query.return_value = mock_job

        national, local = repo._query_data_periods()  # type: ignore[reportPrivateUsage]

        assert national["earliest_date"] == "2000-01-01"
        assert national["latest_date"] == "2025-12-31"
        assert local["earliest_date"] == "2010-04-01"
        assert local["latest_date"] == "2025-06-30"

    @patch(f"{MODULE_PATH}.bigquery")
    def test_returns_none_when_no_data(self, mock_bigquery: MagicMock) -> None:
        repo = _make_repo(mock_bigquery)

        mock_job = MagicMock()
        mock_job.result.return_value = []
        repo._client.query.return_value = mock_job

        national, local = repo._query_data_periods()  # type: ignore[reportPrivateUsage]

        assert national["earliest_date"] is None
        assert local["earliest_date"] is None


class TestSpeakerLinkage:
    """発言者紐付け統計テスト."""

    @patch(f"{MODULE_PATH}.bigquery")
    def test_returns_linkage_stats(self, mock_bigquery: MagicMock) -> None:
        repo = _make_repo(mock_bigquery)

        mock_job = MagicMock()
        mock_job.result.return_value = [
            {
                "total_speakers": 1000,
                "matched_speakers": 800,
                "government_official_count": 50,
            },
        ]
        repo._client.query.return_value = mock_job

        result = repo._query_speaker_linkage()  # type: ignore[reportPrivateUsage]

        assert result["total_speakers"] == 1000
        assert result["matched_speakers"] == 800
        assert result["government_official_count"] == 50
        assert result["linkage_rate"] == 80.0

    @patch(f"{MODULE_PATH}.bigquery")
    def test_returns_zeros_when_empty(self, mock_bigquery: MagicMock) -> None:
        repo = _make_repo(mock_bigquery)

        mock_job = MagicMock()
        mock_job.result.return_value = []
        repo._client.query.return_value = mock_job

        result = repo._query_speaker_linkage()  # type: ignore[reportPrivateUsage]

        assert result["total_speakers"] == 0
        assert result["linkage_rate"] == 0.0

    @patch(f"{MODULE_PATH}.bigquery")
    def test_linkage_rate_zero_when_no_speakers(self, mock_bigquery: MagicMock) -> None:
        repo = _make_repo(mock_bigquery)

        mock_job = MagicMock()
        mock_job.result.return_value = [
            {
                "total_speakers": 0,
                "matched_speakers": 0,
                "government_official_count": 0,
            },
        ]
        repo._client.query.return_value = mock_job

        result = repo._query_speaker_linkage()  # type: ignore[reportPrivateUsage]
        assert result["linkage_rate"] == 0.0


class TestParliamentaryGroupMapping:
    """会派マッピング率テスト."""

    @patch(f"{MODULE_PATH}.bigquery")
    def test_returns_mapping_stats(self, mock_bigquery: MagicMock) -> None:
        repo = _make_repo(mock_bigquery)

        mock_job = MagicMock()
        mock_job.result.return_value = [
            {"total_groups": 200, "mapped_groups": 180},
        ]
        repo._client.query.return_value = mock_job

        result = repo._query_parliamentary_group_mapping()  # type: ignore[reportPrivateUsage]

        assert result["total_parliamentary_groups"] == 200
        assert result["mapped_parliamentary_groups"] == 180
        assert result["mapping_rate"] == 90.0

    @patch(f"{MODULE_PATH}.bigquery")
    def test_returns_zeros_when_empty(self, mock_bigquery: MagicMock) -> None:
        repo = _make_repo(mock_bigquery)

        mock_job = MagicMock()
        mock_job.result.return_value = []
        repo._client.query.return_value = mock_job

        result = repo._query_parliamentary_group_mapping()  # type: ignore[reportPrivateUsage]

        assert result["total_parliamentary_groups"] == 0
        assert result["mapping_rate"] == 0.0


class TestPartyGroupCounts:
    """政党・会派登録数テスト."""

    @patch(f"{MODULE_PATH}.bigquery")
    def test_returns_counts(self, mock_bigquery: MagicMock) -> None:
        repo = _make_repo(mock_bigquery)

        mock_job = MagicMock()
        mock_job.result.return_value = [
            {"party_count": 12, "group_count": 200},
        ]
        repo._client.query.return_value = mock_job

        result = repo._query_party_group_counts()  # type: ignore[reportPrivateUsage]

        assert result["political_party_count"] == 12
        assert result["parliamentary_group_count"] == 200

    @patch(f"{MODULE_PATH}.bigquery")
    def test_returns_zeros_when_empty(self, mock_bigquery: MagicMock) -> None:
        repo = _make_repo(mock_bigquery)

        mock_job = MagicMock()
        mock_job.result.return_value = []
        repo._client.query.return_value = mock_job

        result = repo._query_party_group_counts()  # type: ignore[reportPrivateUsage]

        assert result["political_party_count"] == 0
        assert result["parliamentary_group_count"] == 0


class TestPrefectureStats:
    """都道府県別カバレッジテスト."""

    @patch(f"{MODULE_PATH}.bigquery")
    def test_returns_prefecture_breakdown(self, mock_bigquery: MagicMock) -> None:
        repo = _make_repo(mock_bigquery)

        mock_job = MagicMock()
        mock_job.result.return_value = [
            {
                "prefecture": "東京都",
                "governing_body_count": 62,
                "conversation_count": 5000,
                "meeting_count": 200,
                "politician_count": 300,
                "speaker_count": 400,
                "matched_speaker_count": 350,
                "proposal_count": 100,
                "earliest_date": date(2015, 1, 1),
                "latest_date": date(2025, 3, 1),
            },
            {
                "prefecture": "大阪府",
                "governing_body_count": 43,
                "conversation_count": 3000,
                "meeting_count": 150,
                "politician_count": 200,
                "speaker_count": 250,
                "matched_speaker_count": 200,
                "proposal_count": 50,
                "earliest_date": date(2018, 4, 1),
                "latest_date": date(2025, 1, 15),
            },
        ]
        repo._client.query.return_value = mock_job

        result = repo._query_prefecture_stats()  # type: ignore[reportPrivateUsage]

        assert len(result) == 2
        tokyo = result[0]
        assert tokyo["prefecture"] == "東京都"
        assert tokyo["conversation_count"] == 5000
        assert tokyo["linkage_rate"] == 87.5  # 350/400*100
        assert tokyo["earliest_date"] == "2015-01-01"

        osaka = result[1]
        assert osaka["prefecture"] == "大阪府"
        assert osaka["linkage_rate"] == 80.0  # 200/250*100

    @patch(f"{MODULE_PATH}.bigquery")
    def test_returns_empty_list_when_no_data(self, mock_bigquery: MagicMock) -> None:
        repo = _make_repo(mock_bigquery)

        mock_job = MagicMock()
        mock_job.result.return_value = []
        repo._client.query.return_value = mock_job

        result = repo._query_prefecture_stats()  # type: ignore[reportPrivateUsage]
        assert result == []

    @patch(f"{MODULE_PATH}.bigquery")
    def test_linkage_rate_zero_when_no_speakers(self, mock_bigquery: MagicMock) -> None:
        repo = _make_repo(mock_bigquery)

        mock_job = MagicMock()
        mock_job.result.return_value = [
            {
                "prefecture": "北海道",
                "governing_body_count": 180,
                "conversation_count": 0,
                "meeting_count": 0,
                "politician_count": 0,
                "speaker_count": 0,
                "matched_speaker_count": 0,
                "proposal_count": 0,
                "earliest_date": None,
                "latest_date": None,
            },
        ]
        repo._client.query.return_value = mock_job

        result = repo._query_prefecture_stats()  # type: ignore[reportPrivateUsage]

        assert len(result) == 1
        assert result[0]["linkage_rate"] == 0.0
        assert result[0]["earliest_date"] is None


class TestGetCoverageSummary:
    """get_coverage_summary 統合テスト."""

    @patch(f"{MODULE_PATH}.bigquery")
    @pytest.mark.asyncio
    async def test_returns_full_summary(self, mock_bigquery: MagicMock) -> None:
        repo = _make_repo(mock_bigquery)

        # SQLの内容に基づいてレスポンスを返す（並列実行で順序不定のため）
        sql_response_map = {
            "AS scope": [  # conversations + meetings のscope集計
                {"scope": "national", "conversation_count": 100, "meeting_count": 10},
                {"scope": "local", "conversation_count": 500, "meeting_count": 50},
            ],
            "national_count": [  # politician stats
                {"national_count": 700, "local_count": 3000},
            ],
            "AS cnt": [  # proposal count
                {"cnt": 1500},
            ],
            "earliest_date": [  # data periods
                {
                    "scope": "national",
                    "earliest_date": date(2000, 1, 1),
                    "latest_date": date(2025, 12, 31),
                },
                {
                    "scope": "local",
                    "earliest_date": date(2010, 4, 1),
                    "latest_date": date(2025, 6, 30),
                },
            ],
            "government_official_count": [  # speaker linkage
                {
                    "total_speakers": 1000,
                    "matched_speakers": 800,
                    "government_official_count": 50,
                },
            ],
            "mapped_groups": [  # parliamentary group mapping
                {"total_groups": 200, "mapped_groups": 180},
            ],
            "party_count": [  # party/group counts
                {"party_count": 12, "group_count": 200},
            ],
            "pref_gb": [  # prefecture stats（CTEにpref_gbを含む）
                {
                    "prefecture": "東京都",
                    "governing_body_count": 62,
                    "conversation_count": 5000,
                    "meeting_count": 200,
                    "politician_count": 300,
                    "speaker_count": 400,
                    "matched_speaker_count": 350,
                    "proposal_count": 100,
                    "earliest_date": date(2015, 1, 1),
                    "latest_date": date(2025, 3, 1),
                },
            ],
        }

        def query_side_effect(sql: str) -> MagicMock:
            mock_job = MagicMock()
            # SQLの内容に基づいて適切なレスポンスを返す
            # pref_gbを含むクエリは都道府県別なので先にチェック
            if "pref_gb" in sql:
                mock_job.result.return_value = sql_response_map["pref_gb"]
            elif "government_official_count" in sql:
                mock_job.result.return_value = sql_response_map[
                    "government_official_count"
                ]
            elif "mapped_groups" in sql:
                mock_job.result.return_value = sql_response_map["mapped_groups"]
            elif "party_count" in sql:
                mock_job.result.return_value = sql_response_map["party_count"]
            elif "national_count" in sql:
                mock_job.result.return_value = sql_response_map["national_count"]
            elif "AS cnt" in sql:
                mock_job.result.return_value = sql_response_map["AS cnt"]
            elif "earliest_date" in sql:
                mock_job.result.return_value = sql_response_map["earliest_date"]
            elif "AS scope" in sql:
                mock_job.result.return_value = sql_response_map["AS scope"]
            else:
                mock_job.result.return_value = []
            return mock_job

        repo._client.query.side_effect = query_side_effect

        summary: BQCoverageSummary = await repo.get_coverage_summary()

        # 国会
        assert summary["national"]["conversation_count"] == 100
        assert summary["national"]["meeting_count"] == 10
        # 地方
        assert summary["local_total"]["conversation_count"] == 500
        # 政治家
        assert summary["politician_stats"]["national_politician_count"] == 700
        assert summary["politician_stats"]["local_politician_count"] == 3000
        # 議案
        assert summary["proposal_stats"]["national_proposal_count"] == 1500
        # 発言者紐付け
        assert summary["speaker_linkage"]["linkage_rate"] == 80.0
        # 会派マッピング
        assert summary["parliamentary_group_mapping"]["mapping_rate"] == 90.0
        # 政党・会派
        assert summary["party_group_counts"]["political_party_count"] == 12
        # 収録期間
        assert summary["national_period"]["earliest_date"] == "2000-01-01"
        assert summary["local_period"]["earliest_date"] == "2010-04-01"
        # 都道府県
        assert len(summary["prefecture_stats"]) == 1
        assert summary["prefecture_stats"][0]["prefecture"] == "東京都"


class TestGetPrefectureStats:
    """get_prefecture_stats テスト."""

    @patch(f"{MODULE_PATH}.bigquery")
    @pytest.mark.asyncio
    async def test_returns_prefecture_list(self, mock_bigquery: MagicMock) -> None:
        repo = _make_repo(mock_bigquery)

        mock_job = MagicMock()
        mock_job.result.return_value = [
            {
                "prefecture": "東京都",
                "governing_body_count": 62,
                "conversation_count": 5000,
                "meeting_count": 200,
                "politician_count": 300,
                "speaker_count": 400,
                "matched_speaker_count": 350,
                "proposal_count": 100,
                "earliest_date": date(2015, 1, 1),
                "latest_date": date(2025, 3, 1),
            },
        ]
        repo._client.query.return_value = mock_job

        result: list[PrefectureCoverageStats] = await repo.get_prefecture_stats()

        assert len(result) == 1
        assert result[0]["prefecture"] == "東京都"


class TestTableReference:
    """テーブル参照の生成テスト."""

    @patch(f"{MODULE_PATH}.bigquery")
    def test_table_ref_format(self, mock_bigquery: MagicMock) -> None:
        repo = _make_repo(mock_bigquery)
        ref = repo._table("conversations")
        assert ref == "`test-project.test_dataset.conversations`"

    @patch(f"{MODULE_PATH}.bigquery")
    def test_dataset_ref_format(self, mock_bigquery: MagicMock) -> None:
        repo = _make_repo(mock_bigquery)
        assert repo._dataset_ref == "test-project.test_dataset"
