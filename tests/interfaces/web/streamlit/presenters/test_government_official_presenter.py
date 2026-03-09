"""GovernmentOfficialPresenterのテスト."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.application.dtos.government_official_dto import GovernmentOfficialOutputItem
from src.domain.entities.government_official import GovernmentOfficial
from src.interfaces.web.streamlit.presenters.government_official_presenter import (
    GovernmentOfficialPresenter,
)


@pytest.fixture
def mock_container() -> MagicMock:
    container = MagicMock()
    return container


@pytest.fixture
def presenter(mock_container: MagicMock) -> GovernmentOfficialPresenter:
    with patch(
        "src.interfaces.web.streamlit.presenters.government_official_presenter.RepositoryAdapter"
    ) as mock_adapter_cls:
        mock_adapter = AsyncMock()
        mock_adapter_cls.return_value = mock_adapter
        p = GovernmentOfficialPresenter(container=mock_container)
        # テスト用にリポジトリをモックに差し替え
        p.official_repo = mock_adapter
        p.position_repo = mock_adapter
        p.speaker_repo = mock_adapter
        return p


class TestLoadData:
    def test_load_data_returns_officials(
        self, presenter: GovernmentOfficialPresenter
    ) -> None:
        """load_dataが官僚一覧を返すこと."""
        official = GovernmentOfficial(id=1, name="田中太郎")
        presenter.official_repo.get_all = AsyncMock(return_value=[official])
        presenter.position_repo.get_by_official = AsyncMock(return_value=[])

        result = presenter.load_data()

        assert len(result) == 1
        assert result[0].name == "田中太郎"

    def test_load_data_empty(self, presenter: GovernmentOfficialPresenter) -> None:
        """データがない場合は空リストを返すこと."""
        presenter.official_repo.get_all = AsyncMock(return_value=[])

        result = presenter.load_data()

        assert result == []


class TestCreate:
    def test_create_success(self, presenter: GovernmentOfficialPresenter) -> None:
        """新規作成が成功すること."""
        created = GovernmentOfficial(id=1, name="田中太郎")
        presenter.official_repo.create = AsyncMock(return_value=created)

        success, entity, error = presenter.create(name="田中太郎")

        assert success is True
        assert entity is not None
        assert entity.name == "田中太郎"
        assert error is None


class TestUpdate:
    def test_update_success(self, presenter: GovernmentOfficialPresenter) -> None:
        """更新が成功すること."""
        existing = GovernmentOfficial(id=1, name="田中太郎")
        presenter.official_repo.get_by_id = AsyncMock(return_value=existing)
        presenter.official_repo.update = AsyncMock(return_value=existing)

        success, error = presenter.update(id=1, name="田中次郎")

        assert success is True
        assert error is None

    def test_update_not_found(self, presenter: GovernmentOfficialPresenter) -> None:
        """存在しないIDで更新するとエラーになること."""
        presenter.official_repo.get_by_id = AsyncMock(return_value=None)

        success, error = presenter.update(id=999, name="不明")

        assert success is False
        assert error is not None


class TestDelete:
    def test_delete_success(self, presenter: GovernmentOfficialPresenter) -> None:
        """削除が成功すること."""
        presenter.official_repo.delete = AsyncMock(return_value=None)

        success, error = presenter.delete(id=1)

        assert success is True
        assert error is None


class TestToDataframe:
    def test_to_dataframe(self, presenter: GovernmentOfficialPresenter) -> None:
        """DataFrameに変換できること."""
        officials = [
            GovernmentOfficialOutputItem(
                id=1, name="田中太郎", name_yomi="たなかたろう"
            ),
        ]

        df = presenter.to_dataframe(officials)

        assert df is not None
        assert len(df) == 1
        assert df.iloc[0]["名前"] == "田中太郎"

    def test_to_dataframe_empty(self, presenter: GovernmentOfficialPresenter) -> None:
        """空リストの場合はNoneを返すこと."""
        df = presenter.to_dataframe([])
        assert df is None
