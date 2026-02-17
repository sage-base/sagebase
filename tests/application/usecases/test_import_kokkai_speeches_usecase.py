"""ImportKokkaiSpeechesUseCase のユニットテスト."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.dtos.kokkai_speech_dto import (
    ImportKokkaiSpeechesInputDTO,
    KokkaiSpeechDTO,
)
from src.application.usecases.import_kokkai_speeches_usecase import (
    ImportKokkaiSpeechesUseCase,
)
from src.domain.entities.conference import Conference
from src.domain.entities.governing_body import GoverningBody
from src.domain.entities.meeting import Meeting
from src.domain.entities.minutes import Minutes
from src.domain.entities.speaker import Speaker
from src.domain.services.interfaces.kokkai_speech_service import IKokkaiSpeechService
from src.domain.services.interfaces.unit_of_work import IUnitOfWork


def _make_speech(**overrides: object) -> KokkaiSpeechDTO:
    """テスト用KokkaiSpeechDTOを生成."""
    defaults = {
        "speech_id": "121705253X00320250423001",
        "issue_id": "121705253X00320250423",
        "session": 213,
        "name_of_house": "衆議院",
        "name_of_meeting": "本会議",
        "issue": "第3号",
        "date": "2025-04-23",
        "speech_order": 1,
        "speaker": "岸田文雄君",
        "speaker_yomi": "きしだふみおくん",
        "speech": "テスト発言内容です。",
        "speech_url": "https://kokkai.ndl.go.jp/speech/1",
        "meeting_url": "https://kokkai.ndl.go.jp/meeting/1",
        "pdf_url": "https://kokkai.ndl.go.jp/pdf/1",
    }
    defaults.update(overrides)
    return KokkaiSpeechDTO(**defaults)  # type: ignore[arg-type]


@pytest.fixture()
def mock_speech_service() -> AsyncMock:
    """モックKokkaiSpeechServiceを生成."""
    return AsyncMock(spec=IKokkaiSpeechService)


@pytest.fixture()
def mock_uow() -> AsyncMock:
    """モックUnitOfWorkを生成."""
    uow = AsyncMock(spec=IUnitOfWork)
    uow.meeting_repository = AsyncMock()
    uow.minutes_repository = AsyncMock()
    uow.conversation_repository = AsyncMock()
    uow.speaker_repository = AsyncMock()
    uow.conference_repository = AsyncMock()
    uow.governing_body_repository = AsyncMock()
    uow.commit = AsyncMock()
    uow.rollback = AsyncMock()
    return uow


@pytest.fixture()
def usecase(
    mock_speech_service: AsyncMock,
    mock_uow: AsyncMock,
) -> ImportKokkaiSpeechesUseCase:
    """ユースケースインスタンスを生成."""
    return ImportKokkaiSpeechesUseCase(
        kokkai_speech_service=mock_speech_service,
        unit_of_work_factory=lambda: mock_uow,
    )


def _setup_governing_body(mock_uow: AsyncMock) -> None:
    """GoverningBody "国会" のモックをセットアップ."""
    gb = GoverningBody(name="国会", type="国", id=1)
    mock_uow.governing_body_repository.get_by_name_and_type.return_value = gb


def _setup_conference(mock_uow: AsyncMock, conference_id: int = 10) -> None:
    """Conference のモックをセットアップ."""
    conf = Conference(name="衆議院本会議", governing_body_id=1, id=conference_id)
    mock_uow.conference_repository.get_by_name_and_governing_body.return_value = conf


def _setup_no_existing_meeting(mock_uow: AsyncMock) -> None:
    """既存のMeetingが存在しない状態をセットアップ."""
    mock_uow.meeting_repository.get_by_url.return_value = None
    meeting = Meeting(conference_id=10, date=None, url="", name="", id=100)
    mock_uow.meeting_repository.create.return_value = meeting


def _setup_no_existing_minutes(mock_uow: AsyncMock) -> None:
    """既存のMinutesが存在しない状態をセットアップ."""
    mock_uow.minutes_repository.get_by_meeting.return_value = None
    minutes = Minutes(meeting_id=100, id=200)
    mock_uow.minutes_repository.create.return_value = minutes


def _setup_speaker_not_found(mock_uow: AsyncMock) -> None:
    """Speakerが未登録の状態をセットアップ."""
    mock_uow.speaker_repository.find_by_name.return_value = None
    mock_uow.speaker_repository.create.return_value = Speaker(name="岸田文雄", id=50)


class TestExecute:
    """execute メソッドのテスト."""

    @pytest.mark.asyncio
    async def test_import_new_meeting_speeches(
        self,
        usecase: ImportKokkaiSpeechesUseCase,
        mock_speech_service: AsyncMock,
        mock_uow: AsyncMock,
    ) -> None:
        speeches = [
            _make_speech(speech_order=1, speaker="岸田文雄君"),
            _make_speech(speech_order=2, speaker="河野太郎君"),
        ]
        mock_speech_service.fetch_speeches.return_value = speeches
        _setup_governing_body(mock_uow)
        _setup_conference(mock_uow)
        _setup_no_existing_meeting(mock_uow)
        _setup_no_existing_minutes(mock_uow)
        _setup_speaker_not_found(mock_uow)
        mock_uow.conversation_repository.bulk_create.return_value = [
            MagicMock(id=1),
            MagicMock(id=2),
        ]

        input_dto = ImportKokkaiSpeechesInputDTO(issue_id="121705253X00320250423")
        result = await usecase.execute(input_dto)

        assert result.total_speeches_imported == 2
        assert result.total_meetings_created == 1
        assert result.errors == []
        mock_uow.meeting_repository.create.assert_called_once()
        mock_uow.conversation_repository.bulk_create.assert_called_once()

        # bulk_createに渡されたConversationの中身を検証
        conversations = mock_uow.conversation_repository.bulk_create.call_args[0][0]
        assert len(conversations) == 2
        assert conversations[0].comment == "テスト発言内容です。"
        assert conversations[0].sequence_number == 1
        assert conversations[0].speaker_name == "岸田文雄"
        assert conversations[0].is_manually_verified is True
        assert conversations[0].minutes_id == 200
        assert conversations[1].sequence_number == 2
        assert conversations[1].speaker_name == "河野太郎"

    @pytest.mark.asyncio
    async def test_skip_existing_meeting_speeches(
        self,
        usecase: ImportKokkaiSpeechesUseCase,
        mock_speech_service: AsyncMock,
        mock_uow: AsyncMock,
    ) -> None:
        speeches = [_make_speech()]
        mock_speech_service.fetch_speeches.return_value = speeches
        _setup_governing_body(mock_uow)

        existing_meeting = Meeting(
            conference_id=10,
            date=None,
            url="https://kokkai.ndl.go.jp/meeting/1",
            name="",
            id=100,
        )
        mock_uow.meeting_repository.get_by_url.return_value = existing_meeting
        mock_uow.minutes_repository.get_by_meeting.return_value = Minutes(
            meeting_id=100, id=200
        )
        mock_uow.conversation_repository.get_by_minutes.return_value = [MagicMock(id=1)]

        input_dto = ImportKokkaiSpeechesInputDTO(issue_id="121705253X00320250423")
        result = await usecase.execute(input_dto)

        assert result.total_speeches_imported == 0
        assert result.total_speeches_skipped == 1
        assert result.total_meetings_created == 0
        mock_uow.meeting_repository.create.assert_not_called()
        mock_uow.conversation_repository.bulk_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_multiple_meetings_by_date_range(
        self,
        usecase: ImportKokkaiSpeechesUseCase,
        mock_speech_service: AsyncMock,
        mock_uow: AsyncMock,
    ) -> None:
        speeches = [
            _make_speech(
                issue_id="ISSUE_A",
                speech_order=1,
                meeting_url="https://kokkai.ndl.go.jp/meeting/A",
            ),
            _make_speech(
                issue_id="ISSUE_B",
                speech_order=1,
                date="2025-04-24",
                meeting_url="https://kokkai.ndl.go.jp/meeting/B",
            ),
        ]
        mock_speech_service.fetch_speeches.return_value = speeches
        _setup_governing_body(mock_uow)
        _setup_conference(mock_uow)
        _setup_speaker_not_found(mock_uow)

        mock_uow.meeting_repository.get_by_url.return_value = None
        meeting_counter = {"count": 0}

        async def create_meeting(m: Meeting) -> Meeting:
            meeting_counter["count"] += 1
            m.id = 100 + meeting_counter["count"]
            return m

        mock_uow.meeting_repository.create.side_effect = create_meeting

        minutes_counter = {"count": 0}

        async def create_minutes(m: Minutes) -> Minutes:
            minutes_counter["count"] += 1
            m.id = 200 + minutes_counter["count"]
            return m

        mock_uow.minutes_repository.get_by_meeting.return_value = None
        mock_uow.minutes_repository.create.side_effect = create_minutes
        mock_uow.conversation_repository.bulk_create.return_value = [MagicMock(id=1)]

        input_dto = ImportKokkaiSpeechesInputDTO(
            name_of_house="衆議院",
            from_date="2025-04-23",
            until_date="2025-04-24",
        )
        result = await usecase.execute(input_dto)

        assert result.total_meetings_created == 2
        assert result.total_speeches_imported == 2
        assert result.errors == []

    @pytest.mark.asyncio
    async def test_empty_api_result(
        self,
        usecase: ImportKokkaiSpeechesUseCase,
        mock_speech_service: AsyncMock,
    ) -> None:
        mock_speech_service.fetch_speeches.return_value = []

        input_dto = ImportKokkaiSpeechesInputDTO(issue_id="121705253X00320250423")
        result = await usecase.execute(input_dto)

        assert result.total_speeches_imported == 0
        assert result.total_meetings_created == 0

    @pytest.mark.asyncio
    async def test_error_when_governing_body_not_found(
        self,
        usecase: ImportKokkaiSpeechesUseCase,
        mock_speech_service: AsyncMock,
        mock_uow: AsyncMock,
    ) -> None:
        mock_speech_service.fetch_speeches.return_value = [_make_speech()]
        mock_uow.governing_body_repository.get_by_name_and_type.return_value = None

        input_dto = ImportKokkaiSpeechesInputDTO(issue_id="121705253X00320250423")
        result = await usecase.execute(input_dto)

        assert len(result.errors) == 1

    @pytest.mark.asyncio
    async def test_update_speaker_name_yomi(
        self,
        usecase: ImportKokkaiSpeechesUseCase,
        mock_speech_service: AsyncMock,
        mock_uow: AsyncMock,
    ) -> None:
        speeches = [_make_speech()]
        mock_speech_service.fetch_speeches.return_value = speeches
        _setup_governing_body(mock_uow)
        _setup_conference(mock_uow)
        _setup_no_existing_meeting(mock_uow)
        _setup_no_existing_minutes(mock_uow)
        mock_uow.conversation_repository.bulk_create.return_value = [MagicMock(id=1)]

        existing_speaker = Speaker(name="岸田文雄", id=50, name_yomi=None)
        mock_uow.speaker_repository.find_by_name.return_value = existing_speaker
        mock_uow.speaker_repository.update.return_value = existing_speaker

        input_dto = ImportKokkaiSpeechesInputDTO(issue_id="121705253X00320250423")
        await usecase.execute(input_dto)

        mock_uow.speaker_repository.update.assert_called_once()
        updated = mock_uow.speaker_repository.update.call_args[0][0]
        assert updated.name_yomi == "きしだふみお"

    @pytest.mark.asyncio
    async def test_no_update_when_name_yomi_exists(
        self,
        usecase: ImportKokkaiSpeechesUseCase,
        mock_speech_service: AsyncMock,
        mock_uow: AsyncMock,
    ) -> None:
        speeches = [_make_speech()]
        mock_speech_service.fetch_speeches.return_value = speeches
        _setup_governing_body(mock_uow)
        _setup_conference(mock_uow)
        _setup_no_existing_meeting(mock_uow)
        _setup_no_existing_minutes(mock_uow)
        mock_uow.conversation_repository.bulk_create.return_value = [MagicMock(id=1)]

        existing_speaker = Speaker(name="岸田文雄", id=50, name_yomi="きしだふみお")
        mock_uow.speaker_repository.find_by_name.return_value = existing_speaker

        input_dto = ImportKokkaiSpeechesInputDTO(issue_id="121705253X00320250423")
        await usecase.execute(input_dto)

        mock_uow.speaker_repository.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_new_conference(
        self,
        usecase: ImportKokkaiSpeechesUseCase,
        mock_speech_service: AsyncMock,
        mock_uow: AsyncMock,
    ) -> None:
        speeches = [_make_speech(name_of_meeting="特別委員会")]
        mock_speech_service.fetch_speeches.return_value = speeches
        _setup_governing_body(mock_uow)
        _setup_no_existing_meeting(mock_uow)
        _setup_no_existing_minutes(mock_uow)
        _setup_speaker_not_found(mock_uow)
        mock_uow.conversation_repository.bulk_create.return_value = [MagicMock(id=1)]

        mock_uow.conference_repository.get_by_name_and_governing_body.return_value = (
            None
        )
        new_conf = Conference(name="衆議院特別委員会", governing_body_id=1, id=99)
        mock_uow.conference_repository.create.return_value = new_conf

        input_dto = ImportKokkaiSpeechesInputDTO(issue_id="121705253X00320250423")
        result = await usecase.execute(input_dto)

        assert result.errors == []
        mock_uow.conference_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_missing_params_returns_empty(
        self,
        usecase: ImportKokkaiSpeechesUseCase,
        mock_speech_service: AsyncMock,
    ) -> None:
        mock_speech_service.fetch_speeches.return_value = []

        input_dto = ImportKokkaiSpeechesInputDTO()
        result = await usecase.execute(input_dto)

        assert result.total_speeches_imported == 0

    @pytest.mark.asyncio
    async def test_commit_called_on_success(
        self,
        usecase: ImportKokkaiSpeechesUseCase,
        mock_speech_service: AsyncMock,
        mock_uow: AsyncMock,
    ) -> None:
        speeches = [_make_speech()]
        mock_speech_service.fetch_speeches.return_value = speeches
        _setup_governing_body(mock_uow)
        _setup_conference(mock_uow)
        _setup_no_existing_meeting(mock_uow)
        _setup_no_existing_minutes(mock_uow)
        _setup_speaker_not_found(mock_uow)
        mock_uow.conversation_repository.bulk_create.return_value = [MagicMock(id=1)]

        input_dto = ImportKokkaiSpeechesInputDTO(issue_id="121705253X00320250423")
        await usecase.execute(input_dto)

        mock_uow.commit.assert_called_once()
        mock_uow.rollback.assert_not_called()

    @pytest.mark.asyncio
    async def test_rollback_called_on_error(
        self,
        usecase: ImportKokkaiSpeechesUseCase,
        mock_speech_service: AsyncMock,
        mock_uow: AsyncMock,
    ) -> None:
        mock_speech_service.fetch_speeches.side_effect = RuntimeError("API error")

        input_dto = ImportKokkaiSpeechesInputDTO(issue_id="121705253X00320250423")
        with pytest.raises(RuntimeError, match="API error"):
            await usecase.execute(input_dto)

        mock_uow.rollback.assert_called_once()
        mock_uow.commit.assert_not_called()
