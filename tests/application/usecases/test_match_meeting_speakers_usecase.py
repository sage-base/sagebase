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
from src.domain.entities.conference import Conference
from src.domain.entities.conference_member import ConferenceMember
from src.domain.entities.conversation import Conversation
from src.domain.entities.meeting import Meeting
from src.domain.entities.minutes import Minutes
from src.domain.entities.politician import Politician
from src.domain.entities.speaker import Speaker
from src.domain.repositories.conference_member_repository import (
    ConferenceMemberRepository,
)
from src.domain.repositories.conference_repository import ConferenceRepository
from src.domain.repositories.conversation_repository import ConversationRepository
from src.domain.repositories.meeting_repository import MeetingRepository
from src.domain.repositories.minutes_repository import MinutesRepository
from src.domain.repositories.politician_repository import PoliticianRepository
from src.domain.repositories.speaker_repository import SpeakerRepository
from src.domain.services.interfaces.politician_matching_service import (
    IPoliticianMatchingService,
)
from src.domain.services.speaker_classifier import SkipReason
from src.domain.services.speaker_politician_matching_service import (
    SpeakerPoliticianMatchingService,
)
from src.domain.value_objects.politician_match import PoliticianMatch
from src.domain.value_objects.speaker_politician_match_result import MatchMethod


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
        "conference_repository": AsyncMock(spec=ConferenceRepository),
    }


@pytest.fixture()
def usecase(mock_repos: dict[str, AsyncMock]) -> MatchMeetingSpeakersUseCase:
    """ユースケースインスタンスを生成."""
    return MatchMeetingSpeakersUseCase(
        **mock_repos,
        matching_service=SpeakerPoliticianMatchingService(),
    )


@pytest.fixture()
def mock_baml_service() -> AsyncMock:
    """BAMLマッチングサービスのモック."""
    return AsyncMock(spec=IPoliticianMatchingService)


