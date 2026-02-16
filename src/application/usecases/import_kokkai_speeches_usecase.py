"""国会会議録API発言インポートユースケース.

国会会議録検索システムAPIから発言データを取得し、
Meeting/Minutes/Speaker/Conversation エンティティとしてDBに保存する。
"""

from __future__ import annotations

import logging
import re

from datetime import date
from itertools import groupby
from operator import attrgetter

from src.application.dtos.kokkai_speech_dto import (
    ImportKokkaiSpeechesInputDTO,
    ImportKokkaiSpeechesOutputDTO,
    KokkaiSpeechDTO,
)
from src.domain.entities.conference import Conference
from src.domain.entities.conversation import Conversation
from src.domain.entities.meeting import Meeting
from src.domain.entities.minutes import Minutes
from src.domain.entities.speaker import Speaker
from src.domain.repositories.conference_repository import ConferenceRepository
from src.domain.repositories.conversation_repository import ConversationRepository
from src.domain.repositories.governing_body_repository import GoverningBodyRepository
from src.domain.repositories.meeting_repository import MeetingRepository
from src.domain.repositories.minutes_repository import MinutesRepository
from src.domain.repositories.speaker_repository import SpeakerRepository
from src.domain.services.interfaces.kokkai_speech_service import IKokkaiSpeechService


logger = logging.getLogger(__name__)

# 発言者名末尾の敬称パターン
_HONORIFIC_PATTERN = re.compile(r"(君|くん|さん|殿|氏)$")


