"""ElectionDomainServiceのテスト."""

from datetime import date

import pytest

from src.domain.entities.election import Election
from src.domain.services.election_domain_service import ElectionDomainService


def _make_election(
    term: int,
    election_date: date,
    election_type: str | None = None,
    governing_body_id: int = 1,
    election_id: int | None = None,
) -> Election:
    return Election(
        governing_body_id=governing_body_id,
        term_number=term,
        election_date=election_date,
        election_type=election_type,
        id=election_id,
    )


@pytest.fixture
def service() -> ElectionDomainService:
    return ElectionDomainService()


@pytest.fixture
def shugiin_elections() -> list[Election]:
    """衆議院選挙（第45-50回）のテストデータ."""
    return [
        _make_election(
            45, date(2009, 8, 30), Election.ELECTION_TYPE_GENERAL, election_id=1
        ),
        _make_election(
            46, date(2012, 12, 16), Election.ELECTION_TYPE_GENERAL, election_id=2
        ),
        _make_election(
            47, date(2014, 12, 14), Election.ELECTION_TYPE_GENERAL, election_id=3
        ),
        _make_election(
            48, date(2017, 10, 22), Election.ELECTION_TYPE_GENERAL, election_id=4
        ),
        _make_election(
            49, date(2021, 10, 31), Election.ELECTION_TYPE_GENERAL, election_id=5
        ),
        _make_election(
            50, date(2024, 10, 27), Election.ELECTION_TYPE_GENERAL, election_id=6
        ),
    ]


