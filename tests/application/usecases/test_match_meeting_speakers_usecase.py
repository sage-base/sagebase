"""MatchMeetingSpeakersUseCase のユニットテスト."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock

import pytest

from src.application.dtos.match_meeting_speakers_dto import (
    MatchMeetingSpeakersInputDTO,
)
from src.application.usecases.match_meeting_speakers_usecase import (
    MatchMeetingSpeakersUseCase,
)
from src.domain.entities.conference_member import ConferenceMember
from src.domain.entities.conversation import Conversation
from src.domain.entities.meeting import Meeting
from src.domain.entities.minutes import Minutes
from src.domain.entities.politician import Politician
from src.domain.entities.speaker import Speaker
from src.domain.repositories.conference_member_repository import (
    ConferenceMemberRepository,
)
from src.domain.repositories.conversation_repository import ConversationRepository
from src.domain.repositories.meeting_repository import MeetingRepository
from src.domain.repositories.minutes_repository import MinutesRepository
from src.domain.repositories.politician_repository import PoliticianRepository
from src.domain.repositories.speaker_repository import SpeakerRepository
from src.domain.services.speaker_politician_matching_service import (
    SpeakerPoliticianMatchingService,
)


@pytest.fixture()
def mock_repos() -> dict[str, AsyncMock]:
    """モックリポジトリ群を生成."""
    return {
        "meeting_repository": AsyncMock(spec=MeetingRepository),
        "minutes_repository": AsyncMock(spec=MinutesRepository),
        "conversation_repository": AsyncMock(spec=ConversationRepository),
        "speaker_repository": AsyncMock(spec=SpeakerRepository),
        "conference_member_repository": AsyncMock(spec=ConferenceMemberRepository),
        "politician_repository": AsyncMock(spec=PoliticianRepository),
    }


@pytest.fixture()
def usecase(mock_repos: dict[str, AsyncMock]) -> MatchMeetingSpeakersUseCase:
    """ユースケースインスタンスを生成."""
    return MatchMeetingSpeakersUseCase(
        **mock_repos,
        matching_service=SpeakerPoliticianMatchingService(),
    )


def _setup_meeting(mock_repos: dict[str, AsyncMock]) -> Meeting:
    """Meetingモックをセットアップ."""
    meeting = Meeting(conference_id=10, date=date(2025, 4, 23), name="テスト会議", id=1)
    mock_repos["meeting_repository"].get_by_id.return_value = meeting
    return meeting


def _setup_minutes(mock_repos: dict[str, AsyncMock]) -> Minutes:
    """Minutesモックをセットアップ."""
    minutes = Minutes(meeting_id=1, id=100)
    mock_repos["minutes_repository"].get_by_meeting.return_value = minutes
    return minutes


def _setup_conversations(
    mock_repos: dict[str, AsyncMock], speaker_ids: list[int]
) -> list[Conversation]:
    """Conversationsモックをセットアップ."""
    conversations = [
        Conversation(
            comment=f"発言{i}",
            sequence_number=i,
            minutes_id=100,
            speaker_id=sid,
            id=i,
        )
        for i, sid in enumerate(speaker_ids, start=1)
    ]
    mock_repos["conversation_repository"].get_by_minutes.return_value = conversations
    return conversations


def _setup_speakers(mock_repos: dict[str, AsyncMock], speakers: list[Speaker]) -> None:
    """Speakersモックをセットアップ."""
    mock_repos["speaker_repository"].get_by_ids.return_value = speakers
    mock_repos["speaker_repository"].update.return_value = (
        speakers[0] if speakers else None
    )


def _setup_candidates(
    mock_repos: dict[str, AsyncMock],
    members: list[ConferenceMember],
    politicians: list[Politician],
) -> None:
    """ConferenceMember + Politicianモックをセットアップ."""
    mock_repos[
        "conference_member_repository"
    ].get_by_conference_at_date.return_value = members
    mock_repos["politician_repository"].get_by_ids.return_value = politicians


class TestMatchMeetingSpeakersUseCase:
    """MatchMeetingSpeakersUseCase のテスト."""

    @pytest.mark.asyncio
    async def test_exact_name_match_updates_speaker(
        self, usecase: MatchMeetingSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """完全一致マッチで Speaker.politician_id が更新される."""
        _setup_meeting(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])
        _setup_speakers(
            mock_repos,
            [Speaker(name="岸田文雄", name_yomi="きしだふみお", id=1)],
        )
        _setup_candidates(
            mock_repos,
            [
                ConferenceMember(
                    politician_id=100,
                    conference_id=10,
                    start_date=date(2024, 1, 1),
                    id=1,
                )
            ],
            [
                Politician(
                    name="岸田文雄",
                    prefecture="",
                    district="",
                    furigana="きしだふみお",
                    id=100,
                )
            ],
        )

        result = await usecase.execute(MatchMeetingSpeakersInputDTO(meeting_id=1))

        assert result.success is True
        assert result.matched_count == 1
        assert len(result.results) == 1
        assert result.results[0].politician_id == 100
        assert result.results[0].confidence == 1.0
        assert result.results[0].updated is True
        mock_repos["speaker_repository"].update.assert_called_once()

    @pytest.mark.asyncio
    async def test_yomi_match_updates_speaker(
        self, usecase: MatchMeetingSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """ふりがなマッチで Speaker.politician_id が更新される.

        Speaker名（漢字表記）が候補と異なるが、ふりがなが一致するケース。
        """
        _setup_meeting(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])
        # 漢字表記が異なる（旧字体等を想定）がふりがなは一致
        _setup_speakers(
            mock_repos,
            [Speaker(name="菅義偉（別表記）", name_yomi="すがよしひで", id=1)],
        )
        _setup_candidates(
            mock_repos,
            [
                ConferenceMember(
                    politician_id=200,
                    conference_id=10,
                    start_date=date(2024, 1, 1),
                    id=1,
                )
            ],
            [
                Politician(
                    name="菅義偉",
                    prefecture="",
                    district="",
                    furigana="すがよしひで",
                    id=200,
                )
            ],
        )

        result = await usecase.execute(MatchMeetingSpeakersInputDTO(meeting_id=1))

        assert result.success is True
        assert result.matched_count == 1
        # 漢字名が不一致のためふりがなマッチ（confidence 0.9）
        assert result.results[0].confidence == 0.9
        assert result.results[0].updated is True

    @pytest.mark.asyncio
    async def test_low_confidence_does_not_update(
        self, usecase: MatchMeetingSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """閾値未満の confidence では Speaker.politician_id を更新しない."""
        _setup_meeting(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])
        _setup_speakers(
            mock_repos,
            [Speaker(name="全く異なる名前", id=1)],
        )
        _setup_candidates(
            mock_repos,
            [
                ConferenceMember(
                    politician_id=100,
                    conference_id=10,
                    start_date=date(2024, 1, 1),
                    id=1,
                )
            ],
            [Politician(name="岸田文雄", prefecture="", district="", id=100)],
        )

        result = await usecase.execute(MatchMeetingSpeakersInputDTO(meeting_id=1))

        assert result.success is True
        assert result.matched_count == 0
        assert result.results[0].updated is False
        mock_repos["speaker_repository"].update.assert_not_called()

    @pytest.mark.asyncio
    async def test_already_matched_speaker_skipped(
        self, usecase: MatchMeetingSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """既にマッチ済みの Speaker はスキップされる."""
        _setup_meeting(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])
        _setup_speakers(
            mock_repos,
            [Speaker(name="岸田文雄", politician_id=100, id=1)],
        )
        _setup_candidates(
            mock_repos,
            [
                ConferenceMember(
                    politician_id=100,
                    conference_id=10,
                    start_date=date(2024, 1, 1),
                    id=1,
                )
            ],
            [Politician(name="岸田文雄", prefecture="", district="", id=100)],
        )

        result = await usecase.execute(MatchMeetingSpeakersInputDTO(meeting_id=1))

        assert result.success is True
        assert result.skipped_count == 1
        assert result.matched_count == 0
        mock_repos["speaker_repository"].update.assert_not_called()

    @pytest.mark.asyncio
    async def test_manually_verified_speaker_skipped(
        self, usecase: MatchMeetingSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """手動検証済みの Speaker はスキップされる."""
        _setup_meeting(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])
        _setup_speakers(
            mock_repos,
            [Speaker(name="岸田文雄", is_manually_verified=True, id=1)],
        )
        _setup_candidates(
            mock_repos,
            [
                ConferenceMember(
                    politician_id=100,
                    conference_id=10,
                    start_date=date(2024, 1, 1),
                    id=1,
                )
            ],
            [Politician(name="岸田文雄", prefecture="", district="", id=100)],
        )

        result = await usecase.execute(MatchMeetingSpeakersInputDTO(meeting_id=1))

        assert result.success is True
        assert result.skipped_count == 1
        assert result.matched_count == 0

    @pytest.mark.asyncio
    async def test_meeting_not_found(
        self, usecase: MatchMeetingSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """Meeting が見つからない場合、エラーを返す."""
        mock_repos["meeting_repository"].get_by_id.return_value = None

        result = await usecase.execute(MatchMeetingSpeakersInputDTO(meeting_id=999))

        assert result.success is False
        assert "見つかりません" in result.message

    @pytest.mark.asyncio
    async def test_no_minutes(
        self, usecase: MatchMeetingSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """議事録が無い場合、空結果を返す."""
        _setup_meeting(mock_repos)
        mock_repos["minutes_repository"].get_by_meeting.return_value = None

        result = await usecase.execute(MatchMeetingSpeakersInputDTO(meeting_id=1))

        assert result.success is True
        assert "議事録" in result.message

    @pytest.mark.asyncio
    async def test_no_conversations(
        self, usecase: MatchMeetingSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """発言が無い場合、空結果を返す."""
        _setup_meeting(mock_repos)
        _setup_minutes(mock_repos)
        mock_repos["conversation_repository"].get_by_minutes.return_value = []

        result = await usecase.execute(MatchMeetingSpeakersInputDTO(meeting_id=1))

        assert result.success is True
        assert "発言" in result.message

    @pytest.mark.asyncio
    async def test_no_conference_members(
        self, usecase: MatchMeetingSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """ConferenceMember が無い場合、候補なしメッセージを返す."""
        _setup_meeting(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])
        _setup_speakers(
            mock_repos,
            [Speaker(name="岸田文雄", id=1)],
        )
        mock_repos[
            "conference_member_repository"
        ].get_by_conference_at_date.return_value = []

        result = await usecase.execute(MatchMeetingSpeakersInputDTO(meeting_id=1))

        assert result.success is True
        assert "候補" in result.message

    @pytest.mark.asyncio
    async def test_multiple_speakers_mixed_results(
        self, usecase: MatchMeetingSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """複数発言者で一部マッチ・一部未マッチの混合結果."""
        _setup_meeting(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1, 2, 3])
        _setup_speakers(
            mock_repos,
            [
                Speaker(name="岸田文雄", id=1),
                Speaker(name="不明な人物", id=2),
                Speaker(name="石破茂", politician_id=300, id=3),  # 既にマッチ済み
            ],
        )
        _setup_candidates(
            mock_repos,
            [
                ConferenceMember(
                    politician_id=100,
                    conference_id=10,
                    start_date=date(2024, 1, 1),
                    id=1,
                ),
                ConferenceMember(
                    politician_id=200,
                    conference_id=10,
                    start_date=date(2024, 1, 1),
                    id=2,
                ),
            ],
            [
                Politician(name="岸田文雄", prefecture="", district="", id=100),
                Politician(name="河野太郎", prefecture="", district="", id=200),
            ],
        )

        result = await usecase.execute(MatchMeetingSpeakersInputDTO(meeting_id=1))

        assert result.success is True
        assert result.total_speakers == 3
        assert result.skipped_count == 1  # 石破茂は既にマッチ済み
        assert result.matched_count == 1  # 岸田文雄のみマッチ
        assert len(result.results) == 2  # 未マッチ対象は2人

    @pytest.mark.asyncio
    async def test_surname_only_match(
        self, usecase: MatchMeetingSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """姓のみ一致（同姓1人）でマッチする."""
        _setup_meeting(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])
        _setup_speakers(
            mock_repos,
            [Speaker(name="岸田", id=1)],
        )
        _setup_candidates(
            mock_repos,
            [
                ConferenceMember(
                    politician_id=100,
                    conference_id=10,
                    start_date=date(2024, 1, 1),
                    id=1,
                ),
                ConferenceMember(
                    politician_id=200,
                    conference_id=10,
                    start_date=date(2024, 1, 1),
                    id=2,
                ),
            ],
            [
                Politician(name="岸田文雄", prefecture="", district="", id=100),
                Politician(name="石破茂", prefecture="", district="", id=200),
            ],
        )

        result = await usecase.execute(
            MatchMeetingSpeakersInputDTO(meeting_id=1, confidence_threshold=0.8)
        )

        assert result.success is True
        assert result.matched_count == 1
        assert result.results[0].politician_id == 100
        assert result.results[0].confidence == 0.8

    @pytest.mark.asyncio
    async def test_custom_confidence_threshold(
        self, usecase: MatchMeetingSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """高い閾値を設定すると姓のみ一致（0.8）ではマッチしない."""
        _setup_meeting(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])
        _setup_speakers(
            mock_repos,
            [Speaker(name="岸田", id=1)],
        )
        _setup_candidates(
            mock_repos,
            [
                ConferenceMember(
                    politician_id=100,
                    conference_id=10,
                    start_date=date(2024, 1, 1),
                    id=1,
                )
            ],
            [Politician(name="岸田文雄", prefecture="", district="", id=100)],
        )

        result = await usecase.execute(
            MatchMeetingSpeakersInputDTO(meeting_id=1, confidence_threshold=0.9)
        )

        assert result.success is True
        assert result.matched_count == 0
        assert result.results[0].updated is False

    @pytest.mark.asyncio
    async def test_repository_exception_returns_error(
        self, usecase: MatchMeetingSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """リポジトリで例外が発生した場合、success=False を返す."""
        mock_repos["meeting_repository"].get_by_id.side_effect = RuntimeError(
            "DB接続エラー"
        )

        result = await usecase.execute(MatchMeetingSpeakersInputDTO(meeting_id=1))

        assert result.success is False
        assert "エラー" in result.message

    @pytest.mark.asyncio
    async def test_meeting_without_date_returns_error(
        self, usecase: MatchMeetingSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """日付のない Meeting の場合、エラーを返す."""
        meeting = Meeting(conference_id=10, date=None, name="日付なし会議", id=1)
        mock_repos["meeting_repository"].get_by_id.return_value = meeting

        result = await usecase.execute(MatchMeetingSpeakersInputDTO(meeting_id=1))

        assert result.success is False
        assert "日付" in result.message
