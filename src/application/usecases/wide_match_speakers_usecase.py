"""ConferenceMember非依存の広域マッチングユースケース.

1947-2007年のようにConferenceMemberデータが存在しない時代の
Speaker→Politician マッチングを行う。
候補の絞り込みにはElection（選挙当選者）を使用する。
"""

from __future__ import annotations

from datetime import date
from typing import Any

from src.application.dtos.match_meeting_speakers_dto import SpeakerMatchResultDTO
from src.application.dtos.wide_match_speakers_dto import (
    WideMatchSpeakersInputDTO,
    WideMatchSpeakersOutputDTO,
)
from src.common.logging import get_logger
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
from src.domain.services.speaker_classifier import classify_speaker_skip_reason
from src.domain.services.speaker_politician_matching_service import (
    SpeakerPoliticianMatchingService,
)
from src.domain.value_objects.speaker_politician_match_result import (
    MatchMethod,
    PoliticianCandidate,
)


# 国会の governing_body_id
_KOKKAI_GOVERNING_BODY_ID = 1


class WideMatchSpeakersUseCase:
    """ConferenceMember非依存の広域マッチングユースケース."""

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
        politician_repository: PoliticianRepository,
        election_repository: ElectionRepository,
        election_member_repository: ElectionMemberRepository,
        conference_repository: ConferenceRepository,
        matching_service: SpeakerPoliticianMatchingService,
        election_domain_service: ElectionDomainService,
        baml_matching_service: IPoliticianMatchingService | None = None,
    ) -> None:
        self._meeting_repo = meeting_repository
        self._minutes_repo = minutes_repository
        self._conversation_repo = conversation_repository
        self._speaker_repo = speaker_repository
        self._politician_repo = politician_repository
        self._election_repo = election_repository
        self._election_member_repo = election_member_repository
        self._conference_repo = conference_repository
        self._matching_service = matching_service
        self._election_domain_service = election_domain_service
        self._baml_matching_service = baml_matching_service
        self._logger = get_logger(self.__class__.__name__)

    async def execute(
        self, input_dto: WideMatchSpeakersInputDTO
    ) -> WideMatchSpeakersOutputDTO:
        """広域マッチングを実行する.

        処理フロー:
        1. Meeting取得 → Conference → chamber判定
        2. Minutes → Conversations → 未マッチSpeaker抽出
        3. 選挙当選者ベースの候補リスト構築
        4. ルールベースマッチング → 非政治家分類 → BAMLフォールバック
        5. 信頼度に基づく3段階処理
        """
        try:
            # 1. Meeting取得
            meeting = await self._meeting_repo.get_by_id(input_dto.meeting_id)
            if not meeting or not meeting.id:
                return WideMatchSpeakersOutputDTO(
                    success=False,
                    message=f"会議ID {input_dto.meeting_id} が見つかりません",
                )
            if not meeting.date:
                return WideMatchSpeakersOutputDTO(
                    success=False,
                    message=f"会議ID {input_dto.meeting_id} に日付が設定されていません",
                )

            # Conference → chamber判定
            conference = await self._conference_repo.get_by_id(meeting.conference_id)
            chamber = conference.chamber if conference else None

            # 2. Minutes → Conversations → distinct speaker_ids
            minutes = await self._minutes_repo.get_by_meeting(meeting.id)
            if not minutes or not minutes.id:
                return WideMatchSpeakersOutputDTO(
                    success=True, message="議事録が見つかりません"
                )

            conversations = await self._conversation_repo.get_by_minutes(minutes.id)
            if not conversations:
                return WideMatchSpeakersOutputDTO(
                    success=True, message="発言が見つかりません"
                )

            speaker_ids = list({c.speaker_id for c in conversations if c.speaker_id})
            if not speaker_ids:
                return WideMatchSpeakersOutputDTO(
                    success=True, message="発言者が見つかりません"
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
                return WideMatchSpeakersOutputDTO(
                    success=True,
                    message="マッチング対象の発言者がありません",
                    total_speakers=len(speakers),
                    skipped_count=skipped_count,
                )

            # 4. 選挙当選者ベースの候補リスト構築
            candidates = await self._build_candidate_list_from_elections(
                meeting.date, chamber
            )
            if not candidates:
                self._logger.info("選挙ベース候補なし → 全Politicianフォールバック")
                candidates = await self._build_candidate_list_from_all_politicians()

            if not candidates:
                return WideMatchSpeakersOutputDTO(
                    success=True,
                    message="マッチング候補の政治家が見つかりません",
                    total_speakers=len(speakers),
                    skipped_count=skipped_count,
                )

            # 5. マッチング実行
            results: list[SpeakerMatchResultDTO] = []
            auto_matched_count = 0
            review_matched_count = 0
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

                if (
                    match_result.confidence >= input_dto.review_threshold
                    and match_result.politician_id is not None
                ):
                    updated, action = self._apply_confidence_action(
                        speaker,
                        match_result.politician_id,
                        match_result.politician_name,
                        match_result.confidence,
                        match_result.match_method,
                        input_dto.auto_match_threshold,
                        input_dto.review_threshold,
                    )
                    if updated:
                        await self._speaker_repo.update(speaker)
                        if action == "auto_match":
                            auto_matched_count += 1
                        else:
                            review_matched_count += 1
                        self._logger.info(
                            "マッチ成功(%s): %s → %s (confidence=%.2f, method=%s)",
                            action,
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

                # 非政治家分類
                skip_reason = classify_speaker_skip_reason(speaker.name)
                if skip_reason is not None:
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

            # 6. BAMLフォールバック
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
                        action = "pending"
                        if (
                            baml_result.matched
                            and baml_result.confidence >= input_dto.review_threshold
                            and baml_result.politician_id is not None
                        ):
                            updated, action = self._apply_confidence_action(
                                speaker,
                                baml_result.politician_id,
                                baml_result.politician_name,
                                baml_result.confidence,
                                MatchMethod.BAML,
                                input_dto.auto_match_threshold,
                                input_dto.review_threshold,
                            )
                            if updated:
                                await self._speaker_repo.update(speaker)
                                baml_matched_count += 1
                                if action == "auto_match":
                                    auto_matched_count += 1
                                else:
                                    review_matched_count += 1
                                self._logger.info(
                                    "BAMLマッチ成功(%s): %s → %s (confidence=%.2f)",
                                    action,
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
                for speaker in baml_pending_speakers:
                    if not speaker.id:
                        continue
                    results.append(self._unmatched_dto(speaker))

            total_matched = auto_matched_count + review_matched_count
            return WideMatchSpeakersOutputDTO(
                success=True,
                message=(
                    f"{len(unmatched_speakers)}件の発言者を分析し、"
                    f"{total_matched}件をマッチングしました"
                    f"（自動: {auto_matched_count}, 検証待ち: {review_matched_count}）"
                ),
                total_speakers=len(speakers),
                auto_matched_count=auto_matched_count,
                review_matched_count=review_matched_count,
                skipped_count=skipped_count,
                baml_matched_count=baml_matched_count,
                non_politician_count=non_politician_count,
                results=results,
            )

        except Exception as e:
            self._logger.error("広域マッチングエラー: %s", e, exc_info=True)
            return WideMatchSpeakersOutputDTO(
                success=False,
                message=f"広域マッチング中にエラーが発生しました: {e!s}",
            )

    async def _build_candidate_list_from_elections(
        self, meeting_date: date, chamber: str | None
    ) -> list[PoliticianCandidate]:
        """選挙当選者ベースで候補政治家リストを構築する."""
        elections = await self._election_repo.get_by_governing_body(
            _KOKKAI_GOVERNING_BODY_ID
        )
        if not elections:
            return []

        active_election = self._election_domain_service.get_active_election_at_date(
            elections, meeting_date, chamber
        )
        if not active_election or not active_election.id:
            return []

        # 当選者一覧を取得
        elected_politician_ids = await self._get_elected_politician_ids(
            active_election.id
        )

        # 参議院の場合: 直近2回の選挙当選者を合算（半数改選対応）
        if active_election.is_sangiin:
            previous_elections = [
                e
                for e in elections
                if e.chamber == "参議院"
                and e.election_date < active_election.election_date
            ]
            if previous_elections:
                prev_election = max(previous_elections, key=lambda e: e.election_date)
                if prev_election.id:
                    prev_ids = await self._get_elected_politician_ids(prev_election.id)
                    elected_politician_ids = list(
                        set(elected_politician_ids) | set(prev_ids)
                    )

        if not elected_politician_ids:
            return []

        politicians = await self._politician_repo.get_by_ids(elected_politician_ids)
        return [
            PoliticianCandidate(
                politician_id=p.id,
                name=p.name,
                furigana=p.furigana,
            )
            for p in politicians
            if p.id is not None
        ]

    async def _get_elected_politician_ids(self, election_id: int) -> list[int]:
        """選挙IDから当選者のpolitician_idsを取得する."""
        members = await self._election_member_repo.get_by_election_id(election_id)
        return [m.politician_id for m in members if m.is_elected]

    async def _build_candidate_list_from_all_politicians(
        self,
    ) -> list[PoliticianCandidate]:
        """全Politicianから候補リストを構築する（フォールバック）."""
        all_politicians: list[
            dict[str, Any]
        ] = await self._politician_repo.get_all_for_matching()
        return [
            PoliticianCandidate(
                politician_id=p["id"],
                name=p["name"],
                furigana=None,
            )
            for p in all_politicians
        ]

    def _apply_confidence_action(
        self,
        speaker: Speaker,
        politician_id: int,
        politician_name: str | None,
        confidence: float,
        match_method: MatchMethod,
        auto_threshold: float,
        review_threshold: float,
    ) -> tuple[bool, str]:
        """信頼度に基づいてSpeakerを更新する.

        Returns:
            (updated, action): actionは "auto_match" | "manual_review" | "pending"
        """
        if confidence >= auto_threshold:
            speaker.politician_id = politician_id
            speaker.is_politician = True
            speaker.matching_confidence = confidence
            speaker.matching_reason = f"{match_method.value}: 自動マッチ"
            return True, "auto_match"
        elif confidence >= review_threshold:
            speaker.politician_id = politician_id
            speaker.is_politician = True
            speaker.matching_confidence = confidence
            speaker.matching_reason = f"{match_method.value}: 手動検証待ち"
            return True, "manual_review"
        return False, "pending"
