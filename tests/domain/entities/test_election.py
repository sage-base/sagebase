"""Tests for Election entity."""

from datetime import date

from src.domain.entities.election import Election


class TestElectionChamber:
    """Election.chamber プロパティのテスト."""

    def test_chamber_returns_shugiin_for_general_election(self) -> None:
        """衆議院議員総選挙の場合、'衆議院'を返すこと."""
        election = Election(
            governing_body_id=1,
            term_number=50,
            election_date=date(2024, 10, 27),
            election_type=Election.ELECTION_TYPE_GENERAL,
        )
        assert election.chamber == "衆議院"

    def test_chamber_returns_sangiin_for_sangiin_election(self) -> None:
        """参議院議員通常選挙の場合、'参議院'を返すこと."""
        election = Election(
            governing_body_id=1,
            term_number=26,
            election_date=date(2022, 7, 10),
            election_type=Election.ELECTION_TYPE_SANGIIN,
        )
        assert election.chamber == "参議院"

    def test_chamber_returns_empty_for_other_election_type(self) -> None:
        """その他の選挙種別の場合、空文字列を返すこと."""
        election = Election(
            governing_body_id=2,
            term_number=21,
            election_date=date(2023, 4, 23),
            election_type="統一地方選挙",
        )
        assert election.chamber == ""

    def test_chamber_returns_empty_for_none_election_type(self) -> None:
        """election_typeがNoneの場合、空文字列を返すこと."""
        election = Election(
            governing_body_id=1,
            term_number=1,
            election_date=date(2020, 1, 1),
            election_type=None,
        )
        assert election.chamber == ""