@pytest.fixture()
def usecase_with_baml(
    mock_repos: dict[str, AsyncMock], mock_baml_service: AsyncMock
) -> MatchMeetingSpeakersUseCase:
    """BAMLフォールバック付きユースケースインスタンスを生成."""
    return MatchMeetingSpeakersUseCase(
        **mock_repos,
        matching_service=SpeakerPoliticianMatchingService(),
        baml_matching_service=mock_baml_service,
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
        # 当該 conference も本会議も ConferenceMember が空
        committee = Conference(name="衆議院予算委員会", governing_body_id=1, id=10)
        plenary = Conference(name="衆議院本会議", governing_body_id=1, id=20)
        mock_repos["conference_repository"].get_by_id.return_value = committee
        mock_repos[
            "conference_repository"
        ].get_by_name_and_governing_body.return_value = plenary
        mock_repos[
            "conference_member_repository"
        ].get_by_conference_at_date.side_effect = [
            [],  # 当該 conference → 空
            [],  # 本会議 → 空
        ]

        result = await usecase.execute(MatchMeetingSpeakersInputDTO(meeting_id=1))

        assert result.success is True
        assert "候補" in result.message
        # フォールバックが発動したことを確認
        mock_repos["conference_repository"].get_by_id.assert_called_once_with(10)

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

    @pytest.mark.asyncio
    async def test_fallback_to_plenary_session(
        self, usecase: MatchMeetingSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """ConferenceMember空→本会議のConferenceMemberにフォールバック."""
        _setup_meeting(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])
        _setup_speakers(
            mock_repos,
            [Speaker(name="岸田文雄", name_yomi="きしだふみお", id=1)],
        )

        # 当該conference のConferenceMemberは空
        committee = Conference(name="衆議院予算委員会", governing_body_id=1, id=10)
        plenary = Conference(name="衆議院本会議", governing_body_id=1, id=20)
        mock_repos["conference_repository"].get_by_id.return_value = committee
        mock_repos[
            "conference_repository"
        ].get_by_name_and_governing_body.return_value = plenary

        plenary_members = [
            ConferenceMember(
                politician_id=100,
                conference_id=20,
                start_date=date(2024, 1, 1),
                id=1,
            )
        ]
        mock_repos[
            "conference_member_repository"
        ].get_by_conference_at_date.side_effect = [
            [],  # 当該conference → 空
            plenary_members,  # 本会議 → メンバーあり
        ]
        mock_repos["politician_repository"].get_by_ids.return_value = [
            Politician(
                name="岸田文雄",
                prefecture="",
                district="",
                furigana="きしだふみお",
                id=100,
            )
        ]

        result = await usecase.execute(MatchMeetingSpeakersInputDTO(meeting_id=1))

        assert result.success is True
        assert result.matched_count == 1
        mock_repos["conference_repository"].get_by_id.assert_called_once_with(10)
        mock_repos[
            "conference_repository"
        ].get_by_name_and_governing_body.assert_called_once_with("衆議院本会議", 1)

    @pytest.mark.asyncio
    async def test_no_fallback_when_members_exist(
        self, usecase: MatchMeetingSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """ConferenceMember がある場合、フォールバックは呼ばれない."""
        _setup_meeting(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])
        _setup_speakers(
            mock_repos,
            [Speaker(name="岸田文雄", id=1)],
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

        await usecase.execute(MatchMeetingSpeakersInputDTO(meeting_id=1))

        mock_repos["conference_repository"].get_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_fallback_also_empty(
        self, usecase: MatchMeetingSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """本会議にも ConferenceMember がない場合、候補なしメッセージを返す."""
        _setup_meeting(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])
        _setup_speakers(
            mock_repos,
            [Speaker(name="岸田文雄", id=1)],
        )

        committee = Conference(name="衆議院予算委員会", governing_body_id=1, id=10)
        plenary = Conference(name="衆議院本会議", governing_body_id=1, id=20)
        mock_repos["conference_repository"].get_by_id.return_value = committee
        mock_repos[
            "conference_repository"
        ].get_by_name_and_governing_body.return_value = plenary

        mock_repos[
            "conference_member_repository"
        ].get_by_conference_at_date.side_effect = [
            [],  # 当該conference → 空
            [],  # 本会議 → 空
        ]

        result = await usecase.execute(MatchMeetingSpeakersInputDTO(meeting_id=1))

        assert result.success is True
        assert "候補" in result.message

    @pytest.mark.asyncio
    async def test_no_fallback_without_conference_repository(
        self, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """conference_repository=None の場合、フォールバックは無効."""
        del mock_repos["conference_repository"]
        uc = MatchMeetingSpeakersUseCase(
            **mock_repos,
            matching_service=SpeakerPoliticianMatchingService(),
        )
        _setup_meeting(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])
        _setup_speakers(mock_repos, [Speaker(name="岸田文雄", id=1)])
        mock_repos[
            "conference_member_repository"
        ].get_by_conference_at_date.return_value = []

        result = await uc.execute(MatchMeetingSpeakersInputDTO(meeting_id=1))

        assert result.success is True
        assert "候補" in result.message

    @pytest.mark.asyncio
    async def test_no_fallback_for_plenary_itself(
        self, usecase: MatchMeetingSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """本会議自身では、フォールバックしない."""
        _setup_meeting(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])
        _setup_speakers(mock_repos, [Speaker(name="岸田文雄", id=1)])

        # conference が本会議自身
        plenary = Conference(name="衆議院本会議", governing_body_id=1, id=10)
        mock_repos["conference_repository"].get_by_id.return_value = plenary
        mock_repos[
            "conference_member_repository"
        ].get_by_conference_at_date.return_value = []

        result = await usecase.execute(MatchMeetingSpeakersInputDTO(meeting_id=1))

        assert result.success is True
        assert "候補" in result.message
        # get_by_name_and_governing_body は呼ばれない（自分自身へのフォールバック防止）
        mock_repos[
            "conference_repository"
        ].get_by_name_and_governing_body.assert_not_called()

    @pytest.mark.asyncio
    async def test_fallback_plenary_not_found(
        self, usecase: MatchMeetingSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """本会議が見つからない場合、候補なしメッセージを返す."""
        _setup_meeting(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])
        _setup_speakers(mock_repos, [Speaker(name="岸田文雄", id=1)])

        committee = Conference(name="衆議院予算委員会", governing_body_id=1, id=10)
        mock_repos["conference_repository"].get_by_id.return_value = committee
        mock_repos[
            "conference_repository"
        ].get_by_name_and_governing_body.return_value = None
        mock_repos[
            "conference_member_repository"
        ].get_by_conference_at_date.return_value = []

        result = await usecase.execute(MatchMeetingSpeakersInputDTO(meeting_id=1))

        assert result.success is True
        assert "候補" in result.message


class TestBAMLFallback:
    """BAMLフォールバック関連のテスト."""

    @pytest.mark.asyncio
    async def test_baml_fallback_matches_when_rule_based_fails(
        self,
        usecase_with_baml: MatchMeetingSpeakersUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_baml_service: AsyncMock,
    ) -> None:
        """ルールベース未マッチ時にBAMLフォールバックでマッチ成功する."""
        _setup_meeting(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])
        _setup_speakers(
            mock_repos,
            [Speaker(name="あいまいな名前", id=1)],
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
            [Politician(name="曖昧名前太郎", prefecture="", district="", id=100)],
        )

        mock_baml_service.find_best_match_from_candidates.return_value = (
            PoliticianMatch(
                matched=True,
                politician_id=100,
                politician_name="曖昧名前太郎",
                confidence=0.85,
                reason="BAML判定",
            )
        )

        result = await usecase_with_baml.execute(
            MatchMeetingSpeakersInputDTO(meeting_id=1, enable_baml_fallback=True)
        )

        assert result.success is True
        assert result.matched_count == 1
        assert result.baml_matched_count == 1
        assert result.results[0].match_method == MatchMethod.BAML
        assert result.results[0].updated is True
        mock_baml_service.find_best_match_from_candidates.assert_called_once()

    @pytest.mark.asyncio
    async def test_baml_fallback_disabled_by_default(
        self,
        usecase_with_baml: MatchMeetingSpeakersUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_baml_service: AsyncMock,
    ) -> None:
        """BAMLフォールバック無効時にはBAMLサービスが呼ばれない."""
        _setup_meeting(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])
        _setup_speakers(
            mock_repos,
            [Speaker(name="不明な名前", id=1)],
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

        result = await usecase_with_baml.execute(
            MatchMeetingSpeakersInputDTO(meeting_id=1)
        )

        assert result.success is True
        assert result.matched_count == 0
        assert result.baml_matched_count == 0
        mock_baml_service.find_best_match_from_candidates.assert_not_called()

    @pytest.mark.asyncio
    async def test_baml_error_graceful_handling(
        self,
        usecase_with_baml: MatchMeetingSpeakersUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_baml_service: AsyncMock,
    ) -> None:
        """BAMLサービスでエラーが発生してもバッチは継続する."""
        _setup_meeting(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])
        _setup_speakers(
            mock_repos,
            [Speaker(name="テスト太郎", id=1)],
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

        mock_baml_service.find_best_match_from_candidates.side_effect = RuntimeError(
            "LLMエラー"
        )

        result = await usecase_with_baml.execute(
            MatchMeetingSpeakersInputDTO(meeting_id=1, enable_baml_fallback=True)
        )

        assert result.success is True
        assert result.matched_count == 0
        assert len(result.results) == 1
        assert result.results[0].updated is False

    @pytest.mark.asyncio
    async def test_baml_low_confidence_does_not_update(
        self,
        usecase_with_baml: MatchMeetingSpeakersUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_baml_service: AsyncMock,
    ) -> None:
        """BAMLの信頼度が閾値未満の場合は更新しない."""
        _setup_meeting(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])
        _setup_speakers(
            mock_repos,
            [Speaker(name="不明太郎", id=1)],
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

        mock_baml_service.find_best_match_from_candidates.return_value = (
            PoliticianMatch(
                matched=False,
                confidence=0.5,
                reason="低信頼度",
            )
        )

        result = await usecase_with_baml.execute(
            MatchMeetingSpeakersInputDTO(meeting_id=1, enable_baml_fallback=True)
        )

        assert result.success is True
        assert result.matched_count == 0
        assert result.baml_matched_count == 0
        assert result.results[0].updated is False

    @pytest.mark.asyncio
    async def test_role_name_mapping_passed_to_baml(
        self,
        usecase_with_baml: MatchMeetingSpeakersUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_baml_service: AsyncMock,
    ) -> None:
        """role_name_mappingsがBAMLサービスに渡される."""
        _setup_meeting(mock_repos)
        minutes = Minutes(
            meeting_id=1,
            id=100,
            role_name_mappings={"議長": "大島理森"},
        )
        mock_repos["minutes_repository"].get_by_meeting.return_value = minutes
        _setup_conversations(mock_repos, [1])
        _setup_speakers(
            mock_repos,
            [Speaker(name="あいまい名前", id=1)],
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
            [Politician(name="大島理森", prefecture="", district="", id=100)],
        )

        mock_baml_service.find_best_match_from_candidates.return_value = (
            PoliticianMatch(
                matched=True,
                politician_id=100,
                politician_name="大島理森",
                confidence=0.9,
                reason="マッピング解決",
            )
        )

        result = await usecase_with_baml.execute(
            MatchMeetingSpeakersInputDTO(meeting_id=1, enable_baml_fallback=True)
        )

        call_kwargs = mock_baml_service.find_best_match_from_candidates.call_args
        assert call_kwargs.kwargs["role_name_mappings"] == {"議長": "大島理森"}
        assert result.matched_count == 1
        assert result.baml_matched_count == 1


class TestNonPoliticianClassification:
    """非政治家分類のテスト."""

    @pytest.mark.asyncio
    async def test_role_only_speaker_classified(
        self, usecase: MatchMeetingSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """役職のみの発言者が非政治家として分類される."""
        _setup_meeting(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])
        _setup_speakers(
            mock_repos,
            [Speaker(name="議長", id=1)],
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
        assert result.non_politician_count == 1
        assert result.results[0].skip_reason == SkipReason.ROLE_ONLY

    @pytest.mark.asyncio
    async def test_reference_person_classified(
        self, usecase: MatchMeetingSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """参考人が非政治家として分類される."""
        _setup_meeting(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])
        _setup_speakers(
            mock_repos,
            [Speaker(name="参考人", id=1)],
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

        assert result.non_politician_count == 1
        assert result.results[0].skip_reason == SkipReason.REFERENCE_PERSON

    @pytest.mark.asyncio
    async def test_government_official_classified(
        self, usecase: MatchMeetingSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """政府委員が非政治家として分類される."""
        _setup_meeting(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])
        _setup_speakers(
            mock_repos,
            [Speaker(name="政府委員", id=1)],
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

        assert result.non_politician_count == 1
        assert result.results[0].skip_reason == SkipReason.GOVERNMENT_OFFICIAL

    @pytest.mark.asyncio
    async def test_non_politician_is_politician_flag_set_false(
        self, usecase: MatchMeetingSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """非政治家分類時にis_politician=Trueの場合、Falseに更新される."""
        _setup_meeting(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])
        _setup_speakers(
            mock_repos,
            [Speaker(name="委員長", is_politician=True, id=1)],
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

        assert result.non_politician_count == 1
        mock_repos["speaker_repository"].update.assert_called_once()
        call_args = mock_repos["speaker_repository"].update.call_args
        updated_speaker = call_args[0][0]
        assert updated_speaker.is_politician is False

    @pytest.mark.asyncio
    async def test_non_politician_already_false_no_update(
        self, usecase: MatchMeetingSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """is_politician=Falseの非政治家はupdateが呼ばれない."""
        _setup_meeting(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])
        _setup_speakers(
            mock_repos,
            [Speaker(name="委員長", is_politician=False, id=1)],
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

        assert result.non_politician_count == 1
        mock_repos["speaker_repository"].update.assert_not_called()


class TestIsPoliticianFlag:
    """is_politicianフラグ更新のテスト."""

    @pytest.mark.asyncio
    async def test_match_sets_is_politician_true(
        self, usecase: MatchMeetingSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """ルールベースマッチ成功時にis_politician=Trueが設定される."""
        _setup_meeting(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])
        speaker = Speaker(name="岸田文雄", is_politician=False, id=1)
        _setup_speakers(mock_repos, [speaker])
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

        await usecase.execute(MatchMeetingSpeakersInputDTO(meeting_id=1))

        call_args = mock_repos["speaker_repository"].update.call_args
        updated_speaker = call_args[0][0]
        assert updated_speaker.is_politician is True
        assert updated_speaker.politician_id == 100

    @pytest.mark.asyncio
    async def test_baml_match_sets_is_politician_true(
        self,
        usecase_with_baml: MatchMeetingSpeakersUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_baml_service: AsyncMock,
    ) -> None:
        """BAMLマッチ成功時にis_politician=Trueが設定される."""
        _setup_meeting(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])
        speaker = Speaker(name="あいまい名前", is_politician=False, id=1)
        _setup_speakers(mock_repos, [speaker])
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

        mock_baml_service.find_best_match_from_candidates.return_value = (
            PoliticianMatch(
                matched=True,
                politician_id=100,
                politician_name="岸田文雄",
                confidence=0.9,
                reason="BAML判定",
            )
        )

        await usecase_with_baml.execute(
            MatchMeetingSpeakersInputDTO(meeting_id=1, enable_baml_fallback=True)
        )

        call_args = mock_repos["speaker_repository"].update.call_args
        updated_speaker = call_args[0][0]
        assert updated_speaker.is_politician is True
        assert updated_speaker.politician_id == 100


class TestMixedScenarios:
    """混合シナリオのテスト."""

    @pytest.mark.asyncio
    async def test_mixed_rule_based_non_politician_and_baml(
        self,
        usecase_with_baml: MatchMeetingSpeakersUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_baml_service: AsyncMock,
    ) -> None:
        """ルールベースマッチ + 非政治家分類 + BAMLフォールバックの混合."""
        _setup_meeting(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1, 2, 3])
        _setup_speakers(
            mock_repos,
            [
                Speaker(name="岸田文雄", id=1),  # ルールベースマッチ
                Speaker(name="議長", id=2),  # 非政治家（role_only）
                Speaker(name="あいまい名前", id=3),  # BAMLフォールバック対象
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
                )
            ],
            [Politician(name="岸田文雄", prefecture="", district="", id=100)],
        )

        mock_baml_service.find_best_match_from_candidates.return_value = (
            PoliticianMatch(
                matched=True,
                politician_id=100,
                politician_name="岸田文雄",
                confidence=0.85,
                reason="BAML判定",
            )
        )

        result = await usecase_with_baml.execute(
            MatchMeetingSpeakersInputDTO(meeting_id=1, enable_baml_fallback=True)
        )

        assert result.success is True
        assert result.matched_count == 2  # ルールベース1 + BAML1
        assert result.baml_matched_count == 1
        assert result.non_politician_count == 1
        # BAMLは1回だけ呼ばれる（非政治家はBAMLに渡されない）
        assert mock_baml_service.find_best_match_from_candidates.call_count == 1

    @pytest.mark.asyncio
    async def test_baml_batch_mixed_success_and_failure(
        self,
        usecase_with_baml: MatchMeetingSpeakersUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_baml_service: AsyncMock,
    ) -> None:
        """複数BAMLフォールバック: 1人成功、1人エラーでバッチ継続."""
        _setup_meeting(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1, 2])
        _setup_speakers(
            mock_repos,
            [
                Speaker(name="不明太郎", id=1),
                Speaker(name="不明次郎", id=2),
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
                )
            ],
            [Politician(name="岸田文雄", prefecture="", district="", id=100)],
        )

        # 1人目: BAML成功、2人目: BAMLエラー
        mock_baml_service.find_best_match_from_candidates.side_effect = [
            PoliticianMatch(
                matched=True,
                politician_id=100,
                politician_name="岸田文雄",
                confidence=0.9,
                reason="BAML判定",
            ),
            RuntimeError("LLMエラー"),
        ]

        result = await usecase_with_baml.execute(
            MatchMeetingSpeakersInputDTO(meeting_id=1, enable_baml_fallback=True)
        )

        assert result.success is True
        assert result.matched_count == 1
        assert result.baml_matched_count == 1
        assert len(result.results) == 2
        # 1人目: マッチ成功
        assert result.results[0].updated is True
        assert result.results[0].match_method == MatchMethod.BAML
        # 2人目: エラーだが結果に記録される
        assert result.results[1].updated is False
        assert result.results[1].match_method == MatchMethod.NONE

    @pytest.mark.asyncio
    async def test_all_non_politician_no_baml_called(
        self,
        usecase_with_baml: MatchMeetingSpeakersUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_baml_service: AsyncMock,
    ) -> None:
        """全員が非政治家分類された場合、BAMLは呼ばれない."""
        _setup_meeting(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1, 2])
        _setup_speakers(
            mock_repos,
            [
                Speaker(name="議長", id=1),
                Speaker(name="参考人", id=2),
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
                )
            ],
            [Politician(name="岸田文雄", prefecture="", district="", id=100)],
        )

        result = await usecase_with_baml.execute(
            MatchMeetingSpeakersInputDTO(meeting_id=1, enable_baml_fallback=True)
        )

        assert result.success is True
        assert result.non_politician_count == 2
        assert result.matched_count == 0
        assert result.baml_matched_count == 0
        mock_baml_service.find_best_match_from_candidates.assert_not_called()


