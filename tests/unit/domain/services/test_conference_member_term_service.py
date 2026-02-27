"""ConferenceMemberTermServiceのテスト."""

from datetime import date, timedelta

import pytest

from src.domain.entities.election import Election
from src.domain.services.conference_member_term_service import (
    ConferenceMemberTermService,
)


# 参議院選挙日
SANGIIN_DATE_21 = date(2007, 7, 29)
SANGIIN_DATE_22 = date(2010, 7, 11)
SANGIIN_DATE_23 = date(2013, 7, 21)
SANGIIN_DATE_24 = date(2016, 7, 10)
SANGIIN_DATE_25 = date(2019, 7, 21)
SANGIIN_DATE_26 = date(2022, 7, 10)
SANGIIN_DATE_27 = date(2025, 7, 6)

# 衆議院選挙日
SHUGIIN_DATE_49 = date(2021, 10, 31)
SHUGIIN_DATE_50 = date(2024, 10, 27)


def _make_election(
    term_number: int,
    election_date: date,
    election_type: str = "参議院議員通常選挙",
    election_id: int | None = None,
) -> Election:
    return Election(
        governing_body_id=1,
        term_number=term_number,
        election_date=election_date,
        election_type=election_type,
        id=election_id or term_number,
    )


@pytest.fixture()
def sangiin_elections() -> list[Election]:
    return [
        _make_election(21, SANGIIN_DATE_21),
        _make_election(22, SANGIIN_DATE_22),
        _make_election(23, SANGIIN_DATE_23),
        _make_election(24, SANGIIN_DATE_24),
        _make_election(25, SANGIIN_DATE_25),
        _make_election(26, SANGIIN_DATE_26),
        _make_election(27, SANGIIN_DATE_27),
    ]


@pytest.fixture()
def shugiin_elections() -> list[Election]:
    return [
        _make_election(49, SHUGIIN_DATE_49, "衆議院議員総選挙"),
        _make_election(50, SHUGIIN_DATE_50, "衆議院議員総選挙"),
    ]


class TestCalculateEndDate:
    """calculate_end_dateのテスト."""

    def test_sangiin_odd_term_has_next(self, sangiin_elections: list[Election]) -> None:
        """参議院奇数回（第25回）→ 同パリティ次回（第27回）前日."""
        result = ConferenceMemberTermService.calculate_end_date(
            sangiin_elections[4],
            sangiin_elections,  # term=25
        )
        assert result == SANGIIN_DATE_27 - timedelta(days=1)

    def test_sangiin_even_term_no_next(self, sangiin_elections: list[Election]) -> None:
        """参議院偶数回（第26回）→ 次の偶数回なしでNone."""
        result = ConferenceMemberTermService.calculate_end_date(
            sangiin_elections[5],
            sangiin_elections,  # term=26
        )
        assert result is None

    def test_sangiin_even_term_has_next(
        self, sangiin_elections: list[Election]
    ) -> None:
        """参議院偶数回（第22回）→ 次の偶数回（第24回）前日."""
        result = ConferenceMemberTermService.calculate_end_date(
            sangiin_elections[1],
            sangiin_elections,  # term=22
        )
        assert result == SANGIIN_DATE_24 - timedelta(days=1)

    def test_sangiin_last_odd_no_next(self, sangiin_elections: list[Election]) -> None:
        """参議院最後の奇数回（第27回）→ 次の奇数回なしでNone."""
        result = ConferenceMemberTermService.calculate_end_date(
            sangiin_elections[6],
            sangiin_elections,  # term=27
        )
        assert result is None

    def test_shugiin_has_next(self, shugiin_elections: list[Election]) -> None:
        """衆議院（第49回）→ 次回（第50回）前日."""
        result = ConferenceMemberTermService.calculate_end_date(
            shugiin_elections[0],
            shugiin_elections,  # term=49
        )
        assert result == SHUGIIN_DATE_50 - timedelta(days=1)

    def test_shugiin_no_next(self, shugiin_elections: list[Election]) -> None:
        """衆議院（第50回）→ 次回なしでNone."""
        result = ConferenceMemberTermService.calculate_end_date(
            shugiin_elections[1],
            shugiin_elections,  # term=50
        )
        assert result is None

    def test_empty_elections_list(self) -> None:
        """空の選挙リスト → None."""
        election = _make_election(25, SANGIIN_DATE_25)
        result = ConferenceMemberTermService.calculate_end_date(election, [])
        assert result is None

    def test_single_election_in_list(self) -> None:
        """1件のみの選挙リスト → None."""
        election = _make_election(25, SANGIIN_DATE_25)
        result = ConferenceMemberTermService.calculate_end_date(election, [election])
        assert result is None
