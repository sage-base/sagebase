"""WikipediaElectionDataSourceのユニットテスト."""

from datetime import date
from unittest.mock import patch

import pytest

from src.infrastructure.importers.wikipedia_election_data_source import (
    SUPPORTED_ELECTIONS,
    WikipediaElectionDataSource,
)


MOCK_WIKITEXT_42 = """
{{colorbox|#9E9|自由民主党}} {{colorbox|#f9b|民主党}}

{{衆議院小選挙区当選者(第49回まで)
|北海道1区色=f9b|北海道1区=[[横路孝弘]]
|北海道2区色=9E9|北海道2区=[[吉川貴盛]]
}}

{{衆議院当選者一覧(比例区)
|北海1色=f9b|北海1=[[中沢健次]]
|東北1色=9e9|東北1=[[御法川英文]]
}}
"""

MOCK_WIKITEXT_OLD = """
{{colorbox|#9E9|自由民主党}} {{colorbox|#0ff|日本社会党}}

=== 当選者 ===
{| class="wikitable"
! [[北海道]]
! [[北海道第1区 (中選挙区)|1区]]
|style="background-color:#9e9" | [[町村信孝]]
|style="background-color:#0ff" | [[横路孝弘]]
! [[北海道第2区 (中選挙区)|2区]]
|style="background-color:#9e9" | [[武部勤]]
|}
"""


class TestWikipediaElectionDataSource:
    """WikipediaElectionDataSourceのテスト."""

    @pytest.mark.asyncio
    async def test_fetch_candidates_success(self) -> None:
        ds = WikipediaElectionDataSource()
        with patch(
            "src.infrastructure.importers.wikipedia_election_data_source.fetch_wikipedia_wikitext",
            return_value=MOCK_WIKITEXT_42,
        ):
            info, candidates = await ds.fetch_candidates(42)

        assert info is not None
        assert info.election_number == 42
        assert info.election_date == date(2000, 6, 25)
        assert len(candidates) == 4  # 小選挙区2 + 比例代表2
        names = {c.name for c in candidates}
        assert "横路孝弘" in names
        assert "吉川貴盛" in names
        assert "中沢健次" in names
        assert "御法川英文" in names

    @pytest.mark.asyncio
    async def test_unsupported_election_returns_empty(self) -> None:
        ds = WikipediaElectionDataSource()
        info, candidates = await ds.fetch_candidates(50)
        assert info is None
        assert candidates == []

    @pytest.mark.asyncio
    async def test_all_supported_elections_have_dates(self) -> None:
        from src.infrastructure.importers.wikipedia_election_data_source import (
            ELECTION_DATES,
        )

        for n in SUPPORTED_ELECTIONS:
            assert n in ELECTION_DATES

    @pytest.mark.asyncio
    async def test_election_info_for_each_supported(self) -> None:
        ds = WikipediaElectionDataSource()
        for n in SUPPORTED_ELECTIONS:
            mock_data = MOCK_WIKITEXT_OLD if n <= 40 else MOCK_WIKITEXT_42
            with patch(
                "src.infrastructure.importers.wikipedia_election_data_source.fetch_wikipedia_wikitext",
                return_value=mock_data,
            ):
                info, _ = await ds.fetch_candidates(n)
            assert info is not None
            assert info.election_number == n

    @pytest.mark.asyncio
    async def test_fetch_old_election(self) -> None:
        """中選挙区制（第40回以前）のfetch_candidates."""
        ds = WikipediaElectionDataSource()
        with patch(
            "src.infrastructure.importers.wikipedia_election_data_source.fetch_wikipedia_wikitext",
            return_value=MOCK_WIKITEXT_OLD,
        ):
            info, candidates = await ds.fetch_candidates(40)

        assert info is not None
        assert info.election_number == 40
        assert info.election_date == date(1993, 7, 18)
        assert len(candidates) == 3
        names = {c.name for c in candidates}
        assert "町村信孝" in names
        assert "横路孝弘" in names
        assert "武部勤" in names

    @pytest.mark.asyncio
    async def test_supported_elections_range(self) -> None:
        """第1-44回がサポートされていること."""
        assert SUPPORTED_ELECTIONS == list(range(1, 45))

    @pytest.mark.asyncio
    async def test_first_election(self) -> None:
        """第1回選挙の日付が正しいこと."""
        from src.infrastructure.importers.wikipedia_election_data_source import (
            ELECTION_DATES,
        )

        assert ELECTION_DATES[1] == date(1890, 7, 1)
