"""会議発言者→政治家自動マッチングユースケース.

指定会議の全発言者を ConferenceMember で絞り込んだ候補と
ルールベースでマッチングし、高信頼度の結果で Speaker.politician_id を更新する。
BAMLフォールバックが有効な場合、ルールベースで拾えなかった発言者に対して
LLMによる精密判定を実行する。
"""

from __future__ import annotations

from datetime import date

from src.application.dtos.match_meeting_speakers_dto import (
    MatchMeetingSpeakersInputDTO,
    MatchMeetingSpeakersOutputDTO,
    SpeakerMatchResultDTO,
)
from src.common.logging import get_logger
from src.domain.entities.conference_member import ConferenceMember
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
from src.domain.services.speaker_classifier import classify_speaker_skip_reason
from src.domain.services.speaker_politician_matching_service import (
    SpeakerPoliticianMatchingService,
)
from src.domain.value_objects.speaker_politician_match_result import (
    MatchMethod,
    PoliticianCandidate,
)


class MatchMeetingSpeakersUseCase:
    """会議発言者→政治家自動マッチングユースケース."""

    @staticmethod
    def _unmatched_dto(speaker: Speaker) -> SpeakerMatchResultDTO:
        """未マッチSpeaker用のDTO生成ファクトリ."""
        return SpeakerMatchResultDTO(
            speaker_id=speaker.id,  # type: ignore[arg-type]
            speaker_name=speaker.name,
            politician_id=None,
            politician_name=None,
            confidence=0.0,
            match_method=MatchMethod.NONE,
            updated=False,
        )

    def __init__(
        self,
        meeting_repository: MeetingRepository,
        minutes_repository: MinutesRepository,
        conversation_repository: ConversationRepository,
        speaker_repository: SpeakerRepository,
        conference_member_repository: ConferenceMemberRepository,
        politician_repository: PoliticianRepository,
        matching_service: SpeakerPoliticianMatchingService,
        conference_repository: ConferenceRepository | None = None,
        baml_matching_service: IPoliticianMatchingService | None = None,
    ) -> None:
        self._meeting_repo = meeting_repository
        self._minutes_repo = minutes_repository
        self._conversation_repo = conversation_repository
        self._speaker_repo = speaker_repository
        self._conference_member_repo = conference_member_repository
        self._politician_repo = politician_repository
        self._matching_service = matching_service
        self._conference_repo = conference_repository
        self._baml_matching_service = baml_matching_service
        self._logger = get_logger(self.__class__.__name__)
        if conference_repository is None:
            self._logger.warning(
                "conference_repository未注入: 本会議フォールバックは無効です"
            )

    async def execute(
        self, input_dto: MatchMeetingSpeakersInputDTO
    ) -> MatchMeetingSpeakersOutputDTO:
        """指定会議の発言者を一括マッチングする.

        処理フロー:
        1. Meeting取得 → conference_id, date
        2. Minutes → Conversations → distinct speaker_ids
        3. 未マッチSpeakerを抽出
        4. ConferenceMember + Politician で候補リスト作成
        5. 各Speakerに対してルールベースマッチング実行
        6. 未マッチSpeakerの非政治家分類
        7. BAMLフォールバック（有効時のみ）
        8. 高信頼度の結果で Speaker.politician_id を更新
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

            # 5. 各Speakerに対してルールベースマッチング実行
            results: list[SpeakerMatchResultDTO] = []
            matched_count = 0
            baml_matched_count = 0
            non_politician_count = 0
            baml_pending_speakers: list[Speaker] = []

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
                    speaker.is_politician = True
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
                    continue

                # 6. ルールベース未マッチ → 非政治家分類
                skip_reason = classify_speaker_skip_reason(speaker.name)
                if skip_reason is not None:
                    # 非政治家として分類 → is_politicianをFalseに設定
                    if speaker.is_politician:
                        speaker.is_politician = False
                        await self._speaker_repo.update(speaker)
                    non_politician_count += 1
                    self._logger.debug(
                        "非政治家分類: %s → %s", speaker.name, skip_reason
                    )
                    dto = self._unmatched_dto(speaker)
                    dto.skip_reason = skip_reason
                    results.append(dto)
                    continue

                # BAMLフォールバック対象として保留
                baml_pending_speakers.append(speaker)

            # 7. BAMLフォールバック（有効時のみ）
            if (
                input_dto.enable_baml_fallback
                and self._baml_matching_service is not None
                and baml_pending_speakers
            ):
                role_name_mappings = minutes.role_name_mappings

                for speaker in baml_pending_speakers:
                    if not speaker.id:
                        continue
                    try:
                        baml_svc = self._baml_matching_service
                        baml_result = await baml_svc.find_best_match_from_candidates(
                            speaker_name=speaker.name,
                            candidates=candidates,
                            speaker_type=speaker.type,
                            speaker_party=speaker.political_party_name,
                            role_name_mappings=role_name_mappings,
                        )

                        updated = False
                        if (
                            baml_result.matched
                            and baml_result.confidence >= input_dto.confidence_threshold
                            and baml_result.politician_id is not None
                        ):
                            speaker.politician_id = baml_result.politician_id
                            speaker.is_politician = True
                            await self._speaker_repo.update(speaker)
                            updated = True
                            matched_count += 1
                            baml_matched_count += 1
                            self._logger.info(
                                "BAMLマッチ成功: %s → %s (confidence=%.2f)",
                                speaker.name,
                                baml_result.politician_name,
                                baml_result.confidence,
                            )

                        results.append(
                            SpeakerMatchResultDTO(
                                speaker_id=speaker.id,
                                speaker_name=speaker.name,
                                politician_id=baml_result.politician_id
                                if baml_result.matched
                                else None,
                                politician_name=baml_result.politician_name
                                if baml_result.matched
                                else None,
                                confidence=baml_result.confidence,
                                match_method=MatchMethod.BAML
                                if updated
                                else MatchMethod.NONE,
                                updated=updated,
                            )
                        )
                    except Exception:
                        self._logger.warning(
                            "BAMLフォールバック失敗（スキップ）: %s",
                            speaker.name,
                            exc_info=True,
                        )
                        results.append(self._unmatched_dto(speaker))
            else:
                # BAMLフォールバック無効時、残りの未マッチSpeakerを結果に追加
                for speaker in baml_pending_speakers:
                    if not speaker.id:
                        continue
                    results.append(self._unmatched_dto(speaker))

            return MatchMeetingSpeakersOutputDTO(
                success=True,
                message=(
                    f"{len(unmatched_speakers)}件の発言者を分析し、"
                    f"{matched_count}件をマッチングしました"
                ),
                total_speakers=len(speakers),
                matched_count=matched_count,
                skipped_count=skipped_count,
                baml_matched_count=baml_matched_count,
                non_politician_count=non_politician_count,
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
            members = await self._fallback_to_plenary_session(
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

    async def _fallback_to_plenary_session(
        self, conference_id: int, meeting_date: date
    ) -> list[ConferenceMember]:
        """同じ院の本会議の ConferenceMember にフォールバックする."""
        if not self._conference_repo:
            return []

        conference = await self._conference_repo.get_by_id(conference_id)
        if not conference or not conference.plenary_session_name:
            return []

        # 本会議自身に対するフォールバックは不要（無限ループ防止）
        if conference.name == conference.plenary_session_name:
            return []

        plenary = await self._conference_repo.get_by_name_and_governing_body(
            conference.plenary_session_name, conference.governing_body_id
        )
        if not plenary or not plenary.id:
            return []

        self._logger.info(
            "フォールバック: %s → %s の ConferenceMember を使用",
            conference.name,
            plenary.name,
        )
        return await self._conference_member_repo.get_by_conference_at_date(
            plenary.id, meeting_date
        )