class TestHomonymClassification:
    """同姓同名（homonym）分類のテスト."""

    @pytest.mark.asyncio
    async def test_homonym_speaker_without_baml(
        self, usecase: MatchMeetingSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """同姓候補が複数存在しBAML無効時にskip_reason=HOMONYMが設定される."""
        _setup_meeting(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])
        _setup_speakers(
            mock_repos,
            [Speaker(name="田中", id=1)],
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
                Politician(name="田中太郎", prefecture="", district="", id=100),
                Politician(name="田中次郎", prefecture="", district="", id=200),
            ],
        )

        result = await usecase.execute(MatchMeetingSpeakersInputDTO(meeting_id=1))

        assert result.success is True
        assert result.matched_count == 0
        assert len(result.results) == 1
        assert result.results[0].skip_reason == SkipReason.HOMONYM
        assert result.results[0].politician_id is None

    @pytest.mark.asyncio
    async def test_non_homonym_speaker_no_skip_reason(
        self, usecase: MatchMeetingSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """同姓候補が1人のみの場合はhomonymにならず通常マッチする."""
        _setup_meeting(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])
        _setup_speakers(
            mock_repos,
            [Speaker(name="田中", id=1)],
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
                Politician(name="田中太郎", prefecture="", district="", id=100),
                Politician(name="佐藤花子", prefecture="", district="", id=200),
            ],
        )

        result = await usecase.execute(MatchMeetingSpeakersInputDTO(meeting_id=1))

        assert result.success is True
        assert result.matched_count == 1
        assert result.results[0].politician_id == 100
        assert result.results[0].skip_reason is None

    @pytest.mark.asyncio
    async def test_homonym_resolved_by_baml(
        self,
        usecase_with_baml: MatchMeetingSpeakersUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_baml_service: AsyncMock,
    ) -> None:
        """BAMLが同姓候補を解決した場合、skip_reasonは設定されない."""
        _setup_meeting(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])
        _setup_speakers(
            mock_repos,
            [Speaker(name="田中", id=1)],
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
                Politician(name="田中太郎", prefecture="", district="", id=100),
                Politician(name="田中次郎", prefecture="", district="", id=200),
            ],
        )
        mock_baml_service.find_best_match_from_candidates.return_value = (
            PoliticianMatch(
                politician_id=100,
                politician_name="田中太郎",
                confidence=0.9,
                matched=True,
            )
        )

        result = await usecase_with_baml.execute(
            MatchMeetingSpeakersInputDTO(meeting_id=1, enable_baml_fallback=True)
        )

        assert result.success is True
        assert result.matched_count == 1
        assert result.results[0].politician_id == 100
        assert result.results[0].skip_reason is None

    @pytest.mark.asyncio
    async def test_homonym_not_resolved_by_baml(
        self,
        usecase_with_baml: MatchMeetingSpeakersUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_baml_service: AsyncMock,
    ) -> None:
        """BAMLでも解決できなかった同姓候補にskip_reason=HOMONYMが設定される."""
        _setup_meeting(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])
        _setup_speakers(
            mock_repos,
            [Speaker(name="田中", id=1)],
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
                Politician(name="田中太郎", prefecture="", district="", id=100),
                Politician(name="田中次郎", prefecture="", district="", id=200),
            ],
        )
        mock_baml_service.find_best_match_from_candidates.return_value = (
            PoliticianMatch(
                politician_id=None,
                politician_name=None,
                confidence=0.3,
                matched=False,
            )
        )

        result = await usecase_with_baml.execute(
            MatchMeetingSpeakersInputDTO(meeting_id=1, enable_baml_fallback=True)
        )

        assert result.success is True
        assert result.matched_count == 0
        assert result.results[0].skip_reason == SkipReason.HOMONYM
