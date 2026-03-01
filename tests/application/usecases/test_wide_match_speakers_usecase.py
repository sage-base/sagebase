"""WideMatchSpeakersUseCase のユニットテスト."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock

import pytest

from src.application.dtos.wide_match_speakers_dto import WideMatchSpeakersInputDTO
from src.application.usecases.wide_match_speakers_usecase import (
    WideMatchSpeakersUseCase,
)
from src.domain.entities.conference import Conference
from src.domain.entities.conversation import Conversation
from src.domain.entities.election import Election
from src.domain.entities.election_member import ElectionMember
from src.domain.entities.meeting import Meeting
from src.domain.entities.minutes import Minutes
from src.domain.entities.politician import Politician
from src.domain.entities.speaker import Speaker
from src.domain.repositories.conference_repository import ConferenceRepository
from src.domain.repositories.conversation_repository import ConversationRepository
from src.domain.repositories.election_member_repository import ElectionMemberRepository
from src.domain.repositories.election_repository import ElectionRepository
from src.domain.repositories.meeting_repository import MeetingRepository
from src.domain.repositories.minutes_repository import MinutesRepository
from src.domain.repositories.politician_repository import PoliticianRepository
from src.domain.repositories.speaker_repository import SpeakerRepository
from src.domain.services.election_domain_service import ElectionDomainService
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
        "politician_repository": AsyncMock(spec=PoliticianRepository),
        "election_repository": AsyncMock(spec=ElectionRepository),
        "election_member_repository": AsyncMock(spec=ElectionMemberRepository),
        "conference_repository": AsyncMock(spec=ConferenceRepository),
    }


@pytest.fixture()
def usecase(mock_repos: dict[str, AsyncMock]) -> WideMatchSpeakersUseCase:
    """ユースケースインスタンスを生成."""
    return WideMatchSpeakersUseCase(
        **mock_repos,
        matching_service=SpeakerPoliticianMatchingService(),
        election_domain_service=ElectionDomainService(),
    )


@pytest.fixture()
def mock_baml_service() -> AsyncMock:
    """BAMLマッチングサービスのモック."""
    return AsyncMock(spec=IPoliticianMatchingService)


@pytest.fixture()
def usecase_with_baml(
    mock_repos: dict[str, AsyncMock], mock_baml_service: AsyncMock
) -> WideMatchSpeakersUseCase:
    """BAMLフォールバック付きユースケースインスタンスを生成."""
    return WideMatchSpeakersUseCase(
        **mock_repos,
        matching_service=SpeakerPoliticianMatchingService(),
        election_domain_service=ElectionDomainService(),
        baml_matching_service=mock_baml_service,
    )


# --- ヘルパー関数 ---


def _setup_meeting(mock_repos: dict[str, AsyncMock]) -> Meeting:
    """Meetingモックをセットアップ."""
    meeting = Meeting(
        conference_id=10, date=date(1980, 4, 23), name="第91回国会 衆議院本会議", id=1
    )
    mock_repos["meeting_repository"].get_by_id.return_value = meeting
    return meeting


def _setup_conference(
    mock_repos: dict[str, AsyncMock], chamber: str = "衆議院"
) -> None:
    """Conferenceモックをセットアップ."""
    conference = Conference(
        name=f"{chamber}本会議",
        governing_body_id=1,
        id=10,
    )
    mock_repos["conference_repository"].get_by_id.return_value = conference


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


def _setup_elections_and_members(
    mock_repos: dict[str, AsyncMock],
    politicians: list[Politician],
    chamber: str = "衆議院",
) -> None:
    """選挙・当選者モックをセットアップ."""
    election_type = (
        Election.ELECTION_TYPE_GENERAL
        if chamber == "衆議院"
        else Election.ELECTION_TYPE_SANGIIN
    )
    election = Election(
        governing_body_id=1,
        term_number=35,
        election_date=date(1979, 10, 7),
        election_type=election_type,
        id=1,
    )
    mock_repos["election_repository"].get_by_governing_body.return_value = [election]

    members = [
        ElectionMember(
            election_id=1,
            politician_id=p.id,  # type: ignore[arg-type]
            result="当選",
            id=i,
        )
        for i, p in enumerate(politicians, start=1)
    ]
    mock_repos["election_member_repository"].get_by_election_id.return_value = members
    mock_repos["politician_repository"].get_by_ids.return_value = politicians


def _make_input(
    meeting_id: int = 1,
    auto_match_threshold: float = 0.9,
    review_threshold: float = 0.7,
    enable_baml: bool = False,
) -> WideMatchSpeakersInputDTO:
    return WideMatchSpeakersInputDTO(
        meeting_id=meeting_id,
        auto_match_threshold=auto_match_threshold,
        review_threshold=review_threshold,
        enable_baml_fallback=enable_baml,
    )


# --- テストケース ---


class TestWideMatchSpeakersUseCase:
    """WideMatchSpeakersUseCase のテスト."""

    @pytest.mark.asyncio
    async def test_exact_name_match_auto(
        self, usecase: WideMatchSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """完全一致 → confidence=1.0 → 自動マッチ."""
        _setup_meeting(mock_repos)
        _setup_conference(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])

        speaker = Speaker(name="山田太郎", id=1, is_politician=True)
        _setup_speakers(mock_repos, [speaker])

        politician = Politician(
            name="山田太郎", prefecture="東京都", district="東京1区", id=100
        )
        _setup_elections_and_members(mock_repos, [politician])

        result = await usecase.execute(_make_input())

        assert result.success
        assert result.auto_matched_count == 1
        assert result.review_matched_count == 0
        assert len(result.results) == 1
        assert result.results[0].confidence == 1.0
        assert result.results[0].match_method == MatchMethod.EXACT_NAME
        mock_repos["speaker_repository"].update.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_yomi_match_auto(
        self, usecase: WideMatchSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """ふりがな一致 → confidence=0.9 → 自動マッチ."""
        _setup_meeting(mock_repos)
        _setup_conference(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])

        speaker = Speaker(
            name="異名太郎", name_yomi="やまだたろう", id=1, is_politician=True
        )
        _setup_speakers(mock_repos, [speaker])

        politician = Politician(
            name="山田太郎",
            furigana="ヤマダタロウ",
            prefecture="東京都",
            district="東京1区",
            id=100,
        )
        _setup_elections_and_members(mock_repos, [politician])

        result = await usecase.execute(_make_input())

        assert result.success
        assert result.auto_matched_count == 1
        assert result.review_matched_count == 0
        assert result.results[0].match_method == MatchMethod.YOMI

    @pytest.mark.asyncio
    async def test_surname_match_review_queue(
        self, usecase: WideMatchSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """姓一致（1人） → confidence=0.8 → 手動検証キュー."""
        _setup_meeting(mock_repos)
        _setup_conference(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])

        speaker = Speaker(name="山田", id=1, is_politician=True)
        _setup_speakers(mock_repos, [speaker])

        politician = Politician(
            name="山田太郎", prefecture="東京都", district="東京1区", id=100
        )
        _setup_elections_and_members(mock_repos, [politician])

        result = await usecase.execute(_make_input())

        assert result.success
        assert result.auto_matched_count == 0
        assert result.review_matched_count == 1
        assert result.results[0].confidence == 0.8
        assert result.results[0].match_method == MatchMethod.SURNAME_ONLY
        mock_repos["speaker_repository"].update.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_low_confidence_pending(
        self, usecase: WideMatchSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """マッチなし（confidence=0.0） → 未マッチ保留."""
        _setup_meeting(mock_repos)
        _setup_conference(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])

        speaker = Speaker(name="佐々木花子", id=1, is_politician=True)
        _setup_speakers(mock_repos, [speaker])

        politician = Politician(
            name="山田太郎", prefecture="東京都", district="東京1区", id=100
        )
        _setup_elections_and_members(mock_repos, [politician])

        result = await usecase.execute(_make_input())

        assert result.success
        assert result.auto_matched_count == 0
        assert result.review_matched_count == 0
        # 非政治家分類にも該当しないのでBAML pending → unmatched dto
        assert len(result.results) == 1
        assert result.results[0].updated is False

    @pytest.mark.asyncio
    async def test_non_politician_classification(
        self, usecase: WideMatchSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """非政治家（議長等） → スキップ."""
        _setup_meeting(mock_repos)
        _setup_conference(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])

        speaker = Speaker(name="議長", id=1, is_politician=True)
        _setup_speakers(mock_repos, [speaker])

        politician = Politician(
            name="山田太郎", prefecture="東京都", district="東京1区", id=100
        )
        _setup_elections_and_members(mock_repos, [politician])

        result = await usecase.execute(_make_input())

        assert result.success
        assert result.non_politician_count == 1
        assert result.auto_matched_count == 0

    @pytest.mark.asyncio
    async def test_already_matched_speaker_skipped(
        self, usecase: WideMatchSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """既マッチSpeaker → スキップ."""
        _setup_meeting(mock_repos)
        _setup_conference(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])

        speaker = Speaker(name="山田太郎", id=1, politician_id=100)
        _setup_speakers(mock_repos, [speaker])

        politician = Politician(
            name="山田太郎", prefecture="東京都", district="東京1区", id=100
        )
        _setup_elections_and_members(mock_repos, [politician])

        result = await usecase.execute(_make_input())

        assert result.success
        assert result.skipped_count == 1
        assert result.auto_matched_count == 0

    @pytest.mark.asyncio
    async def test_no_minutes(
        self, usecase: WideMatchSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """議事録なし → 早期リターン."""
        _setup_meeting(mock_repos)
        _setup_conference(mock_repos)
        mock_repos["minutes_repository"].get_by_meeting.return_value = None

        result = await usecase.execute(_make_input())

        assert result.success
        assert result.message == "議事録が見つかりません"

    @pytest.mark.asyncio
    async def test_no_election_data_fallback_to_all(
        self, usecase: WideMatchSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """選挙データなし → 全Politicianフォールバック."""
        _setup_meeting(mock_repos)
        _setup_conference(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])

        speaker = Speaker(name="山田太郎", id=1, is_politician=True)
        _setup_speakers(mock_repos, [speaker])

        # 選挙データなし
        mock_repos["election_repository"].get_by_governing_body.return_value = []

        # 全Politicianフォールバック
        mock_repos["politician_repository"].get_all_for_matching.return_value = [
            {"id": 100, "name": "山田太郎", "party_name": "自由民主党"},
        ]

        result = await usecase.execute(_make_input())

        assert result.success
        # get_all_for_matchingではfuriganaがないのでfurigana matchは効かない
        # 名前の完全一致は効くが、PoliticianCandidateのnameで比較
        mock_repos["politician_repository"].get_all_for_matching.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_baml_fallback_review_queue(
        self,
        usecase_with_baml: WideMatchSpeakersUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_baml_service: AsyncMock,
    ) -> None:
        """BAMLフォールバック → confidence=0.85 → 手動検証キュー."""
        _setup_meeting(mock_repos)
        _setup_conference(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])

        speaker = Speaker(name="田中一郎", id=1, is_politician=True)
        _setup_speakers(mock_repos, [speaker])

        politician = Politician(
            name="山田太郎", prefecture="東京都", district="東京1区", id=100
        )
        _setup_elections_and_members(mock_repos, [politician])

        mock_baml_service.find_best_match_from_candidates.return_value = (
            PoliticianMatch(
                matched=True,
                politician_id=100,
                politician_name="山田太郎",
                political_party_name="自由民主党",
                confidence=0.85,
                reason="BAMLマッチ",
            )
        )

        result = await usecase_with_baml.execute(_make_input(enable_baml=True))

        assert result.success
        assert result.baml_matched_count == 1
        assert result.review_matched_count == 1
        assert result.auto_matched_count == 0

    @pytest.mark.asyncio
    async def test_baml_low_confidence_not_matched(
        self,
        usecase_with_baml: WideMatchSpeakersUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_baml_service: AsyncMock,
    ) -> None:
        """BAMLフォールバック → confidence=0.5 → 未マッチ."""
        _setup_meeting(mock_repos)
        _setup_conference(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])

        speaker = Speaker(name="田中一郎", id=1, is_politician=True)
        _setup_speakers(mock_repos, [speaker])

        politician = Politician(
            name="山田太郎", prefecture="東京都", district="東京1区", id=100
        )
        _setup_elections_and_members(mock_repos, [politician])

        mock_baml_service.find_best_match_from_candidates.return_value = (
            PoliticianMatch(
                matched=False,
                politician_id=None,
                politician_name=None,
                political_party_name=None,
                confidence=0.5,
                reason="低信頼度",
            )
        )

        result = await usecase_with_baml.execute(_make_input(enable_baml=True))

        assert result.success
        assert result.baml_matched_count == 0
        assert result.auto_matched_count == 0
        assert result.review_matched_count == 0

    @pytest.mark.asyncio
    async def test_sangiin_two_elections_combined(
        self, usecase: WideMatchSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """参議院: 直近2回の選挙当選者を合算."""
        meeting = Meeting(
            conference_id=10,
            date=date(1980, 4, 23),
            name="第91回国会 参議院本会議",
            id=1,
        )
        mock_repos["meeting_repository"].get_by_id.return_value = meeting
        _setup_conference(mock_repos, chamber="参議院")
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])

        speaker = Speaker(name="鈴木花子", id=1, is_politician=True)
        _setup_speakers(mock_repos, [speaker])

        # 2回分の参議院選挙
        election1 = Election(
            governing_body_id=1,
            term_number=11,
            election_date=date(1977, 7, 10),
            election_type=Election.ELECTION_TYPE_SANGIIN,
            id=1,
        )
        election2 = Election(
            governing_body_id=1,
            term_number=12,
            election_date=date(1980, 6, 22),
            election_type=Election.ELECTION_TYPE_SANGIIN,
            id=2,
        )
        # meeting.dateより前の選挙のみ返す（get_active_election_at_dateの仕様）
        # date(1980, 4, 23) < date(1980, 6, 22) なので election1 が active
        mock_repos["election_repository"].get_by_governing_body.return_value = [
            election1,
            election2,
        ]

        pol1 = Politician(name="山田太郎", prefecture="東京都", district="東京", id=100)
        pol2 = Politician(name="鈴木花子", prefecture="千葉県", district="千葉", id=101)

        # election1(1977)がactive、election2(1980-06)は未来
        # → previous なし。テスト用にelection2を過去に変更
        election2_adjusted = Election(
            governing_body_id=1,
            term_number=10,
            election_date=date(1974, 7, 7),
            election_type=Election.ELECTION_TYPE_SANGIIN,
            id=2,
        )
        mock_repos["election_repository"].get_by_governing_body.return_value = [
            election1,
            election2_adjusted,
        ]

        # election1の当選者: pol1
        # election2の当選者: pol2
        async def _get_members(election_id: int) -> list[ElectionMember]:
            if election_id == 1:
                return [
                    ElectionMember(
                        election_id=1, politician_id=100, result="当選", id=1
                    )
                ]
            return [
                ElectionMember(election_id=2, politician_id=101, result="当選", id=2)
            ]

        mock_repos[
            "election_member_repository"
        ].get_by_election_id.side_effect = _get_members
        mock_repos["politician_repository"].get_by_ids.return_value = [pol1, pol2]

        result = await usecase.execute(_make_input())

        assert result.success
        # 鈴木花子は完全一致でマッチ
        assert result.auto_matched_count == 1

    @pytest.mark.asyncio
    async def test_matching_confidence_stored(
        self, usecase: WideMatchSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """マッチ時にmatching_confidence/matching_reasonが設定される."""
        _setup_meeting(mock_repos)
        _setup_conference(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])

        speaker = Speaker(name="山田太郎", id=1, is_politician=True)
        _setup_speakers(mock_repos, [speaker])

        politician = Politician(
            name="山田太郎", prefecture="東京都", district="東京1区", id=100
        )
        _setup_elections_and_members(mock_repos, [politician])

        await usecase.execute(_make_input())

        # updateが呼ばれた際のSpeakerを検証
        update_call = mock_repos["speaker_repository"].update.call_args
        updated_speaker: Speaker = update_call[0][0]
        assert updated_speaker.matching_confidence == 1.0
        assert updated_speaker.matching_reason is not None
        assert "自動マッチ" in updated_speaker.matching_reason

    @pytest.mark.asyncio
    async def test_meeting_not_found(
        self, usecase: WideMatchSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """会議が見つからない場合."""
        mock_repos["meeting_repository"].get_by_id.return_value = None

        result = await usecase.execute(_make_input(meeting_id=999))

        assert not result.success
        assert "見つかりません" in result.message

    @pytest.mark.asyncio
    async def test_meeting_without_date(
        self, usecase: WideMatchSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """会議に日付がない場合 → エラーDTO."""
        meeting = Meeting(conference_id=10, date=None, name="日付なし会議", id=1)
        mock_repos["meeting_repository"].get_by_id.return_value = meeting

        result = await usecase.execute(_make_input())

        assert not result.success
        assert "日付が設定されていません" in result.message

    @pytest.mark.asyncio
    async def test_baml_fallback_auto_match(
        self,
        usecase_with_baml: WideMatchSpeakersUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_baml_service: AsyncMock,
    ) -> None:
        """BAMLフォールバック → confidence=0.95 → 自動マッチ."""
        _setup_meeting(mock_repos)
        _setup_conference(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])

        speaker = Speaker(name="田中一郎", id=1, is_politician=True)
        _setup_speakers(mock_repos, [speaker])

        politician = Politician(
            name="山田太郎", prefecture="東京都", district="東京1区", id=100
        )
        _setup_elections_and_members(mock_repos, [politician])

        mock_baml_service.find_best_match_from_candidates.return_value = (
            PoliticianMatch(
                matched=True,
                politician_id=100,
                politician_name="山田太郎",
                political_party_name="自由民主党",
                confidence=0.95,
                reason="BAMLマッチ高信頼度",
            )
        )

        result = await usecase_with_baml.execute(_make_input(enable_baml=True))

        assert result.success
        assert result.baml_matched_count == 1
        assert result.auto_matched_count == 1
        assert result.review_matched_count == 0

    @pytest.mark.asyncio
    async def test_baml_fallback_exception_handled(
        self,
        usecase_with_baml: WideMatchSpeakersUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_baml_service: AsyncMock,
    ) -> None:
        """BAMLフォールバック例外 → スキップして未マッチDTOを返す."""
        _setup_meeting(mock_repos)
        _setup_conference(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])

        speaker = Speaker(name="田中一郎", id=1, is_politician=True)
        _setup_speakers(mock_repos, [speaker])

        politician = Politician(
            name="山田太郎", prefecture="東京都", district="東京1区", id=100
        )
        _setup_elections_and_members(mock_repos, [politician])

        mock_baml_service.find_best_match_from_candidates.side_effect = RuntimeError(
            "BAML API error"
        )

        result = await usecase_with_baml.execute(_make_input(enable_baml=True))

        assert result.success
        assert result.baml_matched_count == 0
        assert result.auto_matched_count == 0
        assert len(result.results) == 1
        assert result.results[0].updated is False

    @pytest.mark.asyncio
    async def test_multiple_speakers_mixed_results(
        self, usecase: WideMatchSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """複数Speaker: マッチ・非政治家・未マッチが混在."""
        _setup_meeting(mock_repos)
        _setup_conference(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1, 2, 3])

        speakers = [
            Speaker(name="山田太郎", id=1, is_politician=True),  # → 完全一致
            Speaker(name="議長", id=2, is_politician=True),  # → 非政治家
            Speaker(name="佐々木花子", id=3, is_politician=True),  # → 未マッチ
        ]
        mock_repos["speaker_repository"].get_by_ids.return_value = speakers
        mock_repos["speaker_repository"].update.return_value = speakers[0]

        politician = Politician(
            name="山田太郎", prefecture="東京都", district="東京1区", id=100
        )
        _setup_elections_and_members(mock_repos, [politician])

        result = await usecase.execute(_make_input())

        assert result.success
        assert result.auto_matched_count == 1
        assert result.non_politician_count == 1
        assert len(result.results) == 3

    @pytest.mark.asyncio
    async def test_homonym_speaker_without_baml(
        self, usecase: WideMatchSpeakersUseCase, mock_repos: dict[str, AsyncMock]
    ) -> None:
        """同姓候補が複数存在しBAML無効時にskip_reason=HOMONYMが設定される."""
        _setup_meeting(mock_repos)
        _setup_conference(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])

        speakers = [Speaker(name="田中", id=1, is_politician=True)]
        mock_repos["speaker_repository"].get_by_ids.return_value = speakers
        mock_repos["speaker_repository"].update.return_value = speakers[0]

        politicians = [
            Politician(
                name="田中太郎", prefecture="東京都", district="東京1区", id=100
            ),
            Politician(
                name="田中次郎", prefecture="大阪府", district="大阪1区", id=200
            ),
        ]
        _setup_elections_and_members(mock_repos, politicians)

        result = await usecase.execute(_make_input())

        assert result.success is True
        assert result.auto_matched_count == 0
        assert len(result.results) == 1
        assert result.results[0].skip_reason == SkipReason.HOMONYM

    @pytest.mark.asyncio
    async def test_homonym_resolved_by_baml(
        self,
        usecase_with_baml: WideMatchSpeakersUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_baml_service: AsyncMock,
    ) -> None:
        """BAMLが同姓候補を解決した場合、skip_reasonは設定されない."""
        _setup_meeting(mock_repos)
        _setup_conference(mock_repos)
        _setup_minutes(mock_repos)
        _setup_conversations(mock_repos, [1])

        speakers = [Speaker(name="田中", id=1, is_politician=True)]
        mock_repos["speaker_repository"].get_by_ids.return_value = speakers
        mock_repos["speaker_repository"].update.return_value = speakers[0]

        politicians = [
            Politician(
                name="田中太郎", prefecture="東京都", district="東京1区", id=100
            ),
            Politician(
                name="田中次郎", prefecture="大阪府", district="大阪1区", id=200
            ),
        ]
        _setup_elections_and_members(mock_repos, politicians)

        mock_baml_service.find_best_match_from_candidates.return_value = (
            PoliticianMatch(
                politician_id=100,
                politician_name="田中太郎",
                confidence=0.95,
                matched=True,
            )
        )

        result = await usecase_with_baml.execute(_make_input(enable_baml=True))

        assert result.success is True
        assert result.auto_matched_count == 1
        assert result.results[0].politician_id == 100
        assert result.results[0].skip_reason is None
