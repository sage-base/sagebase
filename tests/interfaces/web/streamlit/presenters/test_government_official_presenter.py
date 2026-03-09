"""GovernmentOfficialPresenterのテスト."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.application.dtos.government_official_dto import (
    GovernmentOfficialOutputItem,
)
from src.application.usecases.batch_link_speakers_to_government_officials_usecase import (  # noqa: E501
    BatchLinkDetail,
    BatchLinkOutputDto,
)
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
        # テスト用にリポジトリを独立したモックに差し替え
        p.official_repo = AsyncMock()
        p.position_repo = AsyncMock()
        p.speaker_repo = AsyncMock()
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

    def test_load_data_handles_exception(
        self, presenter: GovernmentOfficialPresenter
    ) -> None:
        """例外発生時は空リストを返すこと."""
        presenter.official_repo.get_all = AsyncMock(side_effect=Exception("DB error"))

        result = presenter.load_data()

        assert result == []


class TestSearch:
    def test_search_returns_results(
        self, presenter: GovernmentOfficialPresenter
    ) -> None:
        """名前検索が結果を返すこと."""
        official = GovernmentOfficial(id=1, name="田中太郎")
        presenter.official_repo.search_by_name = AsyncMock(return_value=[official])
        presenter.position_repo.get_by_official = AsyncMock(return_value=[])

        result = presenter.search("田中")

        assert len(result) == 1
        assert result[0].name == "田中太郎"

    def test_search_empty(self, presenter: GovernmentOfficialPresenter) -> None:
        """該当なしの場合は空リストを返すこと."""
        presenter.official_repo.search_by_name = AsyncMock(return_value=[])

        result = presenter.search("存在しない名前")

        assert result == []

    def test_search_handles_exception(
        self, presenter: GovernmentOfficialPresenter
    ) -> None:
        """例外発生時は空リストを返すこと."""
        presenter.official_repo.search_by_name = AsyncMock(
            side_effect=Exception("DB error")
        )

        result = presenter.search("田中")

        assert result == []


class TestCreate:
    def test_create_success(self, presenter: GovernmentOfficialPresenter) -> None:
        """新規作成が成功し、DTOを返すこと."""
        created = GovernmentOfficial(id=1, name="田中太郎")
        presenter.official_repo.create = AsyncMock(return_value=created)

        success, dto, error = presenter.create(name="田中太郎")

        assert success is True
        assert dto is not None
        assert isinstance(dto, GovernmentOfficialOutputItem)
        assert dto.name == "田中太郎"
        assert dto.id == 1
        assert error is None

    def test_create_handles_exception(
        self, presenter: GovernmentOfficialPresenter
    ) -> None:
        """例外発生時はエラーを返すこと."""
        presenter.official_repo.create = AsyncMock(side_effect=Exception("DB error"))

        success, dto, error = presenter.create(name="田中太郎")

        assert success is False
        assert dto is None
        assert error is not None
        assert "DB error" in error


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

    def test_update_handles_exception(
        self, presenter: GovernmentOfficialPresenter
    ) -> None:
        """例外発生時はエラーを返すこと."""
        presenter.official_repo.get_by_id = AsyncMock(side_effect=Exception("DB error"))

        success, error = presenter.update(id=1, name="田中次郎")

        assert success is False
        assert "DB error" in error


class TestDelete:
    def test_delete_success(self, presenter: GovernmentOfficialPresenter) -> None:
        """削除が成功すること."""
        presenter.official_repo.delete = AsyncMock(return_value=None)

        success, error = presenter.delete(id=1)

        assert success is True
        assert error is None

    def test_delete_handles_exception(
        self, presenter: GovernmentOfficialPresenter
    ) -> None:
        """例外発生時はエラーを返すこと."""
        presenter.official_repo.delete = AsyncMock(side_effect=Exception("DB error"))

        success, error = presenter.delete(id=1)

        assert success is False
        assert "DB error" in error


class TestBatchLinkSpeakers:
    def test_batch_link_dry_run(self, presenter: GovernmentOfficialPresenter) -> None:
        """batch_link_speakersがdry_runで結果を返すこと."""
        expected = BatchLinkOutputDto(
            linked_count=2,
            skipped_count=1,
            details=[
                BatchLinkDetail(
                    government_official_id=1,
                    government_official_name="田中太郎",
                    speaker_id=10,
                    speaker_name="田中太郎",
                    normalized_name="田中太郎",
                ),
                BatchLinkDetail(
                    government_official_id=2,
                    government_official_name="佐藤花子",
                    speaker_id=11,
                    speaker_name="佐藤花子",
                    normalized_name="佐藤花子",
                ),
            ],
        )

        with patch(
            "src.interfaces.web.streamlit.presenters.government_official_presenter."
            "BatchLinkSpeakersToGovernmentOfficialsUseCase"
        ) as mock_usecase_cls:
            mock_usecase = AsyncMock()
            mock_usecase.execute = AsyncMock(return_value=expected)
            mock_usecase_cls.return_value = mock_usecase

            result = presenter.batch_link_speakers(dry_run=True)

        assert result.linked_count == 2
        assert result.skipped_count == 1
        assert len(result.details) == 2

    def test_batch_link_handles_exception(
        self, presenter: GovernmentOfficialPresenter
    ) -> None:
        """例外発生時は空の結果を返すこと."""
        with patch(
            "src.interfaces.web.streamlit.presenters.government_official_presenter."
            "BatchLinkSpeakersToGovernmentOfficialsUseCase"
        ) as mock_usecase_cls:
            mock_usecase = AsyncMock()
            mock_usecase.execute = AsyncMock(side_effect=Exception("error"))
            mock_usecase_cls.return_value = mock_usecase

            result = presenter.batch_link_speakers(dry_run=False)

        assert result.linked_count == 0
        assert result.skipped_count == 0
        assert result.details == []


class TestHandleAction:
    def test_handle_action_list(self, presenter: GovernmentOfficialPresenter) -> None:
        """handle_action('list')がload_dataを呼ぶこと."""
        presenter.official_repo.get_all = AsyncMock(return_value=[])

        result = presenter.handle_action("list")

        assert result == []

    def test_handle_action_create(self, presenter: GovernmentOfficialPresenter) -> None:
        """handle_action('create')がcreateを呼ぶこと."""
        created = GovernmentOfficial(id=1, name="田中太郎")
        presenter.official_repo.create = AsyncMock(return_value=created)

        success, dto, error = presenter.handle_action("create", name="田中太郎")

        assert success is True
        assert dto is not None

    def test_handle_action_unknown_raises(
        self, presenter: GovernmentOfficialPresenter
    ) -> None:
        """不明なアクションでValueErrorが発生すること."""
        with pytest.raises(ValueError, match="Unknown action"):
            presenter.handle_action("unknown_action")


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