class TestGetActiveElectionAtDate:
    """get_active_election_at_dateメソッドのテスト."""

    def test_election_day_returns_that_election(
        self, service: ElectionDomainService, shugiin_elections: list[Election]
    ) -> None:
        """選挙当日はその選挙を返す."""
        result = service.get_active_election_at_date(
            shugiin_elections, date(2024, 10, 27)
        )
        assert result is not None
        assert result.term_number == 50

    def test_mid_term_date_returns_correct_election(
        self, service: ElectionDomainService, shugiin_elections: list[Election]
    ) -> None:
        """任期中の日付は該当選挙を返す."""
        result = service.get_active_election_at_date(
            shugiin_elections, date(2020, 5, 1)
        )
        assert result is not None
        assert result.term_number == 48

    def test_day_before_next_election_returns_previous(
        self, service: ElectionDomainService, shugiin_elections: list[Election]
    ) -> None:
        """次の選挙の前日は前の選挙を返す."""
        result = service.get_active_election_at_date(
            shugiin_elections, date(2024, 10, 26)
        )
        assert result is not None
        assert result.term_number == 49

    def test_before_first_election_returns_none(
        self, service: ElectionDomainService, shugiin_elections: list[Election]
    ) -> None:
        """最初の選挙より前の日付はNoneを返す."""
        result = service.get_active_election_at_date(
            shugiin_elections, date(2009, 8, 29)
        )
        assert result is None

    def test_after_latest_election_returns_latest(
        self, service: ElectionDomainService, shugiin_elections: list[Election]
    ) -> None:
        """最新選挙以降の日付は最新選挙を返す."""
        result = service.get_active_election_at_date(
            shugiin_elections, date(2026, 1, 1)
        )
        assert result is not None
        assert result.term_number == 50

    def test_dissolution_date_returns_previous_election(
        self, service: ElectionDomainService, shugiin_elections: list[Election]
    ) -> None:
        """解散日は解散前の選挙を返す（2012-11-16解散）."""
        result = service.get_active_election_at_date(
            shugiin_elections, date(2012, 11, 16)
        )
        assert result is not None
        assert result.term_number == 45

    @pytest.mark.parametrize(
        ("target_date", "expected_term"),
        [
            (date(2010, 6, 1), 45),
            (date(2013, 6, 1), 46),
            (date(2016, 6, 1), 47),
            (date(2019, 6, 1), 48),
            (date(2023, 6, 1), 49),
            (date(2025, 6, 1), 50),
        ],
        ids=[
            "term_45",
            "term_46",
            "term_47",
            "term_48",
            "term_49",
            "term_50",
        ],
    )
    def test_all_term_mappings(
        self,
        service: ElectionDomainService,
        shugiin_elections: list[Election],
        target_date: date,
        expected_term: int,
    ) -> None:
        """各任期中の代表日付が正しい選挙を返す."""
        result = service.get_active_election_at_date(shugiin_elections, target_date)
        assert result is not None
        assert result.term_number == expected_term

    def test_chamber_filter(
        self, service: ElectionDomainService, shugiin_elections: list[Election]
    ) -> None:
        """chamberフィルタで異なる院の選挙が除外される."""
        sangiin_election = _make_election(
            26, date(2022, 7, 10), Election.ELECTION_TYPE_SANGIIN, election_id=100
        )
        all_elections = [*shugiin_elections, sangiin_election]

        result = service.get_active_election_at_date(
            all_elections, date(2023, 1, 1), chamber="参議院"
        )
        assert result is not None
        assert result.term_number == 26

        result = service.get_active_election_at_date(
            all_elections, date(2023, 1, 1), chamber="衆議院"
        )
        assert result is not None
        assert result.term_number == 49

    def test_chamber_none_no_filter(
        self, service: ElectionDomainService, shugiin_elections: list[Election]
    ) -> None:
        """chamber=Noneの場合はフィルタなしで動作する."""
        sangiin_election = _make_election(
            26, date(2022, 7, 10), Election.ELECTION_TYPE_SANGIIN, election_id=100
        )
        all_elections = [*shugiin_elections, sangiin_election]

        result = service.get_active_election_at_date(
            all_elections, date(2023, 1, 1), chamber=None
        )
        assert result is not None
        # フィルタなし: 2023-01-01時点で最新は参議院26回
        assert result.term_number == 26
        assert result.election_date == date(2022, 7, 10)

    def test_empty_list_returns_none(self, service: ElectionDomainService) -> None:
        """空リストはNoneを返す."""
        result = service.get_active_election_at_date([], date(2024, 1, 1))
        assert result is None

    def test_no_matching_chamber_returns_none(
        self, service: ElectionDomainService, shugiin_elections: list[Election]
    ) -> None:
        """マッチするchamberがない場合はNoneを返す."""
        result = service.get_active_election_at_date(
            shugiin_elections, date(2024, 1, 1), chamber="参議院"
        )
        assert result is None

    def test_chamber_empty_string_filters_correctly(
        self, service: ElectionDomainService
    ) -> None:
        """chamber空文字のフィルタが正しく動作する."""
        # election_typeがNoneの場合、chamberは空文字を返す
        local_election = _make_election(1, date(2023, 4, 1), None, election_id=200)
        shugiin = _make_election(
            50,
            date(2024, 10, 27),
            Election.ELECTION_TYPE_GENERAL,
            election_id=6,
        )
        elections = [local_election, shugiin]

        # chamber=""でフィルタ: 空文字chamberの選挙のみ返る
        result = service.get_active_election_at_date(
            elections, date(2024, 12, 1), chamber=""
        )
        assert result is not None
        assert result.term_number == 1

    def test_same_date_elections_returns_one(
        self, service: ElectionDomainService
    ) -> None:
        """同一日付の複数選挙がある場合でもエラーにならない."""
        e1 = _make_election(
            49,
            date(2021, 10, 31),
            Election.ELECTION_TYPE_GENERAL,
            election_id=1,
        )
        e2 = _make_election(
            26,
            date(2021, 10, 31),
            Election.ELECTION_TYPE_SANGIIN,
            election_id=2,
        )
        result = service.get_active_election_at_date([e1, e2], date(2022, 1, 1))
        assert result is not None
        assert result.election_date == date(2021, 10, 31)
