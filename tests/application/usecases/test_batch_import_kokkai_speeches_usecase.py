"""BatchImportKokkaiSpeechesUseCase のユニットテスト."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, call

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
from src.domain.services.interfaces.kokkai_speech_service import IKokkaiSpeechService


def _make_meeting(**overrides: object) -> KokkaiMeetingDTO:
    """テスト用KokkaiMeetingDTOを生成."""
    defaults = {
        "issue_id": "121705253X00320250423",
        "session": 213,
        "name_of_house": "衆議院",
        "name_of_meeting": "本会議",
        "issue": "第3号",
        "date": "2025-04-23",
        "meeting_url": "https://kokkai.ndl.go.jp/meeting/1",
    }
    defaults.update(overrides)
    return KokkaiMeetingDTO(**defaults)  # type: ignore[arg-type]


@pytest.fixture()
def mock_speech_service() -> AsyncMock:
    return AsyncMock(spec=IKokkaiSpeechService)


@pytest.fixture()
def mock_import_usecase() -> AsyncMock:
    return AsyncMock(spec=ImportKokkaiSpeechesUseCase)


@pytest.fixture()
def usecase(
    mock_speech_service: AsyncMock,
    mock_import_usecase: AsyncMock,
) -> BatchImportKokkaiSpeechesUseCase:
    return BatchImportKokkaiSpeechesUseCase(
        kokkai_speech_service=mock_speech_service,
        import_usecase=mock_import_usecase,
    )


class TestFetchTargetMeetings:
    """fetch_target_meetings のテスト."""

    @pytest.mark.asyncio()
    async def test_delegates_to_service(
        self,
        usecase: BatchImportKokkaiSpeechesUseCase,
        mock_speech_service: AsyncMock,
    ) -> None:
        """サービスに正しいパラメータを渡す."""
        meetings = [_make_meeting()]
        mock_speech_service.fetch_meetings.return_value = meetings

        input_dto = BatchImportKokkaiSpeechesInputDTO(
            name_of_house="衆議院",
            session_from=213,
            session_to=213,
        )
        result = await usecase.fetch_target_meetings(input_dto)

        assert result == meetings
        mock_speech_service.fetch_meetings.assert_called_once_with(
            name_of_house="衆議院",
            name_of_meeting=None,
            from_date=None,
            until_date=None,
            session_from=213,
            session_to=213,
        )

    @pytest.mark.asyncio()
    async def test_empty_result(
        self,
        usecase: BatchImportKokkaiSpeechesUseCase,
        mock_speech_service: AsyncMock,
    ) -> None:
        """対象会議がない場合は空リストを返す."""
        mock_speech_service.fetch_meetings.return_value = []
        input_dto = BatchImportKokkaiSpeechesInputDTO(session_from=999, session_to=999)

        result = await usecase.fetch_target_meetings(input_dto)

        assert result == []


class TestExecute:
    """execute のテスト."""

    @pytest.mark.asyncio()
    async def test_import_multiple_meetings(
        self,
        usecase: BatchImportKokkaiSpeechesUseCase,
        mock_speech_service: AsyncMock,
        mock_import_usecase: AsyncMock,
    ) -> None:
        """複数会議のインポートが正しく集約される."""
        meetings = [
            _make_meeting(issue_id="issue1", date="2025-04-01"),
            _make_meeting(issue_id="issue2", date="2025-04-02"),
        ]
        mock_speech_service.fetch_meetings.return_value = meetings
        mock_import_usecase.execute.side_effect = [
            ImportKokkaiSpeechesOutputDTO(
                total_speeches_imported=10,
                total_meetings_created=1,
                total_speakers_created=3,
            ),
            ImportKokkaiSpeechesOutputDTO(
                total_speeches_imported=5,
                total_meetings_created=1,
                total_speakers_created=1,
            ),
        ]

        input_dto = BatchImportKokkaiSpeechesInputDTO(
            session_from=213, session_to=213, sleep_interval=0.0
        )
        result = await usecase.execute(input_dto)

        assert result.total_meetings_found == 2
        assert result.total_meetings_processed == 2
        assert result.total_speeches_imported == 15
        assert result.total_speakers_created == 4
        assert result.errors == []

    @pytest.mark.asyncio()
    async def test_skip_existing_meetings(
        self,
        usecase: BatchImportKokkaiSpeechesUseCase,
        mock_speech_service: AsyncMock,
        mock_import_usecase: AsyncMock,
    ) -> None:
        """既存会議がスキップされる場合のカウント."""
        meetings = [_make_meeting()]
        mock_speech_service.fetch_meetings.return_value = meetings
        mock_import_usecase.execute.return_value = ImportKokkaiSpeechesOutputDTO(
            total_speeches_imported=0,
            total_speeches_skipped=15,
        )

        input_dto = BatchImportKokkaiSpeechesInputDTO(
            session_from=213, session_to=213, sleep_interval=0.0
        )
        result = await usecase.execute(input_dto)

        assert result.total_meetings_skipped == 1
        assert result.total_speeches_skipped == 15
        assert result.total_speeches_imported == 0

    @pytest.mark.asyncio()
    async def test_partial_failure_continues(
        self,
        usecase: BatchImportKokkaiSpeechesUseCase,
        mock_speech_service: AsyncMock,
        mock_import_usecase: AsyncMock,
    ) -> None:
        """個別会議のエラーで全体が停止しない."""
        meetings = [
            _make_meeting(issue_id="ok1"),
            _make_meeting(issue_id="fail1"),
            _make_meeting(issue_id="ok2"),
        ]
        mock_speech_service.fetch_meetings.return_value = meetings
        mock_import_usecase.execute.side_effect = [
            ImportKokkaiSpeechesOutputDTO(total_speeches_imported=5),
            RuntimeError("API接続エラー"),
            ImportKokkaiSpeechesOutputDTO(total_speeches_imported=3),
        ]

        input_dto = BatchImportKokkaiSpeechesInputDTO(
            session_from=213, session_to=213, sleep_interval=0.0
        )
        result = await usecase.execute(input_dto)

        assert result.total_speeches_imported == 8
        assert result.total_meetings_processed == 2
        assert len(result.errors) == 1
        assert "API接続エラー" in result.errors[0]
        # 全3件が処理された（import_usecase.executeが3回呼ばれた）
        assert mock_import_usecase.execute.call_count == 3

    @pytest.mark.asyncio()
    async def test_empty_meetings_returns_immediately(
        self,
        usecase: BatchImportKokkaiSpeechesUseCase,
        mock_speech_service: AsyncMock,
        mock_import_usecase: AsyncMock,
    ) -> None:
        """対象会議がない場合は即座に完了."""
        mock_speech_service.fetch_meetings.return_value = []

        input_dto = BatchImportKokkaiSpeechesInputDTO(session_from=999, session_to=999)
        result = await usecase.execute(input_dto)

        assert result.total_meetings_found == 0
        assert result.total_meetings_processed == 0
        mock_import_usecase.execute.assert_not_called()

    @pytest.mark.asyncio()
    async def test_progress_callback_called(
        self,
        usecase: BatchImportKokkaiSpeechesUseCase,
        mock_speech_service: AsyncMock,
        mock_import_usecase: AsyncMock,
    ) -> None:
        """進捗コールバックが正しく呼び出される."""
        meetings = [
            _make_meeting(issue_id="m1"),
            _make_meeting(issue_id="m2"),
        ]
        mock_speech_service.fetch_meetings.return_value = meetings
        mock_import_usecase.execute.return_value = ImportKokkaiSpeechesOutputDTO(
            total_speeches_imported=5,
        )
        callback = MagicMock()

        input_dto = BatchImportKokkaiSpeechesInputDTO(
            session_from=213, session_to=213, sleep_interval=0.0
        )
        await usecase.execute(input_dto, progress_callback=callback)

        # 各会議の開始時 + 完了通知
        assert callback.call_count == 3
        # 最初の呼び出し: (0, 2, label)
        assert callback.call_args_list[0][0][0] == 0
        assert callback.call_args_list[0][0][1] == 2
        # 2番目: (1, 2, label)
        assert callback.call_args_list[1][0][0] == 1
        assert callback.call_args_list[1][0][1] == 2
        # 完了通知: (2, 2, "完了")
        assert callback.call_args_list[2] == call(2, 2, "完了")

    @pytest.mark.asyncio()
    async def test_errors_from_import_usecase_aggregated(
        self,
        usecase: BatchImportKokkaiSpeechesUseCase,
        mock_speech_service: AsyncMock,
        mock_import_usecase: AsyncMock,
    ) -> None:
        """ImportUseCaseからのエラーが集約される."""
        meetings = [_make_meeting()]
        mock_speech_service.fetch_meetings.return_value = meetings
        mock_import_usecase.execute.return_value = ImportKokkaiSpeechesOutputDTO(
            total_speeches_imported=3,
            errors=["Conference 解決に失敗"],
        )

        input_dto = BatchImportKokkaiSpeechesInputDTO(
            session_from=213, session_to=213, sleep_interval=0.0
        )
        result = await usecase.execute(input_dto)

        assert len(result.errors) == 1
        assert "Conference 解決に失敗" in result.errors[0]

    @pytest.mark.asyncio()
    async def test_session_progress_tracked(
        self,
        usecase: BatchImportKokkaiSpeechesUseCase,
        mock_speech_service: AsyncMock,
        mock_import_usecase: AsyncMock,
    ) -> None:
        """異なる回次の会議で回次ごとの集計が正しく記録される."""
        meetings = [
            _make_meeting(issue_id="s212_m1", session=212, date="2025-01-10"),
            _make_meeting(issue_id="s212_m2", session=212, date="2025-01-11"),
            _make_meeting(issue_id="s213_m1", session=213, date="2025-04-01"),
        ]
        mock_speech_service.fetch_meetings.return_value = meetings
        mock_import_usecase.execute.side_effect = [
            ImportKokkaiSpeechesOutputDTO(total_speeches_imported=10),
            ImportKokkaiSpeechesOutputDTO(
                total_speeches_imported=0, total_speeches_skipped=5
            ),
            ImportKokkaiSpeechesOutputDTO(total_speeches_imported=8),
        ]

        input_dto = BatchImportKokkaiSpeechesInputDTO(
            session_from=212, session_to=213, sleep_interval=0.0
        )
        result = await usecase.execute(input_dto)

        assert len(result.session_progress) == 2

        # 回次212: 2件処理、1件スキップ、10件インポート
        sp212 = result.session_progress[0]
        assert sp212.session == 212
        assert sp212.meetings_processed == 2
        assert sp212.meetings_skipped == 1
        assert sp212.speeches_imported == 10
        assert sp212.speeches_skipped == 5

        # 回次213: 1件処理、0件スキップ、8件インポート
        sp213 = result.session_progress[1]
        assert sp213.session == 213
        assert sp213.meetings_processed == 1
        assert sp213.meetings_skipped == 0
        assert sp213.speeches_imported == 8

    @pytest.mark.asyncio()
    async def test_failed_meetings_recorded(
        self,
        usecase: BatchImportKokkaiSpeechesUseCase,
        mock_speech_service: AsyncMock,
        mock_import_usecase: AsyncMock,
    ) -> None:
        """エラー会議の情報がFailedMeetingInfoに記録される."""
        meetings = [
            _make_meeting(issue_id="ok1", date="2025-04-01"),
            _make_meeting(issue_id="fail1", date="2025-04-02"),
            _make_meeting(issue_id="ok2", date="2025-04-03"),
        ]
        mock_speech_service.fetch_meetings.return_value = meetings
        mock_import_usecase.execute.side_effect = [
            ImportKokkaiSpeechesOutputDTO(total_speeches_imported=5),
            RuntimeError("API接続エラー"),
            ImportKokkaiSpeechesOutputDTO(total_speeches_imported=3),
        ]

        input_dto = BatchImportKokkaiSpeechesInputDTO(
            session_from=213, session_to=213, sleep_interval=0.0
        )
        result = await usecase.execute(input_dto)

        assert len(result.failed_meetings) == 1
        failed = result.failed_meetings[0]
        assert failed.issue_id == "fail1"
        assert failed.session == 213
        assert failed.name_of_house == "衆議院"
        assert failed.name_of_meeting == "本会議"
        assert failed.date == "2025-04-02"
        assert "API接続エラー" in failed.error_message
