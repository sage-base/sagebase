"""会議発言者→政治家自動マッチングユースケース.

指定会議の全発言者を ConferenceMember で絞り込んだ候補と
ルールベースでマッチングし、高信頼度の結果で Speaker.politician_id を更新する。
"""

from datetime import date

from src.application.dtos.match_meeting_speakers_dto import (
    MatchMeetingSpeakersInputDTO,
    MatchMeetingSpeakersOutputDTO,
    SpeakerMatchResultDTO,
)
from src.common.logging import get_logger
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
from src.domain.value_objects.speaker_politician_match_result import (
    PoliticianCandidate,
)


class MatchMeetingSpeakersUseCase:
    """会議発言者→政治家自動マッチングユースケース."""

    def __init__(
        self,
        meeting_repository: MeetingRepository,
        minutes_repository: MinutesRepository,
        conversation_repository: ConversationRepository,
        speaker_repository: SpeakerRepository,
        conference_member_repository: ConferenceMemberRepository,
        politician_repository: PoliticianRepository,
        matching_service: SpeakerPoliticianMatchingService,
    ) -> None:
        self._meeting_repo = meeting_repository
        self._minutes_repo = minutes_repository
        self._conversation_repo = conversation_repository
        self._speaker_repo = speaker_repository
        self._conference_member_repo = conference_member_repository
        self._politician_repo = politician_repository
        self._matching_service = matching_service
        self._logger = get_logger(self.__class__.__name__)

    async def execute(
        self, input_dto: MatchMeetingSpeakersInputDTO
    ) -> MatchMeetingSpeakersOutputDTO:
        """指定会議の発言者を一括マッチングする.

        処理フロー:
        1. Meeting取得 → conference_id, date
        2. Minutes → Conversations → distinct speaker_ids
        3. 未マッチSpeakerを抽出
        4. ConferenceMember + Politician で候補リスト作成
        5. 各Speakerに対してマッチング実行
        6. 高信頼度の結果で Speaker.politician_id を更新
        """
        try:
            # 1. Meeting 取得
            meeting = await self._meeting_repo.get_by_id(input_dto.meeting_id)
            if not meeting or not meeting.id:
                return MatchMeetingSpeakersOutputDTO(
                    success=False,
                    message=f"会議ID {input_dto.meeting_id} が見つかりません",
                )
            if not meeting.date:
                return MatchMeetingSpeakersOutputDTO(
                    success=False,
                    message=f"会議ID {input_dto.meeting_id} に日付が設定されていません",
                )

            # 2. Minutes → Conversations → distinct speaker_ids
            minutes = await self._minutes_repo.get_by_meeting(meeting.id)
            if not minutes or not minutes.id:
                return MatchMeetingSpeakersOutputDTO(
                    success=True,
                    message="議事録が見つかりません",
                )

            conversations = await self._conversation_repo.get_by_minutes(minutes.id)
            if not conversations:
                return MatchMeetingSpeakersOutputDTO(
                    success=True,
                    message="発言が見つかりません",
                )

            speaker_ids = list({c.speaker_id for c in conversations if c.speaker_id})
            if not speaker_ids:
                return MatchMeetingSpeakersOutputDTO(
                    success=True,
                    message="発言者が見つかりません",
                )

            # 3. Speaker取得 → 未マッチのもののみ抽出
            speakers = await self._speaker_repo.get_by_ids(speaker_ids)
            unmatched_speakers: list[Speaker] = []
            skipped_count = 0

            for speaker in speakers:
                if speaker.politician_id is not None:
                    skipped_count += 1
                    continue
                if not speaker.can_be_updated_by_ai():
                    skipped_count += 1
                    continue
                unmatched_speakers.append(speaker)

            if not unmatched_speakers:
                return MatchMeetingSpeakersOutputDTO(
                    success=True,
                    message="マッチング対象の発言者がありません（全て紐付け済みまたは手動検証済み）",
                    total_speakers=len(speakers),
                    skipped_count=skipped_count,
                )

            # 4. ConferenceMember + Politician で候補リスト作成
            candidates = await self._build_candidate_list(
                meeting.conference_id, meeting.date
            )

            if not candidates:
                return MatchMeetingSpeakersOutputDTO(
                    success=True,
                    message="マッチング候補の政治家が見つかりません（ConferenceMemberデータなし）",
                    total_speakers=len(speakers),
                    skipped_count=skipped_count,
                )

            # 5. 各Speakerに対してマッチング実行
            results: list[SpeakerMatchResultDTO] = []
            matched_count = 0

            for speaker in unmatched_speakers:
                if not speaker.id:
                    continue

                match_result = self._matching_service.match(
                    speaker_id=speaker.id,
                    speaker_name=speaker.name,
                    speaker_name_yomi=speaker.name_yomi,
                    candidates=candidates,
                )

                updated = False
                if (
                    match_result.confidence >= input_dto.confidence_threshold
                    and match_result.politician_id is not None
                ):
                    speaker.politician_id = match_result.politician_id
                    await self._speaker_repo.update(speaker)
                    updated = True
                    matched_count += 1
                    self._logger.info(
                        "マッチ成功: %s → %s (confidence=%.2f, method=%s)",
                        speaker.name,
                        match_result.politician_name,
                        match_result.confidence,
                        match_result.match_method.value,
                    )

                results.append(
                    SpeakerMatchResultDTO(
                        speaker_id=match_result.speaker_id,
                        speaker_name=match_result.speaker_name,
                        politician_id=match_result.politician_id,
                        politician_name=match_result.politician_name,
                        confidence=match_result.confidence,
                        match_method=match_result.match_method,
                        updated=updated,
                    )
                )

            return MatchMeetingSpeakersOutputDTO(
                success=True,
                message=(
                    f"{len(unmatched_speakers)}件の発言者を分析し、"
                    f"{matched_count}件をマッチングしました"
                ),
                total_speakers=len(speakers),
                matched_count=matched_count,
                skipped_count=skipped_count,
                results=results,
            )

        except Exception as e:
            self._logger.error("発言者マッチングエラー: %s", e, exc_info=True)
            return MatchMeetingSpeakersOutputDTO(
                success=False,
                message=f"マッチング中にエラーが発生しました: {e!s}",
            )

    async def _build_candidate_list(
        self, conference_id: int, meeting_date: date
    ) -> list[PoliticianCandidate]:
        """会議体 + 日付から候補政治家リストを構築する."""
        members = await self._conference_member_repo.get_by_conference_at_date(
            conference_id, meeting_date
        )
        if not members:
            return []

        politician_ids = list({m.politician_id for m in members})
        politicians = await self._politician_repo.get_by_ids(politician_ids)

        return [
            PoliticianCandidate(
                politician_id=p.id,
                name=p.name,
                furigana=p.furigana,
            )
            for p in politicians
            if p.id is not None
        ]
