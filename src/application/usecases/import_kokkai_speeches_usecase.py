"""国会会議録API発言インポートユースケース.

国会会議録検索システムAPIから発言データを取得し、
Meeting/Minutes/Speaker/Conversation エンティティとしてDBに保存する。
"""

from __future__ import annotations

import logging

from dataclasses import dataclass, field
from datetime import date
from itertools import groupby
from operator import attrgetter

from src.domain.entities.conference import Conference
from src.domain.entities.meeting import Meeting
from src.domain.entities.minutes import Minutes
from src.domain.repositories.conference_repository import ConferenceRepository
from src.domain.repositories.conversation_repository import ConversationRepository
from src.domain.repositories.governing_body_repository import GoverningBodyRepository
from src.domain.repositories.meeting_repository import MeetingRepository
from src.domain.repositories.minutes_repository import MinutesRepository
from src.domain.repositories.speaker_repository import SpeakerRepository
from src.infrastructure.external.kokkai_api.client import KokkaiApiClient
from src.infrastructure.external.kokkai_api.converter import KokkaiSpeechConverter
from src.infrastructure.external.kokkai_api.types import SpeechRecord


logger = logging.getLogger(__name__)


@dataclass
class ImportKokkaiSpeechesInputDTO:
    """入力DTO."""

    # 方法1: issueID指定（単一会議）
    issue_id: str | None = None
    # 方法2: 日付範囲 + 院名指定
    name_of_house: str | None = None
    from_date: str | None = None
    until_date: str | None = None


@dataclass
class ImportKokkaiSpeechesOutputDTO:
    """出力DTO."""

    total_speeches_imported: int = 0
    total_speeches_skipped: int = 0
    total_meetings_created: int = 0
    total_speakers_created: int = 0
    errors: list[str] = field(default_factory=list)


class ImportKokkaiSpeechesUseCase:
    """国会会議録APIから発言を取得しDBに保存するユースケース."""

    # GoverningBody "国会" の検索条件
    _KOKKAI_GB_NAME = "国会"
    _KOKKAI_GB_TYPE = "国"

    def __init__(
        self,
        kokkai_client: KokkaiApiClient,
        meeting_repository: MeetingRepository,
        minutes_repository: MinutesRepository,
        conversation_repository: ConversationRepository,
        speaker_repository: SpeakerRepository,
        conference_repository: ConferenceRepository,
        governing_body_repository: GoverningBodyRepository,
    ) -> None:
        self._client = kokkai_client
        self._meeting_repo = meeting_repository
        self._minutes_repo = minutes_repository
        self._conversation_repo = conversation_repository
        self._speaker_repo = speaker_repository
        self._conference_repo = conference_repository
        self._governing_body_repo = governing_body_repository
        self._converter = KokkaiSpeechConverter()

    async def execute(
        self, input_dto: ImportKokkaiSpeechesInputDTO
    ) -> ImportKokkaiSpeechesOutputDTO:
        """メイン処理: API取得 → エンティティ変換 → DB保存."""
        output = ImportKokkaiSpeechesOutputDTO()

        # 1. APIから発言データを取得
        speeches = await self._fetch_speeches(input_dto)
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

    async def _fetch_speeches(
        self, input_dto: ImportKokkaiSpeechesInputDTO
    ) -> list[SpeechRecord]:
        """APIから発言データを取得."""
        if input_dto.issue_id:
            return await self._client.get_all_speeches(
                issue_id=input_dto.issue_id,
            )
        elif input_dto.name_of_house and input_dto.from_date and input_dto.until_date:
            return await self._client.get_all_speeches(
                name_of_house=input_dto.name_of_house,
                from_date=input_dto.from_date,
                until_date=input_dto.until_date,
            )
        else:
            logger.warning(
                "issue_id または (name_of_house, from_date, until_date) が必要です"
            )
            return []

    async def _process_meeting_speeches(
        self,
        speeches: list[SpeechRecord],
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
            meeting_name = self._converter.build_meeting_name(
                first.session, first.issue
            )
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
        conversations = []
        for speech in speeches:
            speaker_id = await self._resolve_speaker(speech, output)
            conv = self._converter.speech_to_conversation(
                speech, minutes_id=minutes.id, speaker_id=speaker_id
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
        conference_name = self._converter.build_conference_name(
            name_of_house, name_of_meeting
        )

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
        speech: SpeechRecord,
        output: ImportKokkaiSpeechesOutputDTO,
    ) -> int | None:
        """発言者を検索/作成してIDを返す."""
        name = self._converter.normalize_speaker_name(speech.speaker)
        if not name:
            return None

        # 既存Speaker検索
        existing = await self._speaker_repo.find_by_name(name)
        if existing:
            # name_yomi が未設定なら更新
            if not existing.name_yomi and speech.speaker_yomi:
                yomi = self._converter.normalize_speaker_name(speech.speaker_yomi)
                if yomi:
                    existing.name_yomi = yomi
                    await self._speaker_repo.update(existing)
            return existing.id

        # 新規Speaker作成
        speaker = self._converter.speech_to_speaker(speech)
        created = await self._speaker_repo.create(speaker)
        output.total_speakers_created += 1
        return created.id