class ImportKokkaiSpeechesUseCase:
    """国会会議録APIから発言を取得しDBに保存するユースケース."""

    # GoverningBody "国会" の検索条件
    _KOKKAI_GB_NAME = "国会"
    _KOKKAI_GB_TYPE = "国"

    def __init__(
        self,
        kokkai_speech_service: IKokkaiSpeechService,
        meeting_repository: MeetingRepository,
        minutes_repository: MinutesRepository,
        conversation_repository: ConversationRepository,
        speaker_repository: SpeakerRepository,
        conference_repository: ConferenceRepository,
        governing_body_repository: GoverningBodyRepository,
    ) -> None:
        self._speech_service = kokkai_speech_service
        self._meeting_repo = meeting_repository
        self._minutes_repo = minutes_repository
        self._conversation_repo = conversation_repository
        self._speaker_repo = speaker_repository
        self._conference_repo = conference_repository
        self._governing_body_repo = governing_body_repository

    async def execute(
        self, input_dto: ImportKokkaiSpeechesInputDTO
    ) -> ImportKokkaiSpeechesOutputDTO:
        """メイン処理: API取得 → エンティティ変換 → DB保存."""
        output = ImportKokkaiSpeechesOutputDTO()

        # 1. APIから発言データを取得
        speeches = await self._speech_service.fetch_speeches(
            issue_id=input_dto.issue_id,
            name_of_house=input_dto.name_of_house,
            from_date=input_dto.from_date,
            until_date=input_dto.until_date,
        )
        if not speeches:
            logger.info("取得対象の発言データがありません")
            return output

        logger.info("APIから %d 件の発言データを取得しました", len(speeches))

        # 2. GoverningBody "国会" を取得
        governing_body = await self._governing_body_repo.get_by_name_and_type(
            self._KOKKAI_GB_NAME, self._KOKKAI_GB_TYPE
        )
        if not governing_body or not governing_body.id:
            output.errors.append("GoverningBody '国会' が見つかりません")
            return output

        # 3. issueIDごとにグループ化して処理
        sorted_speeches = sorted(speeches, key=attrgetter("issue_id"))
        for issue_id, group in groupby(sorted_speeches, key=attrgetter("issue_id")):
            speech_list = list(group)
            try:
                await self._process_meeting_speeches(
                    speech_list, governing_body.id, output
                )
            except Exception as e:
                error_msg = f"会議 {issue_id} の処理中にエラー: {e}"
                logger.exception(error_msg)
                output.errors.append(error_msg)

        logger.info(
            "インポート完了: %d件保存, %d件スキップ, %d会議作成, %d発言者作成",
            output.total_speeches_imported,
            output.total_speeches_skipped,
            output.total_meetings_created,
            output.total_speakers_created,
        )
        return output

    async def _process_meeting_speeches(
        self,
        speeches: list[KokkaiSpeechDTO],
        governing_body_id: int,
        output: ImportKokkaiSpeechesOutputDTO,
    ) -> None:
        """単一会議の発言群を処理."""
        first = speeches[0]

        # 重複チェック: 同じ meetingURL のMeetingが既にあるか
        existing_meeting = await self._meeting_repo.get_by_url(first.meeting_url)
        if existing_meeting and existing_meeting.id:
            # Minutesが存在し、Conversationがあればスキップ
            existing_minutes = await self._minutes_repo.get_by_meeting(
                existing_meeting.id
            )
            if existing_minutes:
                existing_convs = await self._conversation_repo.get_by_minutes(
                    existing_minutes.id  # type: ignore[arg-type]
                )
                if existing_convs:
                    logger.info(
                        "会議 %s は既にインポート済み（%d件の発言あり）、スキップ",
                        first.issue_id,
                        len(existing_convs),
                    )
                    output.total_speeches_skipped += len(speeches)
                    return

        # Conference を解決
        conference = await self._resolve_conference(
            first.name_of_house, first.name_of_meeting, governing_body_id
        )
        if not conference or not conference.id:
            conf_name = f"{first.name_of_house}{first.name_of_meeting}"
            output.errors.append(f"Conference '{conf_name}' の解決に失敗")
            return

        # Meeting を作成（既存があればそれを使用）
        meeting = existing_meeting
        if not meeting:
            meeting_date = date.fromisoformat(first.date)
            meeting_name = f"第{first.session}回国会 {first.issue}"
            meeting = Meeting(
                conference_id=conference.id,
                date=meeting_date,
                url=first.meeting_url,
                name=meeting_name,
            )
            meeting = await self._meeting_repo.create(meeting)
            output.total_meetings_created += 1
            logger.info("会議を作成: %s (%s)", meeting.name, first.date)

        if not meeting.id:
            output.errors.append(f"Meeting作成に失敗: {first.issue_id}")
            return

        # Minutes を作成
        existing_minutes = await self._minutes_repo.get_by_meeting(meeting.id)
        minutes = existing_minutes
        if not minutes:
            minutes = Minutes(meeting_id=meeting.id, url=first.meeting_url)
            minutes = await self._minutes_repo.create(minutes)

        if not minutes or not minutes.id:
            output.errors.append(f"Minutes作成に失敗: {first.issue_id}")
            return

        # Speaker処理 + Conversation作成
        conversations: list[Conversation] = []
        for speech in speeches:
            speaker_id = await self._resolve_speaker(speech, output)
            speaker_name = self._normalize_speaker_name(speech.speaker)
            conv = Conversation(
                comment=speech.speech,
                sequence_number=speech.speech_order,
                minutes_id=minutes.id,
                speaker_id=speaker_id,
                speaker_name=speaker_name,
                is_manually_verified=True,
            )
            conversations.append(conv)

        # 一括保存
        created = await self._conversation_repo.bulk_create(conversations)
        output.total_speeches_imported += len(created)
        logger.info("会議 %s: %d 件の発言を保存しました", first.issue_id, len(created))

    async def _resolve_conference(
        self,
        name_of_house: str,
        name_of_meeting: str,
        governing_body_id: int,
    ) -> Conference | None:
        """院名 + 会議名 → Conference を特定/新規作成."""
        conference_name = f"{name_of_house}{name_of_meeting}"

        # 既存Conference検索
        conference = await self._conference_repo.get_by_name_and_governing_body(
            conference_name, governing_body_id
        )
        if conference:
            return conference

        # マスターデータにない場合、警告付きで新規作成
        logger.warning(
            "Conference '%s' がマスターデータに存在しません。新規作成します。",
            conference_name,
        )
        new_conference = Conference(
            name=conference_name,
            governing_body_id=governing_body_id,
        )
        return await self._conference_repo.create(new_conference)

    async def _resolve_speaker(
        self,
        speech: KokkaiSpeechDTO,
        output: ImportKokkaiSpeechesOutputDTO,
    ) -> int | None:
        """発言者を検索/作成してIDを返す."""
        name = self._normalize_speaker_name(speech.speaker)
        if not name:
            return None

        # 既存Speaker検索
        existing = await self._speaker_repo.find_by_name(name)
        if existing:
            # name_yomi が未設定なら更新
            if not existing.name_yomi and speech.speaker_yomi:
                yomi = self._normalize_speaker_name(speech.speaker_yomi)
                if yomi:
                    existing.name_yomi = yomi
                    await self._speaker_repo.update(existing)
            return existing.id

        # 新規Speaker作成
        name_yomi = self._normalize_speaker_name(speech.speaker_yomi)
        speaker = Speaker(
            name=name,
            name_yomi=name_yomi if name_yomi else None,
        )
        created = await self._speaker_repo.create(speaker)
        output.total_speakers_created += 1
        return created.id

    @staticmethod
    def _normalize_speaker_name(name: str) -> str:
        """発言者名を正規化する.

        末尾の「君」「さん」等の敬称を除去し、スペースをトリムする。
        """
        normalized = name.strip()
        normalized = _HONORIFIC_PATTERN.sub("", normalized)
        return normalized.strip()
