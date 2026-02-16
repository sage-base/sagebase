"""KokkaiBatchImportPresenterのテスト."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.application.dtos.kokkai_speech_dto import (
    BatchImportKokkaiSpeechesInputDTO,
    ImportKokkaiSpeechesOutputDTO,
    KokkaiMeetingDTO,
)
from src.application.usecases.batch_import_kokkai_speeches_usecase import (
    BatchImportKokkaiSpeechesUseCase,
)
from src.application.usecases.import_kokkai_speeches_usecase import (
    ImportKokkaiSpeechesUseCase,
)


@pytest.fixture()
def mock_batch_usecase() -> AsyncMock:
    """BatchImportKokkaiSpeechesUseCaseのモック."""
    return AsyncMock(spec=BatchImportKokkaiSpeechesUseCase)


@pytest.fixture()
def mock_import_usecase() -> AsyncMock:
    """ImportKokkaiSpeechesUseCaseのモック."""
    return AsyncMock(spec=ImportKokkaiSpeechesUseCase)


@pytest.fixture()
def mock_container(
    mock_batch_usecase: AsyncMock,
    mock_import_usecase: AsyncMock,
) -> MagicMock:
    """DIコンテナのモック."""
    container = MagicMock()
    container.use_cases.batch_import_kokkai_speeches_usecase.return_value = (
        mock_batch_usecase
    )
    container.use_cases.import_kokkai_speeches_usecase.return_value = (
        mock_import_usecase
    )
    return container


@pytest.fixture()
def presenter(mock_container: MagicMock):
    """KokkaiBatchImportPresenterのインスタンス."""
    with patch(
        "src.interfaces.web.streamlit.presenters.base.Container"
    ) as mock_container_cls:
        mock_container_cls.create_for_environment.return_value = mock_container

        from src.interfaces.web.streamlit.presenters.kokkai_batch_import_presenter import (  # noqa: E501
            KokkaiBatchImportPresenter,
        )

        yield KokkaiBatchImportPresenter()


class TestKokkaiBatchImportPresenterInit:
    """初期化テスト."""

    def test_init_creates_instance(self) -> None:
        """Presenterが正しく初期化されることを確認."""
        mock_container = MagicMock()
        mock_container.use_cases.batch_import_kokkai_speeches_usecase.return_value = (
            AsyncMock()
        )
        mock_container.use_cases.import_kokkai_speeches_usecase.return_value = (
            AsyncMock()
        )

        with patch(
            "src.interfaces.web.streamlit.presenters.base.Container"
        ) as mock_container_cls:
            mock_container_cls.create_for_environment.return_value = mock_container

            from src.interfaces.web.streamlit.presenters.kokkai_batch_import_presenter import (  # noqa: E501
                KokkaiBatchImportPresenter,
            )

            p = KokkaiBatchImportPresenter()
            assert p is not None


class TestFetchMeetings:
    """fetch_meetingsメソッドのテスト."""

    def test_delegates_to_batch_usecase(
        self,
        presenter,
        mock_batch_usecase: AsyncMock,
    ) -> None:
        """fetch_meetingsがbatch_usecaseに委譲されることを確認."""
        expected = [
            KokkaiMeetingDTO(
                issue_id="issue1",
                session=213,
                name_of_house="衆議院",
                name_of_meeting="本会議",
                issue="第1号",
                date="2025-04-01",
                meeting_url="https://example.com/1",
            )
        ]
        mock_batch_usecase.fetch_target_meetings.return_value = expected

        input_dto = BatchImportKokkaiSpeechesInputDTO(session_from=213, session_to=213)
        result = presenter.fetch_meetings(input_dto)

        assert result == expected
        mock_batch_usecase.fetch_target_meetings.assert_called_once_with(input_dto)

    def test_returns_empty_list(
        self,
        presenter,
        mock_batch_usecase: AsyncMock,
    ) -> None:
        """結果が空の場合に空リストを返すことを確認."""
        mock_batch_usecase.fetch_target_meetings.return_value = []

        input_dto = BatchImportKokkaiSpeechesInputDTO(session_from=999, session_to=999)
        result = presenter.fetch_meetings(input_dto)

        assert result == []


class TestImportSingleMeeting:
    """import_single_meetingメソッドのテスト."""

    def test_delegates_to_import_usecase(
        self,
        presenter,
        mock_import_usecase: AsyncMock,
    ) -> None:
        """import_single_meetingがimport_usecaseに正しく委譲されることを確認."""
        expected = ImportKokkaiSpeechesOutputDTO(
            total_speeches_imported=5,
            total_speeches_skipped=0,
            total_meetings_created=1,
            total_speakers_created=3,
        )
        mock_import_usecase.execute.return_value = expected

        result = presenter.import_single_meeting("issue123")

        assert result == expected
        call_args = mock_import_usecase.execute.call_args[0][0]
        assert call_args.issue_id == "issue123"

    def test_propagates_exception(
        self,
        presenter,
        mock_import_usecase: AsyncMock,
    ) -> None:
        """UseCase例外がそのまま伝播することを確認."""
        mock_import_usecase.execute.side_effect = RuntimeError("API error")

        with pytest.raises(RuntimeError, match="API error"):
            presenter.import_single_meeting("issue_fail")


class TestLoadDataAndHandleAction:
    """BasePresenter抽象メソッド実装のテスト."""

    def test_load_data_returns_empty(self, presenter) -> None:
        """load_dataが空リストを返すことを確認."""
        assert presenter.load_data() == []

    def test_handle_action_returns_none(self, presenter) -> None:
        """handle_actionがNoneを返すことを確認."""
        assert presenter.handle_action("any_action") is None
