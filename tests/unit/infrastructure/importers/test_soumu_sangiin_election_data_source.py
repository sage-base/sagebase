"""総務省参議院選挙データソースのテスト."""

from unittest.mock import patch

import pytest

from src.domain.value_objects.election_candidate import CandidateRecord, ElectionInfo
from src.infrastructure.importers.soumu_sangiin_election_data_source import (
    SoumuSangiinElectionDataSource,
)
from src.infrastructure.importers.soumu_sangiin_election_scraper import (
    SangiinXlsFileInfo,
)


@pytest.fixture
def data_source() -> SoumuSangiinElectionDataSource:
    return SoumuSangiinElectionDataSource()


class TestSoumuSangiinElectionDataSource:
    """SoumuSangiinElectionDataSourceのテスト."""

    @pytest.mark.asyncio
    async def test_fetch_candidates_no_xls_files(
        self, data_source: SoumuSangiinElectionDataSource
    ) -> None:
        """XLSファイルが見つからない場合はNoneと空リストを返す."""
        with patch(
            "src.infrastructure.importers.soumu_sangiin_election_data_source"
            ".fetch_sangiin_xls_urls",
            return_value=[],
        ):
            info, candidates = await data_source.fetch_candidates(26)
            assert info is None
            assert candidates == []

    @pytest.mark.asyncio
    async def test_fetch_candidates_download_failure(
        self, data_source: SoumuSangiinElectionDataSource
    ) -> None:
        """ダウンロード失敗時はNoneと空リストを返す."""
        xls_info = SangiinXlsFileInfo(
            url="https://example.com/test.xlsx",
            page_code="01",
            link_text="選挙結果",
            file_extension=".xlsx",
        )
        with (
            patch(
                "src.infrastructure.importers.soumu_sangiin_election_data_source"
                ".fetch_sangiin_xls_urls",
                return_value=[xls_info],
            ),
            patch(
                "src.infrastructure.importers.soumu_sangiin_election_data_source"
                ".download_sangiin_xls_files",
                return_value=[],
            ),
        ):
            info, candidates = await data_source.fetch_candidates(26)
            assert info is None
            assert candidates == []

    @pytest.mark.asyncio
    async def test_fetch_candidates_success(
        self, data_source: SoumuSangiinElectionDataSource
    ) -> None:
        """正常にデータを取得できる."""
        from datetime import date
        from pathlib import Path

        xls_info = SangiinXlsFileInfo(
            url="https://example.com/test.xlsx",
            page_code="01",
            link_text="選挙結果",
            file_extension=".xlsx",
        )
        dummy_path = Path("/tmp/dummy.xlsx")

        mock_election_info = ElectionInfo(
            election_number=26,
            election_date=date(2022, 7, 10),
        )
        mock_candidates = [
            CandidateRecord(
                name="候補A",
                party_name="政党A",
                district_name="北海道",
                prefecture="北海道",
                total_votes=5000,
                rank=1,
                is_elected=True,
            ),
            CandidateRecord(
                name="候補B",
                party_name="政党B",
                district_name="北海道",
                prefecture="北海道",
                total_votes=3000,
                rank=2,
                is_elected=True,
            ),
        ]

        with (
            patch(
                "src.infrastructure.importers.soumu_sangiin_election_data_source"
                ".fetch_sangiin_xls_urls",
                return_value=[xls_info],
            ),
            patch(
                "src.infrastructure.importers.soumu_sangiin_election_data_source"
                ".download_sangiin_xls_files",
                return_value=[(xls_info, dummy_path)],
            ),
            patch(
                "src.infrastructure.importers.soumu_sangiin_election_data_source"
                ".parse_sangiin_xls_file",
                return_value=(mock_election_info, mock_candidates),
            ),
        ):
            info, candidates = await data_source.fetch_candidates(26)
            assert info is not None
            assert info.election_number == 26
            assert len(candidates) == 2
            assert candidates[0].name == "候補A"

    @pytest.mark.asyncio
    async def test_fetch_candidates_fallback_election_info(
        self, data_source: SoumuSangiinElectionDataSource
    ) -> None:
        """XLSから選挙情報が取得できない場合、定数マッピングからフォールバックする."""
        from pathlib import Path

        xls_info = SangiinXlsFileInfo(
            url="https://example.com/test.xlsx",
            page_code="01",
            link_text="選挙結果",
            file_extension=".xlsx",
        )
        dummy_path = Path("/tmp/dummy.xlsx")

        mock_candidates = [
            CandidateRecord(
                name="候補A",
                party_name="政党A",
                district_name="北海道",
                prefecture="北海道",
                total_votes=5000,
                rank=1,
                is_elected=True,
            ),
        ]

        with (
            patch(
                "src.infrastructure.importers.soumu_sangiin_election_data_source"
                ".fetch_sangiin_xls_urls",
                return_value=[xls_info],
            ),
            patch(
                "src.infrastructure.importers.soumu_sangiin_election_data_source"
                ".download_sangiin_xls_files",
                return_value=[(xls_info, dummy_path)],
            ),
            patch(
                "src.infrastructure.importers.soumu_sangiin_election_data_source"
                ".parse_sangiin_xls_file",
                return_value=(None, mock_candidates),
            ),
        ):
            info, candidates = await data_source.fetch_candidates(26)
            # フォールバックで選挙情報が生成される
            assert info is not None
            assert info.election_number == 26
            assert info.election_date.year == 2022

    @pytest.mark.asyncio
    async def test_fetch_candidates_duplicate_district_skipped(
        self, data_source: SoumuSangiinElectionDataSource
    ) -> None:
        """同じ選挙区のデータが複数ファイルに存在する場合、最初のものだけ採用する."""
        from datetime import date
        from pathlib import Path

        xls_info_1 = SangiinXlsFileInfo(
            url="https://example.com/page_01.xlsx",
            page_code="01",
            link_text="選挙結果",
            file_extension=".xlsx",
        )
        xls_info_2 = SangiinXlsFileInfo(
            url="https://example.com/page_30.xlsx",
            page_code="30",
            link_text="選挙結果",
            file_extension=".xlsx",
        )
        dummy_path_1 = Path("/tmp/page_01.xlsx")
        dummy_path_2 = Path("/tmp/page_30.xlsx")

        mock_election_info = ElectionInfo(
            election_number=26,
            election_date=date(2022, 7, 10),
        )
        # 両方とも北海道のデータ（重複）
        candidates_1 = [
            CandidateRecord(
                name="候補A",
                party_name="政党A",
                district_name="北海道",
                prefecture="北海道",
                total_votes=5000,
                rank=1,
                is_elected=True,
            ),
        ]
        candidates_2 = [
            CandidateRecord(
                name="候補X",
                party_name="政党X",
                district_name="北海道",
                prefecture="北海道",
                total_votes=3000,
                rank=2,
                is_elected=True,
            ),
        ]

        parse_results = iter(
            [
                (mock_election_info, candidates_1),
                (None, candidates_2),
            ]
        )

        with (
            patch(
                "src.infrastructure.importers.soumu_sangiin_election_data_source"
                ".fetch_sangiin_xls_urls",
                return_value=[xls_info_1, xls_info_2],
            ),
            patch(
                "src.infrastructure.importers.soumu_sangiin_election_data_source"
                ".download_sangiin_xls_files",
                return_value=[
                    (xls_info_1, dummy_path_1),
                    (xls_info_2, dummy_path_2),
                ],
            ),
            patch(
                "src.infrastructure.importers.soumu_sangiin_election_data_source"
                ".parse_sangiin_xls_file",
                side_effect=lambda *_args, **_kwargs: next(parse_results),
            ),
        ):
            info, candidates = await data_source.fetch_candidates(26)
            assert info is not None
            # 最初のファイルの候補者のみ採用（重複はスキップ）
            assert len(candidates) == 1
            assert candidates[0].name == "候補A"

    @pytest.mark.asyncio
    async def test_fetch_candidates_multiple_districts(
        self, data_source: SoumuSangiinElectionDataSource
    ) -> None:
        """異なる選挙区のデータは全て採用される."""
        from datetime import date
        from pathlib import Path

        xls_info_1 = SangiinXlsFileInfo(
            url="https://example.com/page_01.xlsx",
            page_code="01",
            link_text="選挙結果",
            file_extension=".xlsx",
        )
        xls_info_2 = SangiinXlsFileInfo(
            url="https://example.com/page_13.xlsx",
            page_code="13",
            link_text="選挙結果",
            file_extension=".xlsx",
        )
        dummy_path_1 = Path("/tmp/page_01.xlsx")
        dummy_path_2 = Path("/tmp/page_13.xlsx")

        mock_election_info = ElectionInfo(
            election_number=26,
            election_date=date(2022, 7, 10),
        )
        candidates_hokkaido = [
            CandidateRecord(
                name="候補A",
                party_name="政党A",
                district_name="北海道",
                prefecture="北海道",
                total_votes=5000,
                rank=1,
                is_elected=True,
            ),
        ]
        candidates_tokyo = [
            CandidateRecord(
                name="候補B",
                party_name="政党B",
                district_name="東京都",
                prefecture="東京都",
                total_votes=8000,
                rank=1,
                is_elected=True,
            ),
        ]

        parse_results = iter(
            [
                (mock_election_info, candidates_hokkaido),
                (None, candidates_tokyo),
            ]
        )

        with (
            patch(
                "src.infrastructure.importers.soumu_sangiin_election_data_source"
                ".fetch_sangiin_xls_urls",
                return_value=[xls_info_1, xls_info_2],
            ),
            patch(
                "src.infrastructure.importers.soumu_sangiin_election_data_source"
                ".download_sangiin_xls_files",
                return_value=[
                    (xls_info_1, dummy_path_1),
                    (xls_info_2, dummy_path_2),
                ],
            ),
            patch(
                "src.infrastructure.importers.soumu_sangiin_election_data_source"
                ".parse_sangiin_xls_file",
                side_effect=lambda *_args, **_kwargs: next(parse_results),
            ),
        ):
            info, candidates = await data_source.fetch_candidates(26)
            assert info is not None
            # 異なる選挙区の候補者は全て採用
            assert len(candidates) == 2
            districts = {c.district_name for c in candidates}
            assert districts == {"北海道", "東京都"}
