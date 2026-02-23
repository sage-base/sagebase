"""政党所属履歴リポジトリ実装のテスト."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.infrastructure.persistence.party_membership_history_repository_impl import (
    PartyMembershipHistoryRepositoryImpl,
)


class TestGetCurrentByPoliticians:
    """get_current_by_politiciansのテスト."""

    @pytest.fixture()
    def mock_session(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture()
    def repo(self, mock_session: AsyncMock) -> PartyMembershipHistoryRepositoryImpl:
        return PartyMembershipHistoryRepositoryImpl(session=mock_session)

    async def test_empty_list_returns_empty_dict(
        self, repo: PartyMembershipHistoryRepositoryImpl
    ) -> None:
        """空リストでは空dictを返す."""
        result = await repo.get_current_by_politicians([])
        assert result == {}

    async def test_multiple_politicians(
        self,
        repo: PartyMembershipHistoryRepositoryImpl,
        mock_session: AsyncMock,
    ) -> None:
        """複数政治家の所属を正常に取得する."""
        model1 = MagicMock()
        model1.id = 1
        model1.politician_id = 10
        model1.political_party_id = 100
        model1.start_date = date(2024, 1, 1)
        model1.end_date = None
        model1.created_at = None
        model1.updated_at = None

        model2 = MagicMock()
        model2.id = 2
        model2.politician_id = 20
        model2.political_party_id = 200
        model2.start_date = date(2024, 1, 1)
        model2.end_date = None
        model2.created_at = None
        model2.updated_at = None

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [model1, model2]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_session.execute.return_value = result_mock

        result = await repo.get_current_by_politicians(
            [10, 20], as_of_date=date(2024, 6, 1)
        )

        assert len(result) == 2
        assert result[10].political_party_id == 100
        assert result[20].political_party_id == 200

    async def test_expired_history_excluded(
        self,
        repo: PartyMembershipHistoryRepositoryImpl,
        mock_session: AsyncMock,
    ) -> None:
        """期限切れ履歴がSQLで除外された結果、空dictが返される."""
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_session.execute.return_value = result_mock

        result = await repo.get_current_by_politicians(
            [10], as_of_date=date(2025, 1, 1)
        )
        assert result == {}

    async def test_multiple_histories_for_same_politician_uses_latest(
        self,
        repo: PartyMembershipHistoryRepositoryImpl,
        mock_session: AsyncMock,
    ) -> None:
        """同一政治家に複数履歴がある場合、start_date降順で最初のものが優先される."""
        model_new = MagicMock()
        model_new.id = 2
        model_new.politician_id = 10
        model_new.political_party_id = 200
        model_new.start_date = date(2024, 6, 1)
        model_new.end_date = None
        model_new.created_at = None
        model_new.updated_at = None

        model_old = MagicMock()
        model_old.id = 1
        model_old.politician_id = 10
        model_old.political_party_id = 100
        model_old.start_date = date(2020, 1, 1)
        model_old.end_date = None
        model_old.created_at = None
        model_old.updated_at = None

        # start_date降順で返される想定
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [model_new, model_old]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_session.execute.return_value = result_mock

        result = await repo.get_current_by_politicians(
            [10], as_of_date=date(2024, 12, 1)
        )

        assert len(result) == 1
        assert result[10].political_party_id == 200

    async def test_default_as_of_date_uses_today(
        self,
        repo: PartyMembershipHistoryRepositoryImpl,
        mock_session: AsyncMock,
    ) -> None:
        """as_of_dateがNoneの場合、today()が使用される."""
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_session.execute.return_value = result_mock

        result = await repo.get_current_by_politicians([10])
        assert result == {}
        mock_session.execute.assert_called_once()
