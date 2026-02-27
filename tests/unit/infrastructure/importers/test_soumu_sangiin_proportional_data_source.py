"""総務省参議院比例代表データソースのテスト."""

from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from src.domain.value_objects.proportional_candidate import (
    ProportionalCandidateRecord,
    ProportionalElectionInfo,
)
from src.infrastructure.importers.soumu_sangiin_proportional_data_source import (
    SoumuSangiinProportionalDataSource,
)
from src.infrastructure.importers.soumu_sangiin_proportional_scraper import (
    SangiinProportionalXlsInfo,
)


class TestSoumuSangiinProportionalDataSource:
    """参議院比例代表データソースのテスト."""

    @pytest.fixture()
    def data_source(self) -> SoumuSangiinProportionalDataSource:
        return SoumuSangiinProportionalDataSource()

    async def test_fetch_returns_candidates(
        self, data_source: SoumuSangiinProportionalDataSource, tmp_path: Path
    ) -> None:
        """正常系: XLSから候補者データが返される."""
        mock_xls_info = SangiinProportionalXlsInfo(
            url="https://example.com/test.xls",
            link_text="比例代表",
            file_extension=".xls",
        )
        mock_candidates = [
            ProportionalCandidateRecord(
                name="山田太郎",
                party_name="自由民主党",
                block_name="比例代表",
                list_order=0,
                smd_result="",
                loss_ratio=None,
                is_elected=True,
            ),
            ProportionalCandidateRecord(
                name="鈴木花子",
                party_name="立憲民主党",
                block_name="比例代表",
                list_order=0,
                smd_result="",
                loss_ratio=None,
                is_elected=False,
            ),
        ]
        mock_info = ProportionalElectionInfo(
            election_number=26,
            election_date=date(2022, 7, 10),
        )

        with (
            patch(
                "src.infrastructure.importers.soumu_sangiin_proportional_data_source"
                ".fetch_sangiin_proportional_xls_urls",
                return_value=[mock_xls_info],
            ),
            patch(
                "src.infrastructure.importers.soumu_sangiin_proportional_data_source"
                ".download_sangiin_proportional_xls",
                return_value=[(mock_xls_info, tmp_path / "test.xls")],
            ),
            patch(
                "src.infrastructure.importers.soumu_sangiin_proportional_data_source"
                ".parse_sangiin_proportional_xls",
                return_value=(mock_info, mock_candidates),
            ),
        ):
            info, candidates = await data_source.fetch_proportional_candidates(
                26, download_dir=tmp_path
            )

        assert info is not None
        assert info.election_number == 26
        assert len(candidates) == 2
        assert candidates[0].name == "山田太郎"
        assert candidates[0].is_elected is True

    async def test_fetch_no_xls_found(
        self, data_source: SoumuSangiinProportionalDataSource, tmp_path: Path
    ) -> None:
        """XLSが見つからない場合は空を返す."""
        with patch(
            "src.infrastructure.importers.soumu_sangiin_proportional_data_source"
            ".fetch_sangiin_proportional_xls_urls",
            return_value=[],
        ):
            info, candidates = await data_source.fetch_proportional_candidates(
                26, download_dir=tmp_path
            )

        assert info is None
        assert candidates == []

    async def test_fetch_download_fails(
        self, data_source: SoumuSangiinProportionalDataSource, tmp_path: Path
    ) -> None:
        """ダウンロード失敗の場合は空を返す."""
        mock_xls_info = SangiinProportionalXlsInfo(
            url="https://example.com/test.xls",
            link_text="比例代表",
            file_extension=".xls",
        )
        with (
            patch(
                "src.infrastructure.importers.soumu_sangiin_proportional_data_source"
                ".fetch_sangiin_proportional_xls_urls",
                return_value=[mock_xls_info],
            ),
            patch(
                "src.infrastructure.importers.soumu_sangiin_proportional_data_source"
                ".download_sangiin_proportional_xls",
                return_value=[],
            ),
        ):
            info, candidates = await data_source.fetch_proportional_candidates(
                26, download_dir=tmp_path
            )

        assert info is None
        assert candidates == []

    async def test_fetch_fallback_election_info(
        self, data_source: SoumuSangiinProportionalDataSource, tmp_path: Path
    ) -> None:
        """パーサーがelection_infoを返さない場合、SANGIIN_ELECTION_DATESからフォールバック."""
        mock_xls_info = SangiinProportionalXlsInfo(
            url="https://example.com/test.xls",
            link_text="比例代表",
            file_extension=".xls",
        )
        with (
            patch(
                "src.infrastructure.importers.soumu_sangiin_proportional_data_source"
                ".fetch_sangiin_proportional_xls_urls",
                return_value=[mock_xls_info],
            ),
            patch(
                "src.infrastructure.importers.soumu_sangiin_proportional_data_source"
                ".download_sangiin_proportional_xls",
                return_value=[(mock_xls_info, tmp_path / "test.xls")],
            ),
            patch(
                "src.infrastructure.importers.soumu_sangiin_proportional_data_source"
                ".parse_sangiin_proportional_xls",
                return_value=(None, []),
            ),
        ):
            info, candidates = await data_source.fetch_proportional_candidates(
                26, download_dir=tmp_path
            )

        assert info is not None
        assert info.election_number == 26
        assert info.election_date == date(2022, 7, 10)
